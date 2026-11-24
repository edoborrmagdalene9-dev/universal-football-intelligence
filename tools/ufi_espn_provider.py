"""ESPN public soccer JSON enrichment for UFI.
No API key is required. ESPN coverage is competition-specific; missing data stays missing.
"""
from __future__ import annotations
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json, math, re, threading, time

SITE="https://site.api.espn.com/apis/site/v2/sports/soccer"
CORE="https://sports.core.api.espn.com/v2/sports/soccer"
WEB="https://site.web.api.espn.com/apis/common/v3/sports/soccer"
CACHE={}
LOCK=threading.RLock()
TIMEOUT=12
LEAGUE_MAP={
 "soccer_epl":"eng.1","soccer_england_championship":"eng.2","soccer_england_league1":"eng.3",
 "soccer_england_league2":"eng.4","soccer_england_national_league":"eng.5",
 "soccer_spain_la_liga":"esp.1","soccer_spain_segunda_division":"esp.2",
 "soccer_germany_bundesliga":"ger.1","soccer_germany_bundesliga2":"ger.2",
 "soccer_italy_serie_a":"ita.1","soccer_italy_serie_b":"ita.2",
 "soccer_france_ligue_one":"fra.1","soccer_france_ligue_two":"fra.2",
 "soccer_netherlands_eredivisie":"ned.1","soccer_portugal_primeira_liga":"por.1",
 "soccer_belgium_first_div":"bel.1","soccer_turkey_super_league":"tur.1",
 "soccer_usa_mls":"usa.1","soccer_brazil_campeonato":"bra.1",
 "soccer_australia_aleague":"aus.1","soccer_japan_j_league":"jpn.1",
 "soccer_scotland_premiership":"sco.1","soccer_saudi_pro_league":"ksa.1",
 "soccer_uefa_champs_league":"uefa.champions","soccer_uefa_europa_league":"uefa.europa",
 "soccer_uefa_conference_league":"uefa.europa.conf","soccer_afc_champions_league":"afc.champions",
 "soccer_caf_champions_league":"caf.champions","soccer_conmebol_libertadores":"conmebol.libertadores",
 "soccer_conmebol_sudamericana":"conmebol.sudamericana","soccer_mexico_ligamx":"mex.1",
 "soccer_argentina_primera_division":"arg.1","soccer_china_superleague":"chn.1",
 "soccer_india_super_league":"ind.1","soccer_russia_premier_league":"rus.1",
 "soccer_sweden_allsvenskan":"swe.1","soccer_denmark_superliga":"den.1",
 "soccer_norway_eliteserien":"nor.1","soccer_south_africa_premier_league":"rsa.1",
 "soccer_africa_cup_of_nations":"caf.nations","soccer_uefa_nations_league":"uefa.nations",
 "soccer_uefa_u21":"uefa.euro_u21","soccer_fifa_world_cup":"fifa.world",
}

