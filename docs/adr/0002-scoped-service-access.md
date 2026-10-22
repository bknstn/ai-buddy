# ADR 0002: Keep service access scoped and deployment credentials private

Date: 2026-09-14

Status: Accepted

## Context

Calendar, tasks, mail and voice input need different provider capabilities and authorization boundaries.

## Decision

Keep mail read-only; use event-scoped Calendar access and the Tasks scope only for authorized workflows. Reauthorization must preserve intended grants. Keep OAuth material and transcription credentials in private runtime storage. Resolve transcription language explicitly instead of assuming an absent setting means automatic detection.

## Consequences

A granted scope is a capability, not permission for arbitrary writes. Instructions must distinguish API access from authorization for a concrete action. No service data or credential belongs in source.
