"""Explicitly sourced data connectors for UFI. No provider is silently assumed official.

Sources:
- StatsBomb Open Data: https://github.com/statsbomb/open-data (event data for selected competitions)
- Open-Meteo: https://open-meteo.com/en/docs (weather; CC BY 4.0 attribution required)
- OpenFootball: https://github.com/openfootball (open historical results)
- Licensed/user-supplied contest exports for ownership and platform scoring.
Do not scrape sites whose terms prohibit automated use. Tracking, official lineups and DFS ownership
are not available from the public sources above and need a licensed feed or attributed upload.
"""
from __future__ import annotations
import json
import re
from urllib.request import Request, urlopen
import pandas as pd

SOURCES = {
 "statsbomb_open_data": {"url":"https://github.com/statsbomb/open-data", "kind":"selected competition event data", "license_note":"Review repository license/attribution for each use; coverage is selective; not optical tracking."},
 "openfootball": {"url":"https://github.com/openfootball", "kind":"historical fixtures/results", "license_note":"Open-source community data; preserve repository attribution and inspect data-specific license."},
 "open_meteo": {"url":"https://open-meteo.com/en/docs", "kind":"weather forecast and reanalysis", "license_note":"CC BY 4.0 attribution; free tier has rate and use limits."},
 "official_lineup_provider": {"url":"CONFIGURE_UFI_LINEUP_API_URL", "kind":"live confirmed XI", "license_note":"Must be an authorized provider; HTTPS alone is not proof of authority."},
 "contest_entry_export": {"url":"USER_OR_LICENSED_CONTEST_EXPORT", "kind":"historical ownership", "license_note":"No public generic ownership feed; use contest data you are authorized to process."},
 "platform_rulebook": {"url":"USER_SUPPLIED_PLATFORM_RULES", "kind":"scoring and multiplier rules", "license_note":"Must match the exact contest/platform."},
 "tracking_provider": {"url":"LICENSED_OPTICAL_TRACKING_PROVIDER", "kind":"3D kinematics", "license_note":"Requires timestamped x/y/z observations and documented coverage."},
 "derived_from_events": {"url":"https://github.com/statsbomb/open-data", "kind":"derived event metrics", "license_note":"Only available for matches/fields present in source; not optical tracking."},
 "derived_from_results": {"url":"https://github.com/openfootball", "kind":"derived team/match metrics", "license_note":"Score/results only unless event-level data is separately provided."},
 "not_publicly_available": {"url":"", "kind":"requires licensed feed or supplied observations", "license_note":"Never impute this as an observed fact."},
}

def _read_json(url: str, timeout: int = 20):
    if not url.startswith("https://raw.githubusercontent.com/") and not url.startswith("https://api.open-meteo.com/"):
        raise ValueError("Only documented HTTPS raw GitHub and Open-Meteo endpoints are allowed by this connector.")
    req=Request(url, headers={"User-Agent":"UniversalFootballIntelligence/1.0","Accept":"application/json"})
    with urlopen(req,timeout=timeout) as response:
        if response.status != 200: raise RuntimeError(f"HTTP {response.status} from configured public source")
        return json.loads(response.read().decode("utf-8"))

def fetch_statsbomb_competitions(timeout: int = 20) -> pd.DataFrame:
    """Download public StatsBomb competition/season index (no API key)."""
    rows=_read_json("https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json",timeout)
    d=pd.DataFrame(rows)
    if d.empty: raise RuntimeError("StatsBomb competition index was empty")
    d["source_url"]="https://github.com/statsbomb/open-data"
    d["source_license_note"]="Check repository license and attribution; selected competitions only."
    return d

def fetch_statsbomb_matches(competition_id: int, season_id: int, timeout: int = 20) -> pd.DataFrame:
    url=f"https://raw.githubusercontent.com/statsbomb/open-data/master/data/matches/{int(competition_id)}/{int(season_id)}.json"
    rows=_read_json(url,timeout)
    d=pd.json_normalize(rows)
    if not d.empty:
        d["source_url"]=url
        d["source_timestamp_utc"]=pd.Timestamp.now(tz="UTC").isoformat()
    return d

