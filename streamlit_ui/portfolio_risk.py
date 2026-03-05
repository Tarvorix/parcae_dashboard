"""
Portfolio Risk panel — copula, historical, and per-position tail risk analysis.
Ports PortfolioRisk.tsx.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from streamlit_ui.theme import COLORS, fmt_pct, plotly_dark_layout


def render_portfolio_risk(risk_data: dict):
    """Render the portfolio tail risk panel with 3 sub-tabs."""

    tickers = risk_data["tickers"]
    copula = risk_data["copula"]
    historical = risk_data["historical"]

    # ── Ticker badges ────────────────────────────────────────────────────
    badges = " ".join(
        f'<span style="background:{COLORS["blue"]}30;color:{COLORS["blue"]};'
        f'border:1px solid {COLORS["blue"]};border-radius:0.5rem;padding:0.2rem 0.6rem;'
        f'font-size:0.75rem;font-weight:600;">{t}</span>'
        for t in tickers
    )
    st.markdown(
        f"<div style='display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:1rem;'>{badges}</div>",
        unsafe_allow_html=True,
    )

    # ── Sub-tabs ─────────────────────────────────────────────────────────
    tab_copula, tab_historical, tab_positions = st.tabs(
        ["Copula", "Historical", "Positions"]
    )

    # ── Copula tab ───────────────────────────────────────────────────────
    with tab_copula:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("VaR 95%", fmt_pct(abs(copula["var"])))
        with c2:
            st.metric("CVaR 95%", fmt_pct(abs(copula["cvar"])))
        with c3:
            st.metric("Max Drawdown", fmt_pct(abs(copula["max_drawdown_sim"])))
        with c4:
            st.metric("Positions", str(copula["n_positions"]))

        # Weights
        weights = copula.get("weights", [])
        if weights and len(weights) == len(tickers):
            st.markdown(
                f"<div style='font-size:0.75rem;color:{COLORS['gray_400']};margin-top:0.5rem;'>Equal Weights</div>",
                unsafe_allow_html=True,
            )
            weight_cols = st.columns(len(tickers))
            for i, (t, w) in enumerate(zip(tickers, weights)):
                with weight_cols[i]:
                    st.markdown(
                        f"<div style='text-align:center;font-size:0.8rem;'>"
                        f"<span style='color:{COLORS['blue']};font-weight:600;'>{t}</span>"
                        f"<br/><span style='color:{COLORS['gray_400']};'>{w:.1%}</span></div>",
                        unsafe_allow_html=True,
                    )

    # ── Historical tab ───────────────────────────────────────────────────
    with tab_historical:
        r1c1, r1c2, r1c3 = st.columns(3)
        with r1c1:
            st.metric("VaR 95%", fmt_pct(abs(historical["portfolio_var"])))
        with r1c2:
            st.metric("CVaR 95%", fmt_pct(abs(historical["portfolio_cvar"])))
        with r1c3:
            st.metric("Max Drawdown", fmt_pct(abs(historical["portfolio_max_drawdown"])))

        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            st.metric("Sharpe Ratio", f"{historical['portfolio_sharpe']:.2f}")
        with r2c2:
            st.metric("Mean Return", fmt_pct(historical["portfolio_mean_return"]))
        with r2c3:
            st.metric("Std Return", fmt_pct(historical["portfolio_std_return"]))

        # Radar chart: Copula vs Historical
        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

        categories = ["VaR 95%", "CVaR 95%", "Max Drawdown", "Volatility"]
        copula_vals = [
            abs(copula["var"]),
            abs(copula["cvar"]),
            abs(copula["max_drawdown_sim"]),
            copula["std_return"],
        ]
        hist_vals = [
            abs(historical["portfolio_var"]),
            abs(historical["portfolio_cvar"]),
            abs(historical["portfolio_max_drawdown"]),
            historical["portfolio_std_return"],
        ]

        fig = go.Figure()
        fig.add_trace(
            go.Scatterpolar(
                r=copula_vals + [copula_vals[0]],
                theta=categories + [categories[0]],
                fill="toself",
                name="Copula",
                line_color=COLORS["blue"],
                fillcolor=f"{COLORS['blue']}30",
            )
        )
        fig.add_trace(
            go.Scatterpolar(
                r=hist_vals + [hist_vals[0]],
                theta=categories + [categories[0]],
                fill="toself",
                name="Historical",
                line_color=COLORS["purple"],
                fillcolor=f"{COLORS['purple']}30",
            )
        )

        fig.update_layout(
            **plotly_dark_layout(
                height=350,
                polar=dict(
                    bgcolor=COLORS["gray_900"],
                    radialaxis=dict(
                        visible=True,
                        gridcolor=COLORS["gray_800"],
                        tickformat=".1%",
                        tickfont=dict(size=9, color=COLORS["gray_500"]),
                    ),
                    angularaxis=dict(
                        gridcolor=COLORS["gray_800"],
                        tickfont=dict(size=10, color=COLORS["gray_400"]),
                    ),
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.05,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=10),
                ),
            )
        )

        st.plotly_chart(fig, use_container_width=True)

    # ── Positions tab ────────────────────────────────────────────────────
    with tab_positions:
        per_position = historical.get("per_position", [])
        if per_position:
            rows = []
            for pp in per_position:
                idx = pp["position_index"]
                t = tickers[idx] if idx < len(tickers) else f"Pos {idx}"
                rows.append(
                    {
                        "Ticker": t,
                        "Weight": f"{pp['weight']:.1%}",
                        "Mean Ret.": f"{pp['mean_return']:.2%}",
                        "Volatility": f"{pp['std_return']:.2%}",
                        "VaR 95%": f"{abs(pp['var']):.2%}",
                        "CVaR 95%": f"{abs(pp['cvar']):.2%}",
                        "Max DD": f"{abs(pp['max_drawdown']):.2%}",
                        "Sharpe": f"{pp['sharpe']:.2f}",
                    }
                )
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No per-position data available.")
