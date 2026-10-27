import unittest
from unittest.mock import patch
from tools import ufi_historical_results as history
from tools import ufi_provider_adapters as adapters

class HistoricalResultsTests(unittest.TestCase):
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def read(self): return b"Date,HomeTeam,AwayTeam,FTHG,FTAG\n01/08/26,Home FC,Away FC,2,1\n"

    def test_loads_and_normalizes_public_results(self):
        with patch("tools.ufi_historical_results.urllib.request.urlopen",return_value=self.Response()) as get:
            result=history.load_football_data_results("SC0",seasons=2)
        self.assertTrue(result["ok"])
        self.assertEqual(result["record_count"],2)
        self.assertEqual(result["data"][0]["home_team"],"Home FC")
        self.assertEqual(result["data"][0]["home_goals"],2)
        self.assertEqual(get.call_count,2)
        self.assertTrue(all(x.startswith("https://www.football-data.co.uk/") for x in result["source_urls"]))

    def test_rejects_unsupported_league(self):
        with self.assertRaises(ValueError): history.load_football_data_results("FAKE",seasons=2)

    def test_route_exposes_normalized_results(self):
        with patch("tools.ufi_historical_results.load_football_data_results",return_value={"ok":True,"record_count":20,"data":[]}):
            result,_=adapters.handle_extra_route("/api/history/results",{"league":["SC0"],"seasons":["5"]})
        self.assertTrue(result["ok"])
        self.assertEqual(result["record_count"],20)

if __name__=="__main__":unittest.main()
