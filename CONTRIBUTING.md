# Contributing

Start with the [README](README.md), [architecture](docs/architecture.md) and the guide for the integration you want to change.

Keep domain business logic in its owning repository. Keep Buddy changes small and explicit about runtime compatibility, authorization and private-state handling. Use synthetic fixtures; never attach real transcripts, health records, configuration or credentials to a change.

Run the relevant [validation](docs/development.md). Explain the user-visible behavior, checks performed and any runtime-dependent checks that remain. Changes to a private gateway interface need native compatibility validation before deployment.

Record a new architectural decision as the next numbered file in [docs/adr](docs/adr/README.md), with its adoption date, context, decision and consequences. Keep deployment diaries and personal installation evidence outside the public repository.

Source review does not authorize production deployment, new scheduled jobs, external messages or account changes. Follow the [operations workflow](docs/operations.md) for an authorized rollout.
