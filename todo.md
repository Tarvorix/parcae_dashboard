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

## Phase 11 — S&P Mid-Cap 400 & Small-Cap 600 Universe Support ✅ COMPLETE
- [x] backend/data/yfinance_client.py: added `_scrape_sp_tickers()` shared helper, `get_sp400_tickers()`, `get_sp600_tickers()`
- [x] backend/screener/screen.py: added `UNIVERSE_OPTIONS`, `get_universe_tickers()`, and `universe` param to `run_klarman_screen()`
- [x] streamlit_ui/sidebar.py: added universe selector dropdown (S&P 500 / Mid-Cap 400 / Small-Cap 600 / S&P 1500 All), auto-reruns on universe change
- [x] backend/main.py: added `universe` query param to `/watchlist` endpoint with validation
- [x] All 84 screener + API tests passing (47 + 37)

## Phase 12 — Fix Scoring Display & Add Russell 2000 (IN PROGRESS)

### Problem
- Screener shows no scores for any stock, even with "Show all scores" enabled
- Root causes:
  1. `screen.py:176-178` skips stocks if ANY of 3 metrics is None
  2. `tangible_book_value` often returns None from yfinance for many companies
  3. Wikipedia ticker scraping has no error handling — crashes silently
  4. Klarman hard filters too strict for current market (P/TBV ≤ 1.2, FCF ≥ 7%)
  5. No Russell 2000 universe option

### Tasks
- [x] Fix screen.py — allow partial scores from available metrics in unfiltered mode
- [x] Fix yfinance_client.py — add tangible_book_value fallbacks + ticker scraping error handling
- [x] Add Russell 2000 via iShares IWM ETF (ported from stocks repo)
- [x] Update sidebar with Russell 2000 universe option
- [x] Move screener results from sidebar to main screen as ranked table
- [x] Add screener_view.py — clickable ranked rows, score-colored, PASS/FAIL badges
- [x] Add "Back to Screener" navigation from analysis view
- [x] Slim sidebar to controls only (search, universe, run button, portfolio $)
- [x] Commit and push

## Phase 12 — COMPLETE ✅ (263/263 tests passing)

---

## Phase 13 — Data Layer Foundation ✅ COMPLETE (269/269 tests passing)
- [x] Add 13 new fields to get_fundamentals() in yfinance_client.py
- [x] Add None placeholders for new balance sheet lists in build_fallback_edgar_data()
- [x] Add 11 new XBRL concept chains to edgar_client.py
- [x] Extract balance sheet data in get_10yr_financials() loop (tenk.balance_sheet)
- [x] Add 12 new keys to get_10yr_financials() return dict
- [x] Update tests/test_yfinance_client.py — 3 new tests (balance_sheet_keys, working_capital_computed, working_capital_none)
- [x] Update tests/test_edgar_client.py — 3 new tests (balance_sheet_keys, lists_same_length, total_assets_values)

## Phase 14 — EPV + NCAV Valuation Anchors ✅ COMPLETE (306/306 tests passing)
- [x] Create backend/engine/valuation_anchors.py (calculate_epv, calculate_ncav, calculate_valuation_anchors)
- [x] Add config fields (default_cost_of_equity=0.10, default_cost_of_debt=0.05, default_tax_rate=0.21)
- [x] Add valuation_anchors to /analyze/{ticker} response in main.py
- [x] Create tests/test_valuation_anchors.py (37 tests: 19 EPV + 13 NCAV + 5 composite)
- [x] Update tests/test_api.py — valuation_anchors in required keys
- [x] Add epv_per_share_cents and ncav_per_share_cents to WatchlistEntry model
- [x] Frontend React: ValuationAnchors.tsx (bar chart comparing NCAV/Price/DCF/EPV + detail cards)
- [x] Frontend React: Added Valuation Anchors tab to App.tsx
- [x] Streamlit: streamlit_ui/valuation_anchors.py (Plotly bar chart + EPV/NCAV detail cards)
- [x] Streamlit: Added Valuation Anchors tab to streamlit_app.py

