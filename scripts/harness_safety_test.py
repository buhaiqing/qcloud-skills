#!/usr/bin/env python3
"""Tests for harness_safety — Phase 3 destructive detection + token binding."""
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = str(Path(__file__).resolve().parents[1])


class HarnessSafetyTest(unittest.TestCase):
    def test_destructive_detected(self) -> None:
        code = (
            "import sys; sys.path.insert(0,'scripts'); "
            "from harness_safety import is_destructive; "
            "assert is_destructive('Delete the CVM instance ins-1'); "
            "assert not is_destructive('List the CVM instances'); "
            "print('ok')"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT, capture_output=True, text=True,
        check=False)
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_token_binding_ok(self) -> None:
        code = (
            "import hashlib, sys; sys.path.insert(0,'scripts'); "
            "from harness_safety import bind_token; "
            "plan='delete ins-1'; h=hashlib.sha256(plan.encode()).hexdigest()[:16]; "
            "tok=bind_token(plan, h); assert tok==h; print('ok')"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT, capture_output=True, text=True,
        check=False)
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_token_mismatch_refuses(self) -> None:
        code = (
            "import sys\n"
            "sys.path.insert(0, 'scripts')\n"
            "from harness_safety import bind_token\n"
            "try:\n"
            "    bind_token('delete ins-1', 'deadbeef')\n"
            "except PermissionError:\n"
            "    print('ok')\n"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT, capture_output=True, text=True,
        check=False)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("ok", res.stdout)

    def test_inflected_verbs_still_destructive(self) -> None:
        # Regression guard for the inflection gap: "deleted" / "removes" must be
        # caught (a bare substring/split match would let them bypass the token gate).
        code = (
            "import sys; sys.path.insert(0,'scripts'); "
            "from harness_safety import is_destructive; "
            "assert is_destructive('the instance will be deleted'); "
            "assert is_destructive('this removes the disk'); "
            "assert is_destructive('stopping the cluster'); "
            "print('ok')"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT, capture_output=True, text=True,
        check=False)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("ok", res.stdout)


if __name__ == "__main__":
    unittest.main()
