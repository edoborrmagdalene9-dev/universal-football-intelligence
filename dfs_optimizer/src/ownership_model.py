"""Empirical Bayesian DFS ownership from authorized historical contest entries."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.stats import beta

def estimate_historical_ownership(entries: pd.DataFrame, entry_col="entry_id", player_col="player_id", prior_alpha=1.0, prior_beta=1.0, credible_level=.95):
    """Input is long-form: one row per selected player per contest entry; missing players mean not selected."""
    if not {entry_col,player_col}.issubset(entries.columns): raise ValueError(f"Need columns {entry_col!r} and {player_col!r}")
    if prior_alpha<=0 or prior_beta<=0 or not 0<credible_level<1: raise ValueError("Invalid prior or credible_level")
    d=entries[[entry_col,player_col]].dropna().copy()
    d[entry_col]=d[entry_col].astype(str); d[player_col]=d[player_col].astype(str)
    if d.empty: raise ValueError("No valid contest entry/player rows")
    if d.duplicated([entry_col,player_col]).any(): raise ValueError("Duplicate player within entry; deduplicate upstream")
    n=d[entry_col].nunique(); counts=d.groupby(player_col)[entry_col].nunique()
    # If player pool is supplied separately, unseen players need an explicit zero-count row.
    lo=(1-credible_level)/2; hi=1-lo; rows=[]
    for pid,k in counts.items():
        a=prior_alpha+int(k); b=prior_beta+n-int(k)
        rows.append({"player_id":pid,"entries_observed":n,"selected_entries":int(k),"ownership_posterior_mean":a/(a+b),
          "ownership_ci_low":float(beta.ppf(lo,a,b)),"ownership_ci_high":float(beta.ppf(hi,a,b)),
          "observed_ownership":float(k/n),"posterior_alpha":a,"posterior_beta":b,
          "warning":"Contest-specific and slate-specific. Do not transfer to a different platform, contest type or slate without validation."})
    return pd.DataFrame(rows).sort_values("ownership_posterior_mean",ascending=False).reset_index(drop=True)

def add_leverage_metrics(ownership: pd.DataFrame, optimal_roster_probability: pd.Series):
    if not {"player_id","ownership_posterior_mean"}.issubset(ownership.columns): raise ValueError("Ownership table lacks required columns")
    probs=pd.DataFrame({"player_id":optimal_roster_probability.index.astype(str),"optimal_roster_probability":optimal_roster_probability.to_numpy(float)})
    if ((probs.optimal_roster_probability<0)|(probs.optimal_roster_probability>1)).any(): raise ValueError("Roster probabilities must be in [0,1]")
    out=ownership.merge(probs,on="player_id",how="left"); out["leverage_gap_pp"]=(out.optimal_roster_probability-out.ownership_posterior_mean)*100
    out["leverage_ratio"]=out.optimal_roster_probability/out.ownership_posterior_mean.clip(lower=1e-6)
    return out
