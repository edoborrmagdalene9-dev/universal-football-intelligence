import os
import unittest
from unittest.mock import patch

from tools import ufi_provider_adapters as adapters


class GeminiRouteTests(unittest.TestCase):
    def test_status_never_exposes_key(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-secret", "GEMINI_MODEL": "gemini-2.5-flash"}):
            payload, cache_hit = adapters.handle_extra_route("/api/gemini/status", {})
        self.assertFalse(cache_hit)
        self.assertTrue(payload["configured"])
        self.assertNotIn("test-secret", repr(payload))

    def test_research_without_sources_fails_closed(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-secret"}):
            payload, _ = adapters.handle_extra_route(
                "/api/gemini/research", {"question": ["Check team news"]}
            )
        self.assertEqual(payload["status"], "NEEDS_DATA")
        self.assertEqual(payload["claims"], [])

    def test_research_rejects_invalid_source_json(self):
        with self.assertRaises(adapters.AdapterError):
            adapters.handle_extra_route(
                "/api/gemini/research",
                {"question": ["Check team news"], "source_material": ["not-json"]}
            )

    def test_unknown_routes_remain_unchanged(self):
        self.assertIsNone(adapters.handle_extra_route("/api/not-a-real-route", {}))


if __name__ == "__main__":
    unittest.main()
