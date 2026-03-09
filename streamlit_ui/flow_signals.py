"""
Flow Signals tab — Insider transactions, institutional holdings, short interest.
Ports FlowSignals.tsx.
"""

import streamlit as st
from streamlit_ui.theme import COLORS


def _fmt_dollars(n: float) -> str:
    if abs(n) >= 1e9:
        return f"${n / 1e9:.2f}B"
    if abs(n) >= 1e6:
        return f"${n / 1e6:.1f}M"
    if abs(n) >= 1e3:
        return f"${n / 1e3:.0f}K"
    return f"${n:,.0f}"


def render_flow_signals(flow_signals: dict):
    """Render the Flow Signals panel."""

    insider = flow_signals.get("insider")
    institutional = flow_signals.get("institutional")
    short_interest = flow_signals.get("short_interest", {})

    # ── Summary Cards ─────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if insider and insider.get("summary"):
            net = insider["summary"]["net_buying"]
            color = COLORS["green"] if net > 0 else COLORS["red"]
            st.markdown(
                f"""
                <div style="text-align:center;background:{COLORS['gray_800']};border-radius:0.75rem;padding:1rem;border:1px solid {color};">
                    <div style="font-size:0.7rem;color:{COLORS['gray_400']};">Net Insider Buying</div>
                    <div style="font-size:1.5rem;font-weight:800;color:{color};">{_fmt_dollars(net)}</div>
                    <div style="font-size:0.65rem;color:{COLORS['gray_500']};">{insider['summary']['n_transactions']} transactions</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style="text-align:center;background:{COLORS['gray_800']};border-radius:0.75rem;padding:1rem;">
                    <div style="font-size:0.7rem;color:{COLORS['gray_400']};">Net Insider Buying</div>
                    <div style="font-size:1.5rem;font-weight:800;color:{COLORS['gray_600']};">N/A</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col2:
        if insider and insider.get("summary", {}).get("cluster_buy_detected"):
            count = insider["summary"]["cluster_buy_count"]
            st.markdown(
                f"""
                <div style="text-align:center;background:{COLORS['gray_800']};border-radius:0.75rem;padding:1rem;border:1px solid {COLORS['green']};">
                    <div style="font-size:0.7rem;color:{COLORS['gray_400']};">Cluster Buy Alert</div>
                    <div style="font-size:1.5rem;font-weight:800;color:{COLORS['green']};">{count} insiders</div>
                    <div style="font-size:0.65rem;color:{COLORS['gray_500']};">within 90 days</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style="text-align:center;background:{COLORS['gray_800']};border-radius:0.75rem;padding:1rem;">
                    <div style="font-size:0.7rem;color:{COLORS['gray_400']};">Cluster Buy Alert</div>
                    <div style="font-size:1.5rem;font-weight:800;color:{COLORS['gray_600']};">None</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col3:
        short_pct = short_interest.get("short_percent_of_float")
        is_high = short_interest.get("short_interest_high", False)
        color = COLORS["red"] if is_high else COLORS["green"]
        val = f"{short_pct * 100:.1f}%" if short_pct is not None else "N/A"
        st.markdown(
            f"""
            <div style="text-align:center;background:{COLORS['gray_800']};border-radius:0.75rem;padding:1rem;border:1px solid {color if short_pct else COLORS['gray_700']};">
                <div style="font-size:0.7rem;color:{COLORS['gray_400']};">Short % of Float</div>
                <div style="font-size:1.5rem;font-weight:800;color:{color if short_pct else COLORS['gray_600']};">{val}</div>
                <div style="font-size:0.65rem;color:{COLORS['gray_500']};">{'HIGH' if is_high else 'Normal' if short_pct else ''}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        if institutional:
            n_notable = institutional.get("n_notable_holders", 0)
            color = COLORS["green"] if n_notable > 0 else COLORS["gray_600"]
            st.markdown(
                f"""
                <div style="text-align:center;background:{COLORS['gray_800']};border-radius:0.75rem;padding:1rem;border:1px solid {color};">
                    <div style="font-size:0.7rem;color:{COLORS['gray_400']};">Notable Value Investors</div>
                    <div style="font-size:1.5rem;font-weight:800;color:{color};">{n_notable}</div>
                    <div style="font-size:0.65rem;color:{COLORS['gray_500']};">tracked firms</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style="text-align:center;background:{COLORS['gray_800']};border-radius:0.75rem;padding:1rem;">
                    <div style="font-size:0.7rem;color:{COLORS['gray_400']};">Notable Value Investors</div>
                    <div style="font-size:1.5rem;font-weight:800;color:{COLORS['gray_600']};">N/A</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Insider Transactions Table ────────────────────────────────────────
    if insider and insider.get("transactions"):
        st.markdown(
            f"<div style='font-size:0.85rem;color:{COLORS['gray_400']};margin:1.5rem 0 0.5rem;font-weight:600;'>Recent Insider Transactions</div>",
            unsafe_allow_html=True,
        )

        for txn in insider["transactions"][:20]:
            txn_type = txn.get("transaction_type", "")
            icon = "🟢" if txn_type == "Buy" else "🔴"
            color = COLORS["green"] if txn_type == "Buy" else COLORS["red"]
            title = txn.get("officer_title", "")
            title_str = f" ({title})" if title else ""

            st.markdown(
                f"""
                <div style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    padding:0.4rem 0.75rem;
                    border-bottom:1px solid {COLORS['gray_800']};
                    font-size:0.8rem;
                ">
                    <span>
                        {icon} <span style="color:{COLORS['gray_300']};">{txn.get('owner', 'Unknown')}{title_str}</span>
                        <span style="color:{COLORS['gray_500']};margin-left:0.5rem;">{txn.get('date', '')}</span>
                    </span>
                    <span>
                        <span style="color:{color};font-weight:600;">{txn_type}</span>
                        <span style="color:{COLORS['gray_400']};margin-left:0.75rem;">{int(txn.get('shares', 0)):,} shares @ ${txn.get('price', 0):.2f}</span>
                        <span style="color:{COLORS['gray_300']};margin-left:0.75rem;font-weight:600;">{_fmt_dollars(txn.get('value', 0))}</span>
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Notable Value Investors ───────────────────────────────────────────
    if institutional and institutional.get("notable_holders"):
        st.markdown(
            f"<div style='font-size:0.85rem;color:{COLORS['gray_400']};margin:1.5rem 0 0.5rem;font-weight:600;'>Notable Value Investors Holding</div>",
            unsafe_allow_html=True,
        )

        for holder in institutional["notable_holders"]:
            st.markdown(
                f"""
                <div style="
                    display:flex;
                    justify-content:space-between;
                    padding:0.4rem 0.75rem;
                    border-bottom:1px solid {COLORS['gray_800']};
                    font-size:0.8rem;
                ">
                    <span style="color:{COLORS['green']};font-weight:600;">{holder['name']}</span>
                    <span style="color:{COLORS['gray_400']};">{holder.get('shares', 0):,} shares · {_fmt_dollars(holder.get('value', 0))}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Top Institutional Holders ─────────────────────────────────────────
    if institutional and institutional.get("top_holders"):
        st.markdown(
            f"<div style='font-size:0.85rem;color:{COLORS['gray_400']};margin:1.5rem 0 0.5rem;font-weight:600;'>Top Institutional Holders</div>",
            unsafe_allow_html=True,
        )

        for holder in institutional["top_holders"]:
            pct_str = f"{holder.get('pct_held', 0) * 100:.2f}%" if holder.get("pct_held") else ""
            st.markdown(
                f"""
                <div style="
                    display:flex;
                    justify-content:space-between;
                    padding:0.35rem 0.75rem;
                    border-bottom:1px solid {COLORS['gray_800']};
                    font-size:0.78rem;
                ">
                    <span style="color:{COLORS['gray_300']};">{holder['name']}</span>
                    <span style="color:{COLORS['gray_500']};">{pct_str} · {_fmt_dollars(holder.get('value', 0))}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