def fetch_statsbomb_events(match_id: int, timeout: int = 20) -> pd.DataFrame:
    url=f"https://raw.githubusercontent.com/statsbomb/open-data/master/data/events/{int(match_id)}.json"
    rows=_read_json(url,timeout)
    d=pd.json_normalize(rows)
    if not d.empty:
        d["source_url"]=url
        d["source_timestamp_utc"]=pd.Timestamp.now(tz="UTC").isoformat()
    return d

def statsbomb_events_to_tracking(events: pd.DataFrame) -> pd.DataFrame:
    """Build an event-location trace, not continuous player tracking; speed from it is NOT valid."""
    required={"player.id","timestamp","location"}
    if not required.issubset(events.columns): raise ValueError("Events need player.id, timestamp and location")
    rows=[]
    for _,r in events.iterrows():
        loc=r.get("location")
        if isinstance(loc,list) and len(loc)>=2 and pd.notna(r.get("player.id")):
            rows.append({"player_id":str(r["player.id"]),"timestamp":r["timestamp"],"x_m":float(loc[0])*105/120,"y_m":float(loc[1])*68/80,
                         "source_type":"event_location_not_tracking"})
    return pd.DataFrame(rows,columns=["player_id","timestamp","x_m","y_m","source_type"])

def fetch_open_meteo(latitude: float, longitude: float, kickoff_iso: str, timeout: int = 20) -> dict:
    """Fetch hourly forecast around kickoff; returns source and retrieval metadata."""
    from urllib.parse import urlencode
    t=pd.Timestamp(kickoff_iso)
    if t.tzinfo is None: raise ValueError("kickoff_iso must include a timezone")
    start=(t-pd.Timedelta(hours=2)).date().isoformat()
    end=(t+pd.Timedelta(hours=2)).date().isoformat()
    params={"latitude":float(latitude),"longitude":float(longitude),"hourly":"temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,wind_gusts_10m","start_date":start,"end_date":end,"timezone":"UTC"}
    url="https://api.open-meteo.com/v1/forecast?"+urlencode(params)
    req=Request(url,headers={"User-Agent":"UniversalFootballIntelligence/1.0","Accept":"application/json"})
    with urlopen(req,timeout=timeout) as response:
        if response.status!=200: raise RuntimeError(f"Open-Meteo HTTP {response.status}")
        payload=json.loads(response.read().decode("utf-8"))
    times=payload.get("hourly",{}).get("time",[])
    if not times: raise RuntimeError("Weather response had no hourly values")
    ix=min(range(len(times)),key=lambda i:abs((pd.Timestamp(times[i],tz="UTC")-t.tz_convert("UTC")).total_seconds()))
    out={"source":"Open-Meteo","source_url":url,"retrieved_at_utc":pd.Timestamp.now(tz="UTC").isoformat(),"valid_time_utc":pd.Timestamp(times[ix],tz="UTC").isoformat(),"license":"CC BY 4.0; attribution required"}
    for key,values in payload.get("hourly",{}).items():
        if key!="time" and ix<len(values): out[key]=values[ix]
    return out

