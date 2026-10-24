# Runtime adapters

This directory holds optional adapters for conversational runtimes. The
`buddy` package owns profile parsing and generic capability checks; it does not
import a runtime's APIs or configuration schema. Hermes is the first adapter:
see [its integration guide](hermes/README.md).

## Add an adapter

Create `runtimes/<runtime_id>/adapter.py` and expose `get_adapter()`. Runtime
IDs use lowercase letters, digits and underscores, beginning with a letter.
The adapter object provides:

- `runtime_id`: the same identifier as the profile's `[runtime].id`.
- `capabilities`: a `frozenset` of supported generic asset types, such as
  `instruction_files`, `plugin_files`, `script_files` or `skill_files`.
- `features`: a mapping from feature IDs to the capabilities each feature
  requires. The core rejects unknown features and missing capabilities.
- `plan(profile, repository_root)`: return `ArtifactMapping` values for
  existing repository assets. Sources are repository-relative; destinations
  are proposed paths under the profile's configured runtime home.
- `environment(profile)`: return environment variable suggestions for an
  operator to apply manually.

Adapters must be declarative. `check` and `plan` must not import or start the
runtime, make network requests, read runtime state, install files, edit prompts,
configure accounts or create schedules. The registry imports the module named
by the profile ID, so adding an adapter does not require changing core profile
validation or core capability policy.

The fake adapter in `tests/test_buddy.py` exercises the seam. It is a synthetic
test fixture, not a supported second runtime.

## Profile and command behavior

Profiles are private directories created with `python3 -m buddy init --path
PATH` outside this repository. `config.toml` starts with no enabled features.
`check --profile PATH` validates the profile, adapter and declared capabilities
without requiring an installed runtime or contacting services. `plan
--profile PATH` describes mappings for core instruction fragments, optional
private instruction patterns and only explicitly enabled adapter features.
Both commands are read-only. A plan is not installation or compatibility
evidence.

Runtime homes and profile directories must resolve outside the public source
tree. Custom instructions belong under the private profile's `instructions/`
directory. Instruction mappings are review and composition inputs; they never
replace an existing runtime prompt automatically.
