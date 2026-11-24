import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from tools import ufi_espn_provider as espn

class ESPNProviderTests(unittest.TestCase):
    def test_scoreboard_normalizer_preserves_home_away_orientation(self):
        event=espn._normalize_event({
            "id":"evt-1","name":"Home at Away","date":"2026-11-25T19:00:00Z",
            "status":{"type":{"name":"STATUS_SCHEDULED","state":"pre","completed":False}},
            "competitions":[{"competitors":[
                {"homeAway":"home","team":{"id":"1","displayName":"Home FC"}},
                {"homeAway":"away","team":{"id":"2","displayName":"Away FC"}}
            ]}]
        })
        self.assertEqual(event["home"]["name"],"Home FC")
        self.assertEqual(event["away"]["name"],"Away FC")
        self.assertEqual(event["event_id"],"evt-1")

    def test_roster_height_parser_accepts_inches_and_display_height(self):
        self.assertEqual(espn._height_cm({"heightInches":72}),182.9)
        self.assertEqual(espn._height_cm({"displayHeight":"6' 2\""}),188.0)
        self.assertIsNone(espn._height_cm({"displayHeight":"unknown"}))

    def test_opponent_adjusted_form_uses_five_completed_matches_and_ppg(self):
        events=[]
        cutoff=datetime.now(timezone.utc)
        for i in range(5):
            dt=(cutoff-timedelta(days=2+i)).isoformat()
            events.append({"date":dt,"status":{"type":{"completed":True}},
                "competitions":[{"competitors":[
                    {"team":{"id":"1","displayName":"Home"},"score":"2"},
                    {"team":{"id":"2","displayName":"Opponent"},"score":"0"}
                ]}]})
        standings={"league_average_ppg":2.0,"entries":[
            {"team_id":"1","ppg":1.5},{"team_id":"2","ppg":3.0}
        ]}
        result=espn._opponent_adjusted_form(events,"1",standings,cutoff)
        self.assertEqual(result["sample_size"],5)
        self.assertEqual(result["raw_points"],15)
        self.assertEqual(result["opponent_adjusted_points"],22.5)

    def test_boxscore_only_confirms_xi_with_eleven_explicit_starters_each(self):
        teams=[];players=[]
        for team_id in ("1","2"):
            athletes=[]
            for i in range(11):
                athletes.append({"athlete":{"id":f"{team_id}-{i}","displayName":f"P{i}"},
                                 "starter":True,"stats":[]})
            players.append({"team":{"id":team_id},"statistics":[{"athletes":athletes}]})
            teams.append({"team":{"id":team_id,"displayName":team_id},"formation":"4-3-3"})
        result=espn._boxscore_summary({"boxscore":{"teams":teams,"players":players}})
        self.assertTrue(result["starting_xi_confirmed"])
        self.assertEqual(result["starter_counts"],{"1":11,"2":11})

    def test_league_map_covers_major_professional_competitions(self):
        self.assertEqual(espn.LEAGUE_MAP["soccer_epl"],"eng.1")
        self.assertEqual(espn.LEAGUE_MAP["soccer_uefa_champs_league"],"uefa.champions")
        self.assertIn("soccer_saudi_pro_league",espn.LEAGUE_MAP)

if __name__=="__main__":
    unittest.main()