def _cached_json(url, ttl=300):
    now=time.time()
    with LOCK:
        hit=CACHE.get(url)
        if hit and hit[0]>now:return hit[1]
    req=Request(url,headers={"Accept":"application/json","User-Agent":"UniversalFootballIntelligence/1.0 (+https://github.com/edoborrmagdalene9-dev/universal-football-intelligence)"})
    try:
        with urlopen(req,timeout=TIMEOUT) as response:
            body=response.read()
            if len(body)>12_000_000:raise ValueError("ESPN response exceeded 12 MB safety limit")
            data=json.loads(body.decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError("ESPN HTTP "+str(exc.code)) from exc
    except (URLError,TimeoutError) as exc:
        raise RuntimeError("ESPN network request failed: "+type(exc).__name__) from exc
    with LOCK:CACHE[url]=(now+ttl,data)
    return data

def _url(base,params=None):
    return base+("?"+urlencode(params or {}) if params else "")

def _norm(value):
    return re.sub(r"[^a-z0-9]+","",str(value or "").lower())

def _list(value):
    return value if isinstance(value,list) else []

def _events(raw):
    return _list(raw.get("events")) if isinstance(raw,dict) else []

def _competitors(event):
    comps=_list(event.get("competitions"))
    if comps:
        return _list(comps[0].get("competitors"))
    return _list(event.get("competitors"))

def _normalize_event(event):
    competitors=_competitors(event)
    home=away=None
    for item in competitors:
        team=item.get("team") if isinstance(item.get("team"),dict) else item
        side=str(item.get("homeAway") or item.get("home_away") or "").lower()
        record={"name":team.get("displayName") or team.get("name") or team.get("shortDisplayName"),
                "team_id":str(team.get("id") or item.get("team_id") or ""),
                "abbreviation":team.get("abbreviation"),"score":item.get("score"),
                "winner":item.get("winner")}
        if side=="home":home=record
        elif side=="away":away=record
    status=event.get("status") if isinstance(event.get("status"),dict) else {}
    status_type=status.get("type") if isinstance(status.get("type"),dict) else {}
    comp=(event.get("competitions") or [{}])[0] if event.get("competitions") else {}
    venue=comp.get("venue") if isinstance(comp.get("venue"),dict) else {}
    return {"event_id":str(event.get("id") or event.get("event_id") or ""),
            "name":event.get("name") or event.get("shortName"),
            "start_time":event.get("date") or event.get("start_time"),
            "status":{"name":status_type.get("name") or status.get("name"),
                      "description":status_type.get("description") or status.get("detail"),
                      "category":status_type.get("state") or status.get("category"),
                      "completed":status_type.get("completed")},
            "home":home,"away":away,"venue":venue,"raw":event}

def get_scoreboard(league, date):
    day=str(date).replace("-","")[:8]
    if not re.fullmatch(r"\d{8}",day):raise ValueError("date must be YYYY-MM-DD or YYYYMMDD")
    raw=_cached_json(_url(SITE+"/"+league+"/scoreboard",{"dates":day,"limit":1000}),ttl=90)
    return [_normalize_event(x) for x in _events(raw)]

def _match_scoreboard_event(events,home,away):
    h,a=_norm(home),_norm(away)
    exact=[]
    for event in events:
        eh=_norm((event.get("home") or {}).get("name"));ea=_norm((event.get("away") or {}).get("name"))
        if eh==h and ea==a:exact.append(event)
    if len(exact)==1:return exact[0]
    if len(exact)>1:return sorted(exact,key=lambda x:x.get("start_time") or "")[0]
    # Do not reverse home/away silently. Only accept exact normalized orientation.
    return None

def get_event_summary(league,event_id):
    raw=_cached_json(_url(SITE+"/"+league+"/summary",{"event":str(event_id)}),ttl=180)
    return raw if isinstance(raw,dict) else {}

def _flatten_roster(raw):
    direct=_list(raw.get("players"))
    if direct:return direct
    result=[]
    for group in _list(raw.get("athletes")):
        if isinstance(group,dict):
            result.extend(_list(group.get("items")))
    return result

def get_roster(league,team_id):
    raw=_cached_json(_url(SITE+"/"+league+"/teams/"+str(team_id)+"/roster",{"limit":200}),ttl=21600)
    players=[]
    for p in _flatten_roster(raw):
        if not isinstance(p,dict):continue
        pos=p.get("position") if isinstance(p.get("position"),dict) else {}
        players.append({"athlete_id":str(p.get("id") or p.get("athlete_id") or ""),
            "name":p.get("fullName") or p.get("displayName") or p.get("name"),
            "position":pos.get("displayName") or pos.get("name"),
            "height":p.get("displayHeight") or p.get("height"),
            "height_in":p.get("heightInches") or p.get("height_in"),
            "weight":p.get("displayWeight") or p.get("weight"),
            "age":p.get("age"),"date_of_birth":p.get("dateOfBirth"),
            "status":p.get("status"),"injuries":p.get("injuries") or [],
            "source":"ESPN roster"})
    return {"players":players,"team":raw.get("team"),"season":raw.get("season"),
            "observed_at_ms":raw.get("timestamp") or int(time.time()*1000),"total":raw.get("count") or len(players)}

def get_team_schedule(league,team_id,season=None):
    params={"limit":1000}
    if season is not None:params["season"]=str(season)
    raw=_cached_json(_url(SITE+"/"+league+"/teams/"+str(team_id)+"/schedule",params),ttl=1800)
    return _list(raw.get("events"))

def _schedule_metrics(events, cutoff):
    past=[]
    for event in events:
        start=event.get("date") or event.get("start_time")
        try:dt=datetime.fromisoformat(str(start).replace("Z","+00:00"))
        except (TypeError,ValueError):continue
        if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
        if dt<cutoff and (cutoff-dt).total_seconds()<=14*86400:
            past.append((dt,event))
    past.sort(key=lambda x:x[0])
    rest=None
    if past:
        last=past[-1][1]
        end=last.get("end_time")
        try:
            end_dt=datetime.fromisoformat(str(end).replace("Z","+00:00")) if end else None
            if end_dt:
                if end_dt.tzinfo is None:end_dt=end_dt.replace(tzinfo=timezone.utc)
                rest=(cutoff-end_dt).total_seconds()/3600
        except (TypeError,ValueError):pass
    return {"last_14_days":[{"start_time":dt.isoformat(),"event_id":e.get("id") or e.get("event_id"),
                              "status":(e.get("status") or {}).get("type",{}).get("name") if isinstance(e.get("status"),dict) else None}
                             for dt,e in past],
            "rest_hours":rest,"games_14d":len(past),"source":"ESPN team schedule"}

def _boxscore_summary(summary):
    box=summary.get("boxscore") if isinstance(summary.get("boxscore"),dict) else {}
    teams=[]
    for team in _list(box.get("teams")):
        teams.append({"team_id":str(team.get("team",{}).get("id") or team.get("team_id") or ""),
                      "name":team.get("team",{}).get("displayName") or team.get("display_name"),
                      "formation":team.get("formation"),"statistics":team.get("statistics")})
    players=[]
    for team in _list(box.get("players")):
        team_info=team.get("team") if isinstance(team.get("team"),dict) else {}
        for group in _list(team.get("statistics")):
            for athlete in _list(group.get("athletes")):
                p=athlete.get("athlete") if isinstance(athlete.get("athlete"),dict) else {}
                players.append({"team_id":str(team_info.get("id") or ""),
                                "athlete_id":str(p.get("id") or ""),
                                "name":p.get("displayName") or p.get("fullName"),
                                "starter":athlete.get("starter"),
                                "stats":athlete.get("stats"),"source":"ESPN boxscore"})
    return {"teams":teams,"players":players,"player_stats_available":bool(players)}

def enrich_fixture(sport,league,home,away,kickoff):
    league=league or LEAGUE_MAP.get(str(sport))
    if not league:return {"status":"NEEDS_DATA","reason":"No verified ESPN league mapping for this competition.","source":"ESPN"}
    day=str(kickoff or "")[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",day):
        return {"status":"NEEDS_DATA","reason":"Fixture kickoff date is missing or invalid.","source":"ESPN"}
    events=get_scoreboard(league,day)
    event=_match_scoreboard_event(events,home,away)
    if not event:return {"status":"NEEDS_DATA","reason":"ESPN scoreboard did not return this exact home/away fixture on the requested date.","source":"ESPN","scoreboard_count":len(events)}
    event_id=event["event_id"]
    summary=get_event_summary(league,event_id)
    normalized=summary.get("event") if isinstance(summary.get("event"),dict) else {}
    comp=(normalized.get("competitions") or [{}])[0] if normalized.get("competitions") else {}
    competitors=_list(comp.get("competitors"))
    team_ids={}
    for c in competitors:
        team=c.get("team") if isinstance(c.get("team"),dict) else {}
        side=str(c.get("homeAway") or "").lower()
        if side in {"home","away"}:team_ids[side]=str(team.get("id") or c.get("id") or "")
    if not team_ids.get("home"):team_ids["home"]=(event.get("home") or {}).get("team_id")
    if not team_ids.get("away"):team_ids["away"]=(event.get("away") or {}).get("team_id")
    rosters={};schedules={}
    for side in ("home","away"):
        tid=team_ids.get(side)
        if not tid:continue
        try:rosters[side]=get_roster(league,tid)
        except Exception as exc:rosters[side]={"players":[],"error":type(exc).__name__}
        try:
            rows=get_team_schedule(league,tid)
            cutoff=datetime.fromisoformat(str(kickoff).replace("Z","+00:00"))
            if cutoff.tzinfo is None:cutoff=cutoff.replace(tzinfo=timezone.utc)
            schedules[side]=_schedule_metrics(rows,cutoff)
        except Exception as exc:schedules[side]={"error":type(exc).__name__}
    box=_boxscore_summary(summary)
    venue=summary.get("venue") or comp.get("venue") or {}
    form=summary.get("form") or []
    h2h=summary.get("head_to_head") or {}
    officials=summary.get("officials") or []
    return {"status":"FETCHED","source":"ESPN","league":league,"event_id":event_id,
        "event":event,"event_status":event.get("status"),"venue":venue,"officials":officials,
        "key_plays":summary.get("key_plays") or summary.get("keyEvents") or [],
        "team_statistics":summary.get("team_statistics") or [],
        "form":form,"head_to_head":h2h,"boxscore":box,"rosters":rosters,
        "schedules":schedules,"team_ids":team_ids,"observed_at":datetime.now(timezone.utc).isoformat(),
        "note":"ESPN does not publish a soccer injury report through this provider. Roster availability is not a confirmed match XI."}

def leagues():
    raw=_cached_json(_url(CORE+"/leagues",{"limit":1000}),ttl=86400)
    items=_list(raw.get("items"))
    return {"source":"ESPN","sport":"soccer","count":len(items),"leagues":[{"slug":x.get("slug"),"api_url":x.get("$ref") or x.get("api_url")} for x in items]}

