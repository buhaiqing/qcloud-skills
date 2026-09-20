#!/usr/bin/env python3
"""Unit tests for scripts/check_gate_wiring.py.

Each test builds a throwaway repo in a tempdir and drives the CLI as a subprocess from an
unrelated cwd, so the assertions cover the real exit codes and output CI consumes. Every
rule is proven on both sides: it fires on the drift and stays silent once the seam agrees.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_CHECKER = Path(__file__).resolve().parent / "check_gate_wiring.py"

STORE_OWNER = '#!/usr/bin/env python3\nROOT = Path(__file__).resolve().parent.parent\n'
STORE_OWNER += 'HOT_PATH = ROOT / "docs" / "failure-patterns.md"\n'


class FixtureRepo:
    """Minimal but complete repo: one wired gate, one exempt tool, one live threshold."""

    def __init__(self, root: Path) -> None:
        self.root = root
        (root / "scripts").mkdir(parents=True)
        (root / "assets" / "shared").mkdir(parents=True)
        self.add_script("_failure_pattern_store.py", STORE_OWNER)
        self.add_script("base_gate.py", '"""Base gate (CI gate)."""\n')
        self.add_script("base_tool.py", '"""Human-invoked tool."""\n')
        self.add_script("consumer.py", "FLOOR = 1  # test_floor\n")
        (root / "Makefile").write_text("validate:\n\tpython3 scripts/base_gate.py\n", "utf-8")
        self.set_manifest(
            gates={"base_gate": "python3 scripts/base_gate.py"},
            tools={"base_tool": "python3 scripts/base_tool.py"},
        )
        self.set_thresholds({"test_floor": 1})

    # -- helpers ---------------------------------------------------------------
    def add_script(self, name: str, body: str) -> Path:
        path = self.root / "scripts" / name
        path.write_text(body, encoding="utf-8")
        return path

    def add_makefile_line(self, line: str) -> None:
        makefile = self.root / "Makefile"
        makefile.write_text(makefile.read_text(encoding="utf-8") + line + "\n", encoding="utf-8")

    def set_manifest(self, gates: dict[str, str], tools: dict[str, str]) -> None:
        lines = ["gates:"]
        lines += [f'  {key}: "{value}"' for key, value in gates.items()]
        lines.append("tools:")
        lines += [f'  {key}: "{value}"' for key, value in tools.items()]
        (self.root / "assets" / "shared" / "validation_commands.yaml").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

    def set_thresholds(self, payload: dict[str, object]) -> None:
        (self.root / "assets" / "shared" / "thresholds.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )


class CheckerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = FixtureRepo(Path(self._tmp.name) / "repo")
        # Deliberately unrelated cwd: the CLI must resolve everything from --root.
        self.cwd = Path(self._tmp.name)

    def run_checker(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(_CHECKER), "--root", str(self.repo.root), *extra],
            cwd=self.cwd,
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_clean(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for code in ("W1", "W2", "W3"):
            self.assertNotIn(code, result.stdout, result.stdout)


class BaselineTests(CheckerTestCase):
    def test_complete_fixture_is_clean(self) -> None:
        self.assert_clean(self.run_checker())

    def test_json_report_lists_surfaces_and_codes(self) -> None:
        self.repo.add_script("dead.py", '"""Dead (CI gate)."""\n')
        result = self.run_checker("--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("Makefile", report["surfaces"])
        self.assertEqual(report["finding_count"], 1)
        self.assertEqual(report["findings"][0]["code"], "W1")
        self.assertEqual(report["findings"][0]["detail"], "scripts/dead.py")


class W1DeadGateTests(CheckerTestCase):
    def test_w1_fires_when_self_declared_gate_is_unwired(self) -> None:
        self.repo.add_script("orphan_gate.py", '"""Orphan detector (CI gate)."""\n')
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("W1 scripts/orphan_gate.py", result.stdout)

    def test_w1_silent_when_surface_calls_the_script(self) -> None:
        self.repo.add_script("orphan_gate.py", '"""Orphan detector (CI gate)."""\n')
        self.repo.add_makefile_line("\tpython3 scripts/orphan_gate.py")
        self.assert_clean(self.run_checker())

    def test_w1_silent_when_wired_script_imports_it_bare(self) -> None:
        self.repo.add_script("library_gate.py", '"""Shared checks (CI gate)."""\nthing = 1\n')
        self.repo.add_script("entry_gate.py", "from library_gate import thing\n")
        self.repo.add_makefile_line("\tpython3 scripts/entry_gate.py")
        self.assert_clean(self.run_checker())

    def test_w1_fires_when_only_unwired_script_imports_it(self) -> None:
        # The closure must not launder a gate through an importer nobody calls.
        self.repo.add_script("library_gate.py", '"""Shared checks (CI gate)."""\nthing = 1\n')
        self.repo.add_script("loner.py", "from library_gate import thing\n")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("W1 scripts/library_gate.py", result.stdout)

    def test_w1_marker_window_is_the_first_sixty_lines(self) -> None:
        self.repo.add_script("late_gate.py", "# pad\n" * 59 + "# CI gate\n")
        self.assertEqual(self.run_checker().returncode, 1)
        self.repo.add_script("late_gate.py", "# pad\n" * 60 + "# CI gate\n")
        self.assert_clean(self.run_checker())

    def test_w1_ignores_test_named_modules(self) -> None:
        self.repo.add_script("orphan_gate_test.py", '"""Test helper (CI gate)."""\n')
        self.assert_clean(self.run_checker())

    def test_w1_is_case_insensitive(self) -> None:
        self.repo.add_script("orphan_gate.py", '"""Orphan detector (ci Gate)."""\n')
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("W1 scripts/orphan_gate.py", result.stdout)


class W2ManifestTests(CheckerTestCase):
    def test_w2_fires_for_existing_but_unwired_gate(self) -> None:
        self.repo.add_script("loose_gate.py", '"""Unwired detector."""\n')
        self.repo.set_manifest(
            gates={"loose": "python3 scripts/loose_gate.py"},
            tools={"base_tool": "python3 scripts/base_tool.py"},
        )
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("W2 loose: unwired gate scripts/loose_gate.py", result.stdout)

    def test_w2_fires_for_missing_script(self) -> None:
        self.repo.set_manifest(
            gates={"ghost": "python3 scripts/ghost_gate.py"},
            tools={"base_tool": "python3 scripts/base_tool.py"},
        )
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("W2 ghost: command references missing scripts/ghost_gate.py", result.stdout)

    def test_w2_silent_when_gate_is_wired(self) -> None:
        self.repo.add_script("loose_gate.py", '"""Wired detector."""\n')
        self.repo.set_manifest(
            gates={"loose": "python3 scripts/loose_gate.py"},
            tools={"base_tool": "python3 scripts/base_tool.py"},
        )
        self.repo.add_makefile_line("\tpython3 scripts/loose_gate.py")
        self.assert_clean(self.run_checker())

    def test_w2_exempts_tools_section(self) -> None:
        self.repo.add_script("manual_only.py", '"""Human-invoked."""\n')
        self.repo.set_manifest(
            gates={"base_gate": "python3 scripts/base_gate.py"},
            tools={"manual": "python3 scripts/manual_only.py"},
        )
        self.assert_clean(self.run_checker())

    def test_missing_gates_section_is_config_error(self) -> None:
        manifest = self.repo.root / "assets" / "shared" / "validation_commands.yaml"
        manifest.write_text('tools:\n  base_tool: "python3 scripts/base_tool.py"\n', "utf-8")
        result = self.run_checker()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("gates", result.stderr)

    def test_missing_tools_section_is_config_error(self) -> None:
        manifest = self.repo.root / "assets" / "shared" / "validation_commands.yaml"
        manifest.write_text('gates:\n  base_gate: "python3 scripts/base_gate.py"\n', "utf-8")
        result = self.run_checker()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("tools", result.stderr)


class W3ThresholdTests(CheckerTestCase):
    def test_w3a_fires_for_key_without_production_consumer(self) -> None:
        self.repo.set_thresholds({"test_floor": 1, "dead_key": 5})
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("W3 threshold:dead_key", result.stdout)
        self.assertNotIn("W3 threshold:test_floor", result.stdout)

    def test_w3a_silent_when_every_key_has_a_consumer(self) -> None:
        self.repo.set_thresholds({"test_floor": 1, "second_key": 2})
        self.repo.add_script("reader.py", "LIMIT = 2  # second_key\n")
        self.assert_clean(self.run_checker())

    def test_w3a_counts_makefile_and_workflow_as_consumers(self) -> None:
        self.repo.set_thresholds({"make_key": 1, "wf_key": 2})
        self.repo.add_makefile_line("\t# make_key")
        workflow = self.repo.root / ".github" / "workflows"
        workflow.mkdir(parents=True)
        (workflow / "ci.yml").write_text("run: echo wf_key\n", encoding="utf-8")
        self.assert_clean(self.run_checker())

    def test_w3a_ignores_test_files_as_consumers(self) -> None:
        self.repo.set_thresholds({"only_in_test": 1})
        self.repo.add_script("checker_test.py", "ONLY = 1  # only_in_test\n")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("W3 threshold:only_in_test", result.stdout)


class W3StorePathTests(CheckerTestCase):
    def test_w3b_fires_when_a_second_module_declares_the_store_path(self) -> None:
        self.repo.add_script("other_store.py", 'P = ROOT / "docs" / "failure-patterns.md"\n')
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("W3 store-path:other_store", result.stdout)

    def test_w3b_fires_once_listing_every_offender(self) -> None:
        self.repo.add_script("other_store.py", 'P = ROOT / "docs" / "failure-patterns.md"\n')
        self.repo.add_script("third_store.py", 'Q = _ROOT / "docs" / "failure-patterns.md"\n')
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("W3 store-path:other_store, third_store", result.stdout)

    def test_w3b_silent_when_only_the_owner_declares_it(self) -> None:
        self.assert_clean(self.run_checker())

    def test_w3b_ignores_parameterised_lowercase_root(self) -> None:
        self.repo.add_script(
            "param_store.py",
            "def load(root):\n"
            '    """Caller supplies the root; not a declaration."""\n'
            '    return root / "docs" / "failure-patterns.md"\n',
        )
        self.assert_clean(self.run_checker())


if __name__ == "__main__":
    unittest.main()
