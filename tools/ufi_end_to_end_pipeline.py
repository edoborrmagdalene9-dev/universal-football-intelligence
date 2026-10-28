"""Additive orchestration for source fixture ingestion -> historical score model.

This module deliberately does not infer bookmaker prices, player participation, or
tactical observations. Those stages stay WAIT/unknown until their own evidence
is connected and validated.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Callable


def _first(query: dict[str, list[str]], *names: str) -> str:
    for name in names:
        values = query.get(name) or []
        if values and str(values[0]).strip():
            return str(values[0]).strip()
    return ""


def _fixture_from_response(payload: Any, fixture_id: str) -> dict[str, Any]:
    """Unwrap known UFI/Sportmonks envelopes without inventing missing fields."""
    value = payload
    for _ in range(6):
        if not isinstance(value, dict):
            break
        if value.get("id") is not None and str(value.get("id")) == fixture_id:
            return value
        nested = value.get("data")
        if isinstance(nested, dict):
            value = nested
            continue
        if isinstance(nested, list):
            match = next((row for row in nested if isinstance(row, dict)
                          and str(row.get("id", "")) == fixture_id), None)
            if match:
                return match
        break
    raise ValueError("The provider response did not contain the requested fixture record.")


def _teams(fixture: dict[str, Any]) -> tuple[str, str]:
    home = away = ""
    participants = fixture.get("participants")
    if isinstance(participants, list):
        for participant in participants:
            if not isinstance(participant, dict):
                continue
            meta = participant.get("meta") or {}
            side = str(meta.get("location") or "").lower()
            name = str(participant.get("name") or "").strip()
            if side == "home":
                home = name
            elif side == "away":
                away = name
    if not home or not away:
        label = str(fixture.get("name") or "")
        for separator in (" vs ", " v ", " - "):
            if separator in label:
                left, right = [part.strip() for part in label.split(separator, 1)]
                if left and right:
                    home = home or left
                    away = away or right
                    break
    if not home or not away:
        raise ValueError("The provider fixture is missing identifiable home/away team names.")
    return home, away


def _context_summary(fixture: dict[str, Any]) -> dict[str, Any]:
    events = fixture.get("events")
    lineups = fixture.get("lineups")
    statistics = fixture.get("statistics")
    referees = fixture.get("referees")
    scores = fixture.get("scores")
    venue = fixture.get("venue") if isinstance(fixture.get("venue"), dict) else {}
    def count(value: Any) -> int | None:
        return len(value) if isinstance(value, list) else None
    return {
        "events": {"available": isinstance(events, list) and bool(events), "count": count(events)},
        "lineups": {"available": isinstance(lineups, list) and bool(lineups), "count": count(lineups)},
        "statistics": {"available": isinstance(statistics, list) and bool(statistics), "count": count(statistics)},
        "referees": {"available": isinstance(referees, list) and bool(referees), "count": count(referees)},
        "scores": {"available": isinstance(scores, list) and bool(scores), "count": count(scores)},
        "venue": {
            "available": bool(venue),
            "latitude_available": venue.get("latitude") is not None,
            "longitude_available": venue.get("longitude") is not None,
        },
        "missing_data_policy": "Absent provider fields remain unknown; no values are fabricated.",
    }


def generate_fixture_pipeline(
    query: dict[str, list[str]],
    fixture_loader: Callable[[str, dict[str, list[str]]], tuple[Any, bool]],
    score_predictor: Callable[[dict[str, list[str]]], dict[str, Any]],
) -> dict[str, Any]:
    """Fetch one real provider fixture, run the historical baseline, and report gates."""
    fixture_id = _first(query, "fixture_id", "id")
    if not fixture_id.isdigit():
        raise ValueError("fixture_id must be a numeric provider fixture ID.")
    league = _first(query, "league", "league_code").upper()
    if not league:
        raise ValueError("league is required: choose the matching Football-Data.co.uk league code.")
    seasons = _first(query, "seasons") or "3"
    try:
        season_count = int(seasons)
    except ValueError as exc:
        raise ValueError("seasons must be an integer from 1 to 8.") from exc
    if not 1 <= season_count <= 8:
        raise ValueError("seasons must be an integer from 1 to 8.")

    fixture_response, cache_hit = fixture_loader("/api/fixture", {"id": [fixture_id]})
    fixture = _fixture_from_response(fixture_response, fixture_id)
    home, away = _teams(fixture)
    kickoff = str(fixture.get("starting_at") or fixture.get("kickoff") or "")
    requested_cutoff = _first(query, "cutoff_date", "date")
    cutoff = requested_cutoff or (kickoff[:10] if len(kickoff) >= 10 else "")
    if not cutoff:
        raise ValueError("The fixture has no kickoff date; supply cutoff_date=YYYY-MM-DD.")
    try:
        cutoff = date.fromisoformat(cutoff).isoformat()
    except ValueError as exc:
        raise ValueError("cutoff_date must use YYYY-MM-DD.") from exc

    model = score_predictor({
        "home": [home], "away": [away], "league": [league],
        "seasons": [str(season_count)], "cutoff_date": [cutoff],
    })
    model_status = str(model.get("status") or "NEEDS_DATA")
    context = _context_summary(fixture)
    return {
        "ok": True,
        "pipeline": "fixture-ingestion-to-historical-score-model",
        "pipeline_status": "model_ready_market_wait" if model_status == "model_output" else "needs_data",
        "fixture_source": {
            "provider": fixture_response.get("source", "unknown") if isinstance(fixture_response, dict) else "unknown",
            "fixture_id": fixture_id,
            "cache_hit": cache_hit,
            "kickoff": kickoff or None,
            "home": home,
            "away": away,
            "competition_id": fixture.get("league_id"),
            "fetched_at": fixture_response.get("fetchedAt") if isinstance(fixture_response, dict) else None,
        },
        "match_context": context,
        "historical_model": model,
        "stages": {
            "fixture_ingestion": "PASS",
            "historical_poisson_dixon_coles": model_status,
            "player_and_tactical_feature_join": "WAIT",
            "exact_score_market_validation": "WAIT",
            "final_market_decision": "WAIT",
        },
        "market_gate": "WAIT",
        "gate_reasons": [
            "Fixture-to-historical-score-model data flow is connected.",
            "The supplied historical league code must match the fixture competition; the provider league ID is not silently mapped.",
            "Exact-score odds, de-vigged market probabilities, calibrated EV and live-state validation are not established by this pipeline.",
            "Browser-side tactical, chaos and narrative engines remain separate until their outputs have evidence-backed adapters.",
        ],
        "warning": "A generated score distribution is experimental and is not a guaranteed result or betting signal.",
    }
