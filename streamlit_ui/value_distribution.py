"""
Value Distribution tab — 200-bin intrinsic value histogram with percentile markers.
Ports ValueDistributionChart.tsx.
"""

import streamlit as st
import plotly.graph_objects as go
from streamlit_ui.theme import COLORS, fmt_price, fmt_pct, plotly_dark_layout


def render_value_distribution(mos: dict):
    """Render the intrinsic value histogram with reference lines and MoS summary."""

    histogram_data = mos["histogram_data"]
    current_price = mos["current_price"]
    p10 = mos["p10"]
    p25 = mos["p25"]
    p50 = mos["p50"]
    p75 = mos["p75"]
    p90 = mos["p90"]

    # ── Color legend ─────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="display:flex;gap:1.5rem;margin-bottom:0.75rem;font-size:0.75rem;color:{COLORS['gray_400']};">
            <span><span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:{COLORS['red']};margin-right:4px;vertical-align:middle;"></span>Below current price</span>
            <span><span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:{COLORS['amber']};margin-right:4px;vertical-align:middle;"></span>Margin of safety zone</span>
            <span><span style="display:inline-block;width:12px;height:12px;border-radius:2px;background:{COLORS['green']};margin-right:4px;vertical-align:middle;"></span>Above P25 (Klarman's anchor)</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Build bar chart ──────────────────────────────────────────────────
    bin_starts = [b["bin_start"] for b in histogram_data]
    frequencies = [b["frequency"] for b in histogram_data]

    # Per-bin color: red below price, amber in MoS zone, green above p25
    bar_colors = []
    for b in histogram_data:
        mid = (b["bin_start"] + b["bin_end"]) / 2
        if mid < current_price:
            bar_colors.append(COLORS["red"])
        elif mid < p25:
            bar_colors.append(COLORS["amber"])
        else:
            bar_colors.append(COLORS["green"])

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=bin_starts,
            y=frequencies,
            marker_color=bar_colors,
            hovertemplate="Range: %{customdata[0]} – %{customdata[1]}<br>Frequency: %{y:.3%}<extra></extra>",
            customdata=[
                [fmt_price(b["bin_start"]), fmt_price(b["bin_end"])]
                for b in histogram_data
            ],
        )
    )

    # ── Reference lines ──────────────────────────────────────────────────
    ref_lines = [
        (p10, "P10", COLORS["red"]),
        (p25, "P25", COLORS["amber"]),
        (p50, "P50", COLORS["green"]),
        (p75, "P75", COLORS["blue"]),
        (p90, "P90", COLORS["purple"]),
    ]
    for value, label, color in ref_lines:
        fig.add_vline(
            x=value, line_dash="dash", line_color=color, line_width=1, opacity=0.8
        )
        fig.add_annotation(
            x=value,
            y=1,
            yref="paper",
            text=f"{label} {fmt_price(value)}",
            showarrow=False,
            font=dict(color=color, size=9),
            xanchor="left",
            yanchor="top",
            xshift=3,
        )

    # Current price line (solid white)
    fig.add_vline(x=current_price, line_color=COLORS["white"], line_width=2)
    fig.add_annotation(
        x=current_price,
        y=1,
        yref="paper",
        text=f"Price {fmt_price(current_price)}",
        showarrow=False,
        font=dict(color=COLORS["white"], size=10),
        xanchor="right",
        yanchor="top",
        xshift=-3,
    )

    fig.update_layout(
        **plotly_dark_layout(
            height=320,
            bargap=0,
            showlegend=False,
            xaxis_title=None,
            yaxis_title=None,
            yaxis_tickformat=".1%",
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # ── MoS summary strip ────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        val = mos["mos_median"]
        st.metric("MoS vs Median", fmt_pct(val), delta_color="normal")
    with c2:
        val = mos["mos_downside"]
        st.metric("MoS vs P25 (Klarman)", fmt_pct(val), delta_color="normal")
    with c3:
        st.metric("P(Undervalued)", fmt_pct(mos["prob_undervalued"]))
