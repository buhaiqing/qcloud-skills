#!/usr/bin/env python3
"""Unit tests for scripts/validate_eval_queries.py.

Covers L6 (gate must both fire and stay silent) plus the real-repo state
after the agsx/test-ops normalization (L2: cwd-independent subprocess paths).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "validate_eval_queries.py"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True, text=True, check=False,
    )


class ValidateEvalQueriesRepoTest(unittest.TestCase):
    """Real-repo integration: the two files normalized in this change pass."""

    def test_real_repo_scoped_skills_pass(self):
        r = _run(REPO_ROOT)
        out = r.stdout
        # The two skills normalized in this change must be reported OK.
        self.assertIn("OK   qcloud-agsx-ops", out, out)
        self.assertIn("OK   qcloud-test-ops", out, out)
        # No crash: only exit 0 (all compliant) or 1 (violations found).
        self.assertIn(r.returncode, (0, 1), r.stderr)
        # When the gate fires, it must be on real FAIL lines, never a crash.
        if r.returncode != 0:
            self.assertIn("FAIL ", out, out)


class ValidateEvalQueriesSchemaTest(unittest.TestCase):
    """Synthetic repos: the gate fires on violations and stays silent when clean."""

    def _write(self, root: Path, skill: str, cases: list[dict]) -> Path:
        p = root / skill / "assets"
        p.mkdir(parents=True)
        path = p / "eval_queries.json"
        path.write_text(json.dumps(cases), encoding="utf-8")
        return path

    def test_rejects_legacy_eval_set_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(Path(tmp), "qcloud-bad-ops", [
                {"query": "a", "should_trigger": True, "eval_set": "qcloud-bad-ops-v1.0.0"},
                {"query": "b", "should_trigger": True},
                {"query": "c", "should_trigger": False},
                {"query": "d", "should_trigger": False},
            ])
            r = _run(Path(tmp))
            self.assertNotEqual(r.returncode, 0, r.stdout)
            self.assertIn("eval_set", r.stdout, r.stdout)

    def test_rejects_insufficient_positive_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(Path(tmp), "qcloud-bad-ops", [
                {"query": "a", "should_trigger": True},
                {"query": "b", "should_trigger": False},
                {"query": "c", "should_trigger": False},
            ])
            r = _run(Path(tmp))
            self.assertNotEqual(r.returncode, 0, r.stdout)
            self.assertIn("positive case(s)", r.stdout, r.stdout)

    def test_rejects_duplicate_queries(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(Path(tmp), "qcloud-bad-ops", [
                {"query": "dup", "should_trigger": True},
                {"query": "dup", "should_trigger": False},
                {"query": "c", "should_trigger": True},
                {"query": "d", "should_trigger": False},
            ])
            r = _run(Path(tmp))
            self.assertNotEqual(r.returncode, 0, r.stdout)
            self.assertIn("duplicate query", r.stdout, r.stdout)

    def test_accepts_compliant_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(Path(tmp), "qcloud-good-ops", [
                {"query": "a", "should_trigger": True},
                {"query": "b", "should_trigger": True},
                {"query": "c", "should_trigger": False},
                {"query": "d", "should_trigger": False},
            ])
            r = _run(Path(tmp))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("OK   qcloud-good-ops", r.stdout, r.stdout)


if __name__ == "__main__":
    unittest.main()
