# Development and validation

Use Python 3.11 or later for the standalone suites. They use stdlib `unittest`, synthetic data and automatically cleaned temporary directories. Set `PYTHONDONTWRITEBYTECODE=1` to avoid leaving bytecode helpers behind.

## Local checks

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s integrations/buddy-heartbeat -v
PYTHONDONTWRITEBYTECODE=1 python3 integrations/buddy-session-policy/test_policy.py
PYTHONDONTWRITEBYTECODE=1 python3 integrations/buddy-live-progress/test_progress.py
git diff --check
```

The suites cover notification gates and freshness, context provenance and privacy boundaries, greeting/session policy, active-work protection and progress lifecycle. Native session cases skip without Hermes. Running tests does not install plugins, execute collectors or send messages.

## Runtime-dependent checks

Hermes is not vendored here. Run the following only in a separately prepared test environment with the compatible upstream runtime and its dependencies on `PYTHONPATH`:

```bash
PYTHONDONTWRITEBYTECODE=1 python integrations/buddy-openai-web/test_backend.py
PYTHONDONTWRITEBYTECODE=1 python integrations/buddy-live-progress/test_native.py
PYTHONDONTWRITEBYTECODE=1 python integrations/buddy-session-policy/test_policy.py
python -m hermes_cli.main plugins validate /path/to/plugin
```

Use an isolated `HERMES_HOME`, synthetic owner IDs and mocked transport for native tests. Native harness helpers also require the runtime's pytest dependency. Follow the individual guides for plugin requirements and in-process isolation. Do not use a production home for tests or send a real Telegram test message without authorization.

Passing standalone tests does not establish compatibility with a changed runtime, live provider access or successful delivery. Report those limits with validation results.

## Public-source checks

Install [Gitleaks](https://github.com/gitleaks/gitleaks) separately, then scan both files and history:

```bash
gitleaks dir --redact=100 .
gitleaks git --redact=100 --log-opts="--all --full-history" .
```

A directory scan includes ignored local files. A finding there must be checked against the tracked tree and historical objects before concluding it was published. Do not print the credential to investigate it. Git history scans do not detect all personal information; review prose, examples, filenames, commit authors and messages as well.

Never use production credentials or real conversation/health records as fixtures. Clean up one-off probes, scripts, validation copies and downloaded audit tools on every host used for a task. Preserve implementation source and requested deliverables.
