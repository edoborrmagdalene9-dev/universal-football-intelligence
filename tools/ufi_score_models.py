"""Transparent independent-Poisson and Dixon-Coles score models with chronological backtesting."""
from __future__ import annotations
import math, re
from datetime import datetime
from zoneinfo import ZoneInfo

MAX_GOALS=8
MIN_LEAGUE_MATCHES=50
MIN_TEAM_VENUE_APPEARANCES=3
SHRINKAGE_MATCHES=5.0

def norm_team(value):
    return re.sub(r"[^a-z0-9]+","",str(value or "").lower())

def _valid_rows(rows, cutoff=None):
    out=[]
    for row in rows or []:
        try:
            d=str(row.get("date") or "")[:10]
            home=str(row.get("home_team") or "").strip()
            away=str(row.get("away_team") or "").strip()
            hg=int(row.get("home_goals"));ag=int(row.get("away_goals"))
            if not d or not home or not away or hg<0 or ag<0:continue
            if cutoff and d>=str(cutoff)[:10]:continue
            out.append({"date":d,"home_team":home,"away_team":away,"home_goals":hg,"away_goals":ag,
                        "source_url":row.get("source_url"),"season":row.get("season")})
        except (TypeError,ValueError,OverflowError):continue
    return sorted(out,key=lambda x:(x["date"],x["home_team"],x["away_team"]))

def poisson_pmf(k,lam):
    if k<0 or int(k)!=k:return 0.0
    lam=max(1e-8,min(12.0,float(lam)))
    return math.exp(-lam + k*math.log(lam) - math.lgamma(k+1))

def _league_means(rows):
    n=len(rows)
    if not n:return (1.35,1.10)
    return (sum(r["home_goals"] for r in rows)/n,sum(r["away_goals"] for r in rows)/n)

def estimate_lambdas(rows,home,away,prior=SHRINKAGE_MATCHES):
    rows=_valid_rows(rows)
    if len(rows)<MIN_LEAGUE_MATCHES:
        return {"ok":False,"reason":"Fewer than 50 prior league results; do not infer fixture-specific rates.","matches":len(rows)}
    hn=norm_team(home);an=norm_team(away)
    home_rows=[r for r in rows if norm_team(r["home_team"])==hn]
    away_rows=[r for r in rows if norm_team(r["away_team"])==an]
    home_def_rows=[r for r in rows if norm_team(r["home_team"])==hn]
    away_def_rows=[r for r in rows if norm_team(r["away_team"])==an]
    if len(home_rows)<MIN_TEAM_VENUE_APPEARANCES or len(away_rows)<MIN_TEAM_VENUE_APPEARANCES:
        return {"ok":False,"reason":"Each team needs at least 3 prior appearances at its relevant venue.","matches":len(rows),
                "homeVenueAppearances":len(home_rows),"awayVenueAppearances":len(away_rows)}
    league_h,league_a=_league_means(rows)
    # Shrink venue-specific scoring and conceding rates toward league means.
    home_scored=(sum(r["home_goals"] for r in home_rows)+prior*league_h)/(len(home_rows)+prior)
    away_conceded=(sum(r["home_goals"] for r in away_def_rows)+prior*league_h)/(len(away_def_rows)+prior)
    away_scored=(sum(r["away_goals"] for r in away_rows)+prior*league_a)/(len(away_rows)+prior)
    home_conceded=(sum(r["away_goals"] for r in home_def_rows)+prior*league_a)/(len(home_def_rows)+prior)
    lh=max(0.05,min(5.0,league_h*(home_scored/max(.05,league_h))*(away_conceded/max(.05,league_h))))
    la=max(0.05,min(5.0,league_a*(away_scored/max(.05,league_a))*(home_conceded/max(.05,league_a))))
    return {"ok":True,"lambdaHome":lh,"lambdaAway":la,"leagueHomeMean":league_h,"leagueAwayMean":league_a,
            "matches":len(rows),"homeVenueAppearances":len(home_rows),"awayVenueAppearances":len(away_rows),
            "shrinkagePriorMatches":prior}

