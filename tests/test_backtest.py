"""Unit tests for backend/backtest/engine.py

All price fetching is mocked with deterministic data.
"""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch

from backend.backtest.engine import (
    run_backtest,
    _compute_max_drawdown,
    _compute_cagr,
    _compute_sharpe,
    _align_returns,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_mock_prices(ticker: str, n_months: int = 120, annual_return: float = 0.08, seed: int = 42):
    """
    Generate deterministic monthly price history.
    Uses a log-normal random walk with configurable drift.
    """
    rng = np.random.default_rng(seed + hash(ticker) % 1000)
    monthly_return = annual_return / 12.0
    monthly_vol = 0.04
    log_returns = rng.normal(monthly_return, monthly_vol, n_months)
    prices = 50 * np.exp(np.cumsum(log_returns))
    dates = pd.date_range("2015-01-31", periods=n_months, freq="ME")
    return pd.DataFrame({"price": prices}, index=dates)


def mock_get_price_history(ticker: str, years: int = 10):
    """Mock for get_price_history that returns deterministic data."""
    n_months = years * 12
    if ticker == "SPY":
        return make_mock_prices(ticker, n_months, annual_return=0.10, seed=0)
    elif ticker == "FAIL":
        return pd.DataFrame()  # Simulate failure
    elif ticker == "SHORT":
        return make_mock_prices(ticker, 18, seed=99)  # Too short (< 24 months)
    else:
        # Each ticker gets a unique but deterministic series
        seed = sum(ord(c) for c in ticker)
        return make_mock_prices(ticker, n_months, annual_return=0.06 + (seed % 10) * 0.01, seed=seed)


# ── Helper function tests ────────────────────────────────────────────────────

class TestComputeMaxDrawdown:
    def test_no_drawdown_for_monotonic_increase(self):
        equity = pd.Series([100, 110, 120, 130, 140])
        assert _compute_max_drawdown(equity) == 0.0

    def test_drawdown_calculated_correctly(self):
        equity = pd.Series([100, 120, 90, 110, 80])
        # Peak 120, trough 90 -> DD = (90-120)/120 = -0.25
        # Peak 120 (still), trough 80 -> DD = (80-120)/120 = -0.333
        dd = _compute_max_drawdown(equity)
        assert dd == pytest.approx(-1/3, rel=0.01)

    def test_drawdown_is_negative(self):
        equity = pd.Series([100, 110, 95, 105, 90])
        assert _compute_max_drawdown(equity) < 0


class TestComputeCAGR:
    def test_doubling_in_10_years(self):
        cagr = _compute_cagr(100, 200, 10)
        assert cagr == pytest.approx(0.07177, rel=0.01)

    def test_zero_initial_returns_zero(self):
        assert _compute_cagr(0, 200, 10) == 0.0

    def test_zero_final_returns_zero(self):
        assert _compute_cagr(100, 0, 10) == 0.0

    def test_negative_return(self):
        cagr = _compute_cagr(100, 80, 5)
        assert cagr < 0


class TestComputeSharpe:
    def test_positive_sharpe_for_positive_returns(self):
        returns = pd.Series([0.01, 0.02, 0.015, 0.008, 0.012] * 12)
        assert _compute_sharpe(returns) > 0

    def test_zero_std_returns_zero(self):
        # Perfectly constant returns have std ~0 (float precision may be nonzero)
        returns = pd.Series([0.0] * 36)
        assert _compute_sharpe(returns) == 0.0

    def test_annualization(self):
        returns = pd.Series([0.01, 0.02, -0.005, 0.015] * 12)
        monthly_sharpe = returns.mean() / returns.std()
        annual_sharpe = _compute_sharpe(returns)
        # Annual should be sqrt(12) times monthly
        assert annual_sharpe == pytest.approx(monthly_sharpe * np.sqrt(12), rel=0.01)


class TestAlignReturns:
    def test_aligns_to_common_dates(self):
        dates_a = pd.date_range("2020-01-31", periods=36, freq="ME")
        dates_b = pd.date_range("2020-06-30", periods=36, freq="ME")
        a = pd.Series(np.random.randn(36), index=dates_a, name="A")
        b = pd.Series(np.random.randn(36), index=dates_b, name="B")
        aligned = _align_returns({"A": a, "B": b})
        # Should have only overlapping dates
        assert len(aligned) < 36
        assert set(aligned.columns) == {"A", "B"}

    def test_empty_input(self):
        result = _align_returns({})
        assert result.empty


# ── run_backtest Tests ───────────────────────────────────────────────────────

class TestRunBacktest:
    @patch("backend.backtest.engine.get_price_history", side_effect=mock_get_price_history)
    def test_returns_dict_with_required_keys(self, _mock):
        result = run_backtest(
            ranked_tickers=["AAPL", "MSFT", "GOOG", "AMZN", "META"],
            years=5, top_n=5,
        )
        assert "tickers_held" in result
        assert "benchmark" in result
        assert "portfolio" in result
        assert "benchmark_results" in result
        assert "alpha" in result
        assert "monthly_series" in result
        assert "n_periods" in result

    @patch("backend.backtest.engine.get_price_history", side_effect=mock_get_price_history)
    def test_portfolio_keys_present(self, _mock):
        result = run_backtest(
            ranked_tickers=["AAPL", "MSFT", "GOOG"],
            years=5, top_n=3,
        )
        p = result["portfolio"]
        assert {"cagr", "total_return", "max_drawdown", "sharpe", "calmar", "win_rate", "final_value"} == set(p.keys())

    @patch("backend.backtest.engine.get_price_history", side_effect=mock_get_price_history)
    def test_benchmark_keys_present(self, _mock):
        result = run_backtest(
            ranked_tickers=["AAPL", "MSFT", "GOOG"],
            years=5, top_n=3,
        )
        b = result["benchmark_results"]
        assert {"cagr", "total_return", "max_drawdown", "sharpe", "calmar", "final_value"} == set(b.keys())

    @patch("backend.backtest.engine.get_price_history", side_effect=mock_get_price_history)
    def test_alpha_equals_portfolio_minus_benchmark_cagr(self, _mock):
        result = run_backtest(
            ranked_tickers=["AAPL", "MSFT", "GOOG"],
            years=5, top_n=3,
        )
        expected_alpha = result["portfolio"]["cagr"] - result["benchmark_results"]["cagr"]
        assert result["alpha"] == pytest.approx(expected_alpha, abs=0.0001)

    @patch("backend.backtest.engine.get_price_history", side_effect=mock_get_price_history)
    def test_win_rate_between_0_and_1(self, _mock):
        result = run_backtest(
            ranked_tickers=["AAPL", "MSFT", "GOOG", "AMZN"],
            years=5, top_n=4,
        )
        assert 0.0 <= result["portfolio"]["win_rate"] <= 1.0

    @patch("backend.backtest.engine.get_price_history", side_effect=mock_get_price_history)
    def test_max_drawdown_is_negative(self, _mock):
        result = run_backtest(
            ranked_tickers=["AAPL", "MSFT", "GOOG"],
            years=5, top_n=3,
        )
        assert result["portfolio"]["max_drawdown"] <= 0

    @patch("backend.backtest.engine.get_price_history", side_effect=mock_get_price_history)
    def test_monthly_series_length_matches_n_periods(self, _mock):
        result = run_backtest(
            ranked_tickers=["AAPL", "MSFT", "GOOG"],
            years=5, top_n=3,
        )
        assert len(result["monthly_series"]) == result["n_periods"]

    @patch("backend.backtest.engine.get_price_history", side_effect=mock_get_price_history)
    def test_monthly_series_has_required_fields(self, _mock):
        result = run_backtest(
            ranked_tickers=["AAPL", "MSFT", "GOOG"],
            years=5, top_n=3,
        )
        for entry in result["monthly_series"]:
            assert {"date", "portfolio_return", "benchmark_return", "portfolio_equity", "benchmark_equity"} == set(entry.keys())

    @patch("backend.backtest.engine.get_price_history", side_effect=mock_get_price_history)
    def test_top_n_limits_tickers(self, _mock):
        result = run_backtest(
            ranked_tickers=["AAPL", "MSFT", "GOOG", "AMZN", "META", "NFLX", "TSLA"],
            years=5, top_n=3,
        )
        assert len(result["tickers_held"]) <= 3

    @patch("backend.backtest.engine.get_price_history", side_effect=mock_get_price_history)
    def test_equal_vs_score_weighted_differ(self, _mock):
        tickers = ["AAPL", "MSFT", "GOOG", "AMZN"]
        result_eq = run_backtest(ranked_tickers=tickers, years=5, top_n=4, weighting="equal")
        result_sc = run_backtest(ranked_tickers=tickers, years=5, top_n=4, weighting="score")
        # Weighted results should generally differ from equal-weight
        assert result_eq["portfolio"]["cagr"] != result_sc["portfolio"]["cagr"]

    @patch("backend.backtest.engine.get_price_history", side_effect=mock_get_price_history)
    def test_raises_on_insufficient_tickers(self, _mock):
        with pytest.raises(ValueError, match="insufficient|Need at least"):
            run_backtest(
                ranked_tickers=["FAIL", "SHORT"],
                years=5, top_n=2,
            )

    @patch("backend.backtest.engine.get_price_history", side_effect=mock_get_price_history)
    def test_final_value_matches_equity_curve(self, _mock):
        result = run_backtest(
            ranked_tickers=["AAPL", "MSFT", "GOOG"],
            years=5, top_n=3,
        )
        last_entry = result["monthly_series"][-1]
        assert result["portfolio"]["final_value"] == pytest.approx(last_entry["portfolio_equity"], rel=0.001)

    @patch("backend.backtest.engine.get_price_history", side_effect=mock_get_price_history)
    def test_initial_capital_reflected(self, _mock):
        result = run_backtest(
            ranked_tickers=["AAPL", "MSFT", "GOOG"],
            years=5, top_n=3,
            initial_capital=500_000,
        )
        assert result["initial_capital"] == 500_000
        # First equity values should be near initial capital * (1 + first return)
        first = result["monthly_series"][0]
        # Portfolio equity after first period should be close to 500K
        assert first["portfolio_equity"] > 0

    @patch("backend.backtest.engine.get_price_history", side_effect=mock_get_price_history)
    def test_benchmark_is_spy_by_default(self, _mock):
        result = run_backtest(
            ranked_tickers=["AAPL", "MSFT", "GOOG"],
            years=5, top_n=3,
        )
        assert result["benchmark"] == "SPY"

    @patch("backend.backtest.engine.get_price_history", side_effect=mock_get_price_history)
    def test_total_return_consistent_with_final_value(self, _mock):
        result = run_backtest(
            ranked_tickers=["AAPL", "MSFT", "GOOG"],
            years=5, top_n=3,
        )
        p = result["portfolio"]
        expected_total = (p["final_value"] - result["initial_capital"]) / result["initial_capital"]
        assert p["total_return"] == pytest.approx(expected_total, abs=0.001)
