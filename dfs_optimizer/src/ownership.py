"""Ownership estimation helpers with explicit separation of prior and learned data."""
from __future__ import annotations
import numpy as np


def dirichlet_ownership(pick_counts, prior=0.5):
    """Smoothed ownership shares from historical pick counts.

    This is a Dirichlet-multinomial baseline, not a feature-trained ML model.
    Counts should refer to comparable contests/platforms/roster slots.
    """
    counts = np.asarray(pick_counts, dtype=float)
    if counts.ndim != 1 or len(counts) == 0 or not np.all(np.isfinite(counts)):
        raise ValueError("pick_counts must be a finite non-empty vector")
    if np.any(counts < 0) or prior <= 0:
        raise ValueError("counts must be non-negative and prior must be positive")
    adjusted = counts + float(prior)
    return adjusted / adjusted.sum()


def leverage_index(event_probability, ownership, epsilon=1e-6):
    """Return event_probability / ownership, guarding against division by zero."""
    p = np.asarray(event_probability, dtype=float)
    own = np.asarray(ownership, dtype=float)
    p, own = np.broadcast_arrays(p, own)
    if np.any((p < 0) | (p > 1)) or np.any((own < 0) | (own > 1)):
        raise ValueError("probabilities and ownership must be in [0, 1]")
    if epsilon <= 0:
        raise ValueError("epsilon must be positive")
    return p / np.maximum(own, epsilon)


def ownership_adjusted_value(mean_points, ceiling_points, ownership, ceiling_weight=0.5):
    """Exploratory score for ranking; not an expected-payout estimate."""
    mean = np.asarray(mean_points, dtype=float)
    ceiling = np.asarray(ceiling_points, dtype=float)
    own = np.asarray(ownership, dtype=float)
    if np.any(own < 0) or np.any(own > 1):
        raise ValueError("ownership must be in [0, 1]")
    if not 0 <= ceiling_weight <= 1:
        raise ValueError("ceiling_weight must be in [0, 1]")
    raw = (1 - ceiling_weight) * mean + ceiling_weight * ceiling
    return raw * (1.0 - own)
