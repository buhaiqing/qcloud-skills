#!/usr/bin/env python3
"""Tests for tccli_shadow.py — shadow rehearsal shim (record/replay)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tccli_shadow as ts


class NormalizeTest(unittest.TestCase):
    def test_flags_lowercased_and_sorted(self) -> None:
        n = ts.normalize_command("tccli cvm DescribeInstances --Limit 20 --Region ap-guangzhou")
        self.assertEqual(list(n["flags"].keys()), ["limit", "region"])

    def test_resource_ids_placeholdered(self) -> None:
        n = ts.normalize_command("tccli cvm TerminateInstances --instanceIds ins-abc ins-def")
        self.assertEqual(n["flags"]["instanceids"], "ins-* ins-*")

    def test_id_only_difference_maps_to_same_key(self) -> None:
        k1 = ts.command_key("tccli cvm StopInstances --instanceIds ins-aaa --region ap-gz")
        k2 = ts.command_key("tccli cvm StopInstances --instanceIds ins-bbb --region ap-gz")
        self.assertEqual(k1, k2)

    def test_action_changes_key(self) -> None:
        k1 = ts.command_key("tccli cvm StopInstances --instanceIds ins-a")
        k2 = ts.command_key("tccli cvm StartInstances --instanceIds ins-a")
        self.assertNotEqual(k1, k2)

    def test_rejects_non_tccli_and_short_options(self) -> None:
        with self.assertRaises(ValueError):
            ts.normalize_command("aws ec2 describe-instances")
        with self.assertRaises(ValueError):
            ts.normalize_command("tccli cvm Describe -x")

    def test_destructive_detection_covers_full_verb_set(self) -> None:
        # Critic finding: StopInstances / ReleaseAddresses were not gated before.
        self.assertTrue(ts.is_destructive_command("tccli cvm TerminateInstances --x y"))
        self.assertTrue(ts.is_destructive_command("tccli cvm StopInstances --x y"))
        self.assertTrue(ts.is_destructive_command("tccli vpc ReleaseAddresses --x y"))
        self.assertFalse(ts.is_destructive_command("tccli cvm DescribeInstances"))

    def test_multi_value_flag_arity_preserved_in_key(self) -> None:
        # Critic finding: "ins-a ins-b" must not collapse onto "ins-c".
        k2 = ts.command_key("tccli cvm TerminateInstances --instanceIds ins-a ins-b")
        k1 = ts.command_key("tccli cvm TerminateInstances --instanceIds ins-a")
        self.assertNotEqual(k1, k2)


class ExecTest(unittest.TestCase):
    def test_miss_exits_2_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc = ts.main(["exec", "--fixture-dir", tmp,
                          "--", "tccli cvm DescribeInstances"])
            self.assertEqual(rc, 2)

    def test_hit_returns_recorded_stdout_and_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cmd = "tccli cvm TerminateInstances --instanceIds ins-x"
            path = ts.save_fixture(cmd, stdout='{"Response": {"RequestId": "r-1"}}',
                                   stderr="", exit_code=0, fixture_dir=Path(tmp))
            fixture = json.loads(path.read_text())
            self.assertTrue(fixture["destructive"])
            # replay: capture stdout
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = ts.main(["exec", "--fixture-dir", tmp, "--", cmd])
            self.assertEqual(rc, 0)
            self.assertIn("RequestId", buf.getvalue())

    def test_stored_fixture_masks_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cmd = "tccli cvm DescribeInstances"
            ts.save_fixture(cmd, stdout="AKIDz123456SECRET out", stderr="", exit_code=0,
                            fixture_dir=Path(tmp))
            key = ts.command_key(cmd)
            text = (Path(tmp) / f"{key}.json").read_text()
            self.assertNotIn("AKIDz123456SECRET", text)

    def test_reject_malformed_command(self) -> None:
        rc = ts.main(["exec", "--", "not-tccli foo"])
        self.assertEqual(rc, 3)


class RecordSafetyTest(unittest.TestCase):
    def test_record_requires_yes_real_api(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc = ts.main(["record", "--fixture-dir", tmp, "--",
                          "tccli cvm DescribeInstances"])
            self.assertEqual(rc, 4)

    def test_destructive_record_requires_explicit_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc = ts.main(["record", "--yes-real-api", "--fixture-dir", tmp, "--",
                          "tccli cvm TerminateInstances --instanceIds ins-x"])
            self.assertEqual(rc, 4)

    def test_record_with_stubbed_tccli(self) -> None:
        import os
        import subprocess

        with tempfile.TemporaryDirectory() as tmp:
            fake_bin = Path(tmp) / "bin"
            fake_bin.mkdir()
            fake_tccli = fake_bin / "tccli"
            fake_tccli.write_text("#!/bin/sh\necho '{\"Response\": {\"RequestId\": \"fake\"}}'\n")
            fake_tccli.chmod(0o755)
            fixtures = Path(tmp) / "fx"
            env = dict(os.environ, PATH=f"{fake_bin}:{os.environ['PATH']}")
            proc = subprocess.run(
                [sys.executable, str(Path(ts.__file__)), "record",
                 "--yes-real-api", "--fixture-dir", str(fixtures), "--",
                 "tccli cvm DescribeInstances --region ap-gz"],
                capture_output=True, text=True, env=env, check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            stored = list(fixtures.glob("*.json"))
            self.assertEqual(len(stored), 1)
            data = json.loads(stored[0].read_text())
            self.assertEqual(data["exit_code"], 0)
            self.assertIn("RequestId", data["stdout"])

    def test_record_timeout_returns_5(self) -> None:
        import os
        import subprocess

        with tempfile.TemporaryDirectory() as tmp:
            fake_bin = Path(tmp) / "bin"
            fake_bin.mkdir()
            fake_tccli = fake_bin / "tccli"
            fake_tccli.write_text("#!/bin/sh\nsleep 3\n")
            fake_tccli.chmod(0o755)
            fixtures = Path(tmp) / "fx"
            env = dict(os.environ, PATH=f"{fake_bin}:{os.environ['PATH']}")
            proc = subprocess.run(
                [sys.executable, str(Path(ts.__file__)), "record",
                 "--yes-real-api", "--timeout", "1", "--fixture-dir", str(fixtures),
                 "--", "tccli cvm DescribeInstances"],
                capture_output=True, text=True, env=env, check=False,
            )
            self.assertEqual(proc.returncode, 5)
            self.assertIn("RECORD_TIMEOUT", proc.stderr)
            self.assertEqual(list(fixtures.glob("*.json")), [])


class GclRunnerIntegrationTest(unittest.TestCase):
    """TCCLI_SHADOW=1 must route run_command through replay-only exec."""

    CMD = "tccli cvm TerminateInstances --instanceIds ins-x"

    def _fixture_dir(self, tmp: str) -> str:
        ts.save_fixture(self.CMD, stdout='{"Response":{"RequestId":"shadow-1"}}',
                        stderr="", exit_code=0, fixture_dir=Path(tmp))
        return tmp
    def test_shadow_env_replays_fixture_without_network(self) -> None:
        import gcl_runner

        with tempfile.TemporaryDirectory() as tmp:
            fdir = self._fixture_dir(tmp)
            result = gcl_runner.run_command(
                self.CMD,
                env={"TCCLI_SHADOW": "1", "TCLOUD_KB_DIR": "", "SHADOW_FIXTURE_DIR": fdir},
            )
            self.assertTrue(result["shadow"])
            self.assertEqual(result["exit_code"], 0)
            # response came from the recorded fixture, not a real call
            self.assertIn("shadow-1", result["result_excerpt"])

    def test_no_shadow_env_reports_false(self) -> None:
        import os
        from unittest import mock

        import gcl_runner

        with mock.patch.object(gcl_runner.subprocess, "run") as fake_run:
            fake_run.return_value = mock.Mock(stdout="{}", stderr="", returncode=0)
            saved = os.environ.pop("TCCLI_SHADOW", None)
            try:
                result = gcl_runner.run_command(self.CMD)
            finally:
                if saved is not None:
                    os.environ["TCCLI_SHADOW"] = saved
            self.assertFalse(result["shadow"])


if __name__ == "__main__":
    unittest.main()
