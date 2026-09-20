#!/usr/bin/env python3
"""Unit tests for scripts/run_gates.py — the manifest runner every surface consumes.

Each test builds a throwaway root with its own manifest and stub gates, then drives
the CLI as a subprocess from an unrelated cwd. Both sides are covered: a gate that
must run does run (and in manifest order), a failing gate stops the run and is
named, and an unusable manifest exits 2 rather than reporting a pass.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RUNNER = Path(__file__).resolve().parent / "run_gates.py"


class RunnerFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        (root / "scripts").mkdir(parents=True)
        (root / "assets" / "shared").mkdir(parents=True)
        self.log = root / "ran.log"

    def add_gate(self, name: str, exit_code: int = 0) -> None:
        script = self.root / "scripts" / f"{name}.py"
        script.write_text(
            "import pathlib, sys\n"
            f"pathlib.Path({str(self.log)!r}).open('a').write('{name}\\n')\n"
            f"sys.exit({exit_code})\n",
            encoding="utf-8",
        )

    def set_manifest(self, entries: list[tuple[str, str, list[str]]]) -> None:
        lines = ["version: 1", "gates:"]
        for name, command, runs_in in entries:
            lines.append(f"  - name: {name}")
            lines.append(f'    command: "{command}"')
            lines.append(f"    runs_in: [{', '.join(runs_in)}]")
        lines.append("tools: []")
        lines.append("surface_specific:\n  ci: []\n  local: []\n  make: []")
        (self.root / "assets" / "shared" / "validation_commands.yaml").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

    def ran(self) -> list[str]:
        if not self.log.is_file():
            return []
        return [line for line in self.log.read_text(encoding="utf-8").splitlines() if line]


class RunnerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.repo = RunnerFixture(base / "repo")
        self.cwd = base  # unrelated cwd: the runner must resolve everything from --root

    def run_runner(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(RUNNER), "--root", str(self.repo.root), *args],
            cwd=self.cwd,
            capture_output=True,
            text=True,
            check=False,
        )


class SelectionTests(RunnerTestCase):
    def test_runs_only_the_gates_declared_for_the_surface(self) -> None:
        self.repo.add_gate("ci_only")
        self.repo.add_gate("local_only")
        self.repo.add_gate("both")
        self.repo.set_manifest(
            [
                ("ci_only", "python3 scripts/ci_only.py", ["ci"]),
                ("local_only", "python3 scripts/local_only.py", ["local"]),
                ("both", "python3 scripts/both.py", ["ci", "local"]),
            ]
        )
        result = self.run_runner("--set", "ci")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.repo.ran(), ["ci_only", "both"])

    def test_runs_in_manifest_order(self) -> None:
        self.repo.add_gate("first")
        self.repo.add_gate("second")
        self.repo.add_gate("third")
        self.repo.set_manifest(
            [
                ("third", "python3 scripts/third.py", ["make"]),
                ("first", "python3 scripts/first.py", ["make"]),
                ("second", "python3 scripts/second.py", ["make"]),
            ]
        )
        self.assertEqual(self.run_runner("--set", "make").returncode, 0)
        self.assertEqual(self.repo.ran(), ["third", "first", "second"])

    def test_list_prints_without_executing(self) -> None:
        self.repo.add_gate("only")
        self.repo.set_manifest([("only", "python3 scripts/only.py", ["ci"])])
        result = self.run_runner("--set", "ci", "--list")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("only: python3 scripts/only.py", result.stdout)
        self.assertEqual(self.repo.ran(), [], "a --list run must not execute gates")

    def test_surface_with_no_gates_is_a_config_error(self) -> None:
        self.repo.add_gate("only")
        self.repo.set_manifest([("only", "python3 scripts/only.py", ["ci"])])
        result = self.run_runner("--set", "make")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("no gate declares runs_in: [make]", result.stderr)


class FailureTests(RunnerTestCase):
    def test_failing_gate_stops_the_run_and_is_named(self) -> None:
        self.repo.add_gate("passes")
        self.repo.add_gate("breaks", exit_code=3)
        self.repo.add_gate("never")
        self.repo.set_manifest(
            [
                ("passes", "python3 scripts/passes.py", ["ci"]),
                ("breaks", "python3 scripts/breaks.py", ["ci"]),
                ("never", "python3 scripts/never.py", ["ci"]),
            ]
        )
        result = self.run_runner("--set", "ci")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAILED: breaks exited with 3", result.stderr)
        self.assertEqual(self.repo.ran(), ["passes", "breaks"], "must stop at the first failure")

    def test_json_report_carries_status_and_results(self) -> None:
        self.repo.add_gate("only")
        self.repo.set_manifest([("only", "python3 scripts/only.py", ["ci"])])
        result = self.run_runner("--set", "ci", "--json")
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["results"], [{"name": "only", "exit_code": 0}])


class ConfigErrorTests(RunnerTestCase):
    def test_missing_manifest_is_a_config_error(self) -> None:
        result = self.run_runner("--set", "ci")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("MANIFEST ERROR", result.stderr)

    def test_gate_without_runs_in_is_a_config_error(self) -> None:
        self.repo.add_gate("only")
        (self.repo.root / "assets" / "shared" / "validation_commands.yaml").write_text(
            'gates:\n  - name: only\n    command: "python3 scripts/only.py"\n', encoding="utf-8"
        )
        result = self.run_runner("--set", "ci")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("runs_in", result.stderr)

    def test_unknown_surface_is_rejected(self) -> None:
        self.repo.add_gate("only")
        self.repo.set_manifest([("only", "python3 scripts/only.py", ["ci"])])
        result = self.run_runner("--set", "prod")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
