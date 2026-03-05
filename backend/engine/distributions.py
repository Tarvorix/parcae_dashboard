import numpy as np
from typing import Optional


def build_distributions_from_history(edgar_data: dict, yf_data: dict) -> dict:
    """
    Convert 10-year historical financial data into bear/base/bull
    triangular distribution parameters for Monte Carlo DCF.

    Klarman approach:
      - base  = median of historical observations
      - bear  = 10th percentile (worse-than-typical)
      - bull  = 75th percentile (good but not optimistic — stay conservative)
    """
    fcfs = np.array(edgar_data["fcfs"], dtype=float)
    revenues = np.array(edgar_data["revenues"], dtype=float)
    margins = np.array(edgar_data["margins"], dtype=float)

    # ── Year-over-year growth rates ───────────────────────────────────────────
    def _growth_rates(series: np.ndarray) -> np.ndarray:
        diffs = np.diff(series)
        bases = np.abs(series[:-1])
        rates = np.where(bases > 0, diffs / bases, np.nan)
        return rates[np.isfinite(rates)]

    fcf_growth_rates = _growth_rates(fcfs)
    rev_growth_rates = _growth_rates(revenues)

    # ── Revenue growth distribution ───────────────────────────────────────────
    if len(rev_growth_rates) > 0:
        rev_growth = {
            "bear": float(np.percentile(rev_growth_rates, 10)),
            "base": float(np.median(rev_growth_rates)),
            "bull": float(np.percentile(rev_growth_rates, 75)),
        }
    else:
        rev_growth = {"bear": -0.05, "base": 0.03, "bull": 0.08}

    # ── Net margin distribution ───────────────────────────────────────────────
    if len(margins) > 0:
        margin = {
            "bear": float(np.percentile(margins, 10)),
            "base": float(np.median(margins)),
            "bull": float(np.percentile(margins, 75)),
        }
    else:
        margin = {"bear": 0.02, "base": 0.06, "bull": 0.12}

    # ── FCF margin distribution (FCF / Revenue) ───────────────────────────────
    with np.errstate(divide="ignore", invalid="ignore"):
        fcf_margins = np.where(revenues[: len(fcfs)] > 0, fcfs / revenues[: len(fcfs)], np.nan)
    fcf_margins = fcf_margins[np.isfinite(fcf_margins)]

    if len(fcf_margins) > 0:
        fcf_margin = {
            "bear": float(np.percentile(fcf_margins, 10)),
            "base": float(np.median(fcf_margins)),
            "bull": float(np.percentile(fcf_margins, 75)),
        }
    else:
        fcf_margin = {"bear": 0.01, "base": 0.05, "bull": 0.10}

    # ── Discount rate (conservative WACC proxy) ───────────────────────────────
    discount_rate = {
        "bear": 0.12,   # High risk scenario
        "base": 0.10,
        "bull": 0.08,   # Low risk scenario
    }

    return {
        "revenue_growth": rev_growth,
        "fcf_margin": fcf_margin,
        "net_margin": margin,
        "discount_rate": discount_rate,
        "current_fcf": float(fcfs[-1]) if len(fcfs) > 0 else 0.0,
        "current_revenue": float(revenues[-1]) if len(revenues) > 0 else 0.0,
        "shares_outstanding": yf_data.get("shares_outstanding") or 1,
    }


def sample_triangular(bear: float, base: float, bull: float, n: int) -> np.ndarray:
    """
    Draw n samples from a triangular distribution defined by (bear, base, bull).
    Handles degenerate cases where all three values are equal.
    """
    low = min(bear, base, bull)
    high = max(bear, base, bull)
    mode = base

    if low == high:
        return np.full(n, low)

    # Clamp mode strictly inside [low, high]
    mode = float(np.clip(mode, low, high))

    return np.random.triangular(low, mode, high, n)
