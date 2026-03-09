"""
Quality & Distress tab — Piotroski F-Score, Altman Z-Score, Beneish M-Score.
Ports QualityPanel.tsx.
"""

import streamlit as st
from streamlit_ui.theme import COLORS


def _score_badge(label: str, value, color: str, subtitle: str = ""):
    """Render a centered score card with colored value."""
    sub_html = f'<div style="font-size:0.7rem;color:{COLORS["gray_500"]};">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div style="
            text-align:center;
            background-color:{COLORS['gray_800']};
            border:2px solid {color};
            border-radius:1rem;
            padding:1.25rem;
            margin-bottom:0.75rem;
        ">
            <div style="font-size:0.75rem;color:{COLORS['gray_400']};">{label}</div>
            <div style="font-size:2.5rem;font-weight:800;color:{color};">{value}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _piotroski_color(score: int) -> str:
    if score >= 7:
        return COLORS["green"]
    elif score >= 4:
        return COLORS["amber"]
    else:
        return COLORS["red"]


def _altman_color(zone: str) -> str:
    if zone == "Safe":
        return COLORS["green"]
    elif zone == "Grey":
        return COLORS["amber"]
    else:
        return COLORS["red"]


def _beneish_color(likely_manipulator: bool) -> str:
    return COLORS["red"] if likely_manipulator else COLORS["green"]


