import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PLUGIN_PATH = (
    Path(__file__).resolve().parents[1]
    / "runtimes" / "hermes" / "integrations" / "buddy-audigest" / "__init__.py"
)
SPEC = importlib.util.spec_from_file_location("buddy_audigest", PLUGIN_PATH)
PLUGIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PLUGIN)


class AudigestIntegrationTests(unittest.TestCase):
    def test_transcription_requires_explicit_openai_and_passes_only_its_credential(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory).resolve()
            attachment_dir = profile / "cache" / "audio"
            attachment_dir.mkdir(parents=True)
            audio = attachment_dir / "sample.wav"
            audio.touch()
            executable = profile / "audigest" / "venv" / "bin" / "audigest"
            executable.parent.mkdir(parents=True)
            executable.touch()
            args = {"operation": "transcribe", "input": str(audio)}
            key = Mock(return_value="synthetic-openai-key")
            result = subprocess.CompletedProcess([], 0, json.dumps({"id": "sample-id"}).encode())
            with patch.object(PLUGIN.subprocess, "run", return_value=result) as run:
                with patch.dict("os.environ", {"OTHER_API_KEY": "unrelated-synthetic-key"}):
                    self.assertEqual(
                        PLUGIN._run(args, profile, (attachment_dir,), key, None)["transcript_id"],
                        "sample-id",
                    )
                    key.assert_not_called()
                    self.assertNotIn("OPENAI_API_KEY", run.call_args.kwargs["env"])
                    self.assertIn("auto", run.call_args.args[0])

                    PLUGIN._run({**args, "use_openai": True}, profile, (attachment_dir,), key, None)
                    key.assert_called_once_with("OPENAI_API_KEY")
                    self.assertEqual(run.call_args.kwargs["env"]["OPENAI_API_KEY"], key.return_value)
                    self.assertNotIn("OTHER_API_KEY", run.call_args.kwargs["env"])
                    self.assertNotIn(key.return_value, run.call_args.args[0])

    def test_ingest_rejects_external_files_urls_and_symlinked_sidecars(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory).resolve()
            inbox = profile / "audigest" / "inbox"
            inbox.mkdir(parents=True)
            outside = profile / "outside.txt"
            outside.touch()
            audio = inbox / "sample.wav"
            audio.touch()
            audio.with_suffix(".vtt").symlink_to(outside)
            key = Mock()
            with patch.object(PLUGIN.subprocess, "run") as run:
                for source in (str(outside), "https://example.com/sample.wav", str(audio)):
                    with self.subTest(source=source):
                        result = PLUGIN._run(
                            {"operation": "ingest", "input": source, "use_openai": True},
                            profile, (), key, None,
                        )
                        self.assertIn("error", result)
                key.assert_not_called()
                run.assert_not_called()
