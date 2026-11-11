"""Platform-specific fantasy scoring from low-level event expectations."""
from __future__ import annotations
from typing import Mapping


def expected_points(event_rates: Mapping[str, float], scoring_rules: Mapping[str, float],
                    minutes=90.0, minute_basis=90.0):
    """Map event rates into expected points using explicit platform scoring rules.

    event_rates are expected event counts per minute_basis minutes (not raw
    probabilities unless they are probabilities of at most one event). Events
    missing from scoring_rules contribute zero; unknown event rates are ignored.
    """
    if minutes < 0 or minute_basis <= 0:
        raise ValueError("minutes must be non-negative and minute_basis positive")
    total = 0.0
    scale = min(float(minutes), 120.0) / float(minute_basis)
    for event, rate in event_rates.items():
        if rate < 0:
            raise ValueError(f"event rate for {event} cannot be negative")
        total += float(rate) * float(scoring_rules.get(event, 0.0)) * scale
    return total


def score_realized_events(event_counts: Mapping[str, float], scoring_rules: Mapping[str, float]):
    """Score observed event counts under a platform's declared scoring matrix."""
    total = 0.0
    for event, count in event_counts.items():
        if count < 0:
            raise ValueError(f"event count for {event} cannot be negative")
        total += float(count) * float(scoring_rules.get(event, 0.0))
    return total
