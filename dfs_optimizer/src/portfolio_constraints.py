"""Portfolio diversity diagnostics and multiplier assignment."""
import numpy as np
import pandas as pd

def hamming_distance(lineup_a,lineup_b): return len(set(lineup_a).symmetric_difference(set(lineup_b)))
def pairwise_diversity_report(lineups):
 rows=[]
 for i in range(len(lineups)):
  for j in range(i+1,len(lineups)): rows.append({'lineup_a':i+1,'lineup_b':j+1,'hamming_distance':hamming_distance(lineups[i],lineups[j]),'overlap_count':len(set(lineups[i])&set(lineups[j]))})
 return pd.DataFrame(rows,columns=['lineup_a','lineup_b','hamming_distance','overlap_count'])
def apply_captain_multipliers(scores,captain_id,vice_captain_id,player_id_col='player_id',score_col='projected_points',captain_multiplier=2.,vice_multiplier=1.5):
 if captain_id==vice_captain_id: raise ValueError('Captain and vice-captain must differ')
 if not np.isfinite(captain_multiplier+vice_multiplier) or not 0<vice_multiplier<=captain_multiplier: raise ValueError('Invalid multipliers')
 if not {player_id_col,score_col}.issubset(scores.columns) or scores[player_id_col].duplicated().any(): raise ValueError('Missing columns or duplicate player IDs')
 if captain_id not in set(scores[player_id_col]) or vice_captain_id not in set(scores[player_id_col]): raise ValueError('Captain/vice must be in player pool')
 out=scores.copy(); out['assigned_multiplier']=1.; out.loc[out[player_id_col]==captain_id,'assigned_multiplier']=captain_multiplier; out.loc[out[player_id_col]==vice_captain_id,'assigned_multiplier']=vice_multiplier; out['multiplied_projected_points']=pd.to_numeric(out[score_col],errors='raise')*out.assigned_multiplier; out['warning']='Verify platform salary and multiplier rules before use'; return out
