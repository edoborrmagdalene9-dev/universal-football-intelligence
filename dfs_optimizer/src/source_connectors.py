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
        elif cat=="portfolio_optimization":
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
