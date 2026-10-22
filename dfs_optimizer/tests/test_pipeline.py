import io
import unittest
from dfs_optimizer.src.pipeline import load_matches_csv, chronological_backtest, validate_contest_entries_csv

def make_matches(n=60):
    rows=[]
    for i in range(n):
        rows.append({"date": f"2020-{1+i//28:02d}-{1+i%28:02d}", "home_team":"A" if i%2 else "C",
                     "away_team":"B" if i%2 else "D","home_goals":i%4,"away_goals":(i+1)%3})
    return rows

class PipelineTests(unittest.TestCase):
    def test_match_validation_and_duplicate(self):
        csv_data="date,home_team,away_team,home_goals,away_goals\n2024-01-01,A,B,1,0\n2024-01-01,A,B,1,0\n2024-01-02,C,D,-1,0\n"
        out=load_matches_csv(io.StringIO(csv_data))
        self.assertEqual(out["rows_valid"],1)
        self.assertEqual(out["rows_rejected"],1)
        self.assertTrue(any(x["severity"]=="warning" for x in out["issues"]))
    def test_backtest_is_chronological_and_reports_holdout(self):
        out=chronological_backtest(make_matches(),min_train=30)
        self.assertEqual(out["rows"],60)
        self.assertGreater(out["test_metrics"]["matches"],0)
        self.assertLess(out["split_indices"]["train_end_exclusive"],out["split_indices"]["validation_end_exclusive"])
        self.assertIn("mean_brier_score",out["test_metrics"])
    def test_contest_entries_ownership(self):
        out=validate_contest_entries_csv(io.StringIO("entry_id,players\n1,a|b|c\n2,a|c|d\n"))
        self.assertEqual(out["entry_count"],2)
        self.assertEqual(out["player_ownership"]["a"],1.0)
        self.assertEqual(out["pair_counts"]["a + c"],2)

if __name__=="__main__": unittest.main()
