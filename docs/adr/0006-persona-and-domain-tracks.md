# ADR 0006: Use one assistant across explicitly selected domains

Date: 2026-09-29

Status: Accepted

## Context

Requests from several optional domains should share a coherent conversation without merging their implementations or inventing new commitments.

## Decision

Keep a reusable role fragment that routes only to an explicitly configured domain skill and workspace. Respect the user's selected priorities and current permissions; do not create goals or commitments from an interesting topic.

## Consequences

An ordinary question does not require coaching. An interesting topic is not automatically a goal. Domain notes and records stay with their owning service or private workspace. ADR 0017 supersedes the original bundled domain-track persona as a public default.
