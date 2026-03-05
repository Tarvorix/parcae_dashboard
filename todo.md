# Parcae Dashboard — Klarman Value Engine TODO

## Phase 1 — Backend Core ✅ COMPLETE (75/75 tests passing)
- [x] Project directory structure
- [x] backend/config.py
- [x] backend/data/yfinance_client.py
- [x] backend/data/edgar_client.py
- [x] backend/engine/distributions.py
- [x] backend/engine/monte_carlo.py
- [x] backend/engine/margin_of_safety.py
- [x] backend/engine/kelly.py
- [x] backend/requirements.txt
- [x] tests/test_distributions.py (14 tests)
- [x] tests/test_monte_carlo.py (10 tests)
- [x] tests/test_margin_of_safety.py (18 tests)
- [x] tests/test_kelly.py (12 tests)
- [x] tests/test_yfinance_client.py (12 tests)
- [x] tests/test_edgar_client.py (8 tests)
- [x] pytest.ini

## Phase 2 — Screener ✅ COMPLETE (47/47 tests passing)
- [x] backend/screener/screen.py
- [x] tests/test_screen.py (47 tests)
- [x] AAPL, MSFT, KO, JNJ, XOM, WFC all confirmed filtered out by Klarman criteria

## Phase 3 — Portfolio Risk ✅ COMPLETE (58/58 tests passing)
- [x] backend/portfolio/copula.py (Gaussian + Student-t copula)
- [x] backend/portfolio/tail_risk.py (VaR, CVaR, Sharpe, max drawdown, concentration)
- [x] tests/test_copula.py (25 tests)
- [x] tests/test_tail_risk.py (33 tests)

## Phase 4 — Catalyst Tracker ✅ COMPLETE (44/44 tests passing)
- [x] backend/catalyst/particle_filter.py (CatalystParticleFilter + PositionCatalystTracker)
- [x] tests/test_particle_filter.py (44 tests, incl. 3-catalyst / 5-observation scenario)

## Phase 5 — FastAPI Backend ✅ COMPLETE (36/36 tests passing)
- [x] backend/main.py (all routes: /health, /watchlist, /analyze, /portfolio/tail-risk, /watchlist/db, /position catalysts)
- [x] backend/db/models.py (WatchlistEntry, Position, CatalystRecord, CatalystObservation)
- [x] backend/db/database.py (SQLite + SQLAlchemy session management)
- [x] tests/test_api.py (36 integration tests with TestClient + in-memory SQLite)

## Phase 6 — Frontend + Docker ✅ COMPLETE
- [x] frontend/src/types/index.ts (full TypeScript type definitions)
- [x] frontend/src/api/client.ts (all API calls to backend)
- [x] frontend/src/components/ValueDistributionChart.tsx (histogram + MoS overlay)
- [x] frontend/src/components/DownsidePanel.tsx (Klarman checklist tab)
- [x] frontend/src/components/FCFProjections.tsx (FCF bands tab)
- [x] frontend/src/components/DecisionMatrix.tsx (Kelly sizing tab)
- [x] frontend/src/components/Watchlist.tsx (ranked candidates)
- [x] frontend/src/components/PortfolioRisk.tsx (copula tail risk)
- [x] frontend/src/App.tsx (fully wired to live API, no hardcoded data)
- [x] frontend/src/main.tsx
- [x] frontend/index.html
- [x] frontend/package.json + vite.config.ts + tsconfig.json
- [x] frontend/Dockerfile + nginx.conf
- [x] backend/Dockerfile
- [x] docker-compose.yml
- [x] .env.example

## Phase 7 — Streamlit Conversion ✅ COMPLETE
- [x] .streamlit/config.toml (dark theme matching React)
- [x] requirements.txt (root-level for Streamlit Cloud)
- [x] streamlit_ui/theme.py (CSS injection, color constants, Plotly template)
- [x] streamlit_ui/sidebar.py (watchlist, search, screener with caching)
- [x] streamlit_ui/value_distribution.py (200-bin histogram with Plotly)
- [x] streamlit_ui/downside_panel.py (Klarman score + 6-item checklist)
- [x] streamlit_ui/fcf_projections.py (bear/base/bull area chart + table)
- [x] streamlit_ui/decision_matrix.py (Kelly sizing + scenario table)
- [x] streamlit_ui/portfolio_risk.py (copula/historical/positions tabs + radar)
- [x] streamlit_app.py (entry point, direct backend calls, cached analysis)
- [x] Deployment: Streamlit Cloud (free, GitHub-connected, zero config)

## Phase 8 — Data Reliability Fix ✅ COMPLETE
- [x] EDGAR client: added 19 revenue, 7 net income, 4 CFO, 9 CapEx GAAP concept fallbacks
- [x] EDGAR client: lowered minimum year threshold from 5 to 3 (MIN_YEARS_REQUIRED)
- [x] EDGAR client: added `_lookup_first()` helper for fallback chain lookups
- [x] yfinance_client: added `build_fallback_edgar_data()` — synthesizes 5-year history from trailing fundamentals when EDGAR fails
- [x] streamlit_app.py: integrated yfinance fallback in `analyze_ticker()`
- [x] backend/main.py: integrated yfinance fallback in `/analyze/{ticker}` route
- [x] streamlit_ui/theme.py: fixed sidebar disappearing — removed `header {visibility: hidden}` that hid the sidebar toggle button
- [x] tests/test_edgar_client.py: updated 5-year test → 3-year threshold, added test for 3-year data
- [x] tests/test_api.py: updated EDGAR failure test for fallback behavior, added fallback success test

## Phase 9 — Mobile Sidebar Fix ✅ COMPLETE
- [x] streamlit_ui/theme.py: fixed header background from transparent → #030712 so sidebar toggle is visible
- [x] streamlit_ui/theme.py: replaced blanket `[data-testid="stToolbar"] {display: none}` with targeted hide that preserves sidebar toggle
- [x] streamlit_ui/theme.py: added explicit CSS to force sidebar hamburger button visible + tappable on mobile (44px min touch target)
- [x] streamlit_ui/sidebar.py: wrapped ticker search in `st.form(clear_on_submit=True)` so input clears after submission, allowing sequential analyses

## Phase 10 — Screener Show All Scores ✅ COMPLETE
- [x] backend/screener/screen.py: added `filter_results` param to `run_klarman_screen()` — when False, returns all scored stocks with `passes_filter` column
- [x] streamlit_ui/sidebar.py: added "Show all scores" checkbox toggle, `_run_screener_unfiltered()` cached function, pass/fail indicators and score display on candidate cards
- [x] backend/main.py: added `filter_results` query param to `/watchlist` endpoint
- [x] All 84 screener + API tests passing (47 + 37)

## Total: 262/262 tests passing ✅
