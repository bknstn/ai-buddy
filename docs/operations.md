# Operations

This repository supplies reusable source and local profile tooling. It does not imply that an assistant is installed, running locally, or deployed to a server. The CLI does not connect to a host or alter runtime state.

For a new deployment, use the [staged repository-to-server plan](plans/repo-to-vps-migration.md) as a planning checklist. For an existing installation, inspect its private live state before making operational claims; this repository is not a substitute for the runtime's actual configuration, service state or logs.

## Keep the profile, runtime and repository separate

- Clone or fork this repository as shared source. Keep private profiles outside the clone.
- Keep the selected upstream runtime in its own checkout and environment. Runtime modules describe how to adapt source; they do not vendor the upstream runtime.
- Store credentials in the runtime's supported secret store, not in profile configuration, prompts or Git.
- Keep conversations, memory, logs, queues, databases, schedules, backups and domain data in private runtime storage.
- Use a dedicated operating-system account and restrictive permissions where the deployment model supports them. Process isolation is not automatically a filesystem security boundary.
- Treat channel access, service scopes, domain commands and scheduled tasks as individually configured capabilities. Enabling a feature in a profile does not provision or authorize it.

## Publish before deployment

Production integration and domain source must be reviewed, merged and pushed to GitHub `main` before it is installed on a server. Refresh the remote `origin/main` ref, fast-forward the server checkout on `main`, and verify that its HEAD matches that freshly fetched published revision. Do not deploy unpublished feature-branch commits or treat a transfer bundle as publication. Keep deployments fast-forwardable and record only non-sensitive release identifiers in public source.

Before changing a live service, identify the intended assistant and runtime, inspect status and recent relevant errors privately, and plan a rollback. Drain active work when replacing files that may be loaded in memory. Preserve user data and credentials. Verify the specific service, runtime load, channel connection and data integrity after a change. Remove task-created staging copies and temporary backups after successful verification, while retaining the normal recovery policy.

## Hermes module

Hermes is the first runtime module. Its upstream checkout, interpreter, private home, service and plugin paths are determined by the operator's installation; there are no canonical deployment paths or host aliases in this public repository. Follow the [module guide](../runtimes/hermes/README.md) and verify the actual host before acting.

The recorded integration compatibility baseline is Hermes v0.21.7. This is historical compatibility information, not a claim that it is the current or newest version. Before selecting another release, validate the installed plugins and any private gateway interfaces in an isolated environment. For the upstream runtime, verify HEAD against the exact published stable release commit; a clean detached checkout at that release is expected. Do not substitute an untested upstream `main` revision. The `main` publication policy above applies to domain and integration source, not the separate upstream runtime checkout.

Never paste raw service logs, account identifiers, host paths or runtime evidence into public documentation. Keep operational notes private unless they have been reviewed and sanitized for publication.
