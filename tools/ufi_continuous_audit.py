#!/usr/bin/env python3
"""Evidence-gated, concurrent, fixture-isolated market audit engine."""
from __future__ import annotations
import asyncio, json, math, os, re, sqlite3, threading, uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

DEFAULT_THRESHOLD=0.55
MAX_FIXTURES=500
MAX_SELECTIONS=2000
_DB_LOCK=threading.Lock()

def _norm(v: Any)->str:
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",str(v or "").lower())).strip()

def _num(v: Any)->float|None:
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError): return None

def _poisson(lam:float,limit:int=12)->list[float]:
    if not 0<=lam<=12: raise ValueError("xG lambda must be between 0 and 12")
    p=[math.exp(-lam)]
    for k in range(1,limit+1): p.append(p[-1]*lam/k)
    z=sum(p)
    return [x/z for x in p]

def score_matrix(home_lambda:float,away_lambda:float,limit:int=12)->list[list[float]]:
    hp,ap=_poisson(home_lambda,limit),_poisson(away_lambda,limit)
    return [[h*a for a in ap] for h in hp]

def _market_probability(s:dict[str,Any],f:dict[str,Any])->tuple[float|None,str]:
    supplied=_num(s.get("model_probability"))
    if supplied is not None:
        return (supplied,"supplied_market_specific_model_probability") if 0<=supplied<=1 else (None,"model_probability outside [0,1]")
    e=f.get("evidence") if isinstance(f.get("evidence"),dict) else {}
    lh,la=_num(e.get("home_xg")),_num(e.get("away_xg"))
    if lh is None or la is None: return None,"needs validated home_xg and away_xg or model_probability"
    try: matrix=score_matrix(lh,la)
    except ValueError as exc: return None,str(exc)
    market,pick=_norm(s.get("market") or s.get("market_type")),_norm(s.get("selection"))
    target=_norm(s.get("team") or s.get("selection_team"))
    home,away=_norm(f.get("home")),_norm(f.get("away"))
    total=0.0
    supported=False
    for h,row in enumerate(matrix):
        for a,p in enumerate(row):
            g=h+a; hit=False
            if "over 1 5" in market or "over 1 5" in pick: supported=True; hit=g>=2
            elif "under 1 5" in market or "under 1 5" in pick: supported=True; hit=g<=1
            elif "over 2 5" in market or "over 2 5" in pick: supported=True; hit=g>=3
            elif "under 2 5" in market or "under 2 5" in pick: supported=True; hit=g<=2
            elif "over 3 5" in market or "over 3 5" in pick: supported=True; hit=g>=4
            elif "under 3 5" in market or "under 3 5" in pick: supported=True; hit=g<=3
            elif "btts" in market or "both teams to score" in market: supported=True; hit=h>0 and a>0
            elif "double chance" in market or pick in {"12","1x","x2","home or away"}:
                supported=True
                hit=(h!=a if pick in {"12","home or away"} else h>=a if pick=="1x" else a>=h)
            elif market in {"1x2","match result","full time result"}:
                supported=True
                hit=(h>a if pick in {"home","home win","1"} else h==a if pick in {"draw","x"} else a>h if pick in {"away","away win","2"} else False)
            elif "multigoals 1 3" in market or "multi score 1 3" in market:
                supported=True
                hit=(1<=h-a<=3 if target==home else 1<=a-h<=3 if target==away else False)
            if hit: total+=p
    return (min(1.0,max(0.0,total)),"independent_poisson_from_supplied_xg") if supported else (None,"market_not_supported_by_probability_adapter")

