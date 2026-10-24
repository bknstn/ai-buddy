# ADR 0016: Separate the public starter, private profile and runtime modules

Adopted: 2026-10-24

## Context

The repository began as source and operational context for one Hermes-based assistant. Its integration code and documentation combined reusable behavior with one operator's persona, channel assumptions, domain preferences and deployment layout. That mixture made the repository difficult to fork safely and could cause readers to mistake historical installation details for generic assistant requirements.

The repository is being reshaped into a public, customizable starter. The initial implementation supports local profile initialization, validation and planning, but it does not install or start a conversational runtime. The private operating instance, any upstream runtime, and optional domain engines have different ownership and security boundaries.

## Decision

- Keep shared `core/instructions/` generic. Do not prescribe a name, timezone, channel, provider, schedule or domain track in shared defaults.
- Store each operator's instance configuration and custom instructions in a private profile outside the source checkout.
- Keep runtime-specific plugins, prompts, scripts, policies and compatibility notes under `runtimes/<runtime-id>/`. Keep each upstream runtime in a separate checkout.
- Treat Hermes as the first adapter module, not as a universal runtime contract. Its mapped features remain opt-in and require manual review and installation. Record v0.21.7 only as the legacy integrations' tested compatibility baseline, not a latest-version claim.
- Keep domain business logic, tests, data and artifacts in independently maintained repositories. Public examples document possible contracts with synthetic data and do not implement an engine.
- Limit the profile CLI to local `init`, `check` and `plan` operations. These commands do not install integrations, inspect a runtime home, change services, provision credentials or send messages.
- Keep Hermes-specific integrations module-scoped and opt-in. ADR 0017 removes the remaining instance-specific persona and domain-collector coupling from the reusable prompt set.
- Keep live installation evidence and private operational data outside the public repository. Publish reviewed production source before deploying it.

## Consequences

Clones can begin from a neutral profile without inheriting another operator's routine or personal details. Private configuration and behavior can vary without changing shared defaults. Runtime module authors must document capabilities and compatibility instead of assuming that core instructions work identically everywhere.

The starter does not deliver a one-command assistant. Runtime installation, channel and provider setup, credential management, integration validation, domain-engine work and deployment remain separate tasks. The plan output is a manual mapping for review; it is not an install manifest or proof of runtime behavior.

ADR 0006's original persona, ADR 0001's single-chat assumption and provider-specific decisions in ADRs 0005 and 0011 remain historical Hermes installation choices. They are not defaults for new profiles. ADR 0017 clarifies that the old role-and-domain bundle is replaced with optional generic instructions. ADRs 0002–0004, 0012 and 0015 continue to inform security and deployment boundaries where applicable, with actual paths and live state determined by each operator.
