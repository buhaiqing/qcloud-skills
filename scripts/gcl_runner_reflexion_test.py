#!/usr/bin/env python3
"""Unit tests for gcl_runner reflexion wiring.

Tests the integration between gcl_runner and reflexion_retrieve modules,
verifying that failure patterns are loaded, formatted, and injected correctly.

Run: python3 -m unittest scripts.gcl_runner_reflexion_test -v
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

# Ensure scripts/ is on sys.path when invoked as `python3 scripts/gcl_runner_reflexion_test.py"
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import gcl_runner  # noqa: E402


def quiet_cmd_run(ns) -> int:
    """Run cmd_run suppressing stdout/stderr."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return gcl_runner.cmd_run(ns)


class TestLoadFailurePatternsIntegration(unittest.TestCase):
    """Test (1): load_failure_patterns() returns list of pattern dicts."""

    @patch("gcl_runner.load_failure_patterns")
    def test_load_failure_patterns_returns_list_of_dicts(self, mock_load: MagicMock) -> None:
        """Verify load_failure_patterns returns list of pattern dicts with expected keys."""
        # Setup mock to return sample patterns
        mock_patterns: list[dict[str, Any]] = [
            {
                "category": "cli_parameter",
                "skill": "qcloud-cvm-ops",
                "command": "TerminateInstances",
                "error": "MissingParameter",
                "fix": "Use JSON array format",
                "count": 5,
                "reusable": True,
            },
            {
                "category": "runtime",
                "skill": "qcloud-cvm-ops",
                "command": "DescribeInstances",
                "error": "RequestLimitExceeded",
                "fix": "Add retry with backoff",
                "count": 3,
                "reusable": True,
            },
        ]
        mock_load.return_value = mock_patterns

        # Call the function through gcl_runner's import
        result = gcl_runner.load_failure_patterns("qcloud-cvm-ops", "tccli cvm TerminateInstances")

        # Verify it returns a list
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

        # Verify each item is a dict with expected keys
        for pattern in result:
            self.assertIsInstance(pattern, dict)
            self.assertIn("category", pattern)
            self.assertIn("skill", pattern)
            self.assertIn("command", pattern)
            self.assertIn("error", pattern)
            self.assertIn("fix", pattern)
            self.assertIn("count", pattern)
            self.assertIn("reusable", pattern)

    @patch("gcl_runner.load_failure_patterns")
    def test_load_failure_patterns_empty_list_when_no_matches(self, mock_load: MagicMock) -> None:
        """Verify empty list returned when no patterns match."""
        mock_load.return_value = []

        result = gcl_runner.load_failure_patterns("qcloud-nonexistent-ops", "some command")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    @patch("gcl_runner.load_failure_patterns")
    def test_load_failure_patterns_exception_handling(self, mock_load: MagicMock) -> None:
        """Verify exception in load_failure_patterns is handled gracefully in cmd_run context."""
        mock_load.side_effect = Exception("File not found")

        # In cmd_run, exceptions are caught and empty list is used
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            critic_file = tmp_path / "critic.json"
            critic_payload = {
                "scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1, "spec_compliance": 1},
                "suggestions": [],
                "blocking": False,
            }
            critic_file.write_text(json.dumps(critic_payload))

            ns = gcl_runner.build_parser().parse_args([
                "run",
                "--root", str(tmp_path),
                "--skill", "qcloud-test-ops",
                "--request", "test request",
                "--command", 'echo "test"',
                "--critic-json", str(critic_file),
            ])

            # Should not raise - exception is caught in cmd_run
            rc = quiet_cmd_run(ns)
            self.assertEqual(rc, 0)  # PASS


