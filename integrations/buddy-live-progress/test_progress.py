import asyncio
from contextlib import contextmanager
import importlib.util
from pathlib import Path
from types import SimpleNamespace as N
import sys
import unittest

spec = importlib.util.spec_from_file_location("buddy_live_progress_tests", Path(__file__).with_name("__init__.py"))
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


class Adapter:
    def __init__(self):
        self.sent = []
        self.ok = True
        self.block = None

    async def send(self, chat, text, reply_to=None, metadata=None):
        if self.block:
            await self.block.wait()
        self.sent.append((chat, text, metadata))
        return N(success=self.ok, message_id=str(len(self.sent)) if self.ok else None)


def source(**kw):
    return N(**({"platform": "telegram", "chat_id": "1", "user_id": "2", "chat_type": "dm",
                 "thread_id": None, "profile": "default"} | kw))


def event(**kw):
    return N(**({"internal": False, "message_id": "human-1", "text": "проверь маршрут"} | kw))


class Gateway:
    def __init__(self):
        self.config = N(multiplex_profiles=False)
        self.adapter = Adapter()
        self.generation = 1
        self.authorized = True
        self.work = None

    def _is_user_authorized_for_source(self, src):
        return self.authorized

    def _is_session_run_current(self, key, generation):
        return key == "main" and generation == self.generation

    def _delivery_adapter_for(self, src):
        return self.adapter

    async def _handle_message_with_agent(self, ev, src, key, generation):
        return await self.work() if self.work else "result"

    async def _run_agent_await_turn_worker(self, worker, ctx, interrupted, monitor):
        return await worker.executor_task

    def _run_agent_start_turn_worker(self, ctx, run_sync):
        return N(executor_task=asyncio.create_task(asyncio.to_thread(run_sync)))

    async def _hmwa_agent_error_reply(self, error, ev, src, entry, key, prepared):
        await self.adapter.send(src.chat_id, "failure")
        return "failure"


class Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.clock = [0.0]
        self.paused = [False]
        self.policy = m.LiveProgress("1", "2", interval=80,
            clock=lambda: self.clock[0], waiting=lambda _: self.paused[0])
        self.gateway = Gateway()

    @contextmanager
    def active(self):
        turn = m.Turn(self.policy, self.gateway, source(), "main", 1,
                      asyncio.get_running_loop(), self.clock[0])
        token = m.CURRENT.set(turn)
        self.policy.observe(self.gateway.adapter)
        try:
            yield turn
        finally:
            turn.closed = True
            m.CURRENT.reset(token)

    async def test_delivered_commentary_restarts_silence_clock(self):
        with self.active() as turn:
            self.clock[0] = 70
            await self.gateway.adapter.send("1", "Проверю пересадку", metadata={"_interim_send": True})
            self.clock[0] = 100
            self.assertFalse(await self.policy.tick(turn))
            self.assertEqual(len(self.gateway.adapter.sent), 1)
            self.clock[0] = 150
            self.assertTrue(await self.policy.tick(turn))

    async def test_no_status_before_interval_and_no_topic_invention(self):
        with self.active() as turn:
            self.clock[0] = 79
            self.assertFalse(await self.policy.tick(turn))
            self.clock[0] = 80
            self.assertTrue(await self.policy.tick(turn))
            self.assertNotIn("пересад", self.gateway.adapter.sent[-1][1])

    async def test_stage_from_tool_and_thread_context(self):
        with self.active() as turn:
            result = await asyncio.to_thread(self.policy.handle, {"stage": "Проверка пересадки"})
            self.assertIn('"registered": true', result)
            self.assertEqual(self.gateway.adapter.sent, [])
            self.clock[0] = 80
            await self.policy.tick(turn)
            self.assertIn("Проверка пересадки", self.gateway.adapter.sent[0][1])
            self.assertTrue(self.gateway.adapter.sent[0][2]["_interim_send"])

    async def test_rejected_labels_never_replace_declared_topic(self):
        with self.active() as turn:
            self.assertTrue(turn.declare("Сверка источников"))
            for stage in [None, "x", "x"*101, "web_search", "почти готово", "run /tmp/x",
                          "[ссылка](https://example.com)", "первая\nвторая", "<script>", "10%"]:
                self.assertFalse(turn.declare(stage), stage)
            self.assertEqual(turn.stage, "Сверка источников")

    async def test_final_failed_and_other_chat_sends_do_not_claim_progress(self):
        with self.active() as turn:
            self.clock[0] = 40
            await self.gateway.adapter.send("1", "final")
            await self.gateway.adapter.send("9", "unrelated", metadata={"_interim_send": True})
            self.gateway.adapter.ok = False
            await self.gateway.adapter.send("1", "failed", metadata={"_interim_send": True})
            self.assertEqual(turn.last_visible, 0)

    async def test_positional_metadata_is_recorded(self):
        with self.active() as turn:
            self.clock[0] = 42
            await self.gateway.adapter.send("1", "commentary", None, {"_interim_send": True})
            self.assertEqual(turn.last_visible, 42)

    async def test_waiting_for_user_suppresses_and_resets_clock(self):
        with self.active() as turn:
            self.clock[0] = 90
            self.paused[0] = True
            self.assertFalse(await self.policy.tick(turn))
            self.paused[0] = False
            self.clock[0] = 100
            self.assertFalse(await self.policy.tick(turn))
            self.assertEqual(self.gateway.adapter.sent, [])

    async def test_pending_state_failure_fails_closed_without_breaking_work(self):
        with self.active() as turn:
            def broken(_):
                raise RuntimeError("private data must never be logged")
            self.policy.waiting = broken
            self.clock[0] = 90
            with self.assertLogs(m.log, level="WARNING") as logs:
                self.assertFalse(await self.policy.tick(turn))
            self.assertNotIn("private data", str(logs.output))
            self.assertEqual(self.gateway.adapter.sent, [])

    async def test_failed_send_is_paced_without_stopping_task(self):
        with self.active() as turn:
            self.gateway.adapter.ok = False
            self.clock[0] = 90
            self.assertFalse(await self.policy.tick(turn))
            self.assertFalse(await self.policy.tick(turn))
            self.assertEqual(len(self.gateway.adapter.sent), 1)

    async def test_cancel_restart_drain_and_worker_completion_suppress_status(self):
        for flag in ["generation", "_draining", "_external_drain_active", "_restart_requested", "worker"]:
            with self.subTest(flag=flag), self.active() as turn:
                self.clock[0] += 90
                if flag == "generation":
                    self.gateway.generation = 2
                elif flag == "worker":
                    f = asyncio.get_running_loop().create_future(); f.set_result("done")
                    turn.worker = N(executor_task=f)
                else:
                    setattr(self.gateway, flag, True)
                self.assertFalse(await self.policy.tick(turn))
                self.gateway.generation = 1
                if flag not in ("generation", "worker"):
                    setattr(self.gateway, flag, False)
        self.assertEqual(self.gateway.adapter.sent, [])

    async def test_scope_excludes_internal_topics_other_users_and_commands(self):
        self.policy.attach(self.gateway)
        observed = []
        async def work():
            observed.append(self.policy.available())
            return "result"
        self.gateway.work = work
        for ev, src in [(event(internal=True), source()), (event(), source(thread_id="topic")),
                        (event(), source(user_id="other")), (event(), source(chat_id="other")),
                        (event(text="/status"), source()), (event(), source(platform="email")),
                        (event(), source(profile="tutor"))]:
            await self.gateway._handle_message_with_agent(ev, src, "main", 1)
        self.assertEqual(observed, [False]*7)
        self.assertEqual(self.policy.turns, set())

    async def test_authorization_precedes_any_progress(self):
        self.policy.attach(self.gateway)
        self.gateway.authorized = False
        async def work():
            self.assertFalse(self.policy.available())
        self.gateway.work = work
        await self.gateway._handle_message_with_agent(event(), source(), "main", 1)
        self.assertEqual(self.gateway.adapter.sent, [])

    async def test_worker_closes_progress_before_final_and_queued_followup(self):
        self.policy.attach(self.gateway)
        async def work():
            turn = m.CURRENT.get()
            self.assertTrue(self.policy.available())
            f = asyncio.get_running_loop().create_future(); f.set_result("result")
            await self.gateway._run_agent_await_turn_worker(
                N(executor_task=f), N(session_key="main", run_generation=1, scheduled_heartbeat=False), None, None)
            self.assertTrue(turn.closed)
            self.clock[0] = 1000
            self.assertFalse(await self.policy.tick(turn))
            await self.gateway.adapter.send("1", "final")
        self.gateway.work = work
        await self.gateway._handle_message_with_agent(event(), source(), "main", 1)
        self.assertEqual([x[1] for x in self.gateway.adapter.sent], ["final"])
        self.assertFalse(self.policy.available())

    async def test_error_path_closes_progress_before_error_reply(self):
        self.policy.attach(self.gateway)
        async def work():
            turn = m.CURRENT.get()
            await self.gateway._hmwa_agent_error_reply(Exception(), event(), source(), None, "main", None)
            self.assertTrue(turn.closed)
            self.clock[0] = 1000
            self.assertFalse(await self.policy.tick(turn))
        self.gateway.work = work
        await self.gateway._handle_message_with_agent(event(), source(), "main", 1)
        self.assertEqual([x[1] for x in self.gateway.adapter.sent], ["failure"])

    async def test_finish_waits_for_inflight_waiting_send_before_final(self):
        with self.active() as turn:
            self.gateway.adapter.block = asyncio.Event()
            self.clock[0] = 90
            turn.task = asyncio.create_task(self.policy.tick(turn))
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            closing = asyncio.create_task(turn.finish())
            await asyncio.sleep(0)
            self.assertFalse(closing.done())
            self.gateway.adapter.block.set()
            await closing
            await self.gateway.adapter.send("1", "final")
            self.assertEqual(self.gateway.adapter.sent[-1][1], "final")

    async def test_inflight_native_commentary_prevents_duplicate_waiting_bubble(self):
        with self.active() as turn:
            self.gateway.adapter.block = asyncio.Event()
            self.clock[0] = 90
            sending = asyncio.create_task(self.gateway.adapter.send(
                "1", "Нашёл варианты", metadata={"_interim_send": True}))
            await asyncio.sleep(0)
            self.assertEqual(turn.interim_inflight, 1)
            self.assertFalse(await self.policy.tick(turn))
            self.gateway.adapter.block.set()
            await sending
            self.assertEqual([x[1] for x in self.gateway.adapter.sent], ["Нашёл варианты"])

    async def test_attach_idempotent_and_unload_restores_methods(self):
        original = self.gateway._handle_message_with_agent
        adapter_send = self.gateway.adapter.send
        self.policy.attach(self.gateway)
        wrapper = self.gateway._handle_message_with_agent
        self.policy.attach(self.gateway)
        self.assertIs(wrapper, self.gateway._handle_message_with_agent)
        self.policy.observe(self.gateway.adapter)
        self.policy.unload()
        self.assertEqual(original, self.gateway._handle_message_with_agent)
        self.assertEqual(adapter_send, self.gateway.adapter.send)
        self.assertFalse(self.policy.enabled)

    async def test_bridge_mismatch_leaves_native_handler_intact(self):
        self.gateway._run_agent_await_turn_worker = None
        original = self.gateway._handle_message_with_agent
        with self.assertLogs(m.log, level="ERROR"):
            self.policy.attach(self.gateway)
        self.assertEqual(original, self.gateway._handle_message_with_agent)

    async def test_no_tool_state_outside_turn_or_in_second_policy(self):
        self.assertFalse(self.policy.available())
        self.assertIn('"registered": false', self.policy.handle({"stage": "Проверка маршрута"}))
        with self.active():
            other = m.LiveProgress("1", "2")
            self.assertFalse(other.available())
            self.assertIn('"registered": false', other.handle({"stage": "Проверка маршрута"}))

    async def test_queued_human_gets_new_phase_and_internal_queue_stays_quiet(self):
        self.policy.attach(self.gateway)
        async def work():
            root = m.CURRENT.get()
            await root.finish()
            for kind, expected in [(None, True), ("internal_notification", False)]:
                ctx = N(source=source(), session_key="main", run_generation=1,
                        scheduled_heartbeat=False, inbound_message_id="queued-human",
                        persist_user_display_kind=kind)
                def run():
                    current = m.CURRENT.get()
                    return (self.policy.available(), current.stage)
                worker = self.gateway._run_agent_start_turn_worker(ctx, run)
                result = await self.gateway._run_agent_await_turn_worker(worker, ctx, None, None)
                self.assertEqual(result, (expected, ""))
                self.assertIs(m.CURRENT.get(), root)
        self.gateway.work = work
        await self.gateway._handle_message_with_agent(event(), source(), "main", 1)
        self.assertEqual(self.policy.turns, set())


if __name__ == "__main__":
    unittest.main()
