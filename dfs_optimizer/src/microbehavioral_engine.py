"""Opt-in micro-behavioral feature engineering. Missing telemetry is never fabricated.

These features are transparent research hooks, not validated causal effects. Supply
licensed observations and backtested coefficients before relying on adjustments.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

FEATURE_REGISTRY = {
 "safe_circulator_vs_progressive_risk":"pass_length_mean",
 "defensive_blocker_vs_aggressive_tracker":"interceptions_per90",
 "zonal_target_box_entry":"opponent_box_touches_per90",
 "press_resistance":"pass_completion_under_pressure",
 "transition_speed":"transition_attacks_per90",
 "low_block_pass_inflation":"opponent_low_block_rate",
 "press_trigger_interception_surge":"opponent_press_intensity",
 "flank_vulnerability":"opponent_flank_chances_conceded",
 "set_piece_concession_weakness":"opponent_set_piece_aerial_loss_rate",
 "referee_card_severity":"referee_cards_per_foul",
 "tactical_neutralization":"playmaker_marking_intensity",
 "goalkeeper_save_inflation":"opponent_shots_on_target",
 "pass_boundary_proximity":"projected_completed_passes",
 "non_tackle_defensive_value":"interceptions_per90",
 "shot_quality_to_sot":"xg_per_shot",
 "assist_chance_created_multiplier":"chances_created_per90",
 "penalty_taker_dominance":"penalty_share",
 "clean_sheet_55_min_survival":"probability_minutes_ge55",
 "substitution_risk_decay":"substitution_hazard",
 "disciplinary_cascade":"early_yellow_probability",
 "biomechanical_fatigue_decay":"recent_high_intensity_distance",
 "circadian_travel_disruption":"travel_time_zone_delta",
 "weather_pitch_friction":"weather_pitch_friction",
 "recency_bias_ownership":"recent_points_vs_baseline",
 "salary_floor_inefficiency":"salary_remaining",
 "covariance_tail_risk":"team_goal_environment",
 "multi_entry_divergence":"portfolio_exposure",
 "late_swap_state_transition":"late_swap_available",
 "contest_variance_tuner":"contest_payout_top_heaviness",
 "edge_decay_monitor":"market_projection_change",
}

def fingerprint_player_roles(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with transparent, rule-relevant role tags."""
    out=df.copy()
    needed=("pass_length_mean","pass_completion_under_pressure","interceptions_per90",
            "tackles_won_per90","opponent_box_touches_per90","transition_attacks_per90","xg_per_shot")
    for col in needed:
        if col not in out: out[col]=np.nan
    labels=[]
    for _,r in out.iterrows():
        tags=[]
        if pd.notna(r["pass_length_mean"]): tags.append("progressive_risk_taker" if r["pass_length_mean"]>=20 else "safe_circulator")
        if pd.notna(r["interceptions_per90"]) and pd.notna(r["tackles_won_per90"]): tags.append("defensive_blocker" if r["interceptions_per90"]>=r["tackles_won_per90"] else "aggressive_tracker")
        if pd.notna(r["opponent_box_touches_per90"]): tags.append("zonal_target" if r["opponent_box_touches_per90"]>=1 else "peripheral_attacker")
        if pd.notna(r["pass_completion_under_pressure"]): tags.append("press_resistant" if r["pass_completion_under_pressure"]>=.8 else "press_vulnerable")
        if pd.notna(r["transition_attacks_per90"]): tags.append("transition_speed" if r["transition_attacks_per90"]>=2 else "build_up_oriented")
        if pd.notna(r["xg_per_shot"]): tags.append("high_shot_quality" if r["xg_per_shot"]>=.12 else "low_shot_quality")
        labels.append("|".join(tags) if tags else "insufficient_telemetry")
    out["behavioral_fingerprint"]=labels
    out["fingerprint_data_completeness"]=out[list(FEATURE_REGISTRY.values())].notna().mean(axis=1) if all(c in out for c in FEATURE_REGISTRY.values()) else np.nan
    return out

def apply_tactical_multipliers(projections: pd.DataFrame) -> pd.DataFrame:
    """Apply explicit non-negative optional multipliers; absent inputs are neutral."""
    out=projections.copy()
    pairs={"mean_passes":"pass_volume_multiplier","mean_interceptions":"interception_multiplier",
      "mean_shots_on_target":"shot_on_target_multiplier","mean_goals":"goal_multiplier",
      "mean_assists":"assist_multiplier","clean_sheet_prob":"clean_sheet_multiplier","mean_saves":"save_multiplier"}
    for target,mult in pairs.items():
        if target not in out: continue
        values=pd.to_numeric(out[mult],errors="coerce").fillna(1.0).to_numpy(float) if mult in out else np.ones(len(out))
        if np.any(~np.isfinite(values)) or np.any(values<0): raise ValueError(f"{mult} must be finite and non-negative")
        out[target]=pd.to_numeric(out[target],errors="raise").to_numpy(float)*values
        if target=="clean_sheet_prob": out[target]=out[target].clip(0,1)
    return out

def step_boundary_report(projected_passes, passes_per_point=5):
    if passes_per_point<=0: raise ValueError("passes_per_point must be positive")
    p=float(projected_passes)
    if not np.isfinite(p) or p<0: raise ValueError("projected_passes must be finite and non-negative")
    lower=int(p//passes_per_point)*passes_per_point
    return {"projected_passes":p,"current_bracket_points":int(p//passes_per_point),
      "next_threshold_passes":lower+passes_per_point,"passes_to_next_threshold":max(0.0,lower+passes_per_point-p),
      "warning":"Expected pass count alone cannot determine expected step-function points; use a calibrated pass-count distribution."}
