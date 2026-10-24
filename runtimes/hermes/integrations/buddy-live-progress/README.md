# Optional live task progress

This Hermes plugin adds truthful progress and waiting updates to the configured
owner's active, unthreaded private Telegram conversation. It is optional and
disabled until explicitly selected and configured. Native completed assistant
commentary remains enabled while final-text streaming, raw tool progress and
reasoning stay off.

`buddy_progress(stage=...)` records a short topic for the active task. It sends
no message, proves no result and grants no permission. The assistant supplies
useful commentary. After 80 seconds without a successfully delivered interim
message, a lightweight watcher may send a truthful waiting update using that
declared topic. It never turns raw tool arguments, source text or hidden
reasoning into status. Before a topic exists, it reports only that preparing an
answer is taking longer. Further notices use the same interval and claim no new
progress or ETA.

The built-in waiting notices are currently in Russian. Localize those message
templates before enabling the plugin for a different conversation language.

There are no periodic model calls, scheduled jobs or persisted task contents.
The handler enforces active-turn scope. It serves only an authorized real owner
input in the configured main private Telegram chat; other users, topics,
internal wakes and scheduled work cannot start it. Native clarify/approval
queues pause waiting notices. Cancellation, drain, restart and executor
completion suppress new notices. Transport ambiguity cannot prove whether a
timed-out message reached Telegram, so it is never immediately retried.

The hook installs reversible, signature-checked instance wrappers at guarded
human turn admission, worker start/completion and error delivery. It depends on
private Hermes v0.21.7 gateway seams and in-process plugin isolation. Validate
against the exact target runtime version. No stable runtime files are edited.

## Manual configuration

After runtime validation, place `__init__.py` and `plugin.yaml` under
`$HERMES_HOME/plugins/buddy-live-progress/`. Select this plugin on its own or
with any other independently reviewed integrations; it does not activate
other plugins.

```yaml
plugins:
  isolation: in_process
  entries:
    buddy-live-progress:
      settings:
        chat_id: "<configured private chat>"
        user_id: "<configured owner>"
        interval_seconds: 80
display:
  platforms:
    telegram:
      interim_assistant_messages: true
      long_running_notifications: false
```

Keep real identifiers in private runtime configuration. Enabling the plugin is
a runtime change; local profile commands do not configure it.

## Local validation

The lifecycle tests use mocks and send no Telegram messages:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s runtimes/hermes/integrations/buddy-live-progress -v
```

Native tests skip without the Hermes runtime and must be run in an isolated
private environment before installation.
