"""
Parcae Dashboard — Klarman Value Engine (Streamlit)

Single-page dashboard that calls the backend engine directly.
No FastAPI, no Docker, no CORS — just Python.
"""

import os

import streamlit as st

# Inject SEC_IDENTITY from Streamlit secrets if not already in env
if "SEC_IDENTITY" not in os.environ:
    try:
        os.environ["SEC_IDENTITY"] = st.secrets["SEC_IDENTITY"]
    except Exception:
        os.environ["SEC_IDENTITY"] = "ParcaeDashboard admin@parcaedashboard.com"

import numpy as np

from backend.data.yfinance_client import get_fundamentals, get_price_history, build_fallback_edgar_data
from backend.data.edgar_client import get_10yr_financials
from backend.engine.distributions import build_distributions_from_history
from backend.engine.monte_carlo import run_dcf_simulation
from backend.engine.margin_of_safety import calculate_margin_of_safety
from backend.engine.kelly import calculate_position_size
from backend.engine.valuation_anchors import calculate_valuation_anchors
from backend.engine.quality_scores import calculate_quality_scores
from backend.backtest.engine import run_backtest as run_backtest_engine
from backend.data.insider_client import get_flow_signals
from backend.portfolio.copula import gaussian_copula_portfolio_var
from backend.portfolio.tail_risk import calculate_tail_risk_summary

from streamlit_ui.theme import inject_custom_css, COLORS, fmt_price, fmt_pct, score_color
from streamlit_ui.sidebar import render_sidebar
from streamlit_ui.screener_view import render_screener_view
from streamlit_ui.value_distribution import render_value_distribution
from streamlit_ui.downside_panel import render_downside_panel
from streamlit_ui.fcf_projections import render_fcf_projections
from streamlit_ui.decision_matrix import render_decision_matrix
from streamlit_ui.portfolio_risk import render_portfolio_risk
from streamlit_ui.valuation_anchors import render_valuation_anchors
from streamlit_ui.quality_panel import render_quality_panel
from streamlit_ui.flow_signals import render_flow_signals
from streamlit_ui.backtest_view import render_backtest_view

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Parcae Dashboard — Klarman Value Engine",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_custom_css()

# ── Session state defaults ───────────────────────────────────────────────────

if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = None
if "portfolio_value" not in st.session_state:
    st.session_state.portfolio_value = 100_000
if "analysis_tickers" not in st.session_state:
    st.session_state.analysis_tickers = []
if "show_portfolio_risk" not in st.session_state:
    st.session_state.show_portfolio_risk = False


# ── Cached analysis functions ────────────────────────────────────────────────


