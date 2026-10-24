# Runtime-neutral project context

Read `AGENTS.md`, `README.md`, `docs/architecture.md`, `docs/operations.md` and `SECURITY.md` before making repository or operational changes. This repository is public starter source, not a live assistant runtime.

## Repository model

- Shared instructions live in `core/instructions/` and are intended to be generic.
- A private profile contains the instance configuration and optional custom instructions. Keep it outside the repository.
- Runtime modules live under `runtimes/<runtime-id>/` and own runtime-specific integrations and policies.
- Read `runtimes/README.md` for the adapter contract and `runtimes/hermes/README.md` for the first module.
- Upstream runtimes and domain engines remain in separate checkouts.
- `python3 -m buddy init`, `check` and `plan` operate on local profile files. They do not access a host, install software, configure credentials, start services or authorize external actions.

## Operational boundary

Do not assume a runtime process or service exists on the current machine. For work on a running instance, use only operator-provided access and inspect that instance's live configuration, revision and state before making claims. Public documents contain no canonical server paths, service names or SSH aliases because these vary by installation.

Repository work does not itself authorize host access, service changes, data migration, scheduled jobs or external communications. Do not connect to or change a host unless the user requests that operational work. Keep raw operational output and personal data private.

## Publication and compatibility

Review and validate changes, then publish them to the intended protected GitHub `main` branch before production deployment. Update production checkouts only by fast-forwarding to the freshly verified `origin/main`; do not deploy unpublished feature commits or treat copied bundles as publication.

Hermes is the first runtime module. Its existing integrations have a recorded tested compatibility baseline of v0.21.7, not a claim about the newest release. Follow `runtimes/hermes/README.md` for stable release pinning, exact commit verification and module-specific limits. Do not substitute upstream `main` for an approved stable release by default.

## Privacy and task cleanup

Never add credentials, private profile contents, transcripts, raw domain data, runtime databases, deployment logs, personal identifiers or personal filesystem paths to this public repository. Use placeholder paths and synthetic fixtures. Delete task-created temporary scripts, probes and validation copies on each host used, and verify cleanup before reporting completion.
