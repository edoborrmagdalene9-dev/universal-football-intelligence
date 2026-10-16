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

    def test_brier_and_log_loss_are_finite_for_valid_forecast(self):
        probs = [0.5, 0.25, 0.25]
        self.assertGreaterEqual(audit.brier(probs, "H"), 0)
        self.assertGreaterEqual(audit.log_loss(probs, "H"), 0)

    def test_rejects_probabilities_that_do_not_sum_to_one(self):
        with self.assertRaises(ValueError):
            audit.brier([0.4, 0.4, 0.4], "H")


if __name__ == "__main__":
    unittest.main()
