#!/usr/bin/env python3
"""Optional, source-conscious Gemini research adapter for UFI.

This adapter is additive: it never replaces score engines, never qualifies a market,
and never treats generated claims as verified facts. Credentials are read only from
the server environment; never put API keys in source, GitHub, logs, or browser code.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiResearchError(RuntimeError):
    """Raised when the optional research provider cannot safely return a result."""


def gemini_configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def extract_research_brief(question: str, source_material: list[dict[str, Any]] | None = None,
                          *, timeout: float = 20.0) -> dict[str, Any]:
    """Ask Gemini to structure supplied evidence; no web access or facts are assumed.

    source_material should contain fetched, timestamped source records. The function
    returns NEEDS_DATA when no source material is supplied, and never marks claims
    as independently verified.
    """
    if not source_material:
        return {
            "status": "NEEDS_DATA",
            "reason": "No timestamped source material supplied; Gemini must not invent team news.",
            "claims": [],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return {
            "status": "NEEDS_DATA",
            "reason": "Gemini is not configured; use existing provider evidence and preserve unknowns.",
            "claims": [],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    prompt = (
        "You are an evidence extraction assistant for a football research pipeline. "
        "Only extract claims explicitly supported by the supplied source material. "
        "Do not browse, guess, predict scores, estimate probabilities, or fill gaps. "
        "For each claim return text, source_url, source_name, source_timestamp, and "
        "confidence ('direct' or 'ambiguous'). If source support is absent, omit the claim. "
        "Return JSON only with keys: claims, missing_information, conflicts. "
        "User research question: " + question + "\nSOURCE MATERIAL JSON:\n" +
        json.dumps(source_material, ensure_ascii=False, sort_keys=True)
    )
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0}
    }).encode("utf-8")
    url = GEMINI_ENDPOINT.format(model=model) + "?key=" + key
    request = urllib.request.Request(url, data=body, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "UFI-evidence-adapter/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        # Never include request URL or exception text: either can contain a credential.
        raise GeminiResearchError("Gemini request failed (" + type(exc).__name__ + ")") from None

    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
    except (KeyError, IndexError, TypeError, ValueError):
        raise GeminiResearchError("Gemini returned an unexpected response shape") from None

    claims = parsed.get("claims", [])
    if not isinstance(claims, list):
        claims = []
    # Drop claims without traceable source references. These remain research leads,
    # not verified data, until the calling pipeline validates source URLs/timestamps.
    traceable = [
        claim for claim in claims if isinstance(claim, dict)
        and claim.get("source_url") and claim.get("source_timestamp")
        and claim.get("text")
    ]
    return {
        "status": "RESEARCH_LEADS" if traceable else "NEEDS_DATA",
        "claims": traceable,
        "missing_information": parsed.get("missing_information", []),
        "conflicts": parsed.get("conflicts", []),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "provider": "Gemini",
        "verified": False,
        "note": "Claims are unverified extraction leads; validate cited sources before model or qualification use."
    }


def evaluate_market_blacklist(store: Any, fixture: dict[str, Any], market: str) -> dict[str, Any]:
    """Apply only matching team/market/competition blacklist rules.

    A block on one market does not automatically block other markets. This helper
    is intentionally separate from model probability and odds calculations.
    """
    competition = str(fixture.get("competition", ""))
    home = str(fixture.get("home", ""))
    away = str(fixture.get("away", ""))
    reasons = []
    if not home.strip() or not away.strip():
        reasons.append("fixture identity incomplete")
    if home.strip():
        reasons.extend(store.blacklist_reasons(home, market, competition))
    if away.strip():
        reasons.extend(store.blacklist_reasons(away, market, competition))
    return {
        "status": "CUT" if reasons else "SURVIVOR_PENDING_OTHER_GATES",
        "market": market,
        "reasons": reasons,
        "fixture_id": fixture.get("id"),
        "note": "Blacklist result only; all other qualification gates still apply."
    }
