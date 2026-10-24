# ADR 0004: Isolate runtime instances and operational scope

Date: 2026-09-26

Status: Accepted

## Context

Profile multiplexing coupled environments, authorization state and upgrades for assistants with different responsibilities.

## Decision

Give each runtime instance its own private home, runtime checkout, interpreter, dependencies, service, configuration and authorization state. Scope repository context and every operational command to the selected instance.

## Consequences

An instance's repository context and instructions should describe only its runtime and responsibilities. A dedicated home and service provide operational separation; sharing a Linux account does not provide a filesystem security boundary.
