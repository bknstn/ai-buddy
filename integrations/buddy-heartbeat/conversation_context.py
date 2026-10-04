"""Bounded main-chat evidence and a private, source-backed continuity ledger.

This module never sends messages, changes domain data or grants action permission.
Callers hold the heartbeat lock when persisting the returned ledger.
"""
from contextlib import closing
from datetime import datetime, timedelta
import json
import re
import sqlite3
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Warsaw")
KINDS = {"decision", "commitment", "waiting", "preference", "feedback"}
STATUSES = {"active", "done", "cancelled"}
SECRET = re.compile(r"sk-[\w-]{20,}|Bearer\s+\S+|-----BEGIN .*PRIVATE KEY|"
                    r"(?:password|пароль|api[_ -]?key|token|токен)\s*[:=]\s*\S+", re.I)
MAX_MESSAGES = 24
MAX_DIALOGUE_CHARS = 14000
MAX_ENTRIES = 60


def load_ledger(state):
    path = state / "conversation.json"
    value = json.loads(path.read_text()) if path.exists() else {"revision": 0, "entries": []}
    if (not isinstance(value, dict) or type(value.get("revision")) is not int
            or not isinstance(value.get("entries"), list)):
        raise ValueError("Invalid conversation ledger")
    return value


def ledger_context(state, instant):
    value = load_ledger(state)
    cutoff = instant - timedelta(days=14)
    entries = [entry for entry in value["entries"] if entry["status"] == "active"
               or datetime.fromisoformat(entry["updated_at"]) >= cutoff]
    entries.sort(key=lambda entry: (entry["status"] != "active",
        entry.get("review_on") or "9999", entry["id"]))
    chosen, size = [], 0
    for entry in entries:
        length = len(json.dumps(entry, ensure_ascii=False))
        if size + length > 14000:
            continue
        chosen.append(entry)
        size += length
    return {"revision": value["revision"], "entries": chosen,
            "omitted_entries": len(entries) - len(chosen)}


def recent_dialogue(home, state, instant):
    """Read only the configured private DM, including its recent reset/compaction lineage.

    Platform message IDs distinguish human input from internal user-role mirrors.
    Tool payloads, system messages, summaries, topics and other users are excluded.
    """
    installation = state / "installation.json"
    chat_id = str(json.loads(installation.read_text()).get("telegram_chat_id") or "") if installation.exists() else ""
    if not chat_id:
        return {"status": "not_configured", "messages": [], "watermark": 0}
    cutoff = (instant - timedelta(days=7)).timestamp()
    with closing(sqlite3.connect(f"{(home / 'state.db').as_uri()}?mode=ro", uri=True, timeout=3)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        db.row_factory = sqlite3.Row
        watermark = db.execute("""SELECT COALESCE(MAX(m.id),0)
            FROM messages m JOIN sessions s ON s.id=m.session_id
            WHERE s.source='telegram' AND s.chat_id=? AND s.user_id=?
              AND s.chat_type='dm' AND COALESCE(s.thread_id,'')=''
              AND m.timestamp>=? AND m.active=1 AND COALESCE(m._compressed_summary,0)=0
              AND m.role='user' AND m.platform_message_id IS NOT NULL""",
            (chat_id, chat_id, cutoff)).fetchone()[0]
        rows = db.execute("""SELECT m.id, m.role, m.content, m.timestamp, m.platform_message_id
            FROM messages m JOIN sessions s ON s.id=m.session_id
            WHERE s.source='telegram' AND s.chat_id=? AND s.user_id=?
              AND s.chat_type='dm' AND COALESCE(s.thread_id,'')=''
              AND m.timestamp>=? AND m.active=1 AND COALESCE(m._compressed_summary,0)=0
              AND ((m.role='user' AND m.platform_message_id IS NOT NULL)
                OR (m.role='assistant' AND (m.tool_calls IS NULL OR m.tool_calls='[]')))
            ORDER BY m.timestamp DESC, m.id DESC LIMIT 96""", (chat_id, chat_id, cutoff)).fetchall()
    messages, seen, chars, redacted = [], set(), 0, 0
    for row in rows:
        content = row["content"]
        if not isinstance(content, str) or not content.strip():
            continue
        # Do not expand serialized multimodal messages or private tool payloads.
        if content.lstrip().startswith(("[{", '{"')):
            continue
        if SECRET.search(content):
            redacted += 1
            continue
        key = (row["role"], str(row["platform_message_id"])) if row["platform_message_id"] else (row["id"],)
        if key in seen:
            continue
        seen.add(key)
        text = content.strip()[:2000]
        if chars + len(text) > MAX_DIALOGUE_CHARS:
            text = text[:MAX_DIALOGUE_CHARS - chars]
        if not text:
            break
        messages.append({"source_id": row["id"], "role": row["role"],
            "at": datetime.fromtimestamp(row["timestamp"], TZ).isoformat(), "text": text})
        chars += len(text)
        if len(messages) >= MAX_MESSAGES or chars >= MAX_DIALOGUE_CHARS:
            break
    return {"status": "ok", "messages": list(reversed(messages)),
            "lookback_days": 7, "redacted_messages": redacted, "watermark": watermark}


def validate_updates(proposal):
    updates = proposal.get("context_updates", [])
    watermark = proposal.get("dialogue_watermark")
    if watermark is not None and (type(watermark) is not int or watermark < 0):
        raise ValueError("Dialogue watermark must be a nonnegative message ID")
    if not isinstance(updates, list) or len(updates) > 10:
        raise ValueError("At most ten conversation updates")
    if "context_revision" in proposal and (type(proposal["context_revision"]) is not int
            or proposal["context_revision"] < 0):
        raise ValueError("Conversation revision must be nonnegative")
    if updates and (type(proposal.get("context_revision")) is not int or proposal["context_revision"] < 0):
        raise ValueError("Conversation updates need their input revision")
    ids = set()
    for update in updates:
        if not isinstance(update, dict):
            raise ValueError("Conversation update must be an object")
        key = update.get("id")
        if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9][a-z0-9:_-]{0,99}", key) or key in ids:
            raise ValueError("Unique stable conversation IDs required")
        ids.add(key)
        if update.get("kind") not in KINDS or update.get("status") not in STATUSES:
            raise ValueError("Invalid conversation kind or status")
        for field, cap in (("summary", 500), ("next_step", 300), ("quote", 350), ("proposal_quote", 350)):
            text = update.get(field, "")
            if not isinstance(text, str) or len(text) > cap or SECRET.search(text):
                raise ValueError("Invalid or sensitive conversation text")
        if not update.get("summary", "").strip() or not update.get("quote", "").strip():
            raise ValueError("Summary and a meaningful user quotation required")
        if type(update.get("source_id")) is not int or update["source_id"] < 1:
            raise ValueError("A human source ID is required")
        if len(update["quote"].strip()) < 8 and (type(update.get("proposal_source_id")) is not int
                or len(update.get("proposal_quote", "").strip()) < 8):
            raise ValueError("Short confirmations need the concrete preceding proposal")
        review = update.get("review_on")
        if review is not None:
            if not isinstance(review, str) or datetime.strptime(review, "%Y-%m-%d").date().isoformat() != review:
                raise ValueError("Review date must be YYYY-MM-DD or null")
    return updates


