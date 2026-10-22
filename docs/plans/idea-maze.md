# Idea Maze: evidence-quality design scope

Historical scope: 2026-09-24–2026-09-25. This is a public design summary for a separate domain engine, not an instruction to change the Buddy runtime or enable a pipeline.

## Problem

Truncating source text before analysis can hide the evidence that supports an insight. Weak quote normalization can accept fabricated excerpts, and multiple references to one underlying source can exaggerate independent support.

## Adopted scope

- Preserve exact source excerpts with source identity, text version and offsets through the research path.
- Reject empty, stale or fabricated quotations, including Unicode cases that become empty under ASCII-only normalization.
- Add early synthetic regression fixtures and basic ingestion observability, with bounded retries and cursor progress only after persistence.
- Keep optional evidence assessment in the existing research path, with caching, bounded shadow evaluation and safe failure behavior. Keep it disabled without independently validated access and benefit.

## Deferred scope

Broad ranking changes, problem clustering, comment enrichment, general search-provider refactoring and a large benchmark require separate evaluation. Discovery results are not primary evidence, repeated sources are not independent support, and a model assessment is not ground truth.

## Review criteria

Verify exact end-to-end excerpts, stale/fabricated quote rejection, Unicode and HTML behavior, idempotent backfill, compatible CLI JSON, preserved human review and data integrity. Distinguish offline synthetic results from unavailable live experiments. Preserve runtime data and keep source publication ahead of deployment, as recorded in [ADR 0003](../adr/0003-publish-before-deploy.md).
