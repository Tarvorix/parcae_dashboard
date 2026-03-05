"""Unit tests for backend/data/yfinance_client.py

Network calls are mocked so these tests are fast and offline-safe.
"""

import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from backend.data.yfinance_client import (
    get_fundamentals,
    get_price_history,
    get_dividend_history,
    get_sp500_tickers,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_mock_info(overrides: dict | None = None) -> dict:
    info = {
        "longName": "Test Corp",
        "currentPrice": 100.0,
        "marketCap": 1_000_000_000,
        "enterpriseValue": 1_100_000_000,
        "ebit": 120_000_000,
        "ebitda": 150_000_000,
        "freeCashflow": 90_000_000,
        "totalRevenue": 500_000_000,
        "bookValue": 20.0,
        "sharesOutstanding": 10_000_000,
        "totalDebt": 200_000_000,
        "totalCash": 50_000_000,
        "trailingPE": 12.0,
        "priceToBook": 5.0,
        "currentRatio": 1.8,
        "sector": "Technology",
        "industry": "Software",
    }
    if overrides:
        info.update(overrides)
    return info


# ── get_fundamentals ──────────────────────────────────────────────────────────

class TestGetFundamentals:
    @patch("backend.data.yfinance_client.yf.Ticker")
    def test_returns_dict_on_valid_data(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.info = make_mock_info()
        mock_ticker_cls.return_value = mock_ticker

        result = get_fundamentals("TEST")
        assert result is not None
        assert isinstance(result, dict)

    @patch("backend.data.yfinance_client.yf.Ticker")
    def test_ticker_field_correct(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.info = make_mock_info()
        mock_ticker_cls.return_value = mock_ticker

        result = get_fundamentals("AAPL")
        assert result["ticker"] == "AAPL"

    @patch("backend.data.yfinance_client.yf.Ticker")
    def test_returns_none_when_price_missing(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.info = make_mock_info({"currentPrice": None, "regularMarketPrice": None})
        mock_ticker_cls.return_value = mock_ticker

        result = get_fundamentals("MISS")
        assert result is None

    @patch("backend.data.yfinance_client.yf.Ticker")
    def test_returns_none_when_revenue_missing(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.info = make_mock_info({"totalRevenue": None})
        mock_ticker_cls.return_value = mock_ticker

        result = get_fundamentals("MISS")
        assert result is None

    @patch("backend.data.yfinance_client.yf.Ticker")
    def test_returns_none_on_exception(self, mock_ticker_cls):
        mock_ticker_cls.side_effect = Exception("Network error")
        result = get_fundamentals("ERR")
        assert result is None

    @patch("backend.data.yfinance_client.yf.Ticker")
    def test_all_expected_keys_present(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.info = make_mock_info()
        mock_ticker_cls.return_value = mock_ticker

        result = get_fundamentals("TEST")
        expected_keys = {
            "ticker", "name", "price", "market_cap", "enterprise_value",
            "ebit", "ebitda", "free_cashflow", "total_revenue",
            "tangible_book_value", "shares_outstanding", "total_debt",
            "cash", "pe_ratio", "pb_ratio", "current_ratio",
            "sector", "industry",
        }
        assert expected_keys.issubset(result.keys())

    @patch("backend.data.yfinance_client.yf.Ticker")
    def test_uses_regular_market_price_fallback(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.info = make_mock_info({"currentPrice": None, "regularMarketPrice": 88.0})
        mock_ticker_cls.return_value = mock_ticker

        result = get_fundamentals("TEST")
        assert result is not None
        assert result["price"] == 88.0


# ── get_price_history ─────────────────────────────────────────────────────────

class TestGetPriceHistory:
    @patch("backend.data.yfinance_client.yf.Ticker")
    def test_returns_dataframe(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {"Close": [100.0, 105.0, 110.0]},
            index=pd.date_range("2023-01-01", periods=3, freq="ME"),
        )
        mock_ticker_cls.return_value = mock_ticker

        result = get_price_history("TEST")
        assert isinstance(result, pd.DataFrame)
        assert "price" in result.columns

    @patch("backend.data.yfinance_client.yf.Ticker")
    def test_correct_period_passed(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame(
            {"Close": [100.0]},
            index=pd.date_range("2023-01-01", periods=1, freq="ME"),
        )
        mock_ticker_cls.return_value = mock_ticker

        get_price_history("TEST", years=5)
        mock_ticker.history.assert_called_once_with(period="5y", interval="1mo")


# ── get_dividend_history ──────────────────────────────────────────────────────

class TestGetDividendHistory:
    @patch("backend.data.yfinance_client.yf.Ticker")
    def test_returns_series(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.dividends = pd.Series(
            [0.5, 0.5, 0.6],
            index=pd.date_range("2022-01-01", periods=3, freq="QE"),
        )
        mock_ticker_cls.return_value = mock_ticker

        result = get_dividend_history("TEST")
        assert isinstance(result, pd.Series)


# ── get_sp500_tickers ─────────────────────────────────────────────────────────

class TestGetSp500Tickers:
    @patch("backend.data.yfinance_client.pd.read_html")
    def test_returns_list_of_strings(self, mock_read_html):
        df = pd.DataFrame({"Symbol": ["AAPL", "MSFT", "BRK.B", "BF.B"]})
        mock_read_html.return_value = [df]

        result = get_sp500_tickers()
        assert isinstance(result, list)
        assert all(isinstance(t, str) for t in result)

    @patch("backend.data.yfinance_client.pd.read_html")
    def test_dots_replaced_with_dashes(self, mock_read_html):
        df = pd.DataFrame({"Symbol": ["BRK.B", "BF.B"]})
        mock_read_html.return_value = [df]

        result = get_sp500_tickers()
        assert "BRK-B" in result
        assert "BF-B" in result

    @patch("backend.data.yfinance_client.pd.read_html")
    def test_correct_count(self, mock_read_html):
        symbols = [f"SYM{i}" for i in range(503)]
        df = pd.DataFrame({"Symbol": symbols})
        mock_read_html.return_value = [df]

        result = get_sp500_tickers()
        assert len(result) == 503
