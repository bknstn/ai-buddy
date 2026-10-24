# Development and validation

The profile CLI targets Python 3.11 or later and uses only the standard library. Its commands are local and do not access the network.

## Work with a profile

Run from the repository root. Use a private profile directory outside the checkout and replace the example path with a location you control:

```bash
python3 -m buddy init --path /path/to/private/assistant-profile
python3 -m buddy check --profile /path/to/private/assistant-profile
python3 -m buddy plan --profile /path/to/private/assistant-profile --format text
python3 -m buddy plan --profile /path/to/private/assistant-profile --format json
```

`init` refuses an existing destination and locations that resolve inside the repository. It creates only a private `config.toml`, with `runtime.home` set to `<profile>/runtime`; it does not create that runtime directory, populate personal instructions or enable integrations. `check` accepts the profile directory or its `config.toml` and checks the profile structure, runtime adapter and supported feature IDs. It does not require an installed runtime or runtime-home directory; it reports whether the path currently exists without inspecting its contents. Both `check` and `plan` reject profile paths or runtime homes inside the repository, including paths that resolve there through symlinks. `plan` accepts the same profile input and prints mappings for shared instruction fragments, an optional private-instruction pattern, selected runtime features and adapter-suggested environment values. The plan does not read private instruction contents, apply environment values, install or compose files, or execute or inspect a runtime.

Never put live credentials, personal facts, real conversation samples or domain data in a demonstration profile that will be committed. The schema's `runtime.home` is a private filesystem path; use a placeholder in examples and keep real profile files outside Git.

## Repository checks

Start with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git diff --check
```

Run the project checks documented in the relevant runtime module before proposing integration changes. Hermes plugin and gateway checks need a separate test environment with the compatible upstream runtime and dependencies; they cannot be proven by the profile CLI. Use a private test home, synthetic identifiers and mocked or controlled transports. Do not use a production home or send a real external message as a test without explicit authorization.

For new runtime modules, document their supported runtime versions, required hooks, installation steps, tests and capability limits. Validate that the plan output accurately describes the files the module will use. A successful local profile check does not establish runtime compatibility, provider access, channel delivery or domain-engine correctness.

## Public-source review

Install Gitleaks separately if available, then scan the working tree and Git history:

```bash
gitleaks dir --redact=100 .
gitleaks git --redact=100 --log-opts="--all --full-history" .
```

A directory scan may include ignored local files. Check findings against tracked files and history without printing credentials. Automated scans do not find every personal detail; review prose, examples, filenames, commit messages and author metadata manually. Use synthetic fixtures and generic paths.

Remove one-off probes, temporary scripts, validation copies and downloaded audit tools when the task is complete. Preserve requested deliverables, implementation source and pre-existing user files.
