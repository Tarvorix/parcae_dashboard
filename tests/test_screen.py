"""
Unit tests for backend/screener/screen.py

All yfinance network calls are mocked — no internet access required.
The tests cover:
  - individual metric calculators
  - hard-filter logic
  - composite scoring
  - full screen pipeline
  - ranking correctness
  - edge cases (empty results, missing fields, borderline values)
"""

import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from backend.screener.screen import (
    calculate_ev_ebit,
    calculate_fcf_yield,
    calculate_price_tangible_book,
    calculate_net_debt_ebitda,
    passes_klarman_filters,
    score_candidate,
    run_klarman_screen,
)
from backend.config import KlarmanThresholds

config = KlarmanThresholds()


# ── Fixtures / helpers ────────────────────────────────────────────────────────

def make_data(overrides: dict | None = None) -> dict:
    """
    Default fundamentals for a stock that passes all Klarman filters:
      EV/EBIT = 8.0  (≤ 10)
      FCF Yield = 9%  (≥ 7%)
      P/TBV = 1.0     (≤ 1.2)
      Revenue = $200M  (≥ $100M)
    """
    base = {
        "ticker": "TEST",
        "name": "Test Corp",
        "price": 10.0,
        "market_cap": 1_000_000_000,
        "enterprise_value": 800_000_000,
        "ebit": 100_000_000,           # EV/EBIT = 8.0
        "ebitda": 130_000_000,
        "free_cashflow": 90_000_000,   # FCF yield = 9%
        "total_revenue": 200_000_000,
        "tangible_book_value": 10.0,   # P/TBV = price / book = 1.0
        "shares_outstanding": 100_000_000,
        "total_debt": 150_000_000,
        "cash": 50_000_000,
        "sector": "Industrials",
        "industry": "Manufacturing",
    }
    if overrides:
        base.update(overrides)
    return base


# ── calculate_ev_ebit ─────────────────────────────────────────────────────────

class TestCalculateEvEbit:
    def test_correct_calculation(self):
        data = make_data({"enterprise_value": 800_000_000, "ebit": 100_000_000})
        assert calculate_ev_ebit(data) == pytest.approx(8.0)

    def test_returns_none_when_ebit_missing(self):
        assert calculate_ev_ebit(make_data({"ebit": None})) is None

    def test_returns_none_when_ev_missing(self):
        assert calculate_ev_ebit(make_data({"enterprise_value": None})) is None

    def test_returns_none_when_ebit_zero(self):
        assert calculate_ev_ebit(make_data({"ebit": 0})) is None

    def test_returns_none_when_ebit_negative(self):
        # Negative EBIT means loss-making; ratio is not meaningful
        assert calculate_ev_ebit(make_data({"ebit": -50_000_000})) is None


# ── calculate_fcf_yield ───────────────────────────────────────────────────────

class TestCalculateFcfYield:
    def test_correct_calculation(self):
        data = make_data({"free_cashflow": 90_000_000, "market_cap": 1_000_000_000})
        assert calculate_fcf_yield(data) == pytest.approx(0.09)

    def test_returns_none_when_fcf_missing(self):
        assert calculate_fcf_yield(make_data({"free_cashflow": None})) is None

    def test_returns_none_when_market_cap_missing(self):
        assert calculate_fcf_yield(make_data({"market_cap": None})) is None

    def test_returns_none_when_market_cap_zero(self):
        assert calculate_fcf_yield(make_data({"market_cap": 0})) is None

    def test_negative_fcf_yields_negative_result(self):
        """Negative FCF is valid input; caller decides if it passes filters."""
        data = make_data({"free_cashflow": -10_000_000, "market_cap": 1_000_000_000})
        assert calculate_fcf_yield(data) == pytest.approx(-0.01)


# ── calculate_price_tangible_book ─────────────────────────────────────────────

class TestCalculatePriceTangibleBook:
    def test_correct_calculation(self):
        data = make_data({"price": 10.0, "tangible_book_value": 10.0})
        assert calculate_price_tangible_book(data) == pytest.approx(1.0)

    def test_returns_none_when_price_missing(self):
        assert calculate_price_tangible_book(make_data({"price": None})) is None

    def test_returns_none_when_book_missing(self):
        assert calculate_price_tangible_book(make_data({"tangible_book_value": None})) is None

    def test_returns_none_when_book_zero(self):
        assert calculate_price_tangible_book(make_data({"tangible_book_value": 0})) is None

    def test_high_ratio_for_growth_stock(self):
        data = make_data({"price": 50.0, "tangible_book_value": 5.0})
        assert calculate_price_tangible_book(data) == pytest.approx(10.0)


