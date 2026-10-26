"""Additive regression tests for UFI's existing multi-provider backend.

These tests mock network calls: they validate routing and data-contract safety
without consuming provider quota or requiring API keys.
"""
import os
import sys
import unittest
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
