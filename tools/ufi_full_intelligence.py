"""Full UFI evidence orchestrator: score-grid markets, Pirates, congestion and physical duel.
Missing or unverified evidence is never converted into a pass. This module is a
screening/audit layer; it does not place bets or claim calibrated profitability.
"""
from __future__ import annotations
from datetime import datetime, timezone
import math
import re
from typing import Any

PIRATES = (
    "Teague's Code", "Sumbhajee Politics", "Sparrow LNFI", "Davy Jones' Heart",
    "Liar's Dice", "Locker Illusion", "Mao Kun Map", "Jack's Compass", "Up Is Down",
)

COMPONENT_GROUPS = {
    "fixture_integrity": ("fixture_identity","team_orientation","competition_identity","kickoff_timestamp","timezone","fixture_status","venue_identity","source_provider","source_url","source_freshness"),
    "market_integrity": ("market_identity","selection_identity","settlement_rules","decimal_price","price_timestamp","bookmaker_identity","market_line","outcome_completeness","market_suspension","price_freshness"),
    "model_quality": ("historical_sample","home_lambda","away_lambda","dixon_coles_rho","score_grid","probability_bounds","fair_odds","base_rate","chronological_validation","calibration_uncertainty"),
    "squad_evidence": ("official_lineup","lineup_timestamp","goalkeeper_identity","centre_back_pairing","creator_availability","primary_scorer_availability","bench_depth","player_minutes","injury_source","suspension_source"),
    "player_intelligence": ("player_identity","player_position","last_ten_starts","defence_sector_lnfi","midfield_sector_lnfi","attack_sector_lnfi","preferred_foot_source","weak_foot_source","height_cm","aerial_duel_rate"),
    "tactical_evidence": ("home_formation","away_formation","pressing_style","build_up_style","transition_threat","low_block_matchup","wide_overload","central_progression","set_piece_profile","tactical_sample"),
    "congestion": ("home_last_fixture","away_last_fixture","home_rest_hours","away_rest_hours","home_games_14d","away_games_14d","travel_distance","upcoming_priority","extra_time_load","rotation_risk"),
    "environment": ("stadium_coordinates","weather_source","kickoff_weather","wind_speed","precipitation","pitch_condition","surface_type","temperature","humidity","weather_freshness"),
    "physical_duel": ("home_lineup_heights","away_lineup_heights","home_aerial_success","away_aerial_success","keeper_reach","centre_back_aerials","striker_aerials","formation_collision","duel_sample_size","duel_source"),
    "validation_and_risk": ("biscotto_check","league_draw_rate","referee_assignment","referee_card_rate","political_risk_source","contradiction_audit","alternative_scenarios","market_correlation","out_of_sample_sample","decision_trace"),
}
COMPONENTS = tuple((group, name) for group, names in COMPONENT_GROUPS.items() for name in names)

def _num(value):
    try:
        x=float(value)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):
        return None

def _norm(value):
    return re.sub(r"[^a-z0-9]+"," ",str(value or "").lower()).strip()

def _grid(model):
    if not isinstance(model,dict): return []
    direct=model.get("score_grid") or model.get("dixon_coles_rho_minus_0_10_score_grid")
    if isinstance(direct,list): return [x for x in direct if isinstance(x,dict) and _num(x.get("p")) is not None]
    models=model.get("models") or {}
    # User's configured rho=-0.10 surface is the primary selection grid.
    # The empirically fitted rho grid remains available for side-by-side sensitivity review.
    dc=(models.get("xg_dixon_coles_rho_minus_0_10") or models.get("dixon_coles_rho_minus_0_10") or models.get("dixon_coles") or {})
    return [x for x in (dc.get("score_grid") or []) if isinstance(x,dict) and _num(x.get("p")) is not None]

def probability(grid, predicate):
    if not grid: return None
    total=sum(max(0.0,_num(x.get("p")) or 0.0) for x in grid)
    if total<=0: return None
    return sum(max(0.0,_num(x.get("p")) or 0.0) for x in grid if predicate(int(x.get("home",0)),int(x.get("away",0))))/total

def team_goal_profile(grid, side):
    if side not in ("home","away") or not grid: return None
    get=(lambda h,a:h) if side=="home" else (lambda h,a:a)
    p0=probability(grid,lambda h,a:get(h,a)==0)
    p1_3=probability(grid,lambda h,a:1<=get(h,a)<=3)
    p4=probability(grid,lambda h,a:get(h,a)>=4)
    return {"p_zero":p0,"p_one_to_three":p1_3,"p_four_plus":p4,
            "ruin_tail":(p0 or 0)+(p4 or 0)}

