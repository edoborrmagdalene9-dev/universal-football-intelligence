import unittest
from tools.exact_score_walkforward import evaluate, poisson_pmf, result_probs


class WalkForwardTests(unittest.TestCase):
    def test_poisson_distribution_starts_correctly(self):
        self.assertAlmostEqual(poisson_pmf(0, 0), 1.0)
        self.assertAlmostEqual(poisson_pmf(1, 0), 0.0)

    def test_outcomes_normalize(self):
        _, p = result_probs(1.4, 1.1)
        self.assertAlmostEqual(sum(p), 1.0, places=9)

    def test_predictions_start_after_minimum_history_and_compare_baselines(self):
        rows = []
        for i in range(30):
            rows.append({"date": f"2025-01-{(i % 28)+1:02d}", "sort": float(i),
                         "home_team": "A" if i % 2 == 0 else "B",
                         "away_team": "B" if i % 2 == 0 else "A",
                         "home_goals": 1 + (i % 3 == 0), "away_goals": i % 2})
        rows.sort(key=lambda r: r["sort"])
        report, predictions = evaluate(rows, min_history=10, team_window=5)
        self.assertEqual(len(predictions), 20)
        self.assertEqual(report["models"]["league_poisson"]["n"], 20)
        self.assertEqual(report["models"]["rolling_team_rates"]["n"], 20)
        self.assertIn("exact_score_logloss", predictions[0]["models"]["league_poisson"])


if __name__ == "__main__":
    unittest.main()
