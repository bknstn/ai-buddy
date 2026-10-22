# ADR 0004: Isolate Buddy runtime and operational scope

Date: 2026-09-26

Status: Accepted

## Context

Profile multiplexing coupled environments, authorization state and upgrades for assistants with different responsibilities.

## Decision

Give Buddy its own real home directory, runtime checkout, interpreter, dependencies, service, configuration and OAuth session. Scope its repository context and every operational command to Buddy.

## Consequences

Buddy's repository and instructions describe only its own runtime and responsibilities. Legacy aliases refer only to Buddy. A dedicated home and service provide operational separation; sharing a Linux account does not provide a filesystem security boundary.
