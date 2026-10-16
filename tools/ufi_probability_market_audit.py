#!/usr/bin/env python3
"""Research-only audit of model probabilities against timestamp-valid 1X2 odds.

This tool measures probability differences and forecast quality. It does not rank
or recommend bets and does not estimate profit. Odds must be user-supplied with
timezone-aware capture timestamps strictly before kickoff.
"""
from __future__ import annotations
import argparse, csv, json, math
from datetime import datetime, timezone
from pathlib import Path

OUTCOMES = ("H", "D", "A")
MODEL_PREFIX = "ensemble_p_"


def parse_timestamp(value: str) -> datetime:
    """Parse ISO-8601 timestamp and reject timestamps without an explicit zone."""
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return dt.astimezone(timezone.utc)


def normalize_market(odds: list[float]) -> tuple[list[float], float]:
    """Return margin-normalized implied probabilities and raw overround."""
    if len(odds) != 3 or any(not math.isfinite(x) or x <= 1 for x in odds):
        raise ValueError("expected three finite decimal odds values greater than 1")
    raw = [1.0 / x for x in odds]
    total = sum(raw)
    if total <= 0:
        raise ValueError("invalid implied probability total")
    return [x / total for x in raw], total - 1.0


def brier(probs: list[float], actual: str) -> float:
    if actual not in OUTCOMES or len(probs) != 3:
        raise ValueError("invalid outcome or probability vector")
    if any(not math.isfinite(p) or p < 0 or p > 1 for p in probs):
        raise ValueError("probabilities must be finite and in [0, 1]")
    if abs(sum(probs) - 1.0) > 1e-4:
        raise ValueError("probabilities must sum to 1")
    return sum((probs[i] - (1.0 if OUTCOMES[i] == actual else 0.0)) ** 2 for i in range(3))


def log_loss(probs: list[float], actual: str) -> float:
    if actual not in OUTCOMES:
        raise ValueError("invalid outcome")
    if len(probs) != 3 or any(not math.isfinite(p) or p < 0 or p > 1 for p in probs):
        raise ValueError("invalid probability vector")
    if abs(sum(probs) - 1.0) > 1e-4:
        raise ValueError("probabilities must sum to 1")
    return -math.log(max(1e-15, probs[OUTCOMES.index(actual)]))


def load_odds(path: Path) -> tuple[dict, dict]:
    valid, rejected = {}, {"missing_or_invalid_timestamp": 0, "bad_odds": 0, "duplicate_key": 0}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            key = tuple((row.get(k) or "").strip() for k in
                        ("date", "league_code", "home_team", "away_team"))
            try:
                if not all(key):
                    raise ValueError("missing fixture key")
                captured = parse_timestamp(row["captured_at_utc"])
                kickoff = parse_timestamp(row["kickoff_at_utc"])
                if captured >= kickoff:
                    rejected["missing_or_invalid_timestamp"] += 1
                    continue
            except (KeyError, ValueError, TypeError):
                rejected["missing_or_invalid_timestamp"] += 1
                continue
            try:
                odds = [float(row[k]) for k in ("home_odds", "draw_odds", "away_odds")]
                market, overround = normalize_market(odds)
            except (KeyError, ValueError, TypeError):
                rejected["bad_odds"] += 1
                continue
            if key in valid:
                rejected["duplicate_key"] += 1
                # Ambiguous duplicate prices are excluded rather than silently choosing one.
                valid.pop(key, None)
                continue
            valid[key] = {"odds": odds, "market": market, "overround": overround,
                          "captured_at_utc": captured.isoformat(), "kickoff_at_utc": kickoff.isoformat()}
    return valid, rejected


