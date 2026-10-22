# ADR 0001: Use one chat and an unmodified upstream runtime

Date: 2026-09-13

Status: Accepted

## Context

Custom topic-to-workspace patches added maintenance cost while the desired interaction was one assistant conversation.

## Decision

Use a single Telegram conversation, upstream shared-working-directory behavior and explicit domain working directories. Remove the legacy topic-routing source patches.

## Consequences

Domain skills must select their repository and data workspace explicitly. Future interaction extensions should use scoped integrations rather than restoring those patches.
