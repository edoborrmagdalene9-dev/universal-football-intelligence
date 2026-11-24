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
    direct=model.get("score_grid") or model.get("dixon_coles_score_grid")
    if isinstance(direct,list): return [x for x in direct if isinstance(x,dict) and _num(x.get("p")) is not None]
    dc=(model.get("models") or {}).get("dixon_coles") or {}
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
    side="home" if team and team==home_name else "away" if team and team==away_name else selection.get("side")
    line=_num(selection.get("line"))
    if not grid: return None,"score_grid_missing"
    if market in {"1x2","match result","full time result","h2h","moneyline"}:
        if pick in {"home","home win","1"}: return probability(grid,lambda h,a:h>a),"dixon_coles_score_grid"
        if pick in {"draw","x"}: return probability(grid,lambda h,a:h==a),"dixon_coles_score_grid"
        if pick in {"away","away win","2"}: return probability(grid,lambda h,a:h<a),"dixon_coles_score_grid"
    if market in {"double chance","double chance 12","dc12"} or pick in {"12","1x","x2","home or away"}:
        choice="12" if pick in {"12","home or away"} or market in {"double chance 12","dc12"} else pick
        if choice=="12": return probability(grid,lambda h,a:h!=a),"dixon_coles_score_grid"
        if choice=="1x": return probability(grid,lambda h,a:h>=a),"dixon_coles_score_grid"
        if choice=="x2": return probability(grid,lambda h,a:a>=h),"dixon_coles_score_grid"
    if market in {"btts","both teams to score"}:
        yes=pick in {"yes","btts yes"} or "yes" in pick
        return probability(grid,(lambda h,a:h>0 and a>0) if yes else (lambda h,a:h==0 or a==0)),"dixon_coles_score_grid"
    if market in {"over under","totals","total goals","goals over under","asian total"} and line is not None:
        over=pick.startswith("over") or "over" in market
        return probability(grid,(lambda h,a:h+a>line) if over else (lambda h,a:h+a<line)),"dixon_coles_score_grid"
    if market in {"team total","team totals","team goals","team over under","multigoals 1 3","multi score 1 3","team multigoals 1 3"} and side in {"home","away"}:
        if "1 3" in market or "multi" in market:
            return probability(grid,(lambda h,a:1<=h<=3) if side=="home" else (lambda h,a:1<=a<=3)),"dixon_coles_score_grid"
        if line is not None:
            over=pick.startswith("over") or "over" in market
            return probability(grid,(lambda h,a:(h if side=="home" else a)>line) if over else (lambda h,a:(h if side=="home" else a)<line)),"dixon_coles_score_grid"
    if market in {"under 3.5","under 4.5"}:
        ln=3.5 if "3.5" in market else 4.5
        return probability(grid,lambda h,a:h+a<ln),"dixon_coles_score_grid"
    return None,"market_not_supported_by_score_grid_adapter"

