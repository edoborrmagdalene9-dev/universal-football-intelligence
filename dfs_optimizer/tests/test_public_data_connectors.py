import pandas as pd
from dfs_optimizer.src.source_connectors import statsbomb_matches_to_dixon_coles, aggregate_statsbomb_player_events

def test_statsbomb_matches_normalize_to_dixon_coles_schema():
    d=pd.DataFrame([{'match_date':'2024-01-01','home_team.home_team_name':'Home','away_team.away_team_name':'Away','home_score':2,'away_score':1}])
    out=statsbomb_matches_to_dixon_coles(d)
    assert out.loc[0,'home_team']=='Home' and out.loc[0,'home_goals']==2 and out.loc[0,'away_goals']==1

def test_event_aggregates_observed_events_without_claiming_tracking():
    d=pd.DataFrame({'player.id':[1,1,1,2],'player.name':['A','A','A','B'],'type.name':['Shot','Pass','Interception','Shot'],'shot.statsbomb_xg':[.3,None,None,.1],'shot.outcome.name':['Goal',None,None,'Saved'],'pass.outcome.name':[None,None,None,None],'pass.goal_assist':[False,True,False,False]})
    out=aggregate_statsbomb_player_events(d).set_index('player_name')
    assert out.loc['A','goals']==1 and out.loc['A','completed_passes']==1 and out.loc['A','interceptions']==1 and out.loc['A','assists']==1
    assert 'tracking' not in out.loc['A','source'].lower()
