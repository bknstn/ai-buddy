# ADR 0004: Separate Buddy and Tutor runtime instances

Date: 2026-09-26

Status: Accepted

## Context

Profile multiplexing coupled environments, authorization state and upgrades for assistants with different responsibilities.

## Decision

Give Buddy and Tutor independent real home directories, runtime checkouts, interpreters, dependencies, services, configuration and OAuth sessions. Scope every operational command to the intended instance.

## Consequences

Buddy-only work must not restart or update Tutor. Legacy aliases refer only to Buddy. Both can share a Linux user, so this is operational separation rather than a filesystem security boundary.
