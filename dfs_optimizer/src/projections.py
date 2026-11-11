"""Platform-agnostic player-point projection helpers."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerRates:
    minutes: float
    goals_per90: float = 0.0
    assists_per90: float = 0.0
    shots_per90: float = 0.0
    key_passes_per90: float = 0.0
    tackles_interceptions_per90: float = 0.0
    clean_sheet_probability: float = 0.0


@dataclass(frozen=True)
class Scoring:
    goal: float = 0.0
    assist: float = 0.0
    shot: float = 0.0
    key_pass: float = 0.0
    tackle_interception: float = 0.0
    clean_sheet: float = 0.0


def expected_points(rates: PlayerRates, scoring: Scoring) -> float:
    scale = max(0.0, min(120.0, rates.minutes)) / 90.0
    clean_sheet_p = max(0.0, min(1.0, rates.clean_sheet_probability))
    return (
        scale * rates.goals_per90 * scoring.goal
        + scale * rates.assists_per90 * scoring.assist
        + scale * rates.shots_per90 * scoring.shot
        + scale * rates.key_passes_per90 * scoring.key_pass
        + scale * rates.tackles_interceptions_per90 * scoring.tackle_interception
        + clean_sheet_p * scoring.clean_sheet
    )


def approximate_variance(mean_points: float, variance_floor: float = 0.0) -> float:
    """Placeholder only; replace with joint event-level simulation."""
    if mean_points < 0 or variance_floor < 0:
        raise ValueError("inputs must be non-negative")
    return max(mean_points, variance_floor)
