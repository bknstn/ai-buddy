# Optional natural session policy

This Hermes plugin can start a fresh conversation after an eligible opening
greeting in the configured owner's private Telegram chat. It adds no model
calls, schedules, topics or outgoing messages. The plugin is optional and
disabled until an operator selects and configures it.

## Behavior and language scope

- This optional language-specific rule currently recognizes only the listed
  Russian phrases. Adapt the matcher for another language before enabling it
  in a profile that uses that language.
- The matcher recognizes the listed Russian phrases only: `привет` and
  `доброе утро` start a new local day; `продолжим`, `продолжаем`, `продолжай`,
  `вернёмся`, `не сбрасывай`, `без сброса` and `без новой сессии` continue the
  existing conversation.
- This is an optional phrase match in this plugin. It does not set the
  assistant's language or persona. Other-language greetings do not trigger a
  reset.
- The whole eligible message, including its attached task, reaches the new
  conversation normally. Without an opening phrase, the existing conversation
  continues across days.
- Same-day greetings, duplicate/replayed delivery, an already-created session,
  quotes, forwarded inputs, bot/internal notifications, other users, chats,
  topics, platforms and profiles cannot trigger the boundary.
- A greeting during active work follows the gateway's busy policy. Active
  processes and live/finalizing delegations also prevent a reset; queued human
  requests continue after the active turn.
- Voice uses the native cached speech-to-text transcript. A transcription
  failure keeps the existing conversation. Date, history or extension failures
  leave the ordinary message path available. Explicit `/new` or `/stop` cancels
  stale policy work.

The plugin reads `ASSISTANT_TIMEZONE`; it defaults to UTC when the environment
variable is unset. The Hermes profile plan suggests this value from
`assistant.timezone`, but does not export it automatically.

## Runtime design and limits

`pre_gateway_dispatch` installs a reversible instance-local wrapper at
`_handle_message_with_agent`. Policy execution runs after authorization,
control and busy gates and the native pending-agent claim, but before session
opening and model execution. The bridge depends on private Hermes gateway and
store interfaces, including in-process plugin isolation. It has been validated
against Hermes v0.21.7; test it against the exact target version before use.
A changed turn signature disables attachment, and unloading restores the
original instance method.

The transition uses native cleanup, cache eviction, conversation/security
state clearing, route reset and session hooks. It preserves the current turn's
sentinel, lease and generation. The previous session remains in SQLite and can
be recalled under the runtime's existing history policy; this plugin deletes no
transcripts or memory files and adds no exhaustive handoff summary.

Bookkeeping lives in native session metadata under `buddy-session-policy`:
`last_human_day` and the greeting's platform message ID. It contains no chat
text. Bootstrap reads only the latest real human timestamp for the configured
owner and unthreaded private chat, including archived turns while excluding
synthetic inputs.

## Manual configuration

After reviewing and validating the plugin against a private Hermes runtime,
place `__init__.py` and `plugin.yaml` under
`$HERMES_HOME/plugins/buddy-session-policy/`. Configure the private chat and
owner IDs in that runtime's private plugin settings:

```yaml
plugins:
  isolation: in_process
  entries:
    buddy-session-policy:
      settings:
        chat_id: "<configured private chat>"
        user_id: "<configured owner>"
```

Do not place real identifiers in this repository. Enabling the plugin is a
runtime configuration change; local `init`, `check` and `plan` commands do not
perform it.

## Local validation

Run the synthetic lifecycle suite from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 runtimes/hermes/integrations/buddy-session-policy/test_policy.py
```

Native runtime tests skip when Hermes is unavailable. They require a separate
isolated Hermes environment; this source-only check does not establish native
compatibility.