# ── calculate_net_debt_ebitda ─────────────────────────────────────────────────

class TestCalculateNetDebtEbitda:
    def test_correct_calculation(self):
        data = make_data({"total_debt": 400_000_000, "cash": 100_000_000, "ebitda": 150_000_000})
        assert calculate_net_debt_ebitda(data) == pytest.approx(2.0)

    def test_returns_none_when_ebitda_missing(self):
        assert calculate_net_debt_ebitda(make_data({"ebitda": None})) is None

    def test_returns_none_when_ebitda_zero(self):
        assert calculate_net_debt_ebitda(make_data({"ebitda": 0})) is None

    def test_net_cash_position_gives_negative_ratio(self):
        data = make_data({"total_debt": 0, "cash": 200_000_000, "ebitda": 100_000_000})
        assert calculate_net_debt_ebitda(data) < 0

    def test_missing_debt_treated_as_zero(self):
        data = make_data({"total_debt": None, "cash": 0, "ebitda": 100_000_000})
        assert calculate_net_debt_ebitda(data) == pytest.approx(0.0)


# ── passes_klarman_filters ────────────────────────────────────────────────────

class TestPassesKlarmanFilters:
    def test_passing_candidate(self):
        data = make_data()
        assert passes_klarman_filters(data, ev_ebit=8.0, fcf_yield=0.09, ptb=1.0) is True

    def test_fails_revenue_too_small(self):
        data = make_data({"total_revenue": 50_000_000})  # below $100M threshold
        assert passes_klarman_filters(data, ev_ebit=8.0, fcf_yield=0.09, ptb=1.0) is False

    def test_fails_ev_ebit_too_high(self):
        data = make_data()
        assert passes_klarman_filters(data, ev_ebit=15.0, fcf_yield=0.09, ptb=1.0) is False

    def test_fails_ev_ebit_none(self):
        assert passes_klarman_filters(make_data(), ev_ebit=None, fcf_yield=0.09, ptb=1.0) is False

    def test_fails_fcf_yield_too_low(self):
        data = make_data()
        assert passes_klarman_filters(data, ev_ebit=8.0, fcf_yield=0.04, ptb=1.0) is False

    def test_fails_fcf_yield_none(self):
        assert passes_klarman_filters(make_data(), ev_ebit=8.0, fcf_yield=None, ptb=1.0) is False

    def test_fails_ptb_too_high(self):
        data = make_data()
        assert passes_klarman_filters(data, ev_ebit=8.0, fcf_yield=0.09, ptb=2.5) is False

    def test_fails_ptb_none(self):
        assert passes_klarman_filters(make_data(), ev_ebit=8.0, fcf_yield=0.09, ptb=None) is False

    def test_borderline_ev_ebit_exactly_at_threshold(self):
        """Exactly at threshold (10.0) should pass."""
        assert passes_klarman_filters(make_data(), ev_ebit=10.0, fcf_yield=0.09, ptb=1.0) is True

    def test_borderline_fcf_yield_exactly_at_threshold(self):
        """Exactly at 7% should pass."""
        assert passes_klarman_filters(make_data(), ev_ebit=8.0, fcf_yield=0.07, ptb=1.0) is True

    def test_borderline_ptb_exactly_at_threshold(self):
        """Exactly at 1.2 should pass."""
        assert passes_klarman_filters(make_data(), ev_ebit=8.0, fcf_yield=0.09, ptb=1.2) is True


# ── score_candidate ───────────────────────────────────────────────────────────

class TestScoreCandidate:
    def test_returns_positive_score(self):
        assert score_candidate(ev_ebit=8.0, fcf_yield=0.09, ptb=1.0) > 0

    def test_lower_ev_ebit_gives_higher_score(self):
        s_low = score_candidate(ev_ebit=4.0, fcf_yield=0.09, ptb=1.0)
        s_high = score_candidate(ev_ebit=9.0, fcf_yield=0.09, ptb=1.0)
        assert s_low > s_high

    def test_higher_fcf_yield_gives_higher_score(self):
        s_low = score_candidate(ev_ebit=8.0, fcf_yield=0.07, ptb=1.0)
        s_high = score_candidate(ev_ebit=8.0, fcf_yield=0.15, ptb=1.0)
        assert s_high > s_low

    def test_lower_ptb_gives_higher_score(self):
        s_low = score_candidate(ev_ebit=8.0, fcf_yield=0.09, ptb=0.5)
        s_high = score_candidate(ev_ebit=8.0, fcf_yield=0.09, ptb=1.2)
        assert s_low > s_high


