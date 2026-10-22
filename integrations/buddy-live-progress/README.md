# Buddy live task progress

Buddy-only profile plugin. Native completed assistant commentary stays enabled
while final-text streaming, raw tool progress and reasoning remain off. The
old elapsed-minute notifier is disabled only for Telegram.

`buddy_progress(stage=...)` records a short human-language topic for the active
owner task. It sends no message, proves no result and grants no new permission.
The main assistant supplies useful natural commentary. After 80 seconds with
no successfully delivered interim message, a lightweight watcher gives a
truthful waiting update using that declared topic. It never converts raw tool
arguments, source text or hidden reasoning into a status. Before a topic exists
it can only report that preparing an answer is taking longer. Further waiting
notices are paced at the same interval; they do not claim new progress or ETA.

There are no periodic model calls, scheduled jobs or persisted task contents.
Native tool-search defers plugin tools. SOUL supplies the complete single-field
schema so `tool_call` can invoke `buddy_progress` directly, including in a batch
with work tools; no discovery request or tool-search policy change is needed.
Its handler enforces the live-turn scope. The registration check stays stable
because Hermes caches requirement checks and tool schemas between turns.

The plugin serves only an authorized real owner input in Buddy's unthreaded
main Telegram DM. Other users, instances, topics, internal wakes and scheduled
work cannot start it. Native clarify/approval queues pause waiting notices.
Cancellation, drain, restart and executor completion suppress new notices.
An in-flight status is bounded to eight seconds and settled before the final.
Transport ambiguity cannot prove whether a timed-out message reached Telegram;
such a status is never immediately retried.

The hook installs reversible, signature-checked **instance** wrappers at guarded
human turn admission, worker start/completion and error delivery. Queued human
work gets a fresh stage; internal queued work does not. Native commentary send
receipts reset the silence clock. It depends on private v0.21.7 gateway seams,
so validate before upstream upgrades. No stable runtime files are edited.
Keep plugin isolation `in_process`, as with `buddy-session-policy`.

## Installation

Publish reviewed source to GitHub main, then fast-forward the VPS deployment
checkout to the verified published commit. Install `__init__.py`/`plugin.yaml`
in `/home/hermes/.hermes-buddy/plugins/buddy-live-progress/`. Enable alongside
the two existing Buddy plugins. Keep owner IDs in private config:

```yaml
plugins:
  entries:
    buddy-live-progress:
      settings:
        chat_id: "<existing main DM>"
        user_id: "<owner>"
        interval_seconds: 80
display:
  platforms:
    telegram:
      interim_assistant_messages: true
      long_running_notifications: false
```

Append `integrations/buddy-persona/live-progress.md` to SOUL and refresh its
saved current-main-session prompt while idle. Clear only that session's native
tool-name pin so the newly registered messaging tool enters its schemas.
Preserve every message and the current session ID. Quietly restart Buddy alone.

## Verification

Standalone lifecycle tests run with stdlib unittest and no files. On the VPS,
run `test_native.py` too under an isolated Hermes home and with the existing
pytest runner available for native harness helpers. Verify actual callbacks,
context propagation into tool threads, unchanged complete final delivery,
native waiting queues, private signatures and plugin validation. Use mock
Telegram transport; never send a real test message without authorization.
Remove all temporary validation/staging/rollback files when healthy.
