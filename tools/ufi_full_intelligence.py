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

def _derive_lnfi(evidence, selection, fixture):
    """Compute W-L sector totals only from supplied last-ten-start result rows."""
    home_rows=evidence.get("home_players")
    away_rows=evidence.get("away_players")
    if not isinstance(home_rows,list) or not isinstance(away_rows,list):
        return None
    def aggregate(rows):
        totals={"DEF":0,"MID":0,"ATT":0}
        counts={"DEF":0,"MID":0,"ATT":0}
        for player in rows:
            if not isinstance(player,dict): continue
            pos=_norm(player.get("position"))
            sector=("DEF" if pos in {"gk","goalkeeper","cb","lb","rb","lwb","rwb","defender","defence","defense"}
                    else "MID" if pos in {"dm","cdm","cm","am","lm","rm","midfielder","midfield"}
                    else "ATT" if pos in {"st","cf","lw","rw","winger","forward","striker","attacker"}
                    else None)
            starts=player.get("last_ten_starts")
            if sector is None or not isinstance(starts,list) or len(starts)<10: continue
            last=starts[-10:]
            results=[_norm(x.get("result") if isinstance(x,dict) else x) for x in last]
            if any(x not in {"w","win","d","draw","l","loss"} for x in results): continue
            totals[sector]+=sum(1 if x in {"w","win"} else -1 if x in {"l","loss"} else 0 for x in results)
            counts[sector]+=1
        return totals,counts
    ht,hc=aggregate(home_rows); at,ac=aggregate(away_rows)
    if any(hc[k]==0 or ac[k]==0 for k in ("DEF","MID","ATT")): return None
    market=_norm(selection.get("market") or selection.get("market_type"))
    pick=_norm(selection.get("selection") or selection.get("outcome"))
    team=_norm(selection.get("team") or selection.get("selection_team"))
    if team==_norm(fixture.get("home")) or pick in {"home","home win","1"}: selected,opponent=ht,at
    elif team==_norm(fixture.get("away")) or pick in {"away","away win","2"}: selected,opponent=at,ht
    elif market in {"1x2","match result","full time result","h2h"}: return None
    else: selected,opponent=ht,at
    sectors={k:selected[k] for k in ("DEF","MID","ATT")}
    return {"sectors":sectors,"spine_differential":sum(selected.values())-sum(opponent.values()),
            "home_sectors":ht,"away_sectors":at,"source":"supplied player last_ten_starts","sample_starts_per_player":10}

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
    lnfi=evidence.get("lnfi") if isinstance(evidence.get("lnfi"),dict) else _derive_lnfi(evidence,selection,fixture)
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
        if not isinstance(games,list): return None
        return {"games_14d":len(games),"rest_hours":rest,"extra_time":row.get("extra_time_last_match"),
                "travel_distance_km":_num(row.get("travel_distance_km"))}
    hm,am=metrics(home),metrics(away)
    if hm is None or am is None: return {"status":"NEEDS_DATA","reason":"Both teams need dated last-14-day fixture records."}
    rest_ready=hm["rest_hours"] is not None and am["rest_hours"] is not None
    return {"status":"ASSESSED" if rest_ready else "PARTIAL","home":hm,"away":am,
            "rest_differential_hours":hm["rest_hours"]-am["rest_hours"] if rest_ready else None,
            "density_differential":hm["games_14d"]-am["games_14d"],
            "flags":[x for x in (["home_rest_under_48h"] if hm["rest_hours"] is not None and hm["rest_hours"]<48 else [])+(["away_rest_under_48h"] if am["rest_hours"] is not None and am["rest_hours"]<48 else [])],
            "reason":None if rest_ready else "Fixture counts are sourced; exact rest hours require verified match end timestamps."}

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
            requested=value.get("status") if isinstance(value,dict) else None
            status=requested if requested in {"FETCHED","ESTIMATED","ASSESSED","FAIL","PENDING","NOT_APPLICABLE","NEEDS_DATA"} else ("FETCHED" if source and stamp else "NEEDS_DATA")
            if status in {"FETCHED","ESTIMATED","ASSESSED"} and not (source and stamp):
                status="NEEDS_DATA"
            rows.append({"group":group,"component":name,"status":status,"source":source,"fetched_at":stamp})
    statuses=("FETCHED","ESTIMATED","ASSESSED","FAIL","PENDING","NOT_APPLICABLE","NEEDS_DATA")
    return {"total":len(rows),"counts":{state:sum(x["status"]==state for x in rows) for state in statuses},
            "coverage_percent":round(100*sum(x["status"]=="ASSESSED" for x in rows)/len(rows)) if rows else 0,
            "applicable_coverage_percent":round(100*sum(x["status"]=="ASSESSED" for x in rows)/max(1,len(rows)-sum(x["status"]=="NOT_APPLICABLE" for x in rows))) if rows else 0,
            "components":rows}

