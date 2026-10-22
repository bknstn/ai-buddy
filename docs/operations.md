# Operations reference

Hermes runs separately on a VPS under a dedicated `hermes` user. This repository is the source and context pack; do not start a local Hermes process from this checkout.

The layout below is a deployment convention, not a public endpoint or evidence of current service health. For an existing installation, inspect its actual runtime before making operational claims. Configure SSH access yourself; the examples assume an operator-defined `hermes-vps` alias.

## Select the instance

This repository covers AI Buddy only. Keep deployment instructions and runtime context limited to this assistant.

| Component | AI Buddy |
| --- | --- |
| Runtime home | `/home/hermes/.hermes-buddy` |
| Upstream checkout | `/home/hermes/runtimes/hermes-buddy` |
| Interpreter | `/home/hermes/runtimes/hermes-buddy/venv/bin/python` |
| User service | `hermes-buddy.service` |
| Scoped CLI | `/home/hermes/.local/bin/hermes-buddy` |

Buddy has its own real home directory, checkout, interpreter, dependencies, configuration, bot token, provider authorization and state. Keep these scoped to Buddy. Do not share OAuth refresh tokens or enable automatic profile multiplex migration. The legacy `.hermes` and `hermes-gateway.service` aliases refer only to Buddy; prefer canonical names.

## Start with read-only checks

```bash
ssh hermes-vps 'systemctl --user status hermes-buddy.service --no-pager'
ssh hermes-vps 'journalctl --user -u hermes-buddy.service -n 50 --no-pager'
ssh hermes-vps '/home/hermes/.local/bin/hermes-buddy gateway status'
```

Logs may contain personal or operational data. Inspect them privately and do not paste raw output into public issues or commits. Routine work uses the dedicated user; root access is reserved for host administration.

Direct Buddy Python commands must set `HERMES_HOME=/home/hermes/.hermes-buddy` and use Buddy's interpreter.

## Source and data layout

The reference deployment checkout for this repository is `/home/hermes/workspace/ai-buddy`. Domain repositories remain under `/home/hermes/workspace`; Idea Maze runtime data uses `/workspace/idea-maze`, and Health OS uses a separate workspace. Domain skills define the exact CLI and workspace arguments.

Buddy plugins install under `$HERMES_HOME/plugins/`. Heartbeat scripts install under `$HERMES_HOME/scripts/buddy-heartbeat`; private state lives under `$HERMES_HOME/plugin-data/buddy-heartbeat`. Persona fragments are explicitly incorporated into private `SOUL.md`. Copying a prompt into this repository does not make the runtime load it.

Keep private files restricted to the runtime account: normally `0600` for files and `0700` for private directories. Keep credentials, queues, transcripts, health data, logs, job identifiers and backups out of Git.

## Deploy reviewed integration changes

1. Review and validate the change in development, including any native checks it needs.
2. Merge and push reviewed integration/domain source to GitHub `main` before deployment.
3. Fast-forward the VPS checkout on `main`; verify its HEAD equals the published `origin/main`. Confirm the remote ref freshly rather than trusting a stale tracking ref.
4. Drain active Buddy work before replacing installed files or refreshing cached prompts. Preserve sessions, messages, schedules and private configuration.
5. Install only the intended source files and apply authorized private configuration changes. Restart only the affected instance when required.
6. Verify plugin loading, service state, adapter connection and relevant data integrity. Remove task-created staging, validation copies and temporary rollback backups once checks pass.

Do not deploy unpublished feature-branch commits or treat a transferred bundle as proof of publication. If repository access is unavailable, verify the published commit independently before transferring source without credentials.

After an explicitly authorized public-history rewrite, an existing deployment checkout may no longer fast-forward. Verify that its tracked files are clean and that it has no unique unpublished work, then align its `main` to the exact verified published commit. Preserve untracked/private files and restore ordinary fast-forward deployments afterwards. Never merge the old history into the cleaned branch. Use a credential-free HTTPS remote for public source when SSH repository access is unavailable.

## Maintain upstream Hermes

Buddy follows tested stable release tags. Compare HEAD with the exact published release commit; a clean detached HEAD is expected. Domain and integration repositories retain the published-`main` policy. These policies apply to different components.

The recorded compatibility baseline for the included integrations is v0.21.7, not a claim about the latest upstream release. Before upgrading, check plugin hooks, private gateway signatures, dependencies and provider/tool continuations in isolation. Drain Buddy, create a temporary private backup, apply the authorized update and verify startup and state before removing temporary files.

Frozen Hermes agents can retain an old prompt or configuration after a file edit. Refresh the intended cache while idle and preserve conversation history; do not reset all sessions to load a preference.
