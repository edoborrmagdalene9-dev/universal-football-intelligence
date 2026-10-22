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



def run_api_sports_prelock(now=None, api_key=None, league_ids=None, season=None, window_minutes=60):
    """API-Sports adapter: queries fixtures for configured leagues and fetches their lineups.

    Requires an authorized API-Sports/API-Football key and a plan covering requested leagues,
    fixture calls and lineup endpoint. The source_timestamp is retrieval time, not a provider
    publication timestamp; this distinction is included in each row.
    """
    from urllib.parse import urlencode
    api_key=api_key if api_key is not None else os.getenv("UFI_LINEUP_API_TOKEN")
    league_ids=league_ids if league_ids is not None else [v.strip() for v in os.getenv("UFI_API_SPORTS_LEAGUES","").split(",") if v.strip()]
    season=season if season is not None else os.getenv("UFI_API_SPORTS_SEASON")
    if not api_key or not league_ids or not season: raise ValueError("API-Sports requires UFI_LINEUP_API_TOKEN, UFI_API_SPORTS_LEAGUES and UFI_API_SPORTS_SEASON")
    host="v3.football.api-sports.io"; base="https://"+host
    now=pd.Timestamp(now or datetime.now(timezone.utc)); now=now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
    def fetch(url):
        if urlparse(url).hostname!=host: raise ValueError("Unexpected API-Sports host")
        req=Request(url,headers={"User-Agent":"UniversalFootballIntelligence/1.0","Accept":"application/json","x-apisports-key":api_key})
        with urlopen(req,timeout=15) as resp:
            if resp.status!=200: raise RuntimeError(f"API-Sports HTTP {resp.status}")
            data=json.loads(resp.read().decode("utf-8"))
        if data.get("errors"): raise RuntimeError("API-Sports provider error: "+str(data["errors"])[:300])
        return data
    results=[]
    for league in league_ids:
        query=urlencode({"league":league,"season":season,"date":now.date().isoformat(),"timezone":"UTC"})
        fixture_url=base+"/fixtures?"+query
        payload=fetch(fixture_url)
        for fx in payload.get("response",[]):
            fixture=fx.get("fixture",{}); fixture_id=fixture.get("id"); kickoff=fixture.get("date")
            if fixture_id is None or not kickoff: continue
            kt=pd.Timestamp(kickoff)
            if kt.tzinfo is None: continue
            minutes=(kt.tz_convert("UTC")-now).total_seconds()/60
            if not 0<=minutes<=window_minutes: continue
            lineup_url=base+"/fixtures/lineups?"+urlencode({"fixture":fixture_id})
            retrieved=pd.Timestamp.now(tz="UTC").isoformat()
            line_payload=fetch(lineup_url); rows=[]
            for teamrow in line_payload.get("response",[]):
                team_id=(teamrow.get("team") or {}).get("id")
                for status,key in (("starter","startXI"),("bench","substitutes")):
                    for item in teamrow.get(key,[]) or []:
                        player=item.get("player") or {}
                        if player.get("id") is None: continue
                        rows.append({"player_id":str(player["id"]),"player_name":player.get("name",""),
                          "team_id":str(team_id) if team_id is not None else "",
                          "status":status,"source_timestamp":retrieved,"source_timestamp_basis":"retrieved_at_not_provider_publication_time",
                          "source_url":lineup_url})
            if not rows:
                results.append({"fixture_id":fixture_id,"league_id":league,"minutes_to_kickoff":minutes,"status":"lineup_not_yet_available","source_url":lineup_url,"retrieved_at_utc":retrieved})
                continue
            validated,report=validate_prelock_lineups(pd.DataFrame(rows),kt.isoformat(),now_utc=now.to_pydatetime(),max_age_minutes=15,trusted_source_hosts=[host])
            results.append({"fixture_id":fixture_id,"league_id":league,"minutes_to_kickoff":minutes,
                "status":"validated" if report["all_records_valid"] and report["source_authority_verified"] else "needs_review",
                "source_url":lineup_url,"report":report,"players":validated.to_dict(orient="records")})
    return {"run_at_utc":now.isoformat(),"fixtures_checked":len(results),"results":results,"provider":"API-Sports/API-Football",
        "warning":"API-Sports lineup availability depends on competition coverage and typically appears 20-40 minutes pre-kickoff. source_timestamp is retrieval time, not provider publication time. Verify key plan, rate limits, licenses and IDs."}

def run_prelock(now=None, fixtures_url=None, lineup_base_url=None, token=None, trusted_hosts=None, window_minutes=60):
    """Fixture feed JSON: {'fixtures':[{'fixture_id','kickoff_utc','lineup_url'}]}.
    Lineup response must contain a players list with player_id, team_id, status, source_timestamp, source_url.
    Host allowlist is mandatory; a provider URL outside it is rejected.
    """
    if os.getenv("UFI_LINEUP_PROVIDER","custom").strip().lower() in {"api_sports","api-football","api_football"}:
        return run_api_sports_prelock(now=now,api_key=token,window_minutes=window_minutes)
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
