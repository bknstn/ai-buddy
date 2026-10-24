# ADR 0017: Remove bundled instance-specific persona and domain collectors

Adopted: 2026-10-24

## Context

The first public-starter transition separated profiles and runtime modules, but the Hermes module still bundled a persona written for one operator and heartbeat prompts tied to specific domains, routines, language and schedules. Those details could appear to be required behavior when someone cloned the repository. Several collector paths also invoked engines that the generic starter did not own.

## Decision

- Replace instance-specific role, communication and report instructions with optional generic Hermes fragments. They follow the private profile and current user conversation without prescribing a name, language, channel, schedule or domain goal.
- Keep domain business logic and domain-specific collector integrations in their owning repositories or separately configured modules. The bundled heartbeat does not implicitly invoke a domain engine.
- Keep heartbeat disabled unless an operator explicitly selects and configures it. Its daily collector may read Calendar and Tasks with the configured Hermes access, plus bounded conversation context; its weekly collector reads only the runtime metadata sources explicitly configured for it.
- Use exactly the heartbeat topic IDs `calendar`, `tasks`, `projects`, `assistant` and `other`. These labels do not enable or create a data source.
- Leave review cadence, job schedule and destination to operator configuration. Preserve the heartbeat's deterministic quiet-hours and delivery-budget checks as optional code-level controls.
- Remove the domain-specific implementation plan from this repository. Keep only synthetic, general-purpose adapter examples; domain engine plans and implementation guidance belong with their projects.

## Consequences

The `buddy-persona` feature now maps generic optional instruction fragments that an operator reviews and adapts privately. Existing private instances that relied on the former persona or domain collectors must inspect their own configuration and migrate any needed behavior separately; this public change does not update a runtime or private profile.

The heartbeat topics `projects` and `other` are available for classifying a proposal when separately supplied, authorized input exists, but the bundled collector does not source project or other domain data. No feature becomes active through a profile plan alone.
