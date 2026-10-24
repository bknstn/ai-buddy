# Hermes runtime context

Hermes is a separately installed runtime. This source tree contains an adapter and optional integration modules, not Hermes itself or a local Hermes process. Use the repository's [operations guide](../../../docs/operations.md) for generic rollout boundaries and inspect the operator's actual installation before making operational claims.

## Boundaries

- Keep runtime homes, credentials, private instructions, conversations, logs, databases and application data outside the public source checkout.
- `HERMES_HOME` selects the private runtime home. The upstream checkout, Python environment, provider setup, channel and service are operator choices.
- The local `init`, `check` and `plan` commands do not install or run Hermes. A plan is a manual mapping, not compatibility or deployment evidence.
- Optional Hermes features are disabled by default. Installing or enabling one requires deliberate configuration and its own compatibility review.
- The existing heartbeat module is an opt-in Hermes integration. It uses bounded, private conversation context and, when explicitly configured and run, Calendar and Tasks. It has no domain-engine collectors. The conversation reader currently depends on the configured Telegram main-DM session store; this is an implementation limitation, not a core channel requirement.
- Heartbeat topics are exactly `calendar`, `tasks`, `projects`, `assistant` and `other`. Topic labels do not provision data sources. Project or other data may be used only when supplied by a separately configured source.
- Set `ASSISTANT_TIMEZONE` from the private profile when configuring runtime jobs. Optional heartbeat checks accept `HERMES_RUNTIME_CHECKOUT`, `HERMES_SERVICE_NAME`, `HERMES_DISK_PATH` and `HERMES_CHECK_UPSTREAM_RELEASE=1`; unset inputs stay unavailable or not configured.
- The recorded integration compatibility baseline is Hermes v0.21.7. It is historical, not a latest-version claim. Validate native hooks against the exact stable release selected for an instance.

Use synthetic fixtures for tests. Never add real credentials, personal instructions, chat identifiers, private transcripts, raw domain data or live deployment evidence to this public repository.
