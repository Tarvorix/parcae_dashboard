"""Unit tests for backend/data/insider_client.py

All external calls (SEC EDGAR, yfinance) are mocked.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
import pandas as pd
from datetime import datetime, timedelta

from backend.data.insider_client import (
    _parse_form4_xml,
    get_insider_transactions,
    get_institutional_holdings,
    get_short_interest,
    get_flow_signals,
    NOTABLE_VALUE_INVESTORS,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

SAMPLE_FORM4_XML = """<?xml version="1.0"?>
<ownershipDocument>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerName>John Smith</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>0</isDirector>
      <isOfficer>1</isOfficer>
      <isTenPercentOwner>0</isTenPercentOwner>
      <officerTitle>CEO</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2025-06-15</value></transactionDate>
      <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>10000</value></transactionShares>
        <transactionPricePerShare><value>50.00</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </nonDerivativeTransaction>
    <nonDerivativeTransaction>
      <transactionDate><value>2025-06-20</value></transactionDate>
      <transactionCoding><transactionCode>S</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>5000</value></transactionShares>
        <transactionPricePerShare><value>55.00</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>"""

SAMPLE_FORM4_BUY_ONLY = """<?xml version="1.0"?>
<ownershipDocument>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerName>{name}</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>1</isDirector>
      <isOfficer>0</isOfficer>
      <isTenPercentOwner>0</isTenPercentOwner>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>{date}</value></transactionDate>
      <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>1000</value></transactionShares>
        <transactionPricePerShare><value>25.00</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>"""


def make_mock_filing(xml_text: str):
    """Create a mock filing that returns the given XML from .text()."""
    filing = MagicMock()
    filing.text.return_value = xml_text
    return filing


def make_institutional_df(holders: list[dict]) -> pd.DataFrame:
    """Build a DataFrame that mimics yfinance institutional_holders."""
    return pd.DataFrame(holders)


# ── _parse_form4_xml Tests ───────────────────────────────────────────────────

class TestParseForm4Xml:
    def test_parses_buy_transaction(self):
        txns = _parse_form4_xml(SAMPLE_FORM4_XML)
        buys = [t for t in txns if t["transaction_type"] == "Buy"]
        assert len(buys) == 1
        assert buys[0]["shares"] == 10000
        assert buys[0]["price"] == 50.0
        assert buys[0]["value"] == 500000.0

    def test_parses_sell_transaction(self):
        txns = _parse_form4_xml(SAMPLE_FORM4_XML)
        sells = [t for t in txns if t["transaction_type"] == "Sell"]
        assert len(sells) == 1
        assert sells[0]["shares"] == 5000
        assert sells[0]["price"] == 55.0

    def test_extracts_owner_name(self):
        txns = _parse_form4_xml(SAMPLE_FORM4_XML)
        assert all(t["owner"] == "John Smith" for t in txns)

    def test_extracts_officer_info(self):
        txns = _parse_form4_xml(SAMPLE_FORM4_XML)
        assert all(t["is_officer"] is True for t in txns)
        assert all(t["officer_title"] == "CEO" for t in txns)

    def test_extracts_date(self):
        txns = _parse_form4_xml(SAMPLE_FORM4_XML)
        assert txns[0]["date"] == "2025-06-15"

    def test_returns_empty_on_invalid_xml(self):
        assert _parse_form4_xml("not xml at all") == []

    def test_returns_empty_on_empty_string(self):
        assert _parse_form4_xml("") == []

    def test_ignores_non_market_transactions(self):
        # Award (code A) should be ignored — only P and S are tracked
        xml = """<?xml version="1.0"?>
<ownershipDocument>
  <reportingOwner>
    <reportingOwnerId><rptOwnerName>Test</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship><isOfficer>1</isOfficer></reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2025-01-01</value></transactionDate>
      <transactionCoding><transactionCode>A</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>5000</value></transactionShares>
        <transactionPricePerShare><value>0.00</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>"""
        assert len(_parse_form4_xml(xml)) == 0

    def test_detects_director(self):
        xml = SAMPLE_FORM4_BUY_ONLY.format(name="Director Bob", date="2025-01-01")
        txns = _parse_form4_xml(xml)
        assert txns[0]["is_director"] is True

    def test_detects_ten_pct_owner(self):
        xml = """<?xml version="1.0"?>
