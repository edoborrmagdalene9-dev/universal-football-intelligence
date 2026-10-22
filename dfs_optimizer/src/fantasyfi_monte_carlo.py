"""FantasyFi event-level Monte Carlo engine.

Rule weights are delegated to the existing scoring engine. Inputs are per-match
marginal expectations/probabilities, not guarantees. The default sampler is an
auditable baseline; independently sampled events do not reproduce full football
dependence. Optional team-level shocks add limited shared variation.
"""
from __future__ import annotations
import argparse
import numpy as np
import pandas as pd
from .scoring_engine import RULES, goal_points

_REQUIRED = {"player_name", "position", "start_probability", "mean_passes",
 "mean_interceptions", "mean_shots_on_target", "mean_goals", "mean_assists",
 "clean_sheet_prob", "mean_yellow_cards", "mean_red_cards"}

def _prob(values, name):
    a = np.asarray(values, dtype=float)
    if np.any(~np.isfinite(a)) or np.any((a < 0) | (a > 1)):
        raise ValueError(f"{name} must contain finite probabilities in [0, 1]")
    return a

def _nonnegative(values, name):
    a = np.asarray(values, dtype=float)
    if np.any(~np.isfinite(a)) or np.any(a < 0):
        raise ValueError(f"{name} must contain finite non-negative values")
    return a

