# Contributing

Start with the [README](README.md), [architecture](docs/architecture.md), [agent instructions](AGENTS.md) and [security guidance](SECURITY.md). Keep shared source generic and safe for public cloning.

When changing shared instructions, avoid assuming one operator's identity, timezone, channel, provider or routine. Put private preferences in the profile instead. When adding a runtime module, document its supported versions, capabilities, setup, validation and limits. When documenting a domain adapter, keep the engine's implementation and data in its own project and use synthetic fixtures here.

Use the [development guide](docs/development.md) to validate local profile behavior and review public-source changes. Describe what you checked and which runtime-dependent behavior remains unverified. A successful profile check or plan does not establish runtime compatibility or authorization.

Record significant architectural changes as the next numbered file in [docs/adr](docs/adr/README.md), using the actual adoption date, context, decision and consequences. Mark decisions superseded by a later ADR. Keep installation diaries, personal profiles, live operational evidence and deployment logs private.

Source review does not authorize production deployment, new schedules, external messages or account changes. For deployment, follow the published-source and rollback boundaries in the [operations guide](docs/operations.md). Merge and push reviewed production integration and domain source to GitHub `main`, then fast-forward the server checkout to the freshly verified `origin/main` before installation.
