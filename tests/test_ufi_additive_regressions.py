"""Additive regression tests for UFI's existing multi-provider backend.

These tests mock network calls: they validate routing and data-contract safety
without consuming provider quota or requiring API keys.
"""
import os
import sys
import unittest
from io import BytesIO
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import ufi_provider_adapters as adapters
import ufi_live_data_proxy as legacy
import ufi_multi_provider_server as server


class MatchNormalizationTests(unittest.TestCase):
    def test_odds_only_source_does_not_fabricate_score_or_lineups(self):
        rows = adapters.normalize_provider_payload(
            "The Odds API",
            [{"id": "fixture-1", "sport_key": "soccer_test",
              "sport_title": "Test League", "commence_time": "2026-10-27T18:00:00Z",
              "home_team": "Home FC", "away_team": "Away FC",
              "bookmakers": []}],
            "2026-10-26T00:00:00Z",
        )
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["homeTeam"], "Home FC")
        self.assertEqual(row["awayTeam"], "Away FC")
        self.assertIsNone(row["score"])
        self.assertIsNone(row["lineups"])
        self.assertIsNone(row["events"])
        self.assertIsNone(row["statistics"])
        self.assertTrue(row["quality"]["oddsOnlySource"])

    def test_sgo_normalizer_preserves_unknowns_and_reports_missing_fields(self):
        rows = adapters.normalize_provider_payload(
            "SportsGameOdds",
            {"data": [{"eventID": "sgo-1", "teams": {
                "home": {"name": "Home FC"}, "away": {"name": "Away FC"}}}]},
        )
        self.assertEqual(rows[0]["fixtureId"], "sgo-1")
        self.assertIsNone(rows[0]["score"])
        self.assertIn("kickoff", rows[0]["quality"]["missingRequiredFields"])
        self.assertFalse(rows[0]["quality"]["hasScore"])


class ProviderErrorSanitizationTests(unittest.TestCase):
    def test_boolean_error_payload_does_not_become_misleading_message(self):
        http_error = adapters.urllib.error.HTTPError(
            "https://provider.invalid/private?key=not-for-logs", 429, "Too Many Requests",
            {}, BytesIO(b'{"error":true}'))
        with patch.object(adapters.urllib.request, "urlopen", side_effect=http_error):
            with self.assertRaises(adapters.AdapterError) as caught:
                adapters._get_json("https://provider.invalid/private?key=not-for-logs")
        self.assertIn("HTTP 429", str(caught.exception))
        self.assertNotIn("True", str(caught.exception))
        self.assertNotIn("not-for-logs", str(caught.exception))


class ArithmeticTests(unittest.TestCase):
    def test_ev_is_transparent_and_correct(self):
        result = adapters.calculate_ev({"probability": ["0.25"], "odds": ["4.5"]})
        self.assertAlmostEqual(result["expectedReturnPerUnit"], 0.125)
        self.assertAlmostEqual(result["breakEvenProbability"], 1 / 4.5)
        self.assertIn("not a profit guarantee", result["warning"])

    def test_ev_rejects_probability_outside_range(self):
        with self.assertRaises(adapters.AdapterError):
            adapters.calculate_ev({"probability": ["1.2"], "odds": ["2.0"]})

    def test_arbitrage_detects_only_complete_price_sets_mathematically(self):
        result = adapters.calculate_arbitrage({"odds": ["2.2, 3.8, 4.0"]})
        self.assertTrue(result["arbitrageDetected"])
        self.assertAlmostEqual(sum(result["equalPayoutStakeFractions"]), 1.0)
        self.assertIn("settlement rules", result["warning"])

    def test_arbitrage_rejects_invalid_decimal_odds(self):
        with self.assertRaises(adapters.AdapterError):
            adapters.calculate_arbitrage({"odds": ["2.0,1.0"]})


class EmptyPrimaryFeedFallbackTests(unittest.TestCase):
    def test_empty_live_feed_uses_only_provider_marked_live_events(self):
        live_event = {
            "eventID": "live-1",
            "teams": {"home": {"name": "Home FC"}, "away": {"name": "Away FC"}},
            "status": {"startsAt": "2026-10-26T20:00:00Z", "started": True},
        }
        empty_sportmonks = {"source": "Sportmonks", "data": {"data": [], "message": "No results"}}
        sgo_response = {"source": "SportsGameOdds", "fetchedAt": "2026-10-26T20:00:00Z",
                        "cacheHit": False, "data": {"data": [live_event]}}
        with patch.object(server, "_original_get_payload", return_value=(empty_sportmonks, True)), \
             patch.object(adapters, "handle_extra_route", return_value=None), \
             patch.object(adapters, "_sgo_events", return_value=sgo_response) as mock_sgo:
            result, cache_hit = server._integrated_get_payload("/api/live", {})
        self.assertFalse(cache_hit)
        self.assertTrue(result["fallbackUsed"])
        self.assertEqual(result["source"], "SportsGameOdds")
        self.assertEqual(result["recordCount"], 1)
        self.assertEqual(result["data"][0]["fixtureId"], "live-1")
        self.assertEqual(mock_sgo.call_args.args[0]["live"], ["true"])
        self.assertEqual(mock_sgo.call_args.args[0]["started"], ["true"])

    def test_empty_date_feed_uses_odds_fallback_and_filters_to_requested_date(self):
        events = [
            {"id": "in-date", "sport_key": "soccer_epl", "commence_time": "2026-10-27T18:00:00Z",
             "home_team": "Home FC", "away_team": "Away FC", "bookmakers": []},
            {"id": "wrong-date", "sport_key": "soccer_epl", "commence_time": "2026-10-28T18:00:00Z",
             "home_team": "Other Home", "away_team": "Other Away", "bookmakers": []},
        ]
        empty_sportmonks = {"source": "Sportmonks", "data": {"data": [], "message": "No results"}}
        odds_response = {"source": "The Odds API", "fetchedAt": 1793133600,
                         "cacheHit": False, "data": events}
        with patch.object(server, "_original_get_payload", return_value=(empty_sportmonks, True)), \
             patch.object(adapters, "handle_extra_route", return_value=None), \
             patch.object(adapters, "_odds_api", return_value=odds_response) as mock_odds:
            result, cache_hit = server._integrated_get_payload(
                "/api/fixtures", {"date": ["2026-10-27"]})
        self.assertFalse(cache_hit)
        self.assertTrue(result["fallbackUsed"])
        self.assertEqual(result["source"], "The Odds API")
        self.assertEqual(result["recordCount"], 1)
        self.assertEqual(result["data"][0]["fixtureId"], "in-date")
        self.assertIsNone(result["data"][0]["score"])
        self.assertIsNone(result["data"][0]["lineups"])
        self.assertEqual(mock_odds.call_args.args[1]["from"], ["2026-10-27T00:00:00Z"])
        self.assertEqual(mock_odds.call_args.args[1]["to"], ["2026-10-28T00:00:00Z"])