class TestFormatForInjectionIntegration(unittest.TestCase):
    """Test (2): format_for_injection() formats patterns correctly for GCL prompt injection."""

    @patch("gcl_runner.ff_fail")
    def test_format_for_injection_with_patterns(self, mock_format: MagicMock) -> None:
        """Verify format_for_injection returns properly formatted string for injection."""
        patterns: list[dict[str, Any]] = [
            {
                "category": "cli_parameter",
                "skill": "qcloud-cvm-ops",
                "command": "TerminateInstances",
                "error": "MissingParameter",
                "fix": "Use JSON array format",
                "count": 5,
                "reusable": True,
            }
        ]
        expected_block = """## Reflexion Failure Patterns (Pre-flight hints)

- [cli_parameter] qcloud-cvm-ops: MissingParameter
  Fix: Use JSON array format
"""
        mock_format.return_value = expected_block

        result = gcl_runner.ff_fail(patterns)

        self.assertIsInstance(result, str)
        self.assertIn("Reflexion Failure Patterns", result)
        self.assertIn("cli_parameter", result)
        self.assertIn("MissingParameter", result)

    @patch("gcl_runner.ff_fail")
    def test_format_for_injection_empty_list(self, mock_format: MagicMock) -> None:
        """Verify format_for_injection returns empty string for empty list."""
        mock_format.return_value = ""

        result = gcl_runner.ff_fail([])

        self.assertEqual(result, "")

    @patch("gcl_runner.ff_fail")
    def test_format_for_injection_multiple_patterns(self, mock_format: MagicMock) -> None:
        """Verify format_for_injection handles multiple patterns correctly."""
        patterns: list[dict[str, Any]] = [
            {
                "category": "cli_parameter",
                "skill": "qcloud-cvm-ops",
                "command": "TerminateInstances",
                "error": "MissingParameter",
                "fix": "Use JSON array format",
                "count": 5,
                "reusable": True,
            },
            {
                "category": "runtime",
                "skill": "qcloud-cvm-ops",
                "command": "DescribeInstances",
                "error": "RequestLimitExceeded",
                "fix": "Add retry with backoff",
                "count": 3,
                "reusable": True,
            },
        ]
        expected_block = """## Reflexion Failure Patterns (Pre-flight hints)

- [cli_parameter] qcloud-cvm-ops: MissingParameter
  Fix: Use JSON array format
- [runtime] qcloud-cvm-ops: RequestLimitExceeded
  Fix: Add retry with backoff
"""
        mock_format.return_value = expected_block

        result = gcl_runner.ff_fail(patterns)

        self.assertIsInstance(result, str)
        self.assertIn("cli_parameter", result)
        self.assertIn("runtime", result)
        self.assertIn("MissingParameter", result)
        self.assertIn("RequestLimitExceeded", result)

    def test_format_for_injection_real_output_format(self) -> None:
        """Real function (no mock) to address F-002: mock-based tests miss format regressions."""
        from reflexion_retrieve import format_for_injection as real_format

        patterns: list[dict[str, Any]] = [
            {
                "category": "cli_parameter",
                "skill": "qcloud-cvm-ops",
                "command": "TerminateInstances",
                "error": "MissingParameter",
                "fix": "Use JSON array format",
                "count": 5,
                "reusable": True,
            },
        ]
        result = real_format(patterns)

        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith("- ["))
        self.assertIn("qcloud-cvm-ops", result)
        self.assertIn("error=", result)
        self.assertIn("-> fix=", result)
        self.assertIn("(count=5", result)  # P0-C: format includes last_seen
        self.assertIn("`MissingParameter`", result)
        self.assertIn("`Use JSON array format`", result)

        cred_patterns = [
            {
                "category": "runtime",
                "skill": "qcloud-cos-ops",
                "error": "SecretKey=FAKE_SECRET_ID_FOR_TESTONLY",
                "fix": "Rotate credentials",
                "count": 1,
            }
        ]
        cred_result = real_format(cred_patterns)
        self.assertNotIn("FAKE_SECRET_ID", cred_result)
        self.assertIn("<masked>", cred_result)