def render_quality_panel(quality_scores: dict):
    """Render the Quality & Distress scoring panel."""

    piotroski = quality_scores.get("piotroski")
    altman = quality_scores.get("altman")
    beneish = quality_scores.get("beneish")

    if not piotroski and not altman and not beneish:
        st.info("Quality scores unavailable — insufficient financial data.")
        return

    # ── Hero score cards ──────────────────────────────────────────────────
    cols = st.columns(3)

    with cols[0]:
        if piotroski:
            color = _piotroski_color(piotroski["f_score"])
            _score_badge(
                "Piotroski F-Score",
                f"{piotroski['f_score']} / 9",
                color,
                piotroski["classification"],
            )
        else:
            _score_badge("Piotroski F-Score", "N/A", COLORS["gray_600"], "Insufficient EDGAR data")

    with cols[1]:
        if altman:
            color = _altman_color(altman["zone"])
            _score_badge(
                "Altman Z-Score",
                f"{altman['z_score']:.2f}",
                color,
                altman["zone"],
            )
        else:
            _score_badge("Altman Z-Score", "N/A", COLORS["gray_600"], "Missing balance sheet data")

    with cols[2]:
        if beneish:
            color = _beneish_color(beneish["likely_manipulator"])
            flag = "Likely Manipulator" if beneish["likely_manipulator"] else "Unlikely Manipulator"
            _score_badge(
                "Beneish M-Score",
                f"{beneish['m_score']:.2f}",
                color,
                flag,
            )
        else:
            _score_badge("Beneish M-Score", "N/A", COLORS["gray_600"], "Insufficient EDGAR data")

    # ── Piotroski 9-Item Checklist ────────────────────────────────────────
    if piotroski:
        st.markdown(
            f"<div style='font-size:0.85rem;color:{COLORS['gray_400']};margin:1rem 0 0.5rem;font-weight:600;'>Piotroski F-Score Components</div>",
            unsafe_allow_html=True,
        )

        component_labels = {
            "roa_positive": "ROA > 0 (Positive net income / total assets)",
            "cfo_positive": "CFO > 0 (Positive operating cash flow)",
            "delta_roa_positive": "ROA Improving (YoY increase)",
            "accrual_quality": "Accrual Quality (CFO > Net Income)",
            "delta_leverage_down": "Leverage Decreasing (LTD/TA declining)",
            "delta_current_ratio_up": "Current Ratio Improving (YoY increase)",
            "no_dilution": "No Dilution (Shares stable or decreasing)",
            "delta_gross_margin_up": "Gross Margin Improving (YoY increase)",
            "delta_asset_turnover_up": "Asset Turnover Improving (Rev/TA increasing)",
        }

        for key, label in component_labels.items():
            passed = piotroski["components"].get(key, False)
            icon = "✅" if passed else "❌"
            text_color = COLORS["green"] if passed else COLORS["red"]
            st.markdown(
                f"""
                <div style="
                    display:flex;
                    align-items:center;
                    justify-content:space-between;
                    padding:0.4rem 0.75rem;
                    border-bottom:1px solid {COLORS['gray_800']};
                    font-size:0.8rem;
                ">
                    <span>{icon} {label}</span>
                    <span style="color:{text_color};font-weight:600;">{'PASS' if passed else 'FAIL'}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Altman Z-Score Components ─────────────────────────────────────────
    if altman:
        st.markdown(
            f"<div style='font-size:0.85rem;color:{COLORS['gray_400']};margin:1.5rem 0 0.5rem;font-weight:600;'>Altman Z-Score Components</div>",
            unsafe_allow_html=True,
        )

        altman_labels = {
            "x1_working_capital_ta": ("X1: Working Capital / Total Assets", 1.2),
            "x2_retained_earnings_ta": ("X2: Retained Earnings / Total Assets", 1.4),
            "x3_ebit_ta": ("X3: EBIT / Total Assets", 3.3),
            "x4_market_cap_tl": ("X4: Market Cap / Total Liabilities", 0.6),
            "x5_revenue_ta": ("X5: Revenue / Total Assets", 1.0),
        }

        for key, (label, weight) in altman_labels.items():
            val = altman["components"].get(key, 0)
            weighted = val * weight
            st.markdown(
                f"""
                <div style="
                    display:flex;
                    align-items:center;
                    justify-content:space-between;
                    padding:0.4rem 0.75rem;
                    border-bottom:1px solid {COLORS['gray_800']};
                    font-size:0.8rem;
                ">
                    <span style="color:{COLORS['gray_300']};">{label}</span>
                    <span>
                        <span style="color:{COLORS['gray_500']};margin-right:1rem;">Ratio: {val:.4f}</span>
                        <span style="color:{COLORS['blue']};font-weight:600;">Weighted: {weighted:.4f}</span>
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Zone reference
        st.markdown(
            f"""
            <div style="
                display:flex;
                gap:1rem;
                justify-content:center;
                margin-top:0.75rem;
                font-size:0.75rem;
            ">
                <span style="color:{COLORS['green']};">Safe &gt; 2.99</span>
                <span style="color:{COLORS['amber']};">Grey 1.81 – 2.99</span>
                <span style="color:{COLORS['red']};">Distress &lt; 1.81</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Beneish M-Score Components ────────────────────────────────────────
    if beneish:
        st.markdown(
            f"<div style='font-size:0.85rem;color:{COLORS['gray_400']};margin:1.5rem 0 0.5rem;font-weight:600;'>Beneish M-Score Variables</div>",
            unsafe_allow_html=True,
        )

        beneish_labels = {
            "dsri": ("DSRI — Days Sales in Receivables Index", "Rising receivables vs revenue"),
            "gmi": ("GMI — Gross Margin Index", ">1 = deteriorating margins"),
            "aqi": ("AQI — Asset Quality Index", "Non-current asset growth vs total"),
            "sgi": ("SGI — Sales Growth Index", "Revenue growth rate"),
            "depi": ("DEPI — Depreciation Index", ">1 = slowing depreciation"),
            "sgai": ("SGAI — SGA Expense Index", "SGA growth vs revenue growth"),
            "tata": ("TATA — Total Accruals to Total Assets", "Earnings quality signal"),
            "lvgi": ("LVGI — Leverage Index", ">1 = increasing leverage"),
        }

        for key, (label, tooltip) in beneish_labels.items():
            val = beneish["components"].get(key, 0)
            # Flag concerning values
            is_concern = False
            if key == "dsri" and val > 1.05:
                is_concern = True
            elif key == "gmi" and val > 1.0:
                is_concern = True
            elif key == "aqi" and val > 1.0:
                is_concern = True
            elif key == "sgi" and val > 1.20:
                is_concern = True
            elif key == "tata" and val > 0.05:
                is_concern = True
            elif key == "lvgi" and val > 1.10:
                is_concern = True

            val_color = COLORS["red"] if is_concern else COLORS["green"]
            st.markdown(
                f"""
                <div style="
                    display:flex;
                    align-items:center;
                    justify-content:space-between;
                    padding:0.4rem 0.75rem;
                    border-bottom:1px solid {COLORS['gray_800']};
                    font-size:0.8rem;
                " title="{tooltip}">
                    <span style="color:{COLORS['gray_300']};">{label}</span>
                    <span style="color:{val_color};font-weight:600;">{val:.4f}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Threshold reference
        manip_color = COLORS["red"] if beneish["likely_manipulator"] else COLORS["green"]
        st.markdown(
            f"""
            <div style="
                text-align:center;
                margin-top:0.75rem;
                font-size:0.75rem;
                color:{manip_color};
            ">
                M-Score = {beneish['m_score']:.2f} — Threshold: -1.78 (M &gt; -1.78 = likely manipulation)
            </div>
            """,
            unsafe_allow_html=True,
        )
