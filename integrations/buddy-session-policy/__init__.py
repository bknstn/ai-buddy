"""Buddy-only session boundaries; no model calls or outbound messages.

Hermes has a synchronous pre-dispatch hook, but no async session-policy API.
The hook installs a reversible, instance-local bridge at the guarded agent-turn
entry. This narrow private dependency is exercised against the installed runtime.
"""
import asyncio
from contextlib import closing
from datetime import datetime, timezone
from functools import wraps
import inspect
import logging
from pathlib import Path
import re
import sqlite3
import weakref
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
TZ = ZoneInfo("Europe/Warsaw")
STATE_KEY = "buddy-session-policy"
GREETING = re.compile(r"^(?:привет|доброе\s+утро)(?=$|[\s,.!?:;—–-])", re.I)
CONTINUATION = re.compile(
    r"\b(?:продолжим|продолжаем|продолжай|верн[её]мся|"
    r"не\s+сбрасывай|без\s+сброса|без\s+новой\s+сессии)\b", re.I)


def local_day(instant):
    # Native naive gateway timestamps are VPS UTC, not the user's local time.
    if not isinstance(instant, datetime):
        raise ValueError("Missing event timestamp")
    return instant.replace(tzinfo=timezone.utc).astimezone(TZ).date().isoformat() \
        if instant.tzinfo is None else instant.astimezone(TZ).date().isoformat()


def starts_new_day(text):
    text = (text or "").strip()
    return bool(GREETING.match(text)) and not CONTINUATION.search(text)


def is_owner_input(event, chat_id, user_id):
    source = getattr(event, "source", None)
    platform = getattr(source, "platform", None)
    if (not chat_id or not user_id or source is None
            or getattr(platform, "value", platform) != "telegram"
            or source.chat_type != "dm" or source.thread_id
            or str(source.chat_id) != chat_id or str(source.user_id) != user_id
            or getattr(source, "profile", None) not in (None, "default")
            or getattr(source, "is_bot", False)
            or getattr(event, "internal", False)
            or not getattr(event, "allow_gateway_control", True)
            or not getattr(event, "message_id", None)
            or (getattr(event, "text", "") or "").lstrip().startswith("/")):
        return False
    raw = getattr(event, "raw_message", None)
    metadata = getattr(event, "metadata", None) or {}
    return not (metadata.get("forwarded") or metadata.get("forward_origin")
                or (raw is not None and any(getattr(raw, field, None) is not None
                    for field in ("forward_origin", "forward_date", "forward_from"))))


def last_human_day(home, chat_id, user_id):
    """Only aggregate timestamps; includes archived history, excludes synthetic mirrors."""
    with closing(sqlite3.connect(f"{(home / 'state.db').as_uri()}?mode=ro",
                                 uri=True, timeout=2)) as db:
        db.execute("PRAGMA query_only=ON")
        stamp = db.execute("""SELECT MAX(m.timestamp)
            FROM messages m JOIN sessions s ON s.id=m.session_id
            WHERE s.source='telegram' AND s.chat_id=? AND s.user_id=?
              AND s.chat_type='dm' AND COALESCE(s.thread_id,'')=''
              AND m.role='user' AND m.platform_message_id IS NOT NULL
              AND COALESCE(m._compressed_summary,0)=0
              AND COALESCE(m.observed,0)=0
              AND COALESCE(m.display_kind,'') NOT IN
                  ('internal_notification','cron_delivery','compression_summary')""",
            (chat_id, user_id)).fetchone()[0]
    return local_day(datetime.fromtimestamp(stamp, timezone.utc)) if stamp is not None else None


def active_background_work(gateway, key, entry):
    """Fail closed for reset, while allowing the ordinary conversation to proceed."""
    try:
        if gateway.session_store._has_active_processes_safe(key, context=STATE_KEY):
            return True
        from tools.async_delegation import list_async_delegations
        return any(item.get("status") in {"running", "stalling", "finalizing"}
                   and (item.get("session_key") == key
                        or item.get("parent_session_id") == entry.session_id)
                   for item in list_async_delegations())
    except Exception:
        logger.warning("Buddy session boundary deferred: background-work check unavailable")
        return True


