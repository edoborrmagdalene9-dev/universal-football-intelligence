#!/usr/bin/env python3
"""UFI safe operations-cycle runner.

This worker validates backend reachability, snapshots fixture discovery status,
and records Nigeria-time phase transitions. It deliberately does not approve bets:
the exact user filtering prompt and validated historical rules must be integrated
before recommendations can pass. Use a persistent UFI_OPERATIONS_DB path.
"""
from __future__ import annotations
import json, os, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from ufi_operations_brain import OperationsStore, operating_phase

WAT=ZoneInfo("Africa/Lagos")
BACKEND=os.getenv("UFI_BACKEND_URL","https://universal-football-intelligence.onrender.com").rstrip("/")
POLL_SECONDS=max(30,int(os.getenv("UFI_CYCLE_POLL_SECONDS","300")))
REQUEST_TIMEOUT=max(3,int(os.getenv("UFI_REQUEST_TIMEOUT_SECONDS","15")))

def get_json(path):
    req=urllib.request.Request(BACKEND+path,headers={"Accept":"application/json","User-Agent":"UFI-Operations-Cycle/1.0"})
    with urllib.request.urlopen(req,timeout=REQUEST_TIMEOUT) as response:
        if response.status != 200: raise RuntimeError("backend HTTP "+str(response.status))
        return json.loads(response.read().decode("utf-8"))

def rows(payload):
    value=payload
    for _ in range(6):
        if isinstance(value,list): return [x for x in value if isinstance(x,dict)]
        if not isinstance(value,dict): return []
        for key in ("data","fixtures","events","results"):
            v=value.get(key)
            if isinstance(v,list): return [x for x in v if isinstance(x,dict)]
            if isinstance(v,dict):
                nested=v.get("data")
                if isinstance(nested,list): return [x for x in nested if isinstance(x,dict)]
        break
    return []

def run_once(store, now=None):
    now=(now or datetime.now(WAT)).astimezone(WAT)
    phase=operating_phase(now)
    day=now.date().isoformat()
    store.start_phase(phase,day)
    checks={"phase":phase,"nigeria_time":now.isoformat(),"backend":BACKEND,"feeds":{},"recommendations_enabled":False}
    status="complete"
    for label,path in (
        ("today_fixtures","/api/fixtures?date="+day),
        ("tomorrow_fixtures","/api/fixtures?date="+(now.date()+timedelta(days=1)).isoformat()),
        ("live","/api/live"),
    ):
        try:
            payload=get_json(path)
            data=rows(payload)
            # Explicit empty feeds are valid observations, not evidence of failure.
            checks["feeds"][label]={"ok":True,"record_count":len(data),
                "source":payload.get("source") if isinstance(payload,dict) else None,
                "fetched_at":payload.get("fetchedAt") if isinstance(payload,dict) else None,
                "fallback_used":payload.get("fallbackUsed") if isinstance(payload,dict) else None}
        except (urllib.error.URLError,TimeoutError,ValueError,RuntimeError) as exc:
            status="partial"
            checks["feeds"][label]={"ok":False,"error_type":type(exc).__name__}
    # The policy prompt and validated historical rulebook are not wired into
    # the existing provider pipeline yet. Never mark a fixture qualified here.
    checks["note"]="Discovery health only. No fixture is qualified until the exact filtering prompt, blacklist and validated historical rulebook are integrated."
    store.finish_phase(phase,status,checks,day)
    return checks

def main():
    db_path=os.getenv("UFI_OPERATIONS_DB","ufi_operations.sqlite3")
    once="--once" in sys.argv
    store=OperationsStore(db_path)
    try:
        while True:
            result=run_once(store)
            print(json.dumps(result,sort_keys=True),flush=True)
            if once: break
            time.sleep(POLL_SECONDS)
    finally:
        store.close()

if __name__=="__main__": main()
