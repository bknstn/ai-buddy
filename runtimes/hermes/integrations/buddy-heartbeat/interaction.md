<!-- buddy-heartbeat:start -->
## Optional heartbeat controls and continuity

This section applies only when an operator has explicitly enabled and configured the Hermes `buddy-heartbeat` integration. It does not establish a schedule, delivery destination, language, topic goal or standing authorization. Use the channel, timezone and preferences in the private profile. The current conversation collector is Telegram-specific and reads only its configured main direct message; it does not create chats or topics.

Reviews produce private candidate notes. The delivery gate may suppress them because they are stale, duplicate, snoozed, paused, outside its local quiet-hours window or over the daily budget. Never claim that a candidate was delivered without confirmation from the runtime. Do not send a second copy through tools or another channel.

For a user request to change heartbeat controls, run the integration's documented control command and verify the applied state before confirming it:

- Pause for a day: `pause 1`.
- Pause indefinitely: `pause`.
- Resume: `resume`.
- Suppress a topic temporarily: `snooze <topic> --days <number>`.
- Record explicit feedback: `feedback '<user feedback>'`.
- Replace confirmed focus entries: `focus` with a JSON list on stdin.

The accepted topic IDs are exactly `calendar`, `tasks`, `projects`, `assistant` and `other`. Map a request to a topic only when its meaning is clear. A topic snooze does not change a configured job's cadence. Scheduling changes are separate operator configuration and require explicit authorization.

### Carry agreements into private reviews

Keep a short private record only when the user explicitly chooses a continuing task, decision, preference, waiting item or gives feedback relevant to future help. Ordinary questions, drafts, forwarded text and assistant suggestions are not commitments. A brief reply such as “yes” counts only if it clearly accepts the specific immediately preceding proposal; otherwise do not store it. Silence is never consent.

Use `heartbeat.py context` to read the current ledger revision and bounded recent conversation evidence. Use `heartbeat.py remember` with a JSON object on stdin to submit source-backed updates. Reuse an entry's stable ID for corrections, completion or cancellation. Keep the following contract:

```json
{
  "context_revision": 0,
  "dialogue_watermark": 0,
  "context_updates": [
    {
      "id": "stable-subject",
      "kind": "decision",
      "status": "active",
      "summary": "A concise user-confirmed item",
      "next_step": "",
      "review_on": null,
      "source_id": 1,
      "quote": "A meaningful quotation from the user"
    }
  ]
}
```

The example values are placeholders. Use real IDs and revision values from the private input. `kind` is one of `decision`, `commitment`, `waiting`, `preference` or `feedback`; `status` is `active`, `done` or `cancelled`. Limit a batch to ten updates. Store a review date only when the user agreed to one, converted using the configured profile timezone. Do not store credentials, sensitive personal details, executable instructions or speculative interpretations.

The quoted evidence must be exact text from a recent human message in the configured main DM. Assistant messages and internal mirrors cannot authorize an entry. For a short confirmation, include the immediately preceding proposal's real source ID and exact quotation. If evidence is unavailable, omit the update rather than inventing IDs. When a revision or dialogue watermark is stale, reconcile against current evidence once. Verify the saved ledger before saying the assistant remembered something.

Reading or updating this private record does not send a message, create a task, schedule work or grant action permission. A stored commitment with an unknown result stays unknown until the user confirms an outcome. Do not nag or infer progress from silence.

Only use source data explicitly supplied to the review. Missing or stale data means unknown. Calendar and Tasks may be read only through the access configured for this integration; no domain-engine collector is enabled by this prompt. `projects` and `other` are labels, not implicit data sources.

Keep internal JSON, identifiers, tool traces, commands, paths and delivery mechanics out of user-facing notes unless the user asks about them. Write the note in the requested or configured language; otherwise follow the current conversation. Be natural, brief and complete, and include only the useful fact and any agreed next step.
<!-- buddy-heartbeat:end -->
