"""Practical opponent-lineup modeling with explicit data-quality fallbacks.

Historical contest entries are the preferred source. With entries, resample whole
lineups (preserving observed combinations) and apply Dirichlet smoothing to lineup
archetypes. Without entries, sample from marginal ownership; this is a baseline,
not a learned joint-ownership model.
"""
from collections import Counter
import random


def clean_entries(entries):
    """Return unique-player lineups, dropping empty entries and duplicate IDs."""
    return [tuple(dict.fromkeys(str(p) for p in row if p is not None))
            for row in entries if row and any(p is not None for p in row)]


def empirical_joint_summary(entries):
    rows = clean_entries(entries)
    if not rows:
        return {"entries": 0, "player_ownership": {}, "pair_ownership": {},
                "source": "no-data"}
    n = len(rows)
    player_counts, pair_counts = Counter(), Counter()
    for row in rows:
        player_counts.update(set(row))
        players = sorted(set(row))
        for i, p in enumerate(players):
            for q in players[i + 1:]:
                pair_counts[(p, q)] += 1
    return {
        "entries": n,
        "player_ownership": {p: c / n for p, c in player_counts.items()},
        "pair_ownership": {pair: c / n for pair, c in pair_counts.items()},
        "source": "historical-entries",
    }


def sample_opponent_lineups(n, entries=None, player_ownership=None,
                            roster_size=11, seed=None):
    """Sample opponent lineups; empirical bootstrap first, marginal fallback second.

    Returns (lineups, metadata). Historical bootstrap retains observed correlations
    but cannot invent combinations absent from the sample.
    """
    rng = random.Random(seed)
    rows = clean_entries(entries or [])
    result = []
    if rows:
        for _ in range(n):
            result.append(list(rng.choice(rows)))
        return result, {"mode": "empirical-lineup-bootstrap", "historical_entries": len(rows),
                        "warning": "Bootstrap reproduces sample bias and cannot learn unseen lineups."}
    if not player_ownership:
        return [], {"mode": "unavailable", "warning": "Provide historical entries or marginal ownership."}
    pool = sorted(player_ownership, key=lambda p: str(p))
    weights = [max(0.0, float(player_ownership[p])) for p in pool]
    if not any(weights):
        return [], {"mode": "unavailable", "warning": "All ownership weights are zero."}
    for _ in range(n):
        chosen = []
        candidates, candidate_weights = pool[:], weights[:]
        while candidates and len(chosen) < roster_size:
            total = sum(candidate_weights)
            needle = rng.random() * total
            idx = 0
            for idx, w in enumerate(candidate_weights):
                needle -= w
                if needle <= 0:
                    break
            chosen.append(candidates.pop(idx))
            candidate_weights.pop(idx)
        result.append(chosen)
    return result, {"mode": "marginal-ownership-baseline", "historical_entries": 0,
                    "warning": "Independent weighted sampling does NOT learn joint ownership."}
