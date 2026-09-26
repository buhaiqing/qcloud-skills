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

try:  # PyYAML is a hard dependency of scripts/check_yaml_python_drift.py (a CI gate)
    import yaml
except ImportError:  # pragma: no cover - keeps this module importable without it
    yaml = None

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import validate_local

# Blocking CI steps whose script cannot run on a dev machine, each with the reason.
# Empty-by-default: an entry here is a deliberate decision to accept surface drift.
CI_ONLY_BLOCKING = {
    # check_kpi_gates fails closed when no evidence stream exists, and the stream
    # (audit-results/evidence-*.jsonl) is gitignored and machine-local. CI grades a
    # committed fixture; a fresh clone has nothing to grade, so wiring it into the
    # local mirror would fail for the wrong reason.
    "check_kpi_gates.py",
}


class BuildStepsTests(unittest.TestCase):
    def test_commands_match_ci_order(self) -> None:
        steps = validate_local.build_steps(python="python3")
        self.assertEqual(
            [step.name for step in steps],
            [
                "Ruff Python lint",
                "Validate SKILL.md version bumps (diff scope)",
                "Manifest gates",
                "GCL runner smoke test",
                "GCL trace aggregate",
                "Script unit tests (pytest — collects both naming conventions)",
            ],
        )
        # Keyed by name, not by index: positional assertions break every time a
        # step is inserted, which is drift-reporting noise rather than a signal.
        by_name = {step.name: step for step in steps}
        self.assertEqual(by_name["Ruff Python lint"].argv, ("ruff", "check", "."))
        self.assertEqual(by_name["GCL runner smoke test"].argv[-1], "--structural-critic-only")
        self.assertEqual(
            by_name["Script unit tests (pytest — collects both naming conventions)"].argv,
            ("python3", "-m", "pytest", "scripts", "-q"),
        )
        # The plain gates come from the manifest, which CI and `make gates` read
        # too; check_gate_wiring.py rule W4 fails the build if a surface stops
        # consuming it or grows an undeclared gate.
        self.assertEqual(
            by_name["Manifest gates"].argv,
            ("python3", "scripts/run_gates.py", "--set", "local"),
        )

    # `test_every_blocking_ci_script_also_runs_locally` used to compare a
    # hand-copied list against the workflow. It is gone on purpose: the manifest
    # (assets/shared/validation_commands.yaml) is now the single list all three
    # surfaces consume, and check_gate_wiring.py rule W4 asserts that seam in both
    # directions — a surface cannot grow an undeclared gate, and a declared
    # exemption cannot outlive its step. Re-asserting it here by hand would be the
    # same duplication this change removed.

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

    def test_critical_quality_signal_warns_but_does_not_fail(self) -> None:
        """The quality signal mirrors CI, which marks that step `continue-on-error`.

        It derives from machine-local audit-results/ traces: on a fresh clone it is
        always "critical" (3 committed traces → 1 skill, 1 upgrade signal, ratio
        1.0), so treating it as blocking made `make validate` exit 1 for every
        developer while CI stayed green.
        """
        completed = Mock(returncode=0, stdout='{"by_skill":{}}', stderr="")
        report = {
            "quality_score": 0.0,
            "upgrade_signal": "critical",
            "recommendations": ["qcloud-cvm-ops: improve pass rate"],
            "_raw_report": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(validate_local.subprocess, "run", return_value=completed):
                with patch.object(validate_local, "run_quality_score", return_value=report):
                    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
                        io.StringIO()
                    ) as stderr:
                        rc = validate_local.main(["--root", tmp])
        self.assertEqual(rc, 0, "a critical quality signal must not fail the suite")
        self.assertIn("informational", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