def _pirates_layers(fixture, model, selection, p, ev, evidence):
    market=_norm(selection.get("market") or selection.get("market_type"))
    layers=[]
    def add(name,status,detail,metrics=None):
        layers.append({"layer":name,"status":status,"detail":detail,"metrics":metrics or {}})
    base_ok=bool(fixture.get("fixture_id") and fixture.get("home") and fixture.get("away") and fixture.get("kickoff") and selection.get("market") and selection.get("selection"))
    add(PIRATES[0],"ASSESSED" if base_ok else "NEEDS_DATA","Fixture, kickoff and exact market identity checked." if base_ok else "Fixture/market identity or kickoff is missing.")
    politics=evidence.get("politics_referee")
    if isinstance(politics,dict) and politics.get("source") and politics.get("checked_at"):
        add(PIRATES[1],"FAIL" if politics.get("material_risk") is True else "ASSESSED","Evidence-backed institutional/referee context reviewed.",politics)
    else: add(PIRATES[1],"NEEDS_DATA","No sourced institutional, referee or unusual-risk review.")
    lnfi=evidence.get("lnfi")
    if isinstance(lnfi,dict):
        sectors=lnfi.get("sectors") or {}
        required=("DEF","MID","ATT") if market in {"1x2","match result","full time result","h2h"} else ("ATT",)
        vals=[_num(sectors.get(k)) for k in required]
        if all(v is not None for v in vals):
            diff=_num(lnfi.get("spine_differential"))
            failed=(market in {"1x2","match result","full time result","h2h"} and (diff is None or diff<15 or min(vals)<-3))
            add(PIRATES[2],"FAIL" if failed else "ASSESSED","Market-aware last-ten-start DEF/MID/ATT LNFI evaluated.",{"spine_differential":diff,"sectors":sectors,"required_sectors":required})
        else: add(PIRATES[2],"NEEDS_DATA","Player last-ten-start W-L sector totals are incomplete.")
    else: add(PIRATES[2],"NEEDS_DATA","No player last-ten-start DEF/MID/ATT evidence.")
    rates=(model or {}).get("rate_estimate") or {}
    if rates.get("ok") and _num(rates.get("lambdaHome")) is not None and _num(rates.get("lambdaAway")) is not None:
        add(PIRATES[3],"ASSESSED","Historical team attack/defence rates and match score distribution loaded.",{"lambda_home":rates.get("lambdaHome"),"lambda_away":rates.get("lambdaAway")})
    else: add(PIRATES[3],"NEEDS_DATA","No fixture-specific historical team-strength model.")
    no_vig=_num(evidence.get("no_vig_probability"))
    if p is not None and no_vig is not None:
        add(PIRATES[4],"ASSESSED","Model probability compared with a complete, margin-normalized market.",{"model_probability":p,"no_vig_market_probability":no_vig,"gap":p-no_vig})
    else: add(PIRATES[4],"NEEDS_DATA","Complete same-market outcomes are required to challenge market narratives and prices.")
    form=evidence.get("opponent_adjusted_form")
    if isinstance(form,dict) and form.get("sample_size",0)>=5 and form.get("source"):
        add(PIRATES[5],"ASSESSED","Recent form is opponent-adjusted and source-backed.",form)
    else: add(PIRATES[5],"NEEDS_DATA","Opponent-adjusted recent form and sample provenance are missing.")
    tactics=evidence.get("tactical")
    if isinstance(tactics,dict) and tactics.get("source") and tactics.get("formation_home") and tactics.get("formation_away"):
        add(PIRATES[6],"ASSESSED","Formation and tactical matchup evidence loaded.",tactics)
    else: add(PIRATES[6],"NEEDS_DATA","Both formations and sourced tactical matchup evidence are required.")
    if p is not None and _num(selection.get("odds")) and ev is not None:
        add(PIRATES[7],"ASSESSED" if ev>0 else "FAIL","Exact-market model probability, price and EV compared.",{"model_probability":p,"odds":selection.get("odds"),"ev":ev})
    else: add(PIRATES[7],"NEEDS_DATA","Exact-market model probability and fetched price are not both available.")
    scenarios=evidence.get("alternative_scenarios")
    if isinstance(scenarios,list) and scenarios and evidence.get("scenario_engine_ran") is True:
        add(PIRATES[8],"ASSESSED","Alternative score paths were generated and reviewed; they are scenarios, not probabilities.",{"scenario_count":len(scenarios)})
    else: add(PIRATES[8],"NEEDS_DATA","No executed, fixture-specific alternative-scenario review.")
    return layers

def _congestion(evidence):
    home=evidence.get("home_schedule"); away=evidence.get("away_schedule")
    if not isinstance(home,dict) or not isinstance(away,dict):
        return {"status":"NEEDS_DATA","reason":"Previous fixtures, rest hours and next-priority fixtures were not supplied."}
    def metrics(row):
        games=row.get("last_14_days")
        rest=_num(row.get("rest_hours"))
        if not isinstance(games,list) or rest is None: return None
        return {"games_14d":len(games),"rest_hours":rest,"extra_time":bool(row.get("extra_time_last_match"))}
    hm,am=metrics(home),metrics(away)
    if hm is None or am is None: return {"status":"NEEDS_DATA","reason":"Both teams need dated last-14-day fixture records and rest hours."}
    return {"status":"ASSESSED","home":hm,"away":am,"rest_differential_hours":hm["rest_hours"]-am["rest_hours"],
            "density_differential":hm["games_14d"]-am["games_14d"],
            "flags":[x for x in (["home_rest_under_48h"] if hm["rest_hours"]<48 else [])+(["away_rest_under_48h"] if am["rest_hours"]<48 else [])]}

