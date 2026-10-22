# AI Buddy Agent Orientation

This repository is the canonical operations and context pack for the AI Buddy
assistant integrations. It is not the Hermes runtime and it does not contain
the domain engines' source code.

Read first:

- `README.md`
- `.codex/context/hermes.md`

## Clean up task-created temporary files

After every task, delete the temporary scripts and helper files you created
solely to complete that task, on both the Mac and the VPS. This includes
one-off Python/shell/JS scripts, probes, scratch files and temporary validation
copies. Prefer stdin or inline commands when a saved script is unnecessary.
Track your temporary paths and verify their removal before reporting completion,
including after failures. Preserve requested deliverables, implementation code,
installed integrations and pre-existing user files. Do not leave new temporary
scripts behind while cleaning up earlier ones.

## Critical Boundary

Hermes Agent runs on the VPS only, under the dedicated Linux user `hermes`.

Do not assume a local Hermes process exists in this folder. Do not try to run Hermes from this checkout.

Use this repository to understand the current state:

- what Hermes is;
- which domain engines Hermes orchestrates;
- which VPS paths matter;
- which actions require SSH or VPS-side execution;
- which local repos are implementation targets.

## Instance selection and canonical VPS paths

This repository covers **AI Buddy only**. Keep its context, deployment instructions
and runtime configuration scoped to this assistant. Other agents belong in their
own repositories and must not be added to Buddy's context or responsibilities.

| Component | AI Buddy |
| --- | --- |
| HERMES_HOME (real directory) | `/home/hermes/.hermes-buddy` |
| Upstream runtime checkout | `/home/hermes/runtimes/hermes-buddy` |
| Python | `/home/hermes/runtimes/hermes-buddy/venv/bin/python` |
| systemd user service | `hermes-buddy.service` |
| Scoped CLI | `/home/hermes/.local/bin/hermes-buddy` |

Connect with `ssh hermes-vps` as Linux user `hermes`. Start with read-only checks:

```bash
ssh hermes-vps 'systemctl --user status hermes-buddy.service --no-pager'
ssh hermes-vps 'journalctl --user -u hermes-buddy.service -n 50 --no-pager'
ssh hermes-vps '/home/hermes/.local/bin/hermes-buddy gateway status'
```

For direct Buddy Python commands, set `HERMES_HOME=/home/hermes/.hermes-buddy`
and use Buddy's Python above. For authorized framework maintenance, operate
in Buddy's runtime checkout; this local repository contains context only.
Buddy has its own checkout, interpreter, venv, Node dependencies,
configuration, state, bot token and OAuth session. Do not share/copy OAuth
refresh tokens or re-enable automatic profile multiplex migration.

Legacy `/home/hermes/.hermes` points only to `.hermes-buddy`; the
`hermes-agent` link inside Buddy points to its own runtime. The legacy
`hermes-gateway.service` is an alias for `hermes-buddy.service`. Prefer the
canonical names above in new commands and documentation.

Existing domain repositories remain in `/home/hermes/workspace`; Idea Maze
runtime data still lives at `/workspace/idea-maze`. See `docs/operations.md`
for reference paths and deployment conventions, and `docs/adr/` for historical
architecture decisions.

## Current Model

```text
Telegram = user-facing interface
Hermes Agent = VPS-only conversational control plane, memory, routing, approvals
idea-maze-engine = product discovery / idea research engine
health-os = personal health / recovery / training engine
Codex / Claude Code = repo-level implementation help
```

Hermes orchestrates domain engines through stable CLI contracts. Domain repositories keep their own business logic, data, tests, and artifacts.

## Operating Rule

Buddy's upstream Hermes runtime follows tested stable release tags, as approved
2026-10-12. Verify its HEAD against the exact published release commit; a clean
detached HEAD at that tag is expected. Do not require parity with upstream
`origin/main` or install newer untested main commits. Check our integrations
before upgrading, drain Buddy, back up temporarily, verify after startup, then
remove task-created backups and staging once checks pass.

Our production domain/integration repositories on the VPS run on `main`. Merge and push
reviewed changes to GitHub `main` before deployment; update VPS `main` by
fast-forward and verify its HEAD matches `origin/main`. Feature branches are
for development and isolated validation only. Do not advance VPS `main` with
unpublished feature-branch commits, even when transferring code via a bundle.

When the user asks about Hermes itself, first determine whether the task is:

1. Context/planning work in this local `ai-buddy` folder.
2. Repo implementation work in a domain repository.
3. VPS-side Hermes operation requiring SSH to the `hermes` user environment.

If the task is VPS-side, do not pretend it can be answered from the local `ai-buddy` folder alone. State that Hermes is VPS-only and use the VPS paths and commands documented in the context files.

For routine VPS operations, connect with `ssh hermes-vps`; it logs in as the
dedicated `hermes` user. The `idea-maze-vps` alias logs in as `root` and is only
for tasks that genuinely require host-level administration.

When live state differs from these files, treat `/home/hermes` as runtime truth,
make the smallest safe operational decision, and update this repository to
record the verified state. Never copy secrets, raw health data, sessions, or
runtime databases into this repository.

## Public-source boundary

This repository is public. Follow `SECURITY.md`. Do not commit personal profiles,
private transcripts, raw domain data, credentials, deployment logs, real owner/chat/job
identifiers or personal workstation paths. Use generic instructions and synthetic
fixtures. Keep README as the project introduction and usage guide; put design
rationale in chronologically numbered `docs/adr/` records. Keep live operational
evidence private rather than appending it to public context files.
