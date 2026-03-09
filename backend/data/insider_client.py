"""
Insider & Institutional Flow Signals

Fetches:
  1. SEC Form 4 insider transactions (via edgartools)
  2. Institutional holders (via yfinance)
  3. Short interest (from yfinance fundamentals)

Returns composite flow signal dict for a ticker.
"""

from datetime import datetime, timedelta
from typing import Optional
import xml.etree.ElementTree as ET

import yfinance as yf
from edgar import Company

from backend.config import SEC_IDENTITY


# ── Notable value investor firms ─────────────────────────────────────────────

NOTABLE_VALUE_INVESTORS = [
    "baupost",
    "berkshire hathaway",
    "greenlight capital",
    "third point",
    "pershing square",
    "appaloosa",
    "oaktree",
    "fairholme",
    "gotham asset",
    "tweedy browne",
    "southeastern asset",
    "dodge & cox",
    "first eagle",
    "brandes investment",
    "pzena investment",
]


# ── Form 4 Insider Transactions ──────────────────────────────────────────────

def _parse_form4_xml(xml_text: str) -> list[dict]:
    """
    Parse SEC Form 4 XML to extract transaction details.
    Returns list of transaction dicts.
    """
    transactions = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return transactions

    # Get reporting owner name
    owner_name = ""
    owner_elem = root.find(".//reportingOwner/reportingOwnerId/rptOwnerName")
    if owner_elem is not None and owner_elem.text:
        owner_name = owner_elem.text.strip()

    # Get owner relationship
    is_director = False
    is_officer = False
    is_ten_pct = False
    rel_elem = root.find(".//reportingOwner/reportingOwnerRelationship")
    if rel_elem is not None:
        d = rel_elem.find("isDirector")
        if d is not None and d.text and d.text.strip() in ("1", "true"):
            is_director = True
        o = rel_elem.find("isOfficer")
        if o is not None and o.text and o.text.strip() in ("1", "true"):
            is_officer = True
        t = rel_elem.find("isTenPercentOwner")
        if t is not None and t.text and t.text.strip() in ("1", "true"):
            is_ten_pct = True

    officer_title = ""
    title_elem = root.find(".//reportingOwner/reportingOwnerRelationship/officerTitle")
    if title_elem is not None and title_elem.text:
        officer_title = title_elem.text.strip()

    # Parse non-derivative transactions
    for txn in root.findall(".//nonDerivativeTable/nonDerivativeTransaction"):
        try:
            shares_elem = txn.find(".//transactionAmounts/transactionShares/value")
            price_elem = txn.find(".//transactionAmounts/transactionPricePerShare/value")
            code_elem = txn.find(".//transactionCoding/transactionCode")
            date_elem = txn.find(".//transactionDate/value")

            shares = float(shares_elem.text) if shares_elem is not None and shares_elem.text else 0
            price = float(price_elem.text) if price_elem is not None and price_elem.text else 0
            code = code_elem.text.strip() if code_elem is not None and code_elem.text else ""
            date_str = date_elem.text.strip() if date_elem is not None and date_elem.text else ""

            # Determine buy vs sell
            # P = open market purchase, S = open market sale
            # A = grant/award, M = exercise, G = gift, J = other
            acq_disp_elem = txn.find(".//transactionAmounts/transactionAcquiredDisposedCode/value")
            acq_disp = acq_disp_elem.text.strip() if acq_disp_elem is not None and acq_disp_elem.text else ""

            is_buy = acq_disp == "A" and code in ("P",)
            is_sell = acq_disp == "D" and code in ("S",)

            if code in ("P", "S"):  # Only track open market buys/sells
                transactions.append({
                    "owner": owner_name,
                    "is_director": is_director,
                    "is_officer": is_officer,
                    "is_ten_pct_owner": is_ten_pct,
                    "officer_title": officer_title,
                    "transaction_type": "Buy" if is_buy else "Sell",
                    "shares": shares,
                    "price": price,
                    "value": shares * price,
                    "transaction_code": code,
                    "date": date_str,
                })
        except (ValueError, TypeError, AttributeError):
            continue

    return transactions


