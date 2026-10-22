"""Joint lineup + captain/vice optimization and scenario-based portfolio diagnostics.

The solver is a MILP using PuLP/CBC. Upper-tail CVaR is computed over correlated
scenario rows; pass the same scenario matrix for all players to preserve dependence.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import pulp

def optimize_captain_vice_lineup(players, simulation_matrix, budget, roster_size,
        min_positions=None, max_positions=None, max_per_team=None,
        captain_multiplier=2.0, vice_multiplier=1.5,
        captain_salary_multiplier=1.0, vice_salary_multiplier=1.0,
        captain_eligible_positions=None, vice_eligible_positions=None,
        ownership=None, ownership_penalty=0.0, mean_weight=0.5,
        upper_tail_fraction=0.10, tail_weight=0.5):
    """Jointly select roster and unique captain/vice. Multiplier salary rules are configurable."""
    required={"player_id","position","salary","team_id"}
    if not required.issubset(players.columns): raise ValueError("players requires "+", ".join(sorted(required)))
    df=players.reset_index(drop=True).copy(); n=len(df); sims=np.asarray(simulation_matrix,dtype=float)
    if sims.ndim!=2 or sims.shape[1]!=n or sims.shape[0]<100 or not np.isfinite(sims).all(): raise ValueError("simulation_matrix must be finite [>=100 simulations, players]")
    if df.player_id.astype(str).duplicated().any(): raise ValueError("player_id must be unique")
    if not 1<=roster_size<=n or budget<=0: raise ValueError("Invalid budget/roster_size")
    if not (0<vice_multiplier<=captain_multiplier) or min(captain_salary_multiplier,vice_salary_multiplier)<=0: raise ValueError("Invalid multiplier/salary multiplier")
    if not 0<upper_tail_fraction<=1 or not 0<=mean_weight<=1 or tail_weight<0: raise ValueError("Invalid objective weights")
    pos=df.position.astype(str).str.upper().to_numpy(); team=df.team_id.astype(str).to_numpy(); salary=pd.to_numeric(df.salary,errors="raise").to_numpy(float)
    if np.any(~np.isfinite(salary)) or np.any(salary<0): raise ValueError("Invalid salary")
    own=np.zeros(n) if ownership is None else np.asarray(ownership,float)
    if own.shape!=(n,) or np.any(~np.isfinite(own)) or np.any((own<0)|(own>1)): raise ValueError("ownership must align and be in [0,1]")
    mins={str(k).upper():int(v) for k,v in (min_positions or {}).items()}; maxs={str(k).upper():int(v) for k,v in (max_positions or {}).items()}
    ce=set(str(x).upper() for x in captain_eligible_positions) if captain_eligible_positions else set(pos)
    ve=set(str(x).upper() for x in vice_eligible_positions) if vice_eligible_positions else set(pos)
    model=pulp.LpProblem("UFI_Captain_Vice_Tail_Risk",pulp.LpMaximize)
    x=[pulp.LpVariable(f"pick_{i}",cat="Binary") for i in range(n)]
    c=[pulp.LpVariable(f"captain_{i}",cat="Binary") for i in range(n)]
    v=[pulp.LpVariable(f"vice_{i}",cat="Binary") for i in range(n)]
    model += pulp.lpSum(x)==roster_size
    model += pulp.lpSum(c)==1; model += pulp.lpSum(v)==1
    for i in range(n):
        model += c[i]<=x[i]; model += v[i]<=x[i]; model += c[i]+v[i]<=1
        if pos[i] not in ce: model += c[i]==0
        if pos[i] not in ve: model += v[i]==0
    model += pulp.lpSum(x[i]*salary[i]+c[i]*salary[i]*(captain_salary_multiplier-1)+v[i]*salary[i]*(vice_salary_multiplier-1) for i in range(n))<=budget
    for p,m in mins.items(): model += pulp.lpSum(x[i] for i in range(n) if pos[i]==p)>=m
    for p,m in maxs.items(): model += pulp.lpSum(x[i] for i in range(n) if pos[i]==p)<=m
    if max_per_team is not None:
        for t in set(team): model += pulp.lpSum(x[i] for i in range(n) if team[i]==t)<=int(max_per_team)
    base=sims.mean(axis=0); tail=np.quantile(sims,1-upper_tail_fraction,axis=0)
    expected=pulp.lpSum(x[i]*base[i]+c[i]*(captain_multiplier-1)*base[i]+v[i]*(vice_multiplier-1)*base[i] for i in range(n))
    upper=pulp.lpSum(x[i]*tail[i]+c[i]*(captain_multiplier-1)*tail[i]+v[i]*(vice_multiplier-1)*tail[i] for i in range(n))
    # linear expected/ceiling proxy objective; scenario CVaR is reported exactly after selection.
    model += mean_weight*expected+tail_weight*upper-pulp.lpSum(x[i]*ownership_penalty*own[i]*100 for i in range(n))
    status=model.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status]!="Optimal": raise RuntimeError("Captain/vice MILP failed: "+pulp.LpStatus[status])
    selected=[i for i in range(n) if pulp.value(x[i])>.5]; ci=next(i for i in range(n) if pulp.value(c[i])>.5); vi=next(i for i in range(n) if pulp.value(v[i])>.5)
    mult=np.ones(n); mult[ci]=captain_multiplier; mult[vi]=vice_multiplier
    roster_sims=sims[:,selected]@mult[selected]
    return df.iloc[selected].assign(assigned_multiplier=[mult[i] for i in selected],
       role=["CAPTAIN" if i==ci else "VICE_CAPTAIN" if i==vi else "FLEX" for i in selected],
       base_mean=base[selected],scenario_p95=np.percentile(sims[:,selected],95,axis=0),
       projected_ownership_pct=own[selected]*100), {
       "solver":"PuLP/CBC MILP","captain_id":str(df.iloc[ci].player_id),"vice_captain_id":str(df.iloc[vi].player_id),
       "salary_used":float(sum(salary[i]*multiplier for i,multiplier in [(i,captain_salary_multiplier if i==ci else vice_salary_multiplier if i==vi else 1.) for i in selected])),
       "mean_lineup_points":float(roster_sims.mean()),"lineup_p95":float(np.percentile(roster_sims,95)),
       "upper_tail_mean":float(roster_sims[roster_sims>=np.quantile(roster_sims,1-upper_tail_fraction)].mean()),
       "scenario_count":int(len(roster_sims)),"objective":"mean/tail proxy; scenario distribution reported post-solve",
       "warning":"Confirm platform-specific captain salary rules and eligibility. Correlation is preserved only if the input simulations are jointly generated."}

def scenario_risk_report(simulation_matrix, lineups, alpha=0.10):
    """Evaluate portfolio outcomes from common Monte Carlo scenarios; rows must be shared scenarios."""
    sims=np.asarray(simulation_matrix,dtype=float)
    if sims.ndim!=2 or not np.isfinite(sims).all() or not 0<alpha<=1: raise ValueError("Invalid scenarios/alpha")
    matrix=[]
    for lineup in lineups:
        ids=np.asarray(list(lineup),dtype=int)
        if len(ids)==0 or np.any(ids<0) or np.any(ids>=sims.shape[1]): raise ValueError("Each lineup must contain valid column indices")
        matrix.append(sims[:,ids].sum(axis=1))
    if not matrix: return {"lineups":0,"covariance":np.empty((0,0)).tolist(),"lineup_metrics":[]}
    outcomes=np.column_stack(matrix); cutoff=np.quantile(outcomes,1-alpha,axis=0)
    metrics=[]
    for i in range(outcomes.shape[1]):
        tail=outcomes[:,i][outcomes[:,i]>=cutoff[i]]
        metrics.append({"lineup":i+1,"mean":float(outcomes[:,i].mean()),"std":float(outcomes[:,i].std(ddof=1)),
                        "p95":float(np.percentile(outcomes[:,i],95)),"upper_tail_mean":float(tail.mean()),
                        "lower_tail_5pct_mean":float(outcomes[:,i][outcomes[:,i]<=np.quantile(outcomes[:,i],.05)].mean())})
    return {"lineups":len(metrics),"scenario_count":int(len(sims)),"covariance":np.cov(outcomes,rowvar=False).reshape(len(metrics),len(metrics)).tolist(),"correlation":np.corrcoef(outcomes,rowvar=False).reshape(len(metrics),len(metrics)).tolist(),"lineup_metrics":metrics,
            "warning":"Scenario-based dependence is valid only if each row is one joint outcome draw, not independently sampled player marginals."}
