import os
import unittest
from unittest.mock import patch
from tools import ufi_provider_adapters as adapters

class NormalizedProviderAggregationTests(unittest.TestCase):
    def test_aggregates_sgo_and_multiple_odds_sports_and_deduplicates(self):
        sgo_rows=[{
            "fixtureId":"sgo-1","kickoff":"2026-11-25T19:00:00Z",
            "homeTeam":"Team A","awayTeam":"Team B","odds":{"h2h":{"home":2.1}},
            "sources":{"fixture":"SportsGameOdds"}
        }]
        odds_epl=[
            {"fixtureId":"odds-1","kickoff":"2026-11-25T19:00:00Z",
             "homeTeam":"Team A","awayTeam":"Team B","odds":{"h2h":{"away":3.4}},
             "sources":{"odds":"The Odds API"}},
            {"fixtureId":"odds-2","kickoff":"2026-11-26T20:00:00Z",
             "homeTeam":"Team C","awayTeam":"Team D","odds":{},
             "sources":{"odds":"The Odds API"}}
        ]
        odds_mls=[]
        def normalize(provider,payload,fetched_at):
            if provider=="SportsGameOdds": return sgo_rows
            if payload=="epl": return odds_epl
            if payload=="mls": return odds_mls
            return []
        with patch.dict(os.environ,{"SPORTSGAMEODDS_API_KEY":"test","THE_ODDS_API_KEY":"test"}), \
             patch.object(adapters,"_sgo_events",return_value={"data":"sgo","fetchedAt":1}), \
             patch.object(adapters,"_odds_api",side_effect=[
                 {"data":"epl","fetchedAt":2},{"data":"mls","fetchedAt":3}
             ]) as odds_call, \
             patch.object(adapters,"normalize_provider_payload",side_effect=normalize):
            result=adapters._normalized_matches({"sports":["soccer_epl,soccer_usa_mls"]})
        self.assertEqual(result["source"],"multi-provider")
        self.assertEqual(result["recordCount"],2)
        self.assertEqual(result["providerRecordCounts"]["SportsGameOdds"],1)
        self.assertEqual(result["providerRecordCounts"]["The Odds API:soccer_epl"],2)
        self.assertEqual(result["providerRecordCounts"]["The Odds API:soccer_usa_mls"],0)
        self.assertEqual(result["requestedSports"],["soccer_epl","soccer_usa_mls"])
        self.assertEqual(odds_call.call_count,2)
        merged=next(x for x in result["data"] if x["homeTeam"]=="Team A")
        self.assertIn("h2h",merged["odds"])
        self.assertEqual(merged["sources"]["fixture"],"SportsGameOdds")
        self.assertEqual(merged["sources"]["odds"],"The Odds API")

    def test_odds_api_unwraps_json_and_captures_quota_headers(self):
        payload=[{"id":"evt-1","home_team":"Home","away_team":"Away",
                  "commence_time":"2026-11-25T19:00:00Z","sport_key":"soccer_epl",
                  "sport_title":"EPL","bookmakers":[]}]
        headers={"X-Requests-Remaining":"498","X-Requests-Used":"2","X-Requests-Last":"1"}
        with patch.dict(os.environ,{"THE_ODDS_API_KEY":"test"},clear=False), \
             patch.object(adapters,"_get_json",return_value=(payload,headers)), \
             patch.object(adapters,"_cached",side_effect=lambda key,ttl,fn:(fn(),False)):
            result=adapters._odds_api("soccer_epl",{"regions":["uk"],"markets":["h2h"]})
        self.assertEqual(result["data"],payload)
        self.assertEqual(result["quota"]["remaining"],498)
        self.assertEqual(result["quota"]["used"],2)

    def test_odds_api_sports_catalog_returns_only_soccer_keys_without_secret(self):
        payload=[
            {"key":"soccer_epl","title":"EPL","group":"Soccer","active":True},
            {"key":"basketball_nba","title":"NBA","group":"Basketball","active":True},
            {"key":"soccer_test","title":"Test League","group":"Soccer","active":False},
        ]
        with patch.dict(os.environ,{"THE_ODDS_API_KEY":"private-test-key"},clear=False), \
             patch.object(adapters,"_get_json",return_value=(payload,{"X-Requests-Remaining":"90"})), \
             patch.object(adapters,"_cached",side_effect=lambda key,ttl,fn:(fn(),False)):
            result=adapters._odds_sports_catalog()
        self.assertEqual([x["key"] for x in result["sports"]],["soccer_epl","soccer_test"])
        self.assertEqual(result["quota"]["remaining"],90)
        self.assertNotIn("private-test-key",str(result))

    def test_sportmonks_health_probe_checks_api_catalog_without_exposing_token(self):
        with patch.dict(os.environ,{"SPORTMONKS_API_TOKEN":"private-test-token"},clear=False), \
             patch.object(adapters,"_get_json",return_value=({"data":[{"id":1}]},{})) as request:
            result=adapters._provider_health({"providers":["sportmonks"]})
        self.assertTrue(result["checks"]["sportmonks"]["reachable"])
        self.assertEqual(result["checks"]["sportmonks"]["catalogRecords"],1)
        self.assertNotIn("private-test-token",str(result))

    def test_sportmonks_lineup_context_merges_with_odds_event(self):
        sportmonks=[{
            "fixtureId":12345,"kickoff":"2026-11-25T19:00:00Z","homeTeam":"Team A","awayTeam":"Team B",
            "lineups":[{"player_id":10,"position_id":1}],"statistics":[{"type":"shots","value":12}],
            "referees":[{"id":4}],"venue":{"latitude":51.5,"longitude":-0.1},
            "sources":{"fixture":"Sportmonks"},"providerSources":["Sportmonks"]
        }]
        odds=[{
            "fixtureId":"odds-1","kickoff":"2026-11-25T19:00:00Z","homeTeam":"Team A","awayTeam":"Team B",
            "odds":{"h2h":{"home":2.1}},"sources":{"fixture":"The Odds API","odds":"The Odds API"}
        }]
        with patch.dict(os.environ,{"THE_ODDS_API_KEY":"test"},clear=False), \
             patch.object(adapters,"_sportmonks_fixtures",return_value=(sportmonks,[])), \
             patch.object(adapters,"_odds_api",return_value={"data":"odds","fetchedAt":2}), \
             patch.object(adapters,"normalize_provider_payload",side_effect=lambda provider,payload,stamp: odds if provider=="The Odds API" else []):
            result=adapters._normalized_matches({"sports":["soccer_epl"]})
        self.assertEqual(result["recordCount"],1)
        merged=result["data"][0]
        self.assertEqual(merged["sources"]["fixture"],"Sportmonks")
        self.assertEqual(merged["sources"]["odds"],"The Odds API")
        self.assertTrue(merged["lineups"])
        self.assertTrue(merged["venue"])

    def test_caps_sport_requests_to_protect_provider_quota(self):
        with patch.dict(os.environ,{"THE_ODDS_API_KEY":"test"},clear=False):
            with self.assertRaises(adapters.AdapterError):
                adapters._normalized_matches({"sports":[",".join("soccer_league_"+str(i) for i in range(17))]})

if __name__=="__main__":
    unittest.main()