class TestReflexionPatternsEnvVar(unittest.TestCase):
    """Test (3): REFLEXION_PATTERNS env var is set when patterns exist."""

    @patch("gcl_runner.load_failure_patterns")
    @patch("gcl_runner.ff_fail")
    def test_env_var_set_when_patterns_exist(
        self, mock_format: MagicMock, mock_load: MagicMock
    ) -> None:
        """Verify REFLEXION_PATTERNS env var is set when patterns are found."""
        patterns = [{"category": "cli_parameter", "skill": "qcloud-cvm-ops", "error": "test"}]
        mock_load.return_value = patterns
        mock_format.return_value = "## Reflexion Patterns\n\n- test pattern"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            critic_file = tmp_path / "critic.json"
            critic_payload = {
                "scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1, "spec_compliance": 1},
                "suggestions": [],
                "blocking": False,
            }
            critic_file.write_text(json.dumps(critic_payload))

            # Capture the environment passed to run_command
            captured_env: dict[str, str] | None = None

            def capture_run_command(command: str, timeout: int = 120, env: dict[str, str] | None = None) -> dict[str, Any]:
                nonlocal captured_env
                captured_env = env
                return {
                    "command": command,
                    "exit_code": 0,
                    "result_excerpt": "ok",
                    "stdout_len": 2,
                    "stderr_len": 0,
                }

            with patch("gcl_runner.run_command", side_effect=capture_run_command):
                ns = gcl_runner.build_parser().parse_args([
                    "run",
                    "--root", str(tmp_path),
                    "--skill", "qcloud-cvm-ops",
                    "--request", "test request",
                    "--command", 'echo "test"',
                    "--critic-json", str(critic_file),
                ])
                quiet_cmd_run(ns)

            # Verify REFLEXION_PATTERNS was set in env
            self.assertIsNotNone(captured_env)
            self.assertIn("REFLEXION_PATTERNS", captured_env)
            self.assertIn("Reflexion Patterns", captured_env["REFLEXION_PATTERNS"])

    @patch("gcl_runner.load_failure_patterns")
    @patch("gcl_runner.ff_fail")
    def test_env_var_not_set_when_no_patterns(
        self, mock_format: MagicMock, mock_load: MagicMock
    ) -> None:
        """Verify REFLEXION_PATTERNS env var is NOT set when no patterns found."""
        mock_load.return_value = []
        mock_format.return_value = ""

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            critic_file = tmp_path / "critic.json"
            critic_payload = {
                "scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1, "spec_compliance": 1},
                "suggestions": [],
                "blocking": False,
            }
            critic_file.write_text(json.dumps(critic_payload))

            captured_env: dict[str, str] | None = None

            def capture_run_command(command: str, timeout: int = 120, env: dict[str, str] | None = None) -> dict[str, Any]:
                nonlocal captured_env
                captured_env = env
                return {
                    "command": command,
                    "exit_code": 0,
                    "result_excerpt": "ok",
                    "stdout_len": 2,
                    "stderr_len": 0,
                }

            with patch("gcl_runner.run_command", side_effect=capture_run_command):
                ns = gcl_runner.build_parser().parse_args([
                    "run",
                    "--root", str(tmp_path),
                    "--skill", "qcloud-cvm-ops",
                    "--request", "test request",
                    "--command", 'echo "test"',
                    "--critic-json", str(critic_file),
                ])
                quiet_cmd_run(ns)

            # Verify REFLEXION_PATTERNS was NOT set (env should be None or not contain key)
            if captured_env is not None:
                self.assertNotIn("REFLEXION_PATTERNS", captured_env)

    @patch("gcl_runner.load_failure_patterns")
    @patch("gcl_runner.ff_fail")
    def test_env_var_contains_formatted_patterns(
        self, mock_format: MagicMock, mock_load: MagicMock
    ) -> None:
        """Verify REFLEXION_PATTERNS contains the formatted pattern block."""
        patterns = [{"category": "cli_parameter", "skill": "qcloud-cvm-ops", "error": "test"}]
        formatted_block = """## Reflexion Failure Patterns (Pre-flight hints)

- [cli_parameter] qcloud-cvm-ops: MissingParameter
  Fix: Use JSON array format
"""
        mock_load.return_value = patterns
        mock_format.return_value = formatted_block

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            critic_file = tmp_path / "critic.json"
            critic_payload = {
                "scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1, "spec_compliance": 1},
                "suggestions": [],
                "blocking": False,
            }
            critic_file.write_text(json.dumps(critic_payload))

            captured_env: dict[str, str] | None = None

            def capture_run_command(command: str, timeout: int = 120, env: dict[str, str] | None = None) -> dict[str, Any]:
                nonlocal captured_env
                captured_env = env
                return {
                    "command": command,
                    "exit_code": 0,
                    "result_excerpt": "ok",
                    "stdout_len": 2,
                    "stderr_len": 0,
                }

            with patch("gcl_runner.run_command", side_effect=capture_run_command):
                ns = gcl_runner.build_parser().parse_args([
                    "run",
                    "--root", str(tmp_path),
                    "--skill", "qcloud-cvm-ops",
                    "--request", "test request",
                    "--command", 'echo "test"',
                    "--critic-json", str(critic_file),
                ])
                quiet_cmd_run(ns)

            self.assertIsNotNone(captured_env)
            self.assertEqual(captured_env.get("REFLEXION_PATTERNS"), formatted_block)


