# Hermes context for AI Buddy

Read `README.md`, `AGENTS.md`, `docs/architecture.md`, `docs/operations.md` and
`SECURITY.md`. Historical design rationale lives in `docs/adr/`, not in README.
This public context contains reusable operating boundaries, not a live deployment diary.

## Execution boundary

Hermes is VPS-only and runs as Linux user `hermes`. This checkout contains
integration source and documentation; it does not contain a local runtime or the
domain engines. Separate local documentation work, domain implementation and
VPS operations before choosing where to act. Live runtime state wins over recorded
conventions; inspect privately before claiming current service health.

## Instance scope

This context covers AI Buddy only. Use `/home/hermes/.hermes-buddy`, runtime checkout
`/home/hermes/runtimes/hermes-buddy`, its `venv/bin/python`, scoped CLI
`/home/hermes/.local/bin/hermes-buddy` and `hermes-buddy.service`.
Set `HERMES_HOME` explicitly for direct Python commands.

Keep other agents' configuration, paths and responsibilities out of Buddy's
context. Do not share OAuth refresh tokens or restore automatic profile multiplex migration.
The legacy `.hermes` and `hermes-gateway.service` aliases refer only to Buddy.

The operator-defined `ssh hermes-vps` alias logs in as `hermes`. Start with
read-only service status, bounded journal inspection and the scoped gateway
status command. Root access is for host administration. Keep raw logs private.

## Source and compatibility

Buddy upstream follows tested stable tags, with an exact published release
commit and a clean detached HEAD. Integration/domain production checkouts follow
published GitHub main, fast-forwarded only after review and publication.
The included plugin compatibility baseline is v0.21.7; it is not a latest-version
claim. Test native hooks before upgrades and restart only the intended instance.
Drain active work, preserve sessions/data and remove task-created staging/backups
when verification succeeds.

## Integration contracts

- Domain repositories under `/home/hermes/workspace` own CLI contracts and data.
  Idea Maze data remains `/workspace/idea-maze`; select explicit workspaces.
- Main Telegram conversation is unthreaded. Cron attachment and native mirroring
  must not create topics; follow the integration guides.
- Final replies remain complete. Native low verbosity requests concision, and the
  adapter splits long replies. Final-text streaming and raw tool/reasoning output
  stay off; completed live commentary is a separate capability.
- Heartbeat uses bounded private reviews, deterministic delivery gates and a
  private source-backed continuity ledger. Silence is not consent. Context
  storage does not authorize actions or schedule execution.
- Session/progress bridges depend on private gateway interfaces and require
  in-process plugin isolation. Frozen prompts may need a scoped idle refresh.
- Service credentials, profiles, chat/job identifiers, raw health data, transcripts,
  runtime databases and installation evidence stay outside public source.

Use the individual `integrations/*/README.md` files for configuration, tests and
limits. A repository edit does not install a plugin or authorize production changes.
