"""Solver-independent small-pool optimizer and honest MIQP fallback.

For small pools, exhaustive enumeration evaluates the actual quadratic objective
without needing CVXPY or a commercial solver. For larger pools this raises rather
than silently pretending a heuristic is an exact MIQP solution.
"""
from itertools import combinations


def exhaustive_binary_optimizer(means, covariance, salaries, salary_cap,
                                roster_size, ownership=None,
                                variance_weight=0.05, ownership_penalty=0.0,
                                max_players=24):
    ids = list(means)
    n = len(ids)
    if n > max_players:
        raise ValueError(f"Exact fallback limited to {max_players} players; install a MIQP solver or reduce the candidate pool.")
    if roster_size > n:
        raise ValueError("roster_size exceeds player count")
    ownership = ownership or {}
    best = None
    best_value = float("-inf")
    for chosen in combinations(ids, roster_size):
        if sum(float(salaries[p]) for p in chosen) > salary_cap:
            continue
        mean = sum(float(means[p]) for p in chosen)
        quad = sum(float(covariance.get((p, q), covariance.get((q, p), 0.0)))
                   for p in chosen for q in chosen)
        own = sum(float(ownership.get(p, 0.0)) for p in chosen)
        value = mean + variance_weight * quad - ownership_penalty * own
        if value > best_value:
            best_value, best = value, chosen
    if best is None:
        raise ValueError("No feasible lineup satisfies salary and roster constraints")
    return {"lineup": list(best), "objective": best_value,
            "engine": "exact-enumeration", "players_considered": n,
            "objective_note": "Quadratic objective is optimized exactly only within this small candidate pool."}
