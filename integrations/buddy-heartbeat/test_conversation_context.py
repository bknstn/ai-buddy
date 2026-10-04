from datetime import datetime, timedelta
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import conversation_context as cc
import heartbeat as hb


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.instant = datetime(2026, 10, 4, 10, tzinfo=cc.TZ)
        self.human = {"source_id": 10, "role": "user", "at": self.instant.isoformat(),
            "text": "Решил продолжить учебный проект, вернёмся к нему 8 октября."}
        self.dialogue = {"messages": [self.human]}
        self.update = {"id": "learning:project", "kind": "commitment", "status": "active",
            "summary": "Продолжить выбранный учебный проект", "next_step": "",
            "review_on": "2026-10-08", "source_id": 10, "quote": self.human["text"]}
        self.empty = {"revision": 0, "entries": []}
        self.proposal = {"date": "2026-10-04", "items": [], "context_revision": 0,
            "context_updates": [self.update]}

    def test_evidence_must_be_real_human_text(self):
        for dialogue, update in (({"messages": [dict(self.human, role="assistant")]}, self.update),
                (self.dialogue, dict(self.update, quote="Вымышленное согласие"))):
            with self.subTest(update=update), self.assertRaises(ValueError):
                cc.apply_updates(self.empty, dict(self.proposal, context_updates=[update]), dialogue, self.instant)
        self.assertEqual(self.empty, {"revision": 0, "entries": []})

    def test_short_acceptance_needs_the_immediate_concrete_proposal(self):
        human = dict(self.human, text="Да")
        offer = dict(self.human, source_id=9, role="assistant", text="Продолжим выбранный проект?")
        update = dict(self.update, quote="Да")
        with self.assertRaises(ValueError):
            cc.apply_updates(self.empty, dict(self.proposal, context_updates=[update]),
                {"messages": [offer, human]}, self.instant)
        update.update(proposal_source_id=9, proposal_quote=offer["text"])
        saved, outcome = cc.apply_updates(self.empty, dict(self.proposal, context_updates=[update]),
            {"messages": [offer, human]}, self.instant)
        self.assertEqual(outcome, "saved")
        self.assertEqual(saved["entries"][0]["quote"], "Да")
        with self.assertRaises(ValueError):
            cc.apply_updates(self.empty, dict(self.proposal, context_updates=[update]),
                {"messages": [offer, dict(offer, source_id=11), dict(human, source_id=12)]}, self.instant)

    def test_stale_review_cannot_overwrite_new_chat_decision(self):
        current, _ = cc.apply_updates(self.empty, self.proposal, self.dialogue, self.instant)
        result, status = cc.apply_updates(current, self.proposal, self.dialogue, self.instant)
        self.assertEqual(status, "stale")
        self.assertIs(result, current)

    def test_new_human_reply_invalidates_prepared_advice_even_without_ledger_updates(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(hb, "STATE", Path(directory)), \
                patch.object(hb, "now", return_value=self.instant), \
                patch.object(hb, "recent_dialogue", return_value=dict(self.dialogue, watermark=11)):
            hb.write(hb.STATE / "pending.json", dict(self.proposal, dialogue_watermark=10))
            self.assertEqual(hb.deliver(), "")
            self.assertFalse((hb.STATE / "conversation.json").exists())

    def test_completion_updates_same_entry_and_keeps_other_agreements(self):
        saved, _ = cc.apply_updates(self.empty, self.proposal, self.dialogue, self.instant)
        extra = dict(saved["entries"][0], id="other:decision")
        saved["entries"].append(extra)
        human = dict(self.human, source_id=11, text="Этот учебный проект завершён.")
        update = dict(self.update, status="done", source_id=11, quote=human["text"])
        result, _ = cc.apply_updates(saved, dict(self.proposal, context_revision=1,
            context_updates=[update]), {"messages": [human]}, self.instant)
        self.assertEqual(len(result["entries"]), 2)
        self.assertEqual(result["entries"][0]["status"], "done")
        self.assertEqual(result["entries"][1]["status"], "active")
        self.assertEqual(saved["entries"][0]["status"], "active")

    def test_replayed_evidence_does_not_duplicate_or_reopen_work(self):
        saved, _ = cc.apply_updates(self.empty, self.proposal, self.dialogue, self.instant)
        result, status = cc.apply_updates(saved, dict(self.proposal, context_revision=1), self.dialogue, self.instant)
        self.assertEqual(status, "unchanged")
        self.assertEqual(result, saved)

    def test_invalid_batch_changes_nothing_and_unknown_work_cannot_close(self):
        for updates in ([self.update, dict(self.update, id="other", source_id=999)],
                [dict(self.update, status="cancelled")],
                [dict(self.update, summary="password=private-value")]):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                cc.apply_updates(self.empty, dict(self.proposal, context_updates=updates), self.dialogue, self.instant)
        self.assertEqual(self.empty["entries"], [])

    def test_quiet_day_still_persists_agreement_without_message(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(hb, "STATE", Path(directory)), \
                patch.object(hb, "now", return_value=self.instant), \
                patch.object(hb, "recent_dialogue", return_value=self.dialogue):
            hb.write(hb.STATE / "pending.json", self.proposal)
            self.assertEqual(hb.deliver(), "")
            self.assertEqual(cc.load_ledger(hb.STATE)["entries"][0]["id"], self.update["id"])
            self.assertFalse((hb.STATE / "history.json").exists())
            self.assertEqual(list(hb.STATE.glob("*.tmp")), [])

    def test_pause_stops_background_context_updates(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(hb, "STATE", Path(directory)), \
                patch.object(hb, "now", return_value=self.instant):
            hb.write(hb.STATE / "pending.json", self.proposal)
            hb.write(hb.STATE / "controls.json", {"paused": True})
            self.assertEqual(hb.deliver(), "")
            self.assertFalse((hb.STATE / "conversation.json").exists())

    def test_old_active_work_survives_but_old_completed_work_leaves_review_context(self):
        saved, _ = cc.apply_updates(self.empty, self.proposal, self.dialogue, self.instant)
        old = (self.instant - timedelta(days=60)).isoformat()
        saved["entries"][0]["updated_at"] = old
        saved["entries"].append(dict(saved["entries"][0], id="completed", status="done"))
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            hb.write(state / "conversation.json", saved)
            context = cc.ledger_context(state, self.instant)
            self.assertEqual([row["id"] for row in context["entries"]], [self.update["id"]])

    def test_main_chat_reader_excludes_topics_tools_other_users_and_internal_mirrors(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            state = home / "private"
            hb.write(state / "installation.json", {"telegram_chat_id": "123"})
            with sqlite3.connect(home / "state.db") as db:
                db.executescript("""CREATE TABLE sessions(id TEXT, source TEXT, chat_id TEXT,
                    user_id TEXT, chat_type TEXT, thread_id TEXT);
                    CREATE TABLE messages(id INTEGER,session_id TEXT,role TEXT,content TEXT,
                    timestamp REAL,platform_message_id TEXT,active INTEGER,_compressed_summary INTEGER,tool_calls TEXT);""")
                db.executemany("INSERT INTO sessions VALUES(?,?,?,?,?,?)", [
                    ("main", "telegram", "123", "123", "dm", None),
                    ("old-main", "telegram", "123", "123", "dm", None),
                    ("topic", "telegram", "123", "123", "thread", "42"),
                    ("other", "telegram", "123", "456", "dm", None)])
                stamp = self.instant.timestamp()
                rows = [(1,"main","user",self.human["text"],stamp,"tg1",1,0,None),
                    (2,"main","assistant","Понятно, вернёмся к проекту.",stamp,None,1,0,None),
                    (3,"main","user","Internal prepared-note mirror",stamp,None,1,0,None),
                    (4,"topic","user","Other topic",stamp,"tg4",1,0,None),
                    (5,"other","user","Another person",stamp,"tg5",1,0,None),
                    (6,"main","tool","Private tool data",stamp,None,1,0,None),
                    (7,"main","assistant","Tool preamble",stamp,None,1,0,"[{}]"),
                    (8,"main","user","Compressed summary",stamp,"tg8",1,1,None),
                    (9,"main","user","password=private-secret",stamp,"tg9",1,0,None),
                    (10,"old-main","user","Previous session decision",stamp-100,"tg10",1,0,None),
                    (11,"main","user","Too old",stamp-8*86400,"tg11",1,0,None)]
                db.executemany("INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?)", rows)
            result = cc.recent_dialogue(home, state, self.instant)
            self.assertEqual({row["source_id"] for row in result["messages"]}, {1,2,10})
            self.assertEqual(result["redacted_messages"], 1)

    def test_unconfigured_reader_never_guesses_a_chat(self):
        with tempfile.TemporaryDirectory() as directory:
            result = cc.recent_dialogue(Path(directory), Path(directory), self.instant)
            self.assertEqual(result, {"status": "not_configured", "messages": [], "watermark": 0})


if __name__ == "__main__":
    unittest.main()
