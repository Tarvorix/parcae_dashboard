"""
Sidebar: Controls for universe selection, screener execution, manual ticker search,
and portfolio value input.  Screener results are rendered on the main screen via
screener_view.py.
"""

import streamlit as st
import logging
from backend.screener.screen import run_klarman_screen
from streamlit_ui.theme import COLORS, fmt_dollar

logger = logging.getLogger(__name__)

UNIVERSE_LABELS = {
    "S&P 500": "sp500",
    "S&P Mid-Cap 400": "sp400",
    "S&P Small-Cap 600": "sp600",
    "Russell 2000": "russell2000",
    "S&P 1500 (All)": "all",
}


def _run_screener_with_progress(top_n: int, universe: str, filter_results: bool) -> list[dict]:
    """
    Run the Klarman screen with a Streamlit progress bar for real-time feedback.
    NOT cached — caching is handled at the caller level via session state staleness checks.
    """
    progress_bar = st.progress(0, text="Initializing screener…")
    status_text = st.empty()

    scored_count = [0]
    fail_count = [0]

    def on_progress(current, total, ticker, status):
        pct = current / total if total > 0 else 0
        progress_bar.progress(pct, text=f"Screening {current}/{total}: {ticker}")
        if status == "scored":
            scored_count[0] += 1
        elif status == "fail":
            fail_count[0] += 1
        # Update status every 10 tickers to avoid too many rerenders
        if current % 10 == 0 or current == total:
            status_text.markdown(
                f"<div style='font-size:0.7rem;color:{COLORS['gray_500']};'>"
                f"Scored: {scored_count[0]} · Failed: {fail_count[0]} · Progress: {current}/{total}</div>",
                unsafe_allow_html=True,
            )

    df = run_klarman_screen(
        show_progress=False,
        filter_results=filter_results,
        universe=universe,
        progress_callback=on_progress,
    )

    progress_bar.empty()

    if df.empty:
        status_text.markdown(
            f"<div style='font-size:0.75rem;color:{COLORS['red']};'>"
            f"Screener returned 0 results (fetched: {scored_count[0] + fail_count[0] - fail_count[0]}, "
            f"failed: {fail_count[0]}). Yahoo Finance may be rate-limiting this server.</div>",
            unsafe_allow_html=True,
        )
        return []

    status_text.empty()
    return df.head(top_n).to_dict(orient="records")


@st.cache_data(ttl=3600, show_spinner=False)
def _run_screener(top_n: int = 50, universe: str = "sp500") -> list[dict]:
    """Run the Klarman screen (filtered) and cache results for 1 hour."""
    df = run_klarman_screen(show_progress=False, filter_results=True, universe=universe)
    if df.empty:
        return []
    return df.head(top_n).to_dict(orient="records")


@st.cache_data(ttl=3600, show_spinner=False)
def _run_screener_unfiltered(top_n: int = 50, universe: str = "sp500") -> list[dict]:
    """Run the Klarman screen (unfiltered — show all scores) and cache results for 1 hour."""
    df = run_klarman_screen(show_progress=False, filter_results=False, universe=universe)
    if df.empty:
        return []
    return df.head(top_n).to_dict(orient="records")