## Phase 15 — Quality & Distress Scoring ✅ COMPLETE (350/350 tests passing)
- [x] Create backend/engine/quality_scores.py (piotroski, altman, beneish, composite)
- [x] Add config fields (min_piotroski=5, altman thresholds 2.99/1.81, beneish threshold -1.78)
- [x] Add altman_z_score + altman_zone columns to screener in screen.py
- [x] Add quality_scores to /analyze/{ticker} response in main.py
- [x] Add quality score columns to WatchlistEntry model (piotroski_f_score, altman_z_score, altman_zone, beneish_m_score)
- [x] Create tests/test_quality_scores.py (44 tests)
- [x] Update tests/test_screen.py for altman columns (+4 tests)
- [x] Add QualityScores types to frontend/src/types/index.ts (PiotroskiScore, AltmanZScore, BeneishMScore)
- [x] Create frontend/src/components/QualityPanel.tsx (3 score cards + Piotroski checklist + Altman table + Beneish table)
- [x] Add Quality / Distress tab to App.tsx
- [x] Create streamlit_ui/quality_panel.py (3 score cards + expandable sections)
- [x] Add Quality / Distress tab to streamlit_app.py

## Phase 16 — Insider & Institutional Flow Signals ✅ COMPLETE (383/383 tests passing)
- [x] Create backend/data/insider_client.py (Form 4 XML parsing, insider transactions, institutional holdings, short interest, composite)
- [x] Add flow_signals to /analyze/{ticker} response in main.py
- [x] NOTABLE_VALUE_INVESTORS list (15 firms: Baupost, Berkshire, Greenlight, etc.)
- [x] Cluster buy detection (3+ unique insiders within 90 days)
- [x] Create tests/test_insider_client.py (33 tests)
- [x] Add FlowSignals types to frontend/src/types/index.ts (InsiderTransaction, InsiderSummary, InstitutionalHolder, etc.)
- [x] Create frontend/src/components/FlowSignals.tsx (4 summary cards + insider table + institutional table)
- [x] Add Flow Signals tab to App.tsx
- [x] Create streamlit_ui/flow_signals.py (summary cards + tables + badges)
- [x] Add Flow Signals tab to streamlit_app.py

## Phase 17 — Backtesting Framework ✅ COMPLETE (410/410 tests passing)
- [x] Create backend/backtest/__init__.py
- [x] Create backend/backtest/engine.py (run_backtest with CAGR, Sharpe, drawdown, Calmar, win_rate, alpha)
- [x] Add POST /backtest endpoint to main.py (runs screener + backtest pipeline)
- [x] Add BacktestResult model to db/models.py (universe, years, top_n, weighting, all metrics, result_json)
- [x] Create tests/test_backtest.py (27 tests)
- [x] Add BacktestResult types to frontend/src/types/index.ts (BacktestMetrics, BacktestMonthlyPoint, BacktestResult)
- [x] Add runBacktest() to frontend/src/api/client.ts
- [x] Create frontend/src/components/BacktestPanel.tsx (Recharts equity curve + metric cards + final values)
- [x] Create streamlit_ui/backtest_view.py (Plotly equity curve + 7 metric cards + tickers held)
- [x] Add backtest controls to streamlit_ui/sidebar.py (years, top_n, weighting, Run Backtest button)
- [x] Add backtest section to streamlit_app.py

## Phase 18 — DB Migration + Integration Polish ✅ COMPLETE (414/414 tests passing)
- [x] Add migrate_db() to backend/db/database.py (ALTER TABLE for 6 new WatchlistEntry columns)
- [x] Update init_db() to call migrate_db() after create_all()
- [x] Update tests/test_api.py (quality_scores + flow_signals in required keys)
- [x] Update tests/test_screen.py (altman_z_score + altman_zone in required columns)
- [x] All 414 tests passing

## Phase 19 — Screener Data Fetch Reliability Fix (IN PROGRESS)

### Problem
- Screener returns 0 results on all universes, even with "Show all scores" enabled
- Root cause: `get_fundamentals()` silently catches ALL exceptions (bare `except Exception: return None`)
- On Streamlit Cloud, Yahoo Finance rate-limits or blocks requests from cloud server IPs
- Every ticker fails silently → empty results → "No screener results yet"

### Tasks
- [x] Add retry logic with exponential backoff to yfinance data fetching (3 retries: 1s, 2s, 4s)
- [x] Add `fast_info` fallback for price/market_cap when `.info` returns sparse data
- [x] Add logging to `get_fundamentals()` so failures are visible in Streamlit Cloud logs
- [x] Add progress bar + scored/failed counter to screener UI (real-time feedback)
- [x] Relax `get_fundamentals()` to only require `price` (not `total_revenue`) — allows partial scoring
- [x] Add `progress_callback` to `run_klarman_screen()` for UI integration
- [x] Add diagnostic logging to `run_klarman_screen()` (fetch_ok/fetch_fail counts)
- [x] Configure Python logging in `streamlit_app.py` for Streamlit Cloud log visibility
- [x] Update todo.md
- [ ] Commit and push

## Total: 414/414 tests passing ✅