def _physical_duel(evidence):
    home=evidence.get("home_players"); away=evidence.get("away_players")
    hf=evidence.get("formation_home"); af=evidence.get("formation_away")
    if not isinstance(home,list) or not isinstance(away,list) or not home or not away or not hf or not af:
        return {"status":"NEEDS_DATA","reason":"Both confirmed lineups, player heights and both formations are required."}
    def heights(rows):
        vals=[_num(p.get("height_cm")) for p in rows if isinstance(p,dict) and _num(p.get("height_cm")) is not None]
        return vals
    hh,ah=heights(home),heights(away)
    if len(hh)<7 or len(ah)<7:
        return {"status":"NEEDS_DATA","reason":"At least seven sourced player heights per starting XI are required."}
    home_aerial=_num(evidence.get("home_aerial_success")); away_aerial=_num(evidence.get("away_aerial_success"))
    return {"status":"ASSESSED" if home_aerial is not None and away_aerial is not None else "PARTIAL",
            "home_mean_height_cm":round(sum(hh)/len(hh),2),"away_mean_height_cm":round(sum(ah)/len(ah),2),
            "height_differential_cm":round(sum(hh)/len(hh)-sum(ah)/len(ah),2),
            "home_aerial_success":home_aerial,"away_aerial_success":away_aerial,
            "formation_home":hf,"formation_away":af,
            "jump_metrics":"NOT_AVAILABLE_UNLESS_SOURCE_SUPPLIED",
            "note":"Height is not a jump measurement; no vertical-jump value is inferred."}

def _components(evidence, fixture, model, selection):
    rows=[]
    source_fields=evidence.get("component_evidence") if isinstance(evidence.get("component_evidence"),dict) else {}
    for group,name in COMPONENTS:
        value=source_fields.get(name)
        if value is None:
            rows.append({"group":group,"component":name,"status":"NEEDS_DATA","source":None})
        else:
            source=value.get("source") if isinstance(value,dict) else None
            stamp=value.get("fetched_at") if isinstance(value,dict) else None
            status="ASSESSED" if source and stamp else "NEEDS_DATA"
            rows.append({"group":group,"component":name,"status":status,"source":source,"fetched_at":stamp})
    return {"total":len(rows),"counts":{s:sum(x["status"]==s for x in rows) for s in ("ASSESSED","NEEDS_DATA")},"components":rows}

