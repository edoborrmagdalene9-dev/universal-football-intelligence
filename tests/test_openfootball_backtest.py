import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import openfootball_backtest as backtest


class BacktestMathTests(unittest.TestCase):
    def test_outcome_probabilities_are_normalized(self):
        probs = backtest.outcome_probs(1.45, 1.1)
        self.assertEqual(len(probs), 3)
        self.assertTrue(all(0 <= p <= 1 for p in probs))
        self.assertAlmostEqual(sum(probs), 1.0, places=10)

    def test_score_metrics_are_finite_and_nonnegative(self):
        brier, logloss = backtest.scores_for((0.5, 0.25, 0.25), "H")
        self.assertGreaterEqual(brier, 0)
        self.assertGreaterEqual(logloss, 0)

    def test_invalid_goal_values_are_rejected(self):
        self.assertIsNone(backtest.safe_float(""))
        self.assertIsNone(backtest.safe_float("not-a-score"))
        self.assertIsNone(backtest.safe_float("-1"))
        self.assertEqual(backtest.safe_float("2"), 2.0)


if __name__ == "__main__":
    unittest.main()
