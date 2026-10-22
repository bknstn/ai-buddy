# ADR 0005: Keep assistant web research in a profile-local backend

Date: 2026-09-27

Status: Accepted

## Context

Assistant search needed a provider-specific implementation without changing the independent domain retrieval pipeline.

## Decision

Register buddy-openai as a profile-local search and page-reading backend using hosted web search. Require an exact completed open_page action before returning a requested page summary, and label it as a model summary.

## Consequences

Search citations and synthesis do not constitute verbatim page extraction. Domain retrieval remains independent. The original subscription-only routing was later extended by ADR 0011.