def dixon_coles_tau(home_goals,away_goals,lambda_home,lambda_away,rho):
    if home_goals==0 and away_goals==0:return max(1e-8,1-lambda_home*lambda_away*rho)
    if home_goals==0 and away_goals==1:return max(1e-8,1+lambda_home*rho)
    if home_goals==1 and away_goals==0:return max(1e-8,1+lambda_away*rho)
    if home_goals==1 and away_goals==1:return max(1e-8,1-rho)
    return 1.0

def _grid(lambda_home,lambda_away,rho=0.0,max_goals=MAX_GOALS):
    cells=[]
    for h in range(max_goals+1):
        for a in range(max_goals+1):
            p=poisson_pmf(h,lambda_home)*poisson_pmf(a,lambda_away)
            if rho:p*=dixon_coles_tau(h,a,lambda_home,lambda_away,rho)
            cells.append({"home":h,"away":a,"p":max(0.0,p)})
    total=sum(x["p"] for x in cells)
    if total<=0:return cells
    for x in cells:x["p"]/=total
    return cells

def fit_rho(rows):
    rows=_valid_rows(rows)
    if len(rows)<100:return {"rho":0.0,"fitted":False,"reason":"Fewer than 100 prior results; use rho=0 baseline."}
    lh,la=_league_means(rows)
    best=(float("-inf"),0.0)
    for step in range(-15,16):
        rho=step/100.0
        ll=0.0
        for r in rows:
            h=r["home_goals"];a=r["away_goals"]
            tau=dixon_coles_tau(h,a,lh,la,rho)
            p=poisson_pmf(h,lh)*poisson_pmf(a,la)*tau
            ll+=math.log(max(1e-15,p))
        if ll>best[0]:best=(ll,rho)
    return {"rho":best[1],"fitted":True,"training_matches":len(rows),"objective":"training log likelihood"}

def _outcome_probs(grid):
    h=sum(x["p"] for x in grid if x["home"]>x["away"])
    d=sum(x["p"] for x in grid if x["home"]==x["away"])
    a=sum(x["p"] for x in grid if x["home"]<x["away"])
    total=h+d+a
    return [h/total,d/total,a/total] if total else [1/3,1/3,1/3]

def _metrics(samples):
    if not samples:return {"n":0,"exactScoreBrier":None,"exactScoreLogLoss":None,"oneXTwoBrier":None,"oneXTwoLogLoss":None}
    return { "n":len(samples),
        "exactScoreBrier":sum(s["score_brier"] for s in samples)/len(samples),
        "exactScoreLogLoss":sum(s["score_logloss"] for s in samples)/len(samples),
        "oneXTwoBrier":sum(s["outcome_brier"] for s in samples)/len(samples),
        "oneXTwoLogLoss":sum(s["outcome_logloss"] for s in samples)/len(samples)}

def _sample_metrics(grid,actual_h,actual_a):
    if actual_h>MAX_GOALS or actual_a>MAX_GOALS:return None
    probs=_outcome_probs(grid)
    outcome=0 if actual_h>actual_a else 1 if actual_h==actual_a else 2
    score_probs={(x["home"],x["away"]):x["p"] for x in grid}
    actual=(actual_h,actual_a)
    score_brier=sum((p-(1.0 if key==actual else 0.0))**2 for key,p in score_probs.items())
    return {"score_brier":score_brier,"score_logloss":-math.log(max(1e-15,score_probs.get(actual,0.0))),
            "outcome_brier":sum((p-(1.0 if i==outcome else 0.0))**2 for i,p in enumerate(probs)),
            "outcome_logloss":-math.log(max(1e-15,probs[outcome]))}

