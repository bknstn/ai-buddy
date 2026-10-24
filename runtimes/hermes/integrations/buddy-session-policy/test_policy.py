"""Behavior tests; native-store checks run when Hermes is on PYTHONPATH."""
import asyncio
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import importlib.util
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

os.environ["ASSISTANT_TIMEZONE"] = "America/Los_Angeles"

spec = importlib.util.spec_from_file_location("buddy_session_policy", Path(__file__).with_name("__init__.py"))
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)
NOW = datetime(2026, 10, 5, 8, tzinfo=timezone.utc)
OLD = NOW - timedelta(days=1)
NATIVE = importlib.util.find_spec("gateway") is not None


class TimezoneConfigTests(unittest.TestCase):
    def test_private_profile_timezone_environment_is_used(self):
        with patch.dict(os.environ, {"ASSISTANT_TIMEZONE": "UTC"}):
            self.assertEqual(policy.configured_timezone().key, "UTC")


def event(text="Привет, помоги с новой задачей", **changes):
    source = SimpleNamespace(platform=SimpleNamespace(value="telegram"), chat_id="42",
        user_id="42", chat_type="dm", thread_id=None, profile=None, is_bot=False)
    value = SimpleNamespace(text=text, source=source, timestamp=NOW, internal=False,
        allow_gateway_control=True, message_id="101", raw_message=None, metadata={},
        message_type=SimpleNamespace(value="text"))
    value.__dict__.update(changes)
    return value


class AsyncStore:
    def __init__(self, store):
        self.store = store

    def __getattr__(self, name):
        async def call(*args, **kwargs):
            return getattr(self.store, name)(*args, **kwargs)
        return call


class Store:
    def __init__(self):
        self.entry = SimpleNamespace(session_id="old", created_at=OLD, metadata={})
        self.reset_count = 0
        self.background = False
        self.reset_error = False

    def get_or_create_session(self, source, **kwargs):
        return self.entry

    def get_session_metadata(self, key, name, default=None):
        return self.entry.metadata.get(name, default)

    def set_session_metadata(self, key, name, value):
        self.entry.metadata[name] = value
        return True

    def reset_session(self, key):
        if self.reset_error:
            raise sqlite3.OperationalError("synthetic failure")
        self.reset_count += 1
        self.entry = SimpleNamespace(session_id="new", created_at=NOW, metadata={})
        return self.entry

    def _has_active_processes_safe(self, key, **kwargs):
        return self.background


class Gateway:
    def __init__(self, store=None):
        self.session_store = store or Store()
        self.async_session_store = AsyncStore(self.session_store)
        self.generation = 7
        self.calls, self.received = [], []
        self.authorized = True
        self.pending_sentinel = object()
        self.lease = object()
        self._queued_events = {}
        self._transcribe_pending_audio_event_once = AsyncMock(return_value=(None, []))

    def _is_user_authorized_for_source(self, source):
        return self.authorized

    def _is_session_run_current(self, key, generation):
        return generation == self.generation

    async def _cleanup_old_agent_for_reset(self, key):
        self.calls.append("cleanup")

    def _evict_cached_agent(self, key):
        self.calls.append("evict")

    def _clear_conversation_scope(self, key, **kwargs):
        self.calls.append("clear")
        self._queued_events.pop(key, None)

    async def _fire_session_reset_hooks(self, source, key, old, new):
        self.calls.append(("finalize", old, new))

    async def _handle_message_with_agent(self, value, source, key, generation):
        self.received.append((value, self.session_store.get_or_create_session(source).session_id))
        return "Ordinary reply"


