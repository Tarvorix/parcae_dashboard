"""
FCF Projections tab — bear/base/bull scenario cards, area chart, year-by-year table.
Ports FCFProjections.tsx.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from streamlit_ui.theme import COLORS, fmt_pct, fmt_dollar, plotly_dark_layout


def _project_fcf(current_revenue: float, growth: float, margin: float, years: int) -> list[float]:
    """Project FCF for each year under a single scenario."""
    return [current_revenue * ((1 + growth) ** y) * margin for y in range(1, years + 1)]


def render_fcf_projections(distributions: dict, projection_years: int = 10):
    """Render the FCF projection bands and scenario table."""

    rev_growth = distributions["revenue_growth"]
    fcf_margin = distributions["fcf_margin"]
    discount_rate = distributions["discount_rate"]
    current_revenue = distributions["current_revenue"]

    # ── Scenario parameter cards ─────────────────────────────────────────
    st.markdown(
        f"<div style='font-size:0.8rem;color:{COLORS['gray_400']};margin-bottom:0.5rem;'>Distribution Parameters (Bear / Base / Bull)</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    params = [
        ("Revenue Growth", rev_growth, c1),
        ("FCF Margin", fcf_margin, c2),
        ("Discount Rate", discount_rate, c3),
    ]
    for label, vals, col in params:
        with col:
            st.markdown(
                f"""
                <div style="
                    background-color:{COLORS['gray_800']};
                    border-radius:0.5rem;
                    padding:0.75rem;
                    text-align:center;
                ">
                    <div style="font-size:0.7rem;color:{COLORS['gray_400']};margin-bottom:0.25rem;">{label}</div>
                    <div style="font-size:0.85rem;">
                        <span style="color:{COLORS['red']};">{fmt_pct(vals['bear'])}</span>
                        <span style="color:{COLORS['gray_600']};"> / </span>
                        <span style="color:{COLORS['blue']};">{fmt_pct(vals['base'])}</span>
                        <span style="color:{COLORS['gray_600']};"> / </span>
                        <span style="color:{COLORS['green']};">{fmt_pct(vals['bull'])}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)

    # ── Project FCFs ─────────────────────────────────────────────────────
    bear_fcfs = _project_fcf(current_revenue, rev_growth["bear"], fcf_margin["bear"], projection_years)
    base_fcfs = _project_fcf(current_revenue, rev_growth["base"], fcf_margin["base"], projection_years)
    bull_fcfs = _project_fcf(current_revenue, rev_growth["bull"], fcf_margin["bull"], projection_years)

    years = [f"Y{y}" for y in range(1, projection_years + 1)]

    # Convert to $M
    bear_m = [f / 1_000_000 for f in bear_fcfs]
    base_m = [f / 1_000_000 for f in base_fcfs]
    bull_m = [f / 1_000_000 for f in bull_fcfs]

    # ── Area chart ───────────────────────────────────────────────────────
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=years,
            y=bull_m,
            name="Bull",
            mode="lines",
            line=dict(color=COLORS["green"], width=0),
            fill=None,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=base_m,
            name="Base",
            mode="lines",
            line=dict(color=COLORS["blue"], width=2),
            fill="tonexty",
            fillcolor="rgba(34,197,94,0.15)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=years,
            y=bear_m,
            name="Bear",
            mode="lines",
            line=dict(color=COLORS["red"], width=0),
            fill="tonexty",
            fillcolor="rgba(59,130,246,0.15)",
        )
    )

    fig.update_layout(
        **plotly_dark_layout(
            height=300,
            yaxis_title="FCF ($M)",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=10),
            ),
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # ── Year-by-year table ───────────────────────────────────────────────
    df = pd.DataFrame(
        {
            "Year": years,
            "Bear ($M)": [f"{v:.1f}" for v in bear_m],
            "Base ($M)": [f"{v:.1f}" for v in base_m],
            "Bull ($M)": [f"{v:.1f}" for v in bull_m],
        }
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
