# ADR 0010: Start a fresh session on an eligible daily greeting

Date: 2026-10-05

Status: Accepted

## Context

Continuous conversations can grow unwieldy, but time-based resets can interrupt unfinished work or lose the incoming task.

## Decision

In the configured user's main direct-message conversation, an opening greeting on the first human contact of a later day can start a fresh internal session. Explicit continuation, active work, replay protection and scope checks take precedence. Preserve the complete incoming request and old searchable history. Add an 80,000-token native compression trigger cap. This is a historical Telegram integration policy, not a default for every runtime or channel.

## Consequences

No greeting means continuity across days. The plugin does not add a model handoff summary, erase memory or guarantee an absolute context-size ceiling. It depends on private gateway transition interfaces and needs native compatibility tests.
