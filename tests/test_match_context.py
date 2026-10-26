import unittest
from tools.ufi_match_context import normalize_provider_payload

class MatchContextTests(unittest.TestCase):
    def test_sgo_normalization_keeps_unknowns_unknown(self):
        rows=normalize_provider_payload("SportsGameOdds", {"data":[{"eventID":"evt-1","sportID":"SOCCER","leagueID":"EPL","teams":{"home":{"name":"Home FC"},"away":{"name":"Away FC"}},"status":{"startsAt":"2026-10-27T18:00:00Z","started":False}}]}, 123.0)
        self.assertEqual(len(rows),1)
        row=rows[0]
        self.assertEqual(row["homeTeam"],"Home FC")
        self.assertEqual(row["awayTeam"],"Away FC")
        self.assertIsNone(row["score"])
        self.assertFalse(row["quality"]["hasScore"])
        self.assertEqual(row["timestamps"]["fetchedAt"],123.0)

    def test_odds_api_marks_event_as_odds_only(self):
        rows=normalize_provider_payload("The Odds API", [{"id":"abc","sport_key":"soccer_epl","commence_time":"2026-10-27T18:00:00Z","home_team":"Home FC","away_team":"Away FC","bookmakers":[]}], 456.0)
        self.assertEqual(rows[0]["fixtureId"],"abc")
        self.assertTrue(rows[0]["quality"]["oddsOnlySource"])
        self.assertIsNone(rows[0]["score"])
        self.assertIsNone(rows[0]["lineups"])

if __name__ == "__main__":
    unittest.main()
