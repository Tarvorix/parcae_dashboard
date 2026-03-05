"""
Sidebar: Klarman screener watchlist, manual ticker search, portfolio value input.
Ports the left sidebar from App.tsx + Watchlist.tsx.
"""

import streamlit as st
from backend.screener.screen import run_klarman_screen
from streamlit_ui.theme import COLORS, fmt_dollar


UNIVERSE_LABELS = {
    "S&P 500": "sp500",
    "S&P Mid-Cap 400": "sp400",
    "S&P Small-Cap 600": "sp600",
    "S&P 1500 (All)": "all",
}


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
        # Use a form so that Enter submits the ticker, clears the input,
        # and the sidebar remains usable for the next search.
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

        # ── Screener ─────────────────────────────────────────────────────
        col_label, col_btn = st.columns([3, 1])
        with col_label:
            st.markdown(
                f"<span style='font-size:0.7rem;color:{COLORS['gray_400']};text-transform:uppercase;letter-spacing:0.05em;'>Screener</span>",
                unsafe_allow_html=True,
            )
        with col_btn:
            refresh = st.button("🔄", key="refresh_screener", help="Run / refresh screener")

        # ── Universe selector ──────────────────────────────────────────
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

        # Only run screener when user clicks the button
        if refresh:
            _run_screener.clear()
            _run_screener_unfiltered.clear()
            spinner_msg = f"Screening {universe_label}… (this takes a few minutes)"
            with st.spinner(spinner_msg):
                if show_all:
                    st.session_state.watchlist_data = _run_screener_unfiltered(50, universe)
                else:
                    st.session_state.watchlist_data = _run_screener(50, universe)
                st.session_state._last_universe = universe
                st.session_state._last_show_all = show_all

        # Re-run if universe or filter toggle changed without clicking refresh
        if "watchlist_data" in st.session_state and not refresh:
            last_universe = st.session_state.get("_last_universe", "sp500")
            last_show_all = st.session_state.get("_last_show_all", False)
            if universe != last_universe or show_all != last_show_all:
                _run_screener.clear()
                _run_screener_unfiltered.clear()
                spinner_msg = f"Screening {universe_label}… (this takes a few minutes)"
                with st.spinner(spinner_msg):
                    if show_all:
                        st.session_state.watchlist_data = _run_screener_unfiltered(50, universe)
                    else:
                        st.session_state.watchlist_data = _run_screener(50, universe)
                    st.session_state._last_universe = universe
                    st.session_state._last_show_all = show_all

        watchlist = st.session_state.get("watchlist_data", [])

        if not watchlist:
            st.markdown(
                f"<div style='text-align:center;color:{COLORS['gray_600']};font-size:0.75rem;padding:1.5rem 0;'>"
                "No candidates found</div>",
                unsafe_allow_html=True,
            )
        else:
            for candidate in watchlist:
                ticker = candidate["ticker"]
                name = candidate.get("name", ticker)
                fcf_yield = candidate.get("fcf_yield_pct", 0)
                ev_ebit = candidate.get("ev_ebit", 0)
                p_tbv = candidate.get("price_tangible_book", 0)
                score = candidate.get("screen_score", 0)
                passes = candidate.get("passes_filter", True)

                is_selected = st.session_state.get("selected_ticker") == ticker
                bg = f"background-color:{'#1e3a5f30' if is_selected else 'transparent'};"
                border_left = f"border-left:2px solid {COLORS['blue']};" if is_selected else ""

                # Build label with pass/fail indicator when showing all
                pass_icon = ""
                if show_all:
                    pass_icon = "PASS " if passes else "FAIL "

                if st.button(
                    f"{pass_icon}**{ticker}**  ·  {fcf_yield:.1f}% FCF  ·  Score {score:.4f}\n{name[:30]}  ·  EV/EBIT {ev_ebit:.1f}  ·  P/TBV {p_tbv:.2f}",
                    key=f"wl_{ticker}",
                    use_container_width=True,
                ):
                    st.session_state.selected_ticker = ticker

        # ── Portfolio risk button ────────────────────────────────────────
        analyzed = st.session_state.get("analysis_tickers", [])
        if len(analyzed) >= 2:
            st.divider()
            if st.button(
                f"📊 Portfolio Risk ({len(analyzed)} positions)",
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
