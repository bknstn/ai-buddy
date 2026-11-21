# Hermes runtime adapter

Hermes is the only runtime adapter shipped here. This module describes mappings from the starter's source files to a separately installed Hermes runtime; it does not include Hermes itself or make the shared profile portable to another runtime. The local `buddy` commands validate a profile and print a plan. They do not install files, configure services or credentials, create jobs, inspect runtime state, or start an assistant.

Read the [Hermes context](context/hermes.md), [integration guides](integrations/) and [operations guide](../../docs/operations.md) before adapting these assets. The core instructions are at [`core/instructions`](../../core/instructions/). The recorded compatibility baseline for the legacy integrations is Hermes v0.21.7; it is a historical tested baseline, not a latest-version claim. Verify compatibility with the exact upstream release you choose.

## Optional features

All features are disabled by default. To ask the local planner to map the generic persona instructions, a private profile can opt in explicitly:

```toml
[features]
enabled = ["buddy-persona"]
```

Enabling a feature only selects source mappings for manual review. It does not install or activate an integration. Review mapped instructions and code, configure credentials separately, and validate each capability in an isolated runtime before use.

| Feature ID | Planned assets | Scope and limits |
| --- | --- | --- |
| `buddy-heartbeat` | scripts and instruction fragments | Optional bounded review and delivery gate. It has no job or delivery schedule by default. When explicitly configured and run, its current daily collector reads Calendar, Tasks and bounded authorized conversation context. It contains no implicit domain-engine collectors. |
| `buddy-live-progress` | plugin source | Uses Hermes gateway interfaces and requires native compatibility checks. |
| `buddy-openai-web` | plugin source | Optional OpenAI web-search backend; needs separately configured provider access and runtime dependencies. |
| `buddy-persona` | instruction fragments | Generic, optional role and communication guidance. Adapt it to the private profile; it does not prescribe an identity, language, channel, schedule or domain. |
| `buddy-session-policy` | plugin source | Uses Hermes gateway/store interfaces and requires native compatibility checks. Its built-in greeting/continuation matcher is Russian-specific; it is not language-agnostic. |
| `buddy-software-engineer` | skill instructions | Full-stack engineering with planning and review by the main agent and implementation delegated to GPT-6 Luna. See [setup](#software-engineering-skill). |
| `google-calendar` | skill instructions | Instructions only. Provider access, credentials and authorization for any write remain separate. |

The heartbeat code uses topic IDs `calendar`, `tasks`, `projects`, `assistant` and `other` for proposals and snoozes. `projects` and `other` are labels only; this module does not collect domain-project data. Calendar and Tasks collection occurs only when the optional heartbeat review is explicitly configured and run with the required runtime access. Delivery still passes through its private deterministic gate.

## Manual runtime configuration

The plan suggests `HERMES_HOME` from `runtime.home` and `ASSISTANT_TIMEZONE` from `assistant.timezone`. These are examples for manual runtime configuration; the CLI does not export them or inspect the selected directory. Choose private paths and permissions appropriate to the host.

When the optional heartbeat is enabled, it reads the configured Hermes account's Calendar and Tasks using the runtime's authorized provider setup. Its private installation state, credentials, conversation store and generated context remain outside this repository. Optional weekly runtime checks use `HERMES_RUNTIME_CHECKOUT`; service and disk checks use `HERMES_SERVICE_NAME` and `HERMES_DISK_PATH`. `HERMES_CHECK_UPSTREAM_RELEASE=1` opts into a read-only public release lookup. Missing optional inputs are reported as unavailable or not configured.

The heartbeat's delivery gate allows at most one note per configured local day, suppresses delivery outside 09:00–20:59, deduplicates stable keys and limits assistant-maintenance suggestions to one per seven days. These are code-level safety limits for this optional feature. The operator chooses whether to configure any review or delivery job and its cadence; no schedule is included as a default.

## Software engineering skill

Add `buddy-software-engineer` to the existing `features.enabled` list in the private profile. Use `python3 -m buddy plan` to locate the skill and copy `SKILL.md` to `$HERMES_HOME/skills/buddy-software-engineer/SKILL.md` for the intended Hermes profile. Give the profile terminal and delegation tools and access to the intended development repositories.

This skill requires Hermes with pluggable delegation and the official [advanced-delegation plugin](https://hermes-agent.nousresearch.com/marketplace/advanced-delegation), whose minimum is Hermes v0.22.5. The legacy v0.21.7 baseline predates this backend. Use a reviewed stable release and validate the existing integrations before upgrading an instance. Install the plugin from the Hermes catalog with `hermes plugins install advanced-delegation` and confirm it is enabled in the intended profile.

Merge the following into that profile's private `config.yaml`. Keep the profile's main model settings and any other `model_map` options. Selecting `model_map` changes the delegation backend for new sessions in this profile, so review any existing delegation routes before switching. The skill always names its own route and needs no change to the default route.

```yaml
delegation:
  backend: model_map
  backends:
    model_map:
      options:
        - name: buddy-luna-coder
          description: Implement and test software changes planned and reviewed by the lead.
          provider: openai-codex
          model: gpt-6-luna
          reasoning_effort: xhigh
          fallback_providers: []
```

Verify the selected provider account offers [GPT-6 Luna with `xhigh`](https://developers.openai.com/api/docs/models/gpt-6-luna). Check the effective fallback settings and disable fallbacks for this route. Confirm the route with `hermes delegation config --show`, start a new session, and invoke `/buddy-software-engineer` or name the skill in the request. For the first test, use a small change in a disposable local repository. Verify that the main agent plans before dispatch, the child result records `buddy-luna-coder` with `gpt-6-luna` and `xhigh`, and the main agent reviews the actual diff and reruns the checks before reporting completion.

## Local validation

From the repository root, the Hermes-independent suites can be run with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s runtimes/hermes/integrations/buddy-heartbeat -v
PYTHONDONTWRITEBYTECODE=1 python3 runtimes/hermes/integrations/buddy-session-policy/test_policy.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s runtimes/hermes/integrations/buddy-live-progress -v
```

Some native tests skip when Hermes is unavailable. The web backend imports Hermes APIs and dependencies and requires a separate test environment for complete validation. No test here should use production credentials, contact a real account or send a user-facing message.
