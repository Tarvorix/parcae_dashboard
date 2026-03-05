"""Unit tests for backend/engine/margin_of_safety.py"""

import numpy as np
import pytest

from backend.engine.margin_of_safety import calculate_margin_of_safety, _bin_histogram
from backend.config import KlarmanThresholds

config = KlarmanThresholds()


def make_intrinsic_values(median: float = 100.0, std: float = 20.0, n: int = 100_000) -> np.ndarray:
    np.random.seed(0)
    return np.random.normal(median, std, n)


class TestCalculateMarginOfSafety:
    def test_required_keys_present(self):
        iv = make_intrinsic_values()
        result = calculate_margin_of_safety(iv, current_price=70.0)
        required = {
            "current_price", "p10", "p25", "p50", "p75", "p90",
            "mos_median", "mos_downside", "prob_undervalued",
            "klarman_score", "passes_mos_threshold", "histogram_data",
        }
        assert required.issubset(result.keys())

    def test_percentiles_in_order(self):
        iv = make_intrinsic_values()
        r = calculate_margin_of_safety(iv, current_price=70.0)
        assert r["p10"] <= r["p25"] <= r["p50"] <= r["p75"] <= r["p90"]

    def test_mos_positive_when_price_below_median(self):
        iv = make_intrinsic_values(median=100.0)
        r = calculate_margin_of_safety(iv, current_price=70.0)
        assert r["mos_median"] > 0

    def test_mos_negative_when_price_above_median(self):
        iv = make_intrinsic_values(median=100.0)
        r = calculate_margin_of_safety(iv, current_price=130.0)
        assert r["mos_median"] < 0

    def test_prob_undervalued_high_when_price_very_low(self):
        iv = make_intrinsic_values(median=100.0, std=5.0)
        r = calculate_margin_of_safety(iv, current_price=50.0)
        assert r["prob_undervalued"] > 0.99

    def test_prob_undervalued_low_when_price_very_high(self):
        iv = make_intrinsic_values(median=100.0, std=5.0)
        r = calculate_margin_of_safety(iv, current_price=150.0)
        assert r["prob_undervalued"] < 0.01

    def test_prob_undervalued_bounded(self):
        iv = make_intrinsic_values()
        r = calculate_margin_of_safety(iv, current_price=70.0)
        assert 0.0 <= r["prob_undervalued"] <= 1.0

    def test_klarman_score_bounded(self):
        iv = make_intrinsic_values()
        r = calculate_margin_of_safety(iv, current_price=70.0)
        assert 0.0 <= r["klarman_score"] <= 100.0

    def test_passes_mos_threshold_when_large_discount(self):
        iv = make_intrinsic_values(median=100.0, std=5.0)
        r = calculate_margin_of_safety(iv, current_price=50.0)
        assert r["passes_mos_threshold"] is True

    def test_fails_mos_threshold_when_small_discount(self):
        iv = make_intrinsic_values(median=100.0, std=5.0)
        r = calculate_margin_of_safety(iv, current_price=98.0)
        assert r["passes_mos_threshold"] is False

    def test_histogram_data_is_list(self):
        iv = make_intrinsic_values()
        r = calculate_margin_of_safety(iv, current_price=70.0)
        assert isinstance(r["histogram_data"], list)

    def test_histogram_has_correct_bin_count(self):
        iv = make_intrinsic_values()
        r = calculate_margin_of_safety(iv, current_price=70.0)
        assert len(r["histogram_data"]) == config.histogram_bins

    def test_histogram_bins_have_required_fields(self):
        iv = make_intrinsic_values()
        r = calculate_margin_of_safety(iv, current_price=70.0)
        for bin_entry in r["histogram_data"]:
            assert {"bin_start", "bin_end", "count", "frequency"}.issubset(bin_entry.keys())

    def test_histogram_frequencies_sum_to_one(self):
        iv = make_intrinsic_values()
        r = calculate_margin_of_safety(iv, current_price=70.0)
        total_freq = sum(b["frequency"] for b in r["histogram_data"])
        assert abs(total_freq - 1.0) < 0.001

    def test_current_price_in_output(self):
        iv = make_intrinsic_values()
        r = calculate_margin_of_safety(iv, current_price=77.5)
        assert r["current_price"] == 77.5


class TestBinHistogram:
    def test_bin_count(self):
        values = np.linspace(0, 100, 10_000)
        bins = _bin_histogram(values, 50)
        assert len(bins) == 50

    def test_frequencies_sum_to_one(self):
        values = np.random.normal(50, 10, 100_000)
        bins = _bin_histogram(values, 200)
        total = sum(b["frequency"] for b in bins)
        assert abs(total - 1.0) < 0.001

    def test_bin_edges_cover_full_range(self):
        values = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        bins = _bin_histogram(values, 5)
        assert bins[0]["bin_start"] <= 10.0
        assert bins[-1]["bin_end"] >= 50.0
