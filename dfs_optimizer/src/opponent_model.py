"""Opponent lineup behaviour and joint ownership baselines."""
from __future__ import annotations
import numpy as np


def dirichlet_multinomial_lineups(lineup_categories, concentration=20.0, n_entries=1000, seed=None):
    """Sample category counts. Categories should represent observed lineup archetypes."""
    keys = list(lineup_categories)
    weights = np.asarray([lineup_categories[k] for k in keys], dtype=float)
    if not keys or np.any(weights < 0) or not np.all(np.isfinite(weights)) or weights.sum() <= 0:
        raise ValueError("lineup_categories must have non-negative weights and positive sum")
    if concentration <= 0 or n_entries < 1:
        raise ValueError("concentration and n_entries must be positive")
    rng = np.random.default_rng(seed)
    p = rng.dirichlet(weights / weights.sum() * float(concentration))
    counts = rng.multinomial(int(n_entries), p)
    return {key: int(count) for key, count in zip(keys, counts)}


def joint_pick_matrix(lineups, player_ids=None):
    """Estimate pairwise joint pick frequencies from historical entry lineups."""
    rows = [set(row) for row in lineups]
    if not rows:
        raise ValueError("at least one historical lineup is required")
    ids = list(player_ids) if player_ids is not None else sorted(set().union(*rows), key=str)
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("player IDs must be non-empty and unique")
    matrix = np.zeros((len(ids), len(ids)), dtype=float)
    for row in rows:
        present = np.fromiter((player in row for player in ids), dtype=float, count=len(ids))
        matrix += np.outer(present, present)
    return ids, matrix / len(rows)


def pearson_overlap(lineup, opponent_lineup):
    """Normalized overlap: intersection / geometric mean of roster sizes."""
    a, b = set(lineup), set(opponent_lineup)
    return float(len(a & b) / np.sqrt(len(a) * len(b))) if a and b else 0.0


def duplication_summary(candidate_lineup, opponent_lineups):
    field = list(opponent_lineups)
    if not field:
        raise ValueError("opponent_lineups cannot be empty")
    overlaps = np.asarray([pearson_overlap(candidate_lineup, x) for x in field])
    duplicates = np.asarray([set(candidate_lineup) == set(x) for x in field])
    return {"mean_overlap": float(overlaps.mean()), "max_overlap": float(overlaps.max()),
            "share_overlap_at_least_half": float(np.mean(overlaps >= 0.5)),
            "exact_duplicate_rate": float(duplicates.mean())}
