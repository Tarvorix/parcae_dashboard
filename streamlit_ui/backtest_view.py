"""
Backtest Results — equity curve + performance metrics.
"""

import streamlit as st
import plotly.graph_objects as go
from streamlit_ui.theme import COLORS, PLOTLY_TEMPLATE


def _pct(n: float, dp: int = 2) -> str:
    return f"{n * 100:.{dp}f}%"


def _fmt_dollars(n: float) -> str:
    if abs(n) >= 1e6:
        return f"${n / 1e6:.2f}M"
    return f"${n:,.0f}"


def render_backtest_view(result: dict):
    """Render the backtest results panel."""

    portfolio = result["portfolio"]
    benchmark = result["benchmark_results"]
    alpha = result["alpha"]
    series = result["monthly_series"]

    # ── Metric Cards ──────────────────────────────────────────────────────
    st.markdown(
        f"<div style='font-size:0.85rem;color:{COLORS['gray_400']};margin-bottom:0.75rem;font-weight:600;'>"
        f"Backtest: {result['weighting'].title()}-weight Top {result['top_n']} · {result['years']}yr · "
        f"{len(result['tickers_held'])} tickers held</div>",
        unsafe_allow_html=True,
    )

    alpha_color = COLORS["green"] if alpha > 0 else COLORS["red"]

    cols = st.columns(7)
    metrics = [
        ("CAGR", _pct(portfolio["cagr"]), _pct(benchmark["cagr"]), None),
        ("Total Return", _pct(portfolio["total_return"]), _pct(benchmark["total_return"]), None),
        ("Max Drawdown", _pct(portfolio["max_drawdown"]), _pct(benchmark["max_drawdown"]), None),
        ("Sharpe", f"{portfolio['sharpe']:.2f}", f"{benchmark['sharpe']:.2f}", None),
        ("Calmar", f"{portfolio['calmar']:.2f}", f"{benchmark['calmar']:.2f}", None),
        ("Win Rate", _pct(portfolio["win_rate"]), "—", None),
        ("Alpha", _pct(alpha), "—", alpha_color),
    ]

    for i, (label, p_val, b_val, color) in enumerate(metrics):
        with cols[i]:
            card_color = color or COLORS["blue"]
            st.markdown(
                f"""
                <div style="text-align:center;background:{COLORS['gray_800']};border-radius:0.75rem;padding:0.75rem;border:1px solid {COLORS['gray_700']};">
                    <div style="font-size:0.65rem;color:{COLORS['gray_400']};">{label}</div>
                    <div style="font-size:1.1rem;font-weight:700;color:{card_color};">{p_val}</div>
                    <div style="font-size:0.6rem;color:{COLORS['gray_500']};">Bench: {b_val}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Equity Curve ──────────────────────────────────────────────────────
    dates = [s["date"] for s in series]
    p_equity = [s["portfolio_equity"] for s in series]
    b_equity = [s["benchmark_equity"] for s in series]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=p_equity,
        name="Portfolio",
        line=dict(color=COLORS["blue"], width=2),
        fill="tozeroy",
        fillcolor="rgba(59,130,246,0.1)",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=b_equity,
        name=result["benchmark"],
        line=dict(color=COLORS["gray_500"], width=1.5, dash="dot"),
    ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title=dict(text="Equity Curve", font=dict(size=14)),
        yaxis_title="Portfolio Value ($)",
        xaxis_title="Date",
        height=400,
        margin=dict(t=60, b=40, l=60, r=20),
        legend=dict(x=0.02, y=0.98),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Final Values ──────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
            <div style="text-align:center;background:{COLORS['gray_800']};border-radius:0.75rem;padding:1rem;">
                <div style="font-size:0.75rem;color:{COLORS['gray_400']};">Portfolio Final Value</div>
                <div style="font-size:1.5rem;font-weight:800;color:{COLORS['blue']};">{_fmt_dollars(portfolio['final_value'])}</div>
                <div style="font-size:0.7rem;color:{COLORS['gray_500']};">from {_fmt_dollars(result['initial_capital'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div style="text-align:center;background:{COLORS['gray_800']};border-radius:0.75rem;padding:1rem;">
                <div style="font-size:0.75rem;color:{COLORS['gray_400']};">{result['benchmark']} Final Value</div>
                <div style="font-size:1.5rem;font-weight:800;color:{COLORS['gray_500']};">{_fmt_dollars(benchmark['final_value'])}</div>
                <div style="font-size:0.7rem;color:{COLORS['gray_500']};">from {_fmt_dollars(result['initial_capital'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Tickers Held ──────────────────────────────────────────────────────
    with st.expander("Tickers Held"):
        st.write(", ".join(result["tickers_held"]))
