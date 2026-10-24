# Staged repository-to-VPS migration plan

Status: planning guidance. This document does not authorize or perform a server change. The public starter commands only create, validate and describe a local profile; they do not deploy an assistant.

Use this plan when an operator has chosen a server deployment and has separately authorized the work. For an existing production assistant, treat the live host as the source of truth and migrate one reviewed capability at a time. Do not replace a working installation with the starter defaults.

## Stage 0: prepare the public repository (current scope)

Create the generic starter, private-profile boundary, runtime-module contract and synthetic adapter examples. Review local CLI behavior and documentation with no network access and no live credentials. Keep any current operator profile and server state outside the repository. No VPS connection, runtime installation, service change or data migration is part of this repository-only stage; the remaining stages are deferred until an operator requests deployment work.

## Stage 1: inventory the current assistant privately

Record outside this repository the runtime and exact release, installed integrations, service manager, private home, profile/config locations, channel and service scopes, scheduled jobs, domain adapters, dependencies, data stores, backups and recovery steps. Identify which behavior is currently relied on and which must carry forward. Check permissions and account ownership. Identify any deprecated or unsupported collectors and jobs that refer to them; disable or remove those references during the separately authorized migration rather than carrying dormant schedules into staging.

For an existing Hermes installation, include the active plugins and any private gateway interfaces. The documented compatibility baseline for the legacy integrations is v0.21.7; that historical baseline alone does not prove the installed host matches it.

## Stage 2: prepare generic source and a private profile

Fork or clone the reviewed repository. Create a profile outside the checkout, customize the name and timezone, and add instance-specific instructions to the profile. Review the selected runtime and feature list. Keep credentials, private facts, chats, logs and runtime state out of the repository.

Use the local CLI with synthetic or non-sensitive profile data:

```bash
python3 -m buddy check --profile /path/to/private/assistant-profile
python3 -m buddy plan --profile /path/to/private/assistant-profile --format text
```

Compare the printed plan with the inventory. A plan is descriptive: it does not apply configuration or show that the runtime can load a file.

## Stage 3: select and prepare the runtime

Choose a documented runtime module. Install the upstream runtime separately according to its own instructions, pin a reviewed release, and define the private runtime home, service account, secret mechanism and recovery procedure. Keep runtime code, profile, persistent state and domain repositories in their intended private locations. For Hermes, compare HEAD to the exact published stable release commit and keep a clean detached checkout at that release; the recorded v0.21.7 compatibility baseline is not a claim about the current host or newest version. Do not replace it with an untested upstream `main` revision.

For Hermes, review `runtimes/hermes/README.md` and the individual integration guides. Confirm every integration's version and interface requirements in a non-production environment. Do not assume that Hermes-specific behavior transfers automatically to another runtime.

## Stage 4: map and migrate configuration incrementally

Map each selected capability from the inventory to the profile, runtime module or external engine that owns it. Separate reusable guidance from private preferences. Review channel setup, credential scopes, domain workspaces, schedules and side effects independently.

Remove any unselected integration from the staging configuration and verify there are no remaining jobs or prompts that invoke it. Do not add an implicit domain engine to the generic starter as a shortcut.

Migrate persistent data only with a documented format and an approved procedure. Preserve a restorable backup and validate ownership, permissions, record counts or other appropriate integrity checks. Never copy credentials or OAuth refresh tokens into the public repository. Do not remove the old profile, runtime or data until the new deployment passes its acceptance checks.

## Stage 5: validate an isolated server instance

Prepare a staging instance under an appropriately restricted account and a distinct private home. Start with disabled schedules and read-only capabilities. Use synthetic data and a non-production channel or mocked transport. Verify profile parsing, runtime startup, plugin loading, tool access, response completeness, error handling, access scopes, log redaction, persistence and restart behavior.

Test each write-capable operation and any scheduled behavior separately, with explicit authorization and a safe destination. Keep logs and identifiers private. Resolve failures before moving forward; a passing local check or startup message alone is not sufficient.

## Stage 6: review and publish the deployment source

Review the exact diff and scan the tree and history for secrets and personal details. Run relevant local and runtime-dependent checks. Merge and push reviewed production integration and domain changes to GitHub `main` before installation. Fetch or refresh `origin/main` on the server, verify there is no unpublished server-side source to preserve, fast-forward the server checkout on `main`, and confirm its HEAD exactly matches the freshly fetched published `origin/main`. Do not deploy unpublished feature-branch commits or substitute a copied bundle for publication. This `main` policy applies to integration and domain repositories; the upstream Hermes runtime follows its separately pinned stable-release policy.

Keep the source tree and operator-specific configuration separate. Do not place a profile, service override, key, token or data export in the repository to simplify deployment.

## Stage 7: deploy with a rollback gate

At the agreed maintenance window, verify the exact target instance, revision, backup and rollback procedure. Drain active work if replacing loaded integrations. Install only reviewed files and the approved private configuration. Restart only the intended service when required.

Verify service status, runtime version, integration loading, channel connectivity, a bounded authorized read, state integrity and expected schedule state. If a check fails, follow the prepared rollback and retain diagnostic evidence privately. Avoid enabling unattended writes until a separate review confirms their behavior and authorization.

## Stage 8: accept and clean up

Compare the running behavior with the inventory and migration criteria. Confirm data continuity, access controls, failure handling and recovery. Retire the old instance only as specified by the planned cutover and recovery window. Remove task-created staging files, temporary backups and validation copies after the new deployment has been verified and the normal retention policy is satisfied.

The migration is complete only when the intended published source, private profile, selected runtime, integrations and data are verified together. Public documentation should record only reusable instructions and non-sensitive compatibility facts; keep live operational evidence private.
