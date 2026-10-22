# Buddy heartbeat

A profile-local integration for bounded private reviews and conditional Telegram
notes. It combines source collection, a source-backed conversation ledger,
review prompts and a deterministic delivery gate. It is not an independent
uptime monitor and does not update Hermes or domain code.

## Review and delivery flow

An operator can schedule a private weekly improvements review, private daily
preparation and a script-only conditional delivery. A reference configuration
prepares the weekly review on Monday at 08:15, daily context at 08:45 and delivery
at 09:00 in Europe/Warsaw, matching the gate's timezone. These are setup examples,
not a public record of an individual's schedule. Job IDs and routing belong only
in private installation state.

The weekly result feeds daily preparation through native `context_from`.
Preparation returns strict proposal JSON as its local-only cron response; it does
not write files through model tools. The delivery script validates that result,
maintains private state and emits a useful note or stays silent. Private reviews
still consume model calls on silent days.

Use the existing unthreaded main Telegram destination. Disable native cron
mirroring and set delivery `attach_to_session=false`; the runtime's unsupported
in-channel continuation path can otherwise create a topic. The optional prepared
note mirror targets only an existing main session and labels delivery unconfirmed.
No test message should be sent without authorization.

## Bounded conversation continuity

The daily collector can read seven days of the configured owner's main private
DM, capped at 24 text messages and 14,000 characters. Exact owner/chat scope,
real human platform-message IDs and synthetic-mirror exclusions prevent other
conversations and internal outputs from becoming human evidence. Recognizable
credentials and serialized multimodal payloads are excluded. Reads use SQLite
read-only/query-only mode; no transcript belongs in this repository.

`conversation_context.py` maintains private `conversation.json` entries for
explicit decisions, commitments, waiting items, preferences and feedback.
Entries include source quotations, status and agreed next steps/review dates.
Short acceptance requires the immediately preceding concrete proposal.
Provenance checks establish that quoted text exists, not semantic consent.

The chat can persist a verified update via `remember`; daily extraction is a
bounded fallback. A changed ledger revision or newer human evidence invalidates
stale preparation. Silent delivery can still persist authorized context updates;
pause blocks background writes. Replays are idempotent, unknown work cannot be
marked closed, and active entries are not silently evicted. The 60-entry cap
fails explicitly. Recently closed entries remain visible for 14 days; terminal
entries older than 90 days can be pruned on a subsequent write.

No ledger entry creates a task, event, schedule or execution permission. Weekly
review reads the ledger without rereading chat history. Missing evidence means
unavailable; this is not exhaustive conversation memory.

## Sources and permitted actions

Daily collection uses Calendar today/tomorrow, dated unfinished Tasks in that
window or seven days overdue, existing Health OS summary contracts after its
routine Oura sync, Learning OS notes/status and Idea Maze status. It excludes
Calendar descriptions, mail, raw health files, full chat logs and other instances.
Learning collection does not pull, publish or declare mastery. Nutrition is
unavailable unless separately integrated.

Weekly collection reads service/disk state, repository and cron metadata, the
installed release and stable upstream release information. It may propose one
concrete improvement; it never updates, restarts, deletes, commits, pushes or
changes production settings automatically. A clean detached runtime HEAD at a
tested stable release is expected. Domain/integration source follows published
`main`; a stale tracking ref is not proof of current remote parity.

Routine authorized Oura synchronization and this integration's private queue,
context and control state are the background writes. Other actions retain their
own authorization boundaries. Existing explicitly requested reminders have a
separate delivery budget and should not be duplicated by heartbeat.

## Attention and continuity

- At most one emitted heartbeat message per Warsaw day, containing up to two
  short signals; no “everything is fine” message.
- No delivery from 21:00 through 08:59; IANA timezone handles DST.
- Stable keys deduplicate unchanged recommendations, including ignored ones.
- At most one technical Buddy recommendation in any seven-day interval.
- Topic snoozes, temporary/global pause, explicit feedback and confirmed focus
  are persisted. Missing data means unknown, not success or user failure.
