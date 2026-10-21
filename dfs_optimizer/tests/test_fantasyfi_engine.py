import pytest
from dfs_optimizer.src.scoring_engine import score_actual, expected_points, penalty_event_ev
from dfs_optimizer.src.ownership_engine import dirichlet_multinomial_ownership, leverage_index, meets_contrarian_rules

def test_exact_scoring_pass_floor_and_tackles_ignored():
    stats={"minutes":90,"started":True,"goals":1,"shots_on_target":1,"completed_passes":49,
           "interceptions_won":2,"tackles_won":20,"yellow_cards":0}
    # 4 appearance + 40 goal + 6 SoT + 9 pass + 8 interception = 67
    assert score_actual(stats,"forward") == 67

def test_defender_clean_sheet_and_conceded_penalty():
    assert score_actual({"minutes":90,"started":True,"goals_conceded":0},"defender") == 24
    assert score_actual({"minutes":90,"started":True,"goals_conceded":2},"defender") == 0

def test_penalty_ev_break_even_and_seventy_percent():
    assert penalty_event_ev(20/66,"forward") == pytest.approx(0)
    assert penalty_event_ev(.7,"forward") == pytest.approx(26.2)

def test_pass_distribution_uses_discrete_thresholds():
    stats={"appearance_probability":0,"xg":0,"xa":0,"x_sot":0,"x_chances_created":0,
           "x_interceptions":0}
    assert expected_points({**stats,"x_passes":49},"midfielder") == pytest.approx(9.8)
    assert expected_points({**stats,"x_passes":50},"midfielder") == pytest.approx(10)

def test_bayesian_ownership_and_leverage():
    own=dirichlet_multinomial_ownership([["a","b"],["a","c"]],["a","b","c"],prior_strength=1)
    assert own["a"] > own["b"]
    lev=leverage_index({"b":.8},own)
    assert lev["b"] > 1
    assert meets_contrarian_rules(["b","c"],{"b":.05,"c":.08},.2)
