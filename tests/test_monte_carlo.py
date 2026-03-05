"""Unit tests for backend/engine/monte_carlo.py"""

import numpy as np
import pytest

from backend.engine.monte_carlo import run_dcf_simulation
from backend.config import KlarmanThresholds

config = KlarmanThresholds()


def make_distributions(
    rev_growth_base: float = 0.05,
    fcf_margin_base: float = 0.08,
    current_revenue: float = 1_000_000_000,
    shares: int = 10_000_000,
) -> dict:
    return {
        "revenue_growth": {"bear": rev_growth_base - 0.05, "base": rev_growth_base, "bull": rev_growth_base + 0.05},
        "fcf_margin": {"bear": fcf_margin_base - 0.03, "base": fcf_margin_base, "bull": fcf_margin_base + 0.05},
        "net_margin": {"bear": 0.05, "base": 0.10, "bull": 0.15},
        "discount_rate": {"bear": 0.12, "base": 0.10, "bull": 0.08},
        "current_fcf": current_revenue * fcf_margin_base,
        "current_revenue": current_revenue,
        "shares_outstanding": shares,
    }


class TestRunDcfSimulation:
    def test_output_length(self):
        result = run_dcf_simulation(make_distributions())
        assert len(result) == config.n_simulations

    def test_output_is_numpy_array(self):
        result = run_dcf_simulation(make_distributions())
        assert isinstance(result, np.ndarray)

    def test_all_values_finite(self):
        result = run_dcf_simulation(make_distributions())
        assert np.all(np.isfinite(result)), "Non-finite values in simulation output"

    def test_positive_median_for_healthy_company(self):
        """A growing, profitable company should yield positive median intrinsic value."""
        result = run_dcf_simulation(make_distributions())
        assert np.median(result) > 0

    def test_higher_growth_yields_higher_value(self):
        """Holding everything else constant, higher growth → higher intrinsic value."""
        low_growth = run_dcf_simulation(make_distributions(rev_growth_base=0.01))
        high_growth = run_dcf_simulation(make_distributions(rev_growth_base=0.15))
        assert np.median(high_growth) > np.median(low_growth)

    def test_higher_fcf_margin_yields_higher_value(self):
        low_margin = run_dcf_simulation(make_distributions(fcf_margin_base=0.02))
        high_margin = run_dcf_simulation(make_distributions(fcf_margin_base=0.20))
        assert np.median(high_margin) > np.median(low_margin)

    def test_larger_share_count_dilutes_per_share_value(self):
        """More shares outstanding → lower per-share value."""
        few_shares = run_dcf_simulation(make_distributions(shares=1_000_000))
        many_shares = run_dcf_simulation(make_distributions(shares=100_000_000))
        assert np.median(few_shares) > np.median(many_shares)

    def test_distribution_has_spread(self):
        """Monte Carlo output must not be a single point — it should have variance."""
        result = run_dcf_simulation(make_distributions())
        assert np.std(result) > 0

    def test_zero_shares_does_not_crash(self):
        """shares_outstanding = 0 is guarded against inside the function."""
        dist = make_distributions(shares=0)
        result = run_dcf_simulation(dist)
        assert result.shape == (config.n_simulations,)

    def test_negative_revenue_growth_still_returns_valid_array(self):
        """Declining company: some paths may yield negative value — that's valid."""
        dist = make_distributions(rev_growth_base=-0.10)
        result = run_dcf_simulation(dist)
        assert np.all(np.isfinite(result))
        assert result.shape == (config.n_simulations,)