class SessionPolicy:
    def __init__(self, home, chat_id, user_id):
        self.home = Path(home).resolve()
        self.chat_id, self.user_id = str(chat_id or ""), str(user_id or "")
        self.bindings = weakref.WeakKeyDictionary()
        self.enabled = True

    def attach(self, gateway):
        if gateway in self.bindings:
            return
        original = getattr(gateway, "_handle_message_with_agent", None)
        required = ("_is_session_run_current", "_cleanup_old_agent_for_reset",
                    "_evict_cached_agent", "_clear_conversation_scope",
                    "_fire_session_reset_hooks")
        parameters = list(inspect.signature(original).parameters.values()) if callable(original) else []
        if (not asyncio.iscoroutinefunction(original) or len(parameters) != 4
                or any(p.kind not in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) for p in parameters)
                or any(not callable(getattr(gateway, name, None)) for name in required)):
            logger.error("Buddy session policy unavailable: gateway bridge contract changed")
            return
        policy = self
        gateway_ref = weakref.ref(gateway)

        @wraps(original)
        async def guarded_turn(event, source, key, run_generation):
            runner = gateway_ref()
            if policy.enabled and runner is not None:
                if not await policy.prepare(runner, event, source, key, run_generation):
                    return None
            return await original(event, source, key, run_generation)

        gateway._handle_message_with_agent = guarded_turn
        self.bindings[gateway] = (original, guarded_turn)

    def unload(self):
        self.enabled = False
        for gateway, (original, wrapper) in list(self.bindings.items()):
            if gateway._handle_message_with_agent is wrapper:
                gateway._handle_message_with_agent = original
        self.bindings.clear()

    async def prepare(self, gateway, event, source, key, generation):
        if (not is_owner_input(event, self.chat_id, self.user_id)
                or not gateway._is_user_authorized_for_source(source)):
            return True
        current = lambda: gateway._is_session_run_current(key, generation)
        if not current():
            return False
        store = gateway.async_session_store
        try:
            today = local_day(event.timestamp)
            entry = await store.get_or_create_session(source, touch_activity=False)
            state = await store.get_session_metadata(key, STATE_KEY, {})
            if not isinstance(state, dict):
                raise ValueError("Invalid session policy state")
            previous = state.get("last_human_day")
            # Bootstrap from history, and account for human steering that bypassed
            # the idle turn entry. Never use assistant/scheduler activity timestamps.
            if previous != today:
                history_day = await asyncio.to_thread(last_human_day, self.home,
                                                       self.chat_id, self.user_id)
                previous = max(filter(None, (previous, history_day)), default=None)
            created = local_day(entry.created_at)
            text = event.text or ""
            if getattr(getattr(event, "message_type", None), "value", "") == "voice":
                _, transcripts = await gateway._transcribe_pending_audio_event_once(event)
                if transcripts:
                    text = "\n\n".join(transcripts)
            if not current():
                return False
            should_reset = (previous is not None and previous < today and created < today
                            and starts_new_day(text))
            if should_reset and not active_background_work(gateway, key, entry):
                old_sid = entry.session_id
                await gateway._cleanup_old_agent_for_reset(key)
                if not current():
                    return False
                # No await between generation check and route transition: an
                # explicit /new cannot interleave here. Preserve this turn's
                # sentinel, lease and generation; this is not an interrupt.
                entry = gateway.session_store.reset_session(key)
                if entry is None:
                    raise RuntimeError("Missing session during greeting boundary")
                gateway._evict_cached_agent(key)
                queued = list(getattr(gateway, "_queued_events", {}).get(key, []) or [])
                gateway._clear_conversation_scope(key, reason="buddy_new_day")
                # These are real, later user requests, not yesterday's task state.
                if queued:
                    gateway._queued_events[key] = queued
                from gateway.slash_commands_session import _reset_process_scoped_tool_state
                _reset_process_scoped_tool_state()
                # Persist receipt before await/finalization; replay cannot rotate again.
                gateway.session_store.set_session_metadata(key, STATE_KEY,
                    {"last_human_day": today, "greeting_message_id": str(event.message_id)})
                await gateway._fire_session_reset_hooks(source, key, old_sid, entry.session_id)
                from hermes_cli.lifecycle import invoke_hook
                invoke_hook("on_session_reset", session_id=entry.session_id,
                            old_session_id=old_sid, new_session_id=entry.session_id,
                            reason="buddy_new_day", platform="telegram")
                logger.info("Buddy natural new-day session boundary completed")
            elif state.get("last_human_day") != max(previous or today, today):
                await store.set_session_metadata(key, STATE_KEY,
                    {**state, "last_human_day": max(previous or today, today)})
        except Exception:
            # An uncertain date/store/extension must never discard the user's task.
            # Do not expose exception text: runtime paths and payloads may be private.
            logger.warning("Buddy natural session policy deferred; ordinary turn continues")
        return current()


def register(ctx):
    from hermes_cli.config import get_config_path
    policy = SessionPolicy(get_config_path().parent,
                           ctx.get_config("chat_id", ""), ctx.get_config("user_id", ""))

    def pre_dispatch(*, event, gateway, **kwargs):
        # Only attachment here. Actual policy runs AFTER native auth/busy/control
        # guards and the pending-agent sentinel claim; raw events are never rewritten.
        policy.attach(gateway)

    ctx.register_hook("pre_gateway_dispatch", pre_dispatch)
    ctx.on_unload(policy.unload)
