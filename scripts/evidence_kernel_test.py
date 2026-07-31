"""Tests for Evidence Kernel schema validation."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = Path(__file__).resolve().parent / "validate_evidence_schema.py"

VALID = {
    "skill": "qcloud-cvm-ops", "run_id": "r1", "phase": "self-test",
    "intent": "list instances",
    "router_decision": {"top1_skill": "qcloud-cvm-ops", "candidates": ["qcloud-cvm-ops"],
                         "misdelegated": False, "fell_back": False},
    "trace": {}, "golden_ref": "assets/golden/list.json", "fixture_ref": None,
    "safety": {"destructive": False, "token": None, "plan_hash": None, "leak_checked": True},
    "provenance": {"source": "sandbox_e2e", "tool": "tccli", "captured_at": "2026-07-28T00:00:00Z"},
    "budgets": {"context_tokens": 100, "tool_calls": 2, "wall_clock_ms": 500},
    "cost": {"tokens": 100, "usd": None},
    "scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1, "spec_compliance": 1}
}


def _dump(obj):
    p = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(obj, p)
    p.close()
    return p.name


class EvidenceSchemaTests(unittest.TestCase):
    def test_valid_record_passes(self):
        r = subprocess.run([sys.executable, str(VALIDATOR), _dump(VALID)],
                           capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_missing_provenance_fails(self):
        bad = dict(VALID)
        bad.pop("provenance")
        r = subprocess.run([sys.executable, str(VALIDATOR), _dump(bad)],
                           capture_output=True, text=True, check=False)
        self.assertNotEqual(r.returncode, 0)

    def test_kpi2_destructive_requires_token(self):
        bad = dict(VALID)
        bad["safety"] = {"destructive": True, "token": None,
                         "plan_hash": None, "leak_checked": True}
        r = subprocess.run([sys.executable, str(VALIDATOR), _dump(bad)],
                           capture_output=True, text=True, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("KPI#2", r.stdout)

    def test_kpi1_leak_checked_required(self):
        bad = dict(VALID)
        bad["safety"] = {"destructive": False, "token": None,
                         "plan_hash": None, "leak_checked": False}
        r = subprocess.run([sys.executable, str(VALIDATOR), _dump(bad)],
                           capture_output=True, text=True, check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("KPI#1", r.stdout)


if __name__ == "__main__":
    unittest.main()
