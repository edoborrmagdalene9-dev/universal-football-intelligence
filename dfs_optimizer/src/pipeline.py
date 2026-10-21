"""End-to-end data validation and chronological football-score backtesting."""
from __future__ import annotations
import csv
from datetime import datetime
from pathlib import Path
from .dc_model import score_grid, outcome_probabilities

REQUIRED = ("date", "home_team", "away_team", "home_goals", "away_goals")

def _parse_date(value):
    value = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unrecognised date {value!r}; use YYYY-MM-DD or DD/MM/YYYY")

def load_matches_csv(source):
    if isinstance(source, (str, Path)):
        with open(source, newline="", encoding="utf-8-sig") as f:
            return load_matches_csv(f)
    if hasattr(source, "read"):
        reader = csv.DictReader(source)
        if not reader.fieldnames:
            raise ValueError("CSV has no header")
        missing = [c for c in REQUIRED if c not in reader.fieldnames]
        if missing:
            raise ValueError("Missing required columns: " + ", ".join(missing))
        rows = list(reader)
    else:
        rows = list(source)
    if not rows:
        raise ValueError("No match rows found")
    valid, issues, seen = [], [], set()
    for idx, row in enumerate(rows, start=2):
        try:
            date = _parse_date(row.get("date"))
            home, away = str(row.get("home_team", "")).strip(), str(row.get("away_team", "")).strip()
            if not home or not away: raise ValueError("home_team and away_team must be non-empty")
            if home.casefold() == away.casefold(): raise ValueError("home_team and away_team cannot be the same")
            hg, ag = int(row.get("home_goals")), int(row.get("away_goals"))
            if hg < 0 or ag < 0: raise ValueError("goals cannot be negative")
            key = (date, home.casefold(), away.casefold(), hg, ag)
            if key in seen:
                issues.append({"row": idx, "severity": "warning", "message": "Exact duplicate match row"})
                continue
            seen.add(key)
            valid.append({"date": date.isoformat(), "home_team": home, "away_team": away, "home_goals": hg, "away_goals": ag})
        except (ValueError, TypeError) as exc:
            issues.append({"row": idx, "severity": "error", "message": str(exc)})
    valid.sort(key=lambda r: (r["date"], r["home_team"], r["away_team"]))
    return {"matches": valid, "issues": issues, "rows_received": len(rows), "rows_valid": len(valid),
            "rows_rejected": sum(i["severity"] == "error" for i in issues)}

def _rates(rows):
    n = len(rows)
    return ((sum(r["home_goals"] for r in rows) + 0.5) / (n + 1.0),
            (sum(r["away_goals"] for r in rows) + 0.5) / (n + 1.0))

def _brier(probabilities, actual):
    return sum((probabilities[k] - float(k == actual)) ** 2 for k in ("home_win", "draw", "away_win"))