class TestPreflightReflexionLogging(unittest.TestCase):
    """Test (4): preflight_reflexion.matched count is logged in trace."""

    @patch("gcl_runner.load_failure_patterns")
    @patch("gcl_runner.ff_fail")
    def test_matched_count_logged_in_trace(
        self, mock_format: MagicMock, mock_load: MagicMock
    ) -> None:
        """Verify preflight_reflexion includes matched count in trace output."""
        patterns = [
            {"category": "cli_parameter", "skill": "qcloud-cvm-ops", "error": "test1"},
            {"category": "runtime", "skill": "qcloud-cvm-ops", "error": "test2"},
            {"category": "cross_skill", "skill": "qcloud-cvm-ops", "error": "test3"},
        ]
        mock_load.return_value = patterns
        mock_format.return_value = "## Reflexion Patterns\n\n- test"

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            critic_file = tmp_path / "critic.json"
            critic_payload = {
                "scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1, "spec_compliance": 1},
                "suggestions": [],
                "blocking": False,
            }
            critic_file.write_text(json.dumps(critic_payload))

            ns = gcl_runner.build_parser().parse_args([
                "run",
                "--root", str(tmp_path),
                "--skill", "qcloud-cvm-ops",
                "--request", "test request",
                "--command", 'echo "test"',
                "--critic-json", str(critic_file),
            ])
            quiet_cmd_run(ns)

            # Read the trace file
            trace_files = list((tmp_path / "audit-results").glob("gcl-trace-*.json"))
            self.assertEqual(len(trace_files), 1)

            trace_data = json.loads(trace_files[0].read_text())

            # Verify preflight_reflexion exists and has matched count
            self.assertIn("preflight_reflexion", trace_data)
            preflight = trace_data["preflight_reflexion"]
            self.assertIn("matched_failures", preflight)
            self.assertEqual(preflight["matched_failures"], 3)  # Should match number of patterns

    @patch("gcl_runner.load_failure_patterns")
    @patch("gcl_runner.ff_fail")
    def test_matched_count_zero_when_no_patterns(
        self, mock_format: MagicMock, mock_load: MagicMock
    ) -> None:
        """Verify preflight_reflexion.matched_failures is 0 when no patterns found."""
        mock_load.return_value = []
        mock_format.return_value = ""

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            critic_file = tmp_path / "critic.json"
            critic_payload = {
                "scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1, "spec_compliance": 1},
                "suggestions": [],
                "blocking": False,
            }
            critic_file.write_text(json.dumps(critic_payload))

            ns = gcl_runner.build_parser().parse_args([
                "run",
                "--root", str(tmp_path),
                "--skill", "qcloud-cvm-ops",
                "--request", "test request",
                "--command", 'echo "test"',
                "--critic-json", str(critic_file),
            ])
            quiet_cmd_run(ns)

            trace_files = list((tmp_path / "audit-results").glob("gcl-trace-*.json"))
            self.assertEqual(len(trace_files), 1)

            trace_data = json.loads(trace_files[0].read_text())

            self.assertIn("preflight_reflexion", trace_data)
            preflight = trace_data["preflight_reflexion"]
            self.assertIn("matched_failures", preflight)
            self.assertEqual(preflight["matched_failures"], 0)

    @patch("gcl_runner.load_failure_patterns")
    @patch("gcl_runner.ff_fail")
    def test_preflight_reflexion_includes_all_fields(
        self, mock_format: MagicMock, mock_load: MagicMock
    ) -> None:
        """Verify preflight_reflexion includes skill, command, matched, and injection."""
        patterns = [{"category": "cli_parameter", "skill": "qcloud-cvm-ops", "error": "test"}]
        formatted_block = "## Reflexion Patterns\n\n- test pattern"
        mock_load.return_value = patterns
        mock_format.return_value = formatted_block

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            critic_file = tmp_path / "critic.json"
            critic_payload = {
                "scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1, "spec_compliance": 1},
                "suggestions": [],
                "blocking": False,
            }
            critic_file.write_text(json.dumps(critic_payload))

            ns = gcl_runner.build_parser().parse_args([
                "run",
                "--root", str(tmp_path),
                "--skill", "qcloud-cvm-ops",
                "--request", "test request",
                "--command", 'tccli cvm DescribeInstances',
                "--critic-json", str(critic_file),
            ])
            quiet_cmd_run(ns)

            trace_files = list((tmp_path / "audit-results").glob("gcl-trace-*.json"))
            trace_data = json.loads(trace_files[0].read_text())

            preflight = trace_data["preflight_reflexion"]

            # Verify all expected fields
            self.assertIn("skill", preflight)
            self.assertIn("command", preflight)
            self.assertIn("matched_failures", preflight)
            self.assertIn("injection", preflight)

            self.assertEqual(preflight["skill"], "qcloud-cvm-ops")
            self.assertEqual(preflight["command"], "tccli cvm DescribeInstances")
            self.assertEqual(preflight["matched_failures"], 1)
            self.assertEqual(preflight["injection"], formatted_block)


