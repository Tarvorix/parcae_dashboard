"""
Unit tests for backend/portfolio/copula.py

Uses synthetic correlated return series — no network calls.
"""

import numpy as np
import pytest

from backend.portfolio.copula import (
    gaussian_copula_portfolio_var,
    student_t_copula_portfolio_var,
    _empirical_cdf_inverse,
)


# ── Synthetic data helpers ─────────────────────────────────────────────────────

def make_correlated_returns(
    n_positions: int = 4,
    n_periods: int = 120,
    mean: float = 0.008,
    std: float = 0.05,
    rho: float = 0.4,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate synthetic monthly returns with a given pairwise correlation rho.
    Returns (position_returns, correlation_matrix).
    """
    np.random.seed(seed)
    corr = np.full((n_positions, n_positions), rho)
    np.fill_diagonal(corr, 1.0)

    L = np.linalg.cholesky(corr)
    z = np.random.standard_normal((n_periods, n_positions))
    correlated = z @ L.T

    # Scale to target mean/std
    returns = correlated * std + mean   # shape (n_periods, n_positions)
    return returns.T, corr              # (n_positions, n_periods), corr_matrix


def make_identity_returns(n: int = 3, periods: int = 120) -> tuple[np.ndarray, np.ndarray]:
    """Uncorrelated positions — identity correlation matrix."""
    np.random.seed(0)
    returns = np.random.normal(0.01, 0.04, (n, periods))
    corr = np.eye(n)
    return returns, corr


# ── _empirical_cdf_inverse ────────────────────────────────────────────────────

class TestEmpiricalCdfInverse:
    def test_output_shape(self):
        hist = np.sort(np.random.normal(0, 1, 100))
        u = np.random.uniform(0, 1, 200)
        out = _empirical_cdf_inverse(u, hist)
        assert out.shape == (200,)

    def test_u_zero_maps_to_min(self):
        hist = np.sort(np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
        result = _empirical_cdf_inverse(np.array([0.0]), hist)
        assert result[0] == pytest.approx(1.0)

    def test_u_one_maps_to_max(self):
        hist = np.sort(np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
        result = _empirical_cdf_inverse(np.array([1.0]), hist)
        assert result[0] == pytest.approx(5.0)

    def test_interpolation_midpoint(self):
        hist = np.sort(np.array([0.0, 2.0]))
        result = _empirical_cdf_inverse(np.array([0.5]), hist)
        assert result[0] == pytest.approx(1.0)

    def test_output_within_hist_range(self):
        hist = np.sort(np.random.normal(0.01, 0.05, 60))
        u = np.random.uniform(0, 1, 1000)
        out = _empirical_cdf_inverse(u, hist)
        assert out.min() >= hist.min() - 1e-9
        assert out.max() <= hist.max() + 1e-9


# ── gaussian_copula_portfolio_var ─────────────────────────────────────────────

class TestGaussianCopulaPortfolioVar:
    def setup_method(self):
        self.returns, self.corr = make_correlated_returns()

    def test_returns_required_keys(self):
        result = gaussian_copula_portfolio_var(
            self.returns, self.corr, random_state=0
        )
        required = {
            "var", "cvar", "max_drawdown_sim", "mean_return", "std_return",
            "correlation_matrix", "n_positions", "n_simulations",
            "confidence", "weights",
        }
        assert required.issubset(result.keys())

    def test_var_less_than_or_equal_to_cvar(self):
        result = gaussian_copula_portfolio_var(
            self.returns, self.corr, random_state=0
        )
        # VaR ≥ CVaR (CVaR is a worse loss, i.e. more negative)
        assert result["cvar"] <= result["var"]

    def test_var_is_negative_for_risky_portfolio(self):
        """At 95% confidence, 5th-percentile loss should be negative for volatile portfolio."""
        returns, corr = make_correlated_returns(mean=-0.005, std=0.07)
        result = gaussian_copula_portfolio_var(returns, corr, random_state=0)
        assert result["var"] < 0

    def test_n_positions_correct(self):
        result = gaussian_copula_portfolio_var(
            self.returns, self.corr, random_state=0
        )
        assert result["n_positions"] == self.returns.shape[0]

    def test_weights_sum_to_one(self):
        result = gaussian_copula_portfolio_var(
            self.returns, self.corr, random_state=0
        )
        assert abs(sum(result["weights"]) - 1.0) < 1e-9

    def test_custom_weights(self):
        weights = np.array([0.4, 0.3, 0.2, 0.1])
        result = gaussian_copula_portfolio_var(
            self.returns, self.corr, weights=weights, random_state=0
        )
        assert result["weights"] == pytest.approx([0.4, 0.3, 0.2, 0.1], abs=1e-6)

    def test_unequal_weights_differ_from_equal_weight(self):
        equal_result = gaussian_copula_portfolio_var(
            self.returns, self.corr, random_state=42
        )
        skewed_weights = np.array([0.7, 0.1, 0.1, 0.1])
        skewed_result = gaussian_copula_portfolio_var(
            self.returns, self.corr, weights=skewed_weights, random_state=42
        )
        assert equal_result["var"] != skewed_result["var"]

    def test_correlation_matrix_in_output(self):
        result = gaussian_copula_portfolio_var(
            self.returns, self.corr, random_state=0
        )
        assert np.allclose(result["correlation_matrix"], self.corr.tolist())

    def test_reproducible_with_seed(self):
        r1 = gaussian_copula_portfolio_var(self.returns, self.corr, random_state=7)
        r2 = gaussian_copula_portfolio_var(self.returns, self.corr, random_state=7)
        assert r1["var"] == r2["var"]
        assert r1["cvar"] == r2["cvar"]

    def test_different_seeds_give_different_results(self):
        r1 = gaussian_copula_portfolio_var(self.returns, self.corr, random_state=1)
        r2 = gaussian_copula_portfolio_var(self.returns, self.corr, random_state=999)
        # VaR may differ (Monte Carlo noise)
        assert r1["mean_return"] != r2["mean_return"]

    def test_higher_confidence_gives_worse_var(self):
        r95 = gaussian_copula_portfolio_var(
            self.returns, self.corr, confidence=0.95, random_state=0
        )
        r99 = gaussian_copula_portfolio_var(
            self.returns, self.corr, confidence=0.99, random_state=0
        )
        assert r99["var"] <= r95["var"]

    def test_single_position(self):
        returns = np.random.normal(0.01, 0.05, (1, 120))
        corr = np.array([[1.0]])
        result = gaussian_copula_portfolio_var(returns, corr, random_state=0)
        assert result["n_positions"] == 1
        assert len(result["weights"]) == 1

    def test_two_positions(self):
        returns, corr = make_correlated_returns(n_positions=2)
        result = gaussian_copula_portfolio_var(returns, corr, random_state=0)
        assert result["n_positions"] == 2


# ── student_t_copula_portfolio_var ────────────────────────────────────────────

class TestStudentTCopulaPortfolioVar:
    def setup_method(self):
        self.returns, self.corr = make_correlated_returns()

    def test_returns_required_keys(self):
        result = student_t_copula_portfolio_var(
            self.returns, self.corr, random_state=0
        )
        required = {
            "var", "cvar", "max_drawdown_sim", "mean_return", "std_return",
            "correlation_matrix", "n_positions", "n_simulations",
            "confidence", "df", "weights",
        }
        assert required.issubset(result.keys())

    def test_var_leq_cvar(self):
        result = student_t_copula_portfolio_var(
            self.returns, self.corr, random_state=0
        )
        assert result["cvar"] <= result["var"]

    def test_df_in_output(self):
        result = student_t_copula_portfolio_var(
            self.returns, self.corr, df=5.0, random_state=0
        )
        assert result["df"] == 5.0

    def test_weights_sum_to_one(self):
        result = student_t_copula_portfolio_var(
            self.returns, self.corr, random_state=0
        )
        assert abs(sum(result["weights"]) - 1.0) < 1e-9

    def test_reproducible_with_seed(self):
        r1 = student_t_copula_portfolio_var(self.returns, self.corr, random_state=42)
        r2 = student_t_copula_portfolio_var(self.returns, self.corr, random_state=42)
        assert r1["var"] == r2["var"]

    def test_lower_df_gives_heavier_tails(self):
        """Lower degrees of freedom → heavier tails → worse (more negative) VaR."""
        r_fat = student_t_copula_portfolio_var(
            self.returns, self.corr, df=2.5, random_state=0
        )
        r_thin = student_t_copula_portfolio_var(
            self.returns, self.corr, df=30.0, random_state=0
        )
        # With df=2.5, the distribution has fatter tails → worse max drawdown
        assert r_fat["max_drawdown_sim"] <= r_thin["max_drawdown_sim"]

    def test_n_positions_correct(self):
        result = student_t_copula_portfolio_var(
            self.returns, self.corr, random_state=0
        )
        assert result["n_positions"] == self.returns.shape[0]
