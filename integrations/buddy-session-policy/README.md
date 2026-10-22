# Buddy natural session policy

Scope: the configured owner's existing main private Telegram DM in Buddy.
No additional model calls, schedules, topics or outgoing messages are added.

## Behavior

- An opening `привет` or `доброе утро` on the first human contact of a later
  Europe/Warsaw day starts a fresh internal conversation. The whole message,
  including its attached task, reaches the new conversation normally.
- Without the opening greeting, the existing conversation continues across
  days. Explicit `продолжим`, `продолжаем`, `продолжай`, `вернёмся`,
  `не сбрасывай`, `без сброса` or `без новой сессии` overrides a greeting.
- Same-day greetings, duplicate/replayed delivery, a session already created
  today, quotes, forwarded inputs, bot/internal notifications, other users,
  chats, topics, platforms and profiles cannot trigger the boundary.
- A greeting during a live agent turn follows the gateway's existing busy
  policy. This plugin does not interrupt that turn. Queued inputs can reach the
  policy after the active turn finishes. Active terminal processes or live/
  finalizing async delegations also prevent automatic reset; that day's input
  continues the conversation. Later queued user requests survive the boundary.
- Voice uses the native cached STT transcript at turn entry, preventing a second
  transcription during native preparation. Failed STT keeps the conversation.
- Date/history/extension failures leave the ordinary message path available.
  An explicit `/new` or `/stop` that invalidates this turn cancels stale policy
  work rather than creating another session.

Compression is separate: install Buddy's native `compression.threshold_tokens`
cap at **80000**, preserving the existing enabled/ratio/protection settings.
This is an initial operating choice to review after ordinary usage, not a
guarantee that every protected request will fit below that number. Native
hygiene and overflow safeguards continue to apply. No midnight/idle reset is
enabled: absence of a greeting means continuity.

## Runtime design and limitations

`pre_gateway_dispatch` is a public synchronous plugin hook. It only installs
a reversible instance-local wrapper at `_handle_message_with_agent`. Policy
execution occurs after authorization, control/busy gates and the native
pending-agent sentinel claim, before session opening and model execution.
There is no supported async session-policy interface in runtime `345cd2b`.
The bridge and native transition helpers are private dependencies: test this
integration against a future Hermes release before upgrading. A missing or
changed turn signature disables attachment with a log entry. Unload restores
the original instance method.

Verified against stable v0.21.7 on 2026-10-13, including its managed Python
3.14.7 environment. Plugin implementation is unchanged. Native dispatch now
uses the async lifecycle hook; the compatibility test mocks both old sync and
new async dispatch. Preserve `plugins.isolation: in_process`: this bridge
requires the live gateway runner rather than a plugin-host placeholder.

The transition uses native cleanup, cache eviction, conversation/security-state
clearing, route reset and session finalize/reset hooks, preserving the current
turn's sentinel, lease and generation. A small synchronous route reset prevents
an explicit reset from interleaving between the final generation check and
commit. It emits no technical reset banner. The original session remains in
SQLite and can be recalled through native history/search within the existing
retention policy; no transcript or memory file is deleted by this plugin.

Existing memory-provider cleanup flushes pending provider writes. Saved global
memory and Buddy's private continuity ledger remain available to the fresh
agent through their existing mechanisms. This does **not** add an exhaustive
handoff summary or promise that every unsaved detail enters long-term memory.

Bookkeeping lives in native session metadata under `buddy-session-policy`:
`last_human_day` and the greeting's platform message ID. It contains no chat
text. Bootstrap reads only the latest real human timestamp from `state.db`,
including archived turns, with exact owner/DM scope and synthetic exclusions.
Assistant reports cannot advance that date. A fresh session's creation date
also prevents a second reset after a crash before the receipt was persisted.

## Installation

Publish this repository's reviewed source to GitHub `main` before copying the
implementation from a VPS checkout whose `main` matches `origin/main`.
Install only `__init__.py` and `plugin.yaml` into:

`/home/hermes/.hermes-buddy/plugins/buddy-session-policy/`

Enable `buddy-session-policy` alongside existing plugins in Buddy's config.
Configure owner IDs privately on the VPS (never commit private config):

```yaml
plugins:
  entries:
    buddy-session-policy:
      settings:
        chat_id: "<main private DM>"
        user_id: "<owner>"
compression:
  threshold_tokens: 80000
```

Gracefully restart only `hermes-buddy.service` to load the new plugin. Existing
conversation routing and transcripts must remain unchanged by installation;
the first eligible real greeting performs the boundary. Tutor is untouched.

## Validation

Run all repository integration tests with Buddy's Python/runtime on PYTHONPATH
and a temporary isolated `HERMES_HOME`, `TMPDIR`, disabled bytecode and pytest
cache. Tests cover owner scope, dates/DST, same-day/replay/restart, continuation,
scheduled mirrors, voice, store failures, active work, explicit reset races,
queued requests, native gateway admission/turn ownership, native SQLite
history/recovery and the actual compressor cap. Plugin Doctor verifies real
discovery/import/registration. No Telegram test message is needed.

Retain implementation/tests/docs; remove all task-created staging, sandbox,
pytest, probe and backup paths after installation and health verification.
