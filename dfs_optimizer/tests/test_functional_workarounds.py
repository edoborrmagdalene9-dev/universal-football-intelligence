import unittest
from dfs_optimizer.src.ownership_workarounds import sample_opponent_lineups, empirical_joint_summary
from dfs_optimizer.src.event_simulator import simulate_event_points
from dfs_optimizer.src.continuous_time_states import simulate_score_path, estimate_goal_rates
from dfs_optimizer.src.contest_simulator import evaluate_contest
from dfs_optimizer.src.optimizer_fallback import exhaustive_binary_optimizer


class FunctionalWorkaroundTests(unittest.TestCase):
    def test_joint_ownership_bootstrap_and_fallback(self):
        rows, meta = sample_opponent_lineups(20, entries=[["a", "b"], ["a", "c"]], seed=2)
        self.assertEqual(len(rows), 20)
        self.assertEqual(meta["mode"], "empirical-lineup-bootstrap")
        self.assertAlmostEqual(empirical_joint_summary([["a", "b"], ["a", "c"]])["player_ownership"]["a"], 1.0)
        rows, meta = sample_opponent_lineups(2, player_ownership={"a": 1, "b": 1}, roster_size=1, seed=1)
        self.assertEqual(meta["mode"], "marginal-ownership-baseline")

    def test_event_simulator_quantiles(self):
        out = simulate_event_points({"p": {"shots": 2, "points": {"shots": 3}}}, n_sims=200, seed=1)
        self.assertEqual(len(out["player_points"]["p"]), 200)
        self.assertGreaterEqual(out["summary"]["p"]["p99"], out["summary"]["p"]["p50"])

    def test_continuous_time_simulator_and_rates(self):
        out = simulate_score_path(1.2, 0.8, seed=3)
        self.assertIn("home_goals", out)
        rates = estimate_goal_rates([{"home_goals": 2, "away_goals": 1}])
        self.assertEqual(rates["matches"], 1)

    def test_payout_ties_split(self):
        out = evaluate_contest([10], [10, 8], {1: 100, 2: 40})
        self.assertEqual(out["results"][0]["rank"], 1)
        self.assertEqual(out["results"][0]["payout"], 70)

    def test_exact_optimizer(self):
        out = exhaustive_binary_optimizer(
            {"a": 10, "b": 8, "c": 7},
            {(p, q): 0.0 for p in "abc" for q in "abc"},
            {"a": 5, "b": 4, "c": 3}, 8, 2, variance_weight=0)
        self.assertEqual(set(out["lineup"]), {"a", "c"})


if __name__ == "__main__":
    unittest.main()