def get_insider_transactions(ticker: str, lookback_days: int = 365) -> Optional[dict]:
    """
    Fetch SEC Form 4 insider transactions for a ticker.

    Parses the most recent Form 4 filings and extracts open market buys/sells.
    Computes summary statistics including cluster buy detection.

    Returns:
        {
            "transactions": [...],
            "summary": {
                "total_bought": float,
                "total_sold": float,
                "net_buying": float,
                "n_buyers": int,
                "n_sellers": int,
                "n_transactions": int,
                "cluster_buy_detected": bool,
                "cluster_buy_count": int,
            }
        }
    Returns None on error or if no filings found.
    """
    try:
        company = Company(ticker)
        filings = company.get_filings(form="4")
        if filings is None or len(filings) == 0:
            return None

        # Take most recent 50 Form 4s
        recent_filings = filings.head(50) if hasattr(filings, "head") else filings[:50]

        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        all_transactions = []

        for filing in recent_filings:
            try:
                # Try to get the XML text of the filing
                xml_text = filing.text()
                if not xml_text:
                    continue

                txns = _parse_form4_xml(xml_text)
                for txn in txns:
                    # Filter by date if available
                    if txn.get("date"):
                        try:
                            txn_date = datetime.strptime(txn["date"], "%Y-%m-%d")
                            if txn_date < cutoff_date:
                                continue
                        except ValueError:
                            pass
                    all_transactions.append(txn)
            except Exception:
                continue

        # Compute summary
        buys = [t for t in all_transactions if t["transaction_type"] == "Buy"]
        sells = [t for t in all_transactions if t["transaction_type"] == "Sell"]

        total_bought = sum(t["value"] for t in buys)
        total_sold = sum(t["value"] for t in sells)

        unique_buyers = set(t["owner"] for t in buys if t["owner"])
        unique_sellers = set(t["owner"] for t in sells if t["owner"])

        # Cluster buy detection: 3+ unique insiders buying within 90 days
        cluster_buy_detected = False
        cluster_buy_count = 0
        if len(buys) >= 3:
            buy_dates = []
            for b in buys:
                if b.get("date"):
                    try:
                        buy_dates.append((datetime.strptime(b["date"], "%Y-%m-%d"), b["owner"]))
                    except ValueError:
                        pass

            if buy_dates:
                buy_dates.sort(key=lambda x: x[0])
                # Sliding 90-day window
                for i, (date_i, _) in enumerate(buy_dates):
                    window_owners = set()
                    for j in range(i, len(buy_dates)):
                        date_j, owner_j = buy_dates[j]
                        if (date_j - date_i).days <= 90:
                            window_owners.add(owner_j)
                        else:
                            break
                    if len(window_owners) >= 3:
                        cluster_buy_detected = True
                        cluster_buy_count = max(cluster_buy_count, len(window_owners))

        return {
            "transactions": all_transactions,
            "summary": {
                "total_bought": total_bought,
                "total_sold": total_sold,
                "net_buying": total_bought - total_sold,
                "n_buyers": len(unique_buyers),
                "n_sellers": len(unique_sellers),
                "n_transactions": len(all_transactions),
                "cluster_buy_detected": cluster_buy_detected,
                "cluster_buy_count": cluster_buy_count,
            },
        }

    except Exception:
        return None


# ── Institutional Holdings ───────────────────────────────────────────────────

def get_institutional_holdings(ticker: str) -> Optional[dict]:
    """
    Fetch institutional holder data via yfinance.

    Checks against NOTABLE_VALUE_INVESTORS list and returns top holders.

    Returns:
        {
            "notable_holders": [{"name": ..., "shares": ..., "pct_held": ...}, ...],
            "n_notable_holders": int,
            "top_holders": [{"name": ..., "shares": ..., "pct_held": ..., "value": ...}, ...]
        }
    Returns None on error.
    """
    try:
        stock = yf.Ticker(ticker)
        inst_holders = stock.institutional_holders

        if inst_holders is None or inst_holders.empty:
            return {
                "notable_holders": [],
                "n_notable_holders": 0,
                "top_holders": [],
            }

        top_holders = []
        notable_holders = []

        for _, row in inst_holders.head(15).iterrows():
            holder_name = str(row.get("Holder", ""))
            shares = int(row.get("Shares", 0)) if row.get("Shares") is not None else 0
            pct_held = float(row.get("% Out", 0)) if row.get("% Out") is not None else 0.0
            value = float(row.get("Value", 0)) if row.get("Value") is not None else 0.0

            holder_entry = {
                "name": holder_name,
                "shares": shares,
                "pct_held": pct_held,
                "value": value,
            }
            top_holders.append(holder_entry)

            # Check if notable value investor
            holder_lower = holder_name.lower()
            for notable in NOTABLE_VALUE_INVESTORS:
                if notable in holder_lower:
                    notable_holders.append(holder_entry)
                    break

        return {
            "notable_holders": notable_holders,
            "n_notable_holders": len(notable_holders),
            "top_holders": top_holders[:10],
        }

    except Exception:
        return None


# ── Short Interest ───────────────────────────────────────────────────────────

def get_short_interest(yf_data: dict) -> dict:
    """
    Extract short interest data from yfinance fundamentals.

    Returns:
        {
            "short_percent_of_float": float | None,
            "short_ratio": float | None,
            "short_interest_high": bool,  # True if > 10% of float
        }
    """
    short_pct = yf_data.get("short_percent_of_float")
    short_ratio = yf_data.get("short_ratio")

    short_interest_high = False
    if short_pct is not None and short_pct > 0.10:
        short_interest_high = True

    return {
        "short_percent_of_float": short_pct,
        "short_ratio": short_ratio,
        "short_interest_high": short_interest_high,
    }


# ── Composite Flow Signals ──────────────────────────────────────────────────

def get_flow_signals(ticker: str, yf_data: dict) -> dict:
    """
    Composite flow signals for a ticker.

    Returns:
        {
            "insider": {...} | None,
            "institutional": {...} | None,
            "short_interest": {...},
        }
    """
    insider = get_insider_transactions(ticker)
    institutional = get_institutional_holdings(ticker)
    short_interest = get_short_interest(yf_data)

    return {
        "insider": insider,
        "institutional": institutional,
        "short_interest": short_interest,
    }