def run_fantasyfi_monte_carlo(player_df: pd.DataFrame, num_sims: int = 10_000,
                              seed: int = 42, team_shock_sd: float = 0.0):
    """Return summary dataframe and (simulations, players) score matrix.

    Required means/probabilities are explicit. Optional columns: mean_chances_created,
    mean_saves, mean_penalties_saved, mean_penalties_missed, mean_own_goals,
    mean_goals_conceded, appearance_probability, minutes_mean, minutes_sd, team_id.
    """
    if num_sims < 100: raise ValueError("num_sims must be at least 100")
    if team_shock_sd < 0 or not np.isfinite(team_shock_sd): raise ValueError("team_shock_sd must be finite and >= 0")
    missing = sorted(_REQUIRED - set(player_df.columns))
    if missing: raise ValueError("Missing required columns: " + ", ".join(missing))
    if player_df.empty: raise ValueError("player_df must contain at least one player")
    df = player_df.reset_index(drop=True).copy()
    n = len(df); rng = np.random.default_rng(seed)
    start_p = _prob(df["start_probability"], "start_probability")
    appearance_p = _prob(df["appearance_probability"], "appearance_probability") if "appearance_probability" in df else start_p.copy()
    appearance_p = np.maximum(appearance_p, start_p)
    cs_p = _prob(df["clean_sheet_prob"], "clean_sheet_prob")
    positions = df["position"].astype(str).str.upper().to_numpy()
    valid = {"FWD","FW","F","FORWARD","ST","MID","MF","M","MIDFIELDER","DEF","DF","D","DEFENDER","CB","FB","WB","GK","G","GOALKEEPER"}
    unknown = sorted(set(positions) - valid)
    if unknown: raise ValueError("Unknown position(s): " + ", ".join(unknown))
    def rate(column):
        return _nonnegative(df[column] if column in df else np.zeros(n), column)
    sim_start = rng.binomial(1, start_p, size=(num_sims,n))
    # Conditional substitute probability ensures the total appearance rate is appearance_p,
    # rather than accidentally drawing a second independent starter-probability event.
    sub_p = np.divide(appearance_p-start_p, 1-start_p, out=np.zeros_like(start_p), where=(start_p < 1))
    sub_p = np.clip(sub_p, 0, 1)
    sim_sub = (1-sim_start) * rng.binomial(1, sub_p, size=(num_sims,n))
    sim_appear = np.maximum(sim_start, sim_sub)
    if "minutes_mean" in df:
        minutes_mean = _nonnegative(df["minutes_mean"], "minutes_mean")
        minutes_sd = _nonnegative(df["minutes_sd"] if "minutes_sd" in df else np.full(n, 10.0), "minutes_sd")
        minutes = rng.normal(minutes_mean[None,:], minutes_sd[None,:], (num_sims,n))
    else:
        # Baseline minutes differ for starters and substitutes; calibrate these from data when available.
        starter_minutes = rng.normal(78.0, 12.0, (num_sims,n))
        substitute_minutes = rng.normal(22.0, 10.0, (num_sims,n))
        minutes = np.where(sim_start == 1, starter_minutes, substitute_minutes)
    minutes = np.clip(minutes,0,120) * sim_appear
    active = (minutes > 0).astype(int)
    shock = None
    if team_shock_sd > 0:
        teams = df["team_id"].astype(str).to_numpy() if "team_id" in df else np.array(["__slate__"]*n)
        unique = list(dict.fromkeys(teams)); z = rng.normal(0,team_shock_sd,(num_sims,len(unique)))
        shock = np.column_stack([z[:,unique.index(t)] for t in teams])
    def count_draw(means, is_active, shared=None):
        lam = means[None,:]
        if shared is not None: lam = lam * np.exp(shared - 0.5*team_shock_sd**2)
        return rng.poisson(np.broadcast_to(lam,(num_sims,n))) * is_active
    passes = count_draw(rate("mean_passes"),active,shock)
    interceptions = count_draw(rate("mean_interceptions"),active,shock)
    shots = count_draw(rate("mean_shots_on_target"),active,shock)
    goals = count_draw(rate("mean_goals"),active,shock)
    assists = count_draw(rate("mean_assists"),active,shock)
    chances = count_draw(rate("mean_chances_created"),active,shock)
    saves = count_draw(rate("mean_saves"),active,shock)
    pen_saved = count_draw(rate("mean_penalties_saved"),active)
    pen_missed = count_draw(rate("mean_penalties_missed"),active)
    own_goals = count_draw(rate("mean_own_goals"),active)
    conceded = count_draw(rate("mean_goals_conceded"),active,shock)
    yellows = rng.binomial(1,np.clip(rate("mean_yellow_cards"),0,1)[None,:],(num_sims,n))*active
    reds = rng.binomial(1,np.clip(rate("mean_red_cards"),0,1)[None,:],(num_sims,n))*active
    cs = rng.binomial(1,cs_p[None,:],(num_sims,n))*active*(minutes >= RULES.clean_sheet_min_minutes)
    scores = (sim_start*RULES.starting_appearance + sim_sub*RULES.substitute_appearance).astype(float)
    scores += np.floor(passes/RULES.passes_per_point) + interceptions*RULES.interception_won
    scores += shots*RULES.shot_on_target + assists*RULES.assist + chances*RULES.chance_created
    defenders = {"DEF","DF","D","DEFENDER","CB","FB","WB","GK","G","GOALKEEPER"}
    keepers = {"GK","G","GOALKEEPER"}
    for i,pos in enumerate(positions):
        scores[:,i] += goals[:,i]*goal_points(pos)
        if pos in defenders:
            scores[:,i] += cs[:,i]*RULES.clean_sheet + conceded[:,i]*RULES.goal_conceded
        if pos in keepers:
            scores[:,i] += saves[:,i]*RULES.goalkeeper_save + pen_saved[:,i]*RULES.penalty_saved
        scores[:,i] += yellows[:,i]*RULES.yellow_card + reds[:,i]*RULES.red_card
        scores[:,i] += own_goals[:,i]*RULES.own_goal + pen_missed[:,i]*RULES.penalty_missed
    rows=[]
    for i,row in df.iterrows():
        draws=scores[:,i]
        rows.append({"player_name":row["player_name"],"position":row["position"],
          "Mean_Points":float(draws.mean()),"Median_Points":float(np.percentile(draws,50)),
          "Floor_5th":float(np.percentile(draws,5)),"Ceiling_95th":float(np.percentile(draws,95)),
          "Ceiling_99th":float(np.percentile(draws,99)),
          "Probability_20_plus":float(np.mean(draws>=20)),"Probability_40_plus":float(np.mean(draws>=40))})
    summary=pd.DataFrame(rows).sort_values(["Ceiling_99th","Mean_Points"],ascending=False).reset_index(drop=True)
    return summary,scores

def run_fantasyfi_monte_carlo_csv(input_path, output_path, sims=10_000, seed=42):
    summary,_=run_fantasyfi_monte_carlo(pd.read_csv(input_path),num_sims=sims,seed=seed)
    summary.to_csv(output_path,index=False)
    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run FantasyFi Monte Carlo simulations from a player projection CSV.")
    parser.add_argument("--input", required=True, help="Input player projection CSV")
    parser.add_argument("--output", default="fantasyfi_monte_carlo_summary.csv", help="Output summary CSV")
    parser.add_argument("--simulations", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result = run_fantasyfi_monte_carlo_csv(args.input, args.output, args.simulations, args.seed)
    print(result.to_string(index=False))
    print(f"Saved summary to {args.output}")
