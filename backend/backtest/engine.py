"""
Walk-Forward Backtest Engine

Uses current screening rankings + historical prices to simulate portfolio
performance vs a benchmark.

Pipeline:
  1. Fetch monthly prices for ranked tickers + benchmark
  2. Compute monthly returns
  3. Align to common dates
  4. Apply equal-weight or score-weighted allocation
  5. Compute equity curves and performance metrics

Metrics: CAGR, total return, max drawdown, Sharpe, Calmar, win rate, alpha.
"""

from typing import Optional

import numpy as np
import pandas as pd

from backend.data.yfinance_client import get_price_history


def _fetch_monthly_prices(
    tickers: list[str], years: int
) -> dict[str, pd.DataFrame]:
    """
    Fetch monthly price history for each ticker.
    Returns dict mapping ticker -> DataFrame with 'price' column.
    Skips tickers with insufficient data (< 24 months).
    """
    prices = {}
    for ticker in tickers:
        try:
            hist = get_price_history(ticker, years=years)
            if hist is not None and not hist.empty and len(hist) >= 24:
                prices[ticker] = hist
        except Exception:
            continue
    return prices


def _compute_monthly_returns(prices: dict[str, pd.DataFrame]) -> dict[str, pd.Series]:
    """
    Compute monthly percentage returns for each ticker.
    Returns dict mapping ticker -> Series of pct_change returns (NaN-dropped).
    """
    returns = {}
    for ticker, df in prices.items():
        pct = df["price"].pct_change().dropna()
        if len(pct) >= 12:
            returns[ticker] = pct
    return returns


def _align_returns(returns: dict[str, pd.Series]) -> pd.DataFrame:
    """
    Align all return series to common dates via inner join.
    Returns DataFrame with tickers as columns, dates as index.
    """
    if not returns:
        return pd.DataFrame()
    series_list = [s.rename(ticker) for ticker, s in returns.items()]
    aligned = pd.concat(series_list, axis=1, join="inner")
    return aligned.dropna()


def _compute_max_drawdown(equity_curve: pd.Series) -> float:
    """Compute maximum drawdown from an equity curve."""
    peak = equity_curve.expanding().max()
    drawdown = (equity_curve - peak) / peak
    return float(drawdown.min())


def _compute_cagr(initial: float, final: float, years: float) -> float:
    """Compute compound annual growth rate."""
    if initial <= 0 or final <= 0 or years <= 0:
        return 0.0
    return float((final / initial) ** (1.0 / years) - 1.0)


def _compute_sharpe(returns: pd.Series, annualize_factor: float = 12.0) -> float:
    """Compute annualized Sharpe ratio (assumes risk-free rate = 0)."""
    mean_ret = returns.mean()
    std_ret = returns.std()
    if std_ret == 0 or np.isnan(std_ret):
        return 0.0
    return float(mean_ret / std_ret * np.sqrt(annualize_factor))


