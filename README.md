# AI Buddy

AI Buddy is a public starter repository for building a configurable AI assistant. Clone or fork it, choose an execution runtime, and keep each instance's profile and private instructions outside the repository.

The starter includes a small local profile CLI, generic assistant and communication instructions, a runtime-module boundary, and optional adapter examples. Hermes is the only shipped runtime adapter today. Other runtimes require their own module and independent compatibility work; the shared profile schema does not make legacy Hermes integrations portable by itself. This repository does not include or install the Hermes runtime, connect a channel, provision credentials, or provide domain-engine implementations. It is a foundation for customization, not a ready-to-run hosted assistant.

## Quick start

Requirements: Python 3.11 or later. The profile commands use only the Python standard library and do not access the network.

Clone the public repository, then create a private profile outside the checkout. The profile path's parent directory must already exist.

```bash
git clone https://github.com/bknstn/ai-buddy.git ai-buddy
cd ai-buddy
python3 -m buddy init --path /path/to/private/assistant-profile
python3 -m buddy check --profile /path/to/private/assistant-profile
python3 -m buddy plan --profile /path/to/private/assistant-profile --format text
```

`init` creates only a private `config.toml`, with `runtime.home` set to a private `runtime/` directory beneath the profile. Edit the file to set an appropriate name and timezone or choose another private runtime location. The default feature list is empty. Add personal guidance as Markdown files under the profile's `instructions/` directory; the CLI does not create these files or enable integrations. Keep identity details, preferences, credentials and real user data out of Git. `check` validates the profile structure, runtime adapter and selected feature IDs; it does not require an installed runtime. `plan` prints manual mappings for shared instructions, a pattern for private instructions, selected runtime features and adapter-suggested environment values. It does not read or compose private instruction files, apply environment values, install anything, run or inspect a runtime.

The default configuration shape is:

```toml
schema_version = 1

[assistant]
name = "My Assistant"
timezone = "UTC"

[runtime]
id = "hermes"
home = "/absolute/private/path/runtime"

[features]
enabled = []
```

These are replaceable examples. Set an appropriate name and timezone for your assistant, select a runtime module, and enable only capabilities you have configured and reviewed. Profile configuration is private and is not a deployment secret store.

For example, to ask the Hermes planner to include the optional generic persona instructions, change the feature list in the private profile to:

```toml
[features]
enabled = ["buddy-persona"]
```

This selects manual mappings only. Review and adapt the fragments before composing them into a runtime prompt. Do not enable a feature just because it is listed in the module.

## Customize and choose a runtime

1. Edit the private profile's assistant name and timezone, then add your own instructions under its `instructions/` directory. The CLI does not create or read those private instruction files.
2. Keep the default `enabled = []` unless you have deliberately selected an optional feature. Check and review the plan before applying any mapping manually.
3. For Hermes, install the upstream runtime separately by following the [official Hermes Agent setup guide](https://github.com/NousResearch/hermes-agent). Set its private home and environment explicitly, then review the [Hermes adapter guide](runtimes/hermes/README.md) for each selected integration.
4. Validate the selected features against the exact runtime release in an isolated environment before using them with real accounts or data.

The legacy Hermes integration set records v0.21.7 as a tested compatibility baseline. This is historical compatibility information, not a claim that v0.21.7 is the current or newest release. The profile CLI does not install Hermes, configure a provider or channel, or start an assistant.

## What is included

- [`core/instructions/`](core/README.md) provides runtime-neutral starting instructions. Customize them in your private profile rather than encoding one operator's persona or routine in the shared defaults.
- [`runtimes/hermes/`](runtimes/hermes/README.md) documents the initial Hermes adapter and its optional integrations, prompts, scripts and policies. The upstream runtime remains a separate checkout. Hermes integration compatibility was recorded against v0.21.7; this is a historical tested baseline, not a latest-version claim. Feature mappings are opt-in and manual; they do not install or activate an integration. Optional persona fragments are not part of the shared core; review and adapt them before use.
- [`examples/domain-adapter/`](examples/domain-adapter/README.md) demonstrates an optional domain-adapter contract using synthetic data. The example describes an interface; it is not a product engine or a recommendation to enable a domain workflow.
- `buddy` provides local `init`, `check` and `plan` commands for private profiles. These commands do not install or operate an assistant.

Hermes-specific integrations may depend on upstream plugin hooks and private gateway interfaces. Read their individual guides before adapting them, and validate any runtime-dependent behavior in a separate non-production environment.

## Architecture and operations

The [architecture guide](docs/architecture.md) explains the public repository, private profile, runtime module and optional domain boundaries. The [development guide](docs/development.md) covers local commands and review checks. The [operations guide](docs/operations.md) gives generic deployment principles; the [staged migration plan](docs/plans/repo-to-vps-migration.md) is planning guidance only and makes no changes to any VPS.

The [Hermes runtime guide](runtimes/hermes/README.md) describes its scope and limitations. This checkout does not imply that an assistant is running locally or remotely. For existing installations, inspect their private live state before making operational claims.

## Documentation map

- [Architecture](docs/architecture.md): boundaries and data flow.
- [Architecture decisions](docs/adr/README.md): historical rationale and the current runtime/profile separation decision.
- [Runtime adapters](runtimes/README.md): the adapter contract and Hermes module.
- [Development](docs/development.md): local profile commands, documentation checks and public-source review.
- [Operations](docs/operations.md): generic deployment and maintenance conventions.
- [Migration plan](docs/plans/repo-to-vps-migration.md): staged preparation for an operator-managed VPS deployment.
- [Security and privacy](SECURITY.md): private data rules and disclosure guidance.
- [Contributing](CONTRIBUTING.md): change and validation expectations.
- [Agent instructions](AGENTS.md): repository boundaries for coding agents.

README is the project introduction and usage guide. Design rationale belongs in ADRs; profiles, credentials, transcripts, runtime state and live operational evidence belong outside the public repository.

## License

The code and documentation in this repository are licensed under the [MIT License](LICENSE). Hermes Agent and any separately maintained runtime or domain engines are governed by their own licenses.
