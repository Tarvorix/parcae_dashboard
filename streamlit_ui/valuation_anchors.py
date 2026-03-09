"""
Valuation Anchors tab — EPV + NCAV comparison against current price and DCF.
Ports ValuationAnchors.tsx.
"""

import streamlit as st
import plotly.graph_objects as go
from streamlit_ui.theme import COLORS, PLOTLY_TEMPLATE, fmt_price


def render_valuation_anchors(anchors: dict, mos: dict):
    """Render the Valuation Anchors comparison panel."""

    epv = anchors.get("epv")
    ncav = anchors.get("ncav")
    current_price = mos.get("current_price", 0)
    p25 = mos.get("p25", 0)
    p50 = mos.get("p50", 0)
    p75 = mos.get("p75", 0)

    if not epv and not ncav:
        st.info("Valuation anchors unavailable — insufficient financial data.")
        return

    # ── Comparison Bar Chart ──────────────────────────────────────────────
    labels = []
    values = []
    colors = []

    if ncav and ncav.get("ncav_per_share") is not None:
        labels.append("NCAV / Share")
        values.append(ncav["ncav_per_share"])
        colors.append(COLORS["purple"])

    labels.append("Current Price")
    values.append(current_price)
    colors.append(COLORS["white"])

    if p25:
        labels.append("DCF P25")
        values.append(p25)
        colors.append(COLORS["amber"])

    if epv and epv.get("epv_per_share") is not None:
        labels.append("EPV / Share")
        values.append(epv["epv_per_share"])
        colors.append(COLORS["blue"])

    if p50:
        labels.append("DCF P50")
        values.append(p50)
        colors.append(COLORS["green"])

    if p75:
        labels.append("DCF P75")
        values.append(p75)
        colors.append(COLORS["cyan"])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels,
        y=values,
        marker_color=colors,
        text=[fmt_price(v) for v in values],
        textposition="outside",
        textfont=dict(color=COLORS["gray_300"], size=12),
    ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title=dict(text="Valuation Method Comparison", font=dict(size=14)),
        yaxis_title="Price per Share ($)",
        showlegend=False,
        height=400,
        margin=dict(t=60, b=40, l=60, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── EPV Detail Card ───────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"<div style='font-size:0.85rem;color:{COLORS['gray_400']};margin-bottom:0.5rem;font-weight:600;'>Earnings Power Value (Greenwald)</div>",
            unsafe_allow_html=True,
        )
        if epv:
            franchise_color = COLORS["green"] if epv.get("has_franchise") else COLORS["red"]
            franchise_label = "Franchise Moat" if epv.get("has_franchise") else "No Franchise"

            rows = [
                ("NOPAT", fmt_price(epv.get("nopat", 0) / 1e6) + "M"),
                ("WACC", f"{epv.get('wacc', 0) * 100:.1f}%"),
                ("Tax Rate", f"{epv.get('tax_rate_used', 0) * 100:.1f}%"),
                ("EPV Total", fmt_price(epv.get("epv_total", 0) / 1e6) + "M"),
                ("EPV / Share", fmt_price(epv.get("epv_per_share", 0))),
                ("Franchise Value", fmt_price(epv.get("franchise_value", 0) / 1e6) + "M"),
            ]

            for label, value in rows:
                st.markdown(
                    f"""
                    <div style="
                        display:flex;
                        justify-content:space-between;
                        padding:0.35rem 0.5rem;
                        border-bottom:1px solid {COLORS['gray_800']};
                        font-size:0.8rem;
                    ">
                        <span style="color:{COLORS['gray_400']};">{label}</span>
                        <span style="color:{COLORS['gray_200']};font-weight:600;">{value}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown(
                f"""
                <div style="
                    text-align:center;
                    margin-top:0.5rem;
                    padding:0.35rem;
                    border-radius:0.5rem;
                    background-color:{COLORS['gray_800']};
                    font-size:0.8rem;
                    color:{franchise_color};
                    font-weight:600;
                ">
                    {franchise_label}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.caption("EPV unavailable — missing EBIT or shares data.")

    # ── NCAV Detail Card ──────────────────────────────────────────────────
    with col2:
        st.markdown(
            f"<div style='font-size:0.85rem;color:{COLORS['gray_400']};margin-bottom:0.5rem;font-weight:600;'>Net Current Asset Value (Graham)</div>",
            unsafe_allow_html=True,
        )
        if ncav:
            below_color = COLORS["green"] if ncav.get("trades_below_ncav") else COLORS["red"]
            below_label = "Below NCAV" if ncav.get("trades_below_ncav") else "Above NCAV"

            rows = [
                ("Current Assets", fmt_price(ncav.get("current_assets", 0) / 1e6) + "M"),
                ("Total Liabilities", fmt_price(ncav.get("total_liabilities", 0) / 1e6) + "M"),
                ("NCAV Total", fmt_price(ncav.get("ncav_total", 0) / 1e6) + "M"),
                ("NCAV / Share", fmt_price(ncav.get("ncav_per_share", 0))),
                ("Discount to NCAV", f"{ncav.get('discount_to_ncav', 0) * 100:.1f}%"),
            ]

            for label, value in rows:
                st.markdown(
                    f"""
                    <div style="
                        display:flex;
                        justify-content:space-between;
                        padding:0.35rem 0.5rem;
                        border-bottom:1px solid {COLORS['gray_800']};
                        font-size:0.8rem;
                    ">
                        <span style="color:{COLORS['gray_400']};">{label}</span>
                        <span style="color:{COLORS['gray_200']};font-weight:600;">{value}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown(
                f"""
                <div style="
                    text-align:center;
                    margin-top:0.5rem;
                    padding:0.35rem;
                    border-radius:0.5rem;
                    background-color:{COLORS['gray_800']};
                    font-size:0.8rem;
                    color:{below_color};
                    font-weight:600;
                ">
                    {below_label}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.caption("NCAV unavailable — missing current assets or liabilities data.")
