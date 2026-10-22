# ADR 0013: Prefer concise answers without truncating useful reports

Date: 2026-10-19

Status: Accepted

## Context

Answers needed less repetition while long reports still needed useful sources, caveats and complete content.

## Decision

Use concise communication instructions and native agent.text_verbosity: low where supported. Return the complete final response and let the Telegram adapter split it naturally.

## Consequences

There is no fixed word, character or recommendation quota. Frozen agents may retain old instructions or verbosity settings; refresh the intended cache while idle and preserve sessions and messages.
