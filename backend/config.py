from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class KlarmanThresholds:
    # ── Screening thresholds ──────────────────────────────────────────────────
    max_ev_ebit: float = 10.0            # EV/EBIT <= 10
    min_fcf_yield: float = 0.07          # FCF yield >= 7%
    max_price_tangible_book: float = 1.2
    min_revenue: float = 100_000_000     # $100M minimum
    max_net_debt_ebitda: float = 3.0     # Not overleveraged

    # ── Monte Carlo settings ──────────────────────────────────────────────────
    n_simulations: int = 100_000
    projection_years: int = 10
    terminal_growth_rate: float = 0.025  # Conservative 2.5%

    # ── Margin of safety ─────────────────────────────────────────────────────
    required_margin_of_safety: float = 0.30   # Need 30%+ discount
    klarman_downside_percentile: float = 0.25  # Price vs 25th pct of dist

    # ── Kelly sizing ─────────────────────────────────────────────────────────
    max_position_size: float = 0.15    # Max 15% of portfolio
    kelly_fraction: float = 0.25       # Quarter-Kelly (conservative)

    # ── Histogram bucketing ───────────────────────────────────────────────────
    histogram_bins: int = 200          # Max buckets sent to frontend


# Required by SEC EDGAR — override via environment variable
SEC_IDENTITY: str = os.environ.get(
    "SEC_IDENTITY",
    "ParcaeDashboard admin@parcaedashboard.com"
)
