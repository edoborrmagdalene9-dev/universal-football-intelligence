"""Bayesian ownership estimation and lineup leverage helpers."""
from __future__ import annotations
from collections import Counter
from typing import Iterable, Mapping
import numpy as np

def dirichlet_multinomial_ownership(lineups: Iterable[Iterable[str]],
                                    player_ids: Iterable[str],
                                    prior_strength: float = 1.0) -> dict[str,float]:
    """Posterior mean ownership from observed lineups with symmetric Dirichlet prior."""
    if prior_strength <= 0: raise ValueError("prior_strength must be positive")
    players = list(dict.fromkeys(map(str, player_ids)))
    rows = [set(map(str, row)) for row in lineups]
    if not rows: return {p: 0.0 for p in players}
    counts = Counter(p for row in rows for p in row)
    # Ownership is the fraction of entries containing the player, not slot count.
    return {p: (sum(p in row for row in rows) + prior_strength) /
               (len(rows) + 2*prior_strength) for p in players}

def leverage_index(optimal_roster_probability: Mapping[str,float],
                   ownership: Mapping[str,float], epsilon: float = 1e-6) -> dict[str,float]:
    result = {}
    for player, prob in optimal_roster_probability.items():
        if not 0 <= float(prob) <= 1: raise ValueError(f"Invalid roster probability for {player}")
        own = min(1.0, max(0.0, float(ownership.get(player, 0.0))))
        result[player] = float(prob) / max(epsilon, own)
    return result

def ownership_summary(lineups: Iterable[Iterable[str]]) -> dict:
    rows = [set(map(str, row)) for row in lineups]
    if not rows: return {"entries": 0, "ownership": {}, "pair_counts": {}}
    own = Counter(p for row in rows for p in row)
    pairs = Counter()
    for row in rows:
        values = sorted(row)
        for i,a in enumerate(values):
            for b in values[i+1:]: pairs[(a,b)] += 1
    return {"entries": len(rows), "ownership": {p:c/len(rows) for p,c in own.items()},
            "pair_counts": {f"{a}|{b}":c for (a,b),c in pairs.items()}}

def meets_contrarian_rules(lineup: Iterable[str], ownership: Mapping[str,float],
                           max_ownership_sum: float, low_owned_threshold: float = 0.10,
                           min_low_owned: int = 2) -> bool:
    players = list(map(str, lineup))
    return (sum(float(ownership.get(p, 0.0)) for p in players) <= max_ownership_sum
            and sum(float(ownership.get(p, 0.0)) <= low_owned_threshold for p in players) >= min_low_owned)
