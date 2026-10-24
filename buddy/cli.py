"""Private profile initialization, validation, and local mapping plans."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from buddy.errors import BuddyError
from buddy.profile import load_profile
from buddy.runtime import get_adapter, validate_adapter_features


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def profile_template(runtime_home: Path) -> str:
    # JSON strings use the same escaping rules as TOML basic strings.
    return (
        "schema_version = 1\n\n"
        "[assistant]\n"
        'name = "My Assistant"\n'
        'timezone = "UTC"\n\n'
        "[runtime]\n"
        'id = "hermes"\n'
        f"home = {json.dumps(str(runtime_home), ensure_ascii=False)}\n\n"
        "[features]\n"
        "enabled = []\n"
    )


def _resolved_destination(value: str | Path) -> Path:
    return Path(value).expanduser().resolve(strict=False)


def initialize(path: str | Path) -> Path:
    try:
        expanded = Path(path).expanduser()
        lexical_destination = Path(os.path.abspath(expanded))
        destination = _resolved_destination(expanded)
    except (OSError, RuntimeError, ValueError) as exc:
        raise BuddyError("Instance path is not a usable filesystem path") from exc
    repo = REPOSITORY_ROOT.resolve()
    if _path_is_within(lexical_destination, repo) or _path_is_within(destination, repo):
        raise BuddyError("Choose a private instance path outside the repository")
    if os.path.lexists(expanded):
        raise BuddyError(f"Instance path already exists: {destination}")
    parent = destination.parent
    if not parent.is_dir():
        raise BuddyError(f"Parent directory must already exist: {parent}")
    created = False
    config_created = False
    config = destination / "config.toml"
    try:
        destination.mkdir(mode=0o700)
        created = True
        descriptor = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        config_created = True
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(profile_template(destination / "runtime"))
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        if config_created:
            config.unlink(missing_ok=True)
        if created:
            try:
                destination.rmdir()
            except OSError:
                pass
        raise
    return destination


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _load_and_validate_selection(path: str | Path, *, adapter=None):
    profile = load_profile(path)
    repo = REPOSITORY_ROOT.resolve()
    config_path = profile.path / "config.toml"
    if (_path_is_within(Path(os.path.abspath(profile.path)), repo)
            or _path_is_within(profile.path.resolve(strict=False), repo)
            or _path_is_within(Path(os.path.abspath(config_path)), repo)
            or _path_is_within(config_path.resolve(strict=False), repo)):
        raise BuddyError("Private profiles must be stored outside the repository")
    authored_home = Path(os.path.abspath(profile.runtime_home))
    if (_path_is_within(authored_home, repo)
            or _path_is_within(profile.resolved_runtime_home, repo)):
        raise BuddyError("[runtime].home must be outside the repository")
    selected = adapter if adapter is not None else get_adapter(profile.runtime_id)
    if getattr(selected, "runtime_id", None) != profile.runtime_id:
        raise BuddyError("Selected adapter ID does not match profile")
    validate_adapter_features(selected, profile)
    return profile, selected


def validate_profile(path: str | Path, *, adapter=None):
    profile, selected = _load_and_validate_selection(path, adapter=adapter)
    # Checking the adapter's plan verifies that all required source assets are
    # present without reading or listing files under the private runtime home.
    selected.plan(profile, REPOSITORY_ROOT)
    return profile, selected


def make_plan(path: str | Path, *, adapter=None) -> dict:
    profile, selected = _load_and_validate_selection(path, adapter=adapter)
    mappings = selected.plan(profile, REPOSITORY_ROOT)
    plan = {
        "schema_version": 1,
        "runtime": profile.runtime_id,
        "runtime_home": str(profile.runtime_home),
        "assistant": {"name": profile.name, "timezone": profile.timezone},
        "enabled_features": list(profile.enabled_features),
        "mappings": [mapping.as_dict() for mapping in mappings],
        "notes": [
            "Planning only: no files were installed, services started, or schedules created.",
            "Runtime compatibility and native account configuration require separate validation.",
            "Instruction fragments require manual review and composition; existing runtime instructions are not overwritten.",
        ],
    }
    environment = getattr(selected, "environment", None)
    if callable(environment):
        plan["runtime_environment"] = environment(profile)
    return plan


def _render_text(plan: dict) -> str:
    lines = [
        f"Runtime: {plan['runtime']}",
        f"Runtime home: {plan['runtime_home']}",
        f"Assistant: {plan['assistant']['name']} ({plan['assistant']['timezone']})",
        "Enabled features: " + (", ".join(plan["enabled_features"]) or "none"),
        "Suggested environment (manual configuration only):",
    ]
    lines.extend(f"- {key}={value}" for key, value in sorted(plan.get("runtime_environment", {}).items()))
    lines.extend([
        "Planned mappings (manual review; no changes applied):",
    ])
    if plan["mappings"]:
        lines.extend(
            f"- {item['source']} -> {item['destination']} [{item['kind']}]"
            for item in plan["mappings"]
        )
    else:
        lines.append("- No source assets found.")
    lines.extend(f"Note: {note}" for note in plan["notes"])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python3 -m buddy", description="Manage a private AI Buddy profile.")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="Create a private profile directory.")
    init.add_argument("--path", required=True, help="New instance directory outside this repository.")

    check = commands.add_parser("check", help="Validate a private profile and its runtime capabilities.")
    check.add_argument("--profile", required=True, help="Profile directory or config.toml path.")

    plan = commands.add_parser("plan", help="Show a local source-to-runtime mapping without applying it.")
    plan.add_argument("--profile", required=True, help="Profile directory or config.toml path.")
    plan.add_argument("--format", choices=("json", "text"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            destination = initialize(args.path)
            print(f"Created private profile directory: {destination}")
            print(f"Edit {destination / 'config.toml'} to select a runtime and its home directory.")
            print("Optional custom instructions can be added under instructions/.")
            return 0
        if args.command == "check":
            profile, adapter = validate_profile(args.profile)
            print(f"Profile valid: {profile.path}")
            print(f"Runtime adapter: {adapter.runtime_id}")
            state = "exists" if profile.resolved_runtime_home.is_dir() else "not created yet"
            print(f"Runtime home path: {profile.runtime_home} ({state})")
            print("Enabled features: " + (", ".join(profile.enabled_features) or "none"))
            print("Native runtime compatibility and account configuration are not verified.")
            return 0
        plan = make_plan(args.profile)
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True)
              if args.format == "json" else _render_text(plan))
        return 0
    except BuddyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: filesystem operation failed: {exc}", file=sys.stderr)
        return 2
