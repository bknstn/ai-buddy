"""Synthetic regression tests; no real accounts, delivery or private state."""
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import conversation_context as cc
import heartbeat as hb


class PartialContextTests(unittest.TestCase):
    def setUp(self):
        self.instant = datetime(2026, 10, 4, 10, tzinfo=cc.TZ)
        self.ledger = {"revision": 0, "entries": []}
        self.dialogue = {"watermark": 10, "messages": [{"source_id": 10,
            "role": "user", "text": "Continue the example project.",
            "at": self.instant.isoformat()}]}
        self.valid = {"id": "project:example", "kind": "commitment", "status": "active",
            "summary": "Continue the example project", "next_step": "", "review_on": None,
            "source_id": 10, "quote": "Continue the example project."}
        self.invalid = dict(self.valid, id="project:unsupported", quote="Invented user consent.")
        self.item = {"topic": "calendar", "key": "calendar:example",
            "message": "Prepare for the confirmed appointment.",
            "evidence": "An authorized calendar source", "why_now": "Appointment is soon",
            "context_dependencies": []}
        self.proposal = {"date": "2026-10-04", "context_revision": 0,
            "dialogue_watermark": 10, "context_updates": [self.invalid, self.valid],
            "items": [self.item]}

    def apply(self, proposal=None, ledger=None, dialogue=None):
        return cc.apply_verified_updates(ledger or self.ledger, proposal or self.proposal,
            dialogue or self.dialogue, self.instant)

    def test_only_provenance_failures_are_isolated_and_input_is_unchanged(self):
        original = deepcopy(self.proposal)
        for updates in ([self.invalid, self.valid], [self.valid, self.invalid]):
            saved, outcome, rejected = self.apply(dict(self.proposal, context_updates=updates))
            self.assertEqual(outcome, "saved")
            self.assertEqual(saved["revision"], 1)
            self.assertEqual([row["id"] for row in saved["entries"]], [self.valid["id"]])
            self.assertEqual(rejected, {self.invalid["id"]})
        self.assertEqual(self.ledger, {"revision": 0, "entries": []})
        self.assertEqual(self.proposal, original)
        with self.assertRaises(cc.ProvenanceError):
            cc.apply_updates(self.ledger, self.proposal, self.dialogue, self.instant)

    def test_all_invalid_updates_never_create_a_revision(self):
        saved, outcome, rejected = self.apply(dict(self.proposal, context_updates=[self.invalid]))
        self.assertIs(saved, self.ledger)
        self.assertEqual(outcome, "unchanged")
        self.assertEqual(rejected, {self.invalid["id"]})

    def test_missing_source_assistant_text_and_wrong_preceding_proposal_rejected(self):
        for invalid in (dict(self.invalid, source_id=99),
                dict(self.invalid, source_id=9, quote="Continue the example project."),
                dict(self.invalid, quote=self.valid["quote"], proposal_source_id=9,
                     proposal_quote="A different preceding proposal.")):
            dialogue = dict(self.dialogue, messages=[dict(self.dialogue["messages"][0],
                source_id=9, role="assistant"), *self.dialogue["messages"]])
            saved, _, rejected = self.apply(dict(self.proposal,
                context_updates=[invalid, self.valid]), dialogue=dialogue)
            self.assertEqual(rejected, {invalid["id"]})
            self.assertEqual(len(saved["entries"]), 1)

    def test_stale_revision_or_new_reply_still_blocks_the_whole_snapshot(self):
        for changes in ({"context_revision": 1}, {"dialogue_watermark": 11}):
            saved, outcome, rejected = self.apply(dict(self.proposal, **changes))
            self.assertIs(saved, self.ledger)
            self.assertEqual(outcome, "stale")
            self.assertEqual(rejected, set())

    def test_schema_capacity_and_lifecycle_errors_are_not_swallowed(self):
        for update in (dict(self.invalid, summary="password=synthetic-secret"),
                dict(self.valid, status="done"), self.valid):
            with self.subTest(update=update), self.assertRaises(ValueError):
                with patch.object(cc, "MAX_ENTRIES", 0):
                    self.apply(dict(self.proposal, context_updates=[update]))
        with self.assertRaises(ValueError):
            self.apply(dict(self.proposal, context_updates=[self.valid, self.valid]))

    def run_delivery(self, items=None, controls=None, history=None, instant=None):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(hb, "STATE", Path(directory)), \
                patch.object(hb, "now", return_value=instant or self.instant), \
                patch.object(hb, "recent_dialogue", return_value=self.dialogue), \
                patch.object(hb, "queued_proposal", return_value=dict(self.proposal,
                    items=self.proposal["items"] if items is None else items)), \
                patch.object(hb, "mirror_prepared_message") as mirror:
            if controls:
                hb.write(hb.STATE / "controls.json", controls)
            if history:
                hb.write(hb.STATE / "history.json", history)
            with self.assertLogs(level="WARNING") as logs:
                message = hb.deliver()
            self.assertNotIn(self.invalid["quote"], " ".join(logs.output))
            return message, cc.load_ledger(hb.STATE), hb.read(hb.STATE / "history.json", {}), mirror.call_count

    def test_independent_signal_delivers_without_saving_or_emitting_bad_context(self):
        dependent = dict(self.item, key="calendar:unsupported",
            message="Must not be emitted.", context_dependencies=[self.invalid["id"]])
        message, ledger, history, mirrors = self.run_delivery([dependent, self.item])
        self.assertEqual(message, self.item["message"])
        self.assertEqual([entry["id"] for entry in ledger["entries"]], [self.valid["id"]])
        self.assertEqual(history["emitted"][0]["keys"], [self.item["key"]])
        self.assertEqual(mirrors, 1)

    def test_verified_dependency_delivers_but_unknown_or_unspecified_dependency_stays_silent(self):
        good = dict(self.item, context_dependencies=[self.valid["id"]])
        self.assertEqual(self.run_delivery([good])[0], self.item["message"])
        missing = {key: value for key, value in self.item.items() if key != "context_dependencies"}
        for item in (missing, dict(self.item, context_dependencies=["unknown:context"]),
                dict(self.item, context_dependencies=[self.invalid["id"]])):
            message, ledger, history, mirrors = self.run_delivery([item])
            self.assertEqual(message, "")
            self.assertEqual(len(ledger["entries"]), 1)
            self.assertEqual(history, {})
            self.assertEqual(mirrors, 0)

    def test_quiet_snoozed_or_used_budget_still_suppresses_independent_note(self):
        cases = [dict(instant=self.instant.replace(hour=8)),
            dict(controls={"snoozes": {"calendar": (self.instant + timedelta(days=1)).isoformat()}}),
            dict(history={"emitted": [{"date": "2026-10-04", "keys": ["already:sent"]}]})]
        for changes in cases:
            self.assertEqual(self.run_delivery(**changes)[0], "")

    def test_rejected_change_cannot_use_an_older_copy_of_the_same_entry(self):
        old, _ = cc.apply_updates(self.ledger, dict(self.proposal,
            context_updates=[self.valid]), self.dialogue, self.instant)
        old["entries"][0]["id"] = self.invalid["id"]
        self.ledger = old
        self.proposal.update(context_revision=old["revision"], context_updates=[self.invalid])
        dependent = dict(self.item, context_dependencies=[self.invalid["id"]])
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(hb, "STATE", Path(directory)), \
                patch.object(hb, "now", return_value=self.instant), \
                patch.object(hb, "recent_dialogue", return_value=self.dialogue), \
                patch.object(hb, "queued_proposal", return_value=dict(self.proposal, items=[dependent])), \
                patch.object(hb, "mirror_prepared_message") as mirror:
            hb.write(hb.STATE / "conversation.json", old)
            with self.assertLogs(level="WARNING"):
                self.assertEqual(hb.deliver(), "")
            self.assertEqual(cc.load_ledger(hb.STATE), old)
            mirror.assert_not_called()
            self.assertFalse((hb.STATE / "history.json").exists())

    def test_genuine_short_confirmation_is_accepted_without_relaxing_proof(self):
        dialogue = dict(self.dialogue, messages=[
            {"source_id": 9, "role": "assistant", "text": "Continue the example project?"},
            {"source_id": 10, "role": "user", "text": "yes", "at": self.instant.isoformat()}])
        update = dict(self.valid, quote="yes", proposal_source_id=9,
            proposal_quote="Continue the example project?")
        ledger, outcome, rejected = self.apply(dict(self.proposal,
            context_updates=[self.invalid, update]), dialogue=dialogue)
        self.assertEqual(outcome, "saved")
        self.assertEqual(ledger["entries"][0]["quote"], "yes")
        self.assertEqual(rejected, {self.invalid["id"]})

    def test_dependency_schema_remains_strict(self):
        for dependencies in (None, "project:example", [1], ["bad id"], ["same", "same"]):
            with self.subTest(dependencies=dependencies), self.assertRaises(ValueError):
                hb.validate_proposal(dict(self.proposal, items=[dict(self.item,
                    context_dependencies=dependencies)]), self.instant)


if __name__ == "__main__":
    unittest.main()
