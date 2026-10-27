import unittest
from datetime import datetime, timezone
from tools.ufi_live_brain_worker import unwrap_rows, team_names, kickoff_datetime, minute_score, extract_live_stats, odds_values

class LiveBrainWorkerTests(unittest.TestCase):
    def test_unwrap_rows(self):
        rows=[{"fixtureId":"a"},{"fixtureId":"b"}]
        self.assertEqual(unwrap_rows({"data":rows}),rows)
        self.assertEqual(unwrap_rows({"data":{"data":rows}}),rows)
        self.assertEqual(unwrap_rows({"message":"none"}),[])
    def test_home_away(self):
        row={"participants":[{"name":"Away","meta":{"location":"away"}},{"name":"Home","meta":{"location":"home"}}]}
        self.assertEqual(team_names(row),("Home","Away"))
    def test_kickoff_requires_timezone(self):
        self.assertEqual(kickoff_datetime({"kickoff":"2026-10-27T12:00:00Z"}),datetime(2026,10,27,12,tzinfo=timezone.utc))
        self.assertIsNone(kickoff_datetime({"kickoff":"2026-10-27 12:00:00"}))
    def test_minute_and_score(self):
        self.assertEqual(minute_score({"status":{"clock":"17"},"score":{"home":0,"away":0}}),(17,(0,0)))
        self.assertEqual(minute_score({"status":{},"score":None}),(None,None))
    def test_missing_stats_stay_unknown(self):
        self.assertEqual(extract_live_stats({}),{"sot":None,"shots":None,"danger":None})
        got=extract_live_stats({"statistics":[{"type":"Shots on Target","value":2},{"type":"Total Shots","value":5}]})
        self.assertEqual(got["sot"],2.0); self.assertEqual(got["shots"],5.0)
    def test_explicit_market_odds_only(self):
        self.assertEqual(odds_values({"data":[{"name":"Over 0.5 1st Half","odds":"1.21"}]}),[1.21])
        self.assertEqual(odds_values({"data":[{"name":"Match Winner","odds":"1.21"}]}),[])
if __name__=="__main__": unittest.main()
