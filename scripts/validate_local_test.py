#!/usr/bin/env python3
"""Unit tests for scripts/validate_local.py."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import validate_local  # noqa: E402


class BuildStepsTests(unittest.TestCase):
    def test_commands_match_ci_order(self) -> None:
        steps = validate_local.build_steps(python="python3")
        self.assertEqual(
            [step.name for step in steps],
            [
                "Ruff Python lint",
                "Validate SKILL.md frontmatter",
                "Validate Well-Architected worker JSON examples",
                "Validate Markdown local links",
                "Lint Python in Markdown",
                "GCL runner smoke test",
                "GCL trace aggregate",
                "Script unit tests",
                "GCL alarm wire plan",
                "GCL Tier-A conformance",
            ],
        )
        self.assertEqual(steps[0].argv, ("ruff", "check", "."))
        self.assertEqual(steps[5].argv[-1], "--structural-critic-only")
        self.assertEqual(
            steps[7].argv,
            ("python3", "-m", "unittest", "discover", "-s", "scripts", "-p", "*_test.py", "-v"),
        )
        self.assertEqual(
            steps[8].argv,
            (
                "python3",
                "scripts/gcl_alarm_wire.py",
                "plan",
                "--summary",
                "scripts/fixtures/gcl-quality-summary-healthy.json",
            ),
        )

    def test_github_output_adds_ruff_output_format(self) -> None:
        steps = validate_local.build_steps(python="python3", github_output=True)
        self.assertEqual(steps[0].argv, ("ruff", "check", "--output-format=github", "."))


class MainTests(unittest.TestCase):
    def test_list_prints_commands_without_running(self) -> None:
        with patch.object(validate_local.subprocess, "run") as run:
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(validate_local.main(["--list"]), 0)
        run.assert_not_called()
        self.assertIn("Ruff Python lint: ruff check .", stdout.getvalue())

    def test_stops_on_first_failure(self) -> None:
        completed = Mock(returncode=7)
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(validate_local.subprocess, "run", return_value=completed) as run:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(validate_local.main(["--root", tmp]), 7)
        self.assertEqual(run.call_count, 1)

    def test_runs_all_steps_when_successful(self) -> None:
        completed = Mock(returncode=0, stdout='{"by_skill":{}}', stderr="")
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(validate_local.subprocess, "run", return_value=completed) as run:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(validate_local.main(["--root", tmp]), 0)
        self.assertEqual(run.call_count, len(validate_local.build_steps()))


if __name__ == "__main__":
    unittest.main()
