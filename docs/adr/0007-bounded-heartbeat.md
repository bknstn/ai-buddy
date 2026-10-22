# ADR 0007: Separate private review from conditional delivery

Date: 2026-10-02

Status: Accepted

## Context

Useful initiative needs current context, but independent reminders and unconstrained model judgments can produce repetitive notifications.

## Decision

Use bounded collection, private daily and weekly reviews, and a script-only delivery gate. Code enforces quiet hours, stable-key deduplication, snoozes, at most one heartbeat message per day, up to two signals and at most one technical suggestion per seven days.

## Consequences

No actionable change means silence. Existing explicitly requested reminders remain separate. Reviews consume model calls, cannot supervise a stopped gateway and do not authorize automatic upgrades or external writes.
