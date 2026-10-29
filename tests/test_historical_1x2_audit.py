"""Offline tests for historical 1X2 audit logic; no network or dataset download."""
import importlib.util
import unittest
from datetime import date
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "tools" / "historical_1x2_audit.py"
spec = importlib.util.spec_from_file_location("historical_1x2_audit", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class HistoricalAuditTests(unittest.TestCase):
    def test_selection_aliases(self):
        self.assertEqual(module.selection_code("Home"), "H")
        self.assertEqual(module.selection_code("X"), "D")
        self.assertEqual(module.selection_code("2"), "A")
        with self.assertRaises(ValueError):
            module.selection_code("double chance")

    def test_normalization(self):
        self.assertEqual(module.normalize("Man United"), module.normalize("MAN-UNITED"))
        self.assertEqual(module.normalize(""), "")

    def test_audit_returns_probabilities_and_flags(self):
        rows = []
        # Balanced historical league; enough venue-specific records for both teams.
        for i in range(12):
            result = ("H", "D", "A")[i % 3]
            rows.append({
                "date": date(2020, 1, 1).fromordinal(date(2020, 1, 1).toordinal() + i),
                "home": "Home FC", "away": f"Visitor {i}",
                "home_key": "home fc", "away_key": f"visitor {i}",
                "competition": "Test League", "competition_key": "test league",
                "result": result,
            })
            rows.append({
                "date": date(2020, 2, 1).fromordinal(date(2020, 2, 1).toordinal() + i),
                "home": f"Opponent {i}", "away": "Away FC",
                "home_key": f"opponent {i}", "away_key": "away fc",
                "competition": "Test League", "competition_key": "test league",
                "result": result,
            })
        picks = [{
            "date": "2021-01-01", "competition": "Test League",
            "home_team": "Home FC", "away_team": "Away FC", "selection": "Home",
        }]
        report = module.audit(rows, picks)
        self.assertEqual(report["picks_audited"], 1)
        pick = report["picks"][0]
        self.assertAlmostEqual(
            pick["p_home_baseline"] + pick["p_draw_baseline"] + pick["p_away_baseline"], 1.0, places=3
        )
        self.assertEqual(pick["selection"], "HOME")
        self.assertEqual(pick["historical_data_cutoff"], "2020-02-12")
        self.assertIn(pick["screen"], {
            "HIGH_RISK_SCREEN", "REVIEW", "LOWER_HISTORICAL_RISK",
            "LOW_TEAM_SAMPLE", "INSUFFICIENT_TEAM_HISTORY",
        })


    def test_never_uses_future_results_for_historical_fixture(self):
        rows = [{
            "date": date(2025, 1, 2), "home": "Future Home", "away": "Future Away",
            "home_key": "future home", "away_key": "future away",
            "competition": "Test League", "competition_key": "test league", "result": "H",
        }]
        picks = [{
            "date": "2024-01-01", "competition": "Test League",
            "home_team": "Future Home", "away_team": "Future Away", "selection": "Home",
        }]
        pick = module.audit(rows, picks)["picks"][0]
        self.assertEqual(pick["screen"], "INSUFFICIENT_TEAM_HISTORY")
        self.assertAlmostEqual(pick["p_home_baseline"], 1 / 3, places=3)
        self.assertAlmostEqual(pick["p_draw_baseline"], 1 / 3, places=3)
        self.assertAlmostEqual(pick["p_away_baseline"], 1 / 3, places=3)


if __name__ == "__main__":
    unittest.main()
