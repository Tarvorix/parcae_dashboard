"""
Unit tests for backend/portfolio/tail_risk.py

Uses synthetic return series — no network calls.
"""

import numpy as np
import pytest

from backend.portfolio.tail_risk import (
    calculate_historical_var,
    calculate_cvar,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_tail_risk_summary,
    concentration_risk,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_returns(mean: float = 0.01, std: float = 0.05, n: int = 120, seed: int = 0) -> np.ndarray:
    np.random.seed(seed)
    return np.random.normal(mean, std, n)


def make_position_returns(n_pos: int = 3, n_per: int = 120, seed: int = 0) -> np.ndarray:
    np.random.seed(seed)
    return np.random.normal(0.008, 0.04, (n_pos, n_per))


# ── calculate_historical_var ──────────────────────────────────────────────────

class TestCalculateHistoricalVar:
    def test_returns_scalar(self):
        r = make_returns()
        assert isinstance(calculate_historical_var(r), float)

    def test_var_is_in_return_range(self):
        r = make_returns()
        var = calculate_historical_var(r)
        assert r.min() <= var <= r.max()

    def test_var_negative_for_volatile_series(self):
        r = make_returns(mean=-0.01, std=0.07)
        var = calculate_historical_var(r)
        assert var < 0

    def test_higher_confidence_gives_lower_var(self):
        r = make_returns()
        var95 = calculate_historical_var(r, confidence=0.95)
        var99 = calculate_historical_var(r, confidence=0.99)
        assert var99 <= var95

    def test_constant_series_returns_that_value(self):
        r = np.full(100, 0.02)
        var = calculate_historical_var(r, confidence=0.95)
        assert var == pytest.approx(0.02)


# ── calculate_cvar ────────────────────────────────────────────────────────────

class TestCalculateCvar:
    def test_cvar_leq_var(self):
        r = make_returns()
        var = calculate_historical_var(r)
        cvar = calculate_cvar(r)
        assert cvar <= var

    def test_cvar_is_scalar(self):
        assert isinstance(calculate_cvar(make_returns()), float)

    def test_cvar_leq_var_for_many_seeds(self):
        for seed in range(10):
            r = make_returns(seed=seed)
            assert calculate_cvar(r) <= calculate_historical_var(r)

    def test_cvar_worse_for_heavier_tail(self):
        """Return series with outlier losses should have worse CVaR."""
        np.random.seed(1)
        r_normal = np.random.normal(0.01, 0.03, 120)
        r_crash = r_normal.copy()
        r_crash[:5] = -0.30  # Add 5 crash observations
        assert calculate_cvar(r_crash) < calculate_cvar(r_normal)


# ── calculate_max_drawdown ────────────────────────────────────────────────────

class TestCalculateMaxDrawdown:
    def test_returns_non_positive(self):
        r = make_returns()
        assert calculate_max_drawdown(r) <= 0

    def test_all_positive_returns_gives_zero_drawdown(self):
        r = np.full(50, 0.01)
        # All months up → no drawdown
        assert calculate_max_drawdown(r) == pytest.approx(0.0, abs=1e-9)

    def test_single_large_loss_captured(self):
        """A −50% month should produce at least −50% drawdown."""
        r = np.array([0.01, 0.01, -0.50, 0.01, 0.01])
        dd = calculate_max_drawdown(r)
        assert dd <= -0.40

    def test_returns_scalar(self):
        assert isinstance(calculate_max_drawdown(make_returns()), float)


# ── calculate_sharpe_ratio ────────────────────────────────────────────────────

class TestCalculateSharpeRatio:
    def test_returns_scalar(self):
        assert isinstance(calculate_sharpe_ratio(make_returns()), float)

    def test_higher_mean_gives_higher_sharpe(self):
        s_low = calculate_sharpe_ratio(make_returns(mean=0.001, std=0.05))
        s_high = calculate_sharpe_ratio(make_returns(mean=0.015, std=0.05))
        assert s_high > s_low

    def test_higher_std_gives_lower_sharpe(self):
        s_low_vol = calculate_sharpe_ratio(make_returns(mean=0.01, std=0.02))
        s_high_vol = calculate_sharpe_ratio(make_returns(mean=0.01, std=0.10))
        assert s_low_vol > s_high_vol

    def test_constant_series_returns_zero(self):
        r = np.full(120, 0.004)   # exactly risk-free per period
        result = calculate_sharpe_ratio(r, risk_free_rate=0.048, periods_per_year=12)
        assert result == pytest.approx(0.0, abs=0.1)

    def test_zero_std_returns_zero(self):
        r = np.full(60, 0.02)
        result = calculate_sharpe_ratio(r)
        assert result == 0.0


# ── calculate_tail_risk_summary ───────────────────────────────────────────────

class TestCalculateTailRiskSummary:
    def test_required_keys_present(self):
        pos = make_position_returns()
        result = calculate_tail_risk_summary(pos)
        required = {
            "portfolio_var", "portfolio_cvar", "portfolio_max_drawdown",
            "portfolio_sharpe", "portfolio_mean_return", "portfolio_std_return",
            "n_positions", "n_periods", "confidence", "weights", "per_position",
        }
        assert required.issubset(result.keys())

    def test_n_positions_and_periods_correct(self):
        pos = make_position_returns(n_pos=4, n_per=60)
        result = calculate_tail_risk_summary(pos)
        assert result["n_positions"] == 4
        assert result["n_periods"] == 60

    def test_weights_sum_to_one(self):
        pos = make_position_returns()
        result = calculate_tail_risk_summary(pos)
        assert abs(sum(result["weights"]) - 1.0) < 1e-9

    def test_custom_weights_used(self):
        pos = make_position_returns(n_pos=3)
        w = np.array([0.5, 0.3, 0.2])
        result = calculate_tail_risk_summary(pos, weights=w)
        assert result["weights"] == pytest.approx([0.5, 0.3, 0.2], abs=1e-6)

    def test_cvar_leq_var(self):
        pos = make_position_returns()
        result = calculate_tail_risk_summary(pos)
        assert result["portfolio_cvar"] <= result["portfolio_var"]

    def test_max_drawdown_non_positive(self):
        pos = make_position_returns()
        result = calculate_tail_risk_summary(pos)
        assert result["portfolio_max_drawdown"] <= 0

    def test_per_position_length(self):
        pos = make_position_returns(n_pos=5)
        result = calculate_tail_risk_summary(pos)
        assert len(result["per_position"]) == 5

    def test_per_position_has_required_keys(self):
        pos = make_position_returns()
        result = calculate_tail_risk_summary(pos)
        for p in result["per_position"]:
            assert {"position_index", "weight", "mean_return", "std_return",
                    "var", "cvar", "max_drawdown", "sharpe"}.issubset(p.keys())

    def test_single_position(self):
        pos = make_position_returns(n_pos=1)
        result = calculate_tail_risk_summary(pos)
        assert result["n_positions"] == 1
        assert len(result["per_position"]) == 1


# ── concentration_risk ────────────────────────────────────────────────────────

class TestConcentrationRisk:
    def test_equal_weights_gives_minimum_hhi(self):
        n = 5
        w = np.ones(n) / n
        result = concentration_risk(w)
        assert result["hhi"] == pytest.approx(1.0 / n, abs=1e-6)

    def test_full_concentration_gives_hhi_one(self):
        w = np.array([1.0, 0.0, 0.0])
        result = concentration_risk(w)
        assert result["hhi"] == pytest.approx(1.0, abs=1e-6)

    def test_effective_n_equals_n_for_equal_weights(self):
        n = 4
        w = np.ones(n) / n
        result = concentration_risk(w)
        assert result["effective_n"] == pytest.approx(float(n), abs=0.01)

    def test_required_keys_present(self):
        w = np.array([0.25, 0.25, 0.25, 0.25])
        result = concentration_risk(w)
        assert {"hhi", "effective_n", "max_weight", "min_weight"}.issubset(result.keys())

    def test_max_and_min_weight_correct(self):
        w = np.array([0.6, 0.3, 0.1])
        result = concentration_risk(w)
        assert result["max_weight"] == pytest.approx(0.6, abs=1e-4)
        assert result["min_weight"] == pytest.approx(0.1, abs=1e-4)

    def test_unnormalised_weights_are_normalised(self):
        w = np.array([2.0, 2.0, 2.0, 2.0])
        result = concentration_risk(w)
        assert result["hhi"] == pytest.approx(0.25, abs=1e-6)
