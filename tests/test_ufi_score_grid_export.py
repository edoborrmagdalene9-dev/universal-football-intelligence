import unittest
from datetime import date, timedelta
from tools.ufi_score_models import predict_fixture

class ScoreGridExportTests(unittest.TestCase):
    def test_predict_fixture_exposes_full_fitted_and_fixed_rho_grids(self):
        rows=[]
        start=date(2023,1,1)
        for i in range(180):
            home="Home FC" if i%2==0 else "Away FC"
            away="Away FC" if i%2==0 else "Home FC"
            rows.append({"date":(start+timedelta(days=i)).isoformat(),"home_team":home,"away_team":away,
                         "home_goals":2 if i%3 else 1,"away_goals":1 if i%4 else 0})
        result=predict_fixture(rows,"Home FC","Away FC",cutoff_date="2024-01-01",include_backtest=False)
        self.assertEqual(result["status"],"model_output")
        fitted=result["models"]["dixon_coles"]["score_grid"]
        fixed=result["models"]["dixon_coles_rho_minus_0_10"]["score_grid"]
        self.assertEqual(len(fitted),81)
        self.assertEqual(len(fixed),81)
        self.assertAlmostEqual(sum(x["p"] for x in fitted),1.0,places=8)
        self.assertAlmostEqual(sum(x["p"] for x in fixed),1.0,places=8)
        self.assertEqual(result["models"]["dixon_coles_rho_minus_0_10"]["rho"],-0.10)

if __name__=="__main__":
    unittest.main()