def chronological_backtest(rows,test_fraction=0.2,max_test=100):
    rows=_valid_rows(rows)
    if len(rows)<150:return {"status":"NEEDS_DATA","reason":"At least 150 dated historical matches are required for chronological holdout validation.","total_matches":len(rows)}
    split=max(1,min(len(rows)-1,int(len(rows)*(1-max(.1,min(.4,test_fraction))))))
    test=rows[split:][-max_test:]
    metrics={"league_poisson":[],"team_poisson":[],"team_dixon_coles":[]}
    used_dates=[]
    for match in test:
        prior=[r for r in rows if r["date"]<match["date"]]
        if len(prior)<MIN_LEAGUE_MATCHES:continue
        means=_league_means(prior)
        team=estimate_lambdas(prior,match["home_team"],match["away_team"])
        if not team.get("ok"):continue
        rho=fit_rho(prior)["rho"]
        baseline=_grid(means[0],means[1],0)
        team_poisson=_grid(team["lambdaHome"],team["lambdaAway"],0)
        team_dc=_grid(team["lambdaHome"],team["lambdaAway"],rho)
        for name,grid in (("league_poisson",baseline),("team_poisson",team_poisson),("team_dixon_coles",team_dc)):
            sample=_sample_metrics(grid,match["home_goals"],match["away_goals"])
            if sample:metrics[name].append(sample)
        used_dates.append(match["date"])
    return {"status":"complete" if len(used_dates)>=20 else "INSUFFICIENT_TEST_SAMPLE",
            "method":"chronological holdout; each test match uses only results strictly before its date",
            "total_matches":len(rows),"nominal_test_matches":len(test),"evaluated_matches":len(used_dates),
            "test_start":min(used_dates) if used_dates else None,"test_end":max(used_dates) if used_dates else None,
            "metrics":{name:_metrics(values) for name,values in metrics.items()},
            "warning":"Metrics are historical diagnostics, not proof of future profitability. Exact-score Brier is the multiclass scoreline-grid Brier; model comparison uses the same evaluated matches."}

def predict_fixture(rows,home,away,cutoff_date=None):
    if not cutoff_date:
        cutoff_date=datetime.now(ZoneInfo("Africa/Lagos")).date().isoformat()
    prior=_valid_rows(rows,cutoff=cutoff_date)
    rates=estimate_lambdas(prior,home,away)
    if not rates.get("ok"):
        return {"status":"NEEDS_DATA","fixture":{"home":home,"away":away,"cutoff_date":cutoff_date},
                "training_matches":len(prior),"rate_estimate":rates,"predictions":[],
                "market_gate":"WAIT","reason":rates.get("reason","Insufficient prior data.")}
    rho=fit_rho(prior)
    independent=_grid(rates["lambdaHome"],rates["lambdaAway"],0)
    dc=_grid(rates["lambdaHome"],rates["lambdaAway"],rho["rho"])
    def top(grid):
        return [{**x,"fair_odds":(1/x["p"] if x["p"]>0 else None)} for x in sorted(grid,key=lambda x:x["p"],reverse=True)[:12]]
    return {"status":"model_output","fixture":{"home":home,"away":away,"cutoff_date":cutoff_date},
            "training_matches":len(prior),"rate_estimate":rates,"dixon_coles":rho,
            "models":{"independent_poisson":{"top_scores":top(independent),"one_x_two":_outcome_probs(independent)},
                      "dixon_coles":{"top_scores":top(dc),"one_x_two":_outcome_probs(dc)}},
            "historical_backtest":chronological_backtest(prior),
            "market_gate":"WAIT","market_gate_reason":"Exact-score odds, de-vigged market probabilities, calibrated EV and live confirmation have not been checked by this endpoint.",
            "source_urls":sorted({r.get("source_url") for r in prior if r.get("source_url")}),
            "warning":"Model outputs are not calibrated betting advice. Independent Poisson and Dixon-Coles are tested against historical baselines; no profit or win-rate guarantee."}
