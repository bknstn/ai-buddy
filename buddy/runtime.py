"""Runtime adapter contract and lazy registry.

Core deliberately imports no runtime-specific package. A new adapter can be
added as ``runtimes/<id>/adapter.py`` and provide ``get_adapter()``.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
from pathlib import Path
from typing import Protocol

from buddy.errors import BuddyError
from buddy.profile import Profile


@dataclass(frozen=True)
class ArtifactMapping:
    source: str
    destination: str
    kind: str
    action: str = "manual_review"
    note: str = ""

    def as_dict(self) -> dict[str, str]:
        result = {
            "source": self.source,
            "destination": self.destination,
            "kind": self.kind,
            "action": self.action,
        }
        if self.note:
            result["note"] = self.note
        return result


class RuntimeAdapter(Protocol):
    runtime_id: str
    capabilities: frozenset[str]
    features: dict[str, frozenset[str]]

    def plan(self, profile: Profile, repository_root: Path) -> list[ArtifactMapping]: ...

    def environment(self, profile: Profile) -> dict[str, str]: ...


def get_adapter(runtime_id: str) -> RuntimeAdapter:
    module_name = f"runtimes.{runtime_id}.adapter"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name or module_name.startswith(f"{exc.name}."):
            raise BuddyError(f"Runtime adapter not found: {runtime_id}") from exc
        raise BuddyError(f"Runtime adapter {runtime_id!r} could not load: missing {exc.name}") from exc
    factory = getattr(module, "get_adapter", None)
    if not callable(factory):
        raise BuddyError(f"Runtime adapter {runtime_id!r} must define get_adapter()")
    adapter = factory()
    if getattr(adapter, "runtime_id", None) != runtime_id:
        raise BuddyError(f"Runtime adapter ID does not match profile: {runtime_id}")
    if not isinstance(getattr(adapter, "capabilities", None), (set, frozenset)):
        raise BuddyError(f"Runtime adapter {runtime_id!r} has no capability set")
    if not isinstance(getattr(adapter, "features", None), dict):
        raise BuddyError(f"Runtime adapter {runtime_id!r} has no feature capability map")
    return adapter


def validate_adapter_features(adapter: RuntimeAdapter, profile: Profile) -> None:
    for feature in profile.enabled_features:
        required = adapter.features.get(feature)
        if required is None:
            raise BuddyError(f"Runtime {profile.runtime_id!r} does not support feature {feature!r}")
        missing = sorted(set(required) - set(adapter.capabilities))
        if missing:
            raise BuddyError(
                f"Runtime {profile.runtime_id!r} cannot provide {feature!r}; "
                f"missing capabilities: {', '.join(missing)}"
            )
