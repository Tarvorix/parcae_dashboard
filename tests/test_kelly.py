"""Unit tests for backend/engine/kelly.py"""

import pytest

from backend.engine.kelly import calculate_position_size
from backend.config import KlarmanThresholds

config = KlarmanThresholds()

PORTFOLIO = 100_000.0
PRICE = 50.0


class TestCalculatePositionSize:
    def test_required_keys_present(self):
        result = calculate_position_size(0.75, 0.40, PORTFOLIO, PRICE)
        assert {"kelly_full_pct", "kelly_fractional_pct", "dollar_amount", "shares"}.issubset(result.keys())

    def test_zero_prob_returns_zero_position(self):
        result = calculate_position_size(0.0, 0.40, PORTFOLIO, PRICE)
        assert result["kelly_fractional_pct"] == 0.0
        assert result["dollar_amount"] == 0.0
        assert result["shares"] == 0

    def test_zero_mos_returns_zero_position(self):
        result = calculate_position_size(0.80, 0.0, PORTFOLIO, PRICE)
        assert result["kelly_fractional_pct"] == 0.0

    def test_negative_mos_returns_zero_position(self):
        """Negative MoS means overvalued — no position."""
        result = calculate_position_size(0.80, -0.10, PORTFOLIO, PRICE)
        assert result["kelly_fractional_pct"] == 0.0

    def test_position_capped_at_max_size(self):
        """Kelly can recommend large positions; always cap at max_position_size."""
        result = calculate_position_size(0.99, 0.99, PORTFOLIO, PRICE)
        max_pct = config.max_position_size * 100.0
        assert result["kelly_fractional_pct"] <= max_pct + 1e-6

    def test_fractional_kelly_is_quarter_of_full(self):
        """Fractional Kelly should be ≤ quarter-Kelly (before cap)."""
        result = calculate_position_size(0.70, 0.35, PORTFOLIO, PRICE)
        # Full Kelly * 0.25 should equal fractional (before cap)
        expected_frac = min(result["kelly_full_pct"] * config.kelly_fraction, config.max_position_size * 100)
        assert result["kelly_fractional_pct"] == pytest.approx(expected_frac, abs=0.05)

    def test_dollar_amount_consistent_with_pct(self):
        result = calculate_position_size(0.70, 0.35, PORTFOLIO, PRICE)
        # dollar_amount uses full-precision fraction; kelly_fractional_pct is rounded
        # to 1 decimal place, so allow up to $50 tolerance (0.05% of $100k portfolio).
        expected_dollars = PORTFOLIO * result["kelly_fractional_pct"] / 100.0
        assert result["dollar_amount"] == pytest.approx(expected_dollars, abs=50.0)

    def test_shares_consistent_with_dollar_amount(self):
        result = calculate_position_size(0.70, 0.35, PORTFOLIO, PRICE)
        expected_shares = int(result["dollar_amount"] / PRICE)
        assert result["shares"] == expected_shares

    def test_higher_edge_gives_larger_position(self):
        small_mos = calculate_position_size(0.65, 0.20, PORTFOLIO, PRICE)
        large_mos = calculate_position_size(0.65, 0.60, PORTFOLIO, PRICE)
        assert large_mos["kelly_fractional_pct"] >= small_mos["kelly_fractional_pct"]

    def test_higher_prob_gives_larger_position(self):
        low_prob = calculate_position_size(0.55, 0.35, PORTFOLIO, PRICE)
        high_prob = calculate_position_size(0.90, 0.35, PORTFOLIO, PRICE)
        assert high_prob["kelly_fractional_pct"] >= low_prob["kelly_fractional_pct"]

    def test_zero_price_does_not_crash(self):
        result = calculate_position_size(0.75, 0.40, PORTFOLIO, 0.0)
        assert result["shares"] == 0

    def test_returns_for_borderline_prob(self):
        """prob_undervalued exactly 0.5 — tiny or zero Kelly expected."""
        result = calculate_position_size(0.50, 0.30, PORTFOLIO, PRICE)
        # At 50/50 and 30% gain vs 30% loss → Kelly = 0
        assert result["kelly_fractional_pct"] == pytest.approx(0.0, abs=0.5)