def run_audit(predictions_path: Path, odds_path: Path, out_dir: Path) -> dict:
    odds, rejected = load_odds(odds_path)
    rows, unmatched, invalid_probs = [], 0, 0
    with predictions_path.open(encoding="utf-8-sig", newline="") as f:
        predictions = list(csv.DictReader(f))
    for row in predictions:
        key = tuple((row.get(k) or "").strip() for k in
                    ("date", "league_code", "home_team", "away_team"))
        if key not in odds:
            unmatched += 1
            continue
        actual = (row.get("actual_1x2") or "").strip()
        try:
            model_probs = [float(row[MODEL_PREFIX + suffix]) for suffix in ("home", "draw", "away")]
            # Reuse the same probability validity rules as the scoring functions.
            model_brier = brier(model_probs, actual)
            model_ll = log_loss(model_probs, actual)
        except (KeyError, ValueError, TypeError):
            invalid_probs += 1
            continue
        market_row = odds[key]
        market_probs = market_row["market"]
        market_brier = brier(market_probs, actual)
        market_ll = log_loss(market_probs, actual)
        result = {"date": key[0], "league_code": key[1], "home_team": key[2], "away_team": key[3],
                  "actual_1x2": actual, "odds_captured_at_utc": market_row["captured_at_utc"],
                  "kickoff_at_utc": market_row["kickoff_at_utc"],
                  "home_odds": market_row["odds"][0], "draw_odds": market_row["odds"][1],
                  "away_odds": market_row["odds"][2], "market_overround": round(market_row["overround"], 6),
                  "model_brier": round(model_brier, 6), "market_brier": round(market_brier, 6),
                  "model_log_loss": round(model_ll, 6), "market_log_loss": round(market_ll, 6),
                  "brier_difference_model_minus_market": round(model_brier - market_brier, 6),
                  "log_loss_difference_model_minus_market": round(model_ll - market_ll, 6)}
        for i, label in enumerate(("home", "draw", "away")):
            result[f"model_p_{label}"] = round(model_probs[i], 6)
            result[f"market_p_{label}_no_vig"] = round(market_probs[i], 6)
            result[f"probability_gap_{label}"] = round(model_probs[i] - market_probs[i], 6)
        rows.append(result)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_csv = out_dir / "probability_market_audit.csv"
    columns = list(rows[0]) if rows else ["date", "league_code", "home_team", "away_team",
        "actual_1x2", "model_brier", "market_brier", "model_log_loss", "market_log_loss"]
    with output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    n = len(rows)
    summary = {
        "purpose": "retrospective probability-quality audit; not a betting recommendation",
        "matched_scored_fixtures": n,
        "prediction_rows_without_valid_odds_match": unmatched,
        "invalid_prediction_rows": invalid_probs,
        "odds_rejections": rejected,
        "mean_model_brier": round(sum(r["model_brier"] for r in rows) / n, 6) if n else None,
        "mean_market_brier": round(sum(r["market_brier"] for r in rows) / n, 6) if n else None,
        "mean_model_log_loss": round(sum(r["model_log_loss"] for r in rows) / n, 6) if n else None,
        "mean_market_log_loss": round(sum(r["market_log_loss"] for r in rows) / n, 6) if n else None,
        "mean_brier_difference_model_minus_market": round(sum(r["brier_difference_model_minus_market"] for r in rows) / n, 6) if n else None,
        "mean_log_loss_difference_model_minus_market": round(sum(r["log_loss_difference_model_minus_market"] for r in rows) / n, 6) if n else None,
        "interpretation": "Negative model-minus-market differences indicate lower average forecast loss on this matched historical sample only; they do not establish future profitability.",
        "output_csv": str(output_csv),
        "limitations": [
            "Only matched, scored historical fixtures with valid pre-kickoff odds are compared.",
            "Margin-normalized odds are a market benchmark, not objective true probabilities.",
            "Do not infer live performance from retrospective results; use multiple chronological periods and enough fixtures.",
            "This audit reports probability gaps and forecast scores, not recommended selections or profit estimates."
        ]
    }
    (out_dir / "probability_market_audit.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", default="output/openfootball/integrated/advanced/advanced_predictions.csv")
    parser.add_argument("--odds-csv", default="data/private/pre_match_odds.csv")
    parser.add_argument("--out", default="output/openfootball/integrated/market_audit")
    args = parser.parse_args()
    summary = run_audit(Path(args.predictions), Path(args.odds_csv), Path(args.out))
    print(json.dumps(summary, indent=2))
    if summary["matched_scored_fixtures"] == 0:
        raise SystemExit("No matched historical fixtures with valid pre-kickoff odds; audit produced empty outputs.")

if __name__ == "__main__":
    main()
