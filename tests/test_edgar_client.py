"""Unit tests for backend/data/edgar_client.py

SEC EDGAR network calls are fully mocked so tests are fast and offline-safe.
"""

import pytest
from unittest.mock import MagicMock, patch, call


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_mock_filing(
    rev: float = 500_000_000,
    ni: float = 50_000_000,
    cfo: float = 70_000_000,
    capex: float = 20_000_000,
) -> MagicMock:
    """Construct a mock 10-K filing with financials."""
    filing = MagicMock()
    income = MagicMock()
    cashflow = MagicMock()

    income.get.side_effect = lambda key: {
        "Revenues": rev,
        "RevenueFromContractWithCustomerExcludingAssessedTax": None,
        "NetIncomeLoss": ni,
    }.get(key)

    cashflow.get.side_effect = lambda key: {
        "NetCashProvidedByUsedInOperatingActivities": cfo,
        "PaymentsToAcquirePropertyPlantAndEquipment": capex,
    }.get(key)

    filing.financials.income_statement = income
    filing.financials.cash_flow_statement = cashflow
    return filing


def make_10_filings() -> list[MagicMock]:
    # EDGAR returns filings newest-first (index 0 = most recent).
    # Use (9 - i) so that index 0 has the highest revenue and index 9 the lowest.
    return [
        make_mock_filing(
            rev=500_000_000 + (9 - i) * 25_000_000,
            ni=50_000_000 + (9 - i) * 2_000_000,
            cfo=70_000_000 + (9 - i) * 3_000_000,
            capex=20_000_000 + (9 - i) * 500_000,
        )
        for i in range(10)
    ]


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestGet10YrFinancials:
    @patch("backend.data.edgar_client.Company")
    def test_returns_dict_with_required_keys(self, mock_company_cls):
        mock_company = MagicMock()
        mock_company.get_filings.return_value.head.return_value = make_10_filings()
        mock_company_cls.return_value = mock_company

        from backend.data.edgar_client import get_10yr_financials
        result = get_10yr_financials("AAPL")

        assert result is not None
        assert set(result.keys()) == {"revenues", "net_incomes", "fcfs", "margins", "capex"}

    @patch("backend.data.edgar_client.Company")
    def test_all_lists_same_length(self, mock_company_cls):
        mock_company = MagicMock()
        mock_company.get_filings.return_value.head.return_value = make_10_filings()
        mock_company_cls.return_value = mock_company

        from backend.data.edgar_client import get_10yr_financials
        result = get_10yr_financials("AAPL")

        lengths = {k: len(v) for k, v in result.items()}
        unique_lengths = set(lengths.values())
        assert len(unique_lengths) == 1, f"Lists have different lengths: {lengths}"

    @patch("backend.data.edgar_client.Company")
    def test_returns_none_when_fewer_than_5_years(self, mock_company_cls):
        mock_company = MagicMock()
        # Only 3 usable filings
        mock_company.get_filings.return_value.head.return_value = make_10_filings()[:3]
        mock_company_cls.return_value = mock_company

        from backend.data.edgar_client import get_10yr_financials
        result = get_10yr_financials("SHORT")
        assert result is None

    @patch("backend.data.edgar_client.Company")
    def test_returns_none_on_company_exception(self, mock_company_cls):
        mock_company_cls.side_effect = Exception("EDGAR unavailable")

        from backend.data.edgar_client import get_10yr_financials
        result = get_10yr_financials("ERR")
        assert result is None

    @patch("backend.data.edgar_client.Company")
    def test_skips_filing_with_missing_fields(self, mock_company_cls):
        filings = make_10_filings()
        # Make 2 filings throw on financial access
        for f in filings[:2]:
            f.financials.income_statement.get.side_effect = Exception("parse error")

        mock_company = MagicMock()
        mock_company.get_filings.return_value.head.return_value = filings
        mock_company_cls.return_value = mock_company

        from backend.data.edgar_client import get_10yr_financials
        result = get_10yr_financials("PARTIAL")
        # 8 valid filings should still be enough
        assert result is not None
        assert len(result["revenues"]) == 8

    @patch("backend.data.edgar_client.Company")
    def test_fcf_calculated_correctly(self, mock_company_cls):
        """FCF = CFO − |CapEx|"""
        filing = make_mock_filing(cfo=80_000_000, capex=30_000_000)
        filings = [filing] * 7  # enough to pass 5-year threshold

        mock_company = MagicMock()
        mock_company.get_filings.return_value.head.return_value = filings
        mock_company_cls.return_value = mock_company

        from backend.data.edgar_client import get_10yr_financials
        result = get_10yr_financials("FCF")
        expected_fcf = 80_000_000 - 30_000_000
        assert all(abs(v - expected_fcf) < 1 for v in result["fcfs"])

    @patch("backend.data.edgar_client.Company")
    def test_margins_within_zero_one(self, mock_company_cls):
        mock_company = MagicMock()
        mock_company.get_filings.return_value.head.return_value = make_10_filings()
        mock_company_cls.return_value = mock_company

        from backend.data.edgar_client import get_10yr_financials
        result = get_10yr_financials("AAPL")
        for m in result["margins"]:
            assert 0.0 <= m <= 1.0, f"Margin out of range: {m}"

    @patch("backend.data.edgar_client.Company")
    def test_data_in_chronological_order(self, mock_company_cls):
        """Revenues should be oldest-first (ascending for a growing company)."""
        mock_company = MagicMock()
        mock_company.get_filings.return_value.head.return_value = make_10_filings()
        mock_company_cls.return_value = mock_company

        from backend.data.edgar_client import get_10yr_financials
        result = get_10yr_financials("AAPL")
        revs = result["revenues"]
        # Our synthetic data has increasing revenues; reversed list should be ascending
        assert revs == sorted(revs), "Expected chronological (ascending) order"
