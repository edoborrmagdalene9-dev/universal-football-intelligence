from datetime import date, timedelta
import numpy as np
from dfs_optimizer.src.predictive_models.dixon_coles import fit_dixon_coles, score_grid, match_probabilities

def test_fit_and_grid_are_normalized():
    rows=[]
    start=date(2024,1,1)
    scores=[(1,0),(2,1),(0,0),(1,1),(0,1),(3,1),(2,0),(1,2),(0,0),(2,2),(1,0),(0,2)]
    for i,(hg,ag) in enumerate(scores):
        rows.append({"date":(start+timedelta(days=i*7)).isoformat(),
                     "home_team":"A" if i%2==0 else "B",
                     "away_team":"B" if i%2==0 else "A",
                     "home_goals":hg,"away_goals":ag})
    fit=fit_dixon_coles(rows,maxiter=300)
    grid=score_grid(fit,"A","B",max_goals=8)
    assert grid.shape==(9,9)
    assert np.isclose(grid.sum(),1.0)
    probs=match_probabilities(grid)
    assert np.isclose(probs["home_win"]+probs["draw"]+probs["away_win"],1.0)
    assert 0 <= probs["home_clean_sheet"] <= 1
