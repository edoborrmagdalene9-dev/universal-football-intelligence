"""Lightweight event-level DFS simulation; standard-library only.

Rates are per-match expected event counts. Player events are Poisson conditional
on a shared lognormal match-environment factor, creating controllable positive
within-match dependence. This is an interpretable baseline, not a fitted copula.
"""
import math
import random


def _poisson(lam, rng):
    if lam <= 0:
        return 0
    if lam < 30:
        limit, product, count = math.exp(-lam), 1.0, 0
        while product > limit:
            count += 1
            product *= rng.random()
        return count - 1
    # Normal approximation only for high rates.
    return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))


def simulate_event_points(players, n_sims=10000, seed=None,
                          shared_factor_sd=0.15):
    """players: {id: {event_name: expected_count, ... , 'points': {event: points}}}.

    Returns each player's simulated points and summary quantiles. Shared
    lognormal factor makes same-match event volumes move together.
    """
    rng = random.Random(seed)
    totals = {pid: [] for pid in players}
    for _ in range(n_sims):
        z = rng.gauss(0.0, shared_factor_sd)
        shared = math.exp(z - 0.5 * shared_factor_sd ** 2)
        for pid, spec in players.items():
            points = 0.0
            scoring = spec.get("points", {})
            for event, rate in spec.items():
                if event == "points":
                    continue
                count = _poisson(max(0.0, float(rate)) * shared, rng)
                points += count * float(scoring.get(event, 0.0))
            totals[pid].append(points)
    summary = {}
    for pid, values in totals.items():
        ordered = sorted(values)
        n = len(ordered)
        summary[pid] = {
            "mean": sum(ordered) / n if n else 0.0,
            "p50": ordered[int(0.50 * (n - 1))] if n else 0.0,
            "p95": ordered[int(0.95 * (n - 1))] if n else 0.0,
            "p99": ordered[int(0.99 * (n - 1))] if n else 0.0,
            "max": ordered[-1] if n else 0.0,
        }
    return {"player_points": totals, "summary": summary,
            "metadata": {"engine": "poisson-events-shared-lognormal-factor",
                         "simulations": n_sims, "seed": seed,
                         "calibration_required": True}}
