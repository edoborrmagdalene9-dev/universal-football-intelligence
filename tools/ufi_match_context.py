"""Canonical, provenance-aware match-context normalizers for UFI."""
from __future__ import annotations
from datetime import datetime, timezone
import re

def _first(*values):
    for value in values:
        if value not in (None, ""):
            return value
    return None

def _team_name(team):
    if isinstance(team, dict):
        return _first(team.get("name"), team.get("teamName"), team.get("displayName"), team.get("shortName"), team.get("teamID"), team.get("id"))
    return team if isinstance(team, str) else None

def normalize_sgo_event(event, fetched_at=None):
    event = event if isinstance(event, dict) else {}
    teams = event.get("teams") or {}
    home = _team_name(teams.get("home") if isinstance(teams, dict) else None) or _team_name(event.get("homeTeam"))
    away = _team_name(teams.get("away") if isinstance(teams, dict) else None) or _team_name(event.get("awayTeam"))
    status = event.get("status") if isinstance(event.get("status"), dict) else {}
    scores = _first(event.get("scores"), event.get("score"), status.get("score"))
    kickoff = _first(status.get("startsAt"), event.get("startsAt"), event.get("commenceTime"))
    missing = [field for field, value in (("homeTeam",home),("awayTeam",away),("kickoff",kickoff)) if not value]
    return {
        "fixtureId": _first(event.get("eventID"), event.get("id")),
        "sport": _first(event.get("sportID"), "SOCCER"),
        "competition": _first(event.get("leagueID"), (event.get("league") or {}).get("name") if isinstance(event.get("league"),dict) else None),
        "kickoff": kickoff, "homeTeam": home, "awayTeam": away,
        "status": {"started":status.get("started"),"ended":status.get("ended"),"finalized":status.get("finalized"),"clock":_first(status.get("clock"),status.get("displayClock"))},
        "score": scores, "events": event.get("events"), "lineups": event.get("lineups"),
        "statistics": event.get("statistics"), "odds": event.get("odds"),
        "sources": {"fixture":"SportsGameOdds","odds":"SportsGameOdds" if event.get("odds") else None},
        "timestamps": {"providerUpdatedAt":_first(event.get("updatedAt"),status.get("updatedAt")),"fetchedAt":fetched_at},
        "quality": {"missingRequiredFields":missing,"hasScore":scores is not None,"hasLineups":event.get("lineups") is not None,"hasEvents":event.get("events") is not None,"hasStatistics":event.get("statistics") is not None}
    }

def normalize_odds_api_event(event, fetched_at=None):
    event=event if isinstance(event,dict) else {}
    home=_first(event.get("home_team"),event.get("homeTeam"))
    away=_first(event.get("away_team"),event.get("awayTeam"))
    missing=[field for field,value in (("homeTeam",home),("awayTeam",away),("kickoff",event.get("commence_time"))) if not value]
    return {
        "fixtureId":_first(event.get("id"),event.get("eventID")),
        "sport":event.get("sport_key"),"competition":event.get("sport_title"),
        "kickoff":event.get("commence_time"),"homeTeam":home,"awayTeam":away,
        "status":{"started":None,"ended":None,"finalized":None,"clock":None},
        "score":None,"events":None,"lineups":None,"statistics":None,
        "odds":event.get("bookmakers"),
        "sources":{"fixture":"The Odds API","odds":"The Odds API"},
        "timestamps":{"providerUpdatedAt":None,"fetchedAt":fetched_at},
        "quality":{"missingRequiredFields":missing,"hasScore":False,"hasLineups":False,"hasEvents":False,"hasStatistics":False,"oddsOnlySource":True}
    }

def normalize_provider_payload(source, payload, fetched_at=None):
    if isinstance(payload,dict):
        rows=payload.get("data")
        if isinstance(rows,dict):
            rows=rows.get("data") or rows.get("events")
        if not isinstance(rows,list):
            rows=payload.get("events")
    elif isinstance(payload,list):
        rows=payload
    else:
        rows=[]
    normalizer=normalize_sgo_event if source=="SportsGameOdds" else normalize_odds_api_event
    return [normalizer(row,fetched_at) for row in rows if isinstance(row,dict)]
