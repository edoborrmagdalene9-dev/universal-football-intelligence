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
CACHE_TTL = {"live": 15, "fixtures": 300, "fixture": 15}\nREQUESTS: dict[str, list[float]] = {}\nRATE_WINDOW = 60\nRATE_LIMIT = 60


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


def get_payload(route: str, query: dict[str, list[str]]) -> tuple[object, bool]:
    if route == "/api/health":
        return {"ok": True, "provider": "Sportmonks Football API v3", "tokenConfigured": bool(TOKEN),
                "note": "Provider connectivity and coverage must be verified; health does not imply model accuracy."}, False
    if route == "/api/fixtures":
        raw_date = (query.get("date") or [date.today().isoformat()])[0]
        try:
            date.fromisoformat(raw_date)
        except ValueError as exc:
            raise ProviderError("date must use YYYY-MM-DD") from exc
        includes = "participants;scores;state;events.type;lineups.details.type;statistics.type"
        key = "fixtures:" + raw_date
        data, hit = cached(key, CACHE_TTL["fixtures"], lambda: provider_get(
            "/fixtures/date/" + raw_date, {"include": includes, "per_page": "100"}))
        return {"source": "Sportmonks", "fetchedAt": time.time(), "date": raw_date, "cacheHit": hit, "data": data}, hit
    if route == "/api/live":
        includes = "participants;scores;state;events.type;lineups.details.type;statistics.type"
        key = "live"
        data, hit = cached(key, CACHE_TTL["live"], lambda: provider_get("/livescores/inplay", {"include": includes}))
        return {"source": "Sportmonks", "fetchedAt": time.time(), "cacheHit": hit, "data": data}, hit
    if route == "/api/fixture":
        fixture_id = (query.get("id") or [""])[0].strip()
        if not fixture_id.isdigit():
            raise ProviderError("id must be a numeric provider fixture ID")
        includes = "participants;scores;state;events.type;lineups.details.type;statistics.type"
        key = "fixture:" + fixture_id
        data, hit = cached(key, CACHE_TTL["fixture"], lambda: provider_get(
            "/fixtures/" + fixture_id, {"include": includes}))
        return {"source": "Sportmonks", "fetchedAt": time.time(), "cacheHit": hit, "data": data}, hit
    raise ProviderError("Unknown endpoint. Use /api/health, /api/fixtures?date=YYYY-MM-DD, /api/live or /api/fixture?id=ID.")


class Handler(BaseHTTPRequestHandler):
    def _headers(self, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_OPTIONS(self):
        self._headers(204)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        try:
            payload, _ = get_payload(parsed.path, urllib.parse.parse_qs(parsed.query))
            self._headers(200)
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        except ProviderError as exc:
            self._headers(400 if "must use" in str(exc) or "must be" in str(exc) or "Unknown endpoint" in str(exc) else 502)
            self.wfile.write(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):
        # Avoid logging query strings or secrets.
        print(f"{self.address_string()} {self.command} {urllib.parse.urlparse(self.path).path}")


if __name__ == "__main__":
    if not TOKEN:
        print("WARNING: SPORTMONKS_API_TOKEN is unset; /api/health works but data endpoints will not.")
    print(f"UFI live-data proxy listening on 0.0.0.0:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
