"""
Decision Matrix tab — Kelly position sizing, pass/fail verdict, scenario table.
Ports DecisionMatrix.tsx.
"""

import streamlit as st
import pandas as pd
from streamlit_ui.theme import COLORS, fmt_pct, fmt_price


def render_decision_matrix(kelly_sizing: dict, margin_of_safety: dict, ticker: str):
    """Render the Kelly sizing recommendation and scenario table."""

    passes = margin_of_safety["passes_mos_threshold"]

    # ── Verdict banner ───────────────────────────────────────────────────
    if passes:
        banner_color = COLORS["green"]
        banner_border = COLORS["green"]
        banner_text = f"PASS — Consider initiating a position in {ticker}"
    else:
        banner_color = COLORS["red"]
        banner_border = COLORS["red"]
        banner_text = f"FAIL — {ticker} does not meet the 30% margin of safety threshold"

    st.markdown(
        f"""
        <div style="
            background-color:{banner_color}20;
            border:1px solid {banner_border};
            border-radius:0.75rem;
            padding:0.75rem 1rem;
            text-align:center;
            font-weight:700;
            color:{banner_color};
            margin-bottom:1rem;
        ">
            {banner_text}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Kelly breakdown (4 cards) ────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    cards = [
        ("Full Kelly %", f"{kelly_sizing['kelly_full_pct']:.1f}%", COLORS["gray_400"], c1),
        ("Quarter-Kelly %", f"{kelly_sizing['kelly_fractional_pct']:.1f}%", COLORS["blue"], c2),
        ("P(Undervalued)", fmt_pct(margin_of_safety["prob_undervalued"]), COLORS["green"], c3),
        ("MoS vs P25", fmt_pct(margin_of_safety["mos_downside"]), COLORS["amber"], c4),
    ]

    for label, value, color, col in cards:
        with col:
            st.markdown(
                f"""
                <div style="
                    background-color:{COLORS['gray_800']};
                    border:1px solid {COLORS['gray_700']};
                    border-radius:0.75rem;
                    padding:0.75rem;
                    text-align:center;
                ">
                    <div style="font-size:0.7rem;color:{COLORS['gray_400']};">{label}</div>
                    <div style="font-size:1.25rem;font-weight:700;color:{color};">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

    # ── Custom portfolio calculator ──────────────────────────────────────
    st.markdown(
        f"<div style='font-size:0.85rem;color:{COLORS['gray_400']};margin-bottom:0.5rem;font-weight:600;'>Position Calculator</div>",
        unsafe_allow_html=True,
    )

    custom_portfolio = st.number_input(
        "Your portfolio size ($)",
        min_value=1_000,
        value=st.session_state.get("portfolio_value", 100_000),
        step=10_000,
        format="%d",
        key="decision_portfolio_input",
    )

    alloc_pct = kelly_sizing["kelly_fractional_pct"]
    dollar_amount = custom_portfolio * (alloc_pct / 100)
    current_price = margin_of_safety["current_price"]
    shares = int(dollar_amount / current_price) if current_price > 0 else 0

    r1, r2, r3 = st.columns(3)
    with r1:
        st.metric("Allocation", f"{alloc_pct:.1f}%")
    with r2:
        st.metric("Dollar Amount", f"${dollar_amount:,.0f}")
    with r3:
        st.metric("Shares", f"{shares:,}")

    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

    # ── Scenario table (5 preset portfolio sizes) ────────────────────────
    st.markdown(
        f"<div style='font-size:0.85rem;color:{COLORS['gray_400']};margin-bottom:0.5rem;font-weight:600;'>Scenario Table</div>",
        unsafe_allow_html=True,
    )

    preset_sizes = [50_000, 100_000, 250_000, 500_000, 1_000_000]
    rows = []
    for size in preset_sizes:
        d = size * (alloc_pct / 100)
        s = int(d / current_price) if current_price > 0 else 0
        rows.append(
            {
                "Portfolio": f"${size:,}",
                "Allocation %": f"{alloc_pct:.1f}%",
                "Dollar Amount": f"${d:,.0f}",
                "Shares": f"{s:,}",
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
