"""Scheduled pre-lock runner. It only calls an explicitly configured authorized provider."""
from __future__ import annotations
import json, os
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import pandas as pd
from .prelock_pipeline import validate_prelock_lineups

def _fetch_json(url, token=None, timeout=15):
    if not url.startswith("https://"): raise ValueError("Only HTTPS endpoints are accepted")
    headers={"User-Agent":"UniversalFootballIntelligence/1.0","Accept":"application/json"}
    if token: headers["Authorization"]="Bearer "+token
    req=Request(url,headers=headers)
    with urlopen(req,timeout=timeout) as resp:
        if resp.status!=200: raise RuntimeError(f"Provider returned HTTP {resp.status}")
        return json.loads(resp.read().decode("utf-8"))

def run_prelock(now=None, fixtures_url=None, lineup_base_url=None, token=None, trusted_hosts=None, window_minutes=60):
    """Fixture feed JSON: {'fixtures':[{'fixture_id','kickoff_utc','lineup_url'}]}.
    Lineup response must contain a players list with player_id, team_id, status, source_timestamp, source_url.
    Host allowlist is mandatory; a provider URL outside it is rejected.
    """
    fixtures_url=fixtures_url or os.getenv("UFI_FIXTURE_FEED_URL")
    lineup_base_url=lineup_base_url or os.getenv("UFI_LINEUP_API_BASE_URL","")
    token=token if token is not None else os.getenv("UFI_LINEUP_API_TOKEN")
    trusted_hosts=trusted_hosts if trusted_hosts is not None else [h.strip().lower() for h in os.getenv("UFI_LINEUP_TRUSTED_HOSTS","").split(",") if h.strip()]
    if not fixtures_url: raise ValueError("Set UFI_FIXTURE_FEED_URL to your authorized fixture feed")
    if not trusted_hosts: raise ValueError("Set UFI_LINEUP_TRUSTED_HOSTS to provider hostnames you have independently verified")
    now=pd.Timestamp(now or datetime.now(timezone.utc)); now=now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
    payload=_fetch_json(fixtures_url,token); fixtures=payload.get("fixtures",[]) if isinstance(payload,dict) else payload
    results=[]
    for fx in fixtures:
        kickoff=pd.Timestamp(fx["kickoff_utc"])
        if kickoff.tzinfo is None: continue
        minutes=(kickoff.tz_convert("UTC")-now).total_seconds()/60
        if minutes<0 or minutes>window_minutes: continue
        url=str(fx.get("lineup_url") or (lineup_base_url.rstrip("/")+"/"+str(fx["fixture_id"])+"/lineups" if lineup_base_url else ""))
        host=urlparse(url).hostname or ""
        if not url.startswith("https://") or host.lower() not in trusted_hosts:
            results.append({"fixture_id":fx.get("fixture_id"),"minutes_to_kickoff":minutes,"status":"rejected_untrusted_lineup_host","source_url":url})
            continue
        data=_fetch_json(url,token)
        players=data.get("players",data.get("lineups",[])) if isinstance(data,dict) else data
        provider_updated_at=data.get("updated_at") if isinstance(data,dict) else None
        rows=[]
        for row in players:
            row=dict(row); row.setdefault("source_url",url)
            if "source_timestamp" not in row and provider_updated_at: row["source_timestamp"]=provider_updated_at
            rows.append(row)
        d=pd.DataFrame(rows)
        if d.empty:
            results.append({"fixture_id":fx.get("fixture_id"),"minutes_to_kickoff":minutes,"status":"empty_lineup_response","source_url":url})
            continue
        validated,report=validate_prelock_lineups(d,kickoff.isoformat(),now_utc=now.to_pydatetime(),max_age_minutes=15,trusted_source_hosts=trusted_hosts)
        results.append({"fixture_id":fx.get("fixture_id"),"minutes_to_kickoff":minutes,"status":"validated" if report["all_records_valid"] and report["source_authority_verified"] else "needs_review","source_url":url,"report":report,"players":validated.to_dict(orient="records")})
    return {"run_at_utc":now.isoformat(),"fixtures_checked":len(results),"results":results,"provider_configured":True,"warning":"This runner is only as authoritative as the allowlisted licensed feed; verify provider terms, identity mapping, and timestamp semantics."}

def main():
    result=run_prelock()
    os.makedirs("artifacts",exist_ok=True)
    with open("artifacts/prelock_audit.json","w",encoding="utf-8") as f: json.dump(result,f,indent=2,default=str)
    print(json.dumps({k:v for k,v in result.items() if k!="results"},indent=2))
if __name__=="__main__": main()