def _mine_faults(f:dict[str,Any])->list[dict[str,Any]]:
    e=f.get("evidence") if isinstance(f.get("evidence"),dict) else {}
    faults=[]
    def add(code,severity,detail,field):
        faults.append({"fault_id":f["fixture_id"]+":"+code+":"+str(len(faults)+1),"code":code,
                       "severity":severity,"detail":detail,"source_field":field,"status":"candidate"})
    hxg,axg=_num(e.get("home_xg")),_num(e.get("away_xg"))
    if hxg is not None and axg is not None and hxg+axg<=2.20:
        add("low_total_goal_environment","high","Combined supplied xG is <=2.20; goal totals need scrutiny.","home_xg+away_xg")
    age=_num(e.get("data_age_minutes"))
    if age is not None and age>15: add("stale_match_data","critical",f"Evidence is {age:g} minutes old.","data_age_minutes")
    if e.get("lineups_confirmed") is not True:
        add("lineups_unconfirmed" if e.get("lineups_confirmed") is False else "lineup_data_missing",
            "high" if e.get("lineups_confirmed") is False else "medium",
            "Lineups are unconfirmed." if e.get("lineups_confirmed") is False else "Lineup status is unknown; no absence is inferred.","lineups_confirmed")
    if e.get("key_creator_available") is False:
        add("key_creator_unavailable","high","A key creator is explicitly reported unavailable.","key_creator_available")
    tr=_num(e.get("high_transition_rate"))
    if tr is not None and tr>=0.7: add("high_transition_environment","medium","Supplied transition indicator is >=0.70; verify its definition.","high_transition_rate")
    if e.get("passive_build_up") is True:
        add("passive_build_up","medium","Passive build-up reported; counters and set pieces can still create threat.","passive_build_up")
    share=_num(e.get("attacker_goal_share"))
    if share is not None and share<0.55:
        add("low_attacking_zone_goal_share","medium","Less than 55% of supplied goal contribution is attributed to advanced attackers.","attacker_goal_share")
    assertions=e.get("state_assertions") if isinstance(e.get("state_assertions"),list) else []
    for assertion in assertions:
        if isinstance(assertion,str) and _norm(assertion) in {"fixture not started","fixture final score recorded as live","explicit no goal events","explicit goal event recorded"}:
            add("state_assertion:"+_norm(assertion).replace(" ","_"),"critical","Explicit structured match-state assertion; checked by mutex engine.","state_assertions")
    rows=e.get("goal_contributors")
    if isinstance(rows,list) and rows:
        goals=sum(max(0,_num(x.get("goals")) or 0) for x in rows if isinstance(x,dict))
        advanced=sum(max(0,_num(x.get("goals")) or 0) for x in rows if isinstance(x,dict) and _norm(x.get("position")) in {"st","cf","lw","rw","am","attacking midfielder","forward","striker"})
        if goals>0: add("goal_threat_origin_profile","info",f"Advanced roles account for {advanced/goals:.1%} of supplied contributor goals; sample window/source must be checked.","goal_contributors")
    return faults

def _mutex(faults:list[dict[str,Any]],e:dict[str,Any])->list[dict[str,Any]]:
    # Passive build-up and transition threat are not mutually exclusive.
    for x in faults:
        if x["code"] in {"passive_build_up","high_transition_environment"}:
            x["status"]="retained_with_tension"
            x["correlation_note"]="Can coexist through counters, direct play or set pieces; not a hard contradiction."
    assertions={_norm(x) for x in e.get("state_assertions",[]) if isinstance(x,str)}
    pairs=[]
    hard=[("fixture_not_started","fixture_final_score_recorded_as_live"),
          ("explicit_no_goal_events","explicit_goal_event_recorded")]
    for a,b in hard:
        if a in assertions and b in assertions:
            for fault in faults:
                if fault["code"] in {"state_assertion:"+a.replace(" ","_"),"state_assertion:"+b.replace(" ","_")}:
                    fault["status"]="quarantined"
            pairs.append({"assertions":[a,b],"action":"quarantine_conflicting_state","reason":"Explicit structured match-state assertions conflict."})
    return pairs

def _persist(result:dict[str,Any])->str:
    url=os.getenv("REDIS_URL","").strip()
    if url:
        try:
            import redis
            client=redis.Redis.from_url(url,decode_responses=True,socket_timeout=1.5)
            client.setex("ufi:audit:pocket:"+result["audit_id"],2592000,json.dumps(result,separators=(",",":")))
            return "redis"
        except Exception: pass
    path=Path(os.getenv("UFI_AUDIT_DB","/tmp/ufi_audit_pockets.sqlite3"))
    path.parent.mkdir(parents=True,exist_ok=True)
    with _DB_LOCK,sqlite3.connect(path,timeout=3) as db:
        db.execute("CREATE TABLE IF NOT EXISTS audit_pockets(audit_id TEXT PRIMARY KEY,created_at TEXT NOT NULL,payload TEXT NOT NULL)")
        db.execute("INSERT OR REPLACE INTO audit_pockets VALUES(?,?,?)",(result["audit_id"],result["created_at"],json.dumps(result,separators=(",",":"))))
        db.commit()
    return "sqlite_ephemeral_fallback"

