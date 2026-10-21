"""FantasyFi scoring rules and expected-points helpers.

Rules are explicit configuration, not inferred from generic DFS conventions.
Actual completed-pass points use floor(passes / 5); projections can use a
fractional expectation or a supplied pass-count distribution.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import floor
from typing import Mapping, Optional

@dataclass(frozen=True)
class FantasyFiRules:
    starting_appearance: float = 4.0
    substitute_appearance: float = 2.0
    forward_goal: float = 40.0
    midfielder_goal: float = 50.0
    defender_goal: float = 60.0
    goalkeeper_goal: float = 60.0
    assist: float = 20.0
    shot_on_target: float = 6.0  # Includes goals: do not subtract goal shots.
    chance_created: float = 3.0
    passes_per_point: int = 5
    interception_won: float = 4.0
    tackle_won: float = 0.0
    goalkeeper_save: float = 6.0
    penalty_saved: float = 50.0
    clean_sheet: float = 20.0
    clean_sheet_min_minutes: int = 55
    goal_conceded: float = -2.0
    yellow_card: float = -4.0
    red_card: float = -10.0
    own_goal: float = -8.0
    penalty_missed: float = -20.0

RULES = FantasyFiRules()

def goal_points(position: str, rules: FantasyFiRules = RULES) -> float:
    p = position.strip().lower()
    if p in {"f", "fw", "fwd", "forward", "striker", "st"}:
        return rules.forward_goal
    if p in {"m", "mf", "midfielder", "mid"}:
        return rules.midfielder_goal
    if p in {"gk", "goalkeeper", "keeper"}:
        return rules.goalkeeper_goal
    if p in {"d", "df", "def", "defender", "cb", "fb", "wb"}:
        return rules.defender_goal
    raise ValueError(f"Unknown position: {position!r}")

def score_actual(stats: Mapping, position: str, rules: FantasyFiRules = RULES) -> float:
    """Score observed match stats; aliases are intentionally not guessed."""
    points = 0.0
    minutes = float(stats.get("minutes", 0) or 0)
    started = bool(stats.get("started", False))
    appeared = bool(stats.get("appeared", minutes > 0))
    if appeared:
        points += rules.starting_appearance if started else rules.substitute_appearance
    goals = int(stats.get("goals", 0) or 0)
    points += goals * goal_points(position, rules)
    points += float(stats.get("assists", 0) or 0) * rules.assist
    points += float(stats.get("shots_on_target", 0) or 0) * rules.shot_on_target
    points += float(stats.get("chances_created", 0) or 0) * rules.chance_created
    points += floor(max(0, float(stats.get("completed_passes", 0) or 0)) / rules.passes_per_point)
    points += float(stats.get("interceptions_won", 0) or 0) * rules.interception_won
    # Tackles are deliberately ignored: platform scoring assigns zero.
    if position.strip().lower() in {"gk", "goalkeeper", "keeper", "d", "df", "def", "defender", "cb", "fb", "wb"}:
        if minutes >= rules.clean_sheet_min_minutes and float(stats.get("goals_conceded", 0) or 0) == 0:
            points += rules.clean_sheet
        points += float(stats.get("goals_conceded", 0) or 0) * rules.goal_conceded
    if position.strip().lower() in {"gk", "goalkeeper", "keeper"}:
        points += float(stats.get("saves", 0) or 0) * rules.goalkeeper_save
        points += float(stats.get("penalties_saved", 0) or 0) * rules.penalty_saved
    points += float(stats.get("yellow_cards", 0) or 0) * rules.yellow_card
    points += float(stats.get("red_cards", 0) or 0) * rules.red_card
    points += float(stats.get("own_goals", 0) or 0) * rules.own_goal
    points += float(stats.get("penalties_missed", 0) or 0) * rules.penalty_missed
    return points

def expected_points(stats: Mapping, position: str, rules: FantasyFiRules = RULES,
                    pass_count_pmf: Optional[Mapping[int, float]] = None) -> float:
    """Expected points from expected stats.

    Expected stats keys: appearance_probability, start_probability, xg, xa,
    x_sot, x_chances_created, x_passes, x_interceptions, clean_sheet_probability,
    expected_goals_conceded, expected_yellow_cards, expected_red_cards,
    expected_own_goals, expected_penalties_missed, expected_saves,
    expected_penalties_saved. For non-integer expected passes, a supplied PMF
    is preferred; absent one, x_passes/5 is the documented linear approximation.
    """
    appearance = float(stats.get("appearance_probability", 1.0) or 0.0)
    start_probability = float(stats.get("start_probability", 1.0) or 0.0)
    p = appearance * (rules.substitute_appearance +
                      start_probability * (rules.starting_appearance - rules.substitute_appearance))
    p += float(stats.get("xg", 0) or 0) * goal_points(position, rules)
    p += float(stats.get("xa", 0) or 0) * rules.assist
    p += float(stats.get("x_sot", 0) or 0) * rules.shot_on_target
    p += float(stats.get("x_chances_created", 0) or 0) * rules.chance_created
    if pass_count_pmf:
        p += sum(max(0, int(n)) // rules.passes_per_point * float(prob)
                 for n, prob in pass_count_pmf.items())
    else:
        p += max(0.0, float(stats.get("x_passes", 0) or 0)) / rules.passes_per_point
    p += float(stats.get("x_interceptions", 0) or 0) * rules.interception_won
    defensive = position.strip().lower() in {"gk", "goalkeeper", "keeper", "d", "df", "defender", "cb", "fb", "wb"}
    if defensive:
        p += float(stats.get("clean_sheet_probability", 0) or 0) * rules.clean_sheet
        p -= float(stats.get("expected_goals_conceded", 0) or 0) * abs(rules.goal_conceded)
    if position.strip().lower() in {"gk", "goalkeeper", "keeper"}:
        p += float(stats.get("expected_saves", 0) or 0) * rules.goalkeeper_save
        p += float(stats.get("probability_penalty_saved", 0) or 0) * rules.penalty_saved
    p -= float(stats.get("expected_yellow_cards", 0) or 0) * abs(rules.yellow_card)
    p -= float(stats.get("expected_red_cards", 0) or 0) * abs(rules.red_card)
    p -= float(stats.get("expected_own_goals", 0) or 0) * abs(rules.own_goal)
    p -= float(stats.get("expected_penalties_missed", 0) or 0) * abs(rules.penalty_missed)
    return p

def penalty_event_ev(conversion_probability: float, position: str,
                     opponent_penalty_save_probability: float = 0.0,
                     rules: FantasyFiRules = RULES) -> float:
    """Expected fantasy points for a penalty attempt, including shot-on-target on goals.

    Goal outcome scores goal points + 6 SoT; a miss costs 20. Keeper penalty-save
    bonus is a separate opposing-player outcome and is not deducted from taker's EV.
    """
    if not 0 <= conversion_probability <= 1:
        raise ValueError("conversion_probability must be between 0 and 1")
    if not 0 <= opponent_penalty_save_probability <= 1:
        raise ValueError("opponent_penalty_save_probability must be between 0 and 1")
    # Treat conversion_probability as a baseline against an average keeper; the\n    # opponent save rate is a matchup adjustment, not a separate subtraction.\n    effective_conversion = conversion_probability * (1 - opponent_penalty_save_probability)\n    scored = goal_points(position, rules) + rules.shot_on_target\n    return effective_conversion * scored + (1 - effective_conversion) * rules.penalty_missed\n\ndef penalty_matchup_ev(conversion_probability: float, opponent_penalty_save_probability: float,\n                       position: str = "forward", rules: FantasyFiRules = RULES) -> dict:\n    """Expected taker and goalkeeper points for one penalty attempt.\n\n    The keeper save rate is treated as an incremental matchup adjustment to a\n    baseline taker conversion rate; use carefully if taker rates already account\n    for this keeper, to avoid double-counting.\n    """\n    if not 0 <= conversion_probability <= 1 or not 0 <= opponent_penalty_save_probability <= 1:\n        raise ValueError("Probabilities must be between 0 and 1")\n    effective = conversion_probability * (1 - opponent_penalty_save_probability)\n    taker_ev = effective * (goal_points(position, rules) + rules.shot_on_target) + (1-effective) * rules.penalty_missed\n    return {"effective_conversion_probability": effective,\n            "taker_expected_points": taker_ev,\n            "goalkeeper_expected_penalty_save_points": opponent_penalty_save_probability * rules.penalty_saved}\n