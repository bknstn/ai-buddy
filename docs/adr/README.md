# Architecture decision records

ADRs preserve why the design changed. Numbers follow adoption order; same-day decisions follow the recorded sequence. ADRs 0000–0015 describe earlier Hermes integration decisions and were reconstructed from repository documentation on 2026-10-22. ADR 0016 records the first public-starter transition; ADR 0017 clarifies the current generic persona and optional-source boundary. Earlier decisions preserve technical rationale, not defaults for every clone or evidence about a live installation.

Each record contains context, a decision and consequences. They deliberately omit personal profiles, chat/job identifiers, session counts, process IDs, private deployment evidence and temporary backup paths. Installation diaries do not belong in README or in ADRs.

| ADR | Adopted | Decision |
| --- | --- | --- |
| 0000 | 2026-08-23 | [Keep the assistant a control plane](0000-control-plane-and-domain-engines.md) |
| 0001 | 2026-09-13 | [Use one chat and an unmodified upstream runtime](0001-single-chat-and-upstream-runtime.md) |
| 0002 | 2026-09-14 | [Keep service access scoped and deployment credentials private](0002-scoped-service-access.md) |
| 0003 | 2026-09-25 | [Publish reviewed source before deployment](0003-publish-before-deploy.md) |
| 0004 | 2026-09-26 | [Isolate runtime instances and operational scope](0004-independent-instances.md) |
| 0005 | 2026-09-27 | [Keep assistant web research in a profile-local backend](0005-hosted-web-backend.md) |
| 0006 | 2026-09-29 | [Use one assistant across explicitly selected domains](0006-persona-and-domain-tracks.md) |
| 0007 | 2026-10-02 | [Separate private review from conditional delivery](0007-bounded-heartbeat.md) |
| 0008 | 2026-10-03 | [Make patience and practical care explicit](0008-patient-assistance.md) |
| 0009 | 2026-10-04 | [Keep natural reports and bounded continuity in the main chat](0009-main-chat-and-continuity.md) |
| 0010 | 2026-10-05 | [Start a fresh session on an eligible daily greeting](0010-natural-daily-sessions.md) |
| 0011 | 2026-10-12 | [Add explicit API fallback and complete final delivery](0011-api-fallback-and-complete-replies.md) |
| 0012 | 2026-10-13 | [Pin upstream Hermes to tested stable releases](0012-tested-stable-runtime.md) |
| 0013 | 2026-10-19 | [Prefer concise answers without truncating useful reports](0013-concise-complete-reports.md) |
| 0014 | 2026-10-19 | [Provide scoped commentary and truthful waiting notices](0014-natural-live-progress.md) |
| 0015 | 2026-10-22 | [Separate public integration source from private operations context](0015-public-source-boundary.md) |
| 0016 | 2026-10-24 | [Separate the public starter, private profile and runtime modules](0016-public-starter-and-runtime-modules.md) |
| 0017 | 2026-10-24 | [Remove bundled instance-specific persona and domain collectors](0017-generic-persona-and-explicit-sources.md) |

For a new decision, use the next number and its actual adoption date. Preserve old decisions and explicitly identify anything superseded. Follow the [current architecture](../architecture.md) and [operations guide](../operations.md) for present conventions; an ADR is historical rationale, not an instruction to execute a rollout.
