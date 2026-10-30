#!/usr/bin/env python3
"""Small secret-safe HTTP proxy for Sportmonks Football API v3.

Run behind a private/controlled backend (Replit/Render/VPS), never expose the
SPORTMONKS_API_TOKEN in browser JavaScript or commit it to the repository.
This is a data transport adapter, not a prediction model.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import date

API_BASE = "https://api.sportmonks.com/v3/football"
TOKEN = os.environ.get("SPORTMONKS_API_TOKEN", "").strip()
PORT = int(os.environ.get("PORT", "8080"))
ALLOWED_ORIGIN = os.environ.get("UFI_ALLOWED_ORIGIN", "https://edoborrmagdalene9-dev.github.io").strip()
CACHE: dict[str, tuple[float, object]] = {}
CACHE_TTL = {"live": 5, "fixtures": 300, "fixture": 5, "weather": 1800}
REQUESTS: dict[str, list[float]] = {}
RATE_WINDOW = 60
RATE_LIMIT = 60


class ProviderError(Exception):
    pass


def provider_get(path: str, params: dict[str, str] | None = None) -> object:
    if not TOKEN:
        raise ProviderError("SPORTMONKS_API_TOKEN is not configured on the server.")
    query = dict(params or {})
    query["api_token"] = TOKEN
    url = API_BASE + path + "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "UFI-research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            if response.status != 200:
                raise ProviderError(f"Provider returned HTTP {response.status}")
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Never echo request URL: it contains the private token.
        raise ProviderError(f"Football data provider returned HTTP {exc.code}. Check plan, endpoint and token.") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProviderError(f"Football data provider unavailable: {type(exc).__name__}") from exc


def cached(key: str, ttl: int, fn):
    now = time.time()
    if key in CACHE and now - CACHE[key][0] < ttl:
        return CACHE[key][1], True
    value = fn()
    CACHE[key] = (now, value)
    return value, False


def origin_allowed(origin: str | None) -> bool:
    # Non-browser clients may omit Origin. Browser origins must match exactly.
    return not origin or origin == ALLOWED_ORIGIN


def rate_limited(client_ip: str, now: float | None = None) -> bool:
    """Apply a per-client sliding-window limit; return True when over limit."""
    current = time.time() if now is None else now
    recent = [stamp for stamp in REQUESTS.get(client_ip, []) if current - stamp < RATE_WINDOW]
    if len(recent) >= RATE_LIMIT:
        REQUESTS[client_ip] = recent
        return True
    recent.append(current)
    REQUESTS[client_ip] = recent
    return False


def open_meteo_weather(lat: float, lon: float, day: str, hour: int) -> object:
    """Fetch one hourly weather observation/forecast from Open-Meteo (no API key)."""
    today = date.today().isoformat()
    archive = day < today
    base = "https://archive-api.open-meteo.com/v1/archive" if archive else "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": str(lat), "longitude": str(lon), "start_date": day, "end_date": day,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "timezone": "UTC"
    }
    # Forecast uses forecast_days/date selection; archive uses start/end date.
    if not archive:
        params.pop("start_date", None)
        params.pop("end_date", None)
        params["forecast_days"] = "7"
    url = base + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "UFI-research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProviderError("Open-Meteo weather source unavailable: " + type(exc).__name__) from exc
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        raise ProviderError("Weather source returned no hourly observations for that date/location.")
    index = min(range(len(times)), key=lambda i: abs((times[i].split("T")[0] != day) * 100000 + (int(times[i][11:13]) - hour) ** 2))
    if not times[index].startswith(day + "T"):
        raise ProviderError("Requested date is outside the provider's available weather window.")
    def value(key):
        values = hourly.get(key) or []
        return values[index] if index < len(values) else None
    return {
        "source": "Open-Meteo", "sourceUrl": base, "fetchedAt": time.time(),
        "requested": {"latitude": lat, "longitude": lon, "date": day, "hourUtc": hour},
        "matchedHourUtc": times[index], "archive": archive,
        "weather": {"temperatureC": value("temperature_2m"), "relativeHumidityPct": value("relative_humidity_2m"),
                    "precipitationMm": value("precipitation"), "windSpeedKmh": value("wind_speed_10m")},
        "note": "Grid-cell weather estimate, not stadium sensor data; location and kickoff-hour mapping must be checked."
    }


def get_payload(route: str, query: dict[str, list[str]]) -> tuple[object, bool]:
    if route == "/api/health":
        return {"ok": True, "provider": "Sportmonks Football API v3", "tokenConfigured": bool(TOKEN),
                "note": "Provider connectivity and coverage must be verified; health does not imply model accuracy."}, False
    if route == "/api/weather":
        try:
            lat = float((query.get("lat") or [""])[0])
            lon = float((query.get("lon") or [""])[0])
            raw_date = (query.get("date") or [date.today().isoformat()])[0]
            hour = int((query.get("hour") or ["12"])[0])
            date.fromisoformat(raw_date)
            if not (-90 <= lat <= 90 and -180 <= lon <= 180 and 0 <= hour <= 23):
                raise ValueError()
        except (ValueError, TypeError) as exc:
            raise ProviderError("weather requires valid lat, lon, date=YYYY-MM-DD and hour=0..23") from exc
        key = f"weather:{lat:.3f}:{lon:.3f}:{raw_date}:{hour}"
        data, hit = cached(key, CACHE_TTL["weather"], lambda: open_meteo_weather(lat, lon, raw_date, hour))
        data["cacheHit"] = hit
        return data, hit
    if route == "/api/inplay-odds":
        fixture_id = (query.get("id") or [""])[0].strip()
        bookmaker_id = (query.get("bookmaker") or [""])[0].strip()
        market_id = (query.get("market") or ["1"])[0].strip()
        if not fixture_id.isdigit() or not bookmaker_id.isdigit() or not market_id.isdigit():
            raise ProviderError("inplay-odds requires numeric id=fixture, bookmaker=provider bookmaker ID and market=market ID")
        filters = f"bookmakers:{bookmaker_id};markets:{market_id}"
        key = f"inplay-odds:{fixture_id}:{bookmaker_id}:{market_id}"
        data, hit = cached(key, CACHE_TTL["live"], lambda: provider_get(
            "/odds/inplay/fixtures/" + fixture_id,
            {"include": "market;bookmaker;fixture", "filters": filters}))
        return {"source": "Sportmonks in-play odds", "fetchedAt": time.time(), "fixtureId": fixture_id,
                "bookmakerId": bookmaker_id, "marketId": market_id, "cacheHit": hit, "data": data}, hit
    if route == "/api/fixtures":
        raw_date = (query.get("date") or [date.today().isoformat()])[0]
        try:
            date.fromisoformat(raw_date)
        except ValueError as exc:
            raise ProviderError("date must use YYYY-MM-DD") from exc
        includes = "participants;scores;state;events.type;lineups.details.type;statistics.type;referees;venue"
        key = "fixtures:" + raw_date
        data, hit = cached(key, CACHE_TTL["fixtures"], lambda: provider_get(
            "/fixtures/date/" + raw_date, {"include": includes, "per_page": "100"}))
        return {"source": "Sportmonks", "fetchedAt": time.time(), "date": raw_date, "cacheHit": hit, "data": data}, hit
    if route == "/api/live":
        includes = "participants;scores;state;events.type;lineups.details.type;statistics.type;referees;venue"
        key = "live"
        data, hit = cached(key, CACHE_TTL["live"], lambda: provider_get("/livescores/inplay", {"include": includes}))
        return {"source": "Sportmonks", "fetchedAt": time.time(), "cacheHit": hit, "data": data}, hit
    if route == "/api/fixture":
        fixture_id = (query.get("id") or [""])[0].strip()
        if not fixture_id.isdigit():
            raise ProviderError("id must be a numeric provider fixture ID")
        includes = "participants;scores;state;events.type;lineups.details.type;statistics.type;referees;venue"
        key = "fixture:" + fixture_id
        data, hit = cached(key, CACHE_TTL["fixture"], lambda: provider_get(
            "/fixtures/" + fixture_id, {"include": includes}))
        return {"source": "Sportmonks", "fetchedAt": time.time(), "cacheHit": hit, "data": data}, hit
    raise ProviderError("Unknown endpoint. Use /api/health, /api/fixtures?date=YYYY-MM-DD, /api/live, /api/fixture?id=ID, /api/inplay-odds?id=ID&bookmaker=ID&market=1 or /api/weather?lat=..&lon=..&date=YYYY-MM-DD&hour=..")


class Handler(BaseHTTPRequestHandler):
    def _headers(self, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        origin = self.headers.get("Origin")
        if origin and origin == ALLOWED_ORIGIN:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _json(self, status: int, payload: object):
        self._headers(status)
        if status != 204:
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        origin = self.headers.get("Origin")
        if not origin_allowed(origin):
            self._json(403, {"ok": False, "error": "Origin not allowed"})
            return
        self._json(204, {})

    def do_GET(self):
        origin = self.headers.get("Origin")
        if not origin_allowed(origin):
            self._json(403, {"ok": False, "error": "Origin not allowed"})
            return
        if rate_limited(self.client_address[0]):
            self._json(429, {"ok": False, "error": "Rate limit exceeded; retry shortly."})
            return
        parsed = urllib.parse.urlparse(self.path)
        try:
            payload, _ = get_payload(parsed.path, urllib.parse.parse_qs(parsed.query))
            self._json(200, payload)
        except ProviderError as exc:
            status = 400 if "must use" in str(exc) or "must be" in str(exc) or "Unknown endpoint" in str(exc) else 502
            self._json(status, {"ok": False, "error": str(exc)})

    def do_POST(self):
        origin = self.headers.get("Origin")
        if not origin_allowed(origin):
            self._json(403, {"ok": False, "error": "Origin not allowed"})
            return
        if rate_limited(self.client_address[0]):
            self._json(429, {"ok": False, "error": "Rate limit exceeded; retry shortly."})
            return
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path not in ("/api/ai/council", "/api/slip/historical-audit"):
            self._json(405, {"ok": False, "error": "only supported POST routes are /api/ai/council and /api/slip/historical-audit"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > 40000:
                self._json(413, {"ok": False, "error": "Request body must be between 2 and 40000 bytes"})
                return
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
            if parsed.path == "/api/ai/council":
                prompt = data.get("prompt") if isinstance(data, dict) else None
                if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 28000:
                    self._json(400, {"ok": False, "error": "prompt is required and must be at most 28000 characters"})
                    return
                payload, _ = get_payload(parsed.path, {"prompt": [prompt]})
                self._json(200, payload)
                return
            picks = data.get("picks") if isinstance(data, dict) else None
            if not isinstance(picks, list) or not picks or len(picks) > 50:
                self._json(400, {"ok": False, "error": "Provide 1–50 picks in the picks array."})
                return
            try:
                try:
                    from .historical_1x2_audit import audit, download_dataset, load_matches
                except ImportError:
                    from historical_1x2_audit import audit, download_dataset, load_matches
                cache = os.getenv("UFI_HISTORICAL_CACHE", ".cache/ufi-historical")
                parquet = download_dataset(__import__("pathlib").Path(cache))
                rows = load_matches(parquet)
                report = audit(rows, picks)
                self._json(200, {"ok": True, "report": report})
            except RuntimeError as exc:
                self._json(503, {"ok": False, "error": str(exc), "code": "HISTORICAL_DEPENDENCY_OR_DATA_UNAVAILABLE"})
            except (ValueError, OSError) as exc:
                self._json(400, {"ok": False, "error": str(exc)})
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"ok": False, "error": "Request body must be valid JSON"})
        except ProviderError as exc:
            self._json(502, {"ok": False, "error": str(exc)})

    def log_message(self, fmt, *args):
        # Avoid logging query strings or secrets.
        print(f"{self.address_string()} {self.command} {urllib.parse.urlparse(self.path).path}")


if __name__ == "__main__":
    if not TOKEN:
        print("WARNING: SPORTMONKS_API_TOKEN is unset; /api/health works but data endpoints will not.")
    print(f"UFI live-data proxy listening on 0.0.0.0:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
