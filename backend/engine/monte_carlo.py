import numpy as np
from backend.config import KlarmanThresholds
from backend.engine.distributions import sample_triangular

config = KlarmanThresholds()


def run_dcf_simulation(distributions: dict) -> np.ndarray:
    """
    Core Monte Carlo DCF engine.

    Runs N fully vectorized simulations and returns an array of
    intrinsic values per share (length = n_simulations).

    Klarman approach:
    - Use FCF, not accounting earnings
    - Conservative terminal growth (clipped 0–4%)
    - Focus on distribution shape, especially the left tail
    - Revenue × FCF-margin as the FCF projection driver
    """
    n = config.n_simulations
    years = config.projection_years

    current_revenue = distributions["current_revenue"]
    shares = distributions["shares_outstanding"]
    if shares <= 0:
        shares = 1

    # ── Sample all stochastic inputs (shape: (n,)) ────────────────────────────
    revenue_growth = sample_triangular(
        distributions["revenue_growth"]["bear"],
        distributions["revenue_growth"]["base"],
        distributions["revenue_growth"]["bull"],
        n,
    )

    fcf_margin = sample_triangular(
        distributions["fcf_margin"]["bear"],
        distributions["fcf_margin"]["base"],
        distributions["fcf_margin"]["bull"],
        n,
    )

    discount_rate = sample_triangular(
        distributions["discount_rate"]["bear"],
        distributions["discount_rate"]["base"],
        distributions["discount_rate"]["bull"],
        n,
    )

    terminal_growth = np.random.normal(
        config.terminal_growth_rate,
        0.005,   # Small uncertainty around terminal growth
        n,
    )
    terminal_growth = np.clip(terminal_growth, 0.0, 0.04)

    # ── Project discounted FCF over the holding period ────────────────────────
    # revenue_growth and discount_rate are per-year constants per simulation path.
    # year exponents are broadcast via shape (n, 1) × (1, years).
    year_idx = np.arange(1, years + 1, dtype=float)  # shape (years,)

    # Projected revenue for each year: current_rev * (1 + g)^t  → shape (n, years)
    projected_revenue = current_revenue * (
        (1.0 + revenue_growth[:, np.newaxis]) ** year_idx[np.newaxis, :]
    )

    # Projected FCF = revenue × FCF margin  → shape (n, years)
    projected_fcf = projected_revenue * fcf_margin[:, np.newaxis]

    # Discount factors  → shape (n, years)
    discount_factors = (1.0 + discount_rate[:, np.newaxis]) ** year_idx[np.newaxis, :]

    # Present value of FCF stream  → shape (n,)
    pv_fcfs = (projected_fcf / discount_factors).sum(axis=1)

    # ── Terminal value ────────────────────────────────────────────────────────
    final_year_fcf = current_revenue * (1.0 + revenue_growth) ** years * fcf_margin
    spread = discount_rate - terminal_growth

    # Gordon Growth Model — avoid divide-by-zero / negative spread
    tv_raw = np.where(
        spread > 0,
        final_year_fcf * (1.0 + terminal_growth) / spread,
        0.0,
    )
    pv_terminal = tv_raw / (1.0 + discount_rate) ** years

    # ── Aggregate and convert to per-share value ──────────────────────────────
    total_value = pv_fcfs + pv_terminal
    intrinsic_value_per_share = total_value / shares

    return intrinsic_value_per_share
