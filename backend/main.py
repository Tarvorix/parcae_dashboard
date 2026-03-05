"""
Klarman Value Engine — FastAPI Backend

Routes:
  GET  /health                          → liveness check
  GET  /watchlist                       → run Klarman screen, return top 50
  GET  /analyze/{ticker}               → full Monte Carlo DCF analysis
  GET  /portfolio/tail-risk            → copula tail risk for open positions
  GET  /position/{position_id}/catalysts → catalyst tracker for a position
  POST /position/{position_id}/catalyst/{catalyst_id}/observe
                                       → record a new catalyst observation
  GET  /watchlist/db                   → saved watchlist from DB
  POST /watchlist/{ticker}             → save ticker to watchlist DB
"""

from contextlib import asynccontextmanager
from typing import Optional

import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.catalyst.particle_filter import (
    Catalyst,
    CatalystParticleFilter,
    PositionCatalystTracker,
)
from backend.data.edgar_client import get_10yr_financials
from backend.data.yfinance_client import get_fundamentals, get_price_history
from backend.db.database import get_db, init_db
from backend.db.models import (
    CatalystObservation,
    CatalystRecord,
    Position,
    WatchlistEntry,
)
from backend.engine.distributions import build_distributions_from_history
from backend.engine.kelly import calculate_position_size
from backend.engine.margin_of_safety import calculate_margin_of_safety
from backend.engine.monte_carlo import run_dcf_simulation
from backend.portfolio.copula import gaussian_copula_portfolio_var
from backend.portfolio.tail_risk import calculate_tail_risk_summary
from backend.screener.screen import run_klarman_screen


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Klarman Value Engine",
    description="Seth Klarman / Benjamin Graham-style value investing dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://parcae-dashboard.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ObservationRequest(BaseModel):
    observation: bool = Field(..., description="True = positive signal, False = negative")
    observation_strength: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Signal strength 0–1 (1 = fully conclusive)"
    )
    notes: Optional[str] = None


class AddCatalystRequest(BaseModel):
    name: str
    description: Optional[str] = None
    target_date: Optional[str] = None
    value_impact_if_hit: float = Field(..., gt=-1.0, lt=10.0)
    value_impact_if_miss: float = Field(..., gt=-1.0, lt=1.0)
    prior_probability: float = Field(..., gt=0.0, lt=1.0)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "version": "1.0.0"}


# ── Screener ──────────────────────────────────────────────────────────────────

@app.get("/watchlist", tags=["Screener"])
async def get_watchlist(top_n: int = Query(default=50, ge=1, le=500)):
    """
    Run the full Klarman screen against the S&P 500 and return the top N
    candidates ranked by composite screen score.
    """
    df = run_klarman_screen(show_progress=False)
    if df.empty:
        return []
    return df.head(top_n).to_dict(orient="records")


# ── DCF Analysis ──────────────────────────────────────────────────────────────

@app.get("/analyze/{ticker}", tags=["Analysis"])
async def analyze_ticker(
    ticker: str,
    portfolio_value: float = Query(default=100_000, ge=1_000),
):
    """
    Full Monte Carlo DCF analysis for a single ticker.

    Pulls 10yr financials from SEC EDGAR, builds bear/base/bull distributions,
    runs 100K simulations, and returns intrinsic value distribution, margin of
    safety, and Kelly position sizing.
    """
    ticker = ticker.upper()

    yf_data = get_fundamentals(ticker)
    if not yf_data:
        raise HTTPException(status_code=404, detail=f"No yfinance data for {ticker}")

    edgar_data = get_10yr_financials(ticker)
    if not edgar_data:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient SEC EDGAR history for {ticker} (need ≥ 5 years)"
        )

    distributions = build_distributions_from_history(edgar_data, yf_data)
    intrinsic_values = run_dcf_simulation(distributions)

    current_price = yf_data.get("price") or 0.0
    mos = calculate_margin_of_safety(intrinsic_values, current_price)

    kelly = calculate_position_size(
        mos["prob_undervalued"],
        mos["mos_downside"],
        portfolio_value,
        current_price,
    )

    return {
        "ticker": ticker,
        "name": yf_data.get("name"),
        "sector": yf_data.get("sector"),
        "industry": yf_data.get("industry"),
        "distributions": distributions,
        "margin_of_safety": mos,
        "kelly_sizing": kelly,
    }