- Monday's daily review also considers one personal improvement experiment,
  without manufacturing goals or turning silence into acceptance.
- The gate reserves an emission before handing stdout to Hermes. This favors
  no duplicate pings: a subsequent transport failure may lose that day's message.
  `history.emitted` is not a delivery receipt; native cron tracks transport status.
  Keep native `attach_to_session` false to avoid opening topics.
  The installed script mirrors the prepared note separately into the
  existing main conversation when private installation state contains
  `telegram_chat_id`. It labels delivery as unconfirmed; mirror failure never
  prevents transport. No new chat/session/topic is created by that mirror.
- Failures are retained locally (`failure_deliver=local`) to avoid repeated
  infrastructure noise. Weekly cron review can surface actionable failures.
  A broken entire pipeline cannot supervise itself; use a separate uptime monitor
  if that guarantee is needed.

Installed scripts/prompts: `/home/hermes/.hermes-buddy/scripts/buddy-heartbeat`.
Private runtime state: `/home/hermes/.hermes-buddy/plugin-data/buddy-heartbeat`.
Files are private (`0600`, directories `0700`). Never copy that state into Git.
Native cron output and current-context files contain personal data and stay VPS-only.
`interaction.md` is loaded as a marked addition to Buddy's SOUL. Existing frozen
Telegram sessions may need a new session to see new controls.

## Controls

Use Buddy's Python with `HERMES_HOME=/home/hermes/.hermes-buddy`, then
`/home/hermes/.hermes-buddy/scripts/buddy-heartbeat/heartbeat.py`:

| Command | Effect |
| --- | --- |
| `status` | Inspect heartbeat settings and user-confirmed focus |
| `pause 1` | Quiet for 24 hours; preparation also skips model calls |
| `pause` | Pause indefinitely |
| `resume` | Resume |
| `snooze learning --days 7` | Suppress learning signals for seven days |
| `feedback '…'` | Persist explicit feedback for the improvement loop |
| `focus` + JSON list on stdin | Replace confirmed commitments, preserving intended entries |
| `context` | Read the continuity ledger and bounded human evidence |
| `remember` + JSON object on stdin | Validate and merge source-backed updates atomically |

Other topics: `calendar`, `health`, `nutrition`, `projects`, `buddy`.
Natural-language requests are mapped to these commands by the SOUL addition;
verify application before claiming success. Frequency changes need edits to the
named preparation/delivery jobs, not just a promise in chat. Disabling heartbeat
does not disable the user's older reminders.

## Validation

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s integrations/buddy-heartbeat -v`

Twenty-six synthetic tests cover quiet hours, no/stale signal, same-day budget,
deduplication, snooze expiration, technical cadence, DST, proposal validation,
redaction of source errors, persistent delivery reservation, control commands,
native output parsing without model file writes, plain delivery text,
execution-metadata rejection (including cached proposals) and main-chat-only
context mirroring with private errors redacted, main-chat privacy boundaries,
provenance, short confirmations, lifecycle changes, atomic rejection, replay,
stale human/ledger inputs, silent persistence and pause behavior.
They use auto-cleaned temporary directories and no external API or message sends.
Live source checks and native Buddy cron runs are verified separately on VPS.


## Installation and design history

Install scripts and prompts under `$HERMES_HOME/scripts/buddy-heartbeat` and keep
state under `$HERMES_HOME/plugin-data/buddy-heartbeat`. Incorporate `interaction.md`
explicitly into private SOUL instructions. Configure native review/delivery jobs
and real routing privately, only for authorized sources. Frozen conversation
prompts may require a scoped idle refresh.

See [ADR 0007](../../docs/adr/0007-bounded-heartbeat.md) and
[ADR 0009](../../docs/adr/0009-main-chat-and-continuity.md) for design rationale.
Deployment logs, individual reminders and exact job identifiers are not public
configuration examples.
