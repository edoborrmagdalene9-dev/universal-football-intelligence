import pytest
from dfs_optimizer.src.dc_model import score_grid, outcome_probabilities, tau
from dfs_optimizer.src.optimizer import Player, RosterRules, optimize_lineup
from dfs_optimizer.src.portfolio import hamming_distance, validate_portfolio


def test_grid_normalized_and_outcomes_sum():
    grid = score_grid(1.4, 1.0, max_goals=8, rho=-0.08)
    assert sum(grid.values()) == pytest.approx(1.0)
    probs = outcome_probabilities(grid)
    assert sum(probs[k] for k in ("home_win", "draw", "away_win")) == pytest.approx(1.0)


def test_tau_non_low_scoreline_is_one():
    assert tau(2, 2, 1.3, 0.9, -0.1) == 1.0


def test_optimizer_salary_and_roster_constraints():
    players = [
        Player("1", "F1", "A", "FWD", 9000, 12),
        Player("2", "M1", "B", "MID", 6000, 8),
        Player("3", "D1", "C", "DEF", 4000, 5),
        Player("4", "G1", "D", "GK", 3000, 4),
        Player("5", "F2", "B", "FWD", 7000, 9),
    ]
    rules = RosterRules(4, 23000, {"FWD": (1, 1), "MID": (1, 1), "DEF": (1, 1), "GK": (1, 1)})
    lineup = optimize_lineup(players, rules)
    assert len(lineup) == 4
    assert sum(p.salary for p in lineup) <= 23000


def test_portfolio_hamming_distance():
    assert hamming_distance(["a", "b"], ["a", "c"]) == 2
    with pytest.raises(ValueError):
        validate_portfolio([["a", "b"], ["a", "c"]], 3)
