"""Additive multi-entry lineup optimizer using PuLP's MILP backend.

PuLP/CBC is linear/MILP, not a quadratic MIQP solver. The existing optional CVXPY
MIQP adapter remains available for a genuine quadratic objective with a compatible
solver installed.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import pulp

def optimize_fantasyfi_portfolio(player_df, simulation_matrix, ownership=None, budget=100.0,
    roster_size=11, lineup_count=1, min_positions=None, max_positions=None,
    max_player_exposure=1.0, max_overlap=None, ceiling_weight=0.4,
    ownership_penalty=0.15, salary_buffer=0.0):
    """Optimize multiple lineups from a [simulations, players] score matrix.

    Required player columns: player_name, position, salary. Position requirements
    are passed explicitly because official contest roster rules can differ.
    """
    missing={"player_name","position","salary"}-set(player_df.columns)
    if missing: raise ValueError("Missing player columns: "+", ".join(sorted(missing)))
    df=player_df.reset_index(drop=True).copy(); sims=np.asarray(simulation_matrix,dtype=float); n=len(df)
    if sims.ndim!=2 or sims.shape[1]!=n or sims.shape[0]<100: raise ValueError("simulation_matrix must be [>=100 simulations, number of players]")
    if not np.all(np.isfinite(sims)): raise ValueError("simulation_matrix contains non-finite values")
    salary=pd.to_numeric(df["salary"],errors="raise").to_numpy(float)
    if np.any(salary<0) or budget<=0 or salary_buffer<0 or salary_buffer>=budget: raise ValueError("Invalid salary or budget")
    if not 0<max_player_exposure<=1 or lineup_count<1 or not 1<=roster_size<=n: raise ValueError("Invalid portfolio settings")
    own=np.zeros(n) if ownership is None else np.asarray(ownership,dtype=float)
    if own.shape!=(n,) or np.any(~np.isfinite(own)) or np.any((own<0)|(own>1)): raise ValueError("ownership must align and be in [0,1]")
    means=sims.mean(axis=0); p95=np.percentile(sims,95,axis=0); value=means+ceiling_weight*(p95-means)-ownership_penalty*own*100
    positions=df["position"].astype(str).str.upper().to_numpy()
    min_positions=min_positions or {}; max_positions=max_positions or {}
    model=pulp.LpProblem("FantasyFi_MultiEntry_Portfolio",pulp.LpMaximize)
    x=[[pulp.LpVariable(f"x_{l}_{i}",cat="Binary") for i in range(n)] for l in range(lineup_count)]
    for l in range(lineup_count):
        model += pulp.lpSum(x[l])==roster_size
        model += pulp.lpSum(x[l][i]*salary[i] for i in range(n))<=budget-salary_buffer
        for pos,minimum in min_positions.items(): model += pulp.lpSum(x[l][i] for i in range(n) if positions[i]==pos.upper())>=int(minimum)
        for pos,maximum in max_positions.items(): model += pulp.lpSum(x[l][i] for i in range(n) if positions[i]==pos.upper())<=int(maximum)
    # Hard aggregate exposure bounds and lineup-overlap bounds.
    for i in range(n):
        model += pulp.lpSum(x[l][i] for l in range(lineup_count)) <= int(np.floor(max_player_exposure*lineup_count+1e-9))
    if max_overlap is not None:
        for a in range(lineup_count):
            for b in range(a+1,lineup_count):
                # Pairwise overlap linearization y_i = x_ai AND x_bi
                y=[]
                for i in range(n):
                    v=pulp.LpVariable(f"overlap_{a}_{b}_{i}",cat="Binary")
                    model += v<=x[a][i]; model += v<=x[b][i]; model>=x[a][i]+x[b][i]-1
                    y.append(v)
                model += pulp.lpSum(y)<=int(max_overlap)
    model += pulp.lpSum(x[l][i]*float(value[i]) for l in range(lineup_count) for i in range(n))
    status=model.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status]!="Optimal": raise RuntimeError(f"Portfolio optimization failed: {pulp.LpStatus[status]}")
    rows=[]
    for l in range(lineup_count):
        chosen=[i for i in range(n) if pulp.value(x[l][i])>.5]
        if len(chosen)!=roster_size: raise RuntimeError("Solver returned invalid roster size")
        row=df.iloc[chosen].copy(); row["portfolio_entry"]=l+1
        row["simulation_mean"]=means[chosen]; row["simulation_p95"]=p95[chosen]
        row["projected_ownership_pct"]=own[chosen]*100; row["lineup_salary"]=salary[chosen].sum()
        rows.append(row)
    return pd.concat(rows,ignore_index=True), {"lineup_count":lineup_count,"players_in_pool":n,
      "objective":"mean + ceiling_weight*(p95-mean) - ownership_penalty*ownership_percent",
      "solver":"PuLP/CBC MILP","note":"Ownership and salary-floor tactics are hypotheses; unused salary does not guarantee uniqueness or profit."}
