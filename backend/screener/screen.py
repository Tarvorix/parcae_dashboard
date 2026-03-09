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

from backend.data.yfinance_client import (
    get_sp500_tickers,
    get_sp400_tickers,
    get_sp600_tickers,
    get_russell2000_tickers,
    get_fundamentals,
)
from backend.config import KlarmanThresholds
from backend.engine.quality_scores import calculate_altman_z_score

config = KlarmanThresholds()

# ── Universe options ─────────────────────────────────────────────────────────

UNIVERSE_OPTIONS = ("sp500", "sp400", "sp600", "russell2000", "all")


def get_universe_tickers(universe: str = "sp500") -> list[str]:
    """
    Return ticker list for the requested universe.
      sp500      — S&P 500 (large cap)
      sp400      — S&P Mid-Cap 400
      sp600      — S&P Small-Cap 600
      russell2000 — Russell 2000 (via iShares IWM ETF holdings)
      all        — S&P 1500 (500 + 400 + 600 combined, deduplicated)
    """
    if universe == "sp500":
        return get_sp500_tickers()
    elif universe == "sp400":
        return get_sp400_tickers()
    elif universe == "sp600":
        return get_sp600_tickers()
    elif universe == "russell2000":
        return get_russell2000_tickers()
    elif universe == "all":
        combined = get_sp500_tickers() + get_sp400_tickers() + get_sp600_tickers()
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for t in combined:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        return unique
    else:
        return get_sp500_tickers()


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


def score_candidate(
    ev_ebit: Optional[float],
    fcf_yield: Optional[float],
    ptb: Optional[float],
) -> Optional[float]:
    """
    Composite screen score — higher is better.
      40% weight: low EV/EBIT
      40% weight: high FCF yield
      20% weight: low Price/Tangible Book

    Supports partial scoring: if some metrics are None, the score is
    calculated from available metrics with re-normalised weights.
    Returns None only if ALL three metrics are missing.
    """
    components: list[tuple[float, float]] = []  # (score_value, weight)

    if ev_ebit is not None:
        components.append((1.0 / max(ev_ebit, 0.1), 0.4))
    if fcf_yield is not None:
        components.append((fcf_yield, 0.4))
    if ptb is not None:
        components.append((1.0 / max(ptb, 0.1), 0.2))

    if not components:
        return None

    total_weight = sum(w for _, w in components)
    return sum(s * w for s, w in components) / total_weight * 1.0


def run_klarman_screen(
    tickers: Optional[list[str]] = None,
    show_progress: bool = True,
    filter_results: bool = True,
    universe: str = "sp500",
) -> pd.DataFrame:
    """
    Run the Klarman screen against the supplied ticker list.

    If no tickers list is provided, the universe parameter selects which
    index to screen: "sp500", "sp400", "sp600", or "all" (S&P 1500).

    When filter_results=True (default), only candidates passing all hard
    Klarman filters are returned.  When filter_results=False, all stocks
    with calculable metrics are returned with a 'passes_filter' column
    indicating whether they meet the hard thresholds.

    Returns a DataFrame of candidates ranked by composite screen score,
    best opportunities first.  Returns an empty DataFrame if none qualify.
    """
    if tickers is None:
        tickers = get_universe_tickers(universe)

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

        passes = passes_klarman_filters(data, ev_ebit, fcf_yield, ptb)

        if filter_results and not passes:
            continue

        # In filtered mode, require all three metrics for strict Klarman compliance.
        # In unfiltered ("show all") mode, allow partial scores so users can
        # see every stock ranked by whatever metrics are available.
        if filter_results and (ev_ebit is None or fcf_yield is None or ptb is None):
            continue

        score = score_candidate(ev_ebit, fcf_yield, ptb)

        # Skip only if we have zero calculable metrics
        if score is None:
            continue

        # Altman Z-Score (uses yfinance data only — fast enough for screening)
        altman_result = calculate_altman_z_score(data)
        altman_z = altman_result["z_score"] if altman_result else None
        altman_zone = altman_result["zone"] if altman_result else None

        results.append({
            "ticker": ticker,
            "name": data.get("name", ticker),
            "price": data.get("price"),
            "market_cap": data.get("market_cap"),
            "ev_ebit": round(ev_ebit, 2) if ev_ebit is not None else None,
            "fcf_yield_pct": round(fcf_yield * 100.0, 2) if fcf_yield is not None else None,
            "price_tangible_book": round(ptb, 2) if ptb is not None else None,
            "net_debt_ebitda": round(net_debt_ebitda, 2) if net_debt_ebitda is not None else None,
            "altman_z_score": round(altman_z, 4) if altman_z is not None else None,
            "altman_zone": altman_zone,
            "sector": data.get("sector"),
            "industry": data.get("industry"),
            "screen_score": round(score, 6),
            "passes_filter": passes,
        })

    if not results:
        return pd.DataFrame(columns=[
            "ticker", "name", "price", "market_cap", "ev_ebit",
            "fcf_yield_pct", "price_tangible_book", "net_debt_ebitda",
            "altman_z_score", "altman_zone",
            "sector", "industry", "screen_score", "passes_filter",
        ])

    df = pd.DataFrame(results)
    return df.sort_values("screen_score", ascending=False).reset_index(drop=True)
