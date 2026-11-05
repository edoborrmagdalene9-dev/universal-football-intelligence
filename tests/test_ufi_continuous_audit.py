import unittest
from tools.ufi_continuous_audit import audit_slip_payload, score_matrix

class ContinuousAuditTests(unittest.TestCase):
    def test_isolated_pockets_and_probabilities(self):
        r=audit_slip_payload({"fixtures":[
          {"home":"A","away":"B","evidence":{"home_xg":1.2,"away_xg":0.9},"selections":[{"market":"Over 1.5 Goals","selection":"Over 1.5","odds":1.3}]},
          {"home":"C","away":"D","selections":[{"market":"BTTS","selection":"Yes","model_probability":0.31}]}]})
        self.assertEqual(r["fixture_count"],2)
        self.assertNotEqual(r["pockets"][0]["fixture_id"],r["pockets"][1]["fixture_id"])
        self.assertIsNotNone(r["pockets"][0]["selections"][0]["model_probability"])
        self.assertEqual(r["pockets"][1]["selections"][0]["decision"],"DITCH")
    def test_missing_data_is_not_cleared(self):
        r=audit_slip_payload({"fixtures":[{"home":"A","away":"B","selections":[{"market":"Corners","selection":"Over 8.5"}]}]})
        self.assertEqual(r["pockets"][0]["selections"][0]["decision"],"NEEDS_DATA")
    def test_tactical_tension_is_not_false_mutex(self):
        r=audit_slip_payload({"fixtures":[{"home":"A","away":"B","evidence":{"passive_build_up":True,"high_transition_rate":0.8},"selections":[{"market":"BTTS","selection":"Yes","model_probability":0.6}]}]})
        self.assertEqual(r["pockets"][0]["mutex"],[])
        self.assertTrue({"passive_build_up","high_transition_environment"}.issubset({x["code"] for x in r["pockets"][0]["fault_pocket"]}))
    def test_low_probability_is_ditched(self):
        r=audit_slip_payload({"fixtures":[{"home":"A","away":"B","selections":[{"market":"BTTS","selection":"Yes","model_probability":0.4}]}]})
        self.assertEqual(r["pockets"][0]["selections"][0]["decision"],"DITCH")
        self.assertAlmostEqual(r["pockets"][0]["selections"][0]["ditch_probability"],0.6)
    def test_explicit_hard_mutex_quarantines_fixture_faults(self):
        r=audit_slip_payload({"fixtures":[{"home":"A","away":"B","evidence":{"state_assertions":["fixture_not_started","fixture_final_score_recorded_as_live"]},"selections":[{"market":"BTTS","selection":"Yes","model_probability":0.8}]}]})
        pocket=r["pockets"][0]
        self.assertTrue(pocket["mutex"])
        self.assertEqual(pocket["selections"][0]["decision"],"NEEDS_DATA")
        self.assertTrue(all(x["status"]=="quarantined" for x in pocket["fault_pocket"]))
    def test_bad_threshold_rejected(self):
        with self.assertRaises(ValueError):
            audit_slip_payload({"survival_threshold":1.1,"fixtures":[{"home":"A","away":"B","selections":[{"market":"BTTS","selection":"Yes","model_probability":0.5}]}]})
    def test_score_matrix_normalized(self):
        self.assertAlmostEqual(sum(map(sum,score_matrix(1.3,0.8))),1.0,places=8)

if __name__=="__main__": unittest.main()
