import unittest
from unittest.mock import patch

from tools import ufi_prediction_api


class PredictionApiTests(unittest.TestCase):
    def test_requires_home_and_away(self):
        with self.assertRaisesRegex(ValueError, "home and away must be supplied"):
            ufi_prediction_api.generate_score_prediction({"league": ["E0"]})

    def test_rejects_unknown_league(self):
        with self.assertRaisesRegex(ValueError, "league must be a supported"):
            ufi_prediction_api.generate_score_prediction({
                "home": ["Arsenal"], "away": ["Chelsea"], "league": ["NOPE"]
            })

    def test_invalid_cutoff_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "cutoff_date must be YYYY-MM-DD"):
            ufi_prediction_api.generate_score_prediction({
                "home": ["Arsenal"], "away": ["Chelsea"], "league": ["E0"],
                "cutoff_date": ["not-a-date"]
            })

    @patch("tools.ufi_prediction_api.predict_fixture")
    @patch("tools.ufi_prediction_api._historical_data")
    def test_returns_existing_model_output_and_keeps_market_gate_closed(self, historical, predict):
        historical.return_value = {
            "source": "Football-Data.co.uk public historical results",
            "fetched_at": "2026-10-28T00:00:00+00:00",
            "record_count": 120, "seasons_loaded": ["2526"], "source_urls": ["https://example.invalid/E0.csv"],
            "issues": [], "data": [{"date": "2026-01-01"}], "cache_hit": False
        }
        predict.return_value = {
            "status": "model_output", "market_gate": "WAIT",
            "models": {"independent_poisson": {"top_scores": [{"home": 1, "away": 0, "p": 0.2}]}}
        }
        result = ufi_prediction_api.generate_score_prediction({
            "home": ["Arsenal"], "away": ["Chelsea"], "league": ["E0"],
            "seasons": ["5"], "cutoff_date": ["2026-10-28"]
        })
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "model_output")
        self.assertEqual(result["market_gate"], "WAIT")
        self.assertEqual(result["model"]["models"]["independent_poisson"]["top_scores"][0]["home"], 1)
        historical.assert_called_once_with("E0", 5)
        predict.assert_called_once()

    @patch("tools.ufi_prediction_api.predict_fixture")
    @patch("tools.ufi_prediction_api._historical_data")
    def test_insufficient_history_is_reported_without_fake_prediction(self, historical, predict):
        historical.return_value = {
            "source": "Football-Data.co.uk public historical results",
            "fetched_at": None, "record_count": 12, "seasons_loaded": [],
            "source_urls": [], "issues": [], "data": [], "cache_hit": False
        }
        predict.return_value = {
            "status": "NEEDS_DATA", "market_gate": "WAIT", "predictions": [],
            "reason": "Fewer than 50 prior league results."
        }
        result = ufi_prediction_api.generate_score_prediction({
            "home": ["Unknown FC"], "away": ["Other FC"], "league": ["E0"]
        })
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "NEEDS_DATA")
        self.assertEqual(result["model"]["predictions"], [])
        self.assertEqual(result["market_gate"], "WAIT")


if __name__ == "__main__":
    unittest.main()
