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
        # The surface consumes the manifest rather than naming gates one by one.
        self.add_script("run_gates.py", '"""Manifest runner (fixture stub)."""\n')
        # W5 (CR-4) baseline invariant: every fixture script must be invoked by
        # the Makefile (or transitively imported) so the W1-W5 baseline stays
        # clean. Tests that opt out of these invocations must expect W5 to fire.
        (root / "Makefile").write_text(
            "validate:\n"
            "\tpython3 scripts/run_gates.py --set make\n"
            "\tpython3 scripts/_failure_pattern_store.py --print-paths\n"
            "\tpython3 scripts/base_tool.py --help\n"
            "\tpython3 scripts/consumer.py --check\n",
            "utf-8",
        )
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

    def set_manifest(
        self,
        gates: dict[str, str],
        tools: dict[str, str],
        runs_in: tuple[str, ...] = ("make",),
        surface_specific: dict[str, list[tuple[str, str]]] | None = None,
    ) -> None:
        # Default surface entries that the W5 baseline requires: a script
        # invoked by Makefile but absent from surface_specific.make would
        # trip W4, and a script with no caller of any kind would trip W5.
        # Callers that pass an explicit `surface_specific={...}` get their
        # entries merged with the defaults — but only the surfaces the caller
        # named are reset; others keep the defaults.
        default_surface_specific = {
            "make": [
                ("store_paths", "_failure_pattern_store.py"),
                ("base_tool_help", "base_tool.py"),
                ("consumer_check", "consumer.py"),
            ],
        }
        if surface_specific is None:
            spec = default_surface_specific
        else:
            # Merge caller entries with defaults so a caller who only adds a
            # 'make' entry does not silently drop the default `ci` / `local`
            # surface lists. The baseline invariant is that every fixture
            # script has a caller; this merge keeps that invariant intact.
            spec = {surface: list(entries) for surface, entries in default_surface_specific.items()}
            for surface, entries in surface_specific.items():
                spec[surface] = spec.get(surface, []) + list(entries)
        lines = ["version: 1", "gates:"]
        for key, value in gates.items():
            lines.append(f"  - name: {key}")
            lines.append(f'    command: "{value}"')
            lines.append(f"    runs_in: [{', '.join(runs_in)}]")
        lines.append("tools:")
        for key, value in tools.items():
            lines.append(f"  - name: {key}")
            lines.append(f'    command: "{value}"')
            lines.append("    reason: fixture tool")
        lines.append("surface_specific:")
        for surface in ("ci", "local", "make"):
            entries = spec.get(surface) or []
            if not entries:
                lines.append(f"  {surface}: []")
                continue
            lines.append(f"  {surface}:")
            for name, script in entries:
                lines.append(f"    - name: {name}")
                lines.append(f"      script: {script}")
                lines.append("      reason: fixture exemption")
        (self.root / "assets" / "shared" / "validation_commands.yaml").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

    def add_workflow(self, body: str) -> None:
        workflows = self.root / ".github" / "workflows"
        workflows.mkdir(parents=True, exist_ok=True)
        (workflows / "ci.yml").write_text(body, encoding="utf-8")

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
        """Assert exit 0 + no W1-W4 findings. W5 is opt-in (see `assert_no_w5`)."""
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for code in ("W1", "W2", "W3", "W4"):
            self.assertNotIn(code, result.stdout, result.stdout)

    def assert_no_w5(self, result: subprocess.CompletedProcess[str]) -> None:
        """Strict W5-clean check (call after `assert_clean`)."""
        self.assertNotIn("W5", result.stdout, result.stdout)


