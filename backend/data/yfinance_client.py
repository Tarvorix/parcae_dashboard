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


def get_sp500_tickers() -> list[str]:
    """Scrape current S&P 500 constituents from Wikipedia."""
    import urllib.request

    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    req = urllib.request.Request(url, headers={"User-Agent": "ParcaeDashboard/1.0"})
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
    tables = pd.read_html(html)
    return tables[0]["Symbol"].str.replace(".", "-", regex=False).tolist()