class GreetingTests(unittest.TestCase):
    def test_opening_greetings(self):
        for text in ("Привет", "  ПРИВЕТ!", "Привет, assistant. Новая задача", "Доброе утро!", "Привет\nПомоги"):
            with self.subTest(text=text):
                self.assertTrue(policy.starts_new_day(text))

    def test_mention_quote_and_prefix_are_not_greetings(self):
        for text in ("Передай привет", '«Привет»', '"Привет"', "> привет", "Приветствие", "Приветливый", "", "/new"):
            with self.subTest(text=text):
                self.assertFalse(policy.starts_new_day(text))

    def test_explicit_continuation_overrides_greeting(self):
        for text in ("Привет, продолжим вчерашнее", "Доброе утро, продолжаем", "Привет, вернёмся к задаче", "Привет, не сбрасывай сессию", "Привет, без новой сессии"):
            with self.subTest(text=text):
                self.assertFalse(policy.starts_new_day(text))

    def test_configured_midnight_dst_and_naive_utc(self):
        self.assertEqual(policy.local_day(datetime(2026, 10, 5, 7, 1, tzinfo=timezone.utc)), "2026-10-05")
        self.assertEqual(policy.local_day(datetime(2026, 10, 5, 7, 1)), "2026-10-05")
        self.assertEqual(policy.local_day(datetime(2026, 11, 2, 8, 1, tzinfo=timezone.utc)), "2026-11-02")
        with self.assertRaises(ValueError):
            policy.local_day(None)

    def test_scope_rejects_untrusted_or_other_conversations(self):
        for changes in ({"internal": True}, {"allow_gateway_control": False}, {"message_id": None},
                        {"raw_message": SimpleNamespace(forward_origin=object())},
                        {"metadata": {"forwarded": True}}):
            self.assertFalse(policy.is_owner_input(event(**changes), "42", "42"))
        for changes in ({"chat_id": "43"}, {"user_id": "43"}, {"thread_id": "5"},
                        {"chat_type": "group"}, {"profile": "other-profile"}, {"is_bot": True},
                        {"platform": SimpleNamespace(value="email")}):
            value = event()
            value.source.__dict__.update(changes)
            self.assertFalse(policy.is_owner_input(value, "42", "42"))
        self.assertFalse(policy.is_owner_input(event(), "", ""))
        self.assertTrue(policy.is_owner_input(event(), "42", "42"))


class PolicyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.human = self.stack.enter_context(patch.object(policy, "last_human_day", return_value="2026-10-04"))
        self.background = self.stack.enter_context(patch.object(policy, "active_background_work", return_value=False))
        self.reset_hook = Mock()
        self.tool_reset = Mock()
        self.stack.enter_context(patch.dict(sys.modules, {
            "gateway.slash_commands_session": SimpleNamespace(_reset_process_scoped_tool_state=self.tool_reset),
            "hermes_cli.lifecycle": SimpleNamespace(invoke_hook=self.reset_hook)}))
        self.value, self.gateway = event(), Gateway()
        self.policy = policy.SessionPolicy("/tmp/synthetic-assistant-home", "42", "42")
        self.policy.attach(self.gateway)

    async def run_turn(self, value=None):
        value = value or self.value
        return await self.gateway._handle_message_with_agent(value, value.source, "dm-key", 7)

    async def test_greeting_rotates_and_keeps_entire_task_and_turn_owner(self):
        sentinel, lease = self.gateway.pending_sentinel, self.gateway.lease
        self.assertEqual(await self.run_turn(), "Ordinary reply")
        self.assertEqual(self.gateway.session_store.reset_count, 1)
        self.assertIs(self.gateway.received[0][0], self.value)
        self.assertEqual(self.gateway.received[0][1], "new")
        self.assertEqual(self.value.text, "Привет, помоги с новой задачей")
        self.assertEqual(self.gateway.calls, ["cleanup", "evict", "clear", ("finalize", "old", "new")])
        self.assertIs(self.gateway.pending_sentinel, sentinel)
        self.assertIs(self.gateway.lease, lease)
        self.assertEqual(self.gateway.generation, 7)
        self.reset_hook.assert_called_once()
        self.tool_reset.assert_called_once()

    async def test_repeated_greeting_and_duplicate_after_reload_do_not_rotate(self):
        await self.run_turn()
        await self.run_turn()
        self.policy.unload()
        self.policy = policy.SessionPolicy("/tmp/synthetic-assistant-home", "42", "42")
        self.policy.attach(self.gateway)
        await self.run_turn()
        self.assertEqual(self.gateway.session_store.reset_count, 1)

    async def test_no_greeting_continues_across_days_and_later_greeting_stays(self):
        await self.run_turn(event("Продолжим вчерашнюю задачу"))
        await self.run_turn()
        self.assertEqual(self.gateway.session_store.reset_count, 0)
        self.assertEqual(self.gateway.received[-1][1], "old")

    async def test_same_day_and_explicit_continuation_do_not_rotate(self):
        self.human.return_value = "2026-10-05"
        await self.run_turn()
        self.human.return_value = "2026-10-04"
        await self.run_turn(event("Привет, продолжим вчерашнее"))
        self.assertEqual(self.gateway.session_store.reset_count, 0)

    async def test_fresh_manual_session_does_not_rotate_again(self):
        self.gateway.session_store.entry.created_at = NOW
        await self.run_turn()
        self.assertEqual(self.gateway.session_store.reset_count, 0)

    async def test_first_conversation_does_not_create_extra_boundary(self):
        self.human.return_value = None
        await self.run_turn()
        self.assertEqual(self.gateway.session_store.reset_count, 0)

    async def test_foreign_unauthorized_internal_forwarded_input_has_no_effect(self):
        for value in (event(internal=True), event(raw_message=SimpleNamespace(forward_origin=object())), event(allow_gateway_control=False)):
            await self.run_turn(value)
        self.gateway.authorized = False
        await self.run_turn()
        self.assertEqual(self.gateway.session_store.reset_count, 0)
        self.human.assert_not_called()
        self.assertEqual(self.gateway.session_store.entry.metadata, {})

    async def test_background_task_prevents_reset(self):
        self.background.return_value = True
        await self.run_turn()
        self.assertEqual(self.gateway.session_store.reset_count, 0)
        self.assertEqual(self.gateway.received[0][1], "old")
        self.assertEqual(self.gateway.calls, [])

    async def test_followup_queued_during_cleanup_survives_boundary(self):
        followup = event("Ещё одна просьба", message_id="102")
        async def cleanup(key):
            self.gateway._queued_events[key] = [followup]
        self.gateway._cleanup_old_agent_for_reset = cleanup
        await self.run_turn()
        self.assertEqual(self.gateway._queued_events["dm-key"], [followup])

    async def test_steering_recorded_today_overrides_stale_metadata(self):
        self.gateway.session_store.entry.metadata[policy.STATE_KEY] = {"last_human_day": "2026-10-04"}
        self.human.return_value = "2026-10-05"
        await self.run_turn()
        self.assertEqual(self.gateway.session_store.reset_count, 0)

    async def test_voice_uses_cached_native_transcript_without_rewriting_event(self):
        voice = event("", message_type=SimpleNamespace(value="voice"))
        self.gateway._transcribe_pending_audio_event_once.return_value = ('"Привет, новая задача"', ["Привет, новая задача"])
        await self.run_turn(voice)
        self.assertEqual(self.gateway.session_store.reset_count, 1)
        self.assertEqual(voice.text, "")
        self.gateway._transcribe_pending_audio_event_once.assert_awaited_once_with(voice)

    async def test_failed_or_empty_transcription_keeps_conversation(self):
        await self.run_turn(event("", message_type=SimpleNamespace(value="voice")))
        self.assertEqual(self.gateway.session_store.reset_count, 0)

    async def test_store_error_keeps_task_and_old_session(self):
        self.human.side_effect = sqlite3.OperationalError("synthetic failure")
        await self.run_turn()
        self.assertEqual(self.gateway.session_store.reset_count, 0)
        self.assertEqual(self.gateway.received[0][1], "old")

    async def test_failed_reset_keeps_ordinary_turn(self):
        self.gateway.session_store.reset_error = True
        await self.run_turn()
        self.assertEqual(self.gateway.received[0][1], "old")

    async def test_explicit_new_during_cleanup_cancels_stale_policy_turn(self):
        async def explicit_reset(key):
            self.gateway.generation += 1
        self.gateway._cleanup_old_agent_for_reset = explicit_reset
        self.assertIsNone(await self.run_turn())
        self.assertEqual(self.gateway.session_store.reset_count, 0)
        self.assertEqual(self.gateway.received, [])

    async def test_receipt_survives_finalize_failure(self):
        self.gateway._fire_session_reset_hooks = AsyncMock(side_effect=RuntimeError("synthetic failure"))
        await self.run_turn()
        await self.run_turn()
        self.assertEqual(self.gateway.session_store.reset_count, 1)
        self.assertEqual(self.gateway.received[0][1], "new")

    async def test_old_replayed_event_does_not_move_day_backwards(self):
        self.human.return_value = "2026-10-06"
        await self.run_turn()
        self.assertEqual(self.gateway.session_store.reset_count, 0)
        self.assertEqual(self.gateway.session_store.entry.metadata[policy.STATE_KEY]["last_human_day"], "2026-10-06")

    async def test_attach_is_idempotent_and_unload_restores_original(self):
        wrapper = self.gateway._handle_message_with_agent
        self.policy.attach(self.gateway)
        self.assertIs(self.gateway._handle_message_with_agent, wrapper)
        self.policy.unload()
        await self.run_turn()
        self.assertEqual(self.gateway.session_store.reset_count, 0)

    def test_unsupported_gateway_is_left_alone(self):
        # A hashable object with no compatible async turn entry.
        class Unsupported:
            pass
        self.policy.attach(Unsupported())

    def test_changed_turn_signature_is_left_alone(self):
        async def changed_turn(value, source, key, generation, new_required_argument):
            return "unmodified"
        self.gateway._handle_message_with_agent = changed_turn
        separate = policy.SessionPolicy("/tmp/synthetic-assistant-home", "42", "42")
        separate.attach(self.gateway)
        self.assertIs(self.gateway._handle_message_with_agent, changed_turn)


