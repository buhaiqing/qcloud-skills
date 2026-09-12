#!/usr/bin/env python3
"""Unit tests for routing_eval.py — blueprint KPI gate."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "routing_eval.py"


class TestRoutingEval(unittest.TestCase):
    def test_exit_code_pass(self):
        r = subprocess.run(
            ["python3", str(SCRIPT)],
            capture_output=True, text=True, cwd=str(ROOT), check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_output_contains_kpi_header(self):
        r = subprocess.run(
            ["python3", str(SCRIPT)],
            capture_output=True, text=True, cwd=str(ROOT), check=False,
        )
        self.assertIn("Blueprint routing KPI", r.stdout)

    def test_output_contains_results(self):
        r = subprocess.run(
            ["python3", str(SCRIPT)],
            capture_output=True, text=True, cwd=str(ROOT), check=False,
        )
        for line in ["routing-01", "routing-02", "routing-03"]:
            self.assertIn(line, r.stdout, f"{line} missing from output")

    def test_all_pass(self):
        r = subprocess.run(
            ["python3", str(SCRIPT)],
            capture_output=True, text=True, cwd=str(ROOT), check=False,
        )
        self.assertIn("5/5 passed", r.stdout, r.stdout)
        self.assertIn("KPI PASS", r.stdout, r.stdout)

    def test_routing_eval_is_importable(self):
        """Verify routing_eval.py has no syntax/import errors."""
        r = subprocess.run(
            ["python3", "-c", "from routing_eval import main; print('ok')"],
            capture_output=True, text=True, cwd=str(SCRIPT.parent), check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
