"""
Catalyst Particle Filter

Tracks the evolving probability that each investment thesis catalyst will
materialise.  As milestone observations arrive (positive or negative signals),
the filter updates its belief via Sequential Importance Resampling (SIR) — the
standard bootstrap particle filter.

Usage pattern:
    catalyst = Catalyst(
        name="FDA approval",
        description="Phase 3 trial result expected Q2",
        target_date="2025-06-30",
        value_impact_if_hit=0.35,
        value_impact_if_miss=-0.20,
        prior_probability=0.55,
    )
    pf = CatalystParticleFilter(catalyst, n_particles=1000)

    # Each observation arrives as a (bool, strength) tuple
    new_prob = pf.update(observation=True, observation_strength=0.7)
    adjusted_iv = pf.get_updated_value_estimate(intrinsic_value_per_share)
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class Catalyst:
    """Describes a single binary investment catalyst."""
    name: str
    description: str
    target_date: Optional[str]
    value_impact_if_hit: float    # Fractional IV change if catalyst hits (e.g. +0.35)
    value_impact_if_miss: float   # Fractional IV change if catalyst misses (e.g. -0.20)
    prior_probability: float      # Initial belief it will hit (0–1)


class CatalystParticleFilter:
    """
    Sequential Importance Resampling (bootstrap) particle filter for one catalyst.

    Each particle represents a hypothetical "true probability" that the catalyst
    will materialise.  Particles are initialised from a Beta distribution centred
    on the prior, and weights are updated via Bayes' rule each time an
    observation arrives.

    When the Effective Sample Size (ESS) drops below n_particles / 2, the
    degenerate weight distribution is corrected by systematic resampling.
    """

    def __init__(self, catalyst: Catalyst, n_particles: int = 1_000):
        if not 0.0 < catalyst.prior_probability < 1.0:
            raise ValueError("prior_probability must be strictly between 0 and 1")
        if n_particles < 10:
            raise ValueError("n_particles must be at least 10")

        self.catalyst = catalyst
        self.n_particles = n_particles

        # Beta distribution centred on prior with concentration ~10
        # (higher concentration → tighter prior)
        concentration = 10.0
        alpha = catalyst.prior_probability * concentration
        beta = (1.0 - catalyst.prior_probability) * concentration
        self.particles = np.random.beta(alpha, beta, n_particles)

        # Uniform weights to start
        self.weights = np.ones(n_particles) / n_particles

        # History of (observation, strength, resulting_probability) tuples
        self.history: list[dict] = []

    # ── Core particle filter step ──────────────────────────────────────────────

    def update(self, observation: bool, observation_strength: float = 1.0) -> float:
        """
        Incorporate one new observation and return the updated probability estimate.

        Parameters
        ----------
        observation : bool
            True  → positive signal (catalyst more likely to hit)
            False → negative signal (catalyst less likely to hit)
        observation_strength : float in (0, 1]
            How definitive the signal is.  1.0 = fully conclusive;
            0.1 = very weak signal.

        Returns
        -------
        float — current probability estimate that the catalyst will hit.
        """
        observation_strength = float(np.clip(observation_strength, 1e-6, 1.0))

        # Likelihood of observing this signal given each particle's true probability
        if observation:
            likelihoods = self.particles ** observation_strength
        else:
            likelihoods = (1.0 - self.particles) ** observation_strength

        # Weight update (unnormalised)
        self.weights *= likelihoods

        # Guard against all-zero weights (numerical underflow)
        weight_sum = self.weights.sum()
        if weight_sum == 0.0 or not np.isfinite(weight_sum):
            self.weights = np.ones(self.n_particles) / self.n_particles
        else:
            self.weights /= weight_sum

        # ── Systematic resampling when ESS degrades ───────────────────────────
        ess = 1.0 / float(np.sum(self.weights ** 2))
        if ess < self.n_particles / 2:
            self._systematic_resample()

        prob = self.get_probability_estimate()
        self.history.append({
            "observation": observation,
            "observation_strength": observation_strength,
            "probability_after": round(prob, 6),
        })
        return prob

    def _systematic_resample(self) -> None:
        """
        Systematic resampling: draws N evenly-spaced points on the CDF,
        replacing degenerate particles with high-weight ones.
        """
        cumsum = np.cumsum(self.weights)
        u0 = np.random.uniform(0, 1.0 / self.n_particles)
        positions = u0 + np.arange(self.n_particles) / self.n_particles
        indices = np.searchsorted(cumsum, positions)
        indices = np.clip(indices, 0, self.n_particles - 1)
        self.particles = self.particles[indices]
        self.weights = np.ones(self.n_particles) / self.n_particles

    # ── Queries ────────────────────────────────────────────────────────────────

    def get_probability_estimate(self) -> float:
        """Weighted mean of particles — current best estimate of hit probability."""
        return float(np.average(self.particles, weights=self.weights))

    def get_probability_distribution(self) -> dict:
        """
        Returns summary statistics of the current particle distribution.
        Useful for rendering a probability density on the frontend.
        """
        weighted_mean = self.get_probability_estimate()
        # Weighted standard deviation
        variance = float(
            np.average((self.particles - weighted_mean) ** 2, weights=self.weights)
        )
        std = float(np.sqrt(variance))

        # Weighted percentiles via sorted particles
        sort_idx = np.argsort(self.particles)
        sorted_p = self.particles[sort_idx]
        sorted_w = self.weights[sort_idx]
        cumsum_w = np.cumsum(sorted_w)

        def weighted_pct(q: float) -> float:
            idx = np.searchsorted(cumsum_w, q)
            idx = min(idx, len(sorted_p) - 1)
            return float(sorted_p[idx])

        return {
            "mean": round(weighted_mean, 6),
            "std": round(std, 6),
            "p10": round(weighted_pct(0.10), 6),
            "p25": round(weighted_pct(0.25), 6),
            "p50": round(weighted_pct(0.50), 6),
            "p75": round(weighted_pct(0.75), 6),
            "p90": round(weighted_pct(0.90), 6),
            "n_observations": len(self.history),
        }

    def get_updated_value_estimate(self, current_intrinsic_value: float) -> float:
        """
        Adjust intrinsic value based on the current catalyst probability.

        Expected impact = p(hit) × impact_if_hit + p(miss) × impact_if_miss
        Returns the adjusted intrinsic value per share.
        """
        p = self.get_probability_estimate()
        expected_impact = (
            p * self.catalyst.value_impact_if_hit
            + (1.0 - p) * self.catalyst.value_impact_if_miss
        )
        return current_intrinsic_value * (1.0 + expected_impact)

    def reset(self) -> None:
        """Reset particles to the original prior distribution."""
        concentration = 10.0
        alpha = self.catalyst.prior_probability * concentration
        beta = (1.0 - self.catalyst.prior_probability) * concentration
        self.particles = np.random.beta(alpha, beta, self.n_particles)
        self.weights = np.ones(self.n_particles) / self.n_particles
        self.history.clear()


# ── Multi-catalyst portfolio tracker ──────────────────────────────────────────

class PositionCatalystTracker:
    """
    Manages multiple CatalystParticleFilters for a single position.
    Aggregates their expected value impact to produce a composite
    value adjustment.
    """

    def __init__(self, catalysts: list[Catalyst], n_particles: int = 1_000):
        self.filters: dict[str, CatalystParticleFilter] = {
            c.name: CatalystParticleFilter(c, n_particles)
            for c in catalysts
        }

    def update_catalyst(
        self,
        catalyst_name: str,
        observation: bool,
        observation_strength: float = 1.0,
    ) -> float:
        """Update a specific catalyst and return its new probability."""
        if catalyst_name not in self.filters:
            raise KeyError(f"Unknown catalyst: {catalyst_name!r}")
        return self.filters[catalyst_name].update(observation, observation_strength)

    def get_composite_value_estimate(self, base_intrinsic_value: float) -> float:
        """
        Apply all catalyst adjustments sequentially to the base intrinsic value.
        Each catalyst's expected impact is applied multiplicatively.
        """
        value = base_intrinsic_value
        for pf in self.filters.values():
            value = pf.get_updated_value_estimate(value)
        return value

    def get_summary(self) -> list[dict]:
        """Return current state of all catalysts."""
        summary = []
        for name, pf in self.filters.items():
            dist = pf.get_probability_distribution()
            summary.append({
                "catalyst_name": name,
                "description": pf.catalyst.description,
                "target_date": pf.catalyst.target_date,
                "probability": dist["mean"],
                "probability_std": dist["std"],
                "value_impact_if_hit": pf.catalyst.value_impact_if_hit,
                "value_impact_if_miss": pf.catalyst.value_impact_if_miss,
                "n_observations": dist["n_observations"],
                "distribution": dist,
            })
        return summary
