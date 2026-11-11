"""Poisson baseline and Dixon–Coles scoreline probability helpers."""
from __future__ import annotations
import math


def poisson_pmf(k: int, rate: float) -> float:
    if k < 0 or rate < 0:
        raise ValueError("k and rate must be non-negative")
    if rate == 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-rate + k * math.log(rate) - math.lgamma(k + 1))


def tau(home_goals: int, away_goals: int, home_rate: float,
        away_rate: float, rho: float) -> float:
    """Dixon–Coles low-score adjustment for 0-0, 0-1, 1-0, 1-1."""
    if home_goals == 0 and away_goals == 0:
        return 1.0 - home_rate * away_rate * rho
    if home_goals == 0 and away_goals == 1:
        return 1.0 + home_rate * rho
    if home_goals == 1 and away_goals == 0:
        return 1.0 + away_rate * rho
    if home_goals == 1 and away_goals == 1:
        return 1.0 - rho
    return 1.0


def score_grid(home_rate: float, away_rate: float, max_goals: int = 10,
               rho: float = 0.0) -> dict[tuple[int, int], float]:
    """Create a truncated score grid, normalized over included outcomes."""
    if home_rate < 0 or away_rate < 0:
        raise ValueError("goal rates must be non-negative")
    if max_goals < 1:
        raise ValueError("max_goals must be >= 1")
    grid = {}
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            p = poisson_pmf(h, home_rate) * poisson_pmf(a, away_rate)
            p *= tau(h, a, home_rate, away_rate, rho)
            if p < -1e-12:
                raise ValueError("rho/rates yielded negative probability")
            grid[(h, a)] = max(0.0, p)
    total = sum(grid.values())
    if total <= 0:
        raise ValueError("score grid has zero mass")
    return {score: p / total for score, p in grid.items()}


def outcome_probabilities(grid: dict[tuple[int, int], float]) -> dict[str, float]:
    return {
        "home_win": sum(p for (h, a), p in grid.items() if h > a),
        "draw": sum(p for (h, a), p in grid.items() if h == a),
        "away_win": sum(p for (h, a), p in grid.items() if h < a),
        "over_2_5": sum(p for (h, a), p in grid.items() if h + a >= 3),
        "btts_yes": sum(p for (h, a), p in grid.items() if h > 0 and a > 0),
    }
