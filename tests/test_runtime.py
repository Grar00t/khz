"""No model downloads or external services. Temp fixtures; only owned child PIDs."""
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "khz"
loader = importlib.machinery.SourceFileLoader("khz_under_test", str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
khz = importlib.util.module_from_spec(spec)
loader.exec_module(khz)

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.output = io.StringIO()
        self.stack = contextlib.ExitStack()
        self.stack.enter_context(contextlib.redirect_stdout(self.output))
        self.stack.enter_context(contextlib.redirect_stderr(self.output))
        for key, value in {"HOME": str(self.home), "MODELS": str(self.home / "models"),
                           "STATE": str(self.home / "khz"), "REG": str(self.home / "khz/models.tsv"),
                           "START_TIMEOUT": .05, "STOP_TIMEOUT": .3}.items():
            self.stack.enter_context(patch.object(khz, key, value))
        khz.ensure()

    def tearDown(self):
        self.stack.close()
        self.temp.cleanup()

    def cached(self, name, revision="1" * 40, data=b"GGUFsmall"):
        path = self.home / ".cache/huggingface/hub/models--owner--repo/snapshots" / revision / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def register(self):
        path = Path(khz.MODELS) / "demo.gguf"
        path.write_bytes(b"GGUFtest")
        khz.write_rows([["demo", str(path), "builtin", "owner/repo:Q4_K_M", str(path.stat().st_size)]])
        return path

    def test_alias_blocks_traversal_and_control_characters(self):
        for name in ["../other", "a/b", "a\\b", "..", "-x", "a\tb", "a\nb", ""]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                khz.alias(name)
        self.assertEqual(khz.alias("Rawaseeng-14B_Oracle"), "Rawaseeng-14B_Oracle")

    def test_bad_alias_rejected_before_download(self):
        with patch.object(khz.subprocess, "call") as download:
            self.assertEqual(khz.main(["pull", "owner/repo:Q4_K_M", "../outside"]), 1)
            download.assert_not_called()

    def test_exact_quant_not_largest(self):
        expected = self.cached("model-Q4_K_M.gguf")
        self.cached("model-Q8_0.gguf", data=b"GGUF" + b"x" * 500)
        self.assertEqual(khz.select_cached("owner/repo:Q4_K_M"), str(expected))

    def test_ambiguous_quant_requires_choice(self):
        self.cached("a-Q4_K_M.gguf")
        self.cached("b-Q4_K_M.gguf")
        with self.assertRaises(ValueError):
            khz.select_cached("owner/repo:Q4_K_M")

    def test_main_revision_is_respected(self):
        expected = self.cached("model-Q4_K_M.gguf", revision="2" * 40)
        self.cached("model-Q4_K_M.gguf", revision="1" * 40)
        ref = expected.parents[2] / "refs/main"
        ref.parent.mkdir(); ref.write_text("2" * 40)
        self.assertEqual(khz.select_cached("owner/repo:Q4_K_M"), str(expected))

    def test_split_and_invalid_gguf_are_not_silently_selected(self):
        split = self.cached("model-Q4_K_M-00001-of-00002.gguf")
        with self.assertRaises(ValueError): khz.select_cached("owner/repo:Q4_K_M")
        split.unlink()
        self.cached("model-Q4_K_M.gguf", data=b"not-weights")
        with self.assertRaises(ValueError): khz.select_cached("owner/repo:Q4_K_M")

    def test_existing_weight_survives_failed_link_creation(self):
        src = self.cached("model-Q4_K_M.gguf")
        old = self.home / "old.gguf"; old.write_bytes(b"GGUFold")
        dst = self.home / "models/demo.gguf"; os.link(old, dst)
        with patch.object(khz.os, "link", side_effect=OSError("no hardlinks")), patch.object(khz.os, "symlink", side_effect=OSError("no symlinks")):
            with self.assertRaises(OSError): khz.replace_link(str(src), str(dst))
        self.assertEqual(dst.read_bytes(), b"GGUFold")

    def test_unique_existing_weight_is_not_deleted(self):
        src = self.cached("model-Q4_K_M.gguf")
        dst = self.home / "models/demo.gguf"; dst.write_bytes(b"GGUFunique")
        with self.assertRaises(ValueError): khz.replace_link(str(src), str(dst))
        self.assertEqual(dst.read_bytes(), b"GGUFunique")

    def test_managed_link_can_be_replaced_atomically(self):
        src = self.cached("model-Q4_K_M.gguf")
        old = self.home / "old.gguf"; old.write_bytes(b"GGUFold")
        dst = self.home / "models/demo.gguf"; os.link(old, dst)
        self.assertEqual(khz.replace_link(str(src), str(dst)), "hardlink")
        self.assertEqual(dst.read_bytes(), src.read_bytes())
        self.assertEqual(old.read_bytes(), b"GGUFold")

    def test_wrong_server_model_is_not_alive_success(self):
        self.register()
        with patch.object(khz, "health", return_value=True), patch.object(khz, "models_id", return_value="different"), patch.object(khz.subprocess, "Popen") as spawn:
            with self.assertRaisesRegex(ValueError, "PORT_MODEL_MISMATCH"): khz.cmd_run(["demo"])
            spawn.assert_not_called()

    def test_matching_server_is_not_restarted(self):
        self.register()
        with patch.object(khz, "health", return_value=True), patch.object(khz, "models_id", return_value="demo"), patch.object(khz.subprocess, "Popen") as spawn:
            self.assertEqual(khz.cmd_run(["demo"]), 0)
            spawn.assert_not_called()

    def test_stop_denial_keeps_identity_record(self):
        record = {"model": "demo", "identity": {"pid": 4242, "start": "7", "group": 4242, "session": 4242, "boot": "test"}}
        target = Path(khz.STATE) / "demo.pid"; target.write_text(json.dumps(record))
        with patch.object(khz, "process_identity", return_value=record["identity"]), patch.object(khz.os, "killpg", side_effect=PermissionError("fixture")):
            with self.assertRaises(PermissionError): khz.cmd_stop(["demo"])
        self.assertTrue(target.exists())
        self.assertNotIn("STOPPED", self.output.getvalue())

    def test_reused_pid_is_never_signalled(self):
        identity = {"pid": 4242, "start": "7", "group": 4242, "session": 4242, "boot": "test"}
        with patch.object(khz, "process_identity", return_value={**identity, "start": "8"}), patch.object(khz.os, "killpg") as kill:
            with self.assertRaises(ValueError): khz.stop_owned(identity)
            kill.assert_not_called()

    def test_legacy_numeric_pid_is_refused(self):
        target = Path(khz.STATE) / "demo.pid"; target.write_text("4242")
        with patch.object(khz.os, "killpg") as kill:
            with self.assertRaises(ValueError): khz.cmd_stop(["demo"])
            kill.assert_not_called()
        self.assertTrue(target.exists())

    def test_registry_write_failure_preserves_original_index(self):
        self.register(); before = Path(khz.REG).read_bytes()
        with patch.object(khz.os, "replace", side_effect=OSError("fixture")):
            with self.assertRaises(OSError): khz.write_rows([])
        self.assertEqual(Path(khz.REG).read_bytes(), before)

    def test_missing_arguments_return_usage_error(self):
        for args in [["pull"], ["run"], ["stop"], ["logs"], ["list", "extra"]]:
            self.assertEqual(khz.main(args), 2)

    def test_ports_validate_range(self):
        for port in ["0", "65536", "bad"]:
            with self.assertRaises(ValueError): khz.port_number(port)
        self.assertEqual(khz.port_number("8080"), "8080")

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux process supervision")
    def test_start_timeout_reaps_owned_child(self):
        self.register()
        executable = self.home / "fake-llama"
        executable.write_text("#!" + sys.executable + "\nimport time\ntime.sleep(60)\n")
        executable.chmod(0o700)
        created = []
        original = subprocess.Popen
        def spawn(*args, **kwargs):
            child = original(*args, **kwargs); created.append(child); return child
        try:
            with patch.object(khz, "LLAMA", str(executable)), patch.object(khz, "health", return_value=False), patch.object(khz.subprocess, "Popen", side_effect=spawn):
                with self.assertRaises(TimeoutError): khz.cmd_run(["demo"])
            self.assertIsNotNone(created[0].poll())
            self.assertFalse((Path(khz.STATE) / "demo.pid").exists())
        finally:
            for child in created:
                if child.poll() is None: os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=3)

if __name__ == "__main__":
    unittest.main(verbosity=2)
