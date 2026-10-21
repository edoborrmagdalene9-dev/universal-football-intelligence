"""Monte Carlo portfolio evaluation using shared player outcomes and an opponent field.

This is a practical, auditable approximation for top-heavy contests, not an exact
reimplementation of Hunter et al. It needs empirical player SDs and actual/opponent
lineups when available; otherwise results are scenario analysis only.
"""
from __future__ import annotations
import numpy as np

def evaluate_portfolio(portfolios, player_means, player_sds, opponent_lineups=None,
                       simulations=10000, seed=17, top_percentile=0.01):
    if simulations < 100: raise ValueError("simulations must be >= 100")
    if not portfolios: raise ValueError("At least one portfolio lineup is required")
    rng = np.random.default_rng(seed)
    all_ids = sorted({str(p) for row in portfolios for p in row} |
                     {str(p) for row in (opponent_lineups or []) for p in row})
    missing = [p for p in all_ids if p not in player_means]
    if missing: raise ValueError("Missing player means for: "+", ".join(missing[:10]))
    means = np.array([float(player_means[p]) for p in all_ids])
    sds = np.array([max(0.0,float(player_sds.get(p,0))) for p in all_ids])
    idx = {p:i for i,p in enumerate(all_ids)}
    # Same simulated player outcome is shared across every lineup containing that player.
    draws = np.maximum(0, rng.normal(means, sds, size=(simulations,len(all_ids))))
    def lineup_scores(rows):
        return np.stack([draws[:,[idx[str(p)] for p in row]].sum(axis=1) for row in rows],axis=1)
    ours = lineup_scores(portfolios)
    best_ours = ours.max(axis=1)
    if opponent_lineups:
        opp = lineup_scores(opponent_lineups)
        field_best = opp.max(axis=1)
        win_rate = float(np.mean(best_ours > field_best))
        tie_rate = float(np.mean(np.isclose(best_ours,field_best)))
        rank1_or_tie = win_rate+tie_rate
        top_cut = np.quantile(field_best, 1-top_percentile)
        top_rate = float(np.mean(best_ours >= top_cut))
    else:
        field_best = None
        win_rate = tie_rate = rank1_or_tie = top_rate = None
        top_cut = None
    return {
        "simulations": simulations, "portfolio_size": len(portfolios),
        "expected_best_entry_score": float(best_ours.mean()),
        "best_entry_score_p50": float(np.quantile(best_ours,.50)),
        "best_entry_score_p95": float(np.quantile(best_ours,.95)),
        "best_entry_score_p99": float(np.quantile(best_ours,.99)),
        "probability_any_entry_beats_opponent_field": win_rate,
        "probability_tie_or_beat_field_best": rank1_or_tie,
        "estimated_top_percentile_rate": top_rate,
        "opponent_field_best_score_cutoff": float(top_cut) if top_cut is not None else None,
        "warning": "Scenario estimate only; quality depends on calibrated player distributions and representative opponent lineups. It is not a guaranteed rank or exact Hunter et al. solver."
    }
