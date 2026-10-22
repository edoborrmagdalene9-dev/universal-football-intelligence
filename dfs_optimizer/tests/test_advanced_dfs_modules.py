import numpy as np
import pandas as pd
import pytest
from dfs_optimizer.src.spatial_kinematics import pitch_geometry, derive_player_kinematics
from dfs_optimizer.src.metric_registry import metric_registry, audit_metric_data
from dfs_optimizer.src.prelock_pipeline import validate_prelock_lineups, filter_confirmed_starters
from dfs_optimizer.src.portfolio_constraints import hamming_distance, apply_captain_multipliers

def test_metric_registry_is_exactly_300_unique_and_does_not_claim_training():
 r=metric_registry(); assert len(r)==300 and r.metric_name.nunique()==300; assert not r.used_in_prediction.any()
 a=audit_metric_data(pd.DataFrame({'pitch_length_m':[105,None]})); row=a.loc[a.metric_name=='pitch_length_m'].iloc[0]; assert row.non_null_count==1

def test_spatial_kinematics_derived_from_observed_coordinates():
 assert pitch_geometry(105,68)['area_m2']==7140
 t=pd.DataFrame({'player_id':['p','p','p'],'timestamp':['2026-01-01T00:00:00Z','2026-01-01T00:00:01Z','2026-01-01T00:00:02Z'],'x_m':[0,6,14],'y_m':[0,0,0]})
 out=derive_player_kinematics(t,105,68,5.5); assert out.loc[0,'peak_speed_mps']==8; assert out.loc[0,'high_intensity_distance_m']==14

def test_prelock_only_retains_fresh_confirmed_starters():
 now=pd.Timestamp('2026-10-22T12:00:00Z').to_pydatetime()
 d=pd.DataFrame({'player_id':['a','b'],'team_id':['x','x'],'status':['starter','bench'],'source_timestamp':['2026-10-22T11:59:00Z']*2,'source_url':['https://example.org/lineups']*2})
 valid,report=validate_prelock_lineups(d,'2026-10-22T13:00:00Z',now_utc=now,trusted_source_hosts=['example.org']); players=pd.DataFrame({'player_id':['a','b','c'],'projected_points':[10,9,8]})
 assert filter_confirmed_starters(players,valid).player_id.tolist()==['a']; assert report['lock_window_active']; assert report['source_authority_verified'] is True

def test_hamming_and_multiplier_helpers():
 assert hamming_distance(['a','b'],['b','c'])==2
 out=apply_captain_multipliers(pd.DataFrame({'player_id':['a','b'],'projected_points':[10,8]}),'a','b'); assert out.multiplied_projected_points.tolist()==[20,12]
 with pytest.raises(ValueError): apply_captain_multipliers(pd.DataFrame({'player_id':['a'],'projected_points':[10]}),'a','a')
