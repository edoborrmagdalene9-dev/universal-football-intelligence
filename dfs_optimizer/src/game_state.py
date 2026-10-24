"""Simple score-state Markov and conditional minutes primitives.

This is a transparent baseline. Transition probabilities and manager tendencies
must be estimated from historical event/substitution data before production use.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ScoreState:
    home_goals: int = 0
    away_goals: int = 0

    @property
    def label(self):
        return f"{self.home_goals}-{self.away_goals}"

    @property
    def home_status(self):
        return "leading" if self.home_goals > self.away_goals else (
            "trailing" if self.home_goals < self.away_goals else "drawing"
        )


def propagate_score_states(initial, transition_by_minute, checkpoints=(30, 60, 75)):
    """Propagate a discrete score-state distribution across checkpoint transitions.

    transition_by_minute maps a checkpoint minute to {(old_label,new_label): p}.
    Each old state's outgoing probabilities must sum to 1. State labels use H-A
    score notation. Returns {minute: {state_label: probability}}.
    """
    distribution = dict(initial)
    _validate_distribution(distribution)
    result = {}
    for minute in checkpoints:
        transitions = transition_by_minute.get(minute)
        if transitions is None:
            raise ValueError(f"missing transition table for minute {minute}")
        next_dist = {}
        outgoing = {}
        for (old_state, new_state), probability in transitions.items():
            if probability < 0:
                raise ValueError("transition probabilities cannot be negative")
            outgoing[old_state] = outgoing.get(old_state, 0.0) + probability
            if old_state in distribution:
                next_dist[new_state] = next_dist.get(new_state, 0.0) + distribution[old_state] * probability
        for state, mass in distribution.items():
            if mass > 0 and abs(outgoing.get(state, 0.0) - 1.0) > 1e-6:
                raise ValueError(f"outgoing transition probabilities for {state} must sum to 1")
        _validate_distribution(next_dist)
        result[minute] = next_dist
        distribution = next_dist
    return result


def _validate_distribution(distribution: Mapping[str, float]):
    if not distribution or any(p < 0 for p in distribution.values()):
        raise ValueError("state distribution must be non-empty and non-negative")
    if abs(sum(distribution.values()) - 1.0) > 1e-6:
        raise ValueError("state probabilities must sum to 1")


def conditional_minutes(base_minutes, score_state, role="balanced", manager_profile=None):
    """Return a bounded expected-minute estimate adjusted for match state.

    manager_profile maps role/status pairs such as ('attacker','trailing') to a
    minute adjustment. This is an additive adjustment, not a learned distribution.
    """
    if not 0 <= base_minutes <= 120:
        raise ValueError("base_minutes must be between 0 and 120")
    if role not in {"attacker", "defender", "midfielder", "balanced"}:
        raise ValueError("unsupported role")
    profile = manager_profile or {}
    status = score_state.home_status
    adjustment = float(profile.get((role, status), 0.0))
    return max(0.0, min(120.0, float(base_minutes) + adjustment))


def sample_minutes(minute_distribution, n_samples=10_000, seed=None):
    """Sample minutes from explicit (minutes, probability) pairs."""
    import numpy as np
    values = np.asarray([x[0] for x in minute_distribution], dtype=float)
    probs = np.asarray([x[1] for x in minute_distribution], dtype=float)
    if values.ndim != 1 or len(values) == 0 or np.any(values < 0) or np.any(values > 120):
        raise ValueError("minutes must be a non-empty list within 0..120")
    if np.any(probs < 0) or abs(probs.sum() - 1.0) > 1e-6:
        raise ValueError("minute probabilities must be non-negative and sum to 1")
    return np.random.default_rng(seed).choice(values, size=int(n_samples), p=probs)