def _selection_gates(selection, fixture, model, grid, evidence, p):
    market=_norm(selection.get("market") or selection.get("market_type"))
    pick=_norm(selection.get("selection") or selection.get("outcome"))
    rates=(model or {}).get("rate_estimate") or {}
    lh,la=_num(rates.get("lambdaHome")),_num(rates.get("lambdaAway"))
    checks=[]
    def gate(name,passed,detail,required=True):
        checks.append({"gate":name,"status":("PASS" if passed else "FAIL") if required else "NOT_APPLICABLE","detail":detail})
    hard_fail=False
    if market in {"dc12","double chance 12"} or pick in {"12","home or away"}:
        draw=probability(grid,lambda h,a:h==a)
        total=(lh+la) if lh is not None and la is not None else None
        gate("dc12_draw_probability",draw is not None and draw<=0.26,f"Dixon-Coles draw probability={draw}; maximum 0.26")
        gate("dc12_lambda_total",total is not None and total>2.20,f"Combined lambda={total}; must exceed 2.20")
        ah=_num(evidence.get("asian_handicap_main_line"))
        gate("dc12_asian_handicap",ah is not None and abs(ah)>0.25,f"Main AH line={ah}; 0 and ±0.25 are excluded")
        draw_odds=_num(evidence.get("draw_odds"))
        gate("dc12_draw_price",draw_odds is not None and draw_odds>3.00,f"Draw price={draw_odds}; must exceed 3.00")
        under_odds=_num(evidence.get("short_under_odds"))
        gate("dc12_short_under",under_odds is None or under_odds>1.75,f"Short Under 2.0/2.25 price={under_odds}; if supplied must be >1.75")
        gate("dc12_biscotto",evidence.get("biscotto") is False,"Biscotto must be explicitly checked and absent")
        dr=_num(evidence.get("league_draw_rate"))
        gate("dc12_league_draw_rate",dr is not None and dr<=0.30,f"League draw rate={dr}; maximum 0.30")
        gate("dc12_offensive_absences",evidence.get("key_offensive_absences") is False,"Key offensive absences must be explicitly checked and absent")
        gate("dc12_low_block_congestion",evidence.get("low_block_congestion") is False,"Low-block congestion must be explicitly checked and absent")
    elif "multigoals 1 3" in market or "multi score 1 3" in market or "team multigoals 1 3" in market:
        side=selection.get("side")
        team=_norm(selection.get("team") or selection.get("selection_team"))
        if side not in ("home","away"):
            side="home" if team==_norm(fixture.get("home")) else "away" if team==_norm(fixture.get("away")) else None
        lam=lh if side=="home" else la if side=="away" else None
        profile=team_goal_profile(grid,side) if side else None
        gate("multi_1_3_lambda_window",lam is not None and 1.40<=lam<=1.85,f"Team lambda={lam}; target 1.40–1.85")
        gate("multi_1_3_ruin_tail",profile is not None and profile["ruin_tail"]<0.28,f"P(0)+P(4+)={profile.get('ruin_tail') if profile else None}; must be <0.28")
        total_line=_num(evidence.get("supporting_total_line"))
        gate("multi_1_3_supporting_total",total_line is not None and 2.25<=total_line<=2.75,f"Supporting Asian total line={total_line}; must be Over 2.25–2.75")
        gate("multi_1_3_personnel",evidence.get("primary_scorer_and_creator_both_absent") is False and evidence.get("backup_gk_and_key_cb_out") is False,"Creator/scorer and backup-GK/key-CB exclusions must be explicitly cleared")
        gate("multi_1_3_biscotto",evidence.get("biscotto") is False,"Biscotto must be explicitly checked and absent")
        wind=_num((evidence.get("weather") or {}).get("wind_mph")) if isinstance(evidence.get("weather"),dict) else None
        standing=evidence.get("standing_water")
        gate("multi_1_3_weather",standing is False and wind is not None and wind<=25,"Standing water must be absent and wind <=25 mph")
    elif "under 3.5" in market or pick=="under 3.5":
        gate("under_3_5_open_game",evidence.get("open_game") is False,"Under 3.5 is rejected in an open game; explicit closed-game assessment required")
    elif "under 4.5" in market or pick=="under 4.5":
        gate("under_4_5_probability",p is not None and p>=0.78,f"Model P(Under 4.5)={p}; minimum 0.78")
        count=_num(evidence.get("under45_count_in_slip"))
        gate("under_4_5_slip_cap",count is not None and count<1,f"Existing Under 4.5 legs in slip={count}; maximum one")
    for item in checks:
        if item["status"]=="FAIL": hard_fail=True
    return checks,hard_fail

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
        p,method=market_probability(grid,selection)
        odds=_num(selection.get("odds"))
        ev=p*odds-1 if p is not None and odds is not None and odds>1 else None
        gates,failed=_selection_gates(selection,fixture,model,grid,evidence,p)
        pirates=_pirates_layers(fixture,model,selection,p,ev,evidence)
        missing_layers=[x["layer"] for x in pirates if x["status"]=="NEEDS_DATA"]
        failed_layers=[x["layer"] for x in pirates if x["status"]=="FAIL"]
        if failed or failed_layers: decision="DITCH"
        elif p is None or odds is None or missing_layers: decision="NEEDS_DATA"
        elif ev is None or ev<=0: decision="NO_VALUE"
        else: decision="REVIEW_ONLY"
        results.append({"market":selection.get("market"),"selection":selection.get("selection"),"team":selection.get("team"),
            "bookmaker":selection.get("bookmaker"),"odds":odds,"model_probability":p,"fair_odds":(1/p if p and p>0 else None),
            "expected_value_per_unit":ev,"probability_method":method,"decision":decision,
            "hard_gates":gates,"pirates_layers":pirates})
    congestion=_congestion(evidence); physical=_physical_duel(evidence)
    components=_components(evidence,fixture,model,selections[0])
    return {"ok":True,"pipeline":"ufi-full-intelligence-v1","fixture":fixture,
        "model":{"status":model.get("status"),"lambda_home":(model.get("rate_estimate") or {}).get("lambdaHome"),
                 "lambda_away":(model.get("rate_estimate") or {}).get("lambdaAway"),
                 "rho":(model.get("dixon_coles") or {}).get("rho"),"score_grid_cells":len(grid),
                 "training_matches":model.get("training_matches")},
        "congestion":congestion,"physical_duel":physical,"components_100":components,
        "selections":results,
        "summary":{"review_only":sum(x["decision"]=="REVIEW_ONLY" for x in results),
                   "ditch":sum(x["decision"]=="DITCH" for x in results),
                   "needs_data":sum(x["decision"]=="NEEDS_DATA" for x in results),
                   "no_value":sum(x["decision"]=="NO_VALUE" for x in results)},
        "pirates_layers":PIRATES,
        "decision_policy":"No selection is auto-approved. REVIEW_ONLY requires all nine Pirates layers assessed, hard gates clear, a supported score-grid probability, a fetched price and positive raw EV. Calibration and source quality remain separately required.",
        "timestamp":datetime.now(timezone.utc).isoformat()}