def metric_source_catalog() -> pd.DataFrame:
    """Map all 300 registered fields to a concrete source family or honest unavailable status."""
    from .metric_registry import metric_registry
    reg=metric_registry().copy()
    rows=[]
    for _,r in reg.iterrows():
        name=str(r.metric_name).lower(); cat=str(r.category)
        if any(k in name for k in ("weather","wind_","humidity","precipitation","temperature_c")):
            key="open_meteo"; status="fetchable_when venue coordinates and kickoff are supplied"
        elif any(k in name for k in ("sprint","acceleration","high_intensity","tracking_coverage","tracking_source","deceleration","total_distance","distance_per90")):
            key="tracking_provider"; status="requires tracking feed; event locations are not tracking"
        elif cat=="pitch_environment" and any(k in name for k in ("referee","fouls","cards","red_cards","penalties")):
            key="derived_from_results"; status="partial historical coverage; per-referee metrics need match-level referee records"
        elif cat=="pitch_environment":
            key="not_publicly_available"; status="venue/environment measurement required"
        elif cat=="player_kinematics_health" and any(k in name for k in ("npxg","xa","sca","gca","progressive","interceptions","passes_completed","shots_on_target","shots_per90","goals_per90","assists_per90","ball_recoveries","aerial","press_success")):
            key="derived_from_events"; status="derive only where source event coverage supports the definition"
        elif cat=="player_kinematics_health":
            key="not_publicly_available"; status="provider/player medical or tracking data required"
        elif cat=="team_tactics_possession":
            key="derived_from_events" if any(k in name for k in ("possession","passes","xg","counterattack","press","box_entries","set_piece","formation","lineup")) else "derived_from_results"
            status="partial; validate event coverage and feature definition"
        elif cat=="ownership_game_theory":
            key="contest_entry_export"; status="requires historical contest entries or authorized ownership projections"
        elif cat=="platform_scoring_rules":
            key="platform_rulebook"; status="must be verified against the exact platform rulebook"
        elif cat=="portfolio_operations":
            key="derived_from_events"; status="derived from simulation/player data; not a raw source"
        else:
            key="not_publicly_available"; status="needs a verified source or explicit derivation"
        src=SOURCES[key]
        rows.append({"category":r.category,"metric_number":r.metric_number,"metric_name":r.metric_name,"source_family":key,"source_url":src["url"],"acquisition_status":status,"source_limitations":src["license_note"],"currently_populated":False})
    return pd.DataFrame(rows)

def audit_source_coverage(data: pd.DataFrame) -> pd.DataFrame:
    catalog=metric_source_catalog()
    cols=set(data.columns)
    catalog["present_in_input"]=catalog.metric_name.isin(cols)
    if len(data):
        catalog["non_null_count"]=[int(data[c].notna().sum()) if c in cols else 0 for c in catalog.metric_name]
    else: catalog["non_null_count"]=0
    catalog["observed_coverage_pct"]=catalog.non_null_count/max(1,len(data))*100
    return catalog


def fetch_statsbomb_lineups(match_id: int, timeout: int = 20) -> pd.DataFrame:
    """Historical lineups from StatsBomb Open Data, not a live pre-match XI feed."""
    url=f"https://raw.githubusercontent.com/statsbomb/open-data/master/data/lineups/{int(match_id)}.json"
    rows=_read_json(url,timeout)
    d=pd.json_normalize(rows)
    if not d.empty:
        d["source_url"]=url
        d["source_timestamp_utc"]=pd.Timestamp.now(tz="UTC").isoformat()
    return d

def statsbomb_matches_to_dixon_coles(matches: pd.DataFrame) -> pd.DataFrame:
    """Normalize StatsBomb historical matches to the current Dixon-Coles input schema."""
    def value(row, *keys):
        for key in keys:
            if key in row and pd.notna(row[key]): return row[key]
        return None
    rows=[]
    for _,r in matches.iterrows():
        date=value(r,"match_date","date")
        home=value(r,"home_team.home_team_name","home_team_name")
        away=value(r,"away_team.away_team_name","away_team_name")
        hg=value(r,"home_score","home_goals"); ag=value(r,"away_score","away_goals")
        if date is None or home is None or away is None or hg is None or ag is None: continue
        rows.append({"date":str(date),"home_team":str(home),"away_team":str(away),"home_goals":int(hg),"away_goals":int(ag),
                     "source_url":value(r,"source_url") or "https://github.com/statsbomb/open-data"})
    out=pd.DataFrame(rows,columns=["date","home_team","away_team","home_goals","away_goals","source_url"])
    if len(out) and out[["date","home_team","away_team","home_goals","away_goals"]].isna().any().any():
        raise ValueError("Normalized StatsBomb matches contain missing required values")
    return out

