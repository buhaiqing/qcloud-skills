#!/usr/bin/env python3
"""Unit tests for evidence_kernel hardening helpers.

cwd-independent: invoked via
  cd scripts && python3 -m unittest gcl_hardening_test -v
"""
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"


class GclHardeningTest(unittest.TestCase):
    def test_mask_trace_strips_secrets(self):
        code = (
            "import sys; sys.path.insert(0, 'scripts'); "
            "from evidence_kernel import mask_trace; "
            "t = mask_trace({'cmd': 'tccli foo --secretId AKIDxxxx'}); "
            "assert 'AKIDxxxx' not in str(t), t; "
            "print('ok')"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ok", proc.stdout)

    def test_timeout_raises(self):
        code = (
            "import time, sys; sys.path.insert(0, 'scripts'); "
            "from evidence_kernel import with_timeout; "
            "raised = False\n"
            "try:\n"
            "    with_timeout(lambda: time.sleep(5), 0.2)\n"
            "except TimeoutError:\n"
            "    raised = True\n"
            "print('ok' if raised else 'NO RAISE')"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("ok", proc.stdout)


if __name__ == "__main__":
    unittest.main()
