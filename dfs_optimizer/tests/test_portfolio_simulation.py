import pytest
from dfs_optimizer.src.portfolio_simulation import evaluate_portfolio

def test_portfolio_simulation_reuses_player_draws_and_returns_tail_metrics():
    result=evaluate_portfolio([["a","b"],["a","c"]],{"a":10,"b":8,"c":7},
                              {"a":2,"b":3,"c":3},[["b","c"]],simulations=1000,seed=1)
    assert result["simulations"] == 1000
    assert result["best_entry_score_p99"] >= result["best_entry_score_p95"]
    assert 0 <= result["probability_tie_or_beat_field_best"] <= 1
    with pytest.raises(ValueError):
        evaluate_portfolio([["a"]],{}, {},simulations=100)
