"""
Integration tests for backend/main.py (FastAPI)

Uses httpx.AsyncClient with an in-memory SQLite database.
All external calls (yfinance, EDGAR, screener) are mocked.

Coverage:
  - /health
  - /watchlist (screener)
  - /analyze/{ticker}
  - /portfolio/tail-risk
  - /watchlist/db  (save + retrieve)
  - /position/{id}/catalysts
  - /position/{id}/catalyst  (create)
  - /position/{id}/catalyst/{id}/observe
"""

import numpy as np
import pytest
import httpx
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.database import Base, get_db
from backend.db.models import Position, WatchlistEntry, CatalystRecord
from backend.main import app


# ── In-memory SQLite test DB ──────────────────────────────────────────────────
# StaticPool ensures all connections share the same in-memory database instance.

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# ── Mock data ─────────────────────────────────────────────────────────────────

MOCK_YF_DATA = {
    "ticker": "DEEPV",
    "name": "Deep Value Corp",
    "price": 45.0,
    "market_cap": 1_000_000_000,
    "enterprise_value": 900_000_000,
    "ebit": 120_000_000,
    "ebitda": 150_000_000,
    "free_cashflow": 90_000_000,
    "total_revenue": 500_000_000,
    "tangible_book_value": 40.0,
    "shares_outstanding": 22_000_000,
    "total_debt": 200_000_000,
    "cash": 100_000_000,
    "sector": "Industrials",
    "industry": "Manufacturing",
}

MOCK_EDGAR_DATA = {
    "revenues": [400e6, 420e6, 440e6, 460e6, 480e6, 500e6],
    "net_incomes": [40e6, 42e6, 44e6, 46e6, 48e6, 50e6],
    "fcfs": [32e6, 34e6, 36e6, 38e6, 40e6, 42e6],
    "margins": [0.10, 0.10, 0.10, 0.10, 0.10, 0.10],
    "capex": [16e6, 17e6, 18e6, 19e6, 20e6, 21e6],
}

MOCK_SCREEN_ROWS = [
    {
        "ticker": "DEEPV",
        "name": "Deep Value Corp",
        "price": 45.0,
        "market_cap": 1_000_000_000,
        "ev_ebit": 7.5,
        "fcf_yield_pct": 9.0,
        "price_tangible_book": 1.1,
        "net_debt_ebitda": 0.7,
        "sector": "Industrials",
        "industry": "Manufacturing",
        "screen_score": 0.42,
    }
]


