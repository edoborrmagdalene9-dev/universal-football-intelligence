import numpy as np
import pandas as pd
import pytest
from dfs_optimizer.src.probability_calibration import ChronologicalIsotonicCalibrator, MulticlassIsotonicCalibrator, chronological_split
from dfs_optimizer.src.ownership_model import estimate_historical_ownership
from dfs_optimizer.src.advanced_lineup_optimizer import optimize_captain_vice_lineup, optimize_stochastic_portfolio, scenario_risk_report

def test_isotonic_calibration_reports_holdout_metrics():
    n=240; p=np.linspace(.02,.98,n); y=(p>.55).astype(int); dates=pd.date_range('2024-01-01',periods=n,tz='UTC')
    train,hold=chronological_split(pd.DataFrame({'date':dates,'p':p,'y':y}),'date',.75)
    cal=ChronologicalIsotonicCalibrator(min_train=100).fit(train.p,train.y,train.date)
    result=cal.evaluate(hold.p,hold.y)
    assert result['n']==len(hold) and 'calibrated_brier' in result and 'expected_calibration_error' in result

def test_isotonic_rejects_nonchronological_data():
    cal=ChronologicalIsotonicCalibrator(min_train=10,min_unique=3)
    with pytest.raises(ValueError): cal.fit(np.linspace(.01,.99,20),np.array([0,1]*10),pd.date_range('2024-01-01',periods=20)[::-1])

def test_ownership_posterior_is_contest_entry_based():
    d=pd.DataFrame({'entry_id':['e1','e1','e2','e2','e3'],'player_id':['a','b','a','c','a']})
    out=estimate_historical_ownership(d); a=out.loc[out.player_id=='a'].iloc[0]
    assert a.selected_entries==3 and a.entries_observed==3
    assert 0<a.ownership_ci_low<=a.ownership_posterior_mean<=a.ownership_ci_high<1

def test_joint_captain_vice_optimizer_respects_roster_and_uniqueness():
    rng=np.random.default_rng(8); sims=rng.normal(np.array([12,10,9,8,7]),np.array([3,2,2,1,1]),size=(300,5))
    players=pd.DataFrame({'player_id':['gk','def','mid','fwd1','fwd2'],'position':['GK','DEF','MID','FWD','FWD'],'salary':[10]*5,'team_id':['A','A','B','B','C']})
    roster,report=optimize_captain_vice_lineup(players,sims,budget=50,roster_size=4,min_positions={'GK':1,'DEF':1,'MID':1,'FWD':1},max_per_team=3)
    assert len(roster)==4 and (roster.role=='CAPTAIN').sum()==1 and (roster.role=='VICE_CAPTAIN').sum()==1
    assert report['captain_id']!=report['vice_captain_id'] and report['scenario_count']==300

def test_scenario_risk_report_requires_shared_valid_scenarios():
    sims=np.arange(600,dtype=float).reshape(200,3); out=scenario_risk_report(sims,[[0,1],[1,2]],alpha=.1)
    assert out['lineups']==2 and len(out['covariance'])==2 and out['scenario_count']==200

def test_stochastic_portfolio_uses_shared_scenarios_and_diversity_constraints():
    rng=np.random.default_rng(12); sims=rng.normal(np.array([12,10,9,8,7]),np.array([3,2,2,1,1]),size=(250,5))
    players=pd.DataFrame({'player_id':['a','b','c','d','e'],'position':['GK','DEF','MID','FWD','FWD'],'salary':[10]*5,'team_id':['A','A','B','B','C']})
    portfolio,report=optimize_stochastic_portfolio(players,sims,budget=40,roster_size=3,lineup_count=2,max_per_team=3,max_player_exposure=1.0,max_overlap=2,max_pairwise_covariance=1e6)
    assert len(portfolio)==6 and report['lineups']==2 and report['scenario_count']==250
    assert report['covariance'][0][1] <= 1e6

def test_multiclass_isotonic_calibration_keeps_probabilities_normalized():
    rng=np.random.default_rng(13); p=rng.dirichlet([4,2,4],size=450); y=np.array(['H','D','A']*150); dates=pd.date_range('2023-01-01',periods=450,tz='UTC')
    train,hold=chronological_split(pd.DataFrame({'date':dates,'ph':p[:,0],'pd':p[:,1],'pa':p[:,2],'outcome':y}), 'date', .75)
    cal=MulticlassIsotonicCalibrator(min_train=200,min_class_outcomes=10).fit(train[['ph','pd','pa']].to_numpy(),train.outcome,train.date)
    calibrated=cal.predict(hold[['ph','pd','pa']].to_numpy())
    assert np.allclose(calibrated.sum(axis=1),1.0) and np.all((calibrated>=0)&(calibrated<=1))
    assert cal.evaluate(hold[['ph','pd','pa']].to_numpy(),hold.outcome)['n']==len(hold)

def test_ownership_refuses_to_mix_slates_and_can_include_zero_owned_pool():
    d=pd.DataFrame({'entry_id':['e1','e1','e2'],'player_id':['a','b','a'],'slate_id':['s1','s1','s2']})
    with pytest.raises(ValueError): estimate_historical_ownership(d)
    d=d.drop(columns=['slate_id'])
    out=estimate_historical_ownership(d,player_pool=['a','b','c'])
    c=out.loc[out.player_id=='c'].iloc[0]
    assert c.selected_entries==0 and c.observed_ownership==0
