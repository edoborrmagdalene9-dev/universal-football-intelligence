"""Configurable binary ILP lineup optimizer."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence
import pulp


@dataclass(frozen=True)
class Player:
    player_id: str
    name: str
    team: str
    position: str
    salary: int
    projection: float


@dataclass(frozen=True)
class RosterRules:
    roster_size: int
    salary_cap: int
    position_bounds: Mapping[str, tuple[int, int]]
    max_players_per_team: int | None = None
    min_salary: int = 0


def optimize_lineup(players: Sequence[Player], rules: RosterRules) -> list[Player]:
    if not players:
        raise ValueError("player pool is empty")
    ids = [p.player_id for p in players]
    if len(ids) != len(set(ids)):
        raise ValueError("player_id values must be unique")
    if rules.roster_size <= 0 or rules.salary_cap <= 0:
        raise ValueError("roster_size and salary_cap must be positive")
    if any(p.salary < 0 for p in players):
        raise ValueError("salary cannot be negative")
    model = pulp.LpProblem("ufi_dfs_lineup", pulp.LpMaximize)
    x = {p.player_id: pulp.LpVariable(f"pick_{i}", cat="Binary")
         for i, p in enumerate(players)}
    by_id = {p.player_id: p for p in players}
    model += pulp.lpSum(by_id[i].projection * x[i] for i in x)
    model += pulp.lpSum(x.values()) == rules.roster_size
    model += pulp.lpSum(by_id[i].salary * x[i] for i in x) <= rules.salary_cap
    model += pulp.lpSum(by_id[i].salary * x[i] for i in x) >= rules.min_salary
    for position, (low, high) in rules.position_bounds.items():
        if low < 0 or high < low:
            raise ValueError(f"invalid bounds for {position}")
        picks = [x[p.player_id] for p in players if p.position == position]
        model += pulp.lpSum(picks) >= low
        model += pulp.lpSum(picks) <= high
    if rules.max_players_per_team is not None:
        for team in {p.team for p in players}:
            model += pulp.lpSum(x[p.player_id] for p in players if p.team == team) <= rules.max_players_per_team
    status = model.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] != "Optimal":
        raise ValueError(f"No optimal feasible lineup: {pulp.LpStatus[status]}")
    return [p for p in players if pulp.value(x[p.player_id]) > 0.5]
