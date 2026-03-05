"""
Screener View — Main screen ranked table of screened stocks.

Displays all screener results as a styled, clickable ranked list
ordered by composite screen score (best first).  Clicking a row
sets session_state.selected_ticker to drill into full analysis.
"""

import streamlit as st
import pandas as pd
from streamlit_ui.theme import COLORS, fmt_price, fmt_dollar


def render_screener_view(watchlist: list[dict], show_all: bool):
    """
    Render the screener results as the main content area.

    Parameters
    ----------
    watchlist : list[dict]
        Screener results from _run_screener / _run_screener_unfiltered.
    show_all : bool
        Whether "show all scores" mode is active (controls PASS/FAIL badge).
    """

    # ── Header ────────────────────────────────────────────────────────────
    col_title, col_count = st.columns([5, 1])
    with col_title:
        st.markdown(
            f"<h2 style='margin:0;color:{COLORS['white']};'>Screener Results</h2>",
            unsafe_allow_html=True,
        )
    with col_count:
        st.markdown(
            f"<div style='text-align:right;padding-top:0.5rem;color:{COLORS['gray_500']};font-size:0.85rem;'>"
            f"{len(watchlist)} stocks</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.25rem;'></div>", unsafe_allow_html=True)

    # ── Column headers ────────────────────────────────────────────────────
    hdr_style = f"font-size:0.7rem;color:{COLORS['gray_500']};text-transform:uppercase;letter-spacing:0.05em;font-weight:600;"
    h_rank, h_ticker, h_name, h_score, h_ev, h_fcf, h_ptbv, h_sector = st.columns(
        [0.5, 1, 2, 1, 1, 1, 1, 1.5]
    )
    with h_rank:
        st.markdown(f"<div style='{hdr_style}'>#</div>", unsafe_allow_html=True)
    with h_ticker:
        st.markdown(f"<div style='{hdr_style}'>Ticker</div>", unsafe_allow_html=True)
    with h_name:
        st.markdown(f"<div style='{hdr_style}'>Name</div>", unsafe_allow_html=True)
    with h_score:
        st.markdown(f"<div style='{hdr_style}'>Score</div>", unsafe_allow_html=True)
    with h_ev:
        st.markdown(f"<div style='{hdr_style}'>EV/EBIT</div>", unsafe_allow_html=True)
    with h_fcf:
        st.markdown(f"<div style='{hdr_style}'>FCF Yield</div>", unsafe_allow_html=True)
    with h_ptbv:
        st.markdown(f"<div style='{hdr_style}'>P/TBV</div>", unsafe_allow_html=True)
    with h_sector:
        st.markdown(f"<div style='{hdr_style}'>Sector</div>", unsafe_allow_html=True)

    st.markdown(
        f"<hr style='margin:0.25rem 0;border-color:{COLORS['gray_700']};'>",
        unsafe_allow_html=True,
    )

    # ── Rows ──────────────────────────────────────────────────────────────
    for idx, candidate in enumerate(watchlist):
        ticker = candidate["ticker"]
        name = candidate.get("name", ticker)
        score = candidate.get("screen_score", 0)
        ev_ebit = candidate.get("ev_ebit")
        fcf_yield = candidate.get("fcf_yield_pct")
        ptbv = candidate.get("price_tangible_book")
        sector = candidate.get("sector", "—")
        passes = candidate.get("passes_filter", True)
        price = candidate.get("price")
        market_cap = candidate.get("market_cap")

        # Score color
        if score >= 0.15:
            sc_color = COLORS["green"]
        elif score >= 0.08:
            sc_color = COLORS["amber"]
        else:
            sc_color = COLORS["red"]

        # Pass/fail badge
        if show_all:
            if passes:
                badge = f"<span style='color:{COLORS['green']};font-size:0.65rem;font-weight:700;margin-right:0.25rem;'>PASS</span>"
            else:
                badge = f"<span style='color:{COLORS['red']};font-size:0.65rem;font-weight:700;margin-right:0.25rem;'>FAIL</span>"
        else:
            badge = ""

        # Format values
        ev_str = f"{ev_ebit:.1f}" if ev_ebit is not None else "—"
        fcf_str = f"{fcf_yield:.1f}%" if fcf_yield is not None else "—"
        ptbv_str = f"{ptbv:.2f}" if ptbv is not None else "—"
        price_str = fmt_price(price) if price else "—"
        mcap_str = fmt_dollar(market_cap) if market_cap else "—"

        # Selected state
        is_selected = st.session_state.get("selected_ticker") == ticker

        # Row as a clickable button
        c_rank, c_ticker, c_name, c_score, c_ev, c_fcf, c_ptbv, c_sector = st.columns(
            [0.5, 1, 2, 1, 1, 1, 1, 1.5]
        )

        row_style = f"font-size:0.85rem;color:{COLORS['gray_50']};padding:0.15rem 0;"

        with c_rank:
            st.markdown(
                f"<div style='{row_style}color:{COLORS['gray_500']};'>{idx + 1}</div>",
                unsafe_allow_html=True,
            )
        with c_ticker:
            st.markdown(
                f"<div style='{row_style}font-weight:700;'>{badge}{ticker}</div>",
                unsafe_allow_html=True,
            )
        with c_name:
            # Truncate long names
            display_name = name[:35] + "…" if len(name) > 35 else name
            st.markdown(
                f"<div style='{row_style}color:{COLORS['gray_400']};font-size:0.8rem;'>{display_name}</div>",
                unsafe_allow_html=True,
            )
        with c_score:
            st.markdown(
                f"<div style='{row_style}font-weight:700;color:{sc_color};'>{score:.4f}</div>",
                unsafe_allow_html=True,
            )
        with c_ev:
            ev_color = COLORS["green"] if ev_ebit is not None and ev_ebit <= 10 else COLORS["gray_400"]
            st.markdown(
                f"<div style='{row_style}color:{ev_color};'>{ev_str}</div>",
                unsafe_allow_html=True,
            )
        with c_fcf:
            fcf_color = COLORS["green"] if fcf_yield is not None and fcf_yield >= 7.0 else COLORS["gray_400"]
            st.markdown(
                f"<div style='{row_style}color:{fcf_color};'>{fcf_str}</div>",
                unsafe_allow_html=True,
            )
        with c_ptbv:
            ptbv_color = COLORS["green"] if ptbv is not None and ptbv <= 1.2 else COLORS["gray_400"]
            st.markdown(
                f"<div style='{row_style}color:{ptbv_color};'>{ptbv_str}</div>",
                unsafe_allow_html=True,
            )
        with c_sector:
            st.markdown(
                f"<div style='{row_style}color:{COLORS['gray_500']};font-size:0.75rem;'>{sector or '—'}</div>",
                unsafe_allow_html=True,
            )

        # Full-width clickable button below the row data
        if st.button(
            f"Analyze {ticker}  ·  {price_str}  ·  Mkt Cap {mcap_str}",
            key=f"screener_row_{ticker}",
            use_container_width=True,
        ):
            st.session_state.selected_ticker = ticker
            st.rerun()

    # ── Empty state ───────────────────────────────────────────────────────
    if not watchlist:
        st.markdown(
            f"""
            <div style="
                display:flex;
                flex-direction:column;
                align-items:center;
                justify-content:center;
                height:40vh;
                text-align:center;
                color:{COLORS['gray_600']};
            ">
                <div style="font-size:3rem;opacity:0.2;margin-bottom:1rem;">📊</div>
                <div style="font-size:1.1rem;font-weight:700;color:{COLORS['gray_500']};margin-bottom:0.5rem;">
                    No screener results yet
                </div>
                <div style="font-size:0.85rem;">
                    Select a universe and click <b>Run Screener</b> in the sidebar to scan for value opportunities.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
