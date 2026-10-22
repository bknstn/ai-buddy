# ADR 0000: Keep the assistant a control plane

Date: 2026-08-23

Status: Accepted

## Context

Conversation handling and domain workflows need different ownership and release cycles.

## Decision

Use Hermes for conversation, memory, routing, approvals and scheduling. Keep product discovery and health logic in separate engines with stable CLI contracts and structured outputs. Keep this repository as integration source and architecture context.

## Consequences

Domain repositories retain their own tests, data and business logic. A local checkout of this repository is not a running Hermes installation.
