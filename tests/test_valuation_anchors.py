"""Unit tests for backend/engine/valuation_anchors.py

Pure math tests — no mocks or network calls needed.
"""

import pytest

from backend.engine.valuation_anchors import (
    calculate_epv,
    calculate_ncav,
    calculate_valuation_anchors,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_yf_data(overrides: dict | None = None) -> dict:
    """Baseline yfinance data for a healthy company."""
    data = {
        "ticker": "TEST",
        "name": "Test Corp",
        "price": 80.0,
        "market_cap": 800_000_000,
        "enterprise_value": 900_000_000,
        "ebit": 100_000_000,
        "ebitda": 120_000_000,
        "free_cashflow": 75_000_000,
        "total_revenue": 500_000_000,
        "tangible_book_value": 20.0,
        "shares_outstanding": 10_000_000,
        "total_debt": 200_000_000,
        "cash": 50_000_000,
        "total_assets": 600_000_000,
        "total_liabilities": 300_000_000,
        "current_assets": 200_000_000,
        "current_liabilities": 100_000_000,
        "working_capital": 100_000_000,
        "retained_earnings": 150_000_000,
        "tax_rate": 0.21,
        "sector": "Technology",
        "industry": "Software",
    }
    if overrides:
        data.update(overrides)
    return data


# ── EPV Tests ────────────────────────────────────────────────────────────────

class TestCalculateEPV:
    def test_returns_dict_with_required_keys(self):
        result = calculate_epv(make_yf_data())
        assert result is not None
        expected = {"epv_total", "epv_per_share", "nopat", "wacc", "tax_rate_used",
                    "franchise_value", "has_franchise"}
        assert expected == set(result.keys())

    def test_nopat_calculation(self):
        data = make_yf_data()
        result = calculate_epv(data)
        expected_nopat = 100_000_000 * (1 - 0.21)
        assert result["nopat"] == pytest.approx(expected_nopat, rel=1e-4)

    def test_epv_per_share_positive(self):
        result = calculate_epv(make_yf_data())
        assert result["epv_per_share"] > 0

    def test_epv_total_equals_nopat_over_wacc(self):
        result = calculate_epv(make_yf_data())
        expected_epv = result["nopat"] / result["wacc"]
        assert result["epv_total"] == pytest.approx(expected_epv, rel=1e-4)

    def test_epv_per_share_equals_total_over_shares(self):
        data = make_yf_data()
        result = calculate_epv(data)
        expected = result["epv_total"] / data["shares_outstanding"]
        assert result["epv_per_share"] == pytest.approx(expected, rel=1e-4)

    def test_returns_none_when_ebit_missing(self):
        assert calculate_epv(make_yf_data({"ebit": None})) is None

    def test_returns_none_when_ebit_zero(self):
        assert calculate_epv(make_yf_data({"ebit": 0})) is None

    def test_returns_none_when_shares_missing(self):
        assert calculate_epv(make_yf_data({"shares_outstanding": None})) is None

    def test_returns_none_when_shares_zero(self):
        assert calculate_epv(make_yf_data({"shares_outstanding": 0})) is None

    def test_uses_default_tax_rate_when_missing(self):
        result = calculate_epv(make_yf_data({"tax_rate": None}))
        assert result["tax_rate_used"] == pytest.approx(0.21)

    def test_uses_default_tax_rate_when_invalid(self):
        result = calculate_epv(make_yf_data({"tax_rate": -0.5}))
        assert result["tax_rate_used"] == pytest.approx(0.21)

    def test_uses_provided_tax_rate(self):
        result = calculate_epv(make_yf_data({"tax_rate": 0.25}))
        assert result["tax_rate_used"] == pytest.approx(0.25)

    def test_wacc_floor_at_4_percent(self):
        # All equity, zero debt scenario — should still be above 4%
        data = make_yf_data({"total_debt": 0, "market_cap": 1_000_000_000})
        result = calculate_epv(data)
        assert result["wacc"] >= 0.04

    def test_higher_ebit_gives_higher_epv(self):
        low = calculate_epv(make_yf_data({"ebit": 50_000_000}))
        high = calculate_epv(make_yf_data({"ebit": 200_000_000}))
        assert high["epv_per_share"] > low["epv_per_share"]

    def test_franchise_value_positive_when_epv_exceeds_assets(self):
        # High EBIT relative to assets → franchise
        data = make_yf_data({"ebit": 500_000_000, "total_assets": 600_000_000})
        result = calculate_epv(data)
        assert result["franchise_value"] > 0
        assert result["has_franchise"] is True

    def test_franchise_value_negative_when_assets_exceed_epv(self):
        # Low EBIT relative to assets → no franchise
        data = make_yf_data({"ebit": 10_000_000, "total_assets": 600_000_000})
        result = calculate_epv(data)
        assert result["franchise_value"] < 0
        assert result["has_franchise"] is False

    def test_franchise_value_none_when_total_assets_missing(self):
        data = make_yf_data({"total_assets": None})
        result = calculate_epv(data)
        assert result["franchise_value"] is None
        assert result["has_franchise"] is False

    def test_handles_no_debt(self):
        data = make_yf_data({"total_debt": 0})
        result = calculate_epv(data)
        assert result is not None
        assert result["wacc"] > 0

    def test_handles_no_market_cap(self):
        data = make_yf_data({"market_cap": None})
        result = calculate_epv(data)
        assert result is not None
        # With no market cap, should still get a valid result with 100% equity weight


# ── NCAV Tests ───────────────────────────────────────────────────────────────

class TestCalculateNCAV:
    def test_returns_dict_with_required_keys(self):
        result = calculate_ncav(make_yf_data())
        assert result is not None
        expected = {"ncav_total", "ncav_per_share", "current_assets",
                    "total_liabilities", "trades_below_ncav", "discount_to_ncav"}
        assert expected == set(result.keys())

    def test_ncav_calculation(self):
        data = make_yf_data()
        result = calculate_ncav(data)
        expected_ncav = (200_000_000 - 300_000_000) / 10_000_000
        assert result["ncav_per_share"] == pytest.approx(expected_ncav, rel=1e-4)

    def test_ncav_total(self):
        data = make_yf_data()
        result = calculate_ncav(data)
        assert result["ncav_total"] == pytest.approx(200_000_000 - 300_000_000)

    def test_negative_ncav(self):
        # Total liabilities exceed current assets (common case)
        result = calculate_ncav(make_yf_data())
        assert result["ncav_per_share"] < 0

    def test_positive_ncav(self):
        data = make_yf_data({"current_assets": 500_000_000, "total_liabilities": 100_000_000})
        result = calculate_ncav(data)
        assert result["ncav_per_share"] > 0

    def test_trades_below_ncav_true(self):
        data = make_yf_data({
            "current_assets": 500_000_000,
            "total_liabilities": 100_000_000,
            "price": 10.0,
            "shares_outstanding": 10_000_000,
        })
        result = calculate_ncav(data)
        # NCAV/share = (500M - 100M) / 10M = 40, price=10 < 40
        assert result["trades_below_ncav"] is True

    def test_trades_below_ncav_false(self):
        result = calculate_ncav(make_yf_data())
        # NCAV is negative, price is positive
        assert result["trades_below_ncav"] is False

    def test_discount_to_ncav_positive_when_below(self):
        data = make_yf_data({
            "current_assets": 500_000_000,
            "total_liabilities": 100_000_000,
            "price": 10.0,
            "shares_outstanding": 10_000_000,
        })
        result = calculate_ncav(data)
        # NCAV/share=40, price=10 → discount = (40-10)/40 = 0.75
        assert result["discount_to_ncav"] == pytest.approx(0.75, rel=1e-4)

    def test_discount_to_ncav_none_when_ncav_negative(self):
        result = calculate_ncav(make_yf_data())
        assert result["discount_to_ncav"] is None

    def test_returns_none_when_current_assets_missing(self):
        assert calculate_ncav(make_yf_data({"current_assets": None})) is None

    def test_returns_none_when_total_liabilities_missing(self):
        assert calculate_ncav(make_yf_data({"total_liabilities": None})) is None

    def test_returns_none_when_shares_missing(self):
        assert calculate_ncav(make_yf_data({"shares_outstanding": None})) is None

    def test_returns_none_when_shares_zero(self):
        assert calculate_ncav(make_yf_data({"shares_outstanding": 0})) is None


# ── Composite Tests ──────────────────────────────────────────────────────────

class TestCalculateValuationAnchors:
    def test_returns_dict_with_epv_and_ncav(self):
        result = calculate_valuation_anchors(make_yf_data())
        assert "epv" in result
        assert "ncav" in result

    def test_both_present_for_valid_data(self):
        result = calculate_valuation_anchors(make_yf_data())
        assert result["epv"] is not None
        assert result["ncav"] is not None

    def test_epv_none_when_ebit_missing(self):
        result = calculate_valuation_anchors(make_yf_data({"ebit": None}))
        assert result["epv"] is None
        assert result["ncav"] is not None

    def test_ncav_none_when_current_assets_missing(self):
        result = calculate_valuation_anchors(make_yf_data({"current_assets": None}))
        assert result["epv"] is not None
        assert result["ncav"] is None

    def test_both_none_when_data_minimal(self):
        minimal = {"price": 50.0, "total_revenue": 100_000_000}
        result = calculate_valuation_anchors(minimal)
        assert result["epv"] is None
        assert result["ncav"] is None