def run_backtest(
    ranked_tickers: list[str],
    years: int = 10,
    top_n: int = 10,
    weighting: str = "equal",
    initial_capital: float = 100_000,
    benchmark_ticker: str = "SPY",
) -> dict:
    """
    Run a walk-forward backtest using current screening rankings
    and historical monthly prices.

    Args:
        ranked_tickers: Tickers in rank order (best first) from screener.
        years: Number of years of historical data.
        top_n: Number of top-ranked tickers to hold.
        weighting: "equal" or "score" (1/rank normalized).
        initial_capital: Starting portfolio value.
        benchmark_ticker: Benchmark to compare against.

    Returns:
        {
            "tickers_held": [...],
            "benchmark": str,
            "years": int,
            "top_n": int,
            "weighting": str,
            "initial_capital": float,
            "n_periods": int,
            "portfolio": {cagr, total_return, max_drawdown, sharpe, calmar, win_rate, final_value},
            "benchmark_results": {cagr, total_return, max_drawdown, sharpe, calmar, final_value},
            "alpha": float,
            "monthly_series": [{date, portfolio_return, benchmark_return, portfolio_equity, benchmark_equity}, ...]
        }

    Raises:
        ValueError: If fewer than 2 tickers have sufficient price data.
    """
    # Select top N tickers
    selected = ranked_tickers[:top_n]

    # Fetch prices for portfolio tickers + benchmark
    all_tickers = selected + [benchmark_ticker]
    prices = _fetch_monthly_prices(all_tickers, years)

    # Ensure benchmark is available
    if benchmark_ticker not in prices:
        raise ValueError(f"Benchmark {benchmark_ticker} has insufficient price history")

    # Compute returns
    returns_dict = _compute_monthly_returns(prices)

    if benchmark_ticker not in returns_dict:
        raise ValueError(f"Benchmark {benchmark_ticker} has insufficient return data")

    # Separate benchmark from portfolio tickers
    benchmark_returns = returns_dict.pop(benchmark_ticker)

    # Filter to tickers with valid returns
    valid_tickers = [t for t in selected if t in returns_dict]
    if len(valid_tickers) < 2:
        raise ValueError(
            f"Only {len(valid_tickers)} tickers have sufficient price history. Need at least 2."
        )

    # Align portfolio ticker returns
    portfolio_returns_dict = {t: returns_dict[t] for t in valid_tickers}
    aligned = _align_returns(portfolio_returns_dict)

    if aligned.empty or len(aligned) < 12:
        raise ValueError("Insufficient aligned price history for backtest")

    # Align benchmark to same dates
    common_dates = aligned.index.intersection(benchmark_returns.index)
    if len(common_dates) < 12:
        raise ValueError("Insufficient overlapping dates between portfolio and benchmark")

    aligned = aligned.loc[common_dates]
    benchmark_aligned = benchmark_returns.loc[common_dates]

    # Compute weights
    n_held = len(aligned.columns)
    if weighting == "score":
        # 1/rank weights (rank 1 gets highest weight)
        rank_weights = np.array([1.0 / (i + 1) for i in range(n_held)])
        weights = rank_weights / rank_weights.sum()
    else:
        # Equal weight
        weights = np.ones(n_held) / n_held

    # Portfolio returns: weighted sum per period
    portfolio_monthly = (aligned * weights).sum(axis=1)

    # Equity curves
    portfolio_equity = (1 + portfolio_monthly).cumprod() * initial_capital
    benchmark_equity = (1 + benchmark_aligned).cumprod() * initial_capital

    # Portfolio metrics
    n_periods = len(portfolio_monthly)
    actual_years = n_periods / 12.0

    p_final = float(portfolio_equity.iloc[-1])
    p_total_return = (p_final - initial_capital) / initial_capital
    p_cagr = _compute_cagr(initial_capital, p_final, actual_years)
    p_max_dd = _compute_max_drawdown(portfolio_equity)
    p_sharpe = _compute_sharpe(portfolio_monthly)
    p_calmar = abs(p_cagr / p_max_dd) if p_max_dd != 0 else 0.0
    p_win_rate = float((portfolio_monthly > 0).sum() / len(portfolio_monthly))

    # Benchmark metrics
    b_final = float(benchmark_equity.iloc[-1])
    b_total_return = (b_final - initial_capital) / initial_capital
    b_cagr = _compute_cagr(initial_capital, b_final, actual_years)
    b_max_dd = _compute_max_drawdown(benchmark_equity)
    b_sharpe = _compute_sharpe(benchmark_aligned)
    b_calmar = abs(b_cagr / b_max_dd) if b_max_dd != 0 else 0.0

    # Alpha
    alpha = p_cagr - b_cagr

    # Monthly series for charting
    monthly_series = []
    for i, date in enumerate(portfolio_monthly.index):
        monthly_series.append({
            "date": str(date.date()) if hasattr(date, "date") else str(date),
            "portfolio_return": round(float(portfolio_monthly.iloc[i]), 6),
            "benchmark_return": round(float(benchmark_aligned.iloc[i]), 6),
            "portfolio_equity": round(float(portfolio_equity.iloc[i]), 2),
            "benchmark_equity": round(float(benchmark_equity.iloc[i]), 2),
        })

    return {
        "tickers_held": valid_tickers,
        "benchmark": benchmark_ticker,
        "years": years,
        "top_n": top_n,
        "weighting": weighting,
        "initial_capital": initial_capital,
        "n_periods": n_periods,
        "portfolio": {
            "cagr": round(p_cagr, 6),
            "total_return": round(p_total_return, 6),
            "max_drawdown": round(p_max_dd, 6),
            "sharpe": round(p_sharpe, 4),
            "calmar": round(p_calmar, 4),
            "win_rate": round(p_win_rate, 4),
            "final_value": round(p_final, 2),
        },
        "benchmark_results": {
            "cagr": round(b_cagr, 6),
            "total_return": round(b_total_return, 6),
            "max_drawdown": round(b_max_dd, 6),
            "sharpe": round(b_sharpe, 4),
            "calmar": round(b_calmar, 4),
            "final_value": round(b_final, 2),
        },
        "alpha": round(alpha, 6),
        "monthly_series": monthly_series,
    }
