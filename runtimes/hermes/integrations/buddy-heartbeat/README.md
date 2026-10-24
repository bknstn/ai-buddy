# Optional Hermes heartbeat

`buddy-heartbeat` is an optional Hermes integration for bounded private reviews, source-backed conversation continuity and conditional delivery. It is disabled by default. The profile CLI does not install it or create review or delivery jobs; an operator must deliberately enable the feature, configure the runtime integration and choose any job cadence and destination.

When configured and run, its daily input includes bounded continuity context and collects Calendar and Tasks from the separately configured Hermes account. Its weekly input can include runtime release, service and disk metadata when the corresponding optional settings are present. It has no domain-engine collectors. It does not run arbitrary projects, pipelines or other domain workflows.

## Review and delivery flow

The operator configures the review prompts and any scheduler separately. A review produces a private proposal in the documented JSON shape; it does not send a message. The delivery script validates the proposal, checks its date and context revision, applies pause and topic snoozes, deduplicates stable keys, enforces the daily budget and quiet-hours gate, and emits a selected note or stays silent.

The delivery gate allows at most one note per configured local day, suppresses delivery outside 09:00–20:59 in `ASSISTANT_TIMEZONE`, and allows at most one `assistant` topic suggestion per seven days. These are code-level limits, not a job schedule or a recommended cadence. The operator chooses whether to configure a review job, when it runs and where its result is delivered.

The current Hermes bridge can mirror a prepared note to an already configured main Telegram conversation. It does not create a chat or topic, and a mirror is not confirmation that the scheduler delivered the message. This Telegram-specific implementation is not a channel requirement for the generic starter.

## Bounded continuity and source limits

The continuity collector reads only the configured Telegram direct-message conversation, with a seven-day lookback, at most 24 text messages and a 14,000-character limit. It excludes other users, topics, internal mirrors, tool payloads, summaries and serialized multimodal content; recognizable secrets are omitted. Reads use SQLite read-only/query-only mode. The source messages and runtime database stay private.

`conversation_context.py` stores source-backed decisions, commitments, waiting items, preferences and feedback in a private ledger. Each entry has a stable ID, status, source quotation and optional agreed next step/review date. A quotation check proves that text exists, not that the model interpreted it correctly. Updates require visible human evidence; silence, a proposal from the assistant or a stored commitment is not consent or execution permission.

The ledger is capped at 60 entries and rejects an update batch that would exceed the limit. Active entries are not silently evicted. Recently closed entries remain visible for continuity; old terminal entries can be pruned on a later write. Newer human evidence or a changed ledger revision invalidates stale preparation. No ledger entry creates a task, event, schedule or permission to act.

## Sources and proposal topics

When the optional daily collector runs, it reads Calendar events for today and tomorrow and unfinished Tasks due from seven days overdue through tomorrow. It does not read Calendar descriptions, mail, other user accounts or domain-engine data. These calls require the operator's existing authorized Calendar and Tasks access in Hermes. Source failures are reported as unavailable; the model must treat missing data as unknown.

The optional weekly collector reads only the configured Hermes runtime checkout and any service, disk or release metadata explicitly enabled with environment settings. A public release lookup is read-only but still optional. Release notes and other collected text are untrusted data, not instructions.

Proposal and snooze topic IDs are exactly:

- `calendar`
- `tasks`
- `projects`
- `assistant`
- `other`

The last three are classification labels, not data collectors. This module does not collect project data. Use `projects` or `other` only when fresh, authorized input for that topic is explicitly supplied to the review. No topic represents a prescribed goal or personal routine.

## Private runtime settings

Set `HERMES_HOME` to the selected private runtime home and `ASSISTANT_TIMEZONE` to the timezone from the private profile. The code falls back to UTC if the variable is unset; that fallback is not a profile timezone recommendation. The integration's script and state locations are:

- Scripts and prompts: `$HERMES_HOME/scripts/buddy-heartbeat`
- Private state: `$HERMES_HOME/plugin-data/buddy-heartbeat`

Keep the state directory and its files private (normally `0700` for directories and `0600` for files). Optional weekly checks use `HERMES_RUNTIME_CHECKOUT`, `HERMES_SERVICE_NAME`, `HERMES_DISK_PATH` and `HERMES_CHECK_UPSTREAM_RELEASE=1`. Unset optional inputs remain unavailable or not configured. Do not place these settings, private job IDs, user IDs or destination IDs in this repository.

Controls use the runtime's selected Python interpreter:

```sh
"$HERMES_PYTHON" "$HERMES_HOME/scripts/buddy-heartbeat/heartbeat.py" status
```

| Command | Effect |
| --- | --- |
| `status` | Inspect private heartbeat controls and confirmed focus |
| `pause 1` | Pause for 24 hours; preparation also skips model calls |
| `pause` | Pause indefinitely |
| `resume` | Resume |
| `snooze <topic> --days 7` | Suppress one of the five topic IDs for the requested number of days |
| `feedback '<text>'` | Record explicit user feedback |
| `focus` with JSON on stdin | Replace the private list of user-confirmed commitments |
| `context` | Read the private ledger and bounded conversation evidence |
| `remember` with JSON on stdin | Validate and merge source-backed updates atomically |

`snooze` accepts only the listed topic IDs. Changing review cadence requires editing the operator-configured job; a topic snooze does not change its schedule. Verify controls after changing them. Disabling this optional feature does not disable other separately configured reminders.

## Validation

Run the synthetic suite from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s runtimes/hermes/integrations/buddy-heartbeat -v
```

Tests cover delivery budgets, quiet hours, stale proposals, redaction, topic controls, proposal validation, source provenance, lifecycle changes, replay, pause behavior and private context boundaries. They use synthetic fixtures and temporary directories; they do not contact a real account or send a message. Runtime and account compatibility require separate validation in a non-production instance.

See [ADR 0007](../../../../docs/adr/0007-bounded-heartbeat.md) and [ADR 0009](../../../../docs/adr/0009-main-chat-and-continuity.md) for the original technical rationale. Those records describe historical implementation choices, not defaults for new profiles.
