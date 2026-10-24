# AI Buddy agent orientation

This repository is a public starter for a customizable assistant. It contains shared instructions, a local profile CLI, runtime-module documentation and examples. It is not an assistant runtime and does not contain a live instance's private profile, credentials, messages, runtime state or domain-engine source.

Read first:

- `README.md`
- `.codex/context/runtime.md`
- `docs/architecture.md`
- `SECURITY.md`

For Hermes-specific work, read `runtimes/hermes/README.md` and its module context. For domain-engine work, use the owning repository rather than adding business logic here.

## Clean up task-created temporary files

After every task, delete all temporary scripts and helper files created solely to complete that task, locally and on any remote hosts used. This includes one-off Python, shell or JavaScript scripts, probes, scratch files and temporary validation copies. Prefer stdin or inline commands when a saved script is unnecessary. Track temporary paths and verify their removal before reporting completion, including after failures. Preserve requested deliverables, implementation code, installed integrations and pre-existing user files. Do not leave new temporary scripts behind while cleaning up earlier ones.

## Repository boundary

- Keep this repository generic and safe for public cloning. Do not add an operator's personal profile, prescribed life routine, real owner or chat identifiers, private transcript, raw domain data, credential, deployment log or workstation/server path.
- Shared `core/instructions/` is runtime-neutral. Instance-specific preferences and private facts belong in a private profile outside the checkout.
- Runtime modules own runtime-specific instructions, plugins, scripts, policies and compatibility notes. The upstream runtime stays in a separate checkout; do not vendor it here.
- Domain repositories own their business logic, data, tests and artifacts. `examples/` contains interface examples only unless a separate decision explicitly changes the repository's scope.
- The profile CLI's `init`, `check` and `plan` commands are local utilities. Do not describe them as installing or starting an assistant.
- A plan or checked profile does not establish that a runtime loads files, that a service is healthy, or that an integration has permission to act.

## Task routing and operational boundaries

When a request mentions an assistant runtime, first determine whether it is:

1. Repository documentation, shared instruction or starter tooling work here.
2. Implementation work in a runtime or domain repository.
3. Operation of a running assistant on a local or remote host.

Do not assume a runtime is installed in this checkout. For host operations, use the actual operator-provided access details and inspect live state before making claims. Do not connect to or change a host unless the user has asked for that operational work. Separate reversible read-only inspection from service, credential, data, schedule or external communication changes.

Keep service credentials, profiles, sessions, databases, logs, queues, backups and deployment evidence outside public source. Use synthetic fixtures and placeholder paths. Never print secrets to diagnose them.

## Publishing and deployment

Review and validate source changes before publishing. For production integration and domain deployment, merge and push reviewed changes to GitHub `main` first. Update the server only by fast-forwarding its `main` checkout to a freshly fetched `origin/main`, then verify the HEADs match. Do not deploy unpublished feature-branch commits or use a transfer bundle as a substitute for publication. Confirm the live host and target instance, preserve recoverable state, verify after startup, and clean up task-created staging and backups after successful checks.

For the existing Hermes integration set, v0.21.7 is the recorded compatibility baseline, not a latest-version claim. Follow the Hermes module's stable-release guidance and test compatibility before upgrades. Do not substitute upstream `main` for a reviewed stable release by default.

## Documentation and public source

Keep README as the project introduction and usage guide. Put design rationale in chronologically numbered ADRs; keep operational conventions generic and current. Preserve historical records but identify decisions that are superseded. Live installation details and audit evidence belong in private operational notes.

Follow `SECURITY.md`. Review staged files, history, filenames, author metadata and prose before publishing. `.gitignore` is only a guardrail; it cannot remove a file already tracked or clean Git history.

## Open-source repository safety

This repository is intended to be public/open source.

Before modifying, committing, or publishing code, read and follow
`OPEN_SOURCE_REPO_SAFETY.md`.

Treat the rules in that document as mandatory repository-level instructions.

Before every commit:
- review the complete staged diff;
- apply the pre-commit safety gate defined in `OPEN_SOURCE_REPO_SAFETY.md`;
- remove or generalize private operational details;
- never commit secrets, credentials, personal data, employer/client information,
  proprietary context, or maintainer-specific deployment configuration.

If you are uncertain whether some information is safe for a public repository,
do not commit it. Prefer a generic placeholder or ask for clarification.