class EvidenceTests(unittest.TestCase):
    def test_real_human_history_includes_archives_but_excludes_other_lanes(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with sqlite3.connect(home / "state.db") as db:
                db.executescript("""CREATE TABLE sessions(id,source,chat_id,user_id,chat_type,thread_id);
                    CREATE TABLE messages(session_id,role,timestamp,platform_message_id,_compressed_summary,observed,display_kind,active);""")
                db.executemany("INSERT INTO sessions VALUES(?,?,?,?,?,?)", [
                    ("main", "telegram", "42", "42", "dm", None),
                    ("topic", "telegram", "42", "42", "dm", "5"),
                    ("other", "telegram", "99", "99", "dm", None)])
                db.executemany("INSERT INTO messages VALUES(?,?,?,?,?,?,?,?)", [
                    ("main", "user", OLD.timestamp(), "100", 0, 0, None, 0),
                    ("main", "assistant", NOW.timestamp(), "101", 0, 0, None, 1),
                    ("main", "user", NOW.timestamp(), None, 0, 0, None, 1),
                    ("main", "user", NOW.timestamp(), "102", 1, 0, None, 1),
                    ("main", "user", NOW.timestamp(), "103", 0, 1, None, 1),
                    ("main", "user", NOW.timestamp(), "104", 0, 0, "internal_notification", 1),
                    ("topic", "user", NOW.timestamp(), "105", 0, 0, None, 1),
                    ("other", "user", NOW.timestamp(), "106", 0, 0, None, 1)])
            self.assertEqual(policy.last_human_day(home, "42", "42"), "2026-10-04")

    def test_background_guard_matches_parent_and_fails_closed(self):
        gateway = Gateway()
        with patch.dict(sys.modules, {"tools.async_delegation": SimpleNamespace(list_async_delegations=lambda: [
            {"status": "running", "session_key": "other", "parent_session_id": "other"},
            {"status": "finalizing", "parent_session_id": "old"}])}):
            self.assertTrue(policy.active_background_work(gateway, "dm-key", gateway.session_store.entry))
        gateway.session_store.background = True
        self.assertTrue(policy.active_background_work(gateway, "dm-key", gateway.session_store.entry))
        gateway.session_store._has_active_processes_safe = Mock(side_effect=RuntimeError("synthetic"))
        self.assertTrue(policy.active_background_work(gateway, "dm-key", gateway.session_store.entry))


@unittest.skipUnless(NATIVE, "Hermes runtime packages are required; use an isolated HERMES_HOME")
class NativeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        import os
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.home = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.stack.enter_context(patch.dict(os.environ, {"HERMES_HOME": str(self.home)}))
        from gateway.config import GatewayConfig, Platform
        from gateway.session import SessionStore, SessionSource
        self.store = SessionStore(self.home / "sessions", GatewayConfig.from_dict({"write_sessions_json": False}))
        self.addCleanup(self.store._db.close)
        self.source = SessionSource(platform=Platform.TELEGRAM, chat_id="42", user_id="42")
        self.entry = self.store.get_or_create_session(self.source)
        self.entry.created_at = OLD.replace(tzinfo=None)
        self.store._save()
        self.store.append_to_transcript(self.entry.session_id, {"role": "user", "content": "Вчерашняя задача",
            "timestamp": OLD.timestamp(), "message_id": "100"})
        self.gateway = Gateway(self.store)
        self.policy = policy.SessionPolicy(self.home, "42", "42")
        self.policy.attach(self.gateway)
        self.stack.enter_context(patch.object(policy, "active_background_work", return_value=False))

    async def run_turn(self, text="Привет, новая задача"):
        value = event(text, source=self.source)
        return await self.gateway._handle_message_with_agent(value, self.source, self.entry.session_key, 7)

    async def test_real_native_boundary_preserves_history_and_metadata_after_recovery(self):
        await self.run_turn()
        fresh = self.store.get_or_create_session(self.source)
        self.assertNotEqual(fresh.session_id, self.entry.session_id)
        self.assertEqual(self.store._db.get_session(self.entry.session_id)["end_reason"], "session_reset")
        self.assertEqual(self.store.load_transcript(self.entry.session_id)[0]["content"], "Вчерашняя задача")
        self.assertEqual(self.store.load_transcript(fresh.session_id), [])
        self.store._entries.clear()
        self.store._loaded = False
        recovered = self.store.get_or_create_session(self.source)
        self.assertEqual(recovered.session_id, fresh.session_id)
        self.assertEqual(recovered.metadata[policy.STATE_KEY]["greeting_message_id"], "101")
        await self.run_turn()
        self.assertEqual(self.store.get_or_create_session(self.source).session_id, fresh.session_id)

    async def test_native_continuation_preserves_current_transcript(self):
        await self.run_turn("Продолжим вчерашнее")
        self.assertEqual(self.store.get_or_create_session(self.source).session_id, self.entry.session_id)
        self.assertIsNone(self.store._db.get_session(self.entry.session_id)["end_reason"])

    async def test_scheduled_mirror_does_not_prevent_native_boundary(self):
        self.store.append_to_transcript(self.entry.session_id, {"role": "user", "content": "Утренний обзор",
            "timestamp": NOW.timestamp(), "display_kind": "internal_notification"})
        await self.run_turn()
        self.assertNotEqual(self.store.get_or_create_session(self.source).session_id, self.entry.session_id)

    async def test_memory_and_continuity_files_survive_boundary(self):
        paths = [self.home / "memories" / "USER.md", self.home / "plugin-data" / "buddy-heartbeat" / "conversation.json"]
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic saved preference")
        await self.run_turn()
        self.assertEqual([p.read_text() for p in paths], ["synthetic saved preference"] * 2)

    def test_native_compressor_uses_absolute_cap(self):
        from agent.context_compressor import ContextCompressor
        compressor = ContextCompressor(model="gpt-6.1-sol", threshold_percent=0.5,
            config_context_length=1050000, threshold_tokens_cap=80000)
        self.assertEqual(compressor.threshold_tokens, 80000)

    def native_runner(self, busy=False):
        from gateway.run import GatewayRunner
        from gateway.session_state import SessionState
        runner = object.__new__(GatewayRunner)
        runner.config = self.store.config
        runner.session_store = self.store
        runner._async_session_store = AsyncStore(self.store)
        runner._sessions = {self.entry.session_key: SessionState()}
        runner._session_state(self.entry.session_key).persistent.run_generation = 7
        runner._scale_to_zero_note_real_inbound = Mock()
        runner._is_user_authorized_for_source = lambda source: self.gateway.authorized
        runner._admit_bot_message_for_source = lambda source: True
        runner._get_unauthorized_dm_behavior = lambda *a, **kw: "ignore"
        runner._hm_estop_gate = Mock(return_value=None)
        runner._hm_pending_reply_intercepts = AsyncMock(return_value=None)
        runner._hm_evict_idle_stale_agent = Mock()
        runner._hm_evict_reaped_agent = Mock()
        runner._is_session_running = Mock(return_value=busy)
        runner._hm_handle_running_session_message = AsyncMock(return_value="Работа продолжается")
        runner._hm_dispatch_idle_commands = AsyncMock(return_value=(False, None))
        runner._is_telegram_topic_root_lobby = Mock(return_value=False)
        runner._external_drain_active = False
        runner._claim_active_session_slot = Mock(return_value=(None, None))
        runner._hm_rescue_orphaned_fifo = lambda value, source, internal, key: (value, source, internal)
        runner._persist_active_agents = Mock()
        runner._begin_session_run_generation = Mock(return_value=7)
        runner._run_post_turn_hooks = AsyncMock()
        runner._restore_pending_one_turn_model_override = Mock()
        runner._clear_durable_active_turn = AsyncMock()
        runner._release_running_agent_state = Mock()
        runner._release_turn_lease = Mock()
        runner._cleanup_old_agent_for_reset = self.gateway._cleanup_old_agent_for_reset
        runner._evict_cached_agent = self.gateway._evict_cached_agent
        runner._fire_session_reset_hooks = self.gateway._fire_session_reset_hooks
        runner._handle_message_with_agent = self.gateway._handle_message_with_agent
        # The actual lifecycle call site in _hm_admit_event installs our bridge.
        def hooks(name, **kwargs):
            if name == "pre_gateway_dispatch":
                self.policy.attach(kwargs["gateway"])
            return []
        self.stack.enter_context(patch("hermes_cli.plugins.invoke_hook", side_effect=hooks))
        # v0.21.7 dispatches this lifecycle hook asynchronously; retain the
        # synchronous mock for compatibility checks against v0.21.3.
        import hermes_cli.plugins as plugins
        if hasattr(plugins, "ainvoke_hook"):
            async def async_hooks(name, **kwargs):
                return hooks(name, **kwargs)
            self.stack.enter_context(patch.object(plugins, "ainvoke_hook", side_effect=async_hooks))
        return runner

    async def test_native_gateway_dispatch_keeps_response_generation_and_queue(self):
        runner = self.native_runner()
        # Restore the unwrapped agent stub before the real hook attaches once.
        self.policy.unload()
        self.policy = policy.SessionPolicy(self.home, "42", "42")
        runner._handle_message_with_agent = self.gateway._handle_message_with_agent
        value = event(source=self.source)
        value.is_command = lambda: False
        value.get_command = lambda: None
        key = self.entry.session_key
        later = event("Ещё одна просьба", source=self.source, message_id="102")
        async def cleanup(unused):
            runner._queued_events[key] = [later]
        runner._cleanup_old_agent_for_reset = cleanup
        self.assertEqual(await runner._handle_message(value), "Ordinary reply")
        self.assertNotEqual(self.store.get_or_create_session(self.source).session_id, self.entry.session_id)
        self.assertEqual(runner._session_state(key).persistent.run_generation, 7)
        self.assertEqual(runner._queued_events[key], [later])
        runner._release_running_agent_state.assert_called_once_with(key, run_generation=7)
        self.assertIs(self.gateway.received[0][0], value)

    async def test_native_gateway_busy_path_keeps_old_work_and_session(self):
        runner = self.native_runner(busy=True)
        value = event(source=self.source)
        value.get_command = lambda: None
        self.assertEqual(await runner._handle_message(value), "Работа продолжается")
        self.assertEqual(self.store.get_or_create_session(self.source).session_id, self.entry.session_id)
        self.assertEqual(self.gateway.received, [])

    async def test_native_gateway_auth_rejection_cannot_change_session(self):
        runner = self.native_runner()
        self.gateway.authorized = False
        self.assertIsNone(await runner._handle_message(event(source=self.source)))
        self.assertEqual(self.store.get_or_create_session(self.source).session_id, self.entry.session_id)
        self.assertEqual(self.store.get_session_metadata(self.entry.session_key, policy.STATE_KEY, {}), {})


if __name__ == "__main__":
    unittest.main()
