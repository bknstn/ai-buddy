"""Installed-runtime contracts. Requires an isolated runtime; no production transport/state."""
import asyncio
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace as N
import unittest

from test_progress import m

HAS_RUNTIME = importlib.util.find_spec("gateway") is not None


@unittest.skipUnless(HAS_RUNTIME, "Hermes runtime packages are not installed")
class Native(unittest.IsolatedAsyncioTestCase):
    async def test_public_registration_survives_probe_outside_turn(self):
        from model_tools import get_tool_definitions
        from tools.registry import registry
        from test_progress import Gateway, source
        previous = registry.snapshot_registration("buddy_progress")
        unload = []
        ctx = N(get_config=lambda key, default=None: {"chat_id": "1", "user_id": "2"}.get(key, default),
                register_tool=lambda **kw: registry.register(**kw),
                register_hook=lambda *a, **k: None, on_unload=unload.append)
        m.register(ctx)
        registered = registry.snapshot_registration("buddy_progress")
        try:
            outside = get_tool_definitions(enabled_toolsets=["messaging"], quiet_mode=True)
            self.assertIn("tool_call", [x["function"]["name"] for x in outside])
            raw = get_tool_definitions(enabled_toolsets=["messaging"], quiet_mode=True,
                                       skip_tool_search_assembly=True)
            self.assertIn("buddy_progress", [x["function"]["name"] for x in raw])
            self.assertIn('"registered": false', registered.handler({"stage": "Review the route"}))
            policy = registered.handler.__self__
            turn = m.Turn(policy, Gateway(), source(), "main", 1,
                          asyncio.get_running_loop(), policy.clock())
            token = m.CURRENT.set(turn)
            try:
                inside = get_tool_definitions(enabled_toolsets=["messaging"], quiet_mode=True)
                self.assertIn("tool_call", [x["function"]["name"] for x in inside])
                from model_tools import handle_function_call
                answer = await asyncio.to_thread(handle_function_call, "tool_call",
                    {"calls": [{"name": "buddy_progress", "arguments": {"stage": "Review the route"}}]},
                    enabled_toolsets=["messaging"])
                self.assertIn('"registered": true', answer)
            finally:
                m.CURRENT.reset(token)
        finally:
            for fn in unload: fn()
            registry.restore_registration("buddy_progress", registered, previous)

    async def test_actual_gateway_bridge_and_executor_commentary(self):
        import pytest
        from gateway.run import GatewayRunner
        root = Path(sys.modules[GatewayRunner.__module__].__file__).parent.parent
        spec = importlib.util.spec_from_file_location("buddy_native_progress_harness",
                    root / "tests/gateway/test_run_progress_topics.py")
        harness = importlib.util.module_from_spec(spec); spec.loader.exec_module(harness)
        policy = m.LiveProgress("123", "owner", waiting=lambda _: False)
        captured = []
        turns = []
        adapters = []
        make = harness._make_runner

        def make_runner(adapter):
            adapters.append(adapter)
            runner = make(adapter)
            runner._is_session_run_current = lambda *args: True
            policy.attach(runner)
            self.assertIn(runner, policy.bindings, "real private signatures changed")
            original = runner._run_agent

            async def live(**kw):
                turn = m.Turn(policy, runner, kw["source"], kw["session_key"],
                              kw.get("run_generation"), asyncio.get_running_loop(), policy.clock())
                turns.append((turn, turn.last_visible))
                token = m.CURRENT.set(turn)
                policy.turns.add(turn);policy.observe(adapter)
                turn.task = asyncio.create_task(policy.watch(turn))
                try:
                    return await original(**kw)
                finally:
                    await turn.finish();policy.turns.discard(turn);m.CURRENT.reset(token)
            runner._run_agent = live
            return runner

        class Agent:
            def __init__(self, **kw):
                self.tools = []
                self.interim_assistant_callback = kw.get("interim_assistant_callback")

            def run_conversation(self, *args, **kw):
                captured.append(policy.handle({"stage": "Review next steps"}))
                self.interim_assistant_callback("I found a useful option and am checking the details.")
                deadline = time.monotonic() + 3
                while not adapters[0].sent and time.monotonic() < deadline:
                    time.sleep(0.01)
                return {"final_response": "Итог проверки", "messages": [], "api_calls": 1}

        with tempfile.TemporaryDirectory(prefix="buddy-native-progress-") as td, pytest.MonkeyPatch.context() as patch:
            patch.setattr(harness, "_make_runner", make_runner)
            adapter, result = await harness._run_with_agent(patch, Path(td), Agent,
                session_id="synthetic-progress", platform=harness.Platform.TELEGRAM,
                chat_id="123", chat_type="dm", thread_id=None, user_id="owner",
                config_data={"streaming": {"enabled": False}, "display": {"platforms": {
                    "telegram": {"interim_assistant_messages": True, "tool_progress": False,
                                 "streaming": False, "long_running_notifications": False}}}})
            self.assertIn('"registered": true', captured[0])
            self.assertEqual([s["content"] for s in adapter.sent], ["I found a useful option and am checking the details."])
            self.assertFalse(adapter.edits)
            self.assertGreater(turns[0][0].last_visible, turns[0][1], "native delivered commentary must reset silence")
            self.assertEqual(result["final_response"], "Review complete")
            self.assertFalse(policy.turns)
        policy.unload()

    async def test_native_pending_approval_and_clarify_queues(self):
        from tools import approval, clarify_gateway
        key = "buddy-live-progress-synthetic-approval"
        self.assertFalse(m.user_waiting(key))
        entry = clarify_gateway.register("buddy-progress-clarify", key, "Synthetic?", None)
        try:
            self.assertTrue(m.user_waiting(key))
        finally:
            clarify_gateway.clear_session(key)
        self.assertFalse(m.user_waiting(key))
        with approval._lock:
            approval._gateway_queues[key] = [object()]
        try:
            self.assertTrue(m.user_waiting(key))
        finally:
            with approval._lock:
                approval._gateway_queues.pop(key, None)


if __name__ == "__main__":
    unittest.main()
