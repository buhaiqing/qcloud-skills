#!/usr/bin/env python3
"""Unit tests for the aggregate KPI gate (check_kpi_gates).

L5: every assertion checks a populated value, not key presence.
L6: each gate proves BOTH that it fires and that it stays silent — the
threshold cases run the same fixture with different thresholds in
assets/shared/thresholds.json, so a hardcoded number cannot pass them.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_kpi_gates

# Schema-valid EvidenceRecord with KPI#1 (leak_checked) / KPI#2 clean.
VALID_EVIDENCE = {
    "skill": "qcloud-cvm-ops", "run_id": "r1", "phase": "self-test",
    "intent": "list instances",
    "router_decision": {"top1_skill": "qcloud-cvm-ops", "candidates": ["qcloud-cvm-ops"],
                        "misdelegated": False, "fell_back": False},
    "trace": {}, "golden_ref": "assets/golden/list.json", "fixture_ref": None,
    "safety": {"destructive": False, "token": None, "plan_hash": None, "leak_checked": True},
    "provenance": {"source": "sandbox_e2e", "tool": "tccli",
                   "captured_at": "2026-07-28T00:00:00Z"},
    "budgets": {"context_tokens": 100, "tool_calls": 2, "wall_clock_ms": 500},
    "cost": {"tokens": 100, "usd": None},
    "scores": {"correctness": 1, "safety": 1, "idempotency": 1, "traceability": 1,
               "spec_compliance": 1},
}


@contextlib.contextmanager
def _quiet():
    """L20: print-capable gate functions must not leak stdout into test output."""
    with contextlib.redirect_stdout(io.StringIO()):
        yield


def _write_repo(root: Path, min_top1: float, target_top1: float) -> Path:
    """Fixture: qcloud-a-ops gets its positive query wrong (routes to b),
    qcloud-b-ops gets its own right -> avg top1 = (0.0 + 1.0) / 2 = 0.50,
    avg misdelegation = 0.00, 2/2 skills measured."""
    (root / "assets" / "shared").mkdir(parents=True)
    (root / "assets" / "shared" / "thresholds.json").write_text(
        json.dumps({"router_min_top1_accuracy": min_top1,
                    "router_target_top1_accuracy": target_top1}),
        encoding="utf-8",
    )
    audit = root / "audit-results"
    audit.mkdir()
    (audit / "skill-registry.json").write_text(
        json.dumps({"skills": [
            {"name": "qcloud-a-ops", "intent_keywords": []},
            {"name": "qcloud-b-ops", "intent_keywords": ["RunCvmInstance"]},
        ]}),
        encoding="utf-8",
    )
    for name in ("qcloud-a-ops", "qcloud-b-ops"):
        assets = root / name / "assets"
        assets.mkdir(parents=True)
        (assets / "eval_queries.json").write_text(
            json.dumps([{"query": "run cvm instance", "should_trigger": True}]),
            encoding="utf-8",
        )
    return root


@contextlib.contextmanager
def _router_fixture(min_top1: float, target_top1: float):
    """Point the gate at a throwaway repo root (skill dirs + thresholds)."""
    with tempfile.TemporaryDirectory() as td:
        root = _write_repo(Path(td), min_top1, target_top1)
        with mock.patch.object(check_kpi_gates, "ROOT", root), \
                mock.patch.object(check_kpi_gates, "REGISTRY",
                                  root / "audit-results" / "skill-registry.json"), \
                mock.patch.object(check_kpi_gates, "AUDIT", root / "audit-results"), \
                mock.patch.object(check_kpi_gates, "THRESHOLDS",
                                  root / "assets" / "shared" / "thresholds.json"):
            yield root


def _stub_other_kpis() -> contextlib.ExitStack:
    """main() must be judged on the evidence gate alone; the other KPIs shell out
    to the real repo (registry build, spec-drift detector) and are stubbed."""
    stack = contextlib.ExitStack()
    for name in ("kpi3_golden_coverage", "kpi7_router_confusion"):
        stack.enter_context(mock.patch.object(check_kpi_gates, name,
                                              return_value=("pass", "stub", "")))
    stack.enter_context(mock.patch.object(check_kpi_gates, "kpi8_spec_drift",
                                          return_value=("skip", "stub", "")))
    return stack


class Kpi7RouterThresholdTest(unittest.TestCase):
    def test_fails_below_router_min_top1_accuracy(self) -> None:
        """avg top1 = 50% against a 60% ratchet must FAIL."""
        with _router_fixture(0.60, 0.70) as root, _quiet():
            status, detail, _ = check_kpi_gates.kpi7_router_confusion()
            self.assertEqual(status, "fail")
            self.assertIn("50.00%", detail)
            self.assertIn("below ratchet 60.00%", detail)
            # the artifact is still written for trend tracking, even on failure
            written = json.loads(
                (root / "audit-results" / "router-confusion.json").read_text(encoding="utf-8"))
        self.assertEqual(written["qcloud-a-ops"]["top1_accuracy"], 0.0)
        self.assertEqual(written["qcloud-b-ops"]["top1_accuracy"], 1.0)

    def test_passes_above_ratchet_and_names_the_target_gap(self) -> None:
        """Same 50% against a 10% ratchet passes — but 50% < 70% target, so the
        gap must be printed, not hidden behind a ✅."""
        with _router_fixture(0.10, 0.70), _quiet():
            status, detail, _ = check_kpi_gates.kpi7_router_confusion()
        self.assertEqual(status, "pass")
        self.assertIn("avg top1=50.00%", detail)
        self.assertIn("BELOW TARGET 70.00%", detail)
        self.assertIn(check_kpi_gates.ROUTER_GAP_ANCHOR, detail)

    def test_meeting_the_target_reports_no_gap(self) -> None:
        """L6 (silent side): above target, the detail carries no gap warning."""
        with _router_fixture(0.10, 0.40), _quiet():
            status, detail, _ = check_kpi_gates.kpi7_router_confusion()
        self.assertEqual(status, "pass")
        self.assertIn("avg top1=50.00% avg misdelegation=0.00%", detail)
        self.assertNotIn("BELOW TARGET", detail)


class Kpi1SafetyEvidenceTest(unittest.TestCase):
    """KPI#1/#2 must read the real evidence stream (evidence-local.jsonl)."""

    @contextlib.contextmanager
    def _audit_dir(self, lines: list[str]):
        with tempfile.TemporaryDirectory() as td:
            audit = Path(td) / "audit-results"
            audit.mkdir()
            (audit / "evidence-local.jsonl").write_text(
                "\n".join(lines) + "\n", encoding="utf-8"
            )
            with mock.patch.object(check_kpi_gates, "AUDIT", audit):
                yield audit

    def test_jsonl_stream_is_validated_and_counted(self) -> None:
        lines = [json.dumps(VALID_EVIDENCE) for _ in range(3)]
        with self._audit_dir(lines):
            status, detail, _ = check_kpi_gates.kpi1_2_safety()
        self.assertEqual(status, "pass")
        self.assertEqual(detail, "3 record(s) valid")

    def test_malformed_jsonl_line_fails(self) -> None:
        lines = [json.dumps(VALID_EVIDENCE), '{"skill": "broken", ']
        with self._audit_dir(lines):
            status, detail, _ = check_kpi_gates.kpi1_2_safety()
        self.assertEqual(status, "fail")
        self.assertIn("JSONL line", detail)

    def test_main_skips_when_no_evidence_and_fails_on_bad_jsonl(self) -> None:
        """L6: exit 0 when there is no evidence at all, exit 1 on a broken line."""
        with tempfile.TemporaryDirectory() as td, _stub_other_kpis(), _quiet():
            audit = Path(td) / "audit-results"
            audit.mkdir()
            with mock.patch.object(check_kpi_gates, "AUDIT", audit):
                self.assertEqual(check_kpi_gates.main(), 0)  # silent: no evidence
                (audit / "evidence-local.jsonl").write_text(
                    json.dumps(VALID_EVIDENCE) + "\n", encoding="utf-8")
                self.assertEqual(check_kpi_gates.main(), 0)  # silent: clean stream
                (audit / "evidence-local.jsonl").write_text("{not json}\n", encoding="utf-8")
                self.assertEqual(check_kpi_gates.main(), 1)  # fires


if __name__ == "__main__":
    unittest.main()
