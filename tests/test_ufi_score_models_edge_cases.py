import unittest
from tools import ufi_score_models as model

class ScoreModelEdgeCaseTests(unittest.TestCase):
    def test_future_and_same_day_rows_never_enter_training(self):
        rows=[{"date":"2026-10-28","home_team":"Alpha","away_team":"Bravo","home_goals":2,"away_goals":1},
              {"date":"2026-10-29","home_team":"Bravo","away_team":"Alpha","home_goals":0,"away_goals":0}]
        result=model.predict_fixture(rows,"Alpha","Bravo","2026-10-28")
        self.assertEqual(result["status"],"NEEDS_DATA")
        self.assertEqual(result["training_matches"],0)
        self.assertEqual(result["market_gate"],"WAIT")
        self.assertEqual(result["predictions"],[])

    def test_rho_is_not_fit_on_tiny_samples(self):
        rows=[{"date":"2026-01-01","home_team":"Alpha","away_team":"Bravo","home_goals":1,"away_goals":0}]
        result=model.fit_rho(rows)
        self.assertEqual(result["rho"],0.0)
        self.assertFalse(result["fitted"])

    def test_poisson_probability_is_bounded_and_finite(self):
        for lam in (0.05,0.8,2.5,5.0):
            p=model.poisson_pmf(2,lam)
            self.assertGreaterEqual(p,0.0)
            self.assertLessEqual(p,1.0)

if __name__=="__main__":unittest.main()
