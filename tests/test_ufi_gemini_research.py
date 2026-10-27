import os
import unittest
from unittest.mock import patch

from tools.ufi_gemini_research import (
    evaluate_market_blacklist,
    extract_research_brief,
    gemini_configured,
)


class FakeStore:
    def blacklist_reasons(self, team, market, competition=""):
        if team == "North City" and market == "correct_score":
            return ["North City blacklisted (correct_score): test rule"]
        return []


class GeminiResearchTests(unittest.TestCase):
    def test_missing_sources_fails_closed_without_api_call(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            result = extract_research_brief("Check injuries", [])
        self.assertEqual(result["status"], "NEEDS_DATA")
        self.assertEqual(result["claims"], [])

    def test_missing_key_returns_needs_data(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(gemini_configured())
            result = extract_research_brief("Check injuries", [{"source_url": "https://example.com"}])
        self.assertEqual(result["status"], "NEEDS_DATA")

    def test_market_blacklist_does_not_spill_to_other_market(self):
        fixture = {"id": "f1", "home": "North City", "away": "South Town"}
        correct = evaluate_market_blacklist(FakeStore(), fixture, "correct_score")
        corners = evaluate_market_blacklist(FakeStore(), fixture, "corners")
        self.assertEqual(correct["status"], "CUT")
        self.assertEqual(corners["status"], "SURVIVOR_PENDING_OTHER_GATES")

    def test_incomplete_fixture_fails_closed(self):
        result = evaluate_market_blacklist(FakeStore(), {"id": "f2", "home": "", "away": ""}, "corners")
        self.assertEqual(result["status"], "CUT")
        self.assertTrue(result["reasons"])


if __name__ == "__main__":
    unittest.main()
