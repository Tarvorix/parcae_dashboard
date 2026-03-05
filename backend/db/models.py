"""
SQLAlchemy ORM models.

Money values: stored as integer cents (USD × 100) to avoid floating-point
accumulation errors.  Converted to float at the API boundary.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey,
    Integer, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Watchlist candidate ───────────────────────────────────────────────────────

class WatchlistEntry(Base):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(256))
    sector: Mapped[Optional[str]] = mapped_column(String(128))
    industry: Mapped[Optional[str]] = mapped_column(String(128))

    # Screening metrics
    price_cents: Mapped[Optional[int]] = mapped_column(Integer)   # USD × 100
    market_cap_cents: Mapped[Optional[int]] = mapped_column(Integer)
    ev_ebit: Mapped[Optional[float]] = mapped_column(Float)
    fcf_yield_pct: Mapped[Optional[float]] = mapped_column(Float)
    price_tangible_book: Mapped[Optional[float]] = mapped_column(Float)
    screen_score: Mapped[Optional[float]] = mapped_column(Float)

    # Klarman analysis (populated after Monte Carlo run)
    klarman_score: Mapped[Optional[float]] = mapped_column(Float)
    mos_downside: Mapped[Optional[float]] = mapped_column(Float)
    prob_undervalued: Mapped[Optional[float]] = mapped_column(Float)
    p25_value_cents: Mapped[Optional[int]] = mapped_column(Integer)
    p50_value_cents: Mapped[Optional[int]] = mapped_column(Integer)

    last_screened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    # Relationships
    positions: Mapped[list["Position"]] = relationship("Position", back_populates="watchlist_entry")


# ── Open position ─────────────────────────────────────────────────────────────

class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    watchlist_id: Mapped[Optional[int]] = mapped_column(ForeignKey("watchlist.id"), nullable=True)
    ticker: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(256))

    # Position sizing
    shares: Mapped[int] = mapped_column(Integer, default=0)
    avg_cost_cents: Mapped[int] = mapped_column(Integer, default=0)   # per share, USD × 100
    portfolio_value_cents: Mapped[int] = mapped_column(Integer, default=0)

    # Kelly allocation at entry
    kelly_fractional_pct: Mapped[Optional[float]] = mapped_column(Float)
    dollar_amount_cents: Mapped[Optional[int]] = mapped_column(Integer)

    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # Relationships
    watchlist_entry: Mapped[Optional["WatchlistEntry"]] = relationship(
        "WatchlistEntry", back_populates="positions"
    )
    catalysts: Mapped[list["CatalystRecord"]] = relationship(
        "CatalystRecord", back_populates="position"
    )


# ── Catalyst record ───────────────────────────────────────────────────────────

class CatalystRecord(Base):
    __tablename__ = "catalysts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    position_id: Mapped[int] = mapped_column(ForeignKey("positions.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    target_date: Mapped[Optional[str]] = mapped_column(String(16))   # ISO date string

    value_impact_if_hit: Mapped[float] = mapped_column(Float, nullable=False)
    value_impact_if_miss: Mapped[float] = mapped_column(Float, nullable=False)
    prior_probability: Mapped[float] = mapped_column(Float, nullable=False)
    current_probability: Mapped[Optional[float]] = mapped_column(Float)

    n_observations: Mapped[int] = mapped_column(Integer, default=0)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_outcome: Mapped[Optional[bool]] = mapped_column(Boolean)   # True=hit, False=miss

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    # Relationships
    position: Mapped["Position"] = relationship("Position", back_populates="catalysts")
    observations: Mapped[list["CatalystObservation"]] = relationship(
        "CatalystObservation", back_populates="catalyst"
    )


# ── Catalyst observation log ──────────────────────────────────────────────────

class CatalystObservation(Base):
    __tablename__ = "catalyst_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    catalyst_id: Mapped[int] = mapped_column(ForeignKey("catalysts.id"), nullable=False, index=True)

    observation: Mapped[bool] = mapped_column(Boolean, nullable=False)   # True=positive
    observation_strength: Mapped[float] = mapped_column(Float, nullable=False)
    probability_after: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # Relationships
    catalyst: Mapped["CatalystRecord"] = relationship("CatalystRecord", back_populates="observations")
