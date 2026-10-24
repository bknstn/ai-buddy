# ADR 0014: Provide scoped commentary and truthful waiting notices

Date: 2026-10-19

Status: Accepted

## Context

Long user-requested work could remain silent, while elapsed-time notifications could not explain what was being checked.

## Decision

Enable completed task-specific commentary and register buddy_progress to record a short stage. After 80 seconds without a delivered update, an in-memory watcher may send a truthful waiting notice. Keep raw tool output, reasoning and final-text streaming disabled.

## Consequences

Only an authorized user's active direct-message task qualifies. Pause for clarification or approval; stop on cancellation, drain, restart or completion. No periodic model call or persisted task content is added. Private gateway seams require in-process isolation and native validation. This behavior is specific to the optional Hermes integration.
