"""Unit tests for backend/data/edgar_client.py

SEC EDGAR network calls are fully mocked so tests are fast and offline-safe.
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, call


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_statement_df(data: dict[str, float], date_col: str = "2024-09-30") -> pd.DataFrame:
    """Build a mock Statement DataFrame matching edgartools 5.x format."""
    rows = []
    for concept_suffix, value in data.items():
        rows.append({
            "concept": f"us-gaap_{concept_suffix}",
            "label": concept_suffix,
            "standard_concept": concept_suffix,
            date_col: value,
            "level": 0,
            "abstract": False,
            "dimension": False,
            "is_breakdown": False,
            "dimension_axis": None,
            "dimension_member": None,
            "dimension_member_label": None,
            "dimension_label": None,
            "balance": None,
            "weight": None,
            "preferred_sign": None,
            "parent_concept": None,
            "parent_abstract_concept": None,
        })
    return pd.DataFrame(rows)


def make_mock_filing(
    rev: float = 500_000_000,
    ni: float = 50_000_000,
    cfo: float = 70_000_000,
    capex: float = 20_000_000,
    total_assets: float = 800_000_000,
    total_liabilities: float = 400_000_000,
    long_term_debt: float = 200_000_000,
    current_assets: float = 300_000_000,
    current_liabilities: float = 150_000_000,
    shares_outstanding: float = 10_000_000,
    gross_profit: float = 200_000_000,
    depreciation: float = 15_000_000,
    sga: float = 80_000_000,
    receivables: float = 60_000_000,
    ppe_net: float = 250_000_000,
) -> MagicMock:
    """Construct a mock 10-K filing with financials (edgartools 5.x API)."""
    filing = MagicMock()

    inc_df = _make_statement_df({
        "Revenues": rev,
        "NetIncomeLoss": ni,
        "GrossProfit": gross_profit,
        "SellingGeneralAndAdministrativeExpense": sga,
    })

    cf_df = _make_statement_df({
        "NetCashProvidedByUsedInOperatingActivities": cfo,
        "PaymentsToAcquirePropertyPlantAndEquipment": capex,
        "DepreciationDepletionAndAmortization": depreciation,
    })

    bs_df = _make_statement_df({
        "Assets": total_assets,
        "Liabilities": total_liabilities,
        "LongTermDebtNoncurrent": long_term_debt,
        "AssetsCurrent": current_assets,
        "LiabilitiesCurrent": current_liabilities,
        "CommonStockSharesOutstanding": shares_outstanding,
        "AccountsReceivableNetCurrent": receivables,
        "PropertyPlantAndEquipmentNet": ppe_net,
    })

    income_stmt = MagicMock()
    income_stmt.to_dataframe.return_value = inc_df

    cf_stmt = MagicMock()
    cf_stmt.to_dataframe.return_value = cf_df

    bs_stmt = MagicMock()
    bs_stmt.to_dataframe.return_value = bs_df

    tenk = MagicMock()
    tenk.income_statement = income_stmt
    tenk.cash_flow_statement = cf_stmt
    tenk.balance_sheet = bs_stmt

    filing.data_object.return_value = tenk
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
        expected_keys = {
            "revenues", "net_incomes", "fcfs", "margins", "capex",
            "total_assets", "total_liabilities", "long_term_debt",
            "current_assets", "current_liabilities", "shares_outstanding_hist",
            "gross_profits", "depreciation", "sga_expenses", "receivables",
            "ppe_net", "cfo_list",
        }
        assert set(result.keys()) == expected_keys

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
    def test_returns_none_when_fewer_than_min_years(self, mock_company_cls):
        mock_company = MagicMock()
        # Only 2 usable filings — below MIN_YEARS_REQUIRED (3)
        mock_company.get_filings.return_value.head.return_value = make_10_filings()[:2]
        mock_company_cls.return_value = mock_company

        from backend.data.edgar_client import get_10yr_financials
        result = get_10yr_financials("SHORT")
        assert result is None

    @patch("backend.data.edgar_client.Company")
    def test_returns_data_with_3_years(self, mock_company_cls):
        mock_company = MagicMock()
        # 3 usable filings — exactly MIN_YEARS_REQUIRED
        mock_company.get_filings.return_value.head.return_value = make_10_filings()[:3]
        mock_company_cls.return_value = mock_company

        from backend.data.edgar_client import get_10yr_financials
        result = get_10yr_financials("THREE")
        assert result is not None
        assert len(result["revenues"]) == 3

    @patch("backend.data.edgar_client.Company")
    def test_returns_none_on_company_exception(self, mock_company_cls):
        mock_company_cls.side_effect = Exception("EDGAR unavailable")

        from backend.data.edgar_client import get_10yr_financials
        result = get_10yr_financials("ERR")
        assert result is None

    @patch("backend.data.edgar_client.Company")
    def test_skips_filing_with_missing_fields(self, mock_company_cls):
        filings = make_10_filings()
        # Make 2 filings throw on data_object() access
        for f in filings[:2]:
            f.data_object.side_effect = Exception("parse error")

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
        """FCF = CFO - |CapEx|"""
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

    @patch("backend.data.edgar_client.Company")
    def test_balance_sheet_keys_present(self, mock_company_cls):
        mock_company = MagicMock()
        mock_company.get_filings.return_value.head.return_value = make_10_filings()
        mock_company_cls.return_value = mock_company

        from backend.data.edgar_client import get_10yr_financials
        result = get_10yr_financials("AAPL")

        bs_keys = {
            "total_assets", "total_liabilities", "long_term_debt",
            "current_assets", "current_liabilities", "shares_outstanding_hist",
            "gross_profits", "depreciation", "sga_expenses", "receivables",
            "ppe_net", "cfo_list",
        }
        assert bs_keys.issubset(result.keys())

    @patch("backend.data.edgar_client.Company")
    def test_balance_sheet_lists_same_length_as_revenues(self, mock_company_cls):
        mock_company = MagicMock()
        mock_company.get_filings.return_value.head.return_value = make_10_filings()
        mock_company_cls.return_value = mock_company

        from backend.data.edgar_client import get_10yr_financials
        result = get_10yr_financials("AAPL")

        n = len(result["revenues"])
        for key in ["total_assets", "total_liabilities", "cfo_list", "gross_profits"]:
            assert len(result[key]) == n, f"{key} length {len(result[key])} != revenues length {n}"

    @patch("backend.data.edgar_client.Company")
    def test_total_assets_values_extracted(self, mock_company_cls):
        mock_company = MagicMock()
        mock_company.get_filings.return_value.head.return_value = make_10_filings()
        mock_company_cls.return_value = mock_company

        from backend.data.edgar_client import get_10yr_financials
        result = get_10yr_financials("AAPL")

        # Default make_mock_filing has total_assets=800M
        assert all(v == 800_000_000 for v in result["total_assets"])
