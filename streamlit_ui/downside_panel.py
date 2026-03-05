"""
Downside / Klarman tab — score badge, percentile table, 6-item checklist.
Ports DownsidePanel.tsx.
"""

import streamlit as st
from streamlit_ui.theme import COLORS, fmt_price, fmt_pct, score_color


def render_downside_panel(analysis: dict):
    """Render the Klarman checklist and score panel."""

    mos = analysis["margin_of_safety"]
    dists = analysis["distributions"]
    klarman_score = mos["klarman_score"]
    color = score_color(klarman_score)

    # ── Build checklist ──────────────────────────────────────────────────
    checks = [
        {
            "label": "MoS vs P25 ≥ 30%",
            "passed": mos["mos_downside"] >= 0.30,
            "value": fmt_pct(mos["mos_downside"]),
        },
        {
            "label": "P(Undervalued) ≥ 65%",
            "passed": mos["prob_undervalued"] >= 0.65,
            "value": fmt_pct(mos["prob_undervalued"]),
        },
        {
            "label": "FCF Margin (base) ≥ 5%",
            "passed": dists["fcf_margin"]["base"] >= 0.05,
            "value": fmt_pct(dists["fcf_margin"]["base"]),
        },
        {
            "label": "FCF Margin (bear) > 0%",
            "passed": dists["fcf_margin"]["bear"] > 0,
            "value": fmt_pct(dists["fcf_margin"]["bear"]),
        },
        {
            "label": "Revenue Growth (base) > −5%",
            "passed": dists["revenue_growth"]["base"] > -0.05,
            "value": fmt_pct(dists["revenue_growth"]["base"]),
        },
        {
            "label": "Discount Rate (bear) ≥ 10%",
            "passed": dists["discount_rate"]["bear"] >= 0.10,
            "value": fmt_pct(dists["discount_rate"]["bear"]),
        },
    ]
    n_passed = sum(1 for c in checks if c["passed"])

    # ── Hero score card ──────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="
            text-align:center;
            background-color:{COLORS['gray_800']};
            border:2px solid {color};
            border-radius:1rem;
            padding:1.5rem;
            margin-bottom:1rem;
        ">
            <div style="font-size:0.8rem;color:{COLORS['gray_400']};">Klarman Score</div>
            <div style="font-size:3rem;font-weight:800;color:{color};">{klarman_score:.1f}</div>
            <div style="font-size:0.8rem;color:{COLORS['gray_500']};">{n_passed} / 6 criteria passed</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Percentile table ─────────────────────────────────────────────────
    st.markdown(
        f"<div style='font-size:0.8rem;color:{COLORS['gray_400']};margin-bottom:0.5rem;'>Intrinsic Value Percentiles</div>",
        unsafe_allow_html=True,
    )

    percentiles = [
        ("P10", mos["p10"], COLORS["red"]),
        ("P25", mos["p25"], COLORS["amber"]),
        ("P50", mos["p50"], COLORS["green"]),
        ("P75", mos["p75"], COLORS["blue"]),
        ("P90", mos["p90"], COLORS["purple"]),
    ]

    cols = st.columns(5)
    for i, (label, value, clr) in enumerate(percentiles):
        with cols[i]:
            st.markdown(
                f"""
                <div style="
                    text-align:center;
                    background-color:{COLORS['gray_800']};
                    border-radius:0.5rem;
                    padding:0.5rem;
                ">
                    <div style="font-size:0.7rem;color:{COLORS['gray_400']};">{label}</div>
                    <div style="font-size:1rem;font-weight:700;color:{clr};">{fmt_price(value)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        f"""
        <div style="
            text-align:center;
            background-color:{COLORS['gray_800']};
            border-radius:0.5rem;
            padding:0.5rem;
            margin-top:0.5rem;
            margin-bottom:1rem;
        ">
            <div style="font-size:0.7rem;color:{COLORS['gray_400']};">Current Price</div>
            <div style="font-size:1rem;font-weight:700;color:{COLORS['white']};">{fmt_price(mos['current_price'])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 6-item checklist ─────────────────────────────────────────────────
    st.markdown(
        f"<div style='font-size:0.8rem;color:{COLORS['gray_400']};margin-bottom:0.5rem;'>Klarman Checklist</div>",
        unsafe_allow_html=True,
    )

    for check in checks:
        icon = "✅" if check["passed"] else "❌"
        text_color = COLORS["green"] if check["passed"] else COLORS["red"]
        st.markdown(
            f"""
            <div style="
                display:flex;
                align-items:center;
                justify-content:space-between;
                padding:0.5rem 0.75rem;
                border-bottom:1px solid {COLORS['gray_800']};
                font-size:0.85rem;
            ">
                <span>{icon} {check['label']}</span>
                <span style="color:{text_color};font-weight:600;">{check['value']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