def make_mock_price_history(ticker: str, years: int = 5):
    import pandas as pd
    prices = np.linspace(35.0, 45.0, 72)
    idx = pd.date_range("2019-01-01", periods=72, freq="ME")
    return pd.DataFrame({"price": prices}, index=idx)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_db():
    """Wipe and recreate all tables before each test for isolation."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seeded_position(db):
    """Insert a WatchlistEntry and Position, return position.id."""
    entry = WatchlistEntry(ticker="DEEPV", name="Deep Value Corp")
    db.add(entry)
    db.commit()

    pos = Position(
        ticker="DEEPV",
        name="Deep Value Corp",
        shares=100,
        avg_cost_cents=4500,
        portfolio_value_cents=100_000_00,
    )
    db.add(pos)
    db.commit()
    db.refresh(pos)
    return pos.id


@pytest.fixture
def seeded_catalyst(db, seeded_position):
    """Insert a catalyst on the seeded position, return (position_id, catalyst_id)."""
    cat = CatalystRecord(
        position_id=seeded_position,
        name="Merger Close",
        description="Acquisition expected Q3",
        target_date="2025-09-30",
        value_impact_if_hit=0.30,
        value_impact_if_miss=-0.15,
        prior_probability=0.55,
        current_probability=0.55,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return seeded_position, cat.id


# ── /health ────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_status_ok(self, client):
        r = client.get("/health")
        assert r.json()["status"] == "ok"

    def test_version_present(self, client):
        r = client.get("/health")
        assert "version" in r.json()


# ── /watchlist ────────────────────────────────────────────────────────────────

class TestGetWatchlist:
    @patch("backend.main.run_klarman_screen")
    def test_returns_200(self, mock_screen, client):
        import pandas as pd
        mock_screen.return_value = pd.DataFrame(MOCK_SCREEN_ROWS)
        r = client.get("/watchlist")
        assert r.status_code == 200

    @patch("backend.main.run_klarman_screen")
    def test_returns_list(self, mock_screen, client):
        import pandas as pd
        mock_screen.return_value = pd.DataFrame(MOCK_SCREEN_ROWS)
        r = client.get("/watchlist")
        assert isinstance(r.json(), list)

    @patch("backend.main.run_klarman_screen")
    def test_returns_empty_list_when_no_candidates(self, mock_screen, client):
        import pandas as pd
        mock_screen.return_value = pd.DataFrame()
        r = client.get("/watchlist")
        assert r.status_code == 200
        assert r.json() == []

    @patch("backend.main.run_klarman_screen")
    def test_top_n_parameter(self, mock_screen, client):
        import pandas as pd
        rows = MOCK_SCREEN_ROWS * 10
        mock_screen.return_value = pd.DataFrame(rows)
        r = client.get("/watchlist?top_n=3")
        assert len(r.json()) <= 3


# ── /analyze/{ticker} ─────────────────────────────────────────────────────────

class TestAnalyzeTicker:
    @patch("backend.main.get_10yr_financials", return_value=MOCK_EDGAR_DATA)
    @patch("backend.main.get_fundamentals", return_value=MOCK_YF_DATA)
    def test_returns_200(self, _yf, _edgar, client):
        r = client.get("/analyze/DEEPV")
        assert r.status_code == 200

    @patch("backend.main.get_10yr_financials", return_value=MOCK_EDGAR_DATA)
    @patch("backend.main.get_fundamentals", return_value=MOCK_YF_DATA)
    def test_required_keys_present(self, _yf, _edgar, client):
        r = client.get("/analyze/DEEPV")
        data = r.json()
        assert {"ticker", "name", "sector", "distributions",
                "margin_of_safety", "kelly_sizing"}.issubset(data.keys())

    @patch("backend.main.get_10yr_financials", return_value=MOCK_EDGAR_DATA)
    @patch("backend.main.get_fundamentals", return_value=MOCK_YF_DATA)
    def test_ticker_uppercased(self, _yf, _edgar, client):
        r = client.get("/analyze/deepv")
        assert r.json()["ticker"] == "DEEPV"

    @patch("backend.main.get_fundamentals", return_value=None)
    def test_404_when_no_yfinance_data(self, _yf, client):
        r = client.get("/analyze/MISSING")
        assert r.status_code == 404

    @patch("backend.main.get_10yr_financials", return_value=None)
    @patch("backend.main.get_fundamentals", return_value=MOCK_YF_DATA)
    def test_404_when_no_edgar_data(self, _yf, _edgar, client):
        r = client.get("/analyze/NOEDGAR")
        assert r.status_code == 404

    @patch("backend.main.get_10yr_financials", return_value=MOCK_EDGAR_DATA)
    @patch("backend.main.get_fundamentals", return_value=MOCK_YF_DATA)
    def test_histogram_data_present(self, _yf, _edgar, client):
        r = client.get("/analyze/DEEPV")
        assert "histogram_data" in r.json()["margin_of_safety"]

    @patch("backend.main.get_10yr_financials", return_value=MOCK_EDGAR_DATA)
    @patch("backend.main.get_fundamentals", return_value=MOCK_YF_DATA)
    def test_portfolio_value_parameter(self, _yf, _edgar, client):
        r = client.get("/analyze/DEEPV?portfolio_value=500000")
        assert r.status_code == 200
        kelly = r.json()["kelly_sizing"]
        # Dollar amount should scale with portfolio value
        assert kelly["dollar_amount"] >= 0


# ── /portfolio/tail-risk ──────────────────────────────────────────────────────

class TestPortfolioTailRisk:
    @patch("backend.main.get_price_history", side_effect=make_mock_price_history)
    def test_returns_200(self, _hist, client):
        r = client.get("/portfolio/tail-risk?tickers=DEEPV,VALUE")
        assert r.status_code == 200

    @patch("backend.main.get_price_history", side_effect=make_mock_price_history)
    def test_required_keys_present(self, _hist, client):
        r = client.get("/portfolio/tail-risk?tickers=DEEPV,VALUE")
        data = r.json()
        assert {"tickers", "copula", "historical"}.issubset(data.keys())

    @patch("backend.main.get_price_history", side_effect=make_mock_price_history)
    def test_tickers_in_response(self, _hist, client):
        r = client.get("/portfolio/tail-risk?tickers=DEEPV,VALUE")
        assert set(r.json()["tickers"]) == {"DEEPV", "VALUE"}

    def test_422_when_single_ticker(self, client):
        r = client.get("/portfolio/tail-risk?tickers=DEEPV")
        assert r.status_code == 422

    @patch("backend.main.get_price_history", return_value=__import__("pandas").DataFrame())
    def test_404_when_no_price_history(self, _hist, client):
        r = client.get("/portfolio/tail-risk?tickers=A,B")
        assert r.status_code == 404


# ── /watchlist/db ─────────────────────────────────────────────────────────────

class TestWatchlistDb:
    def test_empty_list_on_fresh_db(self, client):
        r = client.get("/watchlist/db")
        assert r.status_code == 200
        assert r.json() == []

    def test_add_ticker_returns_201(self, client):
        r = client.post("/watchlist/DEEPV")
        assert r.status_code == 201

    def test_add_ticker_then_retrieve(self, client):
        client.post("/watchlist/DEEPV")
        r = client.get("/watchlist/db")
        tickers = [e["ticker"] for e in r.json()]
        assert "DEEPV" in tickers

    def test_add_duplicate_does_not_error(self, client):
        client.post("/watchlist/DEEPV")
        r = client.post("/watchlist/DEEPV")
        assert r.status_code == 201

    def test_ticker_uppercased_on_save(self, client):
        client.post("/watchlist/deepv")
        r = client.get("/watchlist/db")
        assert r.json()[0]["ticker"] == "DEEPV"


# ── /position/{id}/catalysts ──────────────────────────────────────────────────

class TestGetPositionCatalysts:
    def test_404_for_unknown_position(self, client):
        r = client.get("/position/9999/catalysts")
        assert r.status_code == 404

    def test_returns_empty_list_for_position_with_no_catalysts(
        self, client, seeded_position
    ):
        r = client.get(f"/position/{seeded_position}/catalysts")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_catalysts_after_adding(self, client, seeded_catalyst):
        position_id, _ = seeded_catalyst
        r = client.get(f"/position/{position_id}/catalysts")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_catalyst_fields_present(self, client, seeded_catalyst):
        position_id, _ = seeded_catalyst
        r = client.get(f"/position/{position_id}/catalysts")
        entry = r.json()[0]
        assert {
            "id", "name", "description", "target_date",
            "prior_probability", "current_probability",
            "value_impact_if_hit", "value_impact_if_miss",
            "n_observations", "is_resolved",
        }.issubset(entry.keys())


# ── /position/{id}/catalyst  (POST) ──────────────────────────────────────────

class TestAddCatalyst:
    def test_returns_201(self, client, seeded_position):
        r = client.post(
            f"/position/{seeded_position}/catalyst",
            json={
                "name": "FDA Approval",
                "description": "Phase 3 result",
                "prior_probability": 0.60,
                "value_impact_if_hit": 0.35,
                "value_impact_if_miss": -0.20,
            },
        )
        assert r.status_code == 201

    def test_404_for_unknown_position(self, client):
        r = client.post(
            "/position/9999/catalyst",
            json={
                "name": "Test",
                "prior_probability": 0.5,
                "value_impact_if_hit": 0.1,
                "value_impact_if_miss": -0.1,
            },
        )
        assert r.status_code == 404


# ── /position/{id}/catalyst/{id}/observe ─────────────────────────────────────

class TestRecordCatalystObservation:
    def test_returns_200(self, client, seeded_catalyst):
        position_id, catalyst_id = seeded_catalyst
        r = client.post(
            f"/position/{position_id}/catalyst/{catalyst_id}/observe",
            json={"observation": True, "observation_strength": 0.8},
        )
        assert r.status_code == 200

    def test_response_has_required_keys(self, client, seeded_catalyst):
        position_id, catalyst_id = seeded_catalyst
        r = client.post(
            f"/position/{position_id}/catalyst/{catalyst_id}/observe",
            json={"observation": True, "observation_strength": 0.8},
        )
        data = r.json()
        assert {"catalyst_id", "updated_probability", "n_observations", "distribution"}.issubset(
            data.keys()
        )

    def test_probability_changes_after_observation(self, client, seeded_catalyst):
        position_id, catalyst_id = seeded_catalyst
        r = client.post(
            f"/position/{position_id}/catalyst/{catalyst_id}/observe",
            json={"observation": True, "observation_strength": 1.0},
        )
        # Prior was 0.55; strong positive signal should push it higher
        updated_prob = r.json()["updated_probability"]
        assert updated_prob > 0.55

    def test_n_observations_increments(self, client, seeded_catalyst):
        position_id, catalyst_id = seeded_catalyst
        for i in range(3):
            client.post(
                f"/position/{position_id}/catalyst/{catalyst_id}/observe",
                json={"observation": True, "observation_strength": 0.5},
            )
        r = client.post(
            f"/position/{position_id}/catalyst/{catalyst_id}/observe",
            json={"observation": False, "observation_strength": 0.5},
        )
        assert r.json()["n_observations"] == 4

    def test_404_for_unknown_catalyst(self, client, seeded_position):
        r = client.post(
            f"/position/{seeded_position}/catalyst/9999/observe",
            json={"observation": True, "observation_strength": 0.7},
        )
        assert r.status_code == 404

    def test_probability_in_valid_range(self, client, seeded_catalyst):
        position_id, catalyst_id = seeded_catalyst
        r = client.post(
            f"/position/{position_id}/catalyst/{catalyst_id}/observe",
            json={"observation": False, "observation_strength": 0.9},
        )
        p = r.json()["updated_probability"]
        assert 0.0 <= p <= 1.0