def _selection_gates(selection, fixture, model, grid, evidence, p):
    market=_norm(selection.get("market") or selection.get("market_type"))
    pick=_norm(selection.get("selection") or selection.get("outcome"))
    rates=(model or {}).get("rate_estimate") or {}
    lh,la=_num(rates.get("lambdaHome")),_num(rates.get("lambdaAway"))
    checks=[]
    def gate(name,passed,detail,available=True,applicable=True):
        status=("NOT_APPLICABLE" if not applicable else "NEEDS_DATA" if not available else "PASS" if passed else "FAIL")
        checks.append({"gate":name,"status":status,"detail":detail})
    is_dc12=market in {"dc12","double chance 12"} or pick in {"12","home or away"}
    if is_dc12:
        draw=probability(grid,lambda h,a:h==a)
        total=(lh+la) if lh is not None and la is not None else None
        gate("dc12_model_draw_probability",draw is not None and draw<=0.26,f"Dixon-Coles P(Draw)={draw}; maximum 0.26",draw is not None)
        draw_market=_num(evidence.get("draw_no_vig_probability"))
        gate("dc12_no_vig_draw_probability",draw_market is not None and draw_market<=0.26,f"Same-book de-vig draw probability={draw_market}; maximum 0.26",draw_market is not None)
        gate("dc12_lambda_total",total is not None and total>2.20,f"Combined lambda={total}; must exceed 2.20",total is not None)
        xg=(model or {}).get("xg_rate_estimate") or {}
        combined_xg=(_num(xg.get("lambdaHome"))+_num(xg.get("lambdaAway"))) if xg.get("ok") and _num(xg.get("lambdaHome")) is not None and _num(xg.get("lambdaAway")) is not None else None
        gate("dc12_combined_xg",combined_xg is not None and combined_xg>=2.50,f"Published xG combined lambda={combined_xg}; minimum 2.50",combined_xg is not None)
        ah=_num(evidence.get("asian_handicap_main_line"))
        gate("dc12_asian_handicap",ah is not None and abs(ah)>=0.75,f"Main AH line={ah}; must be <=-0.75 or >=+0.75",ah is not None)
        draw_odds=_num(evidence.get("draw_odds"))
        gate("dc12_draw_price",draw_odds is not None and draw_odds>3.00,f"1X2 draw price={draw_odds}; must exceed 3.00",draw_odds is not None)
        short_line=_num(evidence.get("short_under_line"))
        short_prob=_num(evidence.get("short_under_no_vig_probability"))
        short_available=short_line is not None and short_line<=2.25
        gate("dc12_short_under_signal",short_prob is not None and short_prob<=0.50,
             f"Under 2.0/2.25 no-vig probability={short_prob}; reject if short (>50%)",
             short_prob is not None if short_available else bool(evidence.get("market_scan_complete")),
             applicable=short_available or not evidence.get("market_scan_complete"))
        supporting=_num(evidence.get("supporting_total_line"))
        gate("dc12_over_2_50_support",supporting is not None and supporting>=2.50,
             f"Supporting Over line={supporting}; minimum 2.50",
             supporting is not None or bool(evidence.get("market_scan_complete")))
        dr=_num(model.get("league_draw_rate"))
        gate("dc12_league_draw_rate",dr is not None and dr<=0.30,f"League draw rate={dr}; maximum 0.30",dr is not None)
        biscotto=evidence.get("biscotto")
        gate("dc12_biscotto",biscotto is False,"Biscotto must be explicitly checked and absent",isinstance(biscotto,bool))
        incentive=evidence.get("competitive_incentive")
        gate("dc12_competitive_incentive",incentive is True,"Clear competitive incentive must be explicitly evidenced",isinstance(incentive,bool))
        absences=evidence.get("key_offensive_absences")
        gate("dc12_offensive_absences",absences is False,"Key offensive absences must be explicitly checked and absent",isinstance(absences,bool))
        low_block=evidence.get("low_block_congestion")
        gate("dc12_low_block_congestion",low_block is False,"Low-block congestion must be explicitly checked and absent",isinstance(low_block,bool))
    elif "multigoals 1 3" in market or "multi score 1 3" in market or "team multigoals 1 3" in market:
        side=selection.get("side")
        team=_norm(selection.get("team") or selection.get("selection_team"))
        if side not in ("home","away"):
            side="home" if team==_norm(fixture.get("home")) else "away" if team==_norm(fixture.get("away")) else None
        xg=(model or {}).get("xg_rate_estimate") or {}
        xg_ready=bool(xg.get("ok")) and _num(xg.get("lambdaHome")) is not None and _num(xg.get("lambdaAway")) is not None
        xg_lh=_num(xg.get("lambdaHome")) if xg_ready else None
        xg_la=_num(xg.get("lambdaAway")) if xg_ready else None
        lam=xg_lh if side=="home" else xg_la if side=="away" else None
        profile=team_goal_profile(grid,side) if side else None
        gate("multi_1_3_xg_rate",xg_ready,"Published source-backed HxG/AxG rates are required for team multigoals.",xg_ready)
        gate("multi_1_3_lambda_window",lam is not None and 1.40<=lam<=1.85,f"Published xG team lambda={lam}; target 1.40–1.85",lam is not None)
        ruin=profile.get("ruin_tail") if profile else None
        gate("multi_1_3_ruin_tail",ruin is not None and ruin<0.28,f"P(0)+P(4+)={ruin}; must be <0.28",ruin is not None)
        total_line=_num(evidence.get("supporting_total_line"))
        gate("multi_1_3_supporting_total",total_line is not None and 2.25<=total_line<=2.75,
             f"Supporting Over line={total_line}; must be Over 2.25–2.75",
             total_line is not None or bool(evidence.get("market_scan_complete")))
        personnel_a=evidence.get("primary_scorer_and_creator_both_absent")
        personnel_b=evidence.get("backup_gk_and_key_cb_out")
        personnel_ready=isinstance(personnel_a,bool) and isinstance(personnel_b,bool)
        gate("multi_1_3_personnel",personnel_a is False and personnel_b is False,"Creator/scorer and backup-GK/key-CB exclusions must be explicitly cleared",personnel_ready)
        biscotto=evidence.get("biscotto")
        gate("multi_1_3_biscotto",biscotto is False,"Biscotto must be explicitly checked and absent",isinstance(biscotto,bool))
        weather=evidence.get("weather") if isinstance(evidence.get("weather"),dict) else {}
        wind=_num(weather.get("wind_mph"))
        standing=evidence.get("standing_water")
        weather_ready=isinstance(standing,bool) and wind is not None
        gate("multi_1_3_weather",standing is False and wind<=25,"Standing water must be absent and wind <=25 mph",weather_ready)
    elif "under 3 5" in pick or market=="under 3 5" or (market in {"over under","totals","total goals","goals over under","asian total"} and pick.startswith("under") and _num(selection.get("line"))==3.5):
        open_game=evidence.get("open_game")
        gate("under_3_5_open_game",open_game is False,"Under 3.5 is rejected in an open game; explicit closed-game assessment required",isinstance(open_game,bool))
    elif "under 4 5" in pick or market=="under 4 5" or (market in {"over under","totals","total goals","goals over under","asian total"} and pick.startswith("under") and _num(selection.get("line"))==4.5):
        gate("under_4_5_probability",p is not None and p>=0.78,f"Model P(Under 4.5)={p}; minimum 0.78",p is not None)
        count=_num(evidence.get("under45_count_in_slip"))
        gate("under_4_5_slip_cap",count is not None and count<1,f"Existing Under 4.5 legs in slip={count}; maximum one",count is not None)
    hard_fail=any(x["status"]=="FAIL" for x in checks)
    return checks,hard_fail

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