def market_probability(grid, selection):
    market=_norm(selection.get("market") or selection.get("market_type"))
    pick=_norm(selection.get("selection") or selection.get("outcome"))
    team=_norm(selection.get("team") or selection.get("selection_team"))
    home_name=_norm(selection.get("home_team")); away_name=_norm(selection.get("away_team"))
    side=selection.get("side") or ("home" if team and team==home_name else "away" if team and team==away_name else None)
    line=_num(selection.get("line"))
    if not grid:return None,"score_grid_missing"
    method="dixon_coles_rho_minus_0_10_score_grid"
    if market in {"1x2","match result","full time result","h2h","moneyline"}:
        if pick in {"home","home win","1"}:return probability(grid,lambda h,a:h>a),method
        if pick in {"draw","x"}:return probability(grid,lambda h,a:h==a),method
        if pick in {"away","away win","2"}:return probability(grid,lambda h,a:h<a),method
    if market in {"double chance","double chance 12","dc12"} or pick in {"12","1x","x2","home or away"}:
        choice="12" if pick in {"12","home or away"} or market in {"double chance 12","dc12"} else pick
        if choice=="12":return probability(grid,lambda h,a:h!=a),method
        if choice=="1x":return probability(grid,lambda h,a:h>=a),method
        if choice=="x2":return probability(grid,lambda h,a:a>=h),method
    if market in {"btts","both teams to score"}:
        yes=pick in {"yes","btts yes"} or "yes" in pick
        return probability(grid,(lambda h,a:h>0 and a>0) if yes else (lambda h,a:h==0 or a==0)),method
    if market in {"over under","totals","total goals","goals over under","asian total"} and line is not None:
        if abs(line-round(line))<1e-9 or abs(line*2-round(line*2))>1e-9:return None,"asian_total_settlement_not_supported"
        over=pick.startswith("over")
        return probability(grid,(lambda h,a:h+a>line) if over else (lambda h,a:h+a<line)),method
    if market in {"team total","team totals","team goals","team over under","multigoals 1 3","multi score 1 3","team multigoals 1 3"} and side in {"home","away"}:
        if "1 3" in market or "multi" in market:
            return probability(grid,(lambda h,a:1<=h<=3) if side=="home" else (lambda h,a:1<=a<=3)),method
        if line is not None:
            if abs(line-round(line))<1e-9 or abs(line*2-round(line*2))>1e-9:return None,"asian_team_total_settlement_not_supported"
            over=pick.startswith("over")
            return probability(grid,(lambda h,a:(h if side=="home" else a)>line) if over else (lambda h,a:(h if side=="home" else a)<line)),method
    if market in {"asian handicap","handicap","spreads"} and side in {"home","away"} and line is not None:
        if abs(line-round(line))<1e-9 or abs(line*2-round(line*2))>1e-9:return None,"asian_handicap_settlement_not_supported"
        return probability(grid,(lambda h,a:h+line>a) if side=="home" else (lambda h,a:a+line>h)),method
    if market in {"correct score","exact score"}:
        match=re.search(r"(\d+)\s*[-:]\s*(\d+)",str(selection.get("selection") or ""))
        if match:
            target=(int(match.group(1)),int(match.group(2)))
            return probability(grid,lambda h,a:(h,a)==target),method
    if market in {"under 3.5","under 4.5"}:
        ln=3.5 if "3.5" in market else 4.5
        return probability(grid,lambda h,a:h+a<ln),method
    return None,"market_not_supported_by_score_grid_adapter"

def _failure_scenarios(selection, grid, fixture, p):
    if not grid or p is None:
        return {"status":"NEEDS_DATA","reason":"A market-mapped Dixon-Coles score grid is required for failure scenarios."}
    total=sum(max(0.0,_num(x.get("p")) or 0.0) for x in grid) or 1.0
    failures=[]
    for cell in grid:
        hit=_selection_hit(selection,int(cell.get("home",0)),int(cell.get("away",0)),fixture)
        if hit is False:
            failures.append({"score":f'{int(cell.get("home",0))}-{int(cell.get("away",0))}',
                             "home_goals":int(cell.get("home",0)),"away_goals":int(cell.get("away",0)),
                             "probability":max(0.0,_num(cell.get("p")) or 0.0)/total})
    failures.sort(key=lambda x:x["probability"],reverse=True)
    market=_norm(selection.get("market") or selection.get("market_type"))
    side=selection.get("side")
    if side not in {"home","away"}:
        team=_norm(selection.get("team") or selection.get("selection_team"))
        side="home" if team==_norm(fixture.get("home")) else "away" if team==_norm(fixture.get("away")) else None
    goal_profile=team_goal_profile(grid,side) if side and ("multigoals 1 3" in market or "multi score 1 3" in market) else None
    return {"status":"ASSESSED","method":"market-mapped Dixon-Coles score-grid failure distribution",
            "success_probability":p,"failure_probability":max(0.0,1.0-p),
            "top_failure_scorelines":failures[:5],
            "greatest_risk":failures[0] if failures else None,
            "team_multigoals_breakdown":goal_profile,
            "note":"Probabilities are model outputs, not calibrated guarantees. Unconventional scenario-engine scores are kept separate and are not assigned probabilities."}

