"""
Quality & Distress Scoring — Piotroski F-Score, Altman Z-Score, Beneish M-Score

Three complementary financial quality models:
- **Piotroski F-Score** (0–9): fundamental strength checklist
- **Altman Z-Score**: bankruptcy probability predictor
- **Beneish M-Score**: earnings manipulation detector
"""

from typing import Optional

from backend.config import KlarmanThresholds

config = KlarmanThresholds()


# ── Piotroski F-Score ────────────────────────────────────────────────────────

def _safe_ratio(numerator, denominator):
    """Return numerator/denominator or None if either is missing or denominator is zero."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def calculate_piotroski_f_score(
    edgar_data: dict,
    yf_data: dict,
) -> Optional[dict]:
    """
    Piotroski F-Score (0–9): 9 binary signals assessing fundamental strength.

    Requires at least 2 years of EDGAR data for year-over-year comparisons.
    Returns None if insufficient data.

    Components:
      Profitability (4):
        1. ROA > 0
        2. CFO > 0
        3. ΔROA > 0 (ROA improved YoY)
        4. Accruals: CFO > Net Income (cash-backed earnings)
      Leverage / Liquidity (3):
        5. ΔLeverage < 0 (LTD/TA decreased)
        6. ΔCurrent Ratio > 0 (liquidity improved)
        7. No dilution (shares didn't increase)
      Operating Efficiency (2):
        8. ΔGross Margin > 0
        9. ΔAsset Turnover > 0 (Revenue/TA improved)
    """
    if not edgar_data:
        return None

    # Need at least 2 years for YoY comparisons
    ni = edgar_data.get("net_incomes", [])
    ta = edgar_data.get("total_assets", [])
    cfo = edgar_data.get("cfo_list", [])
    ltd = edgar_data.get("long_term_debt", [])
    ca = edgar_data.get("current_assets", [])
    cl = edgar_data.get("current_liabilities", [])
    shares = edgar_data.get("shares_outstanding_hist", [])
    gp = edgar_data.get("gross_profits", [])
    revs = edgar_data.get("revenues", [])

    if len(ni) < 2 or len(ta) < 2:
        return None

    # Check that we have non-None values for at least the last 2 years of total_assets
    ta_curr = ta[-1]
    ta_prev = ta[-2]
    if ta_curr is None or ta_prev is None or ta_curr == 0 or ta_prev == 0:
        return None

    # ── 1. ROA > 0 ──
    ni_curr = ni[-1] if ni[-1] is not None else 0
    roa_curr = ni_curr / ta_curr
    roa_positive = roa_curr > 0

    # ── 2. CFO > 0 ──
    cfo_curr = _get_last_valid(cfo)
    cfo_positive = cfo_curr is not None and cfo_curr > 0

    # ── 3. ΔROA > 0 ──
    ni_prev = ni[-2] if ni[-2] is not None else 0
    roa_prev = ni_prev / ta_prev
    delta_roa = roa_curr > roa_prev

    # ── 4. Accruals: CFO > NI ──
    accrual_quality = cfo_curr is not None and cfo_curr > ni_curr

    # ── 5. ΔLeverage < 0 ──
    ltd_curr = _get_last_valid(ltd)
    ltd_prev = _get_prev_valid(ltd)
    if ltd_curr is not None and ltd_prev is not None and ta_curr > 0 and ta_prev > 0:
        lev_curr = ltd_curr / ta_curr
        lev_prev = ltd_prev / ta_prev
        delta_leverage = lev_curr < lev_prev
    else:
        delta_leverage = False

    # ── 6. ΔCurrent Ratio > 0 ──
    ca_curr = _get_last_valid(ca)
    cl_curr = _get_last_valid(cl)
    ca_prev = _get_prev_valid(ca)
    cl_prev = _get_prev_valid(cl)
    if (ca_curr is not None and cl_curr is not None and cl_curr > 0
            and ca_prev is not None and cl_prev is not None and cl_prev > 0):
        cr_curr = ca_curr / cl_curr
        cr_prev = ca_prev / cl_prev
        delta_current_ratio = cr_curr > cr_prev
    else:
        delta_current_ratio = False

    # ── 7. No dilution ──
    sh_curr = _get_last_valid(shares)
    sh_prev = _get_prev_valid(shares)
    if sh_curr is not None and sh_prev is not None:
        no_dilution = sh_curr <= sh_prev
    else:
        # If we can't determine, assume no dilution (conservative)
        no_dilution = True

    # ── 8. ΔGross Margin > 0 ──
    gp_curr = _get_last_valid(gp)
    gp_prev = _get_prev_valid(gp)
    rev_curr = revs[-1] if revs and revs[-1] is not None else None
    rev_prev = revs[-2] if len(revs) >= 2 and revs[-2] is not None else None
    if (gp_curr is not None and gp_prev is not None
            and rev_curr and rev_curr > 0 and rev_prev and rev_prev > 0):
        gm_curr = gp_curr / rev_curr
        gm_prev = gp_prev / rev_prev
        delta_gross_margin = gm_curr > gm_prev
    else:
        delta_gross_margin = False

    # ── 9. ΔAsset Turnover > 0 ──
    if rev_curr and rev_prev and ta_curr > 0 and ta_prev > 0:
        at_curr = rev_curr / ta_curr
        at_prev = rev_prev / ta_prev
        delta_asset_turnover = at_curr > at_prev
    else:
        delta_asset_turnover = False

    components = {
        "roa_positive": roa_positive,
        "cfo_positive": cfo_positive,
        "delta_roa": delta_roa,
        "accrual_quality": accrual_quality,
        "delta_leverage": delta_leverage,
        "delta_current_ratio": delta_current_ratio,
        "no_dilution": no_dilution,
        "delta_gross_margin": delta_gross_margin,
        "delta_asset_turnover": delta_asset_turnover,
    }

    f_score = sum(1 for v in components.values() if v)

    if f_score >= 7:
        classification = "Strong"
    elif f_score >= 4:
        classification = "Neutral"
    else:
        classification = "Weak"

    return {
        "f_score": f_score,
        "components": components,
        "classification": classification,
    }


def _get_last_valid(lst):
    """Get the last non-None value from a list."""
    if not lst:
        return None
    for i in range(len(lst) - 1, -1, -1):
        if lst[i] is not None:
            return lst[i]
    return None


def _get_prev_valid(lst):
    """Get the second-to-last non-None value from a list."""
    if not lst or len(lst) < 2:
        return None
    for i in range(len(lst) - 2, -1, -1):
        if lst[i] is not None:
            return lst[i]
    return None


# ── Altman Z-Score ───────────────────────────────────────────────────────────

def calculate_altman_z_score(
    yf_data: dict,
    edgar_data: Optional[dict] = None,
) -> Optional[dict]:
    """
    Altman Z-Score — bankruptcy prediction model for public companies.

    Z = 1.2×X1 + 1.4×X2 + 3.3×X3 + 0.6×X4 + 1.0×X5

    Where:
      X1 = Working Capital / Total Assets
      X2 = Retained Earnings / Total Assets
      X3 = EBIT / Total Assets
      X4 = Market Cap / Total Liabilities
      X5 = Revenue / Total Assets

    Zones:
      Z > 2.99  → Safe
      1.81–2.99 → Grey zone
      Z < 1.81  → Distress

    Returns None if total_assets or total_liabilities is missing/zero.
    """
    total_assets = yf_data.get("total_assets")
    total_liabilities = yf_data.get("total_liabilities")

    if not total_assets or total_assets <= 0:
        return None
    if total_liabilities is None:
        return None

    working_capital = yf_data.get("working_capital") or 0
    retained_earnings = yf_data.get("retained_earnings") or 0
    ebit = yf_data.get("ebit") or 0
    market_cap = yf_data.get("market_cap") or 0
    revenue = yf_data.get("total_revenue") or 0

    x1 = working_capital / total_assets
    x2 = retained_earnings / total_assets
    x3 = ebit / total_assets
    x4 = market_cap / total_liabilities if total_liabilities > 0 else 0
    x5 = revenue / total_assets

    z_score = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

    if z_score > config.altman_z_safe_threshold:
        zone = "Safe"
    elif z_score >= config.altman_z_distress_threshold:
        zone = "Grey"
    else:
        zone = "Distress"

    return {
        "z_score": round(z_score, 4),
        "components": {
            "x1_working_capital_ta": round(x1, 4),
            "x2_retained_earnings_ta": round(x2, 4),
            "x3_ebit_ta": round(x3, 4),
            "x4_market_cap_tl": round(x4, 4),
            "x5_revenue_ta": round(x5, 4),
        },
        "zone": zone,
    }


# ── Beneish M-Score ──────────────────────────────────────────────────────────

def calculate_beneish_m_score(
    edgar_data: dict,
) -> Optional[dict]:
    """
    Beneish M-Score — detects earnings manipulation.

    M = −4.84 + 0.920×DSRI + 0.528×GMI + 0.404×AQI + 0.892×SGI
        + 0.115×DEPI − 0.172×SGAI + 4.679×TATA − 0.327×LVGI

    Requires at least 2 years of detailed financial data.
    Returns None if insufficient data.

    M > −1.78 → likely manipulator
    M ≤ −1.78 → unlikely manipulator
    """
    if not edgar_data:
        return None

    revs = edgar_data.get("revenues", [])
    ni = edgar_data.get("net_incomes", [])
    recv = edgar_data.get("receivables", [])
    gp = edgar_data.get("gross_profits", [])
    ta = edgar_data.get("total_assets", [])
    ca = edgar_data.get("current_assets", [])
    ppe = edgar_data.get("ppe_net", [])
    dep = edgar_data.get("depreciation", [])
    sga = edgar_data.get("sga_expenses", [])
    tl = edgar_data.get("total_liabilities", [])
    cfo = edgar_data.get("cfo_list", [])

    if len(revs) < 2:
        return None

    # Get current (t) and prior (t-1) values
    rev_t = revs[-1]
    rev_t1 = revs[-2]
    if not rev_t or not rev_t1 or rev_t <= 0 or rev_t1 <= 0:
        return None

    # DSRI = Days Sales in Receivables Index
    recv_t = _get_val(recv, -1)
    recv_t1 = _get_val(recv, -2)
    if recv_t is not None and recv_t1 is not None and recv_t1 > 0 and rev_t1 > 0:
        dsri = (recv_t / rev_t) / (recv_t1 / rev_t1)
    else:
        dsri = 1.0  # neutral

    # GMI = Gross Margin Index (>1 = margins deteriorated)
    gp_t = _get_val(gp, -1)
    gp_t1 = _get_val(gp, -2)
    if gp_t is not None and gp_t1 is not None and rev_t > 0 and rev_t1 > 0:
        gm_t = gp_t / rev_t
        gm_t1 = gp_t1 / rev_t1
        gmi = gm_t1 / gm_t if gm_t > 0 else 1.0
    else:
        gmi = 1.0

    # AQI = Asset Quality Index
    ta_t = _get_val(ta, -1)
    ta_t1 = _get_val(ta, -2)
    ca_t = _get_val(ca, -1)
    ca_t1 = _get_val(ca, -2)
    ppe_t = _get_val(ppe, -1)
    ppe_t1 = _get_val(ppe, -2)
    if (ta_t and ta_t1 and ta_t > 0 and ta_t1 > 0
            and ca_t is not None and ppe_t is not None
            and ca_t1 is not None and ppe_t1 is not None):
        aq_t = 1 - (ca_t + ppe_t) / ta_t
        aq_t1 = 1 - (ca_t1 + ppe_t1) / ta_t1
        aqi = aq_t / aq_t1 if aq_t1 != 0 else 1.0
    else:
        aqi = 1.0

    # SGI = Sales Growth Index
    sgi = rev_t / rev_t1

    # DEPI = Depreciation Index
    dep_t = _get_val(dep, -1)
    dep_t1 = _get_val(dep, -2)
    if (dep_t is not None and dep_t1 is not None
            and ppe_t is not None and ppe_t1 is not None):
        dep_rate_t = dep_t / (dep_t + ppe_t) if (dep_t + ppe_t) > 0 else 0
        dep_rate_t1 = dep_t1 / (dep_t1 + ppe_t1) if (dep_t1 + ppe_t1) > 0 else 0
        depi = dep_rate_t1 / dep_rate_t if dep_rate_t > 0 else 1.0
    else:
        depi = 1.0

    # SGAI = SGA Expense Index
    sga_t = _get_val(sga, -1)
    sga_t1 = _get_val(sga, -2)
    if sga_t is not None and sga_t1 is not None and rev_t > 0 and rev_t1 > 0:
        sgai = (sga_t / rev_t) / (sga_t1 / rev_t1) if (sga_t1 / rev_t1) > 0 else 1.0
    else:
        sgai = 1.0

    # TATA = Total Accruals to Total Assets
    ni_t = _get_val(ni, -1)
    cfo_t = _get_val(cfo, -1)
    if ni_t is not None and cfo_t is not None and ta_t and ta_t > 0:
        tata = (ni_t - cfo_t) / ta_t
    else:
        tata = 0.0

    # LVGI = Leverage Index
    tl_t = _get_val(tl, -1)
    tl_t1 = _get_val(tl, -2)
    if tl_t is not None and tl_t1 is not None and ta_t and ta_t1 and ta_t > 0 and ta_t1 > 0:
        lev_t = tl_t / ta_t
        lev_t1 = tl_t1 / ta_t1
        lvgi = lev_t / lev_t1 if lev_t1 > 0 else 1.0
    else:
        lvgi = 1.0

    m_score = (
        -4.84
        + 0.920 * dsri
        + 0.528 * gmi
        + 0.404 * aqi
        + 0.892 * sgi
        + 0.115 * depi
        - 0.172 * sgai
        + 4.679 * tata
        - 0.327 * lvgi
    )

    return {
        "m_score": round(m_score, 4),
        "components": {
            "dsri": round(dsri, 4),
            "gmi": round(gmi, 4),
            "aqi": round(aqi, 4),
            "sgi": round(sgi, 4),
            "depi": round(depi, 4),
            "sgai": round(sgai, 4),
            "tata": round(tata, 4),
            "lvgi": round(lvgi, 4),
        },
        "likely_manipulator": m_score > config.beneish_manipulation_threshold,
    }


def _get_val(lst, idx):
    """Safely get a value from a list by index, returning None if out of range or None."""
    if not lst or abs(idx) > len(lst):
        return None
    try:
        val = lst[idx]
        return val  # may be None
    except IndexError:
        return None


# ── Composite ────────────────────────────────────────────────────────────────

def calculate_quality_scores(
    yf_data: dict,
    edgar_data: Optional[dict],
) -> dict:
    """
    Calculate all three quality/distress scores.

    Returns a dict with piotroski, altman, and beneish sub-dicts.
    Each may be None if insufficient data.
    """
    return {
        "piotroski": calculate_piotroski_f_score(edgar_data, yf_data) if edgar_data else None,
        "altman": calculate_altman_z_score(yf_data, edgar_data),
        "beneish": calculate_beneish_m_score(edgar_data) if edgar_data else None,
    }
