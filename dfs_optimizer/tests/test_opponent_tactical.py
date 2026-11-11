import pytest
from dfs_optimizer.src.opponent_model import joint_pick_matrix, pearson_overlap, duplication_summary
from dfs_optimizer.src.tactical import adjusted_event_rates, state_conditioned_event_rates

def test_joint_picks_and_overlap():
    ids, matrix = joint_pick_matrix([['A','B'], ['A','C']], ['A','B','C'])
    assert ids == ['A','B','C']
    assert matrix[0,1] == pytest.approx(.5)
    assert pearson_overlap(['A','B'], ['A','C']) == pytest.approx(.5)
    assert duplication_summary(['A','B'], [['A','B'], ['A','C']])['exact_duplicate_rate'] == pytest.approx(.5)

def test_tactical_and_state_rates():
    assert adjusted_event_rates({'tackles':2}, {'tackles':1.2}, {'tackles':1.5})['tackles'] == pytest.approx(3.6)
    mixed = state_conditioned_event_rates({'lead':{'tackles':2}, 'trail':{'tackles':4}}, {'lead':.25, 'trail':.75})
    assert mixed['tackles'] == pytest.approx(3.5)
