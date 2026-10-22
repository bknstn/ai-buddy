# ADR 0015: Separate public integration source from private operations context

Date: 2026-10-22

Status: Accepted

## Context

A repository intended for public reference cannot also carry a personal profile or a detailed installation diary.

## Decision

Make README a project introduction and usage guide. Preserve technical rationale in chronological ADRs, reusable instructions in integration guides, and operating conventions in docs. Remove personal profiles and installation-specific audit logs from the public tree; use anonymous prompt subjects and synthetic examples.

## Consequences

Private runtime truth remains outside Git. Public history and author metadata need their own privacy review; deleting current files alone is insufficient. Replacing published history requires an explicitly coordinated operation and cannot recall existing clones or caches.