@st.cache_data(ttl=1800, show_spinner=False)
def analyze_ticker(ticker: str, portfolio_value: float) -> dict | None:
    """
    Full Monte Carlo DCF analysis for a single ticker.
    Returns the analysis dict or None on failure.
    """
    yf_data = get_fundamentals(ticker)
    if not yf_data:
        return None

    edgar_data = get_10yr_financials(ticker)
    if not edgar_data:
        # Fallback: build synthetic history from yfinance trailing fundamentals
        edgar_data = build_fallback_edgar_data(yf_data)
        if not edgar_data:
            return None

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

    valuation_anchors = calculate_valuation_anchors(yf_data, edgar_data)
    quality_scores = calculate_quality_scores(yf_data, edgar_data)
    flow_signals = get_flow_signals(ticker, yf_data)

    return {
        "ticker": ticker,
        "name": yf_data.get("name"),
        "sector": yf_data.get("sector"),
        "industry": yf_data.get("industry"),
        "distributions": distributions,
        "margin_of_safety": mos,
        "kelly_sizing": kelly,
        "valuation_anchors": valuation_anchors,
        "quality_scores": quality_scores,
        "flow_signals": flow_signals,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def compute_portfolio_risk(
    tickers_tuple: tuple, years: int = 5, confidence: float = 0.95
) -> dict | None:
    """Compute portfolio tail risk using Gaussian copula + historical."""
    ticker_list = list(tickers_tuple)
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
        return None

    min_len = min(len(r) for r in returns_list)
    returns_matrix = np.array([r[-min_len:] for r in returns_list])

    corr = np.corrcoef(returns_matrix)
    eigvals = np.linalg.eigvalsh(corr)
    if eigvals.min() < 0:
        corr += np.eye(len(valid_tickers)) * (abs(eigvals.min()) + 1e-6)
        d = np.sqrt(np.diag(corr))
        corr = corr / np.outer(d, d)

    copula_result = gaussian_copula_portfolio_var(
        returns_matrix, corr, confidence=confidence, n_simulations=50_000
    )
    hist_result = calculate_tail_risk_summary(returns_matrix, confidence=confidence)

    return {
        "tickers": valid_tickers,
        "copula": copula_result,
        "historical": hist_result,
    }


# ── Sidebar ──────────────────────────────────────────────────────────────────

selected_ticker, portfolio_value = render_sidebar()

# ── Main panel ───────────────────────────────────────────────────────────────

# Portfolio risk overlay
if st.session_state.get("show_portfolio_risk"):
    analyzed = st.session_state.get("analysis_tickers", [])
    if len(analyzed) >= 2:
        with st.container():
            col_title, col_close = st.columns([6, 1])
            with col_title:
                st.markdown(
                    f"<h3 style='color:{COLORS['purple']};margin:0;'>Portfolio Tail Risk</h3>",
                    unsafe_allow_html=True,
                )
            with col_close:
                if st.button("✕ Close", key="close_portfolio_risk"):
                    st.session_state.show_portfolio_risk = False
                    st.rerun()

            with st.spinner("Running copula simulation…"):
                risk_data = compute_portfolio_risk(tuple(analyzed))

            if risk_data:
                render_portfolio_risk(risk_data)
            else:
                st.warning("Could not compute portfolio risk — insufficient price history.")

        st.divider()

# Backtest overlay
if st.session_state.get("run_backtest"):
    bt_config = st.session_state.get("bt_config", {})
    with st.container():
        col_title, col_close = st.columns([6, 1])
        with col_title:
            st.markdown(
                f"<h3 style='color:{COLORS['blue']};margin:0;'>Walk-Forward Backtest</h3>",
                unsafe_allow_html=True,
            )
        with col_close:
            if st.button("✕ Close", key="close_backtest"):
                st.session_state.run_backtest = False
                st.rerun()

        with st.spinner("Running screener + backtest…"):
            try:
                from backend.screener.screen import run_klarman_screen as _bt_screen
                df = _bt_screen(
                    show_progress=False,
                    filter_results=False,
                    universe=bt_config.get("universe", "sp500"),
                )
                if df.empty:
                    st.error("Screener returned no results for backtest.")
                else:
                    ranked = df["ticker"].tolist()
                    bt_result = run_backtest_engine(
                        ranked_tickers=ranked,
                        years=bt_config.get("years", 10),
                        top_n=bt_config.get("top_n", 10),
                        weighting=bt_config.get("weighting", "equal"),
                        initial_capital=portfolio_value,
                    )
                    render_backtest_view(bt_result)
            except ValueError as e:
                st.error(f"Backtest failed: {e}")
            except Exception as e:
                st.error(f"Backtest error: {e}")

    st.divider()

# No ticker selected — show screener results on main screen
if not selected_ticker:
    watchlist = st.session_state.get("watchlist_data", [])
    show_all = st.session_state.get("show_all_scores", False)
    render_screener_view(watchlist, show_all)
else:
    # ── Back to screener button ──────────────────────────────────────────
    watchlist = st.session_state.get("watchlist_data", [])
    if watchlist:
        if st.button("← Back to Screener", key="back_to_screener_main"):
            st.session_state.selected_ticker = None
            st.rerun()

    # ── Run analysis ─────────────────────────────────────────────────────
    with st.spinner(f"Running 100K Monte Carlo paths for {selected_ticker}…"):
        analysis = analyze_ticker(selected_ticker, portfolio_value)

    if analysis is None:
        st.error(
            f"Analysis failed for **{selected_ticker}** — insufficient data from Yahoo Finance or SEC EDGAR (need ≥ 5 years of 10-K filings)."
        )
    else:
        # Track analyzed tickers for portfolio risk
        if selected_ticker not in st.session_state.analysis_tickers:
            st.session_state.analysis_tickers.append(selected_ticker)

        mos = analysis["margin_of_safety"]
        kelly = analysis["kelly_sizing"]

        # ── Ticker header ────────────────────────────────────────────────
        hdr_left, hdr_right = st.columns([4, 1])
        with hdr_left:
            st.markdown(
                f"<h2 style='margin:0;'>{selected_ticker}</h2>",
                unsafe_allow_html=True,
            )
            subtitle_parts = []
            if analysis.get("name"):
                subtitle_parts.append(analysis["name"])
            if analysis.get("sector"):
                subtitle_parts.append(
                    f"<span style='color:{COLORS['gray_600']};'>· {analysis['sector']}</span>"
                )
            if subtitle_parts:
                st.markdown(
                    f"<div style='font-size:0.85rem;color:{COLORS['gray_400']};'>{' '.join(subtitle_parts)}</div>",
                    unsafe_allow_html=True,
                )
        with hdr_right:
            if st.button("+ Save to Watchlist", key="save_watchlist"):
                saved = st.session_state.get("saved_watchlist", [])
                if selected_ticker not in saved:
                    saved.append(selected_ticker)
                    st.session_state.saved_watchlist = saved
                    st.toast(f"{selected_ticker} saved to watchlist")

        # ── Klarman score badge + key metrics ────────────────────────────
        ks = mos["klarman_score"]
        ks_color = score_color(ks)

        col_score, col_metrics = st.columns([1, 3])
        with col_score:
            st.markdown(
                f"""
                <div style="
                    text-align:center;
                    background-color:{ks_color}20;
                    border:1px solid {ks_color};
                    border-radius:0.75rem;
                    padding:1rem;
                ">
                    <div style="font-size:0.7rem;color:{COLORS['gray_400']};">Klarman Score</div>
                    <div style="font-size:2.5rem;font-weight:800;color:{ks_color};">{ks:.1f}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_metrics:
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Current Price", fmt_price(mos["current_price"]))
            with m2:
                mos_val = mos["mos_downside"]
                st.metric("MoS vs P25", fmt_pct(mos_val))
            with m3:
                st.metric("Kelly Position", f"{kelly['kelly_fractional_pct']:.1f}%")

        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

        # ── 7-tab analysis ───────────────────────────────────────────────
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
            ["Value Distribution", "Downside / Klarman", "Valuation Anchors",
             "Quality / Distress", "Flow Signals", "FCF Projections", "Decision Matrix"]
        )

        with tab1:
            render_value_distribution(mos)

        with tab2:
            render_downside_panel(analysis)

        with tab3:
            render_valuation_anchors(analysis.get("valuation_anchors", {}), mos)

        with tab4:
            render_quality_panel(analysis.get("quality_scores", {}))

        with tab5:
            render_flow_signals(analysis.get("flow_signals", {}))

        with tab6:
            render_fcf_projections(analysis["distributions"])

        with tab7:
            render_decision_matrix(kelly, mos, selected_ticker)
