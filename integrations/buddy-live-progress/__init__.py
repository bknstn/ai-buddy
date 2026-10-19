"""Owner-DM progress; no polling/model calls, persisted task text or core edits.

Public pre-dispatch/tool registration with a guarded instance-local bridge to
v0.21.7 turn ownership and completion. Missing contracts disable the bridge.
"""
import asyncio
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
import inspect
import json
import logging
import re
import threading
import time
import weakref

log = logging.getLogger(__name__)
CURRENT = ContextVar("buddy_live_progress", default=None)
UNSAFE_STAGE = re.compile(
    r"[\r\n<>`\\/\[\]{}$%]|https?:|\b(?:hermes|cron|heartbeat|web_search|"
    r"terminal|job_id|run_id|почти|готово|завершено)\b", re.I)
SCHEMA = {
    "name": "buddy_progress",
    "description": (
        "Declare the current human-readable stage of a substantial live task for "
        "Buddy's waiting notice. Does NOT send a message. Give one brief natural "
        "commentary alongside this call. Update only at meaningful stage changes, "
        "not for every tool. No completion claims, secrets, commands or tool names. "
        "Unavailable outside the owner's live conversation; never use in scheduled jobs."
    ),
    "parameters": {"type": "object", "properties": {
        "stage": {"type": "string", "description":
                  "Short noun phrase in the user's language, e.g. Проверка пересадки or Сверка источников отчёта."}},
        "required": ["stage"], "additionalProperties": False},
}


def owner_input(event, source, chat_id, user_id):
    platform = getattr(source, "platform", None)
    return bool(chat_id and user_id and source
        and getattr(platform, "value", platform) == "telegram"
        and source.chat_type == "dm" and not source.thread_id
        and str(source.chat_id) == chat_id and str(source.user_id) == user_id
        and getattr(source, "profile", None) in (None, "default")
        and not getattr(source, "is_bot", False)
        and not getattr(event, "internal", False)
        and getattr(event, "allow_gateway_control", True)
        and getattr(event, "message_id", None)
        and not (getattr(event, "text", "") or "").lstrip().startswith("/"))


def user_waiting(key):
    """Native queues, not guessed tool descriptions. Failure suppresses fallback."""
    from tools.approval import has_blocking_approval
    from tools.clarify_gateway import has_pending
    return has_blocking_approval(key) or has_pending(key)


@dataclass(eq=False)
class Turn:
    policy: object
    gateway: object
    source: object
    key: str
    generation: int
    loop: object
    last_visible: float
    stage: str = ""
    closed: bool = False
    task: object = None
    worker: object = None
    parent: object = None
    context_token: object = None
    interim_inflight: int = 0
    changed: object = field(default_factory=asyncio.Event)
    lock: object = field(default_factory=threading.RLock)

    def current(self):
        try:
            return (self.policy.enabled and not self.closed
                and not getattr(self.gateway, "_draining", False)
                and not getattr(self.gateway, "_external_drain_active", False)
                and not getattr(self.gateway, "_restart_requested", False)
                and self.gateway._is_session_run_current(self.key, self.generation)
                and not (self.worker and self.worker.executor_task.done()))
        except Exception:
            return False

    def received(self):
        with self.lock:
            self.last_visible = self.policy.clock()

    def declare(self, stage):
        if not isinstance(stage, str):
            return False
        stage = stage.strip()
        if not 3 <= len(stage) <= 100 or UNSAFE_STAGE.search(stage):
            return False
        with self.lock:
            if not self.current():
                return False
            self.stage = stage
        return True

    def waiting_text(self):
        with self.lock:
            stage = self.stage
        if stage:
            return f"Ещё готовлю результат по теме «{stage}». Готового ответа пока нет."
        # Before the model can declare a stage, do not fabricate a task summary.
        return "Подготовка ответа затянулась — готового результата пока нет."

    async def finish(self):
        self.closed = True
        self.changed.set()
        if self.task and self.task is not asyncio.current_task():
            # The sender is bounded; let any in-flight status finish BEFORE final delivery.
            await self.task


