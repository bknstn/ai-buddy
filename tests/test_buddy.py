from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from buddy.cli import REPOSITORY_ROOT, initialize, make_plan, profile_template, validate_profile
from buddy.errors import BuddyError
from buddy.profile import load_profile
from buddy.runtime import ArtifactMapping


CONFIG = '''schema_version = 1

[assistant]
name = "Test Buddy"
timezone = "UTC"

[runtime]
id = "fake"
home = "{home}"

[features]
enabled = {enabled}
'''


class FakeAdapter:
    runtime_id = "fake"
    capabilities = frozenset({"instruction_files"})
    features = {"fixture-feature": frozenset({"instruction_files"})}

    def __init__(self, destination: Path):
        self.destination = destination

    def plan(self, profile, repository_root):
        return [ArtifactMapping(
            source="synthetic/fixture.md",
            destination=str(self.destination / "fixture.md"),
            kind="instruction_fragment",
        )]

    def environment(self, profile):
        return {}


class BuddyProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.profile_dir = self.root / "profile"
        self.profile_dir.mkdir()
        self.runtime_home = self.root / "runtime-home"
        self.runtime_home.mkdir()
        (self.profile_dir / "config.toml").write_text(
            CONFIG.format(home=self.runtime_home, enabled="[]"), encoding="utf-8"
        )
        self.adapter = FakeAdapter(self.runtime_home)

    def tearDown(self):
        self.temp.cleanup()

    def test_init_creates_private_generic_profile_and_does_not_overwrite(self):
        destination = self.root / "new-instance"
        created = initialize(destination)
        config = created / "config.toml"
        self.assertEqual(config.read_text(encoding="utf-8"), profile_template(created / "runtime"))
        self.assertFalse((created / "runtime").exists())
        self.assertEqual(os.stat(created).st_mode & 0o777, 0o700)
        self.assertEqual(os.stat(config).st_mode & 0o777, 0o600)
        with self.assertRaises(BuddyError):
            initialize(destination)
        self.assertTrue(config.exists())

    def test_init_round_trips_unicode_quotes_and_backslashes_in_paths(self):
        destination = self.root / 'assistant-😀-"quoted"-back\\slash'
        created = initialize(destination)
        profile = load_profile(created)
        self.assertEqual(profile.path, created)
        self.assertEqual(profile.runtime_home, created / "runtime")

    def test_init_does_not_remove_a_path_created_by_another_process_at_the_mkdir_race(self):
        destination = self.root / "raced-instance"
        original_mkdir = Path.mkdir

        def race_mkdir(path, *args, **kwargs):
            if path.resolve(strict=False) == destination.resolve(strict=False):
                original_mkdir(path, *args, **kwargs)
                (path / "keep.txt").write_text("preserve", encoding="utf-8")
                raise FileExistsError(path)
            return original_mkdir(path, *args, **kwargs)

        with patch.object(Path, "mkdir", autospec=True, side_effect=race_mkdir):
            with self.assertRaises(FileExistsError):
                initialize(destination)
        self.assertEqual((destination / "keep.txt").read_text(encoding="utf-8"), "preserve")

    def test_init_rejects_a_destination_inside_repository(self):
        with self.assertRaises(BuddyError):
            initialize(REPOSITORY_ROOT / ".private-profile-test")
        self.assertFalse((REPOSITORY_ROOT / ".private-profile-test").exists())

    def test_disabled_features_are_valid_and_plan_has_no_optional_integration_assets(self):
        profile, adapter = validate_profile(self.profile_dir, adapter=self.adapter)
        self.assertEqual(profile.enabled_features, ())
        self.assertIs(adapter, self.adapter)
        plan = make_plan(self.profile_dir, adapter=self.adapter)
        self.assertEqual(plan["enabled_features"], [])
        self.assertEqual([item["source"] for item in plan["mappings"]], ["synthetic/fixture.md"])

    def test_fake_adapter_is_a_runtime_seam_and_plans_without_core_runtime_knowledge(self):
        (self.profile_dir / "config.toml").write_text(
            CONFIG.format(home=self.runtime_home, enabled='["fixture-feature"]'), encoding="utf-8"
        )
        plan = make_plan(self.profile_dir, adapter=self.adapter)
        self.assertEqual(plan["runtime"], "fake")
        self.assertEqual(plan["mappings"][0]["source"], "synthetic/fixture.md")
        self.assertFalse((self.runtime_home / "fixture.md").exists())

    def test_feature_requires_adapter_capabilities(self):
        (self.profile_dir / "config.toml").write_text(
            CONFIG.format(home=self.runtime_home, enabled='["plugin-feature"]'), encoding="utf-8"
        )
        adapter = FakeAdapter(self.runtime_home)
        adapter.features = {"plugin-feature": frozenset({"plugin_files"})}
        with self.assertRaisesRegex(BuddyError, "missing capabilities: plugin_files"):
            validate_profile(self.profile_dir, adapter=adapter)

    def test_profile_rejects_invalid_timezone_relative_runtime_and_unknown_features(self):
        path = self.profile_dir / "config.toml"
        path.write_text(CONFIG.format(home="relative/path", enabled="[]").replace('timezone = "UTC"', 'timezone = "Mars/Base"'))
        with self.assertRaisesRegex(BuddyError, "Unknown IANA timezone"):
            validate_profile(self.profile_dir, adapter=self.adapter)
        path.write_text(CONFIG.format(home="relative/path", enabled="[]"))
        with self.assertRaisesRegex(BuddyError, "absolute private path"):
            validate_profile(self.profile_dir, adapter=self.adapter)
        path.write_text(CONFIG.format(home=self.runtime_home, enabled='["unknown"]'))
        with self.assertRaisesRegex(BuddyError, "does not support feature"):
            validate_profile(self.profile_dir, adapter=self.adapter)

    def test_check_accepts_a_valid_profile_before_the_runtime_home_exists(self):
        missing_home = self.root / "not-created-yet"
        (self.profile_dir / "config.toml").write_text(
            CONFIG.format(home=missing_home, enabled="[]"), encoding="utf-8"
        )
        profile, _ = validate_profile(self.profile_dir, adapter=self.adapter)
        self.assertFalse(profile.resolved_runtime_home.exists())

    def test_check_and_plan_reject_runtime_or_profile_paths_inside_repository(self):
        (self.profile_dir / "config.toml").write_text(
            CONFIG.format(home=REPOSITORY_ROOT / "private-runtime", enabled="[]"), encoding="utf-8"
        )
        with self.assertRaisesRegex(BuddyError, "outside the repository"):
            validate_profile(self.profile_dir, adapter=self.adapter)
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as public_temp:
            public_profile = Path(public_temp)
            (public_profile / "config.toml").write_text(
                CONFIG.format(home=self.runtime_home, enabled="[]"), encoding="utf-8"
            )
            with self.assertRaisesRegex(BuddyError, "Private profiles"):
                make_plan(public_profile, adapter=self.adapter)

    def test_check_rejects_config_symlink_into_repository(self):
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as source_dir, tempfile.TemporaryDirectory() as profile_dir:
            target = Path(source_dir) / "config.toml"
            target.write_text(CONFIG.format(home=self.runtime_home, enabled="[]"), encoding="utf-8")
            outside_profile = Path(profile_dir)
            (outside_profile / "config.toml").symlink_to(target)
            with self.assertRaisesRegex(BuddyError, "Private profiles"):
                validate_profile(outside_profile, adapter=self.adapter)

    def test_check_rejects_runtime_home_symlink_into_repository(self):
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as source_dir:
            link = self.root / "runtime-link"
            link.symlink_to(source_dir, target_is_directory=True)
            (self.profile_dir / "config.toml").write_text(
                CONFIG.format(home=link, enabled="[]"), encoding="utf-8"
            )
            with self.assertRaisesRegex(BuddyError, "runtime.*outside the repository"):
                validate_profile(self.profile_dir, adapter=self.adapter)

    def test_null_byte_in_runtime_home_is_reported_as_invalid_configuration(self):
        (self.profile_dir / "config.toml").write_text(
            CONFIG.format(home="/tmp/invalid\\u0000path", enabled="[]"), encoding="utf-8"
        )
        with self.assertRaisesRegex(BuddyError, "invalid path character"):
            validate_profile(self.profile_dir, adapter=self.adapter)

    def test_unsupported_domains_table_is_rejected(self):
        config = CONFIG.format(home=self.runtime_home, enabled="[]") + "\n[domains]\nenabled = []\n"
        (self.profile_dir / "config.toml").write_text(config, encoding="utf-8")
        with self.assertRaisesRegex(BuddyError, "unsupported top-level fields"):
            validate_profile(self.profile_dir, adapter=self.adapter)

    def test_hermes_plan_sources_exist_and_destinations_remain_unmodified(self):
        from runtimes.hermes.adapter import get_adapter

        (self.profile_dir / "config.toml").write_text(
            CONFIG.replace('id = "fake"', 'id = "hermes"')
            .format(home=self.runtime_home, enabled='["buddy-live-progress", "google-calendar"]'),
            encoding="utf-8",
        )
        plan = make_plan(self.profile_dir, adapter=get_adapter())
        self.assertTrue(plan["mappings"])
        self.assertEqual(plan["runtime_environment"]["ASSISTANT_TIMEZONE"], "UTC")
        for item in plan["mappings"]:
            if item["source"].startswith("<profile>"):
                continue
            self.assertTrue((REPOSITORY_ROOT / item["source"]).is_file(), item["source"])
        self.assertFalse((self.runtime_home / "plugins").exists())
        self.assertFalse((self.runtime_home / "skills").exists())

    def test_hermes_plan_rejects_missing_required_feature_assets(self):
        from runtimes.hermes.adapter import get_adapter

        config = CONFIG.replace('id = "fake"', 'id = "hermes"').format(
            home=self.runtime_home, enabled='["buddy-openai-web"]'
        )
        (self.profile_dir / "config.toml").write_text(config, encoding="utf-8")
        profile = load_profile(self.profile_dir)
        with tempfile.TemporaryDirectory() as source_dir:
            repository = Path(source_dir)
            instructions = repository / "core" / "instructions"
            instructions.mkdir(parents=True)
            (instructions / "assistant.md").write_text("Generic instruction", encoding="utf-8")
            with self.assertRaisesRegex(BuddyError, "Required feature asset is missing"):
                get_adapter().plan(profile, repository)


if __name__ == "__main__":
    unittest.main()
