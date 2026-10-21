"""Configurable FantasyFi lineup and diversified portfolio optimizer."""
from __future__ import annotations
from itertools import combinations
from typing import Mapping, Sequence
import pulp

def optimize_lineup(players: Sequence[Mapping], roster_size: int, salary_cap: float,
                    positional_slots: Mapping[str,int], team_cap: int | None = None,
                    captain_multiplier: float = 1.0, require_low_owned: int = 0,
                    low_owned_threshold: float = 0.10,
                    max_ownership_sum: float | None = None,
                    solver=None) -> dict:
    """Maximize projected points under salary, roster, position and optional ownership rules.

    Each player row needs id, team, position, salary, projection; ownership is optional.
    Captain/MVP slots are not platform-universal, so multiplier is an optional single
    captain decision here. Use the platform's actual roster rules before enabling it.
    """
    if roster_size < 1 or salary_cap <= 0: raise ValueError("Invalid roster_size/salary_cap")
    ids = [str(p["id"]) for p in players]
    if len(ids) != len(set(ids)): raise ValueError("Player IDs must be unique")
    byid = {str(p["id"]):p for p in players}
    prob = pulp.LpProblem("FantasyFi_Lineup", pulp.LpMaximize)
    x = {i:pulp.LpVariable("pick_"+str(k), cat="Binary") for k,i in enumerate(ids)}
    captain = {i:pulp.LpVariable("captain_"+str(k), cat="Binary") for k,i in enumerate(ids)} if captain_multiplier != 1 else {}
    prob += pulp.lpSum(float(byid[i]["projection"])*x[i] +
                       (float(byid[i]["projection"])*(captain_multiplier-1)*captain[i] if captain else 0)
                       for i in ids)
    prob += pulp.lpSum(x.values()) == roster_size
    prob += pulp.lpSum(float(byid[i]["salary"])*x[i] for i in ids) <= salary_cap
    for pos, count in positional_slots.items():
        prob += pulp.lpSum(x[i] for i in ids if str(byid[i]["position"]).lower() == pos.lower()) >= int(count)
    if team_cap is not None:
        for team in {str(p["team"]) for p in players}:
            prob += pulp.lpSum(x[i] for i in ids if str(byid[i]["team"]) == team) <= int(team_cap)
    if captain:
        prob += pulp.lpSum(captain.values()) == 1
        for i in ids: prob += captain[i] <= x[i]
    if require_low_owned:
        prob += pulp.lpSum(x[i] for i in ids if float(byid[i].get("ownership",1)) <= low_owned_threshold) >= require_low_owned
    if max_ownership_sum is not None:
        prob += pulp.lpSum(float(byid[i].get("ownership",0))*x[i] for i in ids) <= max_ownership_sum
    status = prob.solve(solver or pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] != "Optimal":
        raise RuntimeError(f"Lineup optimizer status: {pulp.LpStatus[status]}")
    selected = [i for i in ids if pulp.value(x[i]) > 0.5]
    cap = next((i for i in ids if captain and pulp.value(captain[i]) > 0.5), None)
    return {"players": selected, "captain": cap, "projected_points": float(pulp.value(prob.objective)),
            "salary": sum(float(byid[i]["salary"]) for i in selected), "status": pulp.LpStatus[status]}

def optimize_portfolio(players: Sequence[Mapping], lineup_count: int, roster_size: int,
                       salary_cap: float, positional_slots: Mapping[str,int],
                       min_hamming_distance: int = 2, team_cap: int | None = None) -> list[dict]:
    """Sequential ILP portfolio with pairwise minimum symmetric-difference constraints."""
    if lineup_count < 1: raise ValueError("lineup_count must be >= 1")
    ids = [str(p["id"]) for p in players]
    byid = {str(p["id"]):p for p in players}
    if min_hamming_distance < 0 or min_hamming_distance > 2*roster_size:
        raise ValueError("Invalid Hamming distance")
    chosen = []
    for n in range(lineup_count):
        prob = pulp.LpProblem(f"FantasyFi_Portfolio_{n+1}", pulp.LpMaximize)
        x = {i:pulp.LpVariable(f"p{n}_{k}", cat="Binary") for k,i in enumerate(ids)}
        prob += pulp.lpSum(float(byid[i]["projection"])*x[i] for i in ids)
        prob += pulp.lpSum(x.values()) == roster_size
        prob += pulp.lpSum(float(byid[i]["salary"])*x[i] for i in ids) <= salary_cap
        for pos,count in positional_slots.items():
            prob += pulp.lpSum(x[i] for i in ids if str(byid[i]["position"]).lower()==pos.lower()) >= int(count)
        if team_cap is not None:
            for team in {str(p["team"]) for p in players}:
                prob += pulp.lpSum(x[i] for i in ids if str(byid[i]["team"])==team) <= team_cap
        for j, prior in enumerate(chosen):
            # Equal roster size: symmetric difference = 2*(roster_size - overlap).
            prob += pulp.lpSum(x[i] for i in prior) <= roster_size - (min_hamming_distance+1)//2
        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
        if pulp.LpStatus[status] != "Optimal":
            raise RuntimeError(f"Could not produce portfolio lineup {n+1}: {pulp.LpStatus[status]}")
        selected = [i for i in ids if pulp.value(x[i]) > .5]
        chosen.append(selected)
    return [{"players": row, "projected_points": sum(float(byid[i]["projection"]) for i in row),
             "salary": sum(float(byid[i]["salary"]) for i in row)} for row in chosen]
