"""Unit tests for backend/engine/distributions.py"""

import numpy as np
import pytest

from backend.engine.distributions import build_distributions_from_history, sample_triangular


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_edgar_data(n: int = 10) -> dict:
    """Synthetic edgar data: steadily growing company."""
    base_rev = 1_000_000_000  # $1B
    revenues = [base_rev * (1.05 ** i) for i in range(n)]
    net_incomes = [r * 0.10 for r in revenues]
    fcfs = [r * 0.08 for r in revenues]
    margins = [ni / r for ni, r in zip(net_incomes, revenues)]
    capex = [r * 0.04 for r in revenues]
    return {
        "revenues": revenues,
        "net_incomes": net_incomes,
        "fcfs": fcfs,
        "margins": margins,
        "capex": capex,
    }


def make_yf_data() -> dict:
    return {
        "ticker": "TEST",
        "price": 50.0,
        "shares_outstanding": 10_000_000,
        "market_cap": 500_000_000,
    }


# ── build_distributions_from_history ──────────────────────────────────────────

class TestBuildDistributions:
    def test_returns_required_keys(self):
        result = build_distributions_from_history(make_edgar_data(), make_yf_data())
        required = {
            "revenue_growth", "fcf_margin", "net_margin",
            "discount_rate", "current_fcf", "current_revenue", "shares_outstanding",
        }
        assert required.issubset(result.keys())

    def test_sub_dicts_have_bear_base_bull(self):
        result = build_distributions_from_history(make_edgar_data(), make_yf_data())
        for key in ("revenue_growth", "fcf_margin", "net_margin", "discount_rate"):
            assert set(result[key].keys()) == {"bear", "base", "bull"}, f"{key} missing keys"

    def test_bear_leq_base_leq_bull_for_growth(self):
        result = build_distributions_from_history(make_edgar_data(), make_yf_data())
        for key in ("revenue_growth", "fcf_margin"):
            d = result[key]
            assert d["bear"] <= d["base"] <= d["bull"], f"{key}: bear <= base <= bull violated"

    def test_current_values_match_last_year(self):
        edgar = make_edgar_data()
        result = build_distributions_from_history(edgar, make_yf_data())
        assert result["current_revenue"] == pytest.approx(edgar["revenues"][-1], rel=1e-6)
        assert result["current_fcf"] == pytest.approx(edgar["fcfs"][-1], rel=1e-6)

    def test_shares_outstanding_passed_through(self):
        yf = make_yf_data()
        result = build_distributions_from_history(make_edgar_data(), yf)
        assert result["shares_outstanding"] == yf["shares_outstanding"]

    def test_discount_rate_conservative(self):
        result = build_distributions_from_history(make_edgar_data(), make_yf_data())
        dr = result["discount_rate"]
        # Bear discount rate should be highest (more risk)
        assert dr["bear"] > dr["bull"]
        assert dr["bear"] >= 0.08

    def test_handles_minimal_history(self):
        """Should still return a valid dict with 5 years of data."""
        result = build_distributions_from_history(make_edgar_data(n=5), make_yf_data())
        assert "revenue_growth" in result

    def test_fallback_when_no_shares(self):
        """Missing shares_outstanding should default to 1, not crash."""
        yf = make_yf_data()
        yf["shares_outstanding"] = None
        result = build_distributions_from_history(make_edgar_data(), yf)
        assert result["shares_outstanding"] == 1


# ── sample_triangular ─────────────────────────────────────────────────────────

class TestSampleTriangular:
    N = 100_000

    def test_output_shape(self):
        samples = sample_triangular(-0.1, 0.05, 0.2, self.N)
        assert samples.shape == (self.N,)

    def test_samples_within_bounds(self):
        low, mode, high = -0.05, 0.05, 0.15
        samples = sample_triangular(low, mode, high, self.N)
        assert samples.min() >= low - 1e-9
        assert samples.max() <= high + 1e-9

    def test_mode_is_most_common(self):
        """Median of samples should be close to the mode for a symmetric triangle."""
        samples = sample_triangular(0.0, 0.5, 1.0, self.N)
        assert abs(np.median(samples) - 0.5) < 0.02

    def test_degenerate_all_equal(self):
        """If bear == base == bull, all samples must equal that value."""
        samples = sample_triangular(0.05, 0.05, 0.05, 100)
        assert np.all(samples == pytest.approx(0.05))

    def test_negative_values_supported(self):
        """Should handle negative growth rates without error."""
        samples = sample_triangular(-0.30, -0.10, 0.05, self.N)
        assert samples.shape == (self.N,)
        assert samples.min() >= -0.30 - 1e-9

    def test_deterministic_with_seed(self):
        np.random.seed(42)
        s1 = sample_triangular(0.0, 0.1, 0.2, 1000)
        np.random.seed(42)
        s2 = sample_triangular(0.0, 0.1, 0.2, 1000)
        np.testing.assert_array_equal(s1, s2)
