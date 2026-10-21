"""Provider-neutral historical player-stat ingestion and projection helpers.

One row per player per fixture is required, including zero-minute rows when known,
so appearance/start probabilities are not biased toward players who appeared.
The projection uses empirical rates; goals per 90 are NOT mislabeled as xG.
"""
from __future__ import annotations
import csv
import io
import math
from statistics import pstdev
from .scoring_engine import score_actual
from collections import defaultdict, Counter
from statistics import median
from typing import Iterable, Mapping

NUMERIC_FIELDS = (
    "minutes", "started", "goals", "assists", "shots_on_target",
    "chances_created", "completed_passes", "interceptions_won", "tackles_won",
    "goals_conceded", "saves", "penalties_saved", "yellow_cards", "red_cards",
    "own_goals", "penalties_missed", "aerial_wins", "aerial_duels",
    "set_piece_shots", "penalty_attempts", "penalties_scored", "penalties_faced",
)
REQUIRED = {"player_id", "player_name", "team", "position", "match_date", "minutes"}

def _num(value, field):
    if value is None or str(value).strip() == "":
        return 0.0
    try:
        x = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be numeric; got {value!r}")
    if not math.isfinite(x):
        raise ValueError(f"{field} must be finite")
    return x

def read_player_stats_csv(source) -> dict:
    reader = csv.DictReader(source)
    if not reader.fieldnames:
        raise ValueError("Player stats CSV is empty or has no header")
    missing = sorted(REQUIRED - set(reader.fieldnames))
    if missing:
        raise ValueError("Missing required player-stat columns: " + ", ".join(missing))
    rows, issues = [], []
    seen = set()
    for line, raw in enumerate(reader, start=2):
        try:
            row = {k: (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
            if not all(row.get(k) for k in ("player_id","player_name","team","position","match_date")):
                raise ValueError("player_id/name/team/position/match_date cannot be blank")
            row["player_id"] = str(row["player_id"])
            row["match_date"] = str(row["match_date"])
            key = (row["player_id"], row["match_date"], str(row.get("fixture_id", "")))
            if key in seen:
                raise ValueError("duplicate player-date-fixture row")
            seen.add(key)
            for field in NUMERIC_FIELDS:
                row[field] = _num(row.get(field, 0), field)
            if row["minutes"] < 0 or row["minutes"] > 130:
                raise ValueError("minutes must be between 0 and 130")
            if row["started"] not in (0, 1):
                raise ValueError("started must be 0 or 1")
            if row["minutes"] == 0 and row["started"] == 1:
                raise ValueError("a zero-minute row cannot be marked as started")
            for field in NUMERIC_FIELDS:
                if row[field] < 0:
                    raise ValueError(f"{field} cannot be negative")
            if row["penalties_scored"] > row["penalty_attempts"]:
                raise ValueError("penalties_scored cannot exceed penalty_attempts")
            rows.append(row)
        except ValueError as exc:
            issues.append({"line": line, "reason": str(exc)})
    return {"rows": rows, "rows_received": len(rows)+len(issues),
            "rows_valid": len(rows), "rows_rejected": len(issues), "issues": issues}

def build_player_projections(rows: Iterable[Mapping], recent_matches: int = 10,
                             expected_minutes_override: Mapping[str, float] | None = None) -> dict:
    """Return profiles and optimizer-ready rows using last-N dated observations.

    Required input rows should include non-appearance observations. Event counts are
    converted to per-90 rates using minutes actually played; expected minutes default
    to median recent minutes. Small-sample penalty rates use Beta(1,1) smoothing.
    """
    if recent_matches < 1:
        raise ValueError("recent_matches must be positive")
    groups = defaultdict(list)
    for r in rows:
        groups[str(r["player_id"])].append(dict(r))
    profiles, players = [], []
    for pid, history in groups.items():
        history.sort(key=lambda r: str(r["match_date"]))
        recent = history[-recent_matches:]
        identity = recent[-1]
        appeared = [r for r in recent if float(r.get("minutes",0)) > 0]
        total_minutes = sum(float(r.get("minutes",0)) for r in appeared)
        expected_minutes = float((expected_minutes_override or {}).get(
            pid, median([float(r["minutes"]) for r in appeared]) if appeared else 0))
        expected_minutes = max(0, min(120, expected_minutes))
        appearance_probability = sum(float(r.get("minutes",0)) > 0 for r in recent) / len(recent)
        start_probability = sum(float(r.get("started",0)) > 0 for r in recent) / len(recent)
        def total(field): return sum(float(r.get(field,0) or 0) for r in appeared)
        def rate90(field): return total(field) / total_minutes * 90 if total_minutes > 0 else 0.0
        scale = expected_minutes / 90
        attempts, scored = total("penalty_attempts"), total("penalties_scored")
        pens_saved, pens_faced = total("penalties_saved"), total("penalties_faced")
        # Beta(1,1) posterior means avoid extreme 0/100% rates from tiny samples.
        pen_conversion = (scored + 1) / (attempts + 2)
        keeper_pen_save = (pens_saved + 1) / (pens_faced + 2)
        pass_values = Counter(int(float(r.get("completed_passes",0))) for r in appeared)
        pmf_den = sum(pass_values.values())
        pass_pmf = ({n: count/pmf_den for n,count in pass_values.items()} if pmf_den else {})
        stats = {
            "appearance_probability": appearance_probability,
            "start_probability": start_probability,
            "xg": rate90("goals") * scale,
            "xa": rate90("assists") * scale,
            "x_sot": rate90("shots_on_target") * scale,
            "x_chances_created": rate90("chances_created") * scale,
            "x_passes": rate90("completed_passes") * scale,
            "x_interceptions": rate90("interceptions_won") * scale,
            "clean_sheet_probability": sum(float(r.get("minutes",0)) >= 55 and float(r.get("goals_conceded",0)) == 0 for r in appeared) / max(1,len(appeared)),
            "expected_goals_conceded": rate90("goals_conceded") * scale,
            "expected_yellow_cards": rate90("yellow_cards") * scale,
            "expected_red_cards": rate90("red_cards") * scale,
            "expected_own_goals": rate90("own_goals") * scale,
            "expected_penalties_missed": max(0, attempts-scored) / max(1,len(appeared)),
            "expected_saves": rate90("saves") * scale,
            "probability_penalty_saved": keeper_pen_save * min(1.0, pens_faced / max(1,len(appeared))),
        }
        observed_points = [score_actual(r, str(identity["position"])) for r in appeared]
        profile = {
            "player_id": pid, "player_name": identity["player_name"], "team": identity["team"],
            "position": identity["position"], "sample_matches": len(recent),
            "sample_appearances": len(appeared), "expected_minutes": expected_minutes,
            "historical_points_mean": sum(observed_points)/len(observed_points) if observed_points else 0.0,
            "historical_points_sd": pstdev(observed_points) if len(observed_points)>1 else 0.0,
            "interceptions_per90": rate90("interceptions_won"),
            "completed_passes_per90": rate90("completed_passes"),
            "pass_count_pmf": pass_pmf,
            "yellow_cards_per90": rate90("yellow_cards"),
            "aerial_win_rate": (total("aerial_wins")+1)/(total("aerial_duels")+2),
            "set_piece_shots_per90": rate90("set_piece_shots"),
            "penalty_conversion_posterior": pen_conversion,
            "goalkeeper_penalty_save_posterior": keeper_pen_save,
            "penalty_attempts_observed": int(attempts),
            "penalties_faced_observed": int(pens_faced),
            "projection_inputs": stats,
        }
        # salary and fixture context are supplied by the current slate CSV, not inferred.
        profiles.append(profile)
    return {"profiles": profiles, "warning": (
        "Empirical historical event rates are not true xG/xA forecasts. Include zero-minute "
        "player-fixture rows to estimate availability; add salary and current fixture context "
        "from a permitted source before lineup optimization.")}

def merge_projections_with_slate(profiles: Iterable[Mapping], slate_rows: Iterable[Mapping],
                                 expected_points_fn) -> list[dict]:
    """Join historical player profiles to current slate metadata by stable player_id."""
    by_id = {str(p["player_id"]): p for p in profiles}
    out = []
    for slate in slate_rows:
        pid = str(slate["player_id"])
        if pid not in by_id:
            continue
        p = by_id[pid]
        minutes = float(slate.get("expected_minutes") or p["expected_minutes"])
        inputs = dict(p["projection_inputs"])
        scale = minutes / max(1.0, p["expected_minutes"]) if p["expected_minutes"] > 0 else 0.0
        for key in ("xg","xa","x_sot","x_chances_created","x_passes","x_interceptions",
                    "expected_goals_conceded","expected_yellow_cards","expected_red_cards",
                    "expected_own_goals","expected_penalties_missed","expected_saves"):
            inputs[key] = float(inputs.get(key,0))*scale
        # Use historical pass-count PMF scaled only when expected minutes are close to sample minutes.
        pass_pmf = p["pass_count_pmf"] if abs(minutes-p["expected_minutes"]) <= 1 else None
        projection = float(slate.get("projection") or expected_points_fn(inputs, str(slate["position"]), pass_count_pmf=pass_pmf or None))
        row = dict(slate); row["id"] = pid; row["projection"] = projection
        row["ownership"] = float(slate.get("ownership") or 0)
        row["historical_interceptions_per90"] = p["interceptions_per90"]
        row["historical_passes_per90"] = p["completed_passes_per90"]
        row["historical_aerial_win_rate"] = p["aerial_win_rate"]
        row["historical_penalty_conversion"] = p["penalty_conversion_posterior"]
        out.append(row)
    return out