# ── Portfolio Tail Risk ───────────────────────────────────────────────────────

@app.get("/portfolio/tail-risk", tags=["Portfolio"])
async def portfolio_tail_risk(
    tickers: str = Query(
        ...,
        description="Comma-separated tickers, e.g. AAPL,MSFT,KO",
    ),
    years: int = Query(default=5, ge=1, le=10),
    confidence: float = Query(default=0.95, ge=0.80, le=0.999),
    db: Session = Depends(get_db),
):
    """
    Gaussian copula tail risk model for a portfolio of tickers.

    Fetches historical monthly returns for each ticker, builds a correlation
    matrix, and runs 50K copula simulations to estimate VaR / CVaR.
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if len(ticker_list) < 2:
        raise HTTPException(
            status_code=422,
            detail="Provide at least 2 tickers for portfolio risk analysis"
        )

    returns_list = []
    valid_tickers = []
    for ticker in ticker_list:
        hist = get_price_history(ticker, years=years)
        if hist.empty or len(hist) < 24:
            continue
        pct = hist["price"].pct_change().dropna().values
        returns_list.append(pct)
        valid_tickers.append(ticker)

    if len(returns_list) < 2:
        raise HTTPException(
            status_code=404,
            detail="Could not retrieve enough price history for at least 2 tickers"
        )

    # Align lengths (trim to shortest series)
    min_len = min(len(r) for r in returns_list)
    returns_matrix = np.array([r[-min_len:] for r in returns_list])

    # Empirical correlation matrix
    corr = np.corrcoef(returns_matrix)

    # Clamp to positive semi-definite (add small diagonal if needed)
    eigvals = np.linalg.eigvalsh(corr)
    if eigvals.min() < 0:
        corr += np.eye(len(valid_tickers)) * (abs(eigvals.min()) + 1e-6)
        d = np.sqrt(np.diag(corr))
        corr = corr / np.outer(d, d)

    copula_result = gaussian_copula_portfolio_var(
        returns_matrix, corr, confidence=confidence, n_simulations=50_000
    )

    hist_result = calculate_tail_risk_summary(
        returns_matrix, confidence=confidence
    )

    return {
        "tickers": valid_tickers,
        "copula": copula_result,
        "historical": hist_result,
    }


# ── Watchlist DB ──────────────────────────────────────────────────────────────

@app.get("/watchlist/db", tags=["Watchlist DB"])
async def get_saved_watchlist(db: Session = Depends(get_db)):
    """Return all saved watchlist entries from the database."""
    entries = db.query(WatchlistEntry).order_by(WatchlistEntry.klarman_score.desc()).all()
    return [
        {
            "id": e.id,
            "ticker": e.ticker,
            "name": e.name,
            "sector": e.sector,
            "klarman_score": e.klarman_score,
            "mos_downside": e.mos_downside,
            "screen_score": e.screen_score,
            "last_analyzed_at": e.last_analyzed_at.isoformat() if e.last_analyzed_at else None,
        }
        for e in entries
    ]


@app.post("/watchlist/{ticker}", tags=["Watchlist DB"], status_code=201)
async def add_to_watchlist(ticker: str, db: Session = Depends(get_db)):
    """Save a ticker to the watchlist database (upsert)."""
    ticker = ticker.upper()
    existing = db.query(WatchlistEntry).filter(WatchlistEntry.ticker == ticker).first()
    if existing:
        return {"message": f"{ticker} already in watchlist", "id": existing.id}

    entry = WatchlistEntry(ticker=ticker)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"message": f"{ticker} added to watchlist", "id": entry.id}


# ── Position Catalyst Tracker ─────────────────────────────────────────────────

@app.get("/position/{position_id}/catalysts", tags=["Catalysts"])
async def get_position_catalysts(position_id: int, db: Session = Depends(get_db)):
    """Return all catalysts for a position with their current probability estimates."""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail=f"Position {position_id} not found")

    catalysts = (
        db.query(CatalystRecord)
        .filter(CatalystRecord.position_id == position_id)
        .all()
    )

    return [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "target_date": c.target_date,
            "prior_probability": c.prior_probability,
            "current_probability": c.current_probability,
            "value_impact_if_hit": c.value_impact_if_hit,
            "value_impact_if_miss": c.value_impact_if_miss,
            "n_observations": c.n_observations,
            "is_resolved": c.is_resolved,
            "resolved_outcome": c.resolved_outcome,
        }
        for c in catalysts
    ]


@app.post("/position/{position_id}/catalyst", tags=["Catalysts"], status_code=201)
async def add_catalyst(
    position_id: int,
    req: AddCatalystRequest,
    db: Session = Depends(get_db),
):
    """Add a new catalyst to a position."""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail=f"Position {position_id} not found")

    catalyst = CatalystRecord(
        position_id=position_id,
        name=req.name,
        description=req.description,
        target_date=req.target_date,
        value_impact_if_hit=req.value_impact_if_hit,
        value_impact_if_miss=req.value_impact_if_miss,
        prior_probability=req.prior_probability,
        current_probability=req.prior_probability,
    )
    db.add(catalyst)
    db.commit()
    db.refresh(catalyst)
    return {"id": catalyst.id, "message": "Catalyst added"}


@app.post(
    "/position/{position_id}/catalyst/{catalyst_id}/observe",
    tags=["Catalysts"],
)
async def record_catalyst_observation(
    position_id: int,
    catalyst_id: int,
    req: ObservationRequest,
    db: Session = Depends(get_db),
):
    """
    Record a new observation for a catalyst and update its probability via
    the particle filter.

    Replays all prior observations to rebuild the particle filter state,
    then applies the new observation.
    """
    catalyst_record = (
        db.query(CatalystRecord)
        .filter(
            CatalystRecord.id == catalyst_id,
            CatalystRecord.position_id == position_id,
        )
        .first()
    )
    if not catalyst_record:
        raise HTTPException(
            status_code=404,
            detail=f"Catalyst {catalyst_id} not found for position {position_id}"
        )
    if catalyst_record.is_resolved:
        raise HTTPException(
            status_code=409,
            detail="Catalyst is already resolved — no further observations allowed"
        )

    # Rebuild particle filter from full observation history
    catalyst_obj = Catalyst(
        name=catalyst_record.name,
        description=catalyst_record.description or "",
        target_date=catalyst_record.target_date,
        value_impact_if_hit=catalyst_record.value_impact_if_hit,
        value_impact_if_miss=catalyst_record.value_impact_if_miss,
        prior_probability=catalyst_record.prior_probability,
    )
    pf = CatalystParticleFilter(catalyst_obj, n_particles=2_000)

    prior_observations = (
        db.query(CatalystObservation)
        .filter(CatalystObservation.catalyst_id == catalyst_id)
        .order_by(CatalystObservation.observed_at)
        .all()
    )
    for obs in prior_observations:
        pf.update(obs.observation, obs.observation_strength)

    # Apply the new observation
    new_prob = pf.update(req.observation, req.observation_strength)

    # Persist the observation
    obs_record = CatalystObservation(
        catalyst_id=catalyst_id,
        observation=req.observation,
        observation_strength=req.observation_strength,
        probability_after=new_prob,
        notes=req.notes,
    )
    db.add(obs_record)

    # Update the catalyst record
    catalyst_record.current_probability = new_prob
    catalyst_record.n_observations = len(prior_observations) + 1

    db.commit()

    return {
        "catalyst_id": catalyst_id,
        "updated_probability": round(new_prob, 6),
        "n_observations": catalyst_record.n_observations,
        "distribution": pf.get_probability_distribution(),
    }