class LiveProgress:
    def __init__(self, chat_id, user_id, interval=80, clock=time.monotonic, waiting=user_waiting):
        self.chat_id, self.user_id = str(chat_id or ""), str(user_id or "")
        self.interval = max(60, min(180, float(interval)))
        self.clock, self.waiting = clock, waiting
        self.enabled = True
        self.bindings = weakref.WeakKeyDictionary()
        self.adapters = weakref.WeakKeyDictionary()
        self.turns = set()

    def available(self):
        turn = CURRENT.get()
        return bool(turn and turn.policy is self and turn.current())

    def handle(self, args, **kwargs):
        turn = CURRENT.get()
        ok = bool(isinstance(args, dict) and turn and turn.policy is self
                  and turn.declare(args.get("stage")))
        return json.dumps({"registered": ok, "message_sent": False,
                           "hint": "Continue the actual task; use brief commentary for useful updates."})

    def observe(self, adapter):
        if adapter is None or adapter in self.adapters:
            return
        original = getattr(adapter, "send", None)
        if not inspect.iscoroutinefunction(original):
            return
        policy = self

        @wraps(original)
        async def send(chat_id, content, *args, **kwargs):
            turn = CURRENT.get()
            # Native queued follow-ups start their consumer before the next worker.
            # That consumer inherits the parent context; only the same admission /
            # generation may resolve to its current human child, never another turn.
            if turn and turn.closed and turn.policy is policy:
                turn = next((t for t in policy.turns if t.parent is turn and t.current()), turn)
            metadata = kwargs.get("metadata", args[1] if len(args) > 1 else None) or {}
            own = turn and turn.policy is policy and str(chat_id) == policy.chat_id
            if own and metadata.get("_buddy_waiting") and not turn.current():
                from gateway.platforms.base import SendResult
                return SendResult(success=False, error="obsolete_progress")
            native_interim = bool(own and metadata.get("_interim_send") and not metadata.get("_buddy_waiting"))
            if native_interim:
                turn.interim_inflight += 1
            try:
                result = await original(chat_id, content, *args, **kwargs)
            finally:
                if native_interim:
                    turn.interim_inflight -= 1
            if (own and metadata.get("_interim_send") and turn.current()
                    and getattr(result, "success", False) and getattr(result, "message_id", None)):
                turn.received()
            return result

        adapter.send = send
        original_ref = weakref.WeakMethod(original) if inspect.ismethod(original) else weakref.ref(original)
        self.adapters[adapter] = (original_ref, weakref.ref(send))

    async def tick(self, turn):
        if not turn.current():
            return False
        try:
            if self.waiting(turn.key):
                turn.received()  # no immediate ping when the human eventually answers
                return False
            with turn.lock:
                due = self.clock() - turn.last_visible >= self.interval
            if not due or turn.interim_inflight:
                return False
            adapter = turn.gateway._delivery_adapter_for(turn.source)
            if adapter is None:
                return False
            self.observe(adapter)
            result = await asyncio.wait_for(adapter.send(
                turn.source.chat_id, turn.waiting_text(), metadata={
                    "_interim_send": True, "_non_conversational": True, "_buddy_waiting": True,
                }), timeout=8)
            if getattr(result, "success", False) and getattr(result, "message_id", None):
                turn.received()
                return True
        except asyncio.CancelledError:
            raise
        except Exception:
            # Never let a progress failure interrupt work, expose payloads, or retry
            # an ambiguous send immediately. Pace failures as well as successes.
            log.warning("Buddy waiting update unavailable")
        turn.received()
        return False

    async def watch(self, turn):
        try:
            while turn.current():
                try:
                    await asyncio.wait_for(turn.changed.wait(), timeout=1)
                    break
                except asyncio.TimeoutError:
                    await self.tick(turn)
        except Exception:
            log.warning("Buddy progress watcher stopped; ordinary task continues")

    def attach(self, gateway):
        if gateway in self.bindings or getattr(getattr(gateway, "config", None), "multiplex_profiles", False):
            return
        names = {"_handle_message_with_agent": 4, "_run_agent_start_turn_worker": 2,
                 "_run_agent_await_turn_worker": 4,
                 "_hmwa_agent_error_reply": 6}
        originals = {n: getattr(gateway, n, None) for n in names}
        try:
            compatible = all(callable(fn)
                and (inspect.iscoroutinefunction(fn) == (n != "_run_agent_start_turn_worker"))
                and len(inspect.signature(fn).parameters) == names[n] for n, fn in originals.items())
        except (TypeError, ValueError):
            compatible = False
        if not compatible or any(not callable(getattr(gateway, n, None)) for n in
                ("_is_session_run_current", "_is_user_authorized_for_source", "_delivery_adapter_for")):
            log.error("Buddy live progress unavailable: gateway bridge contract changed")
            return
        policy = self
        ref = weakref.ref(gateway)

        @wraps(originals["_handle_message_with_agent"])
        async def handle(event, source, key, generation):
            runner = ref()
            if (not policy.enabled or runner is None
                    or not owner_input(event, source, policy.chat_id, policy.user_id)
                    or not runner._is_user_authorized_for_source(source)
                    or not runner._is_session_run_current(key, generation)):
                return await originals["_handle_message_with_agent"](event, source, key, generation)
            turn = Turn(policy, runner, source, key, generation, asyncio.get_running_loop(), policy.clock())
            token = CURRENT.set(turn)
            policy.turns.add(turn)
            policy.observe(runner._delivery_adapter_for(source))
            turn.task = asyncio.create_task(policy.watch(turn))
            try:
                return await originals["_handle_message_with_agent"](event, source, key, generation)
            finally:
                for child in list(policy.turns):
                    if child.parent is turn:
                        await child.finish()
                        policy.turns.discard(child)
                await turn.finish()
                policy.turns.discard(turn)
                CURRENT.reset(token)

        @wraps(originals["_run_agent_start_turn_worker"])
        def start_worker(ctx, run_sync):
            parent = CURRENT.get()
            turn = parent
            if (parent and parent.policy is policy and parent.closed
                    and not ctx.scheduled_heartbeat and ctx.session_key == parent.key
                    and ctx.run_generation == parent.generation and ctx.inbound_message_id
                    and ctx.persist_user_display_kind not in ("internal_notification", "cron_delivery")
                    and owner_input(type("Input", (), {"message_id": ctx.inbound_message_id})(),
                                    ctx.source, policy.chat_id, policy.user_id)):
                turn = Turn(policy, parent.gateway, ctx.source, parent.key, parent.generation,
                            asyncio.get_running_loop(), policy.clock(), parent=parent)
                turn.context_token = CURRENT.set(turn)
                policy.turns.add(turn)
                turn.task = asyncio.create_task(policy.watch(turn))
            try:
                worker = originals["_run_agent_start_turn_worker"](ctx, run_sync)
                if turn and turn.policy is policy and not ctx.scheduled_heartbeat:
                    turn.worker = worker
                return worker
            except BaseException:
                if turn is not parent:
                    turn.closed = True; turn.changed.set()
                    policy.turns.discard(turn)
                    CURRENT.reset(turn.context_token)
                raise

        @wraps(originals["_run_agent_await_turn_worker"])
        async def await_worker(worker, ctx, interrupted, monitor):
            turn = CURRENT.get()
            owns = (turn and turn.policy is policy and ctx.session_key == turn.key
                    and ctx.run_generation == turn.generation and not ctx.scheduled_heartbeat)
            if owns:
                turn.worker = worker
            try:
                return await originals["_run_agent_await_turn_worker"](worker, ctx, interrupted, monitor)
            finally:
                if owns:
                    await turn.finish()
                    if turn.parent is not None:
                        policy.turns.discard(turn)
                        CURRENT.reset(turn.context_token)

        @wraps(originals["_hmwa_agent_error_reply"])
        async def error_reply(*args, **kwargs):
            turn = CURRENT.get()
            if turn and turn.policy is policy:
                await turn.finish()
            return await originals["_hmwa_agent_error_reply"](*args, **kwargs)

        wrappers = dict(zip(names, (handle, start_worker, await_worker, error_reply)))
        for name, fn in wrappers.items():
            setattr(gateway, name, fn)
        self.bindings[gateway] = (originals, wrappers)

    def unload(self):
        self.enabled = False
        for turn in list(self.turns):
            turn.closed = True
            turn.loop.call_soon_threadsafe(turn.changed.set)
        for obj, (originals, wrappers) in list(self.bindings.items()):
            for name, original in originals.items():
                if getattr(obj, name) is wrappers[name]:
                    setattr(obj, name, original)
        for adapter, (original_ref, wrapper_ref) in list(self.adapters.items()):
            original, wrapper = original_ref(), wrapper_ref()
            if original is not None and adapter.send is wrapper:
                adapter.send = original
        self.bindings.clear(); self.adapters.clear()


def register(ctx):
    policy = LiveProgress(ctx.get_config("chat_id", ""), ctx.get_config("user_id", ""),
                          ctx.get_config("interval_seconds", 80))
    ctx.register_tool(name="buddy_progress", toolset="messaging", schema=SCHEMA,
                      # Native check_fn/tool-schema results are TTL-cached. Never
                      # cache a per-turn ContextVar here: enforce ownership in handle.
                      handler=policy.handle, check_fn=lambda: policy.enabled)
    ctx.register_hook("pre_gateway_dispatch", lambda *, gateway, **kwargs: policy.attach(gateway))
    ctx.on_unload(policy.unload)
