"""Contest-level rank, tie, payout, and ROI simulation."""
import random


def score_lineup(lineup, player_points, scoring_weights=None):
    """Score a lineup from player point outcomes; missing players score zero."""
    return sum(float(player_points.get(p, 0.0)) *
               float((scoring_weights or {}).get(p, 1.0)) for p in lineup)


def evaluate_contest(candidate_scores, opponent_scores, payouts):
    """Expected payout under rank payouts; tied ranks split prizes across tied slots.

    payouts maps 1-based finishing rank to prize amount, e.g. {1: 100, 2: 40}.
    """
    field = [float(x) for x in opponent_scores]
    results = []
    for candidate in candidate_scores:
        all_scores = field + [float(candidate)]
        better = sum(s > candidate for s in field)
        tied = sum(s == candidate for s in field)
        first_rank = better + 1
        prize = sum(float(payouts.get(rank, 0.0))
                    for rank in range(first_rank, first_rank + tied + 1)) / (tied + 1)
        results.append({"score": float(candidate), "rank": first_rank,
                        "tied_entries_including_candidate": tied + 1, "payout": prize})
    return {"results": results,
            "expected_payout": sum(r["payout"] for r in results) / len(results) if results else 0.0,
            "top_1_rate": sum(r["rank"] == 1 for r in results) / len(results) if results else 0.0}


def simulate_contest(candidate_lineups, opponent_lineups, player_simulations,
                     payouts, entry_fee=0.0, seed=None):
    """Use shared simulation index for player outcomes and evaluate field payout.

    player_simulations maps player ID to a list of simulated points.
    """
    if not player_simulations:
        raise ValueError("player_simulations cannot be empty")
    n = min(len(v) for v in player_simulations.values())
    if n == 0:
        raise ValueError("Each player needs at least one simulated outcome")
    rng = random.Random(seed)
    # Re-sample the simulation row indices to support repeated contest trials.
    trials = []
    for _ in range(n):
        idx = rng.randrange(n)
        outcomes = {p: values[idx] for p, values in player_simulations.items()}
        cand_scores = [score_lineup(lu, outcomes) for lu in candidate_lineups]
        opp_scores = [score_lineup(lu, outcomes) for lu in opponent_lineups]
        ev = evaluate_contest(cand_scores, opp_scores, payouts)
        for item in ev["results"]:
            item["net"] = item["payout"] - entry_fee
        trials.append(ev)
    return {"trials": trials,
            "mean_payout_per_candidate": sum(t["expected_payout"] for t in trials) / len(trials) if trials else 0.0,
            "entry_fee": entry_fee,
            "warning": "Opponent lineups and player outcomes must be realistic and independently validated."}
