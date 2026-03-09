"""
Valuation Anchors — EPV (Greenwald) + NCAV (Graham)

Provides two non-growth-dependent valuation methods as independent price
anchors alongside the Monte Carlo DCF:

- **EPV** (Earnings Power Value): capitalises current normalised earnings
  at the company's cost of capital, assuming zero growth.
- **NCAV** (Net Current Asset Value): Graham's liquidation floor — current
  assets minus *all* liabilities.
"""

from typing import Optional

from backend.config import KlarmanThresholds

config = KlarmanThresholds()


def calculate_epv(
    yf_data: dict,
    edgar_data: Optional[dict] = None,
) -> Optional[dict]:
    """
    Earnings Power Value (Bruce Greenwald methodology).

    EPV = Adjusted_EBIT × (1 − tax_rate) / WACC
    Per share = EPV / shares_outstanding

    No growth assumption — just current earnings power capitalised.
    Returns None if EBIT or shares_outstanding is missing/invalid.
    """
    ebit = yf_data.get("ebit")
    shares = yf_data.get("shares_outstanding")

    if not ebit or not shares or shares <= 0:
        return None

    # Tax rate — prefer yfinance effective rate, fall back to default
    tax_rate = yf_data.get("tax_rate")
    if tax_rate is None or tax_rate <= 0 or tax_rate >= 1:
        tax_rate = config.default_tax_rate

    # WACC estimation
    total_debt = yf_data.get("total_debt") or 0
    market_cap = yf_data.get("market_cap") or 0
    total_capital = market_cap + total_debt

    if total_capital > 0:
        equity_weight = market_cap / total_capital
        debt_weight = total_debt / total_capital
    else:
        equity_weight = 1.0
        debt_weight = 0.0

    wacc = (
        equity_weight * config.default_cost_of_equity
        + debt_weight * config.default_cost_of_debt * (1 - tax_rate)
    )
    wacc = max(wacc, 0.04)  # Floor at 4% to avoid extreme values

    # NOPAT = EBIT × (1 − tax_rate)
    nopat = ebit * (1 - tax_rate)

    # EPV = NOPAT / WACC
    epv_total = nopat / wacc
    epv_per_share = epv_total / shares

    # Franchise value: EPV − reproduction cost of assets (total_assets as proxy)
    total_assets = yf_data.get("total_assets")
    franchise_value = None
    if total_assets and total_assets > 0:
        franchise_value = epv_total - total_assets

    return {
        "epv_total": round(epv_total, 2),
        "epv_per_share": round(epv_per_share, 2),
        "nopat": round(nopat, 2),
        "wacc": round(wacc, 4),
        "tax_rate_used": round(tax_rate, 4),
        "franchise_value": round(franchise_value, 2) if franchise_value is not None else None,
        "has_franchise": franchise_value is not None and franchise_value > 0,
    }


def calculate_ncav(
    yf_data: dict,
) -> Optional[dict]:
    """
    Net Current Asset Value (Benjamin Graham).

    NCAV = (Current Assets − Total Liabilities) / Shares Outstanding

    Stocks trading below NCAV are the cheapest possible — Graham's
    cigar-butt strategy.  Very few stocks trade below NCAV in modern
    markets.

    Returns None if current_assets, total_liabilities, or
    shares_outstanding is missing/invalid.
    """
    current_assets = yf_data.get("current_assets")
    total_liabilities = yf_data.get("total_liabilities")
    shares = yf_data.get("shares_outstanding")
    price = yf_data.get("price")

    if current_assets is None or total_liabilities is None:
        return None
    if not shares or shares <= 0:
        return None

    ncav_total = current_assets - total_liabilities
    ncav_per_share = ncav_total / shares

    # Discount to NCAV: positive means price is below NCAV
    discount_to_ncav = None
    if ncav_per_share > 0 and price:
        discount_to_ncav = (ncav_per_share - price) / ncav_per_share

    return {
        "ncav_total": round(ncav_total, 2),
        "ncav_per_share": round(ncav_per_share, 2),
        "current_assets": current_assets,
        "total_liabilities": total_liabilities,
        "trades_below_ncav": (
            price is not None
            and ncav_per_share > 0
            and price < ncav_per_share
        ),
        "discount_to_ncav": round(discount_to_ncav, 4) if discount_to_ncav is not None else None,
    }


def calculate_valuation_anchors(
    yf_data: dict,
    edgar_data: Optional[dict] = None,
) -> dict:
    """Compute both EPV and NCAV valuation anchors."""
    return {
        "epv": calculate_epv(yf_data, edgar_data),
        "ncav": calculate_ncav(yf_data),
    }
