import numpy as np
import pytest

from dfs_optimizer.src.correlation import covariance_from_std_corr, portfolio_variance
from dfs_optimizer.src.simulation import simulate_correlated_points, lineup_ceiling
from dfs_optimizer.src.game_state import ScoreState, conditional_minutes, sample_minutes
from dfs_optimizer.src.ownership import dirichlet_ownership, leverage_index
from dfs_optimizer.src.scoring import expected_points, score_realized_events


def test_covariance_and_portfolio_variance():
    cov = covariance_from_std_corr([2, 3], [[1, 0.5], [0.5, 1]])
    assert cov[0, 1] == pytest.approx(3.0)
    assert portfolio_variance(cov, [0, 1]) == pytest.approx(16.0)


def test_invalid_non_psd_correlation_rejected():
    with pytest.raises(ValueError):
        covariance_from_std_corr([1, 1, 1], [[1, .9, -.9], [.9, 1, .9], [-.9, .9, 1]])


def test_simulation_reproducible_and_ceiling():
    cov = np.array([[4.0, 1.0], [1.0, 9.0]])
    a = simulate_correlated_points([5, 6], cov, 1000, seed=7)
    b = simulate_correlated_points([5, 6], cov, 1000, seed=7)
    assert a.shape == (1000, 2)
    assert np.allclose(a, b)
    assert lineup_ceiling(a, [0, 1], .9) > 0


def test_ownership_and_leverage():
    own = dirichlet_ownership([60, 40])
    assert own.sum() == pytest.approx(1.0)
    assert leverage_index(.25, .05) == pytest.approx(5.0)


def test_conditional_minutes_and_score_scoring():
    assert conditional_minutes(60, ScoreState(0, 2), "attacker",
                               {("attacker", "trailing"): 10}) == 70
    assert sample_minutes([(45, .25), (90, .75)], 20, seed=1).shape == (20,)
    assert expected_points({"shots": 3, "yellow": .2}, {"shots": 1, "yellow": -2}) == pytest.approx(2.6)
    assert score_realized_events({"goals": 2, "yellow": 1}, {"goals": 5, "yellow": -1}) == 9
