"""
Portfolio Tail Risk Metrics

Computes CVaR, historical VaR, max drawdown, and Sharpe ratio from a
portfolio's simulated or historical return series.  Designed to complement
the copula simulation output from copula.py.
"""

import numpy as np
from typing import Optional


def calculate_historical_var(
    returns: np.ndarray,
    confidence: float = 0.95,
) -> float:
    """
    Historical simulation VaR at the given confidence level.
    Returns the loss (negative return) at the (1-confidence) percentile.
    """
    alpha = 1.0 - confidence
    return float(np.percentile(returns, alpha * 100))


def calculate_cvar(
    returns: np.ndarray,
    confidence: float = 0.95,
) -> float:
    """
    Conditional Value-at-Risk (Expected Shortfall) at the given confidence level.
    Average of all returns below the VaR threshold.
    """
    var = calculate_historical_var(returns, confidence)
    tail = returns[returns <= var]
    return float(tail.mean()) if len(tail) > 0 else var


def calculate_max_drawdown(returns: np.ndarray) -> float:
    """
    Maximum drawdown from a returns series (period-by-period, not paths).
    Returns the worst peak-to-trough decline as a negative fraction.
    """
    cumulative = np.cumprod(1.0 + returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - running_max) / running_max
    return float(drawdowns.min())


def calculate_sharpe_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.05,
    periods_per_year: int = 12,
) -> float:
    """
    Annualised Sharpe ratio.

    Parameters
    ----------
    returns : array of per-period returns
    risk_free_rate : annual risk-free rate
    periods_per_year : 12 for monthly, 252 for daily
    """
    period_rf = risk_free_rate / periods_per_year
    excess = returns - period_rf
    std = float(np.std(excess, ddof=1))
    if std < 1e-12:
        return 0.0
    return float(np.mean(excess) / std * np.sqrt(periods_per_year))


def calculate_tail_risk_summary(
    position_returns: np.ndarray,
    weights: Optional[np.ndarray] = None,
    confidence: float = 0.95,
    risk_free_rate: float = 0.05,
    periods_per_year: int = 12,
) -> dict:
    """
    Full tail risk summary for a portfolio.

    Parameters
    ----------
    position_returns : shape (n_positions, n_periods)
        Historical period returns per position.
    weights : shape (n_positions,), optional
        Portfolio weights. Defaults to equal-weight.

    Returns
    -------
    dict with var, cvar, max_drawdown, sharpe_ratio, mean_return, std_return,
    and per-position stats.
    """
    n_positions, n_periods = position_returns.shape

    if weights is None:
        weights = np.ones(n_positions) / n_positions
    else:
        weights = np.asarray(weights, dtype=float)
        weights = weights / weights.sum()

    # Weighted portfolio return series
    portfolio_returns = position_returns.T @ weights   # shape (n_periods,)

    var = calculate_historical_var(portfolio_returns, confidence)
    cvar = calculate_cvar(portfolio_returns, confidence)
    max_dd = calculate_max_drawdown(portfolio_returns)
    sharpe = calculate_sharpe_ratio(portfolio_returns, risk_free_rate, periods_per_year)

    # Per-position stats
    per_position = []
    for i in range(n_positions):
        r = position_returns[i]
        per_position.append({
            "position_index": i,
            "weight": round(float(weights[i]), 4),
            "mean_return": round(float(r.mean()), 6),
            "std_return": round(float(r.std(ddof=1)), 6),
            "var": round(calculate_historical_var(r, confidence), 6),
            "cvar": round(calculate_cvar(r, confidence), 6),
            "max_drawdown": round(calculate_max_drawdown(r), 6),
            "sharpe": round(calculate_sharpe_ratio(r, risk_free_rate, periods_per_year), 4),
        })

    return {
        "portfolio_var": round(var, 6),
        "portfolio_cvar": round(cvar, 6),
        "portfolio_max_drawdown": round(max_dd, 6),
        "portfolio_sharpe": round(sharpe, 4),
        "portfolio_mean_return": round(float(portfolio_returns.mean()), 6),
        "portfolio_std_return": round(float(portfolio_returns.std(ddof=1)), 6),
        "n_positions": n_positions,
        "n_periods": n_periods,
        "confidence": confidence,
        "weights": weights.tolist(),
        "per_position": per_position,
    }


def concentration_risk(weights: np.ndarray) -> dict:
    """
    Herfindahl-Hirschman Index (HHI) and effective N for portfolio concentration.
    HHI = 1 → completely concentrated; HHI = 1/N → perfectly diversified.
    """
    w = np.asarray(weights, dtype=float)
    w = w / w.sum()
    hhi = float(np.sum(w ** 2))
    effective_n = 1.0 / hhi if hhi > 0 else 0.0
    return {
        "hhi": round(hhi, 6),
        "effective_n": round(effective_n, 2),
        "max_weight": round(float(w.max()), 4),
        "min_weight": round(float(w.min()), 4),
    }
