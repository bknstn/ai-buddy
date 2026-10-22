# ADR 0009: Keep natural reports and bounded continuity in the main chat

Date: 2026-10-04

Status: Accepted

## Context

Native scheduled continuation could create extra topics, while private reviews did not reliably receive decisions from ordinary conversation.

## Decision

Deliver to the existing unthreaded main chat, disable native cron attachment/mirroring for that route, and use natural report text. Add a bounded main-DM collector and a private source-backed ledger for decisions, commitments, waiting items, preferences and feedback. Recheck live Calendar capabilities before requesting new consent.

## Consequences

The collector is capped at seven days, 24 text messages and 14,000 characters. New human evidence or ledger revisions invalidate stale proposals. Quote matching proves provenance, not semantic consent. Context storage authorizes no new actions.
