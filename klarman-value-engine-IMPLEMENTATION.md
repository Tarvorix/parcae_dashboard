# Klarman Value Engine — Full Claude Code Implementation Plan

> The React prototype (klarman-value-engine.jsx) is already built.
> This plan turns it into a production system with real data, automated screening, and portfolio risk.
>
> **Prompt for Claude Code:** "Read this file fully before writing any code. Implement Phase 1 first. Do not move to the next phase until the current one is complete and tested."

---

## What This System Does

1. **Screens** the full stock universe nightly for Klarman/Graham candidates (low EV/EBIT, high FCF yield, low price-to-tangible-book)
2. **Auto-populates** distributional DCF inputs from 10 years of historical financial data
3. **Runs 50K–200K Monte Carlo paths** per candidate to produce a full intrinsic value distribution
4. **Calculates margin of safety** — how far current price is below the 25th percentile of the value distribution (Klarman's downside focus)
5. **Scores and ranks** a watchlist by Klarman Score daily
6. **Tracks catalyst milestones** per position using a particle filter to update value estimates as events unfold
7. **Models portfolio tail risk** using copulas across all open positions
8. **Serves everything** through the existing React frontend wired to a live FastAPI backend

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend                           │
│   (klarman-value-engine.jsx — already built)               │
│   Wire to API instead of hardcoded scenarios               │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST + WebSocket
┌───────────────────────▼─────────────────────────────────────┐
│                  FastAPI Backend                            │
│   /screen        → run nightly screener                    │
│   /analyze/{id}  → full Monte Carlo DCF                    │
│   /portfolio     → copula tail risk                        │
│   /watchlist     → ranked candidates                       │
│   /position/{id} → catalyst tracker                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
    yfinance       SEC EDGAR       SQLite DB
    (prices,       (10yr history,  (positions,
    ratios,        raw filings,    catalysts,
    dividends)     XBRL data)      watchlist)
```

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Frontend | React 18 + TypeScript (existing .jsx, convert to .tsx) |
| Backend | Python 3.11 + FastAPI |
| Data — fast | yfinance (prices, ratios, dividends) |
| Data — deep | SEC EDGAR via edgartools (10yr financials) |
| Monte Carlo | NumPy — pure vectorized, no scipy needed |
| Copula | SciPy stats (Gaussian copula), manual Student-t |
| Particle Filter | NumPy — sequential importance resampling |
| Database | SQLite via SQLAlchemy (upgrade to Postgres when needed) |
| Task Queue | APScheduler (nightly screen job, no Redis needed for v1) |
| Deploy | Docker Compose → Railway or Render |

---

## Project Structure

```
klarman-value-engine/
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ValueDistributionChart.tsx   # Histogram + MoS overlay
│   │   │   ├── DownsidePanel.tsx            # Klarman checklist tab
│   │   │   ├── FCFProjections.tsx           # FCF bands tab
│   │   │   ├── DecisionMatrix.tsx           # Kelly sizing tab
│   │   │   ├── Watchlist.tsx                # Ranked candidates
│   │   │   └── PortfolioRisk.tsx            # Copula tail risk
│   │   ├── api/
│   │   │   └── client.ts                    # All fetch calls to backend
│   │   └── types/
│   │       └── index.ts
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── main.py                              # FastAPI app
│   ├── config.py                            # All thresholds + settings
│   ├── requirements.txt
│   ├── db/
│   │   ├── models.py                        # SQLAlchemy models
│   │   └── database.py                      # Session management
│   ├── data/
│   │   ├── yfinance_client.py               # yfinance wrapper
│   │   └── edgar_client.py                  # edgartools wrapper
│   ├── screener/
│   │   └── screen.py                        # Nightly Klarman screen
│   ├── engine/
│   │   ├── distributions.py                 # Build triangular dists from history
│   │   ├── monte_carlo.py                   # Core DCF simulation
│   │   ├── margin_of_safety.py              # MoS calc + Klarman score
│   │   └── kelly.py                         # Position sizing
│   ├── portfolio/
│   │   ├── copula.py                        # Gaussian + Student-t copula
│   │   └── tail_risk.py                     # CVaR, max drawdown
│   └── catalyst/
│       └── particle_filter.py               # Milestone tracking
├── docker-compose.yml
└── .env.example
```

---

## Phase 1 — Backend Core: Data + Monte Carlo DCF

### `backend/config.py`

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class KlarmanThresholds:
    # Screening thresholds
    max_ev_ebit: float = 10.0           # EV/EBIT <= 10
    min_fcf_yield: float = 0.07         # FCF yield >= 7%
    max_price_tangible_book: float = 1.2
    min_revenue: float = 100_000_000    # $100M minimum
    max_net_debt_ebitda: float = 3.0    # Not overleveraged

    # Monte Carlo settings
    n_simulations: int = 100_000
    projection_years: int = 10
    terminal_growth_rate: float = 0.025  # Conservative 2.5%

    # Margin of safety
    required_margin_of_safety: float = 0.30   # Need 30%+ discount
    klarman_downside_percentile: float = 0.25  # Price vs 25th pct of dist

    # Kelly sizing
    max_position_size: float = 0.15     # Max 15% of portfolio
    kelly_fraction: float = 0.25        # Quarter-Kelly (conservative)

SEC_IDENTITY = "Your Name your@email.com"  # Required by SEC EDGAR
```

---

### `backend/data/yfinance_client.py`

```python
import yfinance as yf
import pandas as pd
from typing import Optional

def get_fundamentals(ticker: str) -> Optional[dict]:
    """
    Pull current fundamentals needed for Klarman screening.
    Returns None if data unavailable.
    """
    stock = yf.Ticker(ticker)
    info = stock.info

    try:
        return {
            "ticker": ticker,
            "name": info.get("longName", ticker),
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "ebit": info.get("ebit"),
            "ebitda": info.get("ebitda"),
            "free_cashflow": info.get("freeCashflow"),
            "total_revenue": info.get("totalRevenue"),
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


def get_dividend_history(ticker: str) -> pd.DataFrame:
    """Full dividend history for Klarman checklist."""
    stock = yf.Ticker(ticker)
    return stock.dividends


def get_sp500_tickers() -> list[str]:
    tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
    return tables[0]["Symbol"].str.replace(".", "-").tolist()
```

---

### `backend/data/edgar_client.py`

```python
from edgar import Company, set_identity
from typing import Optional
import pandas as pd
from backend.config import SEC_IDENTITY

set_identity(SEC_IDENTITY)


def get_10yr_financials(ticker: str) -> Optional[dict]:
    """
    Pull 10 years of annual financials from SEC EDGAR 10-K filings.
    Returns dict with lists of annual values, oldest to newest.
    """
    try:
        company = Company(ticker)
        filings = company.get_filings(form="10-K").head(12)

        revenues, net_incomes, fcfs, margins, capex_list = [], [], [], [], []

        for filing in filings:
            try:
                financials = filing.financials
                income = financials.income_statement
                cashflow = financials.cash_flow_statement

                rev = income.get("Revenues") or income.get("RevenueFromContractWithCustomerExcludingAssessedTax")
                ni = income.get("NetIncomeLoss")
                cfo = cashflow.get("NetCashProvidedByUsedInOperatingActivities")
                capex = cashflow.get("PaymentsToAcquirePropertyPlantAndEquipment")

                if rev and ni and cfo and capex:
                    revenues.append(float(rev))
                    net_incomes.append(float(ni))
                    fcf = float(cfo) - abs(float(capex))
                    fcfs.append(fcf)
                    margins.append(float(ni) / float(rev) if float(rev) > 0 else 0)
                    capex_list.append(abs(float(capex)))
            except Exception:
                continue

        if len(revenues) < 5:
            return None  # Not enough history

        return {
            "revenues": revenues,
            "net_incomes": net_incomes,
            "fcfs": fcfs,
            "margins": margins,
            "capex": capex_list,
        }

    except Exception:
        return None
```

---

### `backend/engine/distributions.py`

```python
import numpy as np
from typing import Optional

def build_distributions_from_history(edgar_data: dict, yf_data: dict) -> dict:
    """
    Convert 10yr historical financial data into bear/base/bull
    triangular distribution parameters for Monte Carlo DCF.

    Klarman approach: base = median, bear = 10th percentile (or worse),
    bull = 75th percentile (not optimistic — stay conservative).
    """
    fcfs = np.array(edgar_data["fcfs"])
    revenues = np.array(edgar_data["revenues"])
    margins = np.array(edgar_data["margins"])

    # FCF growth rates year-over-year
    fcf_growth_rates = np.diff(fcfs) / np.abs(fcfs[:-1])
    fcf_growth_rates = fcf_growth_rates[np.isfinite(fcf_growth_rates)]

    rev_growth_rates = np.diff(revenues) / revenues[:-1]
    rev_growth_rates = rev_growth_rates[np.isfinite(rev_growth_rates)]

    # Revenue growth distribution
    rev_growth = {
        "bear": float(np.percentile(rev_growth_rates, 10)),
        "base": float(np.median(rev_growth_rates)),
        "bull": float(np.percentile(rev_growth_rates, 75)),
    }

    # Margin distribution
    margin = {
        "bear": float(np.percentile(margins, 10)),
        "base": float(np.median(margins)),
        "bull": float(np.percentile(margins, 75)),
    }

    # FCF margin = FCF / Revenue
    current_rev = revenues[-1] if len(revenues) > 0 else 0
    fcf_margins = fcfs / revenues[:len(fcfs)] if current_rev > 0 else fcfs
    fcf_margin = {
        "bear": float(np.percentile(fcf_margins, 10)),
        "base": float(np.median(fcf_margins)),
        "bull": float(np.percentile(fcf_margins, 75)),
    }

    # Discount rate (WACC proxy — use conservative range)
    discount_rate = {
        "bear": 0.12,   # High risk
        "base": 0.10,
        "bull": 0.08,   # Low risk
    }

    return {
        "revenue_growth": rev_growth,
        "fcf_margin": fcf_margin,
        "net_margin": margin,
        "discount_rate": discount_rate,
        "current_fcf": float(fcfs[-1]) if len(fcfs) > 0 else 0,
        "current_revenue": float(revenues[-1]) if len(revenues) > 0 else 0,
        "shares_outstanding": yf_data.get("shares_outstanding", 1),
    }


def sample_triangular(bear: float, base: float, bull: float, n: int) -> np.ndarray:
    """Sample from triangular distribution."""
    low = min(bear, base, bull)
    high = max(bear, base, bull)
    mode = base
    # Clamp mode to [low, high]
    mode = max(low, min(mode, high))
    return np.random.triangular(low, mode, high, n)
```

---

### `backend/engine/monte_carlo.py`

```python
import numpy as np
from backend.config import KlarmanThresholds
from backend.engine.distributions import sample_triangular

config = KlarmanThresholds()


def run_dcf_simulation(distributions: dict) -> np.ndarray:
    """
    Core Monte Carlo DCF engine.
    Runs N simulations, returns array of intrinsic values per share.

    Klarman approach:
    - Use FCF not earnings
    - Conservative terminal growth
    - Focus on distribution shape, especially left tail
    """
    n = config.n_simulations
    years = config.projection_years

    current_fcf = distributions["current_fcf"]
    shares = distributions["shares_outstanding"]

    # Sample all distributions
    revenue_growth = sample_triangular(
        distributions["revenue_growth"]["bear"],
        distributions["revenue_growth"]["base"],
        distributions["revenue_growth"]["bull"],
        n
    )

    fcf_margin = sample_triangular(
        distributions["fcf_margin"]["bear"],
        distributions["fcf_margin"]["base"],
        distributions["fcf_margin"]["bull"],
        n
    )

    discount_rate = sample_triangular(
        distributions["discount_rate"]["bear"],
        distributions["discount_rate"]["base"],
        distributions["discount_rate"]["bull"],
        n
    )

    terminal_growth = np.random.normal(
        config.terminal_growth_rate,
        0.005,  # Small uncertainty around terminal growth
        n
    )
    terminal_growth = np.clip(terminal_growth, 0.0, 0.04)

    # Project FCF for each year
    current_revenue = distributions["current_revenue"]
    pv_fcfs = np.zeros(n)

    for year in range(1, years + 1):
        projected_revenue = current_revenue * (1 + revenue_growth) ** year
        projected_fcf = projected_revenue * fcf_margin
        discount_factor = (1 + discount_rate) ** year
        pv_fcfs += projected_fcf / discount_factor

    # Terminal value
    final_year_fcf = current_revenue * (1 + revenue_growth) ** years * fcf_margin
    terminal_value = final_year_fcf * (1 + terminal_growth) / (discount_rate - terminal_growth)
    terminal_value = np.where(
        discount_rate > terminal_growth,
        terminal_value / (1 + discount_rate) ** years,
        0  # Degenerate case
    )

    total_value = pv_fcfs + terminal_value

    # Per share intrinsic value
    intrinsic_value_per_share = total_value / shares if shares > 0 else total_value

    return intrinsic_value_per_share
```

---

### `backend/engine/margin_of_safety.py`

```python
import numpy as np
from backend.config import KlarmanThresholds

config = KlarmanThresholds()


def calculate_margin_of_safety(
    intrinsic_values: np.ndarray,
    current_price: float
) -> dict:
    """
    Klarman-style margin of safety analysis.
    Focus on downside: compare price to 25th percentile of value distribution.
    """
    p10 = np.percentile(intrinsic_values, 10)
    p25 = np.percentile(intrinsic_values, 25)
    p50 = np.percentile(intrinsic_values, 50)
    p75 = np.percentile(intrinsic_values, 75)
    p90 = np.percentile(intrinsic_values, 90)

    # Margin of safety vs median
    mos_median = (p50 - current_price) / p50 if p50 > 0 else -1

    # Klarman's preferred: MoS vs 25th percentile (downside focus)
    mos_downside = (p25 - current_price) / p25 if p25 > 0 else -1

    # Probability price is below intrinsic value
    prob_undervalued = np.mean(intrinsic_values > current_price)

    # Klarman score: composite of downside MoS + probability undervalued
    # Both must be strong for a high score
    klarman_score = (
        max(0, mos_downside) * 0.5 +
        max(0, prob_undervalued - 0.5) * 2 * 0.5
    ) * 100

    return {
        "current_price": current_price,
        "p10": round(p10, 2),
        "p25": round(p25, 2),
        "p50": round(p50, 2),
        "p75": round(p75, 2),
        "p90": round(p90, 2),
        "mos_median": round(mos_median, 4),
        "mos_downside": round(mos_downside, 4),
        "prob_undervalued": round(prob_undervalued, 4),
        "klarman_score": round(klarman_score, 1),
        "passes_mos_threshold": mos_downside >= config.required_margin_of_safety,
        "histogram_data": intrinsic_values.tolist(),  # For frontend chart
    }
```

---

### `backend/engine/kelly.py`

```python
from backend.config import KlarmanThresholds

config = KlarmanThresholds()


def calculate_position_size(
    prob_undervalued: float,
    mos_downside: float,
    portfolio_value: float,
    current_price: float
) -> dict:
    """
    Fractional Kelly position sizing.
    Kelly fraction = edge / odds
    Edge = probability weighted gain - probability weighted loss
    """
    prob_win = prob_undervalued
    prob_loss = 1 - prob_win

    # Expected gain if right: MoS realized
    expected_gain = max(0, mos_downside)
    # Expected loss if wrong: assume 30% downside (Klarman's downside focus)
    expected_loss = 0.30

    if expected_loss == 0 or prob_win == 0:
        return {"kelly_pct": 0, "dollar_amount": 0, "shares": 0}

    # Kelly formula
    kelly_full = (prob_win * expected_gain - prob_loss * expected_loss) / expected_gain
    kelly_full = max(0, kelly_full)

    # Apply fraction (quarter-Kelly) and cap
    kelly_fractional = kelly_full * config.kelly_fraction
    kelly_capped = min(kelly_fractional, config.max_position_size)

    dollar_amount = portfolio_value * kelly_capped
    shares = int(dollar_amount / current_price) if current_price > 0 else 0

    return {
        "kelly_full_pct": round(kelly_full * 100, 1),
        "kelly_fractional_pct": round(kelly_capped * 100, 1),
        "dollar_amount": round(dollar_amount, 2),
        "shares": shares,
    }
```

---

## Phase 2 — Screener: Nightly Klarman Screen

### `backend/screener/screen.py`

```python
import pandas as pd
from tqdm import tqdm
from backend.data.yfinance_client import get_sp500_tickers, get_fundamentals
from backend.config import KlarmanThresholds

config = KlarmanThresholds()


def calculate_ev_ebit(data: dict) -> float | None:
    ev = data.get("enterprise_value")
    ebit = data.get("ebit")
    if ev and ebit and ebit > 0:
        return ev / ebit
    return None


def calculate_fcf_yield(data: dict) -> float | None:
    fcf = data.get("free_cashflow")
    mc = data.get("market_cap")
    if fcf and mc and mc > 0:
        return fcf / mc
    return None


def calculate_price_tangible_book(data: dict) -> float | None:
    price = data.get("price")
    book = data.get("tangible_book_value")
    if price and book and book > 0:
        return price / book
    return None


def run_klarman_screen() -> pd.DataFrame:
    """
    Run nightly Klarman screen against S&P 500.
    Returns DataFrame of candidates sorted by Klarman Score.
    """
    tickers = get_sp500_tickers()
    results = []

    for ticker in tqdm(tickers, desc="Screening"):
        data = get_fundamentals(ticker)
        if not data:
            continue

        # Hard filters
        ev_ebit = calculate_ev_ebit(data)
        fcf_yield = calculate_fcf_yield(data)
        ptb = calculate_price_tangible_book(data)
        revenue = data.get("total_revenue", 0) or 0

        if revenue < config.min_revenue:
            continue
        if ev_ebit is None or ev_ebit > config.max_ev_ebit:
            continue
        if fcf_yield is None or fcf_yield < config.min_fcf_yield:
            continue
        if ptb is None or ptb > config.max_price_tangible_book:
            continue

        results.append({
            "ticker": ticker,
            "name": data.get("name"),
            "price": data.get("price"),
            "ev_ebit": round(ev_ebit, 2),
            "fcf_yield": round(fcf_yield * 100, 2),
            "price_tangible_book": round(ptb, 2),
            "sector": data.get("sector"),
        })

    df = pd.DataFrame(results)
    if df.empty:
        return df

    # Sort: low EV/EBIT, high FCF yield, low P/TBV
    df["screen_score"] = (
        (1 / df["ev_ebit"].clip(lower=0.1)) * 0.4 +
        df["fcf_yield"] * 0.4 +
        (1 / df["price_tangible_book"].clip(lower=0.1)) * 0.2
    )
    return df.sort_values("screen_score", ascending=False).reset_index(drop=True)
```

---

## Phase 3 — Portfolio Risk: Copula Model

### `backend/portfolio/copula.py`

```python
import numpy as np
from scipy import stats


def gaussian_copula_portfolio_var(
    position_returns: np.ndarray,
    correlation_matrix: np.ndarray,
    confidence: float = 0.95,
    n_simulations: int = 50_000
) -> dict:
    """
    Gaussian copula to model correlated portfolio tail risk.
    position_returns: shape (n_positions, n_historical_periods)
    """
    n_positions = position_returns.shape[0]

    # Fit marginal distributions (empirical CDF → normal scores)
    uniform_samples = np.random.multivariate_normal(
        mean=np.zeros(n_positions),
        cov=correlation_matrix,
        size=n_simulations
    )
    # Convert to uniform via normal CDF
    uniform_samples = stats.norm.cdf(uniform_samples)

    # Map back to each position's empirical distribution
    portfolio_sim_returns = np.zeros((n_simulations, n_positions))
    for i in range(n_positions):
        sorted_hist = np.sort(position_returns[i])
        idx = (uniform_samples[:, i] * len(sorted_hist)).astype(int).clip(0, len(sorted_hist) - 1)
        portfolio_sim_returns[:, i] = sorted_hist[idx]

    # Equal-weighted portfolio return (caller can pass weights)
    portfolio_returns = portfolio_sim_returns.mean(axis=1)

    var_95 = np.percentile(portfolio_returns, (1 - confidence) * 100)
    cvar_95 = portfolio_returns[portfolio_returns <= var_95].mean()

    return {
        "var_95": round(float(var_95), 4),
        "cvar_95": round(float(cvar_95), 4),
        "max_drawdown_sim": round(float(portfolio_returns.min()), 4),
        "correlation_matrix": correlation_matrix.tolist(),
    }
```

---

## Phase 4 — Catalyst Tracker: Particle Filter

### `backend/catalyst/particle_filter.py`

```python
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class Catalyst:
    name: str
    description: str
    target_date: Optional[str]
    value_impact_if_hit: float    # % change in intrinsic value if catalyst hits
    value_impact_if_miss: float   # % change if catalyst misses (negative)
    prior_probability: float      # Initial belief it will hit


class CatalystParticleFilter:
    """
    Tracks evolving probability estimates for position catalysts.
    Each observation (milestone hit/miss) updates belief via particle filter.
    """

    def __init__(self, catalyst: Catalyst, n_particles: int = 1000):
        self.catalyst = catalyst
        self.n_particles = n_particles
        # Particles represent probability space [0, 1]
        self.particles = np.random.beta(
            catalyst.prior_probability * 10,
            (1 - catalyst.prior_probability) * 10,
            n_particles
        )
        self.weights = np.ones(n_particles) / n_particles

    def update(self, observation: bool, observation_strength: float = 1.0) -> float:
        """
        Update particle weights based on new observation.
        observation: True = positive signal, False = negative signal
        observation_strength: 0-1, how definitive the signal is
        """
        if observation:
            likelihoods = self.particles ** observation_strength
        else:
            likelihoods = (1 - self.particles) ** observation_strength

        self.weights *= likelihoods
        self.weights /= self.weights.sum()

        # Resample if effective sample size too low
        n_eff = 1.0 / np.sum(self.weights ** 2)
        if n_eff < self.n_particles / 2:
            indices = np.random.choice(self.n_particles, self.n_particles, p=self.weights)
            self.particles = self.particles[indices]
            self.weights = np.ones(self.n_particles) / self.n_particles

        return self.get_probability_estimate()

    def get_probability_estimate(self) -> float:
        """Current probability estimate that catalyst will hit."""
        return float(np.average(self.particles, weights=self.weights))

    def get_updated_value_estimate(self, current_intrinsic_value: float) -> float:
        """
        Adjust intrinsic value estimate based on current catalyst probability.
        """
        p = self.get_probability_estimate()
        expected_impact = (
            p * self.catalyst.value_impact_if_hit +
            (1 - p) * self.catalyst.value_impact_if_miss
        )
        return current_intrinsic_value * (1 + expected_impact)
```

---

## Phase 5 — FastAPI Backend

### `backend/main.py`

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np

from backend.screener.screen import run_klarman_screen
from backend.data.yfinance_client import get_fundamentals
from backend.data.edgar_client import get_10yr_financials
from backend.engine.distributions import build_distributions_from_history
from backend.engine.monte_carlo import run_dcf_simulation
from backend.engine.margin_of_safety import calculate_margin_of_safety
from backend.engine.kelly import calculate_position_size

app = FastAPI(title="Klarman Value Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/watchlist")
async def get_watchlist():
    """Run full Klarman screen, return ranked candidates."""
    df = run_klarman_screen()
    return df.head(50).to_dict(orient="records")


@app.get("/analyze/{ticker}")
async def analyze_ticker(ticker: str, portfolio_value: float = 100_000):
    """Full Monte Carlo DCF analysis for a single ticker."""
    yf_data = get_fundamentals(ticker)
    if not yf_data:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}")

    edgar_data = get_10yr_financials(ticker)
    if not edgar_data:
        raise HTTPException(status_code=404, detail=f"No EDGAR history for {ticker}")

    distributions = build_distributions_from_history(edgar_data, yf_data)
    intrinsic_values = run_dcf_simulation(distributions)

    current_price = yf_data.get("price", 0)
    mos = calculate_margin_of_safety(intrinsic_values, current_price)

    kelly = calculate_position_size(
        mos["prob_undervalued"],
        mos["mos_downside"],
        portfolio_value,
        current_price
    )

    return {
        "ticker": ticker,
        "name": yf_data.get("name"),
        "sector": yf_data.get("sector"),
        "distributions": distributions,
        "margin_of_safety": mos,
        "kelly_sizing": kelly,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

## Phase 6 — Wire Frontend to Backend

In `frontend/src/api/client.ts`:

```typescript
const BASE = "http://localhost:8000";

export async function getWatchlist() {
  const res = await fetch(`${BASE}/watchlist`);
  return res.json();
}

export async function analyzeStock(ticker: string, portfolioValue = 100000) {
  const res = await fetch(`${BASE}/analyze/${ticker}?portfolio_value=${portfolioValue}`);
  if (!res.ok) throw new Error(`Analysis failed for ${ticker}`);
  return res.json();
}
```

Replace all hardcoded scenario data in `App.tsx` with calls to these functions. The existing chart components only need the `margin_of_safety.histogram_data` array — everything else slots in by key name.

---

## Docker Compose

```yaml
version: "3.9"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - SEC_IDENTITY=Your Name your@email.com
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend
    command: npm run dev -- --host
```

---

## requirements.txt

```
fastapi==0.110.0
uvicorn==0.29.0
yfinance==0.2.38
edgartools==2.5.0
pandas==2.2.1
numpy==1.26.4
scipy==1.13.0
scikit-learn==1.4.2
xgboost==2.0.3
tqdm==4.66.2
pydantic==2.6.4
pydantic-settings==2.2.1
python-dotenv==1.0.1
apscheduler==3.10.4
sqlalchemy==2.0.29
aiosqlite==0.20.0
pytest==8.1.1
httpx==0.27.0
```

---

## Phase Order for Claude Code

1. **Phase 1** — `config.py`, `yfinance_client.py`, `edgar_client.py`, `distributions.py`, `monte_carlo.py`, `margin_of_safety.py`, `kelly.py` + unit tests
2. **Phase 2** — `screen.py` + test against 20 tickers
3. **Phase 3** — `copula.py` + `tail_risk.py` + tests
4. **Phase 4** — `particle_filter.py` + tests
5. **Phase 5** — `main.py` FastAPI with all routes wired + integration test
6. **Phase 6** — Frontend `client.ts`, replace hardcoded data, verify charts still render

---

## Claude Code Prompts (Use in Order)

```
Phase 1: "Read valueinvesting-klarman.md. Set up the project structure and implement Phase 1: config.py, yfinance_client.py, edgar_client.py, distributions.py, monte_carlo.py, margin_of_safety.py, kelly.py. Write pytest tests for each module. Do not proceed to Phase 2."

Phase 2: "Phase 1 passes. Implement Phase 2: screen.py. Test it against AAPL, MSFT, KO, and 5 other tickers. Print results table."

Phase 3: "Phase 2 passes. Implement Phase 3: copula.py and tail_risk.py. Write tests using synthetic correlated returns data."

Phase 4: "Phase 3 passes. Implement Phase 4: particle_filter.py. Test with a 3-catalyst scenario, simulating 5 observations."

Phase 5: "Phase 4 passes. Implement Phase 5: main.py FastAPI backend with all routes. Write integration tests using httpx."

Phase 6: "Phase 5 passes. Wire the React frontend to the backend API. Replace all hardcoded scenario data in App.tsx with live API calls. Verify all 4 chart tabs render with real data."
```

---

## Notes for Claude Code

- Never hardcode tickers or financial data — always pull live
- EDGAR requires `set_identity()` before any request — do this at module load time
- Monte Carlo arrays are 100K elements — use NumPy vectorized ops only, no Python loops
- Frontend histogram needs `histogram_data` binned to 200 buckets max before rendering — bin in the backend before sending
- Kelly sizing: always cap at `max_position_size` — never return uncapped Kelly
- All money values in USD cents stored as integers in DB, converted to float at API boundary
