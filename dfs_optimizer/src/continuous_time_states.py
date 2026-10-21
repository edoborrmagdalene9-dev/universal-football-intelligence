"""Event-driven score-state simulator using a continuous-time Markov process.

States are score difference from the perspective of the selected team. Goal
hazards can vary by state. This is a continuous-time baseline; fit rates from
time-stamped match data before production use.
"""
import random


def simulate_score_path(home_goal_rate, away_goal_rate, minutes=90,
                        home_state_multipliers=None, away_state_multipliers=None,
                        seed=None):
    """Return event timeline and final score. Multipliers map 'lead','draw','trail'."""
    rng = random.Random(seed)
    hm = {"lead": 1.0, "draw": 1.0, "trail": 1.0}
    am = {"lead": 1.0, "draw": 1.0, "trail": 1.0}
    hm.update(home_state_multipliers or {})
    am.update(away_state_multipliers or {})
    t, h, a, timeline = 0.0, 0, 0, []
    while t < minutes:
        state_h = "lead" if h > a else "trail" if h < a else "draw"
        state_a = "lead" if a > h else "trail" if a < h else "draw"
        rh = max(0.0, float(home_goal_rate)) * max(0.0, float(hm[state_h]))
        ra = max(0.0, float(away_goal_rate)) * max(0.0, float(am[state_a]))
        total = rh + ra
        if total <= 0:
            break
        dt = rng.expovariate(total / minutes)
        t += dt
        if t > minutes:
            break
        if rng.random() < rh / total:
            h += 1
            timeline.append({"minute": round(t, 3), "team": "home", "score": [h, a]})
        else:
            a += 1
            timeline.append({"minute": round(t, 3), "team": "away", "score": [h, a]})
    return {"home_goals": h, "away_goals": a, "timeline": timeline,
            "metadata": {"engine": "continuous-time competing-hazards",
                         "rates_are_per_match": True, "fitted": False}}


def estimate_goal_rates(matches, smoothing=0.5):
    """Estimate per-match goal rates from rows with home_goals and away_goals."""
    rows = [m for m in matches if m.get("home_goals") is not None and m.get("away_goals") is not None]
    if not rows:
        raise ValueError("At least one historical match with final scores is required")
    n = len(rows)
    return {"home": (sum(float(m["home_goals"]) for m in rows) + smoothing) / (n + 2 * smoothing),
            "away": (sum(float(m["away_goals"]) for m in rows) + smoothing) / (n + 2 * smoothing),
            "matches": n, "warning": "Use league/team/time-conditioned estimates for serious forecasts."}
