"""
Shared theme constants, CSS injection, and formatting helpers for the Streamlit UI.
Matches the React dark theme (Tailwind gray-950 palette, blue/green/red/amber accents).
"""

import streamlit as st
import plotly.graph_objects as go

# ── Color palette (Tailwind equivalents) ─────────────────────────────────────

COLORS = {
    "red": "#ef4444",
    "amber": "#f59e0b",
    "green": "#22c55e",
    "blue": "#3b82f6",
    "purple": "#8b5cf6",
    "cyan": "#06b6d4",
    "white": "#ffffff",
    "gray_50": "#f9fafb",
    "gray_400": "#9ca3af",
    "gray_500": "#6b7280",
    "gray_600": "#4b5563",
    "gray_700": "#374151",
    "gray_800": "#1f2937",
    "gray_900": "#111827",
    "gray_950": "#030712",
}


def inject_custom_css():
    """Inject custom CSS for dark theme refinements beyond config.toml."""
    st.markdown(
        """
        <style>
        /* Metric cards */
        [data-testid="stMetric"] {
            background-color: #1f2937;
            border: 1px solid #374151;
            border-radius: 0.75rem;
            padding: 0.75rem 1rem;
        }
        [data-testid="stMetric"] label {
            color: #9ca3af;
        }

        /* Sidebar item spacing */
        section[data-testid="stSidebar"] .stButton > button {
            width: 100%;
            text-align: left;
            background-color: transparent;
            border: none;
            border-bottom: 1px solid #1f293780;
            border-radius: 0;
            padding: 0.75rem 0.5rem;
            color: #f9fafb;
            font-size: 0.85rem;
        }
        section[data-testid="stSidebar"] .stButton > button:hover {
            background-color: #1f293780;
        }

        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.25rem;
            background-color: #1f293780;
            border-radius: 0.75rem;
            padding: 0.25rem;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 0.5rem;
            padding: 0.5rem 1rem;
            color: #9ca3af;
        }
        .stTabs [aria-selected="true"] {
            background-color: #3b82f6;
            color: #ffffff;
        }

        /* Tables */
        .stDataFrame {
            border: 1px solid #374151;
            border-radius: 0.5rem;
        }

        /* Dividers */
        hr {
            border-color: #374151;
        }

        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── Formatting helpers ───────────────────────────────────────────────────────


def fmt_dollar(n: float) -> str:
    """Format dollar amounts: $1.2k, $1.2M, $1.2B."""
    if abs(n) >= 1_000_000_000:
        return f"${n / 1_000_000_000:.1f}B"
    if abs(n) >= 1_000_000:
        return f"${n / 1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"${n / 1_000:.1f}k"
    return f"${n:.2f}"


def fmt_pct(n: float) -> str:
    """Format a fraction as percentage with 1 decimal place."""
    return f"{n * 100:.1f}%"


def fmt_price(n: float) -> str:
    """Format a stock price."""
    return f"${n:,.2f}"


def fmt_large(n: float) -> str:
    """Format large numbers (market cap, revenue)."""
    if abs(n) >= 1_000_000_000:
        return f"${n / 1_000_000_000:.1f}B"
    if abs(n) >= 1_000_000:
        return f"${n / 1_000_000:.0f}M"
    return f"${n:,.0f}"


# ── Plotly dark template ─────────────────────────────────────────────────────


def plotly_dark_layout(**overrides) -> dict:
    """Return a Plotly layout dict matching the dark theme."""
    base = dict(
        template="plotly_dark",
        paper_bgcolor=COLORS["gray_900"],
        plot_bgcolor=COLORS["gray_900"],
        font=dict(color=COLORS["gray_400"], size=11),
        margin=dict(l=50, r=20, t=30, b=40),
        xaxis=dict(gridcolor=COLORS["gray_800"], zerolinecolor=COLORS["gray_700"]),
        yaxis=dict(gridcolor=COLORS["gray_800"], zerolinecolor=COLORS["gray_700"]),
    )
    base.update(overrides)
    return base


def score_color(score: float) -> str:
    """Return color based on Klarman score thresholds."""
    if score >= 50:
        return COLORS["green"]
    if score >= 25:
        return COLORS["amber"]
    return COLORS["red"]
