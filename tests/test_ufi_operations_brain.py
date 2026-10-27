import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from tools.ufi_operations_brain import OperationsStore, operating_phase, normalize_team

WAT = ZoneInfo("Africa/Lagos")


class OperationsBrainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = OperationsStore(Path(self.tmp.name) / "ops.sqlite3")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_nigeria_clock_cutoff(self):
        self.assertEqual(operating_phase(datetime(2026, 10, 27, 20, 59, tzinfo=WAT)), "qualification")
        self.assertEqual(operating_phase(datetime(2026, 10, 27, 21, 0, tzinfo=WAT)), "nightly_preparation")

    def test_normalize_team_alias(self):
        self.assertEqual(normalize_team(" FC  Example! "), "fc example")

    def test_blacklist_blocks_market_and_all_scopes(self):
        self.store.blacklist_team("Example FC", "failed user policy")
        self.assertTrue(self.store.blacklist_reasons("example fc", "Over 0.5 HT"))
        self.assertFalse(self.store.blacklist_reasons("Other FC", "Over 0.5 HT"))

    def test_market_specific_blacklist_does_not_block_other_market(self):
        self.store.blacklist_team("Example FC", "market-specific issue", scope="Over 0.5 HT")
        self.assertTrue(self.store.blacklist_reasons("Example FC", "Over 0.5 HT"))
        self.assertFalse(self.store.blacklist_reasons("Example FC", "Under 3.5 FT"))

    def test_unvalidated_rule_and_missing_prompt_fail_closed(self):
        self.store.save_rule("r1", "Over 0.5 HT", "v1", {"example": True}, status="experimental")
        decision = self.store.qualify(
            {"id": "f1", "home": "A", "away": "B"}, "Over 0.5 HT",
            prompt_pass=None, rule_id="r1", required_data_present=True,
            data_age_seconds=2, phase_time=datetime(2026, 10, 27, 12, 0, tzinfo=WAT))
        self.assertEqual(decision.status, "REJECTED")
        self.assertTrue(any("prompt" in x for x in decision.reasons))
        self.assertTrue(any("validated" in x for x in decision.reasons))

    def test_qualified_requires_validated_rule_fresh_data_prompt_and_odds(self):
        self.store.save_rule("r1", "Over 0.5 HT", "v1", {"test": True}, status="validated")
        decision = self.store.qualify(
            {"id": "f1", "home": "A", "away": "B", "competition": "League"},
            "Over 0.5 HT", prompt_pass=True, rule_id="r1", required_data_present=True,
            data_age_seconds=5, max_data_age_seconds=30, odds=1.2, odds_range=(1.1, 1.3),
            phase_time=datetime(2026, 10, 27, 12, 0, tzinfo=WAT))
        self.assertEqual(decision.status, "QUALIFIED_FOR_REVIEW")

    def test_stale_data_rejected(self):
        self.store.save_rule("r1", "Market", "v1", {}, status="validated")
        decision = self.store.qualify(
            {"id": "f1", "home": "A", "away": "B"}, "Market", prompt_pass=True,
            rule_id="r1", required_data_present=True, data_age_seconds=999,
            max_data_age_seconds=30)
        self.assertEqual(decision.status, "REJECTED")

    def test_three_units_are_independent_and_failure_pauses_only_one(self):
        for unit in (1, 2, 3):
            self.store.configure_unit(unit, 1000, 150)
        self.store.unit_event(1, "u1-fail", "settlement", -50, qualifying_failure=True)
        rows = [self.store.db.execute("SELECT * FROM units WHERE unit_id=?", (u,)).fetchone() for u in (1, 2, 3)]
        self.assertEqual(rows[0]["status"], "paused_today")
        self.assertEqual(rows[1]["status"], "active")
        self.assertEqual(rows[2]["status"], "active")

    def test_duplicate_ledger_event_not_applied_twice(self):
        self.store.configure_unit(1, 1000, 150)
        self.store.unit_event(1, "same", "settlement", -50)
        self.store.unit_event(1, "same", "settlement", -50)
        row = self.store.db.execute("SELECT bankroll FROM units WHERE unit_id=1").fetchone()
        self.assertEqual(row["bankroll"], 950)

    def test_successful_cycle_resets_lives_and_mode(self):
        self.store.configure_unit(1, 1000, 150)
        self.store.unit_event(1, "mode", "set_mode", details={"mode": "absorber_boost"})
        self.store.unit_event(1, "success", "cycle", cycle_success=True)
        row = self.store.db.execute("SELECT * FROM units WHERE unit_id=1").fetchone()
        self.assertEqual(row["remaining_lives"], 4)
        self.assertEqual(row["mode"], "normal")

    def test_invalid_stakes_rejected(self):
        with self.assertRaises(ValueError):
            self.store.configure_unit(4, 1000, 150)


if __name__ == "__main__":
    unittest.main()