def audit_full_fixture(payload):
    if not isinstance(payload,dict): raise ValueError("JSON object required.")
    fixture=payload.get("fixture") if isinstance(payload.get("fixture"),dict) else {}
    model=payload.get("model") if isinstance(payload.get("model"),dict) else {}
    evidence=payload.get("evidence") if isinstance(payload.get("evidence"),dict) else {}
    selections=payload.get("selections") if isinstance(payload.get("selections"),list) else []
    grid=_grid(model)
    if not fixture.get("home") or not fixture.get("away"): raise ValueError("fixture.home and fixture.away are required.")
    if not selections: raise ValueError("At least one exact market selection is required.")
    if len(selections)>500: raise ValueError("Maximum 500 market selections per fixture.")
    results=[]
    for selection in selections:
        if not isinstance(selection,dict): continue
        selection_evidence=dict(evidence)
        if isinstance(selection.get("evidence"),dict):
            selection_evidence.update(selection["evidence"])
        p,method=market_probability(grid,selection)
        backtest=(model or {}).get("historical_backtest") or {}
        if selection_evidence.get("validation_matches") is None and _num(backtest.get("evaluated_matches")) is not None:
            selection_evidence["validation_matches"]=_num(backtest.get("evaluated_matches"))
        uncertainty,uncertainty_details=_model_probability_uncertainty(model,selection,p)
        if selection_evidence.get("uncertainty") is None and uncertainty is not None:
            selection_evidence["uncertainty"]=uncertainty
            selection_evidence["uncertainty_method"]=uncertainty_details.get("method")
        if selection_evidence.get("source_updated_at") is None:
            selection_evidence["source_updated_at"]=selection_evidence.get("price_timestamp")
        up_is_down=_failure_scenarios(selection,grid,fixture,p)
        if up_is_down.get("status")=="ASSESSED":
            selection_evidence["alternative_scenarios"]=up_is_down["top_failure_scorelines"]
            selection_evidence["scenario_engine_ran"]=True
        if p is not None and (model.get("models") or {}).get("xg_dixon_coles_rho_minus_0_10"):
            method="xg_dixon_coles_rho_minus_0_10_score_grid"
        odds=_num(selection.get("odds"))
        ev=p*odds-1 if p is not None and odds is not None and odds>1 else None
        gates,failed=_selection_gates(selection,fixture,model,grid,selection_evidence,p)
        pirates=_pirates_layers(fixture,model,selection,p,ev,selection_evidence)
        edge5400=_bookie_edge_5400(p,odds,selection_evidence,fixture)
        missing_layers=[x["layer"] for x in pirates if x["status"]=="NEEDS_DATA"]
        failed_layers=[x["layer"] for x in pirates if x["status"]=="FAIL"]
        gate_missing=any(x["status"]=="NEEDS_DATA" for x in gates)
        if failed or failed_layers or edge5400["status"]=="FAIL": decision="DITCH"
        elif p is None or odds is None or missing_layers or gate_missing or edge5400["status"]!="PASS": decision="NEEDS_DATA"
        elif ev is None or ev<=0: decision="NO_VALUE"
        else: decision="REVIEW_ONLY"
        results.append({"market":selection.get("market"),"selection":selection.get("selection"),"team":selection.get("team"),
            "bookmaker":selection.get("bookmaker"),"odds":odds,"model_probability":p,"fair_odds":(1/p if p and p>0 else None),
            "expected_value_per_unit":ev,"probability_method":method,"decision":decision,
            "hard_gates":gates,"bookie_edge_5400":edge5400,"up_is_down_scenarios":up_is_down,"pirates_layers":pirates})
    congestion=_congestion(evidence); physical=_physical_duel(evidence)
    components=_components(evidence,fixture,model,selections[0])
    correlations=_market_correlations(selections,grid,fixture)
    return {"ok":True,"pipeline":"ufi-full-intelligence-v1","fixture":fixture,
        "model":{"status":model.get("status"),"lambda_home":(model.get("rate_estimate") or {}).get("lambdaHome"),
                 "lambda_away":(model.get("rate_estimate") or {}).get("lambdaAway"),
                 "fitted_rho":(model.get("dixon_coles") or {}).get("rho"),
                 "market_rho":-0.10 if ((model.get("models") or {}).get("xg_dixon_coles_rho_minus_0_10") or (model.get("models") or {}).get("dixon_coles_rho_minus_0_10")) else (model.get("dixon_coles") or {}).get("rho"),
                 "xg_rate_estimate":model.get("xg_rate_estimate"),
                 "model_grid_source":"published_xg" if (model.get("models") or {}).get("xg_dixon_coles_rho_minus_0_10") else "historical_goals_only",
                 "score_grid_cells":len(grid),
                 "training_matches":model.get("training_matches")},
        "congestion":congestion,"physical_duel":physical,"components_100":components,"market_correlations":correlations,
        "selections":results,
        "summary":{"review_only":sum(x["decision"]=="REVIEW_ONLY" for x in results),
                   "ditch":sum(x["decision"]=="DITCH" for x in results),
                   "needs_data":sum(x["decision"]=="NEEDS_DATA" for x in results),
                   "no_value":sum(x["decision"]=="NO_VALUE" for x in results)},
        "pirates_layers":PIRATES,
        "decision_policy":"No selection is auto-approved. REVIEW_ONLY requires all nine Pirates layers assessed, hard gates clear, a supported score-grid probability, a fetched price and positive raw EV. Calibration and source quality remain separately required.",
        "timestamp":datetime.now(timezone.utc).isoformat()}
