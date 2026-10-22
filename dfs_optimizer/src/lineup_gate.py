"""Fail-closed confirmed-lineup gate.

No unauthenticated endpoint is treated as a live source. A user/provider supplies
an official lineup CSV; this module verifies freshness, kickoff window and XI counts
before an export is allowed.
"""
from __future__ import annotations
from datetime import datetime, timezone

REQUIRED = {"fixture_id","kickoff_utc","confirmed_at_utc","player_id","player_name",
            "team","position","salary","status","starting"}

def _dt(value):
    value = str(value).strip().replace("Z","+00:00")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a timezone, preferably UTC/Z")
    return parsed.astimezone(timezone.utc)

def validate_confirmed_lineup(rows, now=None, max_age_minutes=90,
                              min_minutes_to_kickoff=45, max_minutes_to_kickoff=75,
                              require_eleven_per_team=True):
    rows = [dict(r) for r in rows]
    errors = []
    if not rows:
        return {"ready":False,"errors":["No confirmed lineup rows supplied"],"rows":[]}
    missing = sorted(REQUIRED - set(rows[0]))
    if missing:
        return {"ready":False,"errors":["Missing columns: "+", ".join(missing)],"rows":[]}
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    try:
        fixtures = {str(r["fixture_id"]).strip() for r in rows}
        kickoffs = {_dt(r["kickoff_utc"]) for r in rows}
        if len(fixtures) != 1: errors.append("Upload must contain exactly one fixture_id")
        if len(kickoffs) != 1: errors.append("All rows must have the same kickoff_utc")
        kickoff = next(iter(kickoffs)) if len(kickoffs)==1 else None
        confirmed_times = [_dt(r["confirmed_at_utc"]) for r in rows]
    except (ValueError, TypeError) as exc:
        return {"ready":False,"errors":[str(exc)],"rows":[]}
    if kickoff:
        minutes = (kickoff-now.astimezone(timezone.utc)).total_seconds()/60
        if minutes < min_minutes_to_kickoff or minutes > max_minutes_to_kickoff:
            errors.append(f"Kickoff is {minutes:.1f} minutes away; accepted window is {min_minutes_to_kickoff}-{max_minutes_to_kickoff} minutes")
    age = (now.astimezone(timezone.utc)-min(confirmed_times)).total_seconds()/60
    if age < -5 or age > max_age_minutes:
        errors.append(f"Lineup confirmation timestamp is not fresh (age {age:.1f} minutes; max {max_age_minutes})")
    if any(str(r["status"]).strip().lower() not in {"confirmed","official"} for r in rows):
        errors.append("Every row must have status=confirmed or status=official")
    ids = [str(r["player_id"]).strip() for r in rows]
    if any(not x for x in ids): errors.append("player_id cannot be blank")
    if len(ids) != len(set(ids)): errors.append("Duplicate player_id in lineup upload")
    starters = [r for r in rows if str(r["starting"]).strip().lower() in {"1","true","yes","starter","starting"}]
    if require_eleven_per_team:
        team_counts = {}
        for r in starters:
            team = str(r["team"]).strip()
            team_counts[team] = team_counts.get(team,0)+1
        if len(team_counts) < 2 or any(n != 11 for n in team_counts.values()):
            errors.append("Expected exactly 11 confirmed starters for each of two teams; found "+repr(team_counts))
    return {"ready":not errors,"errors":errors,"rows":rows,"starting_rows":starters,
            "fixture_id":next(iter(fixtures)) if len(fixtures)==1 else None,
            "kickoff_utc":kickoff.isoformat() if kickoff else None,
            "confirmation_age_minutes":round(age,2)}

def gate_csv(source, **kwargs):
    import csv
    return validate_confirmed_lineup(csv.DictReader(source), **kwargs)
