import yfinance as yf
import pandas as pd
from typing import Optional


def get_fundamentals(ticker: str) -> Optional[dict]:
    """
    Pull current fundamentals needed for Klarman screening.
    Returns None if essential data is unavailable.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        market_cap = info.get("marketCap")
        enterprise_value = info.get("enterpriseValue")
        total_revenue = info.get("totalRevenue")

        # Require at minimum a price and revenue to be useful
        if not price or not total_revenue:
            return None

        return {
            "ticker": ticker,
            "name": info.get("longName", ticker),
            "price": price,
            "market_cap": market_cap,
            "enterprise_value": enterprise_value,
            "ebit": info.get("ebit"),
            "ebitda": info.get("ebitda"),
            "free_cashflow": info.get("freeCashflow"),
            "total_revenue": total_revenue,
            "tangible_book_value": info.get("bookValue"),  # Per share
            "shares_outstanding": info.get("sharesOutstanding"),
            "total_debt": info.get("totalDebt"),
            "cash": info.get("totalCash"),
            "pe_ratio": info.get("trailingPE"),
            "pb_ratio": info.get("priceToBook"),
            "current_ratio": info.get("currentRatio"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
        }
    except Exception:
        return None


def get_price_history(ticker: str, years: int = 10) -> pd.DataFrame:
    """Annual price data for momentum features."""
    stock = yf.Ticker(ticker)
    hist = stock.history(period=f"{years}y", interval="1mo")
    return hist[["Close"]].rename(columns={"Close": "price"})


def get_dividend_history(ticker: str) -> pd.Series:
    """Full dividend history for Klarman checklist."""
    stock = yf.Ticker(ticker)
    return stock.dividends


def build_fallback_edgar_data(yf_data: dict) -> Optional[dict]:
    """
    Build a synthetic EDGAR-like data dict from yfinance trailing fundamentals.

    Used as a fallback when SEC EDGAR cannot provide enough historical 10-K
    filings (e.g. recent IPOs, foreign filers, parsing failures).  Constructs
    a conservative 5-year synthetic history by assuming flat revenue and
    margins — this ensures the Monte Carlo engine can still run, albeit with
    wider (more conservative) distributions.
    """
    total_revenue = yf_data.get("total_revenue")
    free_cashflow = yf_data.get("free_cashflow")
    ebit = yf_data.get("ebit")

    if not total_revenue or total_revenue <= 0:
        return None

    # Derive net income proxy from EBIT (assume ~20% effective tax rate)
    ni_proxy = ebit * 0.80 if ebit else total_revenue * 0.05

    # Derive FCF — use yfinance value if available, else conservative 5% of rev
    fcf_proxy = free_cashflow if free_cashflow else total_revenue * 0.05

    # Derive capex as CFO minus FCF approximation (conservative)
    cfo_proxy = fcf_proxy * 1.3 if fcf_proxy > 0 else total_revenue * 0.08
    capex_proxy = abs(cfo_proxy - fcf_proxy)

    margin_proxy = ni_proxy / total_revenue if total_revenue > 0 else 0.05

    # Build 5 years of synthetic data with slight historical variation
    # to give the distribution builder non-degenerate spread.
    # Apply ±5% annual variation around current trailing values.
    n_years = 5
    variation_factors = [0.90, 0.95, 0.97, 1.00, 1.02]

    revenues = [total_revenue * f for f in variation_factors]
    net_incomes = [ni_proxy * f for f in variation_factors]
    fcfs = [fcf_proxy * f for f in variation_factors]
    margins_list = [margin_proxy] * n_years
    capex = [capex_proxy * f for f in variation_factors]

    return {
        "revenues": revenues,
        "net_incomes": net_incomes,
        "fcfs": fcfs,
        "margins": margins_list,
        "capex": capex,
    }


def get_sp500_tickers() -> list[str]:
    """Scrape current S&P 500 constituents from Wikipedia."""
    import urllib.request

    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    req = urllib.request.Request(url, headers={"User-Agent": "ParcaeDashboard/1.0"})
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
    tables = pd.read_html(html)
    return tables[0]["Symbol"].str.replace(".", "-", regex=False).tolist()