<ownershipDocument>
  <reportingOwner>
    <reportingOwnerId><rptOwnerName>Big Owner</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship>
      <isTenPercentOwner>1</isTenPercentOwner>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2025-01-01</value></transactionDate>
      <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>100000</value></transactionShares>
        <transactionPricePerShare><value>10.00</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>"""
        txns = _parse_form4_xml(xml)
        assert txns[0]["is_ten_pct_owner"] is True


# ── get_insider_transactions Tests ───────────────────────────────────────────

class TestGetInsiderTransactions:
    @patch("backend.data.insider_client.Company")
    def test_returns_dict_with_required_keys(self, MockCompany):
        mock_company = MagicMock()
        MockCompany.return_value = mock_company
        mock_filings = MagicMock()
        mock_filings.__len__ = lambda self: 1
        mock_filings.__iter__ = lambda self: iter([make_mock_filing(SAMPLE_FORM4_XML)])
        mock_filings.head.return_value = [make_mock_filing(SAMPLE_FORM4_XML)]
        mock_company.get_filings.return_value = mock_filings

        result = get_insider_transactions("TEST")
        assert result is not None
        assert "transactions" in result
        assert "summary" in result
        assert {"total_bought", "total_sold", "net_buying", "n_buyers", "n_sellers",
                "n_transactions", "cluster_buy_detected", "cluster_buy_count"} == set(result["summary"].keys())

    @patch("backend.data.insider_client.Company")
    def test_summary_computation(self, MockCompany):
        mock_company = MagicMock()
        MockCompany.return_value = mock_company
        mock_filings = MagicMock()
        mock_filings.__len__ = lambda self: 1
        mock_filings.__iter__ = lambda self: iter([make_mock_filing(SAMPLE_FORM4_XML)])
        mock_filings.head.return_value = [make_mock_filing(SAMPLE_FORM4_XML)]
        mock_company.get_filings.return_value = mock_filings

        result = get_insider_transactions("TEST")
        summary = result["summary"]
        assert summary["total_bought"] == 500000.0  # 10000 * 50
        assert summary["total_sold"] == 275000.0    # 5000 * 55
        assert summary["net_buying"] == 225000.0
        assert summary["n_buyers"] == 1
        assert summary["n_sellers"] == 1

    @patch("backend.data.insider_client.Company")
    def test_cluster_buy_detection(self, MockCompany):
        """3+ unique insiders buying within 90 days triggers cluster detection."""
        mock_company = MagicMock()
        MockCompany.return_value = mock_company

        # Create 4 different insiders buying within 30 days
        filings = []
        for i, name in enumerate(["Alice CEO", "Bob CFO", "Carol Director", "Dave VP"]):
            date = f"2025-06-{10 + i:02d}"
            xml = SAMPLE_FORM4_BUY_ONLY.format(name=name, date=date)
            filings.append(make_mock_filing(xml))

        mock_filings = MagicMock()
        mock_filings.__len__ = lambda self: 4
        mock_filings.__iter__ = lambda self: iter(filings)
        mock_filings.head.return_value = filings
        mock_company.get_filings.return_value = mock_filings

        result = get_insider_transactions("TEST")
        assert result["summary"]["cluster_buy_detected"] is True
        assert result["summary"]["cluster_buy_count"] >= 3

    @patch("backend.data.insider_client.Company")
    def test_no_cluster_with_single_buyer(self, MockCompany):
        mock_company = MagicMock()
        MockCompany.return_value = mock_company

        xml = SAMPLE_FORM4_BUY_ONLY.format(name="Same Person", date="2025-06-01")
        filings = [make_mock_filing(xml)] * 5  # Same person 5 times

        mock_filings = MagicMock()
        mock_filings.__len__ = lambda self: 5
        mock_filings.__iter__ = lambda self: iter(filings)
        mock_filings.head.return_value = filings
        mock_company.get_filings.return_value = mock_filings

        result = get_insider_transactions("TEST")
        assert result["summary"]["cluster_buy_detected"] is False

    @patch("backend.data.insider_client.Company")
    def test_returns_none_on_no_filings(self, MockCompany):
        mock_company = MagicMock()
        MockCompany.return_value = mock_company
        mock_filings = MagicMock()
        mock_filings.__len__ = lambda self: 0
        mock_company.get_filings.return_value = mock_filings

        assert get_insider_transactions("TEST") is None

    @patch("backend.data.insider_client.Company")
    def test_returns_none_on_exception(self, MockCompany):
        MockCompany.side_effect = Exception("API error")
        assert get_insider_transactions("FAIL") is None


# ── get_institutional_holdings Tests ─────────────────────────────────────────

class TestGetInstitutionalHoldings:
    @patch("backend.data.insider_client.yf.Ticker")
    def test_returns_dict_with_required_keys(self, MockTicker):
        mock_stock = MagicMock()
        MockTicker.return_value = mock_stock
        mock_stock.institutional_holders = make_institutional_df([
            {"Holder": "Vanguard Group", "Shares": 5000000, "% Out": 0.05, "Value": 250000000},
        ])

        result = get_institutional_holdings("TEST")
        assert result is not None
        assert {"notable_holders", "n_notable_holders", "top_holders"} == set(result.keys())

    @patch("backend.data.insider_client.yf.Ticker")
    def test_detects_notable_value_investor(self, MockTicker):
        mock_stock = MagicMock()
        MockTicker.return_value = mock_stock
        mock_stock.institutional_holders = make_institutional_df([
            {"Holder": "Baupost Group LLC", "Shares": 2000000, "% Out": 0.03, "Value": 100000000},
            {"Holder": "Vanguard Group", "Shares": 5000000, "% Out": 0.05, "Value": 250000000},
        ])

        result = get_institutional_holdings("TEST")
        assert result["n_notable_holders"] == 1
        assert result["notable_holders"][0]["name"] == "Baupost Group LLC"

    @patch("backend.data.insider_client.yf.Ticker")
    def test_detects_berkshire(self, MockTicker):
        mock_stock = MagicMock()
        MockTicker.return_value = mock_stock
        mock_stock.institutional_holders = make_institutional_df([
            {"Holder": "Berkshire Hathaway Inc", "Shares": 10000000, "% Out": 0.10, "Value": 500000000},
        ])

        result = get_institutional_holdings("TEST")
        assert result["n_notable_holders"] == 1

    @patch("backend.data.insider_client.yf.Ticker")
    def test_empty_dataframe(self, MockTicker):
        mock_stock = MagicMock()
        MockTicker.return_value = mock_stock
        mock_stock.institutional_holders = pd.DataFrame()

        result = get_institutional_holdings("TEST")
        assert result is not None
        assert result["n_notable_holders"] == 0
        assert result["top_holders"] == []

    @patch("backend.data.insider_client.yf.Ticker")
    def test_none_dataframe(self, MockTicker):
        mock_stock = MagicMock()
        MockTicker.return_value = mock_stock
        mock_stock.institutional_holders = None

        result = get_institutional_holdings("TEST")
        assert result is not None
        assert result["n_notable_holders"] == 0

    @patch("backend.data.insider_client.yf.Ticker")
    def test_top_holders_limited_to_10(self, MockTicker):
        mock_stock = MagicMock()
        MockTicker.return_value = mock_stock
        holders = [{"Holder": f"Fund {i}", "Shares": 1000, "% Out": 0.01, "Value": 50000}
                   for i in range(15)]
        mock_stock.institutional_holders = make_institutional_df(holders)

        result = get_institutional_holdings("TEST")
        assert len(result["top_holders"]) == 10

    @patch("backend.data.insider_client.yf.Ticker")
    def test_returns_none_on_exception(self, MockTicker):
        MockTicker.side_effect = Exception("API error")
        assert get_institutional_holdings("FAIL") is None


# ── get_short_interest Tests ─────────────────────────────────────────────────

class TestGetShortInterest:
    def test_returns_required_keys(self):
        result = get_short_interest({"short_percent_of_float": 0.05, "short_ratio": 3.2})
        assert {"short_percent_of_float", "short_ratio", "short_interest_high"} == set(result.keys())

    def test_high_short_interest_flag(self):
        result = get_short_interest({"short_percent_of_float": 0.15, "short_ratio": 5.0})
        assert result["short_interest_high"] is True

    def test_normal_short_interest_flag(self):
        result = get_short_interest({"short_percent_of_float": 0.03, "short_ratio": 2.0})
        assert result["short_interest_high"] is False

    def test_missing_short_data(self):
        result = get_short_interest({})
        assert result["short_percent_of_float"] is None
        assert result["short_ratio"] is None
        assert result["short_interest_high"] is False

    def test_none_short_pct_not_flagged(self):
        result = get_short_interest({"short_percent_of_float": None})
        assert result["short_interest_high"] is False

    def test_exactly_10_pct_not_flagged(self):
        # Threshold is > 10%, not >= 10%
        result = get_short_interest({"short_percent_of_float": 0.10})
        assert result["short_interest_high"] is False


# ── get_flow_signals Tests ───────────────────────────────────────────────────

class TestGetFlowSignals:
    @patch("backend.data.insider_client.get_institutional_holdings", return_value={"notable_holders": [], "n_notable_holders": 0, "top_holders": []})
    @patch("backend.data.insider_client.get_insider_transactions", return_value=None)
    def test_returns_dict_with_required_keys(self, _insider, _inst):
        result = get_flow_signals("TEST", {"short_percent_of_float": 0.05, "short_ratio": 3.0})
        assert {"insider", "institutional", "short_interest"} == set(result.keys())

    @patch("backend.data.insider_client.get_institutional_holdings", return_value=None)
    @patch("backend.data.insider_client.get_insider_transactions", return_value=None)
    def test_insider_none_propagates(self, _insider, _inst):
        result = get_flow_signals("TEST", {})
        assert result["insider"] is None

    @patch("backend.data.insider_client.get_institutional_holdings", return_value=None)
    @patch("backend.data.insider_client.get_insider_transactions", return_value=None)
    def test_institutional_none_propagates(self, _insider, _inst):
        result = get_flow_signals("TEST", {})
        assert result["institutional"] is None

    @patch("backend.data.insider_client.get_institutional_holdings", return_value=None)
    @patch("backend.data.insider_client.get_insider_transactions", return_value=None)
    def test_short_interest_always_present(self, _insider, _inst):
        result = get_flow_signals("TEST", {"short_percent_of_float": 0.20})
        assert result["short_interest"] is not None
        assert result["short_interest"]["short_interest_high"] is True
