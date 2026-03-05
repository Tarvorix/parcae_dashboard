import numpy as np
from backend.config import KlarmanThresholds

config = KlarmanThresholds()


def _bin_histogram(values: np.ndarray, n_bins: int) -> list[dict]:
    """
    Bin a 1-D array into n_bins buckets.
    Returns a list of {bin_start, bin_end, count, frequency} dicts
    suitable for rendering on the frontend.
    """
    counts, edges = np.histogram(values, bins=n_bins)
    total = len(values)
    result = []
    for i, count in enumerate(counts):
        result.append({
            "bin_start": round(float(edges[i]), 2),
            "bin_end": round(float(edges[i + 1]), 2),
            "count": int(count),
            "frequency": round(float(count) / total, 6),
        })
    return result


def calculate_margin_of_safety(
    intrinsic_values: np.ndarray,
    current_price: float,
) -> dict:
    """
    Klarman-style margin-of-safety analysis.

    Focus on downside: compare price to the 25th percentile of the
    value distribution rather than the mean or median.

    Returns a dict ready to be serialised directly by FastAPI.
    """
    # ── Percentile anchors ────────────────────────────────────────────────────
    p10 = float(np.percentile(intrinsic_values, 10))
    p25 = float(np.percentile(intrinsic_values, 25))
    p50 = float(np.percentile(intrinsic_values, 50))
    p75 = float(np.percentile(intrinsic_values, 75))
    p90 = float(np.percentile(intrinsic_values, 90))

    # ── Margin of safety calculations ─────────────────────────────────────────
    mos_median = (p50 - current_price) / p50 if p50 > 0 else -1.0

    # Klarman's preferred metric: MoS vs the downside percentile
    mos_downside = (p25 - current_price) / p25 if p25 > 0 else -1.0

    # Probability that any simulated intrinsic value exceeds the current price
    prob_undervalued = float(np.mean(intrinsic_values > current_price))

    # ── Composite Klarman score (0–100) ───────────────────────────────────────
    # Both the downside MoS *and* the probability of being undervalued must
    # be strong to earn a high score.
    klarman_score = (
        max(0.0, mos_downside) * 0.5
        + max(0.0, prob_undervalued - 0.5) * 2.0 * 0.5
    ) * 100.0

    # ── Histogram bucketed for the frontend (max 200 bins) ───────────────────
    histogram_data = _bin_histogram(intrinsic_values, config.histogram_bins)

    return {
        "current_price": current_price,
        "p10": round(p10, 2),
        "p25": round(p25, 2),
        "p50": round(p50, 2),
        "p75": round(p75, 2),
        "p90": round(p90, 2),
        "mos_median": round(mos_median, 4),
        "mos_downside": round(mos_downside, 4),
        "prob_undervalued": round(prob_undervalued, 4),
        "klarman_score": round(klarman_score, 1),
        "passes_mos_threshold": bool(mos_downside >= config.required_margin_of_safety),
        "histogram_data": histogram_data,
    }
