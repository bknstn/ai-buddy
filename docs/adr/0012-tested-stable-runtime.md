# ADR 0012: Pin upstream Hermes to tested stable releases

Date: 2026-10-13

Status: Accepted

## Context

The upstream main branch may contain untested changes, while integration plugins depend on release-specific behavior.

## Decision

For the original Hermes instance, follow tested published stable tags for the upstream runtime. Validate the exact release commit and selected integrations before upgrading. The policy was selected on 2026-10-12 and applied with v0.21.7 on 2026-10-13.

## Consequences

A clean detached HEAD at the selected release is expected. Domain and integration repositories still deploy published main. Separate instances require separate upgrade scope; private backups and isolated staging are temporary.
