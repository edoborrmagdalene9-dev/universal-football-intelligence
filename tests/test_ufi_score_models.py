import math
import unittest
from datetime import date, timedelta
from tools import ufi_score_models as model

def synthetic_rows():
    teams=["Alpha","Bravo","Cedar","Delta","Elm","Fjord","Grove","Harbor","Iris","Juniper"]
    rows=[]
    day=date(2023,7,1)
    for season in range(4):
        for i,home in enumerate(teams):
            for j,away in enumerate(teams):
                if i==j:continue
                rows.append({"date":day.isoformat(),"home_team":home,"away_team":away,
                    "home_goals":(i+j+season)%4,"away_goals":(i*2+j+season)%3,
                    "source_url":"https://example.com/results.csv","season":str(season)})
                day+=timedelta(days=1)
    return rows

class ScoreModelsTests(unittest.TestCase):
    def test_poisson_grid_is_normalized(self):
        grid=model._grid(1.4,1.1,0)
        self.assertAlmostEqual(sum(x["p"] for x in grid),1.0,places=10)

    def test_dixon_coles_only_adjusts_low_score_cells(self):
        self.assertNotEqual(model.dixon_coles_tau(0,0,1.4,1.1,0.1),1.0)
        self.assertEqual(model.dixon_coles_tau(2,2,1.4,1.1,0.1),1.0)

    def test_source_backed_prediction_and_chronological_backtest(self):
        rows=synthetic_rows()
        result=model.predict_fixture(rows,"Alpha","Bravo","2027-01-01")
        self.assertEqual(result["status"],"model_output")
        self.assertGreater(result["training_matches"],150)
        for name in ("independent_poisson","dixon_coles"):
            self.assertTrue(result["models"][name]["top_scores"])
            self.assertAlmostEqual(sum(result["models"][name]["one_x_two"]),1.0,places=8)
        backtest=result["historical_backtest"]
        self.assertEqual(backtest["status"],"complete")
        self.assertGreaterEqual(backtest["evaluated_matches"],20)
        self.assertIsNotNone(backtest["metrics"]["team_dixon_coles"]["oneXTwoLogLoss"])
        self.assertEqual(result["market_gate"],"WAIT")

    def test_insufficient_team_history_fails_closed(self):
        rows=synthetic_rows()[:60]
        result=model.predict_fixture(rows,"Unknown Home","Unknown Away","2027-01-01")
        self.assertEqual(result["status"],"NEEDS_DATA")
        self.assertEqual(result["market_gate"],"WAIT")

if __name__=="__main__":unittest.main()
