import unittest
from unittest.mock import Mock

from tools.ufi_end_to_end_pipeline import generate_fixture_pipeline


class EndToEndPipelineTests(unittest.TestCase):
    def setUp(self):
        self.fixture = {
            "source": "Sportmonks",
            "fetchedAt": "2026-10-28T07:00:00Z",
            "data": {"data": {
                "id": 19722758,
                "name": "St. Mirren vs Hibernian",
                "starting_at": "2026-10-28 19:45:00",
                "league_id": 501,
                "participants": [
                    {"name": "Hibernian", "meta": {"location": "away"}},
                    {"name": "St. Mirren", "meta": {"location": "home"}},
                ],
                "events": [],
                "lineups": [{"player_name": "Known"}],
                "statistics": [],
                "referees": [{"id": 1}],
                "scores": [],
                "venue": {"latitude": "55.85", "longitude": "-4.44"},
            }},
        }
        self.loader = Mock(return_value=(self.fixture, False))
        self.predictor = Mock(return_value={
            "ok": True, "status": "model_output", "market_gate": "WAIT",
            "models": {"independent_poisson": {"top_scores": [{"home": 1, "away": 0, "p": 0.2}]}},
        })

    def test_real_fixture_fields_flow_to_score_model_and_market_stays_wait(self):
        result = generate_fixture_pipeline(
            {"fixture_id": ["19722758"], "league": ["SC0"], "seasons": ["3"]},
            self.loader, self.predictor,
        )
        self.loader.assert_called_once_with("/api/fixture", {"id": ["19722758"]})
        self.predictor.assert_called_once_with({
            "home": ["St. Mirren"], "away": ["Hibernian"], "league": ["SC0"],
            "seasons": ["3"], "cutoff_date": ["2026-10-28"],
        })
        self.assertEqual(result["pipeline_status"], "model_ready_market_wait")
        self.assertEqual(result["fixture_source"]["provider"], "Sportmonks")
        self.assertTrue(result["match_context"]["lineups"]["available"])
        self.assertFalse(result["match_context"]["events"]["available"])
        self.assertEqual(result["market_gate"], "WAIT")
        self.assertEqual(result["stages"]["player_and_tactical_feature_join"], "WAIT")

    def test_missing_fixture_id_rejected(self):
        with self.assertRaisesRegex(ValueError, "numeric provider fixture ID"):
            generate_fixture_pipeline({"league": ["E0"]}, self.loader, self.predictor)

    def test_missing_league_code_rejected_instead_of_guessing_competition_mapping(self):
        with self.assertRaisesRegex(ValueError, "league is required"):
            generate_fixture_pipeline({"fixture_id": ["19722758"]}, self.loader, self.predictor)

    def test_provider_payload_without_requested_fixture_is_rejected(self):
        self.loader.return_value = ({"source": "Sportmonks", "data": {"data": []}}, False)
        with self.assertRaisesRegex(ValueError, "did not contain the requested fixture"):
            generate_fixture_pipeline(
                {"fixture_id": ["19722758"], "league": ["SC0"]}, self.loader, self.predictor
            )

    def test_needs_data_is_not_promoted_to_model_ready(self):
        self.predictor.return_value = {"status": "NEEDS_DATA", "models": {}}
        result = generate_fixture_pipeline(
            {"fixture_id": ["19722758"], "league": ["SC0"]}, self.loader, self.predictor
        )
        self.assertEqual(result["pipeline_status"], "needs_data")
        self.assertEqual(result["market_gate"], "WAIT")


if __name__ == "__main__":
    unittest.main()