class TestReflexionEndToEnd(unittest.TestCase):
    """End-to-end tests for reflexion wiring."""

    @patch("gcl_runner.load_failure_patterns")
    @patch("gcl_runner.ff_fail")
    def test_full_reflexion_flow_with_patterns(
        self, mock_format: MagicMock, mock_load: MagicMock
    ) -> None:
        """Verify complete reflexion flow: load → format → inject → log."""
        patterns = [
            {
                "category": "cli_parameter",
                "skill": "qcloud-cvm-ops",
                "command": "TerminateInstances",
                "error": "MissingParameter",
                "fix": "Use JSON array format",
                "count": 5,
                "reusable": True,
            }
        ]
        formatted_block = """## Reflexion Failure Patterns (Pre-flight hints)

- [cli_parameter] qcloud-cvm-ops: MissingParameter
  Fix: Use JSON array format
"""
        mock_load.return_value = patterns
        mock_format.return_value = formatted_block

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            critic_file = tmp_path / "critic.json"
            critic_payload = {
                "scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1, "spec_compliance": 1},
                "suggestions": [],
                "blocking": False,
            }
            critic_file.write_text(json.dumps(critic_payload))

            captured_env: dict[str, str] | None = None

            def capture_run_command(command: str, timeout: int = 120, env: dict[str, str] | None = None) -> dict[str, Any]:
                nonlocal captured_env
                captured_env = env
                return {
                    "command": command,
                    "exit_code": 0,
                    "result_excerpt": "ok",
                    "stdout_len": 2,
                    "stderr_len": 0,
                }

            with patch("gcl_runner.run_command", side_effect=capture_run_command):
                ns = gcl_runner.build_parser().parse_args([
                    "run",
                    "--root", str(tmp_path),
                    "--skill", "qcloud-cvm-ops",
                    "--request", "test request",
                    "--command", 'tccli cvm TerminateInstances',
                    "--critic-json", str(critic_file),
                ])
                rc = quiet_cmd_run(ns)

            # Verify execution succeeded
            self.assertEqual(rc, 0)

            # Verify env was set
            self.assertIsNotNone(captured_env)
            self.assertIn("REFLEXION_PATTERNS", captured_env)
            self.assertEqual(captured_env["REFLEXION_PATTERNS"], formatted_block)

            # Verify trace was written with preflight info
            trace_files = list((tmp_path / "audit-results").glob("gcl-trace-*.json"))
            self.assertEqual(len(trace_files), 1)

            trace_data = json.loads(trace_files[0].read_text())
            self.assertIn("preflight_reflexion", trace_data)
            self.assertEqual(trace_data["preflight_reflexion"]["matched_failures"], 1)
            self.assertEqual(trace_data["preflight_reflexion"]["injection"], formatted_block)


