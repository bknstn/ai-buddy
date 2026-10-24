"""Hermes adapter for planning source asset locations.

This module describes mappings only. It does not install plugins, modify
Hermes configuration, compose SOUL.md, inspect private runtime files, or start
services and schedules. The native compatibility of the legacy integrations
must be verified against the separately installed runtime.
"""

from __future__ import annotations

from pathlib import Path

from buddy.errors import BuddyError
from buddy.profile import Profile
from buddy.runtime import ArtifactMapping


CAPABILITIES = frozenset({"instruction_files", "plugin_files", "script_files", "skill_files"})
FEATURES = {
    "buddy-heartbeat": frozenset({"script_files", "instruction_files"}),
    "buddy-live-progress": frozenset({"plugin_files"}),
    "buddy-openai-web": frozenset({"plugin_files"}),
    "buddy-persona": frozenset({"instruction_files"}),
    "buddy-session-policy": frozenset({"plugin_files"}),
    "google-calendar": frozenset({"skill_files"}),
}


class HermesAdapter:
    runtime_id = "hermes"
    capabilities = CAPABILITIES
    features = FEATURES

    def environment(self, profile: Profile) -> dict[str, str]:
        """Environment settings an operator may apply manually after review."""
        return {
            "HERMES_HOME": str(profile.runtime_home),
            "ASSISTANT_TIMEZONE": profile.timezone,
        }

    def plan(self, profile: Profile, repository_root: Path) -> list[ArtifactMapping]:
        home = profile.runtime_home
        mappings: list[ArtifactMapping] = []
        instruction_dir = repository_root / "core" / "instructions"
        core_instructions = sorted(instruction_dir.glob("*.md")) if instruction_dir.is_dir() else []
        if not core_instructions:
            raise BuddyError("Required core instruction fragments are missing from core/instructions")
        for source in core_instructions:
            if not source.is_file():
                raise BuddyError(f"Required instruction asset is missing: {source.relative_to(repository_root)}")
            mappings.append(ArtifactMapping(
                source=source.relative_to(repository_root).as_posix(),
                destination=str(home / "instructions" / "ai-buddy" / source.name),
                kind="instruction_fragment",
                note="Review and compose manually; no existing SOUL.md or prompt is overwritten.",
            ))

        mappings.append(ArtifactMapping(
            source="<profile>/instructions/*.md",
            destination=str(home / "instructions" / "ai-buddy" / "private"),
            kind="private_instruction_pattern",
            note="Optional user-authored input; not enumerated or read by plan.",
        ))

        integration_root = repository_root / "runtimes" / "hermes" / "integrations"
        for feature in profile.enabled_features:
            if feature == "buddy-heartbeat":
                folder = integration_root / feature
                script_names = {
                    "collect_daily.py", "collect_weekly.py", "conversation_context.py",
                    "deliver.py", "heartbeat.py", "daily-prompt.md", "interaction.md",
                    "weekly-prompt.md",
                }
                for name in sorted(script_names):
                    source = folder / name
                    if not source.is_file():
                        raise BuddyError(f"Required feature asset is missing: {source.relative_to(repository_root)}")
                    kind = "script" if source.suffix == ".py" else "instruction_fragment"
                    mappings.append(ArtifactMapping(
                        source=source.relative_to(repository_root).as_posix(),
                        destination=str(home / "scripts" / feature / name),
                        kind=kind,
                        note="Manual installation only; collectors may access external sources when explicitly run.",
                    ))
            elif feature in {"buddy-live-progress", "buddy-openai-web", "buddy-session-policy"}:
                folder = integration_root / feature
                for name in ("__init__.py", "plugin.yaml"):
                    source = folder / name
                    if not source.is_file():
                        raise BuddyError(f"Required feature asset is missing: {source.relative_to(repository_root)}")
                    mappings.append(ArtifactMapping(
                        source=source.relative_to(repository_root).as_posix(),
                        destination=str(home / "plugins" / feature / name),
                        kind="plugin",
                        note="Manual installation and runtime compatibility review required.",
                    ))
            elif feature == "buddy-persona":
                folder = integration_root / feature
                persona_files = sorted(source for source in folder.glob("*.md") if source.name != "README.md")
                if not persona_files:
                    raise BuddyError("Required persona instruction assets are missing")
                for source in persona_files:
                    if source.is_file() and source.name != "README.md":
                        mappings.append(ArtifactMapping(
                            source=source.relative_to(repository_root).as_posix(),
                            destination=str(home / "instructions" / "ai-buddy" / "persona" / source.name),
                            kind="persona_instruction",
                            note="Optional guidance; review and compose manually. No existing SOUL.md or prompt is overwritten.",
                        ))
            elif feature == "google-calendar":
                source = integration_root / feature / "SKILL.md"
                if not source.is_file():
                    raise BuddyError(f"Required feature asset is missing: {source.relative_to(repository_root)}")
                mappings.append(ArtifactMapping(
                    source=source.relative_to(repository_root).as_posix(),
                    destination=str(home / "skills" / feature / "SKILL.md"),
                    kind="skill",
                    note="Instructions only; API access and credentials remain separately configured.",
                ))
        return mappings


def get_adapter() -> HermesAdapter:
    return HermesAdapter()
