import contextlib
from datetime import datetime, timedelta
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import heartbeat as hb


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.instant = datetime(2026, 10, 2, 9, 0, tzinfo=hb.TZ)
        self.item = {"topic": "learning", "key": "learning:first-diagnostic",
            "message": "Один небольшой следующий шаг.", "evidence": "onboarding pending",
            "why_now": "explicit active goal"}
        self.proposal = {"date": "2026-10-02", "items": [self.item]}
        self.history = {"emitted": [], "feedback": []}
        self.settings = {"paused": False, "snoozes": {}}

    def choose(self, **changes):
        return hb.choose(changes.get("proposal", self.proposal),
            changes.get("history", self.history), changes.get("settings", self.settings),
            changes.get("instant", self.instant))

    def test_empty_and_stale_candidates_are_silent(self):
        self.assertEqual(self.choose(proposal={"date": "2026-10-02", "items": []}), [])
        self.assertEqual(self.choose(proposal={"date": "2026-10-01", "items": [self.item]}), [])

    def test_quiet_hours_and_pause(self):
        for hour in (0, 8, 21, 23):
            self.assertEqual(self.choose(instant=self.instant.replace(hour=hour)), [])
        self.assertEqual(self.choose(settings={"paused": True}), [])
        self.assertEqual(self.choose(settings={"pause_until": (self.instant + timedelta(hours=2)).isoformat()}), [])
        self.assertTrue(self.choose(settings={"pause_until": (self.instant - timedelta(hours=2)).isoformat()}))

    def test_topic_snooze_expires(self):
        self.settings["snoozes"]["learning"] = (self.instant + timedelta(days=7)).isoformat()
        self.assertEqual(self.choose(), [])
        self.settings["snoozes"]["learning"] = (self.instant - timedelta(seconds=1)).isoformat()
        self.assertTrue(self.choose())

    def test_duplicate_and_daily_budget(self):
        self.history["emitted"] = [{"date": "2026-10-01", "at": "2026-10-01T09:00:00+02:00",
            "keys": [self.item["key"]], "topics": ["learning"]}]
        self.assertEqual(self.choose(), [])
        self.history["emitted"][0].update(date="2026-10-02", keys=["other"])
        self.assertEqual(self.choose(), [])

    def test_weekly_technical_budget_keeps_personal_signal(self):
        technical = dict(self.item, topic="buddy", key="buddy:release:new")
        self.proposal["items"].insert(0, technical)
        self.history["emitted"] = [{"date": "2026-09-30", "at": "2026-09-30T09:00:00+02:00",
            "keys": ["buddy:old"], "topics": ["buddy"]}]
        self.assertEqual(self.choose(), [self.item])

    def test_warsaw_dst_is_wall_clock(self):
        for month, day, offset in ((10, 24, 2), (10, 26, 1), (3, 30, 2)):
            instant = datetime(2026, month, day, 9, tzinfo=hb.TZ)
            proposal = dict(self.proposal, date=instant.date().isoformat())
            self.assertEqual(instant.utcoffset(), timedelta(hours=offset))
            self.assertTrue(self.choose(instant=instant, proposal=proposal))
            self.assertFalse(self.choose(instant=instant.replace(hour=8), proposal=proposal))

    def test_validation_and_message_markers(self):
        hb.validate_proposal(self.proposal, self.instant)
        for marker in ("[SILENT]", "MEDIA:", "[CRON_FAILURE]"):
            with self.assertRaises(ValueError):
                hb.validate_proposal({"date": "2026-10-02", "items": [dict(self.item, message=marker)]}, self.instant)
        with self.assertRaises(ValueError):
            hb.validate_proposal({"date": "2026-10-01", "items": []}, self.instant)

    def test_unavailable_source_reveals_no_error_payload(self):
        def failure():
            raise ValueError("secret-token-in-private-url")
        self.assertEqual(hb.source(failure), {"status": "unavailable", "error_type": "ValueError"})

    def test_delivery_reservation_persists_and_blocks_replay(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(hb, "STATE", Path(directory)), patch.object(hb, "now", return_value=self.instant):
            hb.write(hb.STATE / "pending.json", self.proposal)
            self.assertIn(self.item["message"], hb.deliver())
            self.assertEqual(hb.deliver(), "")
            self.assertEqual(len(hb.read(hb.STATE / "history.json", {})["emitted"]), 1)
            self.assertEqual(list(hb.STATE.glob("*.tmp")), [])

    def test_control_commands_persist(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(hb, "STATE", Path(directory)), patch.object(hb, "now", return_value=self.instant), contextlib.redirect_stdout(io.StringIO()):
            for arguments in (["pause"], ["resume"], ["snooze", "learning", "--days", "7"]):
                with patch("sys.argv", ["heartbeat.py"] + arguments):
                    hb.main()
            self.assertFalse(hb.controls()["paused"])
            self.assertIn("learning", hb.controls()["snoozes"])

    def test_native_output_is_validated_without_agent_file_writes(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(hb, "HOME", Path(directory)), patch.object(hb, "STATE", Path(directory) / "state"):
            hb.write(hb.STATE / "installation.json", {"daily_id": "daily"})
            folder = hb.HOME / "cron/output/daily"
            folder.mkdir(parents=True)
            output = folder / "run.md"
            output.write_text("# Job\n## Prompt\nquoted data\n## Response\n\n" + json.dumps(self.proposal))
            self.assertEqual(hb.queued_proposal(self.instant), self.proposal)
            output.write_text("# Job\n**Status:** silent (wakeAgent=false)\n")
            self.assertEqual(hb.queued_proposal(self.instant)["items"], [])
            output.write_text("# Job\n## Response\nnot json")
            with self.assertRaises(ValueError):
                hb.queued_proposal(self.instant)


if __name__ == "__main__":
    unittest.main()