def render_sidebar():
    """Render the sidebar and return (selected_ticker, portfolio_value)."""

    with st.sidebar:
        # ── Branding ─────────────────────────────────────────────────────
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.5rem;">
                <span style="color:{COLORS['blue']};font-size:1.5rem;">📉</span>
                <div>
                    <div style="font-weight:700;font-size:1.1rem;color:#fff;">Klarman Value Engine</div>
                    <div style="font-size:0.7rem;color:{COLORS['gray_500']};">Parcae Dashboard · Seth Klarman / Benjamin Graham</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()

        # ── Manual ticker search ─────────────────────────────────────────
        with st.form("ticker_search_form", clear_on_submit=True):
            ticker_input = st.text_input(
                "Search ticker",
                placeholder="Enter ticker (e.g. AAPL)",
                key="ticker_search_input",
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button(
                "Analyze", use_container_width=True
            )
            if submitted and ticker_input:
                t = ticker_input.strip().upper()
                if t:
                    st.session_state.selected_ticker = t

        # ── Portfolio value ──────────────────────────────────────────────
        portfolio_value = st.number_input(
            "Portfolio $",
            min_value=1_000,
            value=st.session_state.get("portfolio_value", 100_000),
            step=10_000,
            format="%d",
        )
        st.session_state.portfolio_value = portfolio_value

        st.divider()

        # ── Screener controls ────────────────────────────────────────────
        st.markdown(
            f"<span style='font-size:0.7rem;color:{COLORS['gray_400']};text-transform:uppercase;letter-spacing:0.05em;font-weight:600;'>Screener</span>",
            unsafe_allow_html=True,
        )

        # Universe selector
        universe_label = st.selectbox(
            "Universe",
            options=list(UNIVERSE_LABELS.keys()),
            index=0,
            key="universe_selector",
            label_visibility="collapsed",
        )
        universe = UNIVERSE_LABELS[universe_label]

        show_all = st.checkbox(
            "Show all scores",
            value=st.session_state.get("show_all_scores", False),
            key="show_all_scores",
            help="Show scores for all stocks, not just those passing Klarman filters",
        )

        # Result limit
        result_limit = st.radio(
            "Results",
            options=["Top 50", "Top 100", "All"],
            index=0,
            key="screener_result_limit",
            horizontal=True,
            label_visibility="collapsed",
        )
        max_results = {"Top 50": 50, "Top 100": 100, "All": 9999}[result_limit]

        # Run screener button
        refresh = st.button(
            "Run Screener", key="refresh_screener",
            use_container_width=True, type="primary",
        )

        if refresh:
            _run_screener.clear()
            _run_screener_unfiltered.clear()
            st.session_state.watchlist_data = _run_screener_with_progress(
                max_results, universe, filter_results=not show_all,
            )
            st.session_state._last_universe = universe
            st.session_state._last_show_all = show_all
            # Clear selected ticker to show screener results on main screen
            st.session_state.selected_ticker = None

        # Re-run if universe or filter toggle changed without clicking refresh
        if "watchlist_data" in st.session_state and not refresh:
            last_universe = st.session_state.get("_last_universe", "sp500")
            last_show_all = st.session_state.get("_last_show_all", False)
            if universe != last_universe or show_all != last_show_all:
                _run_screener.clear()
                _run_screener_unfiltered.clear()
                st.session_state.watchlist_data = _run_screener_with_progress(
                    max_results, universe, filter_results=not show_all,
                )
                st.session_state._last_universe = universe
                st.session_state._last_show_all = show_all

        # Show result count
        watchlist = st.session_state.get("watchlist_data", [])
        if watchlist:
            st.markdown(
                f"<div style='text-align:center;color:{COLORS['gray_500']};font-size:0.75rem;padding:0.5rem 0;'>"
                f"{len(watchlist)} stocks ranked by score</div>",
                unsafe_allow_html=True,
            )

        st.divider()

        # ── Back to screener (when viewing analysis) ──────────────────────
        if st.session_state.get("selected_ticker") and watchlist:
            if st.button(
                "← Back to Screener",
                key="back_to_screener",
                use_container_width=True,
            ):
                st.session_state.selected_ticker = None
                st.rerun()

        # ── Backtest controls ──────────────────────────────────────────
        st.markdown(
            f"<span style='font-size:0.7rem;color:{COLORS['gray_400']};text-transform:uppercase;letter-spacing:0.05em;font-weight:600;'>Backtest</span>",
            unsafe_allow_html=True,
        )

        bt_years = st.slider("Years", min_value=1, max_value=20, value=10, key="bt_years")
        bt_top_n = st.slider("Top N", min_value=2, max_value=50, value=10, key="bt_top_n")
        bt_weighting = st.radio(
            "Weighting",
            options=["Equal", "Score"],
            index=0,
            key="bt_weighting",
            horizontal=True,
            label_visibility="collapsed",
        )

        if st.button("Run Backtest", key="run_backtest_btn", use_container_width=True):
            st.session_state.run_backtest = True
            st.session_state.bt_config = {
                "years": bt_years,
                "top_n": bt_top_n,
                "weighting": bt_weighting.lower(),
                "universe": universe,
            }

        st.divider()

        # ── Portfolio risk button ────────────────────────────────────────
        analyzed = st.session_state.get("analysis_tickers", [])
        if len(analyzed) >= 2:
            if st.button(
                f"Portfolio Risk ({len(analyzed)} positions)",
                key="portfolio_risk_btn",
                use_container_width=True,
            ):
                st.session_state.show_portfolio_risk = not st.session_state.get(
                    "show_portfolio_risk", False
                )

    return (
        st.session_state.get("selected_ticker"),
        st.session_state.get("portfolio_value", 100_000),
    )
