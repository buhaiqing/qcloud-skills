#!/usr/bin/env python3
"""Unit tests for scripts/check_test_collection.py.

Each test builds a throwaway repo in a tempdir and drives the CLI as a
subprocess from an unrelated cwd, so the assertions cover the real exit codes
and output CI consumes.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_CHECKER = Path(__file__).resolve().parent / "check_test_collection.py"

COLLECTIBLE_TEST = '''"""Collectible under pytest's default test_*.py pattern."""
import unittest


class MiniTest(unittest.TestCase):
    def test_passes(self) -> None:
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
'''

ORPHAN_TEST = '''"""Test-shaped body, but the name matches no configured runner pattern."""
import unittest


class OrphanTest(unittest.TestCase):
    def test_passes(self) -> None:
        self.assertTrue(True)
'''


class FixtureRepo:
    """Minimal repo: one collectible test plus the threshold contract."""

    def __init__(self, root: Path) -> None:
        self.root = root
        (root / "scripts").mkdir(parents=True)
        (root / "assets" / "shared").mkdir(parents=True)
        (root / "scripts" / "test_min.py").write_text(COLLECTIBLE_TEST, encoding="utf-8")
        self.set_floor(1)

    def set_floor(self, value: object) -> None:
        payload = json.dumps({"tests_min_collected": value})
        (self.root / "assets" / "shared" / "thresholds.json").write_text(payload, encoding="utf-8")

    def add_orphan(self, name: str) -> Path:
        path = self.root / "scripts" / name
        path.write_text(ORPHAN_TEST, encoding="utf-8")
        return path


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


class CollectionFloorTests(CheckerTestCase):
    def test_clean_when_count_meets_floor(self) -> None:
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("1 collected", result.stdout)
        self.assertIn("OK", result.stdout)

    def test_c1_fires_when_floor_above_collected(self) -> None:
        self.repo.set_floor(50)
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("C1 1 < 50", result.stdout)

    def test_c1_silent_when_floor_is_zero(self) -> None:
        self.repo.set_floor(0)
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("C1", result.stdout)


class OrphanTestFileTests(CheckerTestCase):
    def test_c2_fires_for_test_shaped_file_outside_runner_patterns(self) -> None:
        self.repo.add_orphan("checks_foo.py")
        result = self.run_checker()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("C2 scripts/checks_foo.py", result.stdout)
        self.assertNotIn("C1", result.stdout)  # C1 isolated: the floor is met

    def test_c2_silent_when_every_test_file_is_collected(self) -> None:
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("C2", result.stdout)

    def test_json_report_names_the_orphan(self) -> None:
        self.repo.add_orphan("checks_foo.py")
        result = self.run_checker("--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["collected"], 1)
        self.assertEqual(report["test_files"], 2)
        self.assertEqual([f["code"] for f in report["findings"]], ["C2"])
        self.assertIn("checks_foo.py", report["findings"][0]["detail"])


class ConfigErrorTests(CheckerTestCase):
    def test_missing_threshold_is_config_error(self) -> None:
        (self.repo.root / "assets" / "shared" / "thresholds.json").unlink()
        result = self.run_checker()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("tests_min_collected", result.stderr)

    def test_non_integer_threshold_is_config_error(self) -> None:
        self.repo.set_floor("many")
        result = self.run_checker()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("must be an integer", result.stderr)

    def test_missing_scripts_dir_is_config_error(self) -> None:
        shutil.rmtree(self.repo.root / "scripts")
        result = self.run_checker()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("no scripts directory", result.stderr)


if __name__ == "__main__":
    unittest.main()
