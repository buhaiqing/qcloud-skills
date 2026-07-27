#!/usr/bin/env python3
"""Tests for scripts/aggregate_kpi.py KPI targets."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aggregate_kpi.py"


class AggregateKpiTest(unittest.TestCase):
    def test_kpi_targets_enforced(self) -> None:
        rec = {
            "skill": "s",
            "run_id": "r",
            "phase": "self-test",
            "intent": "i",
            "router_decision": {
                "top1_skill": "s",
                "candidates": ["s"],
                "misdelegated": False,
                "fell_back": False,
            },
            "trace": {},
            "golden_ref": "g",
            "fixture_ref": None,
            "safety": {"destructive": False, "token": None, "plan_hash": None, "leak_checked": True},
            "provenance": {"source": "sandbox_e2e", "tool": "tccli", "captured_at": "2026-07-28T00:00:00Z"},
            "budgets": {"context_tokens": 1, "tool_calls": 1, "wall_clock_ms": 1},
            "cost": {"tokens": 1, "usd": None},
            "scores": {
                "correctness": 1,
                "safety": 1,
                "idempotency": 1,
                "traceability": 1,
                "spec_compliance": 1,
            },
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(rec, f)
            tmp = f.name
        try:
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), tmp],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            out = json.loads(proc.stdout)
            self.assertEqual(out["kpi"]["leak"], 0)
            self.assertEqual(out["kpi"]["provenance"], 1.0)
        finally:
            Path(tmp).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
