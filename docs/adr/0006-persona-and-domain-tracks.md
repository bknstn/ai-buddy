# ADR 0006: Use one assistant across explicit domain tracks

Date: 2026-09-29

Status: Accepted

## Context

Health, product discovery, learning and planning should share a coherent conversation without merging their implementations or inventing new commitments.

## Decision

Keep a reusable role fragment that routes requests to the relevant domain skill and current workspace. Support practical learning and planning while retaining explicit priorities, realistic capacity and the existing action permissions.

## Consequences

An ordinary question does not require coaching. An interesting topic is not automatically a goal. Learning notes and learner profiles stay in their separate private workspace.
