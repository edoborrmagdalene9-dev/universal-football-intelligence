import unittest
from unittest.mock import patch
from tools import ufi_provider_adapters as adapters

class ScoreModelRouteTests(unittest.TestCase):
    def test_score_route_requires_fixture_and_league(self):
        with self.assertRaises(adapters.AdapterError):
            adapters.handle_extra_route("/api/models/score",{"home":["Alpha"],"away":["Bravo"]})

    def test_score_route_uses_historical_data_and_model_output(self):
        history={"data":[{"date":"2025-01-01","home_team":"Alpha","away_team":"Bravo","home_goals":2,"away_goals":1}],
                 "source":"Football-Data.co.uk public historical results","source_urls":["https://example.com/results.csv"],
                 "fetched_at":"2026-10-27T15:30:00Z","record_count":1}
        prediction={"status":"model_output","training_matches":1,"rate_estimate":{"lambdaHome":1.2,"lambdaAway":0.9},
                    "models":{"independent_poisson":{"top_scores":[],"one_x_two":[0.4,0.3,0.3]}},
                    "historical_backtest":{"status":"NEEDS_DATA"},"market_gate":"WAIT"}
        with patch("tools.ufi_historical_results.load_football_data_results",return_value=history):
            with patch("tools.ufi_score_models.predict_fixture",return_value=prediction) as predict:
                result,_=adapters.handle_extra_route("/api/models/score",{"home":["Alpha"],"away":["Bravo"],"league":["SC0"],"date":["2026-10-28"],"seasons":["5"]})
        self.assertTrue(result["ok"])
        self.assertEqual(result["league_code"],"SC0")
        self.assertEqual(result["market_gate"],"WAIT")
        self.assertEqual(predict.call_args.args[0],history["data"])

if __name__=="__main__":unittest.main()
