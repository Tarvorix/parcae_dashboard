"""
SQLAlchemy session management for SQLite (upgradeable to Postgres).
"""

import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///./parcae.db"
)

# Render provides postgres:// but SQLAlchemy requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a database session, closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_db() -> None:
    """
    Add new columns to existing tables that were created before the column existed.
    Since we use create_all (not Alembic), new columns on existing tables
    need explicit ALTER TABLE.
    """
    insp = inspect(engine)
    if not insp.has_table("watchlist"):
        return  # Table doesn't exist yet — create_all will handle it

    existing_cols = {c["name"] for c in insp.get_columns("watchlist")}
    new_cols = {
        "piotroski_f_score": "INTEGER",
        "altman_z_score": "REAL",
        "altman_zone": "VARCHAR(16)",
        "beneish_m_score": "REAL",
        "epv_per_share_cents": "INTEGER",
        "ncav_per_share_cents": "INTEGER",
    }

    with engine.begin() as conn:
        for col, type_ in new_cols.items():
            if col not in existing_cols:
                conn.execute(text(f"ALTER TABLE watchlist ADD COLUMN {col} {type_}"))


def init_db() -> None:
    """Create all tables and run migrations.  Call once at startup."""
    from backend.db import models  # noqa: F401 — import to register models
    Base.metadata.create_all(bind=engine)
    migrate_db()
