"""Daily UFI fixture preparation runner. Fail-closed: discovery is not a prediction or bet approval."""
from __future__ import annotations
import json, os, urllib.error, urllib.parse, urllib.request
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
try:
    from .ufi_operations_brain import OperationsStore, operating_phase, nigeria_now
except ImportError:
    from ufi_operations_brain import OperationsStore, operating_phase, nigeria_now

WAT=ZoneInfo("Africa/Lagos")
BACKEND=os.getenv("UFI_BACKEND_URL","https://universal-football-intelligence.onrender.com").rstrip("/")
DB=os.getenv("UFI_OPERATIONS_DB","ufi_operations.sqlite3")
OUT=os.getenv("UFI_NIGHTLY_REPORT","artifacts/ufi-nightly-report.json")

def _get(path,timeout=20):
    req=urllib.request.Request(BACKEND+path,headers={"Accept":"application/json","User-Agent":"UFI-Nightly-Prep/1.0"})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        if response.status!=200: raise RuntimeError("backend HTTP "+str(response.status))
        return json.loads(response.read().decode())

def _rows(value):
    for _ in range(7):
        if isinstance(value,list): return [x for x in value if isinstance(x,dict)]
        if not isinstance(value,dict): return []
        next_value=None
        for key in ("data","fixtures","events","results"):
            candidate=value.get(key)
            if isinstance(candidate,list): return [x for x in candidate if isinstance(x,dict)]
            if isinstance(candidate,dict) and isinstance(candidate.get("data"),list):
                return [x for x in candidate["data"] if isinstance(x,dict)]
            if isinstance(candidate,dict): next_value=candidate
        if next_value is None:return []
        value=next_value
    return []

def _fixture(row):
    participants=row.get("participants") or row.get("teams") or []
    home=str(row.get("home") or row.get("home_name") or "")
    away=str(row.get("away") or row.get("away_name") or "")
    if isinstance(participants,list):
        for p in participants:
            if not isinstance(p,dict):continue
            name=str(p.get("name") or p.get("short_code") or "")
            location=str(p.get("meta",{}).get("location","") if isinstance(p.get("meta"),dict) else p.get("location","")).lower()
            if not home and ("home" in location or p.get("is_home") is True):home=name
            elif not away and ("away" in location or p.get("is_home") is False):away=name
        if not home and len(participants)>0 and isinstance(participants[0],dict):home=str(participants[0].get("name") or "")
        if not away and len(participants)>1 and isinstance(participants[1],dict):away=str(participants[1].get("name") or "")
    comp=row.get("competition") or row.get("league") or row.get("tournament") or {}
    if isinstance(comp,dict):comp=comp.get("name") or comp.get("display_name") or ""
    kickoff=row.get("kickoff") or row.get("starting_at") or row.get("start_time") or row.get("date")
    ident=row.get("id") or row.get("fixture_id")
    return {"id":str(ident or ""),"home":home,"away":away,"competition":str(comp),"kickoff":kickoff,
            "source_status":row.get("status") or row.get("state"),"raw_source_id":ident}

def send_telegram(text):
    token=os.getenv("TELEGRAM_BOT_TOKEN","").strip()
    chat=os.getenv("TELEGRAM_CHAT_ID","").strip()
    if not token or not chat:return {"sent":False,"reason":"Telegram bot token or chat ID not configured on runner."}
    body=urllib.parse.urlencode({"chat_id":chat,"text":text[:3900],"disable_web_page_preview":"true"}).encode()
    req=urllib.request.Request("https://api.telegram.org/bot"+token+"/sendMessage",data=body,method="POST")
    try:
        with urllib.request.urlopen(req,timeout=15) as response:
            result=json.loads(response.read().decode())
        return {"sent":bool(result.get("ok")),"reason":None if result.get("ok") else "Telegram API rejected message."}
    except (urllib.error.URLError,urllib.error.HTTPError,TimeoutError,ValueError) as exc:
        return {"sent":False,"reason":"Telegram delivery failed ("+type(exc).__name__+")."}

def main():
    now=nigeria_now()
    phase=operating_phase(now)
    target=(now+timedelta(days=1)).date().isoformat()
    store=OperationsStore(DB)
    store.start_phase(phase,now.date().isoformat())
    report={"created_at":now.isoformat(),"timezone":"Africa/Lagos","phase":phase,"target_date":target,
            "backend":BACKEND,"fixtures":[],"status":"partial","gates":{"filtering_prompt":"not configured in automated runner",
            "validated_rules":"not confirmed","historical_validation":"not run in this preparation step",
            "live_confirmation":"required before any market can pass"}}
    try:
        payload=_get("/api/fixtures?"+urllib.parse.urlencode({"date":target}))
        rows=_rows(payload)
        source=str(payload.get("source","unknown")) if isinstance(payload,dict) else "unknown"
        fetched=payload.get("fetchedAt") or payload.get("fetched_at") if isinstance(payload,dict) else None
        for raw in rows:
            item=_fixture(raw)
            if not item["id"] or not item["home"] or not item["away"]:
                item["status"]="WAIT"
                item["reasons"]=["fixture identity incomplete"]
            else:
                # The shared user prompt and validated rulebook are required; never approve merely because fixtures were found.
                decision=store.qualify(item,"correct_score",prompt_pass=None,rule_id=None,
                    required_data_present=bool(fetched),data_age_seconds=0 if fetched else None,
                    max_data_age_seconds=3600)
                item["status"]="WAIT" if decision.status!="QUALIFIED_FOR_REVIEW" else "QUALIFIED_FOR_REVIEW"
                item["reasons"]=list(decision.reasons)
            item["source"]=source
            item["source_fetched_at"]=fetched
            item["verified_prediction"]=False
            report["fixtures"].append(item)
        report["status"]="complete" if rows else "partial"
        report["note"]="Fixture discovery only. No probabilities, correct scores, or bet recommendations were fabricated. All markets remain on WAIT until source evidence, the shared filtering prompt, validated rules, model outputs, market odds, and live confirmation are wired and pass."
        store.finish_phase(phase,report["status"],{"target_date":target,"fixture_count":len(rows),"source":source},now.date().isoformat())
    except Exception as exc:
        report["status"]="failed"
        report["error"]="Fixture preparation failed ("+type(exc).__name__+")."
        store.finish_phase(phase,"failed",{"target_date":target,"error_type":type(exc).__name__},now.date().isoformat())
    finally:
        store.close()
    Path(OUT).parent.mkdir(parents=True,exist_ok=True)
    Path(OUT).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    counts={"fixtures":len(report["fixtures"]),"wait":sum(x.get("status")=="WAIT" for x in report["fixtures"])}
    msg=("UFI "+phase+" report ("+now.strftime("%Y-%m-%d %H:%M WAT")+")\nNext-day fixtures: "+target+
         "\nFixtures discovered: "+str(counts["fixtures"])+"; WAIT: "+str(counts["wait"])+
         "\nStatus: "+report["status"]+"\nNo bets placed. Every candidate requires the existing score models, evidence/odds gates, historical validation and live confirmation.")
    report["telegram"]=send_telegram(msg)
    Path(OUT).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":report["status"],"phase":phase,"target_date":target,**counts,"report":OUT,"telegram":report["telegram"]}))
    if report["status"]=="failed":raise SystemExit(1)

if __name__=="__main__":main()
