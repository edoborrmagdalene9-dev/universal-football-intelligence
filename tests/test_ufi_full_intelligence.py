import unittest
from tools.ufi_full_intelligence import audit_full_fixture, market_probability, team_goal_profile, COMPONENTS

def sample_grid():
    # Deterministic normalized grid for adapter tests only; not a real match forecast.
    cells=[]
    for h in range(9):
        for a in range(9):
            p=(0.22 if h==1 else 0.08 if h==0 else 0.07)/(9*9)
            cells.append({"home":h,"away":a,"p":p})
    total=sum(x["p"] for x in cells)
    for x in cells: x["p"]/=total
    return cells

class FullIntelligenceTests(unittest.TestCase):
    def test_market_probability_uses_dixon_coles_score_grid(self):
        grid=sample_grid()
        p,method=market_probability(grid,{"market":"Double Chance 12","selection":"12"})
        self.assertGreater(p,0)
        self.assertLessEqual(p,1)
        self.assertEqual(method,"dixon_coles_score_grid")

    def test_team_multigoals_reports_both_ruin_tails(self):
        profile=team_goal_profile(sample_grid(),"home")
        self.assertAlmostEqual(profile["p_zero"]+profile["p_one_to_three"]+profile["p_four_plus"],1.0)
        self.assertAlmostEqual(profile["ruin_tail"],profile["p_zero"]+profile["p_four_plus"])

    def test_missing_pirates_evidence_never_auto_passes(self):
        model={"status":"model_output","rate_estimate":{"ok":True,"lambdaHome":1.6,"lambdaAway":1.1},
               "dixon_coles":{"rho":-0.1},"models":{"dixon_coles":{"score_grid":sample_grid()}}}
        result=audit_full_fixture({
            "fixture":{"fixture_id":"test-1","home":"Home","away":"Away","kickoff":"2026-11-25T19:00:00Z"},
            "model":model,"evidence":{},
            "selections":[{"market":"1X2","selection":"Home","odds":2.2}]
        })
        selection=result["selections"][0]
        self.assertEqual(selection["decision"],"NEEDS_DATA")
        self.assertEqual(len(selection["pirates_layers"]),9)
        self.assertTrue(any(x["status"]=="NEEDS_DATA" for x in selection["pirates_layers"]))

    def test_dc12_missing_evidence_is_needs_data_not_a_false_fail(self):
        model={"status":"model_output","rate_estimate":{"ok":True,"lambdaHome":1.5,"lambdaAway":1.0},
               "dixon_coles":{"rho":-0.1},"models":{"dixon_coles":{"score_grid":sample_grid()}}}
        result=audit_full_fixture({
            "fixture":{"fixture_id":"test-2","home":"Home","away":"Away","kickoff":"2026-11-25T19:00:00Z"},
            "model":model,"evidence":{},
            "selections":[{"market":"DC12","selection":"12","odds":1.5}]
        })
        self.assertEqual(result["selections"][0]["decision"],"NEEDS_DATA")
        self.assertTrue(any(x["status"]=="NEEDS_DATA" for x in result["selections"][0]["hard_gates"]))

    def test_5400_gate_requires_independent_validation_and_fresh_snapshots(self):
        from datetime import datetime, timezone
        from tools.ufi_full_intelligence import _bookie_edge_5400
        missing=_bookie_edge_5400(0.6,2.0,{},{"status":"scheduled"})
        self.assertEqual(missing["status"],"NEEDS_DATA")
        evidence={"uncertainty":0.01,"validation_matches":600,"snapshots":5,
                  "no_vig_probability":0.45,"source_updated_at":datetime.now(timezone.utc).isoformat(),
                  "match_second":2700}
        passed=_bookie_edge_5400(0.6,2.0,evidence,{"status":"live"})
        self.assertEqual(passed["status"],"PASS")
        self.assertGreaterEqual(passed["margin_score"],1.05)

    def test_market_correlation_identifies_alternative_1x2_outcomes(self):
        from tools.ufi_full_intelligence import _market_correlations
        rows=[{"home":1,"away":0,"p":0.5},{"home":0,"away":1,"p":0.5}]
        result=_market_correlations([
            {"market":"1X2","selection":"Home"},
            {"market":"1X2","selection":"Away"}
        ],rows,{"home":"Home","away":"Away"})
        self.assertEqual(result[0]["relationship"],"mutually_exclusive")

    def test_100_component_check_is_exactly_100_and_missing_stays_unknown(self):
        model={"status":"NEEDS_DATA"}
        result=audit_full_fixture({
            "fixture":{"fixture_id":"test-3","home":"Home","away":"Away"},
            "model":model,"evidence":{},
            "selections":[{"market":"Unsupported","selection":"Home","odds":2.0}]
        })
        self.assertEqual(len(COMPONENTS),100)
        self.assertEqual(result["components_100"]["total"],100)
        self.assertEqual(result["components_100"]["counts"]["ASSESSED"],0)
        self.assertEqual(result["components_100"]["counts"]["NEEDS_DATA"],100)

    def test_physical_duel_never_infers_jump_from_height(self):
        players=[{"height_cm":180+i} for i in range(11)]
        result=audit_full_fixture({
            "fixture":{"fixture_id":"test-4","home":"Home","away":"Away"},
            "model":{"status":"NEEDS_DATA"},"evidence":{"home_players":players,"away_players":players,
            "formation_home":"4-3-3","formation_away":"4-4-2"},
            "selections":[{"market":"Unsupported","selection":"Home","odds":2.0}]
        })
        self.assertEqual(result["physical_duel"]["status"],"PARTIAL")
        self.assertEqual(result["physical_duel"]["jump_metrics"],"NOT_AVAILABLE_UNLESS_SOURCE_SUPPLIED")

if __name__=="__main__":
    unittest.main()
