"""HTTP adapter for UFI's historical exact-score baseline models.

This endpoint is additive: it exposes the existing Poisson/Dixon-Coles model and
keeps the market gate at WAIT unless separately validated odds are supplied.
"""
from __future__ import annotations

import threading
import time
from datetime import date
from typing import Any

try:
    from .ufi_historical_results import LEAGUE_CODES, load_football_data_results
    from .ufi_score_models import predict_fixture
except ImportError:
    from ufi_historical_results import LEAGUE_CODES, load_football_data_results
    from ufi_score_models import predict_fixture

_CACHE: dict[tuple[str, int], tuple[float, dict[str, Any]]] = {}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL_SECONDS = 900


def _value(query: dict[str, list[str]], *names: str) -> str:
    for name in names:
        values = query.get(name) or []
        if values and str(values[0]).strip():
            return str(values[0]).strip()
    return ""


def _historical_data(league: str, seasons: int) -> dict[str, Any]:
    key = (league, seasons)
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached and now - cached[0] < _CACHE_TTL_SECONDS:
            result = dict(cached[1])
            result["cache_hit"] = True
            return result

    result = load_football_data_results(league, seasons=seasons, timeout=8.0)
    with _CACHE_LOCK:
        _CACHE[key] = (time.monotonic(), result)
    result = dict(result)
    result["cache_hit"] = False
    return result


def generate_score_prediction(query: dict[str, list[str]]) -> dict[str, Any]:
    """Create a source-backed exact-score distribution or a clear NEEDS_DATA result."""
    home = _value(query, "home", "home_team", "homeTeam")
    away = _value(query, "away", "away_team", "awayTeam")
    if not home or not away:
        raise ValueError("home and away must be supplied as non-empty team names.")

    league = _value(query, "league", "league_code").upper() or "E0"
    if league not in LEAGUE_CODES:
        raise ValueError("league must be a supported football-data league code, for example E0.")

    try:
        seasons = int(_value(query, "seasons") or "5")
    except ValueError as exc:
        raise ValueError("seasons must be an integer from 1 to 8.") from exc
    if not 1 <= seasons <= 8:
        raise ValueError("seasons must be an integer from 1 to 8.")

    cutoff = _value(query, "cutoff_date", "date")
    if cutoff:
        try:
            cutoff = date.fromisoformat(cutoff).isoformat()
        except ValueError as exc:
            raise ValueError("cutoff_date must be YYYY-MM-DD.") from exc
    else:
        cutoff = date.today().isoformat()

    historical = _historical_data(league, seasons)
    rows = historical.get("data") or []
    include_backtest = _value(query, "include_backtest").lower() in {"1", "true", "yes"}
    model = predict_fixture(rows, home, away, cutoff_date=cutoff, include_backtest=include_backtest)
    status = model.get("status", "NEEDS_DATA")
    return {
        # ok means the request was processed; status separately says whether the
        # historical sample was sufficient to generate fixture-specific output.
        "ok": True,
        "status": status,
        "source": historical.get("source"),
        "fetched_at": historical.get("fetched_at"),
        "cache_hit": historical.get("cache_hit", False),
        "league_code": league,
        "requested_seasons": seasons,
        "source_record_count": historical.get("record_count", len(rows)),
        "historical_record_count": historical.get("record_count", len(rows)),
        "historical_seasons_loaded": historical.get("seasons_loaded", []),
        "source_urls": historical.get("source_urls", []),
        "historical_source_urls": historical.get("source_urls", []),
        "historical_issues": historical.get("issues", []),
        "rate_estimate": model.get("rate_estimate", {}),
        "training_matches": model.get("training_matches", 0),
        "dixon_coles": model.get("dixon_coles", {}),
        "models": model.get("models", {}),
        "historical_backtest": model.get("historical_backtest"),
        "reason": model.get("reason") or (model.get("rate_estimate") or {}).get("reason"),
        "market_gate": "WAIT",
        "model": model,
        "note": (
            "This endpoint returns an experimental historical Poisson/Dixon-Coles "
            "distribution, not a guaranteed score or betting signal. Exact-score "
            "odds, de-vigged market probabilities and a validated EV gate are not "
            "connected to this request; the market gate therefore remains WAIT."
        ),
    }