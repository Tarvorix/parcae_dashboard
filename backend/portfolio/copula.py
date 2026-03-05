"""
Gaussian Copula Portfolio Risk Model

Models correlated portfolio tail risk by:
  1. Fitting empirical marginal distributions to each position's return history.
  2. Generating correlated uniform samples via a Gaussian copula.
  3. Mapping those samples back through each position's empirical CDF to
     produce realistic joint return scenarios.
  4. Computing portfolio-level VaR and CVaR from the simulated distribution.

A Student-t copula option is also provided for fatter tails (Klarman's concern
is always the left tail, not the average outcome).
"""

import numpy as np
from scipy import stats
from typing import Optional


def _empirical_cdf_inverse(u: np.ndarray, sorted_hist: np.ndarray) -> np.ndarray:
    """
    Map uniform samples u ∈ [0, 1] back to the empirical distribution
    defined by sorted_hist via linear interpolation.
    """
    n = len(sorted_hist)
    # Convert u to fractional indices, clipped to valid range
    idx_float = u * (n - 1)
    idx_lo = np.floor(idx_float).astype(int).clip(0, n - 2)
    idx_hi = (idx_lo + 1).clip(0, n - 1)
    frac = idx_float - idx_lo
    return sorted_hist[idx_lo] * (1.0 - frac) + sorted_hist[idx_hi] * frac


def gaussian_copula_portfolio_var(
    position_returns: np.ndarray,
    correlation_matrix: np.ndarray,
    weights: Optional[np.ndarray] = None,
    confidence: float = 0.95,
    n_simulations: int = 50_000,
    random_state: Optional[int] = None,
) -> dict:
    """
    Gaussian copula simulation for portfolio tail risk.

    Parameters
    ----------
    position_returns : shape (n_positions, n_periods)
        Historical period returns for each position (e.g. monthly).
    correlation_matrix : shape (n_positions, n_positions)
        Linear correlation matrix across positions.
    weights : shape (n_positions,), optional
        Portfolio weights. Defaults to equal-weight.
    confidence : float
        VaR/CVaR confidence level (default 0.95).
    n_simulations : int
        Number of Monte Carlo paths (default 50,000).
    random_state : int, optional
        Seed for reproducibility.

    Returns
    -------
    dict with var, cvar, max_drawdown_sim, mean_return, std_return,
    correlation_matrix, and n_positions.
    """
    if random_state is not None:
        np.random.seed(random_state)

    n_positions = position_returns.shape[0]

    if weights is None:
        weights = np.ones(n_positions) / n_positions
    else:
        weights = np.asarray(weights, dtype=float)
        weights = weights / weights.sum()   # normalise

    # ── Step 1: Generate correlated standard-normal samples ───────────────────
    # shape (n_simulations, n_positions)
    z = np.random.multivariate_normal(
        mean=np.zeros(n_positions),
        cov=correlation_matrix,
        size=n_simulations,
    )

    # ── Step 2: Convert to uniform [0,1] via the standard normal CDF ─────────
    u = stats.norm.cdf(z)   # shape (n_simulations, n_positions)

    # ── Step 3: Map each column through that position's empirical CDF ─────────
    sim_returns = np.zeros((n_simulations, n_positions))
    for i in range(n_positions):
        sorted_hist = np.sort(position_returns[i])
        sim_returns[:, i] = _empirical_cdf_inverse(u[:, i], sorted_hist)

    # ── Step 4: Weighted portfolio return for each simulated path ─────────────
    portfolio_returns = sim_returns @ weights   # shape (n_simulations,)

    # ── Step 5: Risk metrics ──────────────────────────────────────────────────
    alpha = 1.0 - confidence
    var = float(np.percentile(portfolio_returns, alpha * 100))
    tail_losses = portfolio_returns[portfolio_returns <= var]
    cvar = float(tail_losses.mean()) if len(tail_losses) > 0 else var

    return {
        "var": round(var, 6),
        "cvar": round(cvar, 6),
        "max_drawdown_sim": round(float(portfolio_returns.min()), 6),
        "mean_return": round(float(portfolio_returns.mean()), 6),
        "std_return": round(float(portfolio_returns.std()), 6),
        "correlation_matrix": correlation_matrix.tolist(),
        "n_positions": n_positions,
        "n_simulations": n_simulations,
        "confidence": confidence,
        "weights": weights.tolist(),
    }


def student_t_copula_portfolio_var(
    position_returns: np.ndarray,
    correlation_matrix: np.ndarray,
    df: float = 4.0,
    weights: Optional[np.ndarray] = None,
    confidence: float = 0.95,
    n_simulations: int = 50_000,
    random_state: Optional[int] = None,
) -> dict:
    """
    Student-t copula — heavier tails than Gaussian.  Preferred when
    modelling crisis scenarios (Klarman focus: protect the downside).

    Uses the Cholesky decomposition of the correlation matrix to generate
    correlated t-distributed samples, then follows the same
    copula → empirical-CDF → portfolio path as the Gaussian variant.

    Parameters
    ----------
    df : float
        Degrees of freedom for the t-distribution (lower = fatter tails).
        Typical values: 3–6 for equity returns.
    """
    if random_state is not None:
        np.random.seed(random_state)

    n_positions = position_returns.shape[0]

    if weights is None:
        weights = np.ones(n_positions) / n_positions
    else:
        weights = np.asarray(weights, dtype=float)
        weights = weights / weights.sum()

    # ── Cholesky decomposition of correlation matrix ───────────────────────────
    L = np.linalg.cholesky(correlation_matrix)   # lower triangular

    # ── Draw independent standard-normal samples, then correlate ─────────────
    z_indep = np.random.standard_normal((n_simulations, n_positions))
    z_corr = z_indep @ L.T   # shape (n_simulations, n_positions)

    # ── Chi-squared scaling to produce t-distributed marginals ───────────────
    chi2 = np.random.chisquare(df, size=n_simulations) / df   # shape (n_simulations,)
    t_samples = z_corr / np.sqrt(chi2[:, np.newaxis])

    # ── Convert to uniform via t-CDF ─────────────────────────────────────────
    u = stats.t.cdf(t_samples, df=df)

    # ── Map through empirical CDFs ────────────────────────────────────────────
    sim_returns = np.zeros((n_simulations, n_positions))
    for i in range(n_positions):
        sorted_hist = np.sort(position_returns[i])
        sim_returns[:, i] = _empirical_cdf_inverse(u[:, i], sorted_hist)

    portfolio_returns = sim_returns @ weights

    alpha = 1.0 - confidence
    var = float(np.percentile(portfolio_returns, alpha * 100))
    tail_losses = portfolio_returns[portfolio_returns <= var]
    cvar = float(tail_losses.mean()) if len(tail_losses) > 0 else var

    return {
        "var": round(var, 6),
        "cvar": round(cvar, 6),
        "max_drawdown_sim": round(float(portfolio_returns.min()), 6),
        "mean_return": round(float(portfolio_returns.mean()), 6),
        "std_return": round(float(portfolio_returns.std()), 6),
        "correlation_matrix": correlation_matrix.tolist(),
        "n_positions": n_positions,
        "n_simulations": n_simulations,
        "confidence": confidence,
        "df": df,
        "weights": weights.tolist(),
    }
