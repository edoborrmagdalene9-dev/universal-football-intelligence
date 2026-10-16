import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "ufi_probability_market_audit.py"
spec = importlib.util.spec_from_file_location("ufi_probability_market_audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ProbabilityMarketAuditTests(unittest.TestCase):
    def test_normalized_market_sums_to_one_and_reports_overround(self):
        probs, overround = audit.normalize_market([2.0, 3.5, 4.0])
        self.assertAlmostEqual(sum(probs), 1.0)
        self.assertGreater(overround, 0.0)

    def test_rejects_invalid_decimal_odds(self):
        with self.assertRaises(ValueError):
            audit.normalize_market([2.0, 1.0, 3.0])

    def test_rejects_timezone_missing_timestamp(self):
        with self.assertRaises(ValueError):
            audit.parse_timestamp("2026-10-16T12:00:00")

    def test_rejects_capture_after_kickoff(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "odds.csv"
            path.write_text(
                "date,league_code,home_team,away_team,home_odds,draw_odds,away_odds,captured_at_utc,kickoff_at_utc\n"
                "2026-10-01,ENG1,A,B,2.1,3.2,3.4,2026-10-01T20:00:00Z,2026-10-01T19:00:00Z\n",
                encoding="utf-8",
            )
            rows, rejected = audit.load_odds(path)
            self.assertEqual(rows, {})
            self.assertEqual(rejected["missing_or_invalid_timestamp"], 1)

    def test_duplicate_fixture_prices_are_excluded_even_with_three_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "odds.csv"
            header = "date,league_code,home_team,away_team,home_odds,draw_odds,away_odds,captured_at_utc,kickoff_at_utc\n"
            row = "2026-10-01,ENG1,A,B,2.1,3.2,3.4,2026-10-01T17:00:00Z,2026-10-01T19:00:00Z\n"
            path.write_text(header + row + row + row, encoding="utf-8")
            rows, rejected = audit.load_odds(path)
            self.assertEqual(rows, {})
            self.assertEqual(rejected["duplicate_key"], 2)

    def test_end_to_end_audit_writes_probability_gap_and_scores(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            predictions = root / "predictions.csv"
            odds = root / "odds.csv"
            predictions.write_text(
                "date,league_code,home_team,away_team,actual_1x2,ensemble_p_home,ensemble_p_draw,ensemble_p_away\n"
                "2026-10-01,ENG1,A,B,H,0.5,0.3,0.2\n",
                encoding="utf-8",
            )
            odds.write_text(
                "date,league_code,home_team,away_team,home_odds,draw_odds,away_odds,captured_at_utc,kickoff_at_utc\n"
                "2026-10-01,ENG1,A,B,2.0,3.3333333333,5.0,2026-10-01T17:00:00Z,2026-10-01T19:00:00Z\n",
                encoding="utf-8",
            )
            summary = audit.run_audit(predictions, odds, root / "out")
            self.assertEqual(summary["matched_scored_fixtures"], 1)
            self.assertTrue((root / "out" / "probability_market_audit.csv").is_file())
            self.assertTrue((root / "out" / "probability_market_audit.json").is_file())
            with (root / "out" / "probability_market_audit.csv").open(encoding="utf-8-sig", newline="") as handle:
                import csv
                row = next(csv.DictReader(handle))
            self.assertIn("probability_gap_home", row)
            self.assertIn("brier_difference_model_minus_market", row)

    def test_brier_and_log_loss_are_finite_for_valid_forecast(self):
        probs = [0.5, 0.25, 0.25]
        self.assertGreaterEqual(audit.brier(probs, "H"), 0)
        self.assertGreaterEqual(audit.log_loss(probs, "H"), 0)

    def test_rejects_probabilities_that_do_not_sum_to_one(self):
        with self.assertRaises(ValueError):
            audit.brier([0.4, 0.4, 0.4], "H")


if __name__ == "__main__":
    unittest.main()