class RoutingAndSecretSafetyTests(unittest.TestCase):
    def test_provider_status_never_returns_secret_values(self):
        with patch.dict(os.environ, {
            "SPORTSGAMEODDS_API_KEY": "TEST-SHOULD-NOT-LEAK",
            "THE_ODDS_API_KEY": "TEST-SHOULD-NOT-LEAK-2",
            "SHARPAPI_KEY": "",
            "WEATHERAPI_KEY": "",
        }, clear=False):
            payload, _ = server._integrated_get_payload("/api/providers/status", {})
        rendered = str(payload)
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["secretValuesReturned"])
        self.assertNotIn("TEST-SHOULD-NOT-LEAK", rendered)
        self.assertIn("sportsGameOdds", payload["providers"])

    def test_original_health_route_is_preserved(self):
        payload, _ = server._integrated_get_payload("/api/health", {})
        self.assertTrue(payload["ok"])
        self.assertIn("tokenConfigured", payload)

    def test_unknown_route_keeps_legacy_error_contract(self):
        with self.assertRaises(legacy.ProviderError):
            server._integrated_get_payload("/api/does-not-exist", {})

    def test_matches_route_fails_clearly_without_keys(self):
        with patch.dict(os.environ, {
            "SPORTSGAMEODDS_API_KEY": "",
            "THE_ODDS_API_KEY": "",
        }, clear=False):
            with self.assertRaises(adapters.AdapterError) as caught:
                adapters.handle_extra_route("/api/matches", {})
        self.assertIn("Configure", str(caught.exception))
        self.assertNotIn("apiKey", str(caught.exception))

    def test_normalized_match_feed_requests_a_batch_by_default(self):
        event_rows = [
            {"eventID": "one", "teams": {"home": {"name": "Home A"},
             "away": {"name": "Away A"}}, "status": {"startsAt": "2026-10-28T18:00:00Z"}},
            {"eventID": "two", "teams": {"home": {"name": "Home B"},
             "away": {"name": "Away B"}}, "status": {"startsAt": "2026-10-28T19:00:00Z"}},
        ]
        provider_result = {"source": "SportsGameOdds", "fetchedAt": "2026-10-26T00:00:00Z",
                           "cacheHit": False, "data": {"data": event_rows}}
        with patch.dict(os.environ, {"SPORTSGAMEODDS_API_KEY": "test-key"}, clear=False), \
             patch.object(adapters, "_sgo_events", return_value=provider_result) as mock_sgo:
            result = adapters._normalized_matches({})
        self.assertEqual(mock_sgo.call_args.args[0]["limit"], ["50"])
        self.assertEqual(result["recordCount"], 2)
        self.assertEqual([row["fixtureId"] for row in result["data"]], ["one", "two"])

    def test_weather_fallback_uses_requested_hour_not_current_conditions(self):
        weatherapi_payload = {
            "location": {"name": "Berlin", "tz_id": "Europe/Berlin"},
            "forecast": {"forecastday": [{
                "date": "2026-10-27",
                "hour": [
                    {"time": "2026-10-27 14:00", "temp_c": 20, "humidity": 70,
                     "precip_mm": 0.1, "chance_of_rain": 15, "wind_kph": 8},
                    {"time": "2026-10-27 15:00", "temp_c": 21, "humidity": 65,
                     "precip_mm": 0.2, "chance_of_rain": 25, "wind_kph": 9},
                ],
            }]},
        }
        def fake_extra(route, query):
            if route == "/api/weather":
                return None
            if route == "/api/weather/weatherapi":
                return {"source": "WeatherAPI.com", "fetchedAt": 1,
                        "data": weatherapi_payload}, False
            return None
        with patch.dict(os.environ, {"WEATHERAPI_KEY": "test-key"}, clear=False), \
             patch.object(server, "_original_get_payload",
                          side_effect=legacy.ProviderError("Open-Meteo unavailable")), \
             patch.object(adapters, "handle_extra_route", side_effect=fake_extra):
            result, cache_hit = server._integrated_get_payload(
                "/api/weather", {"lat": ["51.5"], "lon": ["-0.1"],
                                 "date": ["2026-10-27"], "hour": ["14"]})
        self.assertFalse(cache_hit)
        self.assertTrue(result["fallbackUsed"])
        self.assertEqual(result["matchedLocalTime"], "2026-10-27 15:00")
        self.assertEqual(result["weather"]["temperatureC"], 21)
        self.assertEqual(result["weather"]["precipitationProbabilityPct"], 25)
        self.assertNotIn("current conditions", result["note"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
