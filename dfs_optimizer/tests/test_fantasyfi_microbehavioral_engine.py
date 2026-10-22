import numpy as np
import pandas as pd
import pytest
from dfs_optimizer.src.fantasyfi_monte_carlo import run_fantasyfi_monte_carlo
from dfs_optimizer.src.microbehavioral_engine import apply_tactical_multipliers, fingerprint_player_roles, step_boundary_report

def sample_players():
    return pd.DataFrame({"player_name":["High-pass CB","Aggressive MID"],"position":["DEF","MID"],
      "start_probability":[1.0,.95],"appearance_probability":[1.0,.98],"mean_passes":[88.,32.],
      "mean_interceptions":[2.,1.],"mean_shots_on_target":[.5,.2],"mean_goals":[.1,.05],
      "mean_assists":[0.,.1],"clean_sheet_prob":[.45,0.],"mean_yellow_cards":[.1,.4],"mean_red_cards":[.01,.02]})

def test_monte_carlo_reproducible_shape_and_tails():
    df=sample_players(); summary,matrix=run_fantasyfi_monte_carlo(df,num_sims=1000,seed=7)
    assert matrix.shape==(1000,2)
    assert {"Floor_5th","Ceiling_95th","Ceiling_99th"}<=set(summary.columns)
    _,matrix2=run_fantasyfi_monte_carlo(df,num_sims=1000,seed=7)
    assert np.array_equal(matrix,matrix2)

def test_invalid_probability_rejected():
    df=sample_players(); df.loc[0,"clean_sheet_prob"]=1.2
    with pytest.raises(ValueError): run_fantasyfi_monte_carlo(df,num_sims=1000)

def test_boundary_and_multiplier():
    assert step_boundary_report(49)["passes_to_next_threshold"]==1
    assert step_boundary_report(50)["current_bracket_points"]==10
    out=apply_tactical_multipliers(pd.DataFrame({"mean_passes":[80.],"pass_volume_multiplier":[1.1]}))
    assert out.loc[0,"mean_passes"]==pytest.approx(88.)

def test_fingerprint_does_not_invent_data():
    out=fingerprint_player_roles(pd.DataFrame({"player_name":["Unknown"]}))
    assert out.loc[0,"behavioral_fingerprint"]=="insufficient_telemetry"