def chronological_backtest(matches, min_train=30, train_fraction=0.70, validation_fraction=0.15, max_goals=8, rho=0.0):
    rows = sorted(matches, key=lambda r: (r["date"], r["home_team"], r["away_team"]))
    n = len(rows)
    if n < max(min_train + 3, 10):
        raise ValueError(f"Need more historical matches; received {n}, minimum is {max(min_train + 3, 10)}")
    train_end = max(min_train, int(n * train_fraction))
    val_end = max(train_end + 1, int(n * (train_fraction + validation_fraction)))
    if val_end >= n: val_end = n - 1
    if train_end >= val_end: raise ValueError("Not enough rows for chronological train/validation/test splits")
    predictions = []
    for i in range(train_end, n):
        hr, ar = _rates(rows[:i])
        grid = score_grid(hr, ar, max_goals=max_goals, rho=rho)
        probs = outcome_probabilities(grid)
        actual = rows[i]
        actual_result = "home_win" if actual["home_goals"] > actual["away_goals"] else "away_win" if actual["home_goals"] < actual["away_goals"] else "draw"
        best_score = max(grid, key=grid.get)
        predictions.append({"row_index": i, "date": actual["date"], "home_team": actual["home_team"], "away_team": actual["away_team"],
            "actual_score": f'{actual["home_goals"]}-{actual["away_goals"]}', "predicted_score": f"{best_score[0]}-{best_score[1]}",
            "scoreline_hit": best_score == (actual["home_goals"], actual["away_goals"]), "actual_result": actual_result,
            "predicted_result": max(("home_win", "draw", "away_win"), key=lambda k: probs[k]), "brier": _brier(probs, actual_result),
            "home_rate": hr, "away_rate": ar, "home_win_probability": probs["home_win"], "draw_probability": probs["draw"], "away_win_probability": probs["away_win"]})
    def metrics(items):
        if not items: return {"matches": 0}
        return {"matches": len(items), "exact_scoreline_accuracy": sum(x["scoreline_hit"] for x in items)/len(items),
            "result_accuracy": sum(x["predicted_result"] == x["actual_result"] for x in items)/len(items),
            "mean_brier_score": sum(x["brier"] for x in items)/len(items)}
    val_predictions = [p for p in predictions if train_end <= p["row_index"] < val_end]
    test_predictions = [p for p in predictions if p["row_index"] >= val_end]
    for p in predictions: p.pop("row_index", None)
    return {"rows": n, "split_indices": {"train_end_exclusive": train_end, "validation_end_exclusive": val_end},
        "train_period": {"from": rows[0]["date"], "to": rows[train_end-1]["date"], "matches": train_end},
        "validation_period": {"from": rows[train_end]["date"], "to": rows[val_end-1]["date"], "matches": val_end-train_end},
        "test_period": {"from": rows[val_end]["date"], "to": rows[-1]["date"], "matches": n-val_end},
        "validation_metrics": metrics(val_predictions), "test_metrics": metrics(test_predictions), "all_heldout_metrics": metrics(predictions),
        "predictions": predictions, "baseline": "expanding-window global home/away Poisson score grid",
        "warning": "Baseline only. Exact scoreline accuracy is naturally low; calibrate and compare against league-aware models."}

def validate_contest_entries_csv(source, player_separator="|"):
    if isinstance(source, (str, Path)):
        with open(source, newline="", encoding="utf-8-sig") as f: return validate_contest_entries_csv(f, player_separator)
    reader = csv.DictReader(source)
    if not reader.fieldnames or not {"entry_id", "players"}.issubset(reader.fieldnames):
        raise ValueError("Contest entries need CSV columns: entry_id,players")
    rows, issues, ids = [], [], set()
    for idx, row in enumerate(reader, start=2):
        entry_id = str(row.get("entry_id", "")).strip()
        players = list(dict.fromkeys(p.strip() for p in str(row.get("players", "")).split(player_separator) if p.strip()))
        if not entry_id or not players:
            issues.append({"row": idx, "message": "entry_id and at least one player are required"}); continue
        if entry_id in ids:
            issues.append({"row": idx, "message": f"Duplicate entry_id {entry_id!r}"}); continue
        ids.add(entry_id); rows.append({"entry_id": entry_id, "players": players})
    player_counts, pair_counts = {}, {}
    for row in rows:
        for p in row["players"]: player_counts[p] = player_counts.get(p, 0) + 1
        ps = sorted(row["players"])
        for i, p in enumerate(ps):
            for q in ps[i+1:]:
                key = f"{p} + {q}"; pair_counts[key] = pair_counts.get(key, 0) + 1
    n = len(rows)
    return {"entries": rows, "entry_count": n, "issues": issues,
        "player_ownership": {p: c/n for p,c in player_counts.items()} if n else {}, "pair_counts": pair_counts,
        "warning": "Ownership is meaningful only for the same contest/platform/slate and after suitable entry deduplication."}
