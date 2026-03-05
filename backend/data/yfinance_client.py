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

        # Tangible book value per share — try multiple yfinance fields
        # bookValue is "Book Value Per Share (mrq)" in Yahoo Finance
        tangible_bv = info.get("bookValue")
        if tangible_bv is None:
            # Reverse-calculate from priceToBook ratio if available
            ptb_ratio = info.get("priceToBook")
            if ptb_ratio and ptb_ratio > 0 and price:
                tangible_bv = price / ptb_ratio

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
            "tangible_book_value": tangible_bv,  # Per share
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


def _scrape_sp_tickers(url: str) -> list[str]:
    """Scrape S&P index constituents from a Wikipedia list page."""
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "ParcaeDashboard/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8")
    tables = pd.read_html(html)
    return tables[0]["Symbol"].str.replace(".", "-", regex=False).tolist()


# ── Hardcoded fallback tickers (top ~50 by market cap) ────────────────────────
# Used when Wikipedia scraping fails (rate-limited, network errors, etc.)

_SP500_FALLBACK = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "BRK-B", "UNH", "JNJ",
    "V", "XOM", "JPM", "PG", "MA", "HD", "CVX", "LLY", "ABBV", "MRK",
    "PEP", "KO", "COST", "AVGO", "WMT", "TMO", "MCD", "CSCO", "ACN", "ABT",
    "DHR", "CRM", "NEE", "LIN", "TXN", "WFC", "BMY", "PM", "UPS", "MS",
    "RTX", "UNP", "SCHW", "HON", "LOW", "AMGN", "INTC", "QCOM", "IBM", "GS",
]

_SP400_FALLBACK = [
    "DECK", "WSM", "FIX", "TXRH", "TOL", "PCTY", "LNTH", "MEDP", "MTH", "EHC",
    "CIVI", "PNFP", "PIPR", "CBT", "WFRD", "SLM", "BOOT", "KNF", "CALM", "CSWI",
    "IBOC", "SIG", "COOP", "PI", "ACIW", "AWI", "MOD", "DY", "ESNT", "BLD",
    "ENSG", "SKY", "QTWO", "MMSI", "NOVT", "SITE", "RHP", "KBR", "FSS", "VIRT",
    "TNET", "EXPO", "PRGS", "SPSC", "CW", "GMS", "TFIN", "APAM", "POWL", "SIGI",
]

_SP600_FALLBACK = [
    "CARG", "ATEN", "SMTC", "AEIS", "AORT", "ARLO", "AROC", "AX", "BCC", "CAKE",
    "CENTA", "CPRX", "DFIN", "DORM", "EAT", "EPRT", "ETD", "EVTC", "FELE", "FORM",
    "GSHD", "HASI", "HBI", "HEES", "HLF", "IBKR", "IDCC", "IPAR", "JACK", "KFRC",
    "LGND", "LKFN", "LQDT", "MATX", "MCRI", "MHO", "MGEE", "NSIT", "OFG", "PATK",
    "PLMR", "PRFT", "PRLB", "RDN", "RGR", "RMBS", "SNDR", "STEP", "TBBK", "UFPI",
]


def get_sp500_tickers() -> list[str]:
    """Scrape current S&P 500 constituents from Wikipedia, with hardcoded fallback."""
    try:
        return _scrape_sp_tickers(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )
    except Exception:
        return list(_SP500_FALLBACK)


def get_sp400_tickers() -> list[str]:
    """Scrape current S&P Mid-Cap 400 constituents from Wikipedia, with hardcoded fallback."""
    try:
        return _scrape_sp_tickers(
            "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"
        )
    except Exception:
        return list(_SP400_FALLBACK)


def get_sp600_tickers() -> list[str]:
    """Scrape current S&P Small-Cap 600 constituents from Wikipedia, with hardcoded fallback."""
    try:
        return _scrape_sp_tickers(
            "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies"
        )
    except Exception:
        return list(_SP600_FALLBACK)


def get_russell2000_tickers() -> list[str]:
    """
    Fetch Russell 2000 constituents from iShares IWM ETF holdings CSV.
    Falls back to S&P 600 + S&P 400 if the iShares download fails.
    """
    import urllib.request
    import csv
    import io

    iwm_url = (
        "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/"
        "1467271812596.ajax?fileType=csv&fileName=IWM_holdings&dataType=fund"
    )

    try:
        req = urllib.request.Request(iwm_url, headers={
            "User-Agent": "ParcaeDashboard/1.0",
            "Accept": "text/csv,text/plain,*/*",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        # The iShares CSV has header rows before the actual data.
        # Find the line starting with "Ticker," which marks the real header.
        lines = raw.splitlines()
        header_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith("Ticker,") or line.strip().startswith('"Ticker"'):
                header_idx = i
                break

        if header_idx is None:
            raise ValueError("Could not find Ticker header in IWM CSV")

        csv_text = "\n".join(lines[header_idx:])
        reader = csv.DictReader(io.StringIO(csv_text))

        tickers = []
        skip_values = {"", "-", "USD", "CASH", "TBILL", "MARGIN_USD", "UNKNOWN"}
        for row in reader:
            ticker = (row.get("Ticker") or "").strip().upper()
            if ticker and ticker not in skip_values:
                # Skip rows that look like cash or currency positions
                asset_class = (row.get("Asset Class") or "").strip().upper()
                if asset_class in ("CASH", "FUTURES", "MONEY MARKET"):
                    continue
                # Normalise BRK.B → BRK-B for yfinance compatibility
                ticker = ticker.replace(".", "-")
                tickers.append(ticker)

        if len(tickers) > 100:
            return tickers

        # Too few tickers — likely a parsing issue, fall through to fallback
        raise ValueError(f"Only parsed {len(tickers)} tickers from IWM CSV")

    except Exception:
        # Fallback: combine S&P 600 (small-cap) + S&P 400 (mid-cap) as
        # a reasonable approximation of the Russell 2000 universe.
        combined = get_sp600_tickers() + get_sp400_tickers()
        seen: set[str] = set()
        unique: list[str] = []
        for t in combined:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        return unique
