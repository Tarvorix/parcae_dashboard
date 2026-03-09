"""Unit tests for backend/engine/quality_scores.py

Pure math tests — no mocks or network calls needed.
"""

import pytest

from backend.engine.quality_scores import (
    calculate_piotroski_f_score,
    calculate_altman_z_score,
    calculate_beneish_m_score,
    calculate_quality_scores,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_healthy_edgar(n: int = 5) -> dict:
    """Synthetic EDGAR data for a healthy, improving company."""
    return {
        "revenues": [100e6 * (1.05 ** i) for i in range(n)],
        "net_incomes": [10e6 * (1.05 ** i) for i in range(n)],
        "fcfs": [8e6 * (1.05 ** i) for i in range(n)],
        "margins": [0.10] * n,
        "capex": [4e6] * n,
        "total_assets": [200e6 * (1.03 ** i) for i in range(n)],
        "total_liabilities": [80e6 * (1.02 ** i) for i in range(n)],
        "long_term_debt": [50e6 * (0.98 ** i) for i in range(n)],  # decreasing
        "current_assets": [60e6 * (1.03 ** i) for i in range(n)],
        "current_liabilities": [30e6 * (1.01 ** i) for i in range(n)],
        "shares_outstanding_hist": [10e6] * n,  # no dilution
        "gross_profits": [40e6 * (1.06 ** i) for i in range(n)],  # improving margins
        "depreciation": [5e6] * n,
        "sga_expenses": [15e6] * n,
        "receivables": [12e6] * n,
        "ppe_net": [80e6] * n,
        "cfo_list": [12e6 * (1.05 ** i) for i in range(n)],  # CFO > NI
    }


def make_distressed_edgar(n: int = 5) -> dict:
    """Synthetic EDGAR data for a deteriorating company."""
    return {
        "revenues": [100e6 * (0.90 ** i) for i in range(n)],  # declining
        "net_incomes": [-5e6 * (1 + i * 0.2) for i in range(n)],  # worsening losses
        "fcfs": [-3e6] * n,
        "margins": [-0.05] * n,
        "capex": [4e6] * n,
        "total_assets": [200e6 * (0.97 ** i) for i in range(n)],  # shrinking
        "total_liabilities": [150e6 * (1.05 ** i) for i in range(n)],  # growing
        "long_term_debt": [100e6 * (1.10 ** i) for i in range(n)],  # increasing
        "current_assets": [30e6 * (0.95 ** i) for i in range(n)],  # shrinking
        "current_liabilities": [40e6 * (1.05 ** i) for i in range(n)],  # growing
        "shares_outstanding_hist": [10e6 * (1 + i * 0.05) for i in range(n)],  # diluting
        "gross_profits": [20e6 * (0.90 ** i) for i in range(n)],  # shrinking
        "depreciation": [5e6] * n,
        "sga_expenses": [15e6 * (1.05 ** i) for i in range(n)],  # growing
        "receivables": [12e6 * (1.10 ** i) for i in range(n)],  # growing (bad)
        "ppe_net": [80e6 * (0.95 ** i) for i in range(n)],
        "cfo_list": [-2e6] * n,  # negative CFO
    }


def make_healthy_yf(overrides: dict | None = None) -> dict:
    """Baseline yfinance data for a healthy company."""
    data = {
        "ticker": "TEST",
        "price": 100.0,
        "market_cap": 1_000_000_000,
        "ebit": 120_000_000,
        "ebitda": 150_000_000,
        "total_revenue": 500_000_000,
        "total_assets": 800_000_000,
        "total_liabilities": 300_000_000,
        "current_assets": 250_000_000,
        "current_liabilities": 100_000_000,
        "working_capital": 150_000_000,
        "retained_earnings": 200_000_000,
        "shares_outstanding": 10_000_000,
        "total_debt": 200_000_000,
    }
    if overrides:
        data.update(overrides)
    return data


# ── Piotroski F-Score Tests ──────────────────────────────────────────────────

class TestPiotroskiFScore:
    def test_returns_dict_with_required_keys(self):
        result = calculate_piotroski_f_score(make_healthy_edgar(), make_healthy_yf())
        assert result is not None
        assert {"f_score", "components", "classification"} == set(result.keys())

    def test_f_score_is_integer_0_to_9(self):
        result = calculate_piotroski_f_score(make_healthy_edgar(), make_healthy_yf())
        assert isinstance(result["f_score"], int)
        assert 0 <= result["f_score"] <= 9

    def test_healthy_company_scores_high(self):
        result = calculate_piotroski_f_score(make_healthy_edgar(), make_healthy_yf())
        assert result["f_score"] >= 6  # healthy company should score well

    def test_healthy_company_classified_strong_or_neutral(self):
        result = calculate_piotroski_f_score(make_healthy_edgar(), make_healthy_yf())
        assert result["classification"] in ("Strong", "Neutral")

    def test_distressed_company_scores_low(self):
        result = calculate_piotroski_f_score(make_distressed_edgar(), make_healthy_yf())
        assert result["f_score"] <= 4

    def test_distressed_company_classified_weak_or_neutral(self):
        result = calculate_piotroski_f_score(make_distressed_edgar(), make_healthy_yf())
        assert result["classification"] in ("Weak", "Neutral")

    def test_components_are_booleans(self):
        result = calculate_piotroski_f_score(make_healthy_edgar(), make_healthy_yf())
        for key, val in result["components"].items():
            assert isinstance(val, bool), f"{key} is not bool: {type(val)}"

    def test_nine_components(self):
        result = calculate_piotroski_f_score(make_healthy_edgar(), make_healthy_yf())
        assert len(result["components"]) == 9

    def test_f_score_equals_sum_of_true_components(self):
        result = calculate_piotroski_f_score(make_healthy_edgar(), make_healthy_yf())
        assert result["f_score"] == sum(1 for v in result["components"].values() if v)

    def test_roa_positive_for_profitable_company(self):
        result = calculate_piotroski_f_score(make_healthy_edgar(), make_healthy_yf())
        assert result["components"]["roa_positive"] is True

    def test_roa_negative_for_unprofitable_company(self):
        result = calculate_piotroski_f_score(make_distressed_edgar(), make_healthy_yf())
        assert result["components"]["roa_positive"] is False

    def test_cfo_positive_for_healthy_company(self):
        result = calculate_piotroski_f_score(make_healthy_edgar(), make_healthy_yf())
        assert result["components"]["cfo_positive"] is True

    def test_no_dilution_when_shares_stable(self):
        result = calculate_piotroski_f_score(make_healthy_edgar(), make_healthy_yf())
        assert result["components"]["no_dilution"] is True

    def test_dilution_detected_when_shares_increase(self):
        result = calculate_piotroski_f_score(make_distressed_edgar(), make_healthy_yf())
        assert result["components"]["no_dilution"] is False

    def test_returns_none_with_insufficient_data(self):
        edgar = make_healthy_edgar(n=1)  # only 1 year
        assert calculate_piotroski_f_score(edgar, make_healthy_yf()) is None

    def test_returns_none_with_none_edgar(self):
        assert calculate_piotroski_f_score(None, make_healthy_yf()) is None

    def test_returns_none_when_total_assets_all_none(self):
        edgar = make_healthy_edgar()
        edgar["total_assets"] = [None] * 5
        assert calculate_piotroski_f_score(edgar, make_healthy_yf()) is None

    def test_classification_strong_for_score_7_plus(self):
        result = calculate_piotroski_f_score(make_healthy_edgar(), make_healthy_yf())
        if result["f_score"] >= 7:
            assert result["classification"] == "Strong"

    def test_classification_weak_for_score_3_or_less(self):
        result = calculate_piotroski_f_score(make_distressed_edgar(), make_healthy_yf())
        if result["f_score"] <= 3:
            assert result["classification"] == "Weak"


# ── Altman Z-Score Tests ─────────────────────────────────────────────────────

class TestAltmanZScore:
    def test_returns_dict_with_required_keys(self):
        result = calculate_altman_z_score(make_healthy_yf())
        assert result is not None
        assert {"z_score", "components", "zone"} == set(result.keys())

    def test_z_score_is_float(self):
        result = calculate_altman_z_score(make_healthy_yf())
        assert isinstance(result["z_score"], float)

    def test_components_has_five_ratios(self):
        result = calculate_altman_z_score(make_healthy_yf())
        expected = {"x1_working_capital_ta", "x2_retained_earnings_ta",
                    "x3_ebit_ta", "x4_market_cap_tl", "x5_revenue_ta"}
        assert expected == set(result["components"].keys())

    def test_healthy_company_in_safe_zone(self):
        result = calculate_altman_z_score(make_healthy_yf())
        assert result["zone"] == "Safe"
        assert result["z_score"] > 2.99

    def test_distressed_company_in_distress_zone(self):
        distressed = make_healthy_yf({
            "working_capital": -50_000_000,
            "retained_earnings": -100_000_000,
            "ebit": -20_000_000,
            "market_cap": 50_000_000,
            "total_revenue": 100_000_000,
            "total_assets": 200_000_000,
            "total_liabilities": 250_000_000,
        })
        result = calculate_altman_z_score(distressed)
        assert result["zone"] == "Distress"
        assert result["z_score"] < 1.81

    def test_grey_zone(self):
        # Construct data that gives Z in grey zone (1.81–2.99)
        grey = make_healthy_yf({
            "working_capital": 30_000_000,
            "retained_earnings": 50_000_000,
            "ebit": 40_000_000,
            "market_cap": 300_000_000,
            "total_revenue": 400_000_000,
            "total_assets": 500_000_000,
            "total_liabilities": 300_000_000,
        })
        result = calculate_altman_z_score(grey)
        assert result["zone"] == "Grey"
        assert 1.81 <= result["z_score"] <= 2.99

    def test_returns_none_when_total_assets_missing(self):
        assert calculate_altman_z_score(make_healthy_yf({"total_assets": None})) is None

    def test_returns_none_when_total_assets_zero(self):
        assert calculate_altman_z_score(make_healthy_yf({"total_assets": 0})) is None

    def test_returns_none_when_total_liabilities_missing(self):
        assert calculate_altman_z_score(make_healthy_yf({"total_liabilities": None})) is None

    def test_handles_zero_total_liabilities(self):
        # Zero liabilities shouldn't crash (X4 = 0)
        data = make_healthy_yf({"total_liabilities": 0})
        result = calculate_altman_z_score(data)
        assert result is not None
        assert result["components"]["x4_market_cap_tl"] == 0

    def test_higher_ebit_improves_z_score(self):
        low = calculate_altman_z_score(make_healthy_yf({"ebit": 10_000_000}))
        high = calculate_altman_z_score(make_healthy_yf({"ebit": 200_000_000}))
        assert high["z_score"] > low["z_score"]


# ── Beneish M-Score Tests ────────────────────────────────────────────────────

class TestBeneishMScore:
    def test_returns_dict_with_required_keys(self):
        result = calculate_beneish_m_score(make_healthy_edgar())
        assert result is not None
        assert {"m_score", "components", "likely_manipulator"} == set(result.keys())

    def test_m_score_is_float(self):
        result = calculate_beneish_m_score(make_healthy_edgar())
        assert isinstance(result["m_score"], float)

    def test_components_has_eight_variables(self):
        result = calculate_beneish_m_score(make_healthy_edgar())
        expected = {"dsri", "gmi", "aqi", "sgi", "depi", "sgai", "tata", "lvgi"}
        assert expected == set(result["components"].keys())

    def test_clean_company_not_manipulator(self):
        result = calculate_beneish_m_score(make_healthy_edgar())
        assert result["likely_manipulator"] is False
        assert result["m_score"] < -1.78

    def test_likely_manipulator_flag(self):
        # Construct data that looks manipulated:
        # rapid revenue growth, growing receivables, accruals > cash
        edgar = make_healthy_edgar()
        edgar["revenues"] = [50e6, 100e6, 200e6, 400e6, 800e6]  # extreme growth
        edgar["receivables"] = [5e6, 15e6, 45e6, 135e6, 405e6]  # receivables grow faster
        edgar["net_incomes"] = [5e6, 20e6, 60e6, 160e6, 300e6]  # NI >> CFO
        edgar["cfo_list"] = [3e6, 5e6, 8e6, 10e6, 12e6]  # CFO barely grows
        result = calculate_beneish_m_score(edgar)
        # TATA will be very high (NI >> CFO), DSRI will spike
        assert result["likely_manipulator"] is True

    def test_returns_none_with_insufficient_data(self):
        edgar = make_healthy_edgar(n=1)
        assert calculate_beneish_m_score(edgar) is None

    def test_returns_none_with_none_edgar(self):
        assert calculate_beneish_m_score(None) is None

    def test_returns_none_when_revenues_have_zero(self):
        edgar = make_healthy_edgar()
        edgar["revenues"][-1] = 0
        assert calculate_beneish_m_score(edgar) is None

    def test_sgi_reflects_revenue_growth(self):
        result = calculate_beneish_m_score(make_healthy_edgar())
        # Healthy company has 5% growth, so SGI should be ~1.05
        assert result["components"]["sgi"] == pytest.approx(1.05, rel=0.01)

    def test_tata_near_zero_for_cash_backed_earnings(self):
        edgar = make_healthy_edgar()
        # Make CFO = NI (zero accruals)
        edgar["cfo_list"] = edgar["net_incomes"][:]
        result = calculate_beneish_m_score(edgar)
        assert abs(result["components"]["tata"]) < 0.05


# ── Composite Tests ──────────────────────────────────────────────────────────

class TestCalculateQualityScores:
    def test_returns_dict_with_three_keys(self):
        result = calculate_quality_scores(make_healthy_yf(), make_healthy_edgar())
        assert {"piotroski", "altman", "beneish"} == set(result.keys())

    def test_all_present_for_valid_data(self):
        result = calculate_quality_scores(make_healthy_yf(), make_healthy_edgar())
        assert result["piotroski"] is not None
        assert result["altman"] is not None
        assert result["beneish"] is not None

    def test_piotroski_none_when_no_edgar(self):
        result = calculate_quality_scores(make_healthy_yf(), None)
        assert result["piotroski"] is None
        assert result["altman"] is not None  # Altman uses yfinance only
        assert result["beneish"] is None

    def test_altman_none_when_missing_assets(self):
        result = calculate_quality_scores(
            make_healthy_yf({"total_assets": None}),
            make_healthy_edgar(),
        )
        assert result["altman"] is None
        assert result["piotroski"] is not None
