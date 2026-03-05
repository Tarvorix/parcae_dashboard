"""
Unit tests for backend/catalyst/particle_filter.py

Covers:
  - CatalystParticleFilter: init, update, resampling, value estimate
  - PositionCatalystTracker: multi-catalyst composite value
  - 3-catalyst scenario with 5 observations each (per implementation spec)
"""

import numpy as np
import pytest

from backend.catalyst.particle_filter import (
    Catalyst,
    CatalystParticleFilter,
    PositionCatalystTracker,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_catalyst(
    name: str = "Test Catalyst",
    prior: float = 0.6,
    impact_hit: float = 0.25,
    impact_miss: float = -0.15,
) -> Catalyst:
    return Catalyst(
        name=name,
        description="Test catalyst description",
        target_date="2025-12-31",
        value_impact_if_hit=impact_hit,
        value_impact_if_miss=impact_miss,
        prior_probability=prior,
    )


def make_filter(prior: float = 0.6, n: int = 1_000) -> CatalystParticleFilter:
    np.random.seed(42)
    return CatalystParticleFilter(make_catalyst(prior=prior), n_particles=n)


# ── Catalyst dataclass ────────────────────────────────────────────────────────

class TestCatalyst:
    def test_fields_accessible(self):
        c = make_catalyst()
        assert c.name == "Test Catalyst"
        assert c.prior_probability == 0.6
        assert c.value_impact_if_hit == 0.25
        assert c.value_impact_if_miss == -0.15

    def test_optional_target_date(self):
        c = Catalyst(
            name="No date",
            description="",
            target_date=None,
            value_impact_if_hit=0.1,
            value_impact_if_miss=-0.1,
            prior_probability=0.5,
        )
        assert c.target_date is None


# ── CatalystParticleFilter: initialisation ────────────────────────────────────

class TestCatalystParticleFilterInit:
    def test_particles_shape(self):
        pf = make_filter(n=500)
        assert pf.particles.shape == (500,)

    def test_weights_shape(self):
        pf = make_filter(n=500)
        assert pf.weights.shape == (500,)

    def test_weights_sum_to_one(self):
        pf = make_filter()
        assert abs(pf.weights.sum() - 1.0) < 1e-9

    def test_particles_within_zero_one(self):
        pf = make_filter()
        assert pf.particles.min() >= 0.0
        assert pf.particles.max() <= 1.0

    def test_initial_estimate_near_prior(self):
        """Particle mean should be close to the prior (±0.1 is generous)."""
        pf = make_filter(prior=0.70)
        assert abs(pf.get_probability_estimate() - 0.70) < 0.10

    def test_invalid_prior_zero_raises(self):
        with pytest.raises(ValueError):
            CatalystParticleFilter(make_catalyst(prior=0.0))

    def test_invalid_prior_one_raises(self):
        with pytest.raises(ValueError):
            CatalystParticleFilter(make_catalyst(prior=1.0))

    def test_invalid_n_particles_raises(self):
        with pytest.raises(ValueError):
            CatalystParticleFilter(make_catalyst(), n_particles=5)

    def test_history_empty_at_init(self):
        pf = make_filter()
        assert pf.history == []


# ── CatalystParticleFilter: update ────────────────────────────────────────────

class TestCatalystParticleFilterUpdate:
    def test_returns_float(self):
        pf = make_filter()
        result = pf.update(True)
        assert isinstance(result, float)

    def test_probability_in_zero_one(self):
        pf = make_filter()
        for _ in range(10):
            p = pf.update(True)
            assert 0.0 <= p <= 1.0

    def test_positive_observations_increase_probability(self):
        pf = make_filter(prior=0.5)
        initial = pf.get_probability_estimate()
        for _ in range(5):
            pf.update(True, observation_strength=1.0)
        assert pf.get_probability_estimate() > initial

    def test_negative_observations_decrease_probability(self):
        pf = make_filter(prior=0.5)
        initial = pf.get_probability_estimate()
        for _ in range(5):
            pf.update(False, observation_strength=1.0)
        assert pf.get_probability_estimate() < initial

    def test_strong_signal_moves_more_than_weak_signal(self):
        np.random.seed(0)
        pf_strong = make_filter(prior=0.5, n=2000)
        pf_weak = make_filter(prior=0.5, n=2000)
        np.random.seed(0)
        pf_strong.update(True, observation_strength=1.0)
        np.random.seed(0)
        pf_weak.update(True, observation_strength=0.1)
        assert pf_strong.get_probability_estimate() > pf_weak.get_probability_estimate()

    def test_history_grows_with_updates(self):
        pf = make_filter()
        for i in range(5):
            pf.update(i % 2 == 0)
        assert len(pf.history) == 5

    def test_history_entry_has_required_keys(self):
        pf = make_filter()
        pf.update(True, 0.8)
        entry = pf.history[0]
        assert {"observation", "observation_strength", "probability_after"}.issubset(entry.keys())

    def test_weights_sum_to_one_after_update(self):
        pf = make_filter()
        pf.update(True)
        assert abs(pf.weights.sum() - 1.0) < 1e-9

    def test_probability_converges_to_high_after_many_positive_obs(self):
        """10 strong positive observations should push probability well above the prior."""
        np.random.seed(1)
        pf = CatalystParticleFilter(make_catalyst(prior=0.5), n_particles=5_000)
        for _ in range(10):
            pf.update(True, observation_strength=1.0)
        assert pf.get_probability_estimate() > 0.70

    def test_probability_converges_to_low_after_many_negative_obs(self):
        """10 strong negative observations should push probability well below the prior."""
        np.random.seed(2)
        pf = CatalystParticleFilter(make_catalyst(prior=0.5), n_particles=5_000)
        for _ in range(10):
            pf.update(False, observation_strength=1.0)
        assert pf.get_probability_estimate() < 0.30


# ── CatalystParticleFilter: probability distribution ─────────────────────────

class TestGetProbabilityDistribution:
    def test_required_keys(self):
        pf = make_filter()
        dist = pf.get_probability_distribution()
        assert {"mean", "std", "p10", "p25", "p50", "p75", "p90", "n_observations"}.issubset(dist.keys())

    def test_percentiles_in_order(self):
        pf = make_filter()
        dist = pf.get_probability_distribution()
        assert dist["p10"] <= dist["p25"] <= dist["p50"] <= dist["p75"] <= dist["p90"]

    def test_mean_in_zero_one(self):
        pf = make_filter()
        assert 0.0 <= pf.get_probability_distribution()["mean"] <= 1.0

    def test_n_observations_matches_history(self):
        pf = make_filter()
        pf.update(True)
        pf.update(False)
        assert pf.get_probability_distribution()["n_observations"] == 2


# ── CatalystParticleFilter: value estimate ────────────────────────────────────

class TestGetUpdatedValueEstimate:
    def test_returns_positive_for_positive_expected_impact(self):
        """With high probability of hitting a positive catalyst, IV should increase."""
        np.random.seed(0)
        pf = CatalystParticleFilter(make_catalyst(prior=0.9, impact_hit=0.30, impact_miss=-0.05))
        adjusted = pf.get_updated_value_estimate(100.0)
        assert adjusted > 100.0

    def test_returns_less_than_base_for_mostly_negative_catalyst(self):
        """With high probability of missing a destructive catalyst, IV should fall."""
        np.random.seed(0)
        pf = CatalystParticleFilter(make_catalyst(prior=0.05, impact_hit=0.10, impact_miss=-0.40))
        adjusted = pf.get_updated_value_estimate(100.0)
        assert adjusted < 100.0

    def test_proportional_to_base_value(self):
        pf = make_filter()
        v1 = pf.get_updated_value_estimate(100.0)
        v2 = pf.get_updated_value_estimate(200.0)
        assert v2 == pytest.approx(v1 * 2.0, rel=1e-9)


# ── CatalystParticleFilter: reset ─────────────────────────────────────────────

class TestReset:
    def test_history_cleared_after_reset(self):
        pf = make_filter()
        pf.update(True)
        pf.update(False)
        pf.reset()
        assert pf.history == []

    def test_weights_uniform_after_reset(self):
        pf = make_filter()
        for _ in range(5):
            pf.update(True)
        pf.reset()
        assert np.allclose(pf.weights, 1.0 / pf.n_particles)


# ── PositionCatalystTracker ───────────────────────────────────────────────────

class TestPositionCatalystTracker:
    def make_tracker(self) -> PositionCatalystTracker:
        np.random.seed(0)
        catalysts = [
            make_catalyst("FDA Approval", prior=0.55, impact_hit=0.35, impact_miss=-0.20),
            make_catalyst("Earnings Beat", prior=0.65, impact_hit=0.12, impact_miss=-0.08),
            make_catalyst("Buyback Announcement", prior=0.45, impact_hit=0.08, impact_miss=-0.03),
        ]
        return PositionCatalystTracker(catalysts, n_particles=500)

    def test_all_catalysts_registered(self):
        tracker = self.make_tracker()
        assert set(tracker.filters.keys()) == {"FDA Approval", "Earnings Beat", "Buyback Announcement"}

    def test_update_unknown_catalyst_raises(self):
        tracker = self.make_tracker()
        with pytest.raises(KeyError):
            tracker.update_catalyst("Nonexistent", True)

    def test_update_returns_probability(self):
        tracker = self.make_tracker()
        p = tracker.update_catalyst("FDA Approval", True, 0.8)
        assert 0.0 <= p <= 1.0

    def test_composite_value_different_from_base(self):
        tracker = self.make_tracker()
        base = 50.0
        adjusted = tracker.get_composite_value_estimate(base)
        # With 3 non-neutral catalysts, the estimate should differ from base
        assert adjusted != base

    def test_summary_has_all_catalysts(self):
        tracker = self.make_tracker()
        summary = tracker.get_summary()
        assert len(summary) == 3

    def test_summary_entry_has_required_keys(self):
        tracker = self.make_tracker()
        for entry in tracker.get_summary():
            assert {"catalyst_name", "description", "target_date", "probability",
                    "value_impact_if_hit", "value_impact_if_miss",
                    "n_observations", "distribution"}.issubset(entry.keys())

    def test_n_observations_updates_correctly(self):
        tracker = self.make_tracker()
        for _ in range(5):
            tracker.update_catalyst("FDA Approval", True, 0.7)
        summary = {e["catalyst_name"]: e for e in tracker.get_summary()}
        assert summary["FDA Approval"]["n_observations"] == 5
        assert summary["Earnings Beat"]["n_observations"] == 0


# ── 3-Catalyst Scenario: 5 observations each (per implementation spec) ────────

class TestThreeCatalystScenario:
    """
    Simulate a realistic position with 3 catalysts and 5 observations per catalyst.
    Validates that the particle filter correctly tracks probability evolution.
    """

    def setup_method(self):
        np.random.seed(99)
        catalysts = [
            Catalyst("FDA Phase 3",       "FDA phase 3 approval",    "2025-06-01",  0.40, -0.25, 0.55),
            Catalyst("Patent Extension",  "Patent cliff extension",  "2025-09-15",  0.15, -0.08, 0.70),
            Catalyst("M&A Rumour",        "Acquisition by BigCo",    "2025-12-31",  0.50, -0.05, 0.30),
        ]
        self.tracker = PositionCatalystTracker(catalysts, n_particles=2_000)
        self.base_iv = 80.0

        # 5 observations per catalyst (mixed positive/negative signals)
        self.observation_sequences = {
            "FDA Phase 3":      [(True, 0.6), (True, 0.8), (False, 0.3), (True, 0.9), (True, 0.7)],
            "Patent Extension": [(True, 0.5), (True, 0.6), (True, 0.7), (False, 0.4), (True, 0.6)],
            "M&A Rumour":       [(False, 0.7), (False, 0.5), (True, 0.4), (False, 0.8), (False, 0.6)],
        }

    def _run_all_observations(self) -> dict[str, list[float]]:
        probability_traces: dict[str, list[float]] = {k: [] for k in self.observation_sequences}
        for catalyst_name, obs_seq in self.observation_sequences.items():
            for obs, strength in obs_seq:
                p = self.tracker.update_catalyst(catalyst_name, obs, strength)
                probability_traces[catalyst_name].append(p)
        return probability_traces

    def test_all_5_observations_recorded_per_catalyst(self):
        self._run_all_observations()
        summary = {e["catalyst_name"]: e for e in self.tracker.get_summary()}
        for name in self.observation_sequences:
            assert summary[name]["n_observations"] == 5

    def test_all_probabilities_in_valid_range(self):
        traces = self._run_all_observations()
        for name, probs in traces.items():
            for p in probs:
                assert 0.0 <= p <= 1.0, f"{name}: probability {p} out of range"

    def test_mostly_positive_catalyst_probability_above_prior(self):
        """FDA Phase 3 gets 4 positive, 1 negative → should end above prior (0.55)."""
        traces = self._run_all_observations()
        final_p = traces["FDA Phase 3"][-1]
        assert final_p > 0.55, f"Expected > 0.55 after positive signals, got {final_p:.3f}"

    def test_mostly_negative_catalyst_probability_below_prior(self):
        """M&A Rumour gets 4 negative, 1 positive → should end below prior (0.30)."""
        traces = self._run_all_observations()
        final_p = traces["M&A Rumour"][-1]
        assert final_p < 0.30, f"Expected < 0.30 after negative signals, got {final_p:.3f}"

    def test_composite_value_estimate_is_positive(self):
        self._run_all_observations()
        adjusted = self.tracker.get_composite_value_estimate(self.base_iv)
        assert adjusted > 0.0

    def test_probabilities_evolve_over_observations(self):
        """No catalyst should have identical probability for all 5 observations."""
        traces = self._run_all_observations()
        for name, probs in traces.items():
            unique = set(round(p, 4) for p in probs)
            assert len(unique) > 1, f"{name}: probability never changed across 5 observations"

    def test_summary_reflects_final_state(self):
        self._run_all_observations()
        summary = {e["catalyst_name"]: e for e in self.tracker.get_summary()}
        assert len(summary) == 3
        for name in self.observation_sequences:
            assert summary[name]["probability"] is not None
