import os
import unittest
from unittest.mock import patch
from tools import ufi_provider_adapters as adapters

class ProviderAdapterTests(unittest.TestCase):
    def test_status_never_returns_secrets(self):
        with patch.dict(os.environ, {"SHARPAPI_KEY":"secret-test-value","WEATHERAPI_KEY":""}, clear=False):
            payload, hit = adapters.handle_extra_route("/api/providers/status", {})
        self.assertFalse(hit)
        self.assertTrue(payload["providers"]["sharpapi"]["configured"])
        self.assertFalse(payload["providers"]["weatherapi"]["configured"])
        self.assertNotIn("secret-test-value", str(payload))

    def test_expected_value_and_break_even(self):
        result = adapters.calculate_ev({"probability":["0.25"],"odds":["4"]})
        self.assertEqual(result["expectedReturnPerUnit"], 0)
        self.assertEqual(result["breakEvenProbability"], 0.25)

    def test_arbitrage_detected_only_when_implied_sum_below_one(self):
        yes = adapters.calculate_arbitrage({"odds":["2.2,4.0,4.0"]})
        no = adapters.calculate_arbitrage({"odds":["2.0,3.0,3.0"]})
        self.assertTrue(yes["arbitrageDetected"])
        self.assertFalse(no["arbitrageDetected"])
        self.assertAlmostEqual(sum(yes["equalPayoutStakeFractions"]), 1.0)

    def test_invalid_odds_rejected(self):
        with self.assertRaises(adapters.AdapterError):
            adapters.calculate_ev({"probability":["1.2"],"odds":["2"]})
        with self.assertRaises(adapters.AdapterError):
            adapters.calculate_arbitrage({"odds":["1.0,2.0"]})


    def test_health_route_reports_missing_keys_without_networking(self):
        adapters._CACHE.clear()
        with patch.dict(os.environ, {}, clear=True), patch.object(adapters, "_get_json", return_value=({"current":{"temperature_2m":30}},{})):
            payload, hit = adapters.handle_extra_route("/api/providers/health", {"providers":["sportsgameodds,theoddsapi,weatherapi,sharpapi,openmeteo"]})
        self.assertFalse(hit)
        self.assertFalse(payload["checks"]["sportsgameodds"]["reachable"])
        self.assertEqual(payload["checks"]["theoddsapi"]["status"], "not-configured")
        self.assertTrue(payload["checks"]["openmeteo"]["reachable"])
        self.assertNotIn("apiKey", str(payload))

    def test_health_probe_uses_provider_adapter_and_does_not_echo_key(self):
        adapters._CACHE.clear()
        with patch.dict(os.environ, {"SPORTSGAMEODDS_API_KEY":"dummy-test-secret"}, clear=False), patch.object(adapters, "_sgo_events", return_value={"source":"SportsGameOdds","data":[{"eventID":"fixture-1"}]}):
            payload, hit = adapters.handle_extra_route("/api/providers/health", {"provider":["sportsgameodds"]})
        self.assertTrue(payload["checks"]["sportsgameodds"]["reachable"])
        self.assertNotIn("dummy-test-secret", str(payload))

if __name__ == "__main__":
    unittest.main()