def audit_fixture(f:dict[str,Any],threshold:float)->dict[str,Any]:
    faults=_mine_faults(f); mutex=_mutex(faults,f.get("evidence") or {})
    selections=[]
    for s in f["_selections"]:
        p,method=_market_probability(s,f); odds=_num(s.get("odds"))
        implied=1/odds if odds is not None and odds>1 else None
        decision="NEEDS_DATA" if p is None or mutex else "DITCH" if p<threshold else "KEEP"
        selections.append({"selection":s.get("selection"),"market":s.get("market") or s.get("market_type"),
            "odds":odds,"model_probability":p,"ditch_probability":1-p if p is not None else None,
            "break_even_probability":implied,"probability_edge_vs_raw_odds":p-implied if p is not None and implied is not None else None,
            "probability_method":method,"decision":decision,
            "reason":"Hard contradiction in explicit match-state evidence; fixture quarantined." if mutex else "Below configured survival threshold." if decision=="DITCH" else
                    "Probability unavailable; not cleared." if decision=="NEEDS_DATA" else
                    "Meets threshold but remains subject to evidence and correlation gates."})
    return {"fixture_id":f["fixture_id"],"fixture":f["name"],"home":f["home"],"away":f["away"],
            "fault_pocket":faults,"mutex":mutex,"selections":selections,
            "status":"NEEDS_DATA" if any(x["decision"]=="NEEDS_DATA" for x in selections) else
                     "DITCH" if any(x["decision"]=="DITCH" for x in selections) else "KEEP"}

async def _parallel(fixtures:list[dict[str,Any]],threshold:float)->list[dict[str,Any]]:
    sem=asyncio.Semaphore(32)
    async def one(f):
        async with sem: return await asyncio.to_thread(audit_fixture,f,threshold)
    return await asyncio.gather(*(one(f) for f in fixtures))

def audit_slip_payload(payload:dict[str,Any])->dict[str,Any]:
    if not isinstance(payload,dict): raise ValueError("JSON object required.")
    raw=payload.get("fixtures")
    if not isinstance(raw,list) or not raw: raise ValueError("fixtures must be a non-empty array.")
    if len(raw)>MAX_FIXTURES: raise ValueError(f"Maximum {MAX_FIXTURES} fixtures per audit.")
    threshold=_num(payload.get("survival_threshold"))
    threshold=DEFAULT_THRESHOLD if threshold is None else threshold
    if not 0<=threshold<=1: raise ValueError("survival_threshold must be between 0 and 1.")
    fixtures=[]; count=0
    for i,item in enumerate(raw):
        if not isinstance(item,dict): raise ValueError(f"fixtures[{i}] must be an object.")
        home,away=str(item.get("home") or "").strip(),str(item.get("away") or "").strip()
        if not home or not away: raise ValueError(f"fixtures[{i}] requires home and away.")
        selections=item.get("selections")
        if not isinstance(selections,list) or not selections: raise ValueError(f"fixtures[{i}] requires selections.")
        count+=len(selections)
        if count>MAX_SELECTIONS: raise ValueError(f"Maximum {MAX_SELECTIONS} selections per audit.")
        fid=str(item.get("fixture_id") or uuid.uuid5(uuid.NAMESPACE_URL,_norm(home)+"|"+_norm(away)).hex)
        fixtures.append({"fixture_id":fid,"name":str(item.get("name") or home+" vs "+away),
                         "home":home,"away":away,"evidence":item.get("evidence") if isinstance(item.get("evidence"),dict) else {},
                         "_selections":selections})
    results=asyncio.run(_parallel(fixtures,threshold))
    response={"ok":True,"audit_id":uuid.uuid4().hex,"created_at":datetime.now(timezone.utc).isoformat(),
        "pipeline":"ufi-continuous-market-audit-v1","fixture_count":len(results),"selection_count":count,
        "survival_threshold":threshold,"pockets":results,
        "summary":{"keep":sum(x["decision"]=="KEEP" for f in results for x in f["selections"]),
                   "ditch":sum(x["decision"]=="DITCH" for f in results for x in f["selections"]),
                   "needs_data":sum(x["decision"]=="NEEDS_DATA" for f in results for x in f["selections"]),
                   "fixtures_with_faults":sum(bool(f["fault_pocket"]) for f in results)},
        "limitations":["Only explicit market_probability or supplied xG creates probabilities.",
          "xG uses an independent-Poisson baseline, not a player/tactical calibrated model.",
          "Unsupported or missing markets remain NEEDS_DATA, never cleared.",
          "Raw odds break-even is not de-vigged without a complete same-market book.",
          "No bet placement or automatic stake escalation."]}
    response["storage_backend"]=_persist(response)
    return response