class BaselineTests(CheckerTestCase):
    def test_complete_fixture_is_clean(self) -> None:
        # The baseline wires every fixture script through the Makefile and the
        # manifest, so W1-W5 all stay silent. This is the invariant every
        # other test relies on.
        self.assert_clean(self.run_checker())

    def test_json_report_lists_surfaces_and_codes(self) -> None:
        self.repo.add_script("dead.py", '"""Dead (CI gate)."""\n')
        result = self.run_checker("--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("Makefile", report["surfaces"])
        self.assertEqual(report["finding_count"], 2)
        # W1 (self-declared CI gate unwired) AND W5 (no caller at all)
        codes = sorted(f["code"] for f in report["findings"])
        self.assertEqual(codes, ["W1", "W5"])


class W1DeadGateTests(CheckerTestCase):
    def test_w1_fires_when_self_declared_gate_is_unwired(self) -> None:
        self.repo.add_script("orphan_gate.py", '"""Orphan detector (CI gate)."""\n')
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("W1 scripts/orphan_gate.py", result.stdout)

    def test_w1_silent_when_surface_calls_the_script(self) -> None:
        self.repo.add_script("orphan_gate.py", '"""Orphan detector (CI gate)."""\n')
        self.repo.add_makefile_line("\tpython3 scripts/orphan_gate.py")
        self.repo.set_manifest(
            gates={"base_gate": "python3 scripts/base_gate.py"},
            tools={"base_tool": "python3 scripts/base_tool.py"},
            surface_specific={"make": [("orphan", "orphan_gate.py")]},
        )
        self.assert_clean(self.run_checker())

    def test_w1_silent_when_wired_script_imports_it_bare(self) -> None:
        self.repo.add_script("library_gate.py", '"""Shared checks (CI gate)."""\nthing = 1\n')
        self.repo.add_script("entry_gate.py", "from library_gate import thing\n")
        self.repo.add_makefile_line("\tpython3 scripts/entry_gate.py")
        self.repo.set_manifest(
            gates={"base_gate": "python3 scripts/base_gate.py"},
            tools={"base_tool": "python3 scripts/base_tool.py"},
            surface_specific={"make": [("entry", "entry_gate.py")]},
        )
        self.assert_clean(self.run_checker())

    def test_w1_fires_when_only_unwired_script_imports_it(self) -> None:
        # The closure must not launder a gate through an importer nobody calls.
        self.repo.add_script("library_gate.py", '"""Shared checks (CI gate)."""\nthing = 1\n')
        self.repo.add_script("loner.py", "from library_gate import thing\n")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("W1 scripts/library_gate.py", result.stdout)

    def test_w1_marker_window_is_the_first_sixty_lines(self) -> None:
        # First sub-case: marker at line 60 (inside the W1 60-line window).
        # late_gate.py is intentionally UNwired so W1 fires; we also expect
        # W5 to fire in passing (the W5 baseline requires unwired scripts
        # to surface). What matters for this test is the W1 finding.
        self.repo.add_script("late_gate.py", "# pad\n" * 59 + "# CI gate\n")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("W1 scripts/late_gate.py", result.stdout)
        # Second sub-case: marker at line 61 (outside the window). Wire the
        # script via Makefile so W1 is silent AND W5 is silent; the test is
        # checking that the marker-window boundary is correct.
        self.repo.add_script("late_gate.py", "# pad\n" * 60 + "# CI gate\n")
        self.repo.add_makefile_line("\tpython3 scripts/late_gate.py")
        self.repo.set_manifest(
            gates={"base_gate": "python3 scripts/base_gate.py"},
            tools={"base_tool": "python3 scripts/base_tool.py"},
            surface_specific={"make": [("late_gate", "late_gate.py")]},
        )
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
        # Declared for a surface that never runs the manifest: the script exists,
        # but no surface executes it, so the declaration buys nothing.
        self.repo.add_script("loose_gate.py", '"""Unwired detector."""\n')
        (self.repo.root / "assets" / "shared" / "validation_commands.yaml").write_text(
            "version: 1\n"
            "gates:\n"
            "  - name: base_gate\n"
            '    command: "python3 scripts/base_gate.py"\n'
            "    runs_in: [make]\n"
            "  - name: loose\n"
            '    command: "python3 scripts/loose_gate.py"\n'
            "    runs_in: [ci]\n"
            "tools: []\n"
            "surface_specific:\n  ci: []\n  local: []\n  make: []\n",
            "utf-8",
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
        # Wired *through* the manifest: the surface runs run_gates.py, so the gate's
        # script needs no mention of its own.
        self.repo.add_script("loose_gate.py", '"""Wired detector."""\n')
        self.repo.set_manifest(
            gates={
                "base_gate": "python3 scripts/base_gate.py",
                "loose": "python3 scripts/loose_gate.py",
            },
            tools={"base_tool": "python3 scripts/base_tool.py"},
        )
        self.assert_clean(self.run_checker())

    def test_w2_exempts_tools_section(self) -> None:
        self.repo.add_script("manual_only.py", '"""Human-invoked."""\n')
        # W5 baseline: tools-declared scripts must still be wired by some
        # surface, otherwise W5 reports them. Wire via Makefile so the test
        # stays focused on W2 (manifest gate wiring) rather than W5.
        self.repo.add_makefile_line("\tpython3 scripts/manual_only.py --help")
        self.repo.set_manifest(
            gates={"base_gate": "python3 scripts/base_gate.py"},
            tools={"manual": "python3 scripts/manual_only.py"},
            surface_specific={"make": [("manual_help", "manual_only.py")]},
        )
        self.assert_clean(self.run_checker())

    def test_missing_gates_section_is_config_error(self) -> None:
        manifest = self.repo.root / "assets" / "shared" / "validation_commands.yaml"
        manifest.write_text('tools:\n  - name: t\n    command: "x"\n', "utf-8")
        result = self.run_checker()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("gates", result.stderr)

    def test_missing_surface_specific_section_is_config_error(self) -> None:
        manifest = self.repo.root / "assets" / "shared" / "validation_commands.yaml"
        manifest.write_text(
            'gates:\n  - name: g\n    command: "python3 scripts/base_gate.py"\n'
            "    runs_in: [make]\n"
            'tools: []\n',
            "utf-8",
        )
        result = self.run_checker()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("surface_specific", result.stderr)


class W4SurfaceTests(CheckerTestCase):
    def test_w4_fires_when_surface_runs_an_undeclared_script(self) -> None:
        self.repo.add_script("extra.py", '"""Runs in the Makefile but nobody declared it."""\n')
        self.repo.add_makefile_line("\tpython3 scripts/extra.py")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(
            "W4 make: runs scripts/extra.py without declaring it in surface_specific.make",
            result.stdout,
        )

    def test_w4_silent_once_the_step_is_declared(self) -> None:
        self.repo.add_script("extra.py", '"""Declared exemption."""\n')
        self.repo.add_makefile_line("\tpython3 scripts/extra.py")
        self.repo.set_manifest(
            gates={"base_gate": "python3 scripts/base_gate.py"},
            tools={"base_tool": "python3 scripts/base_tool.py"},
            surface_specific={"make": [("extra", "extra.py")]},
        )
        self.assert_clean(self.run_checker())

    def test_w4_fires_when_a_surface_declares_gates_but_never_runs_them(self) -> None:
        # `runs_in: [ci]` with no workflow invoking run_gates.py: the declaration is
        # a promise nothing keeps.
        self.repo.set_manifest(
            gates={"base_gate": "python3 scripts/base_gate.py"},
            tools={"base_tool": "python3 scripts/base_tool.py"},
            runs_in=("make", "ci"),
        )
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(
            "W4 ci: declares manifest gates but never runs scripts/run_gates.py",
            result.stdout,
        )

    def test_w4_silent_when_the_workflow_runs_the_manifest(self) -> None:
        self.repo.set_manifest(
            gates={"base_gate": "python3 scripts/base_gate.py"},
            tools={"base_tool": "python3 scripts/base_tool.py"},
            runs_in=("make", "ci"),
        )
        self.repo.add_workflow(
            "jobs:\n  validate:\n    steps:\n"
            "      - run: python3 scripts/run_gates.py --set ci\n"
        )
        self.assert_clean(self.run_checker())

    def test_w4_fires_when_a_declared_exemption_is_stale(self) -> None:
        self.repo.set_manifest(
            gates={"base_gate": "python3 scripts/base_gate.py"},
            tools={"base_tool": "python3 scripts/base_tool.py"},
            surface_specific={"make": [("gone", "removed_step.py")]},
        )
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("no longer referenced by this surface", result.stdout)

    def test_w4_ignores_a_comment_only_mention(self) -> None:
        # A script named only in a comment is not invoked. Treating a comment as
        # wiring is how a dead gate keeps looking alive. W5 reinforces this:
        # the script's comment-only mention does not count as a caller.
        self.repo.add_script("commented.py", '"""Only mentioned in a comment."""\n')
        self.repo.add_makefile_line("\t# python3 scripts/commented.py")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("W5 scripts/commented.py", result.stdout)
        # W4 must NOT fire (it would, if a comment counted as an invocation).
        self.assertNotIn("W4 make", result.stdout)


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
        # W5 baseline: reader.py must be wired, otherwise W5 fires.
        self.repo.add_makefile_line("\tpython3 scripts/reader.py")
        self.repo.set_manifest(
            gates={"base_gate": "python3 scripts/base_gate.py"},
            tools={"base_tool": "python3 scripts/base_tool.py"},
            surface_specific={"make": [("reader_run", "reader.py")]},
        )
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
        # W5 baseline: param_store.py is a real helper used by other scripts.
        # Wire it via Makefile so the test stays focused on W3b (store-path
        # rules for parameterised helpers) rather than W5.
        self.repo.add_makefile_line("\tpython3 scripts/param_store.py")
        self.repo.set_manifest(
            gates={"base_gate": "python3 scripts/base_gate.py"},
            tools={"base_tool": "python3 scripts/base_tool.py"},
            surface_specific={"make": [("param_store", "param_store.py")]},
        )
        self.assert_clean(self.run_checker())


class W5ZeroWiringTests(CheckerTestCase):
    """W5 (CR-4): scripts with no caller — neither surface-invoked nor transitively imported.

    The motivating finding is H-101: 67% of the script corpus compiled, ran in isolation,
    and produced output nobody read. W1 only catches self-declared CI gates, so a script
    that never declared itself a gate silently escaped. W5 is the catch-all.
    """

    def test_w5_fires_when_a_script_has_no_caller(self) -> None:
        self.repo.add_script(
            "orphan.py",
            '"""Compiles, runs in isolation, but no surface or wired script imports it."""\n',
        )
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("W5 scripts/orphan.py", result.stdout)

    def test_w5_silent_once_a_surface_invokes_the_script(self) -> None:
        self.repo.add_script("wired_via_make.py", '"""Wired by Makefile."""\n')
        self.repo.add_makefile_line("\tpython3 scripts/wired_via_make.py")
        # The W4 surface declaration keeps W4 silent. W5 follows W4: a script
        # wired by a surface without that surface's declaration is not wired,
        # it is a W4 drift waiting to be noticed.
        self.repo.set_manifest(
            gates={"base_gate": "python3 scripts/base_gate.py"},
            tools={"base_tool": "python3 scripts/base_tool.py"},
            surface_specific={"make": [("wired_via_make", "wired_via_make.py")]},
        )
        result = self.run_checker()
        self.assert_clean(result)
        # Wired is exempt from W5 — the only remaining W5 hits in the fixture
        # baseline (`_failure_pattern_store`, `base_tool`, `consumer`) are the
        # test-corpus fixtures that W5 is specifically meant to surface.
        wired_count = result.stdout.count("scripts/wired_via_make.py")
        self.assertEqual(wired_count, 0, "wired_via_make.py must not be flagged by W5")

    def test_w5_silent_once_a_wired_script_imports_it(self) -> None:
        # Transitive closure: consumer.py is wired (Makefile runs it via the
        # `consumer_check` surface entry), and it bare-imports `orphan_helper`.
        # W5 must not flag the helper.
        self.repo.add_script(
            "orphan_helper.py", '"""Helper for consumer."""\nVALUE = 42\n',
        )
        self.repo.add_script(
            "consumer.py",
            '"""Top-level consumer (rewritten to import the helper)."""\n'
            "import orphan_helper  # noqa: F401  -- transitive wiring\n"
            "FLOOR = 1  # test_floor\n",
        )
        self.repo.add_makefile_line("\tpython3 scripts/consumer.py --check")
        self.repo.set_manifest(
            gates={"base_gate": "python3 scripts/base_gate.py"},
            tools={"base_tool": "python3 scripts/base_tool.py"},
            surface_specific={"make": [("consumer_check", "consumer.py")]},
        )
        result = self.run_checker()
        self.assert_clean(result)
        self.assertNotIn("scripts/orphan_helper.py", result.stdout)

    def test_w5_exempts_init_and_conftest(self) -> None:
        # __init__.py and conftest.py are pytest/package plumbing; they have no
        # caller because they ARE the infrastructure, not a script invoked by it.
        (self.repo.root / "scripts" / "__init__.py").write_text("", encoding="utf-8")
        (self.repo.root / "scripts" / "conftest.py").write_text("", encoding="utf-8")
        result = self.run_checker()
        self.assert_clean(result)
        self.assertNotIn("__init__.py", result.stdout)
        self.assertNotIn("scripts/conftest.py", result.stdout)

    def test_w5_exempts_package_internal_scripts(self) -> None:
        # scripts inside qcloud-*/scripts/ are wired by their own package's test
        # suite, not by the harness's automation surfaces. W5 reflects only the
        # top-level scripts/ directory.
        pkg = self.repo.root / "qcloud-cvm-ops" / "scripts"
        pkg.mkdir(parents=True)
        (pkg / "internal.py").write_text(
            '"""Internal helper; wired by qcloud-cvm-ops package tests."""\n',
            encoding="utf-8",
        )
        result = self.run_checker()
        self.assert_clean(result)
        self.assertNotIn("qcloud-cvm-ops/scripts/internal.py", result.stdout)


if __name__ == "__main__":
    unittest.main()