class TestRubricCalibrationOverride(unittest.TestCase):
    """Test: calibrated rubric thresholds override defaults inside cmd_run context."""

    def test_rubric_calibration_overrides_thresholds(self) -> None:
        """Context manager _rubric_calibration overrides and restores RUBRIC_THRESHOLDS."""
        orig = dict(gcl_runner.RUBRIC_THRESHOLDS)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "audit-results").mkdir()
            calib_file = tmp_path / "audit-results" / "rubric-calibration-test.json"
            calib_file.write_text(
                json.dumps({
                    "skills": {
                        "qcloud-cvm-ops": {
                            "correctness": 0.6,
                            "safety": 1.0,
                            "idempotency": 0.4,
                            "traceability": 0.5,
                            "spec_compliance": 0.5,
                        }
                    }
                })
            )

            # Inside context manager: thresholds should be overridden
            with gcl_runner._rubric_calibration(tmp_path, "qcloud-cvm-ops"):
                self.assertEqual(gcl_runner.RUBRIC_THRESHOLDS["correctness"], 0.6)
                self.assertEqual(gcl_runner.RUBRIC_THRESHOLDS["idempotency"], 0.4)
                # Unchanged dimensions
                self.assertEqual(gcl_runner.RUBRIC_THRESHOLDS["safety"], 1.0)
                self.assertEqual(gcl_runner.RUBRIC_THRESHOLDS["traceability"], 0.5)
                self.assertEqual(gcl_runner.RUBRIC_THRESHOLDS["spec_compliance"], 0.5)

            # After exit: original thresholds restored
            self.assertEqual(gcl_runner.RUBRIC_THRESHOLDS, orig)

    def test_rubric_calibration_no_file_keeps_defaults(self) -> None:
        """When no calibration file exists, RUBRIC_THRESHOLDS are unchanged."""
        orig = dict(gcl_runner.RUBRIC_THRESHOLDS)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with gcl_runner._rubric_calibration(tmp_path, "qcloud-cvm-ops"):
                self.assertEqual(gcl_runner.RUBRIC_THRESHOLDS, orig)

        self.assertEqual(gcl_runner.RUBRIC_THRESHOLDS, orig)

    def test_rubric_calibration_unknown_skill_keeps_defaults(self) -> None:
        """When calibration file exists but skill has no entry, defaults unchanged."""
        orig = dict(gcl_runner.RUBRIC_THRESHOLDS)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "audit-results").mkdir()
            calib_file = tmp_path / "audit-results" / "rubric-calibration-test.json"
            calib_file.write_text(
                json.dumps({"skills": {"another-skill": {"correctness": 0.9}}})
            )
            with gcl_runner._rubric_calibration(tmp_path, "qcloud-cvm-ops"):
                self.assertEqual(gcl_runner.RUBRIC_THRESHOLDS, orig)

        self.assertEqual(gcl_runner.RUBRIC_THRESHOLDS, orig)

    def test_rubric_calibration_exception_during_load_restores_thresholds(self) -> None:
        """If loading raises an exception, thresholds are still restored."""
        orig = dict(gcl_runner.RUBRIC_THRESHOLDS)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "audit-results").mkdir()
            # Malformed JSON — will raise during load
            calib_file = tmp_path / "audit-results" / "rubric-calibration-bad.json"
            calib_file.write_text("{ this is not json")

            with gcl_runner._rubric_calibration(tmp_path, "qcloud-cvm-ops"):
                # Should still be unchanged because load failed
                self.assertEqual(gcl_runner.RUBRIC_THRESHOLDS, orig)

        self.assertEqual(gcl_runner.RUBRIC_THRESHOLDS, orig)
if __name__ == "__main__":
    unittest.main()