def aggregate_statsbomb_player_events(events: pd.DataFrame) -> pd.DataFrame:
    """Aggregate directly observed event fields; does not infer SCA/GCA or physical tracking."""
    required={"player.id","player.name","type.name"}
    if not required.issubset(events.columns): raise ValueError("Events need player.id, player.name and type.name")
    d=events.copy()
    d["player_id"]=d["player.id"].astype(str); d["player_name"]=d["player.name"]
    d["event_type"]=d["type.name"].astype(str).str.lower()
    d["xg"]=pd.to_numeric(d.get("shot.statsbomb_xg",pd.Series(0,index=d.index)),errors="coerce").fillna(0)
    outcome=d.get("shot.outcome.name",pd.Series("",index=d.index)).fillna("").astype(str).str.lower()
    d["shot_event"]=d.event_type.eq("shot")
    d["goal_event"]=d.shot_event & outcome.eq("goal")
    d["sot_event"]=d.shot_event & outcome.isin(["goal","saved","saved to post"])
    d["pass_event"]=d.event_type.eq("pass")
    pass_outcome=d.get("pass.outcome.name",pd.Series("",index=d.index)).fillna("").astype(str)
    d["completed_pass_event"]=d.pass_event & pass_outcome.eq("")
    d["interception_event"]=d.event_type.eq("interception")
    assist=d.get("pass.goal_assist",pd.Series(False,index=d.index)).fillna(False).astype(bool)
    d["assist_event"]=assist
    out=d.groupby(["player_id","player_name"],dropna=False).agg(
      events=("event_type","size"), shots=("shot_event","sum"), goals=("goal_event","sum"),
      shots_on_target=("sot_event","sum"), xg=("xg","sum"), completed_passes=("completed_pass_event","sum"),
      interceptions=("interception_event","sum"), assists=("assist_event","sum")).reset_index()
    out["source"]="StatsBomb Open Data event aggregation"
    out["source_url"]="https://github.com/statsbomb/open-data"
    out["limitations"]="Only selected match coverage; provider event definitions apply; not full-season per-90 rates without minutes and match coverage."
    return out


def fetch_openfootball_results(raw_csv_url: str, timeout: int = 20) -> pd.DataFrame:
    """Fetch an OpenFootball raw CSV and normalize common score-result columns."""
    from io import StringIO
    from urllib.parse import urlparse
    from urllib.request import Request, urlopen
    parsed=urlparse(raw_csv_url)
    if parsed.scheme!="https" or parsed.hostname!="raw.githubusercontent.com" or "/openfootball/" not in parsed.path:
        raise ValueError("URL must be a raw.githubusercontent.com/openfootball/... CSV URL")
    req=Request(raw_csv_url,headers={"User-Agent":"UniversalFootballIntelligence/1.0","Accept":"text/csv,text/plain"})
    with urlopen(req,timeout=timeout) as response:
        if response.status!=200: raise RuntimeError(f"OpenFootball HTTP {response.status}")
        raw=response.read(10_000_000).decode("utf-8-sig","replace")
    source=pd.read_csv(StringIO(raw))
    norm={re.sub(r"[^a-z0-9]","",str(c).lower()):c for c in source.columns}
    def col(*aliases):
        for alias in aliases:
            if alias in norm: return norm[alias]
        return None
    date_col=col("date","matchdate","datetime")
    home_col=col("hometeam","home","team1","teamhome")
    away_col=col("awayteam","away","team2","teamaway")
    hg_col=col("homegoals","fthg","homescored")
    ag_col=col("awaygoals","ftag","awayscored")
    score_col=col("ft","fulltime","fulltimescore","score","result")
    if not all([date_col,home_col,away_col]) or (not (hg_col and ag_col) and not score_col):
        raise ValueError("CSV columns could not be mapped; expected date, home/away teams and score or home/away goals")
    rows=[]
    for _,row in source.iterrows():
        try:
            if hg_col and ag_col: hg,ag=int(row[hg_col]),int(row[ag_col])
            else:
                match=re.match(r"^\s*(\d+)\s*[-:]\s*(\d+)\s*$",str(row[score_col]))
                if not match: continue
                hg,ag=int(match.group(1)),int(match.group(2))
            if pd.isna(row[home_col]) or pd.isna(row[away_col]): continue
            rows.append({"date":str(row[date_col]) if date_col else "", "home_team":str(row[home_col]),"away_team":str(row[away_col]),"home_goals":hg,"away_goals":ag,"source_url":raw_csv_url})
        except (TypeError,ValueError):
            continue
    out=pd.DataFrame(rows,columns=["date","home_team","away_team","home_goals","away_goals","source_url"])
    if out.empty: raise ValueError("No rows could be normalized from this OpenFootball CSV; inspect the source column schema.")
    return out


