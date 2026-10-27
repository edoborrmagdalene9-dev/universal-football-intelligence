import os
import tempfile
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from tools.ufi_operations_brain import OperationsStore, operating_phase
from tools.ufi_nightly_runner import _fixture, _rows

WAT=ZoneInfo("Africa/Lagos")

class NightlyOperationsTests(unittest.TestCase):
    def test_2100_wat_switches_to_nightly_prep(self):
        self.assertEqual(operating_phase(datetime(2026,10,27,20,59,tzinfo=WAT)),"qualification")
        self.assertEqual(operating_phase(datetime(2026,10,27,21,0,tzinfo=WAT)),"nightly_preparation")

    def test_unverified_prompt_and_rule_cannot_qualify(self):
        with tempfile.TemporaryDirectory() as d:
            store=OperationsStore(os.path.join(d,"ops.sqlite3"))
            fixture={"id":"123","home":"Home FC","away":"Away FC","competition":"League"}
            decision=store.qualify(fixture,"correct_score",prompt_pass=None,rule_id=None,
                required_data_present=True,data_age_seconds=2,max_data_age_seconds=60)
            self.assertEqual(decision.status,"REJECTED")
            self.assertTrue(any("prompt" in reason for reason in decision.reasons))
            self.assertTrue(any("validated research rule" in reason for reason in decision.reasons))
            store.close()

    def test_stale_and_missing_data_reject(self):
        with tempfile.TemporaryDirectory() as d:
            store=OperationsStore(os.path.join(d,"ops.sqlite3"))
            fixture={"id":"123","home":"Home FC","away":"Away FC"}
            stale=store.qualify(fixture,"correct_score",prompt_pass=True,rule_id=None,
                required_data_present=True,data_age_seconds=999,max_data_age_seconds=60)
            missing=store.qualify(fixture,"correct_score",prompt_pass=True,rule_id=None,
                required_data_present=False,data_age_seconds=None,max_data_age_seconds=60)
            self.assertTrue(any("stale" in x for x in stale.reasons))
            self.assertTrue(any("unavailable" in x for x in missing.reasons))
            store.close()

    def test_three_unit_ledgers_pause_only_failed_unit_and_reset_on_success(self):
        with tempfile.TemporaryDirectory() as d:
            store=OperationsStore(os.path.join(d,"ops.sqlite3"))
            for unit in (1,2,3): store.configure_unit(unit,1000,150,50,75)
            failed=store.unit_event(1,"u1-fail","settlement",-50,qualifying_failure=True)
            self.assertEqual(failed["status"],"paused_today")
            other=store.db.execute("SELECT status FROM units WHERE unit_id=2").fetchone()[0]
            self.assertEqual(other,"active")
            reset=store.unit_event(1,"u1-cycle-success","cycle",100,cycle_success=True)
            self.assertEqual(reset["remaining_lives"],4)
            self.assertEqual(reset["mode"],"normal")
            store.close()

    def test_fixture_rows_are_unwrapped_without_fabricating_unknown_fields(self):
        raw={"id":8,"participants":[{"name":"Home FC","meta":{"location":"home"}},{"name":"Away FC","meta":{"location":"away"}}]}
        rows=_rows({"data":{"data":[raw]}})
        self.assertEqual(len(rows),1)
        fixture=_fixture(rows[0])
        self.assertEqual(fixture["home"],"Home FC")
        self.assertEqual(fixture["away"],"Away FC")
        self.assertIsNone(fixture["kickoff"])

if __name__=="__main__":unittest.main()
