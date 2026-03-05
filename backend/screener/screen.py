"""
Nightly Klarman Screen

Screens a list of tickers (default: full S&P 500) against three hard filters:
  1. EV/EBIT  ≤ max_ev_ebit          (cheap on earnings power)
  2. FCF Yield ≥ min_fcf_yield        (high free cash generation)
  3. Price/Tangible Book ≤ max_ptb    (not overpriced vs assets)
  4. Revenue  ≥ min_revenue           (avoid micro-caps)

Candidates that pass all four filters are scored and ranked so the best
Klarman opportunities float to the top of the watchlist.
"""

import pandas as pd
from tqdm import tqdm
from typing import Optional

from backend.data.yfinance_client import get_sp500_tickers, get_fundamentals
from backend.config import KlarmanThresholds

config = KlarmanThresholds()


# ── Individual metric calculators ─────────────────────────────────────────────

def calculate_ev_ebit(data: dict) -> Optional[float]:
    ev = data.get("enterprise_value")
    ebit = data.get("ebit")
    if ev and ebit and ebit > 0:
        return ev / ebit
    return None


def calculate_fcf_yield(data: dict) -> Optional[float]:
    fcf = data.get("free_cashflow")
    mc = data.get("market_cap")
    if fcf and mc and mc > 0:
        return fcf / mc
    return None


def calculate_price_tangible_book(data: dict) -> Optional[float]:
    price = data.get("price")
    book = data.get("tangible_book_value")
    if price and book and book > 0:
        return price / book
    return None


def calculate_net_debt_ebitda(data: dict) -> Optional[float]:
    total_debt = data.get("total_debt") or 0.0
    cash = data.get("cash") or 0.0
    ebitda = data.get("ebitda")
    net_debt = total_debt - cash
    if ebitda and ebitda > 0:
        return net_debt / ebitda
    return None


# ── Core screening logic ──────────────────────────────────────────────────────

def passes_klarman_filters(
    data: dict,
    ev_ebit: Optional[float],
    fcf_yield: Optional[float],
    ptb: Optional[float],
) -> bool:
    """Return True only if all hard Klarman filters are satisfied."""
    revenue = data.get("total_revenue") or 0

    if revenue < config.min_revenue:
        return False
    if ev_ebit is None or ev_ebit > config.max_ev_ebit:
        return False
    if fcf_yield is None or fcf_yield < config.min_fcf_yield:
        return False
    if ptb is None or ptb > config.max_price_tangible_book:
        return False

    return True


def score_candidate(ev_ebit: float, fcf_yield: float, ptb: float) -> float:
    """
    Composite screen score — higher is better.
      40% weight: low EV/EBIT
      40% weight: high FCF yield
      20% weight: low Price/Tangible Book
    """
    ev_ebit_score = 1.0 / max(ev_ebit, 0.1)
    fcf_score = fcf_yield          # already a decimal (e.g. 0.09 for 9%)
    ptb_score = 1.0 / max(ptb, 0.1)

    return ev_ebit_score * 0.4 + fcf_score * 0.4 + ptb_score * 0.2


def run_klarman_screen(
    tickers: Optional[list[str]] = None,
    show_progress: bool = True,
) -> pd.DataFrame:
    """
    Run the Klarman screen against the supplied ticker list.
    Defaults to the full S&P 500 if no list is provided.

    Returns a DataFrame of candidates ranked by composite screen score,
    best opportunities first.  Returns an empty DataFrame if none qualify.
    """
    if tickers is None:
        tickers = get_sp500_tickers()

    results: list[dict] = []

    iterator = tqdm(tickers, desc="Klarman screen") if show_progress else tickers

    for ticker in iterator:
        data = get_fundamentals(ticker)
        if not data:
            continue

        ev_ebit = calculate_ev_ebit(data)
        fcf_yield = calculate_fcf_yield(data)
        ptb = calculate_price_tangible_book(data)
        net_debt_ebitda = calculate_net_debt_ebitda(data)

        if not passes_klarman_filters(data, ev_ebit, fcf_yield, ptb):
            continue

        results.append({
            "ticker": ticker,
            "name": data.get("name", ticker),
            "price": data.get("price"),
            "market_cap": data.get("market_cap"),
            "ev_ebit": round(ev_ebit, 2),
            "fcf_yield_pct": round(fcf_yield * 100.0, 2),
            "price_tangible_book": round(ptb, 2),
            "net_debt_ebitda": round(net_debt_ebitda, 2) if net_debt_ebitda is not None else None,
            "sector": data.get("sector"),
            "industry": data.get("industry"),
            "screen_score": round(score_candidate(ev_ebit, fcf_yield, ptb), 6),
        })

    if not results:
        return pd.DataFrame(columns=[
            "ticker", "name", "price", "market_cap", "ev_ebit",
            "fcf_yield_pct", "price_tangible_book", "net_debt_ebitda",
            "sector", "industry", "screen_score",
        ])

    df = pd.DataFrame(results)
    return df.sort_values("screen_score", ascending=False).reset_index(drop=True)
