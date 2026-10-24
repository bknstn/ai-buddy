"""Load and validate private AI Buddy profile configuration."""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
import tomllib
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from buddy.errors import BuddyError


RUNTIME_ID = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class Profile:
    path: Path
    schema_version: int
    name: str
    timezone: str
    runtime_id: str
    runtime_home: Path
    resolved_runtime_home: Path
    enabled_features: tuple[str, ...]


def profile_config_path(path: str | Path) -> Path:
    """Accept either a profile directory or its config.toml file."""
    candidate = Path(path).expanduser()
    if candidate.is_dir():
        candidate = candidate / "config.toml"
    elif candidate.name != "config.toml":
        candidate = candidate / "config.toml"
    return Path(os.path.abspath(candidate))


def load_profile(path: str | Path) -> Profile:
    config_path = profile_config_path(path)
    if not config_path.is_file():
        raise BuddyError(f"Profile config not found: {config_path}")
    try:
        with config_path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise BuddyError(f"Cannot read profile config: {exc}") from exc

    if set(raw) - {"schema_version", "assistant", "runtime", "features"}:
        raise BuddyError("Profile has unsupported top-level fields")
    schema_version = raw.get("schema_version")
    if type(schema_version) is not int or schema_version != 1:
        raise BuddyError("schema_version must be 1")

    assistant = raw.get("assistant")
    runtime = raw.get("runtime")
    features = raw.get("features")
    if not isinstance(assistant, dict) or set(assistant) != {"name", "timezone"}:
        raise BuddyError("[assistant] must contain only name and timezone")
    if not isinstance(runtime, dict) or set(runtime) != {"id", "home"}:
        raise BuddyError("[runtime] must contain only id and home")
    if not isinstance(features, dict) or set(features) != {"enabled"}:
        raise BuddyError("[features] must contain only enabled")

    name = assistant.get("name")
    timezone = assistant.get("timezone")
    runtime_id = runtime.get("id")
    runtime_home = runtime.get("home")
    enabled = features.get("enabled")
    if not isinstance(name, str) or not name.strip():
        raise BuddyError("[assistant].name must be a non-empty string")
    if not isinstance(timezone, str) or not timezone.strip():
        raise BuddyError("[assistant].timezone must be an IANA timezone")
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise BuddyError(f"Unknown IANA timezone: {timezone}") from exc
    if not isinstance(runtime_id, str) or not RUNTIME_ID.fullmatch(runtime_id):
        raise BuddyError("[runtime].id must start with a lowercase letter and contain only lowercase letters, digits, or underscores")
    if not isinstance(runtime_home, str) or not runtime_home.strip():
        raise BuddyError("[runtime].home must be an absolute private path")
    if "\x00" in runtime_home:
        raise BuddyError("[runtime].home contains an invalid path character")
    home = Path(runtime_home).expanduser()
    if not home.is_absolute():
        raise BuddyError("[runtime].home must be an absolute private path")
    try:
        resolved_home = home.resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        raise BuddyError("[runtime].home is not a usable filesystem path") from exc
    if not isinstance(enabled, list) or any(not isinstance(item, str) or not item.strip() for item in enabled):
        raise BuddyError("[features].enabled must be an array of feature IDs")
    if len(enabled) != len(set(enabled)):
        raise BuddyError("[features].enabled must not contain duplicates")

    return Profile(
        path=config_path.parent,
        schema_version=schema_version,
        name=name.strip(),
        timezone=timezone,
        runtime_id=runtime_id,
        runtime_home=home,
        resolved_runtime_home=resolved_home,
        enabled_features=tuple(sorted(enabled)),
    )