# ── run_klarman_screen (full pipeline) ────────────────────────────────────────

# Realistic mock fundamentals for 8 well-known tickers.
# Only DEEPV and VALUE are constructed to pass all Klarman filters.
MOCK_UNIVERSE = {
    "AAPL": make_data({
        "ticker": "AAPL", "name": "Apple Inc.",
        "enterprise_value": 3_000_000_000_000,
        "ebit": 120_000_000_000,        # EV/EBIT ≈ 25  → FAILS ev_ebit filter
        "free_cashflow": 100_000_000_000,
        "market_cap": 3_000_000_000_000,
        "total_revenue": 380_000_000_000,
        "price": 195.0, "tangible_book_value": 3.5,  # P/TBV ≈ 55 → FAILS ptb filter
        "sector": "Technology",
    }),
    "MSFT": make_data({
        "ticker": "MSFT", "name": "Microsoft Corp.",
        "enterprise_value": 3_100_000_000_000,
        "ebit": 88_000_000_000,         # EV/EBIT ≈ 35 → FAILS
        "free_cashflow": 75_000_000_000,
        "market_cap": 3_000_000_000_000,
        "total_revenue": 230_000_000_000,
        "price": 400.0, "tangible_book_value": 25.0,
        "sector": "Technology",
    }),
    "KO": make_data({
        "ticker": "KO", "name": "Coca-Cola Co.",
        "enterprise_value": 280_000_000_000,
        "ebit": 11_000_000_000,         # EV/EBIT ≈ 25 → FAILS
        "free_cashflow": 9_500_000_000,
        "market_cap": 240_000_000_000,
        "total_revenue": 45_000_000_000,
        "price": 55.0, "tangible_book_value": -2.0,  # negative TBV → FAILS ptb
        "sector": "Consumer Staples",
    }),
    "JNJ": make_data({
        "ticker": "JNJ", "name": "Johnson & Johnson",
        "enterprise_value": 380_000_000_000,
        "ebit": 16_000_000_000,         # EV/EBIT ≈ 23 → FAILS
        "free_cashflow": 14_000_000_000,
        "market_cap": 370_000_000_000,
        "total_revenue": 85_000_000_000,
        "price": 160.0, "tangible_book_value": 20.0,
        "sector": "Healthcare",
    }),
    "XOM": make_data({
        "ticker": "XOM", "name": "ExxonMobil Corp.",
        "enterprise_value": 500_000_000_000,
        "ebit": 36_000_000_000,         # EV/EBIT ≈ 14 → FAILS
        "free_cashflow": 30_000_000_000,
        "market_cap": 470_000_000_000,
        "total_revenue": 400_000_000_000,
        "price": 110.0, "tangible_book_value": 55.0,
        "sector": "Energy",
    }),
    "WFC": make_data({
        "ticker": "WFC", "name": "Wells Fargo",
        "enterprise_value": None,       # No EV for banks → ev_ebit = None → FAILS
        "ebit": None,
        "free_cashflow": 20_000_000_000,
        "market_cap": 180_000_000_000,
        "total_revenue": 80_000_000_000,
        "price": 48.0, "tangible_book_value": 42.0,
        "sector": "Financials",
    }),
    # --- Synthetic passing candidates ---
    "DEEPV": make_data({
        "ticker": "DEEPV", "name": "Deep Value Co.",
        "enterprise_value": 500_000_000,
        "ebit": 100_000_000,            # EV/EBIT = 5.0 ✓
        "free_cashflow": 90_000_000,    # FCF yield = 9% ✓
        "market_cap": 1_000_000_000,
        "total_revenue": 500_000_000,
        "price": 10.0, "tangible_book_value": 10.0,  # P/TBV = 1.0 ✓
        "sector": "Industrials",
    }),
    "VALUE": make_data({
        "ticker": "VALUE", "name": "Value Holdings Ltd.",
        "enterprise_value": 600_000_000,
        "ebit": 100_000_000,            # EV/EBIT = 6.0 ✓
        "free_cashflow": 80_000_000,    # FCF yield = 8% ✓
        "market_cap": 1_000_000_000,
        "total_revenue": 400_000_000,
        "price": 8.0, "tangible_book_value": 8.0,   # P/TBV = 1.0 ✓
        "sector": "Industrials",
    }),
}


def fake_get_fundamentals(ticker: str):
    return MOCK_UNIVERSE.get(ticker)