def fetch_api_sports_1x2_odds(fixture_id: int, api_key: str | None = None, timeout: int = 20) -> pd.DataFrame:
    """Fetch currently available API-Sports 1X2 odds and remove overround per bookmaker.

    This is a current snapshot, not a historical closing-odds archive. Poll/store snapshots
    over time if your license and plan permit; never label current odds as closing odds.
    """
    import os
    from urllib.parse import urlencode
    api_key=api_key or os.getenv("UFI_LINEUP_API_TOKEN")
    if not api_key: raise ValueError("Set UFI_LINEUP_API_TOKEN in the runtime environment; do not hardcode keys.")
    url="https://v3.football.api-sports.io/odds?"+urlencode({"fixture":int(fixture_id)})
    req=Request(url,headers={"User-Agent":"UniversalFootballIntelligence/1.0","Accept":"application/json","x-apisports-key":api_key})
    with urlopen(req,timeout=timeout) as response:
        if response.status!=200: raise RuntimeError(f"API-Sports odds HTTP {response.status}")
        payload=json.loads(response.read().decode("utf-8"))
    if payload.get("errors"): raise RuntimeError("API-Sports odds error: "+str(payload["errors"])[:300])
    rows=[]; retrieved=pd.Timestamp.now(tz="UTC").isoformat()
    for item in payload.get("response",[]):
        fixture=(item.get("fixture") or {}).get("id",fixture_id)
        for book in item.get("bookmakers",[]) or []:
            for bet in book.get("bets",[]) or []:
                title=str(bet.get("name","")).strip().lower()
                if title not in {"match winner","1x2","fulltime result","full time result"}: continue
                values={str(v.get("value","")).strip().lower():v.get("odd") for v in bet.get("values",[]) or []}
                def find(*keys):
                    for key in keys:
                        if key in values:
                            try:
                                odd=float(values[key])
                                if odd>1: return odd
                            except (TypeError,ValueError): pass
                    return None
                home=find("home","1"); draw=find("draw","x"); away=find("away","2")
                if not all(v is not None for v in (home,draw,away)): continue
                raw=np.array([1/home,1/draw,1/away],float); norm=raw/raw.sum()
                rows.append({"fixture_id":fixture,"bookmaker":book.get("name","unknown"),"market":bet.get("name"),
                  "home_decimal_odds":home,"draw_decimal_odds":draw,"away_decimal_odds":away,
                  "raw_home_implied_probability":raw[0],"raw_draw_implied_probability":raw[1],"raw_away_implied_probability":raw[2],
                  "no_vig_home_probability":norm[0],"no_vig_draw_probability":norm[1],"no_vig_away_probability":norm[2],
                  "retrieved_at_utc":retrieved,"source_url":url,"source_note":"Current odds snapshot; not closing odds. API plan/coverage may omit bookmakers."})
    return pd.DataFrame(rows)