def apply_updates(ledger, proposal, dialogue, instant):
    """Validate provenance and apply one atomic batch. A stale snapshot changes nothing."""
    updates = validate_updates(proposal)
    if not updates:
        return ledger, "unchanged"
    if proposal["context_revision"] != ledger["revision"]:
        return ledger, "stale"
    if (proposal.get("dialogue_watermark") is not None
            and proposal["dialogue_watermark"] != dialogue.get("watermark")):
        return ledger, "stale"
    human = {row["source_id"]: row for row in dialogue.get("messages", []) if row["role"] == "user"}
    entries = {entry["id"]: dict(entry) for entry in ledger["entries"]}
    changed = False
    for update in updates:
        row = human.get(update["source_id"])
        if not row or update["quote"].strip() not in row["text"]:
            raise ValueError("Conversation update is not backed by visible human input")
        if update.get("proposal_source_id") is not None:
            preceding = [message for message in dialogue.get("messages", [])
                         if message["source_id"] < row["source_id"]]
            previous = preceding[-1] if preceding else None
            if (not previous or previous["role"] != "assistant"
                    or previous["source_id"] != update["proposal_source_id"]
                    or not update.get("proposal_quote", "").strip()
                    or update["proposal_quote"].strip() not in previous["text"]):
                raise ValueError("Confirmation must reference the immediately preceding proposal")
        old = entries.get(update["id"])
        if old and old["source_id"] >= update["source_id"]:
            continue
        if not old and update["status"] != "active":
            raise ValueError("Cannot close an unknown commitment")
        entry = {key: update.get(key) for key in
            ("id", "kind", "status", "summary", "next_step", "review_on", "source_id", "quote",
             "proposal_source_id", "proposal_quote")}
        entry.update(accepted_at=old["accepted_at"] if old else row["at"],
                     source_at=row["at"], updated_at=instant.isoformat())
        entries[entry["id"]] = entry
        changed = True
    if not changed:
        return ledger, "unchanged"
    # Keep terminal entries for continuity without evicting unresolved work.
    cutoff = instant - timedelta(days=90)
    rows = [entry for entry in entries.values() if entry["status"] == "active"
            or datetime.fromisoformat(entry["updated_at"]) >= cutoff]
    if len(rows) > MAX_ENTRIES:
        raise ValueError("Conversation ledger is full; consolidate resolved entries")
    return {"revision": ledger["revision"] + 1, "entries": rows}, "saved"
