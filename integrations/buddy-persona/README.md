# Buddy communication preferences

`communication.md` is the marked general communication block in Buddy's private
`SOUL.md`. `scheduled-reports.md` supplies report guidance; its separately marked
`buddy-report-brevity` block can be appended to existing outward report prompts
without replacing their current requirements or newer heading preferences.

To request concise replies, set the native Buddy-only configuration:

```yaml
agent:
  text_verbosity: low
```

This requests shorter final answers on the configured Responses transport,
including its API fallback. It does not set an output token limit. Preserve
the existing model, reasoning, streaming and delivery settings. Source rules
remain useful when a transport does not support the native parameter.

The stable v0.21.7 gateway freezes agents and their system prompts. Its cache
signature does not include `agent.text_verbosity`; a config edit alone does not
update a cached agent. Refresh Buddy's instruction cache only while idle,
preserving the existing session and messages. Fresh scheduled runs read the
updated configuration and prompt. Scope the refresh to Buddy.

Telegram's native adapter splits complete replies with numbered parts,
UTF-16-aware sizing, natural break points and balanced code fences. Cron passes
the full report to this adapter. Keep this behavior: concision must not become
truncation or a fixed recommendation count.

`live-progress.md` supplies the separate live-task update rule. Its installed
companion is `integrations/buddy-live-progress/`: completed commentary plus a
bounded waiting fallback, scoped to the owner's active human task. Preserve
the final-only/silent policy for scheduled work.
