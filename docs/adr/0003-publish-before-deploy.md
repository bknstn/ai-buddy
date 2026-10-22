# ADR 0003: Publish reviewed source before deployment

Date: 2026-09-25

Status: Accepted

## Context

Delivering reviewed code directly to a server before publishing it made the deployed revision difficult to reconcile with the shared repository.

## Decision

Production domain and integration repositories run on main. Publish reviewed commits to GitHub main first, then fast-forward the VPS main and verify the remote revision.

## Consequences

Feature branches are for development and isolated validation. Bundles can transport already-published source but cannot bypass publication. Upstream Hermes has a separate stable-release policy recorded in ADR 0012.