class TestRunKlarmanScreen:
    @patch("backend.screener.screen.get_fundamentals", side_effect=fake_get_fundamentals)
    def test_returns_dataframe(self, _mock):
        df = run_klarman_screen(tickers=list(MOCK_UNIVERSE.keys()), show_progress=False)
        assert isinstance(df, pd.DataFrame)

    @patch("backend.screener.screen.get_fundamentals", side_effect=fake_get_fundamentals)
    def test_only_passing_candidates_in_results(self, _mock):
        df = run_klarman_screen(tickers=list(MOCK_UNIVERSE.keys()), show_progress=False)
        assert set(df["ticker"].tolist()) == {"DEEPV", "VALUE"}

    @patch("backend.screener.screen.get_fundamentals", side_effect=fake_get_fundamentals)
    def test_sorted_by_screen_score_descending(self, _mock):
        df = run_klarman_screen(tickers=list(MOCK_UNIVERSE.keys()), show_progress=False)
        scores = df["screen_score"].tolist()
        assert scores == sorted(scores, reverse=True)

    @patch("backend.screener.screen.get_fundamentals", side_effect=fake_get_fundamentals)
    def test_best_candidate_is_first(self, _mock):
        """DEEPV has lower EV/EBIT (5 vs 6) so should rank first."""
        df = run_klarman_screen(tickers=list(MOCK_UNIVERSE.keys()), show_progress=False)
        assert df.iloc[0]["ticker"] == "DEEPV"

    @patch("backend.screener.screen.get_fundamentals", side_effect=fake_get_fundamentals)
    def test_required_columns_present(self, _mock):
        df = run_klarman_screen(tickers=list(MOCK_UNIVERSE.keys()), show_progress=False)
        required = {
            "ticker", "name", "price", "market_cap", "ev_ebit",
            "fcf_yield_pct", "price_tangible_book", "sector", "screen_score",
        }
        assert required.issubset(df.columns)

    @patch("backend.screener.screen.get_fundamentals", return_value=None)
    def test_empty_dataframe_when_no_data_available(self, _mock):
        df = run_klarman_screen(tickers=["FAKE1", "FAKE2"], show_progress=False)
        assert df.empty

    @patch("backend.screener.screen.get_fundamentals", side_effect=fake_get_fundamentals)
    def test_empty_dataframe_when_nothing_passes_filters(self, _mock):
        """Pass only tickers that we know fail filters."""
        failing = ["AAPL", "MSFT", "KO", "JNJ", "XOM", "WFC"]
        df = run_klarman_screen(tickers=failing, show_progress=False)
        assert df.empty

    @patch("backend.screener.screen.get_fundamentals", side_effect=fake_get_fundamentals)
    def test_screen_score_is_positive(self, _mock):
        df = run_klarman_screen(tickers=["DEEPV", "VALUE"], show_progress=False)
        assert (df["screen_score"] > 0).all()

    @patch("backend.screener.screen.get_fundamentals", side_effect=fake_get_fundamentals)
    def test_fcf_yield_pct_is_percentage_not_decimal(self, _mock):
        """fcf_yield_pct should be e.g. 9.0 not 0.09."""
        df = run_klarman_screen(tickers=["DEEPV"], show_progress=False)
        assert df.iloc[0]["fcf_yield_pct"] == pytest.approx(9.0, abs=0.01)

    @patch("backend.screener.screen.get_fundamentals", side_effect=fake_get_fundamentals)
    def test_index_is_reset(self, _mock):
        df = run_klarman_screen(tickers=list(MOCK_UNIVERSE.keys()), show_progress=False)
        assert list(df.index) == list(range(len(df)))

    @patch("backend.screener.screen.get_fundamentals", side_effect=fake_get_fundamentals)
    def test_single_passing_ticker(self, _mock):
        df = run_klarman_screen(tickers=["DEEPV"], show_progress=False)
        assert len(df) == 1
        assert df.iloc[0]["ticker"] == "DEEPV"

    @patch("backend.screener.screen.get_fundamentals", side_effect=fake_get_fundamentals)
    def test_aapl_msft_ko_jnj_xom_wfc_all_filtered_out(self, _mock):
        """Confirmed: none of these well-known large-caps pass Klarman's strict filters."""
        real_tickers = ["AAPL", "MSFT", "KO", "JNJ", "XOM", "WFC"]
        df = run_klarman_screen(tickers=real_tickers, show_progress=False)
        for ticker in real_tickers:
            assert ticker not in df["ticker"].values, f"{ticker} should not pass filters"
