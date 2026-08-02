#!/usr/bin/env python3
"""Unit tests for scripts/skill_quality_score.py.

Pure stdlib. Run with:
    cd scripts && python3 -m unittest test_skill_quality_score -v

L1 lesson: TestCase subclasses are auto-discovered by unittest discover.
L4 lesson: every rejection path needs an explicit test.
L5 lesson: assert populated values, not just key presence.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from skill_quality_score import (
    UPGRADE_THRESHOLD,
    _load_pattern_counts,
    _recurring_pattern_count,
    aggregate_skill_scores,
    build_report,
    compute_components,
    quality_score_from_components,
    read_evidence_records,
    read_traces,
)

# Monotonic counter so duplicate (skill, status) writes don't overwrite.
_COUNTER = {"n": 0}


def _next_seq() -> int:
    _COUNTER["n"] += 1
    return _COUNTER["n"]


def _write_trace(root: Path, skill: str, status: str = "PASS", scores: dict | None = None) -> Path:
    """Write a single gcl-trace-*.json under audit-results/."""
    audit = root / "audit-results"
    audit.mkdir(parents=True, exist_ok=True)
    if scores is None:
        scores = {"correctness": 1.0, "safety": 1.0, "idempotency": 0.8,
                  "traceability": 1.0, "spec_compliance": 1.0}
    body = {
        "skill": skill,
        "iterations": [
            {"iter": 1, "decision": status,
             "critic": {"scores": scores}},
        ],
        "final": {"status": status, "iter": 1},
    }
    p = audit / f"gcl-trace-test-{skill}-{status}-{_next_seq()}.json"
    p.write_text(json.dumps(body), encoding="utf-8")
    return p


def _write_evidence(root: Path, skill: str, source: str = "gcl_runner",
                    leak_checked: bool = True) -> Path:
    """Write an evidence-*.json under audit-results/."""
    audit = root / "audit-results"
    audit.mkdir(parents=True, exist_ok=True)
    body = {
        "skill": skill,
        "run_id": f"test-{skill}-{_next_seq()}",
        "safety": {"destructive": False, "token_bound": False,
                   "leak_checked": leak_checked},
        "provenance": {"source": source, "tool": "tccli"},
    }
    p = audit / f"evidence-test-{skill}-{_next_seq()}.json"
    p.write_text(json.dumps(body), encoding="utf-8")
    return p


def _write_patterns(root: Path, rows: list[tuple[str, int]]) -> Path:
    """Write a docs/failure-patterns.md fixture. rows = [(skill, count), ...]."""
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Failure Patterns — Reflexion Memory\n",
        "| Skill | Command | Error Pattern | Root Cause | Fix | Count | LastSeen | Severity |",
        "|-------|---------|---------------|------------|-----|-------|----------|----------|",
    ]
    for skill, count in rows:
        lines.append(f"| `{skill}` | `cmd` | `pat` | `root` | `fix` | {count} | — | minor |")
    p = docs / "failure-patterns.md"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


class EmptyDataTests(unittest.TestCase):
    """No trace / no evidence → graceful empty result, not a crash (L10)."""

    def test_no_traces_returns_empty(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = build_report(root)
            self.assertEqual(report["by_skill"], {})
            self.assertEqual(report["upgrade_signal"], [])
            self.assertEqual(report["summary"]["total_executions"], 0)

    def test_no_traces_does_not_raise(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # Must not raise even when audit-results/ is missing
            try:
                aggregate_skill_scores(root)
            except (ImportError, OSError, ValueError, KeyError, AttributeError, TypeError) as e:
                self.fail(f"aggregate_skill_scores raised on empty data: {e}")

    def test_read_traces_returns_empty_list_when_dir_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            traces = read_traces(root, since_hours=168)
            self.assertEqual(traces, [])


class PassRateTests(unittest.TestCase):
    """Per-skill pass_rate component correctness (40% weight)."""

    def test_single_skill_all_pass_score_one(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for _ in range(3):
                _write_trace(root, "qcloud-cvm-ops", "PASS")
            # Evidence records present + provenance known → provenance=1.0.
            for _ in range(3):
                _write_evidence(root, "qcloud-cvm-ops", source="gcl_runner")
            report = build_report(root)
            self.assertIn("qcloud-cvm-ops", report["by_skill"])
            entry = report["by_skill"]["qcloud-cvm-ops"]
            self.assertEqual(entry["total"], 3)
            self.assertEqual(entry["pass"], 3)
            self.assertEqual(entry["pass_rate"], 1.0)
            # All components must be 1.0 (greenfield: passes + evidence + no
            # recurring patterns + no degraded dims).
            self.assertAlmostEqual(entry["components"]["gcl_pass_rate"], 1.0)
            self.assertAlmostEqual(entry["components"]["evidence_kernel_provenance"], 1.0)
            self.assertAlmostEqual(entry["components"]["reflexion_failure_recurrence"], 1.0)
            self.assertAlmostEqual(entry["components"]["distribution_drift_severity"], 1.0)
            self.assertAlmostEqual(entry["quality_score"], 1.0, places=4)
            self.assertFalse(entry["upgrade_signal"])

    def test_mixed_pass_and_fail_computes_correctly(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_trace(root, "qcloud-cvm-ops", "PASS")
            _write_trace(root, "qcloud-cvm-ops", "SAFETY_FAIL")
            _write_trace(root, "qcloud-cvm-ops", "PASS")
            _write_trace(root, "qcloud-cvm-ops", "MAX_ITER")
            report = build_report(root)
            entry = report["by_skill"]["qcloud-cvm-ops"]
            self.assertEqual(entry["total"], 4)
            self.assertEqual(entry["pass"], 2)
            self.assertEqual(entry["safety_fail"], 1)
            self.assertAlmostEqual(entry["pass_rate"], 0.5, places=4)
            self.assertAlmostEqual(entry["components"]["gcl_pass_rate"], 0.5)

    def test_multiple_skills_aggregated_separately(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_trace(root, "qcloud-cvm-ops", "PASS")
            _write_trace(root, "qcloud-cvm-ops", "PASS")
            _write_trace(root, "qcloud-cdb-ops", "SAFETY_FAIL")
            report = build_report(root)
            self.assertEqual(len(report["by_skill"]), 2)
            self.assertEqual(report["by_skill"]["qcloud-cvm-ops"]["pass_rate"], 1.0)
            self.assertEqual(report["by_skill"]["qcloud-cdb-ops"]["pass_rate"], 0.0)


class EvidenceProvenanceTests(unittest.TestCase):
    """evidence_kernel post_record presence drives provenance component (20%)."""

    def test_evidence_present_source_known_provenance_is_one(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_trace(root, "qcloud-cvm-ops", "PASS")
            _write_evidence(root, "qcloud-cvm-ops", source="gcl_runner")
            report = build_report(root)
            comp = report["by_skill"]["qcloud-cvm-ops"]["components"]
            self.assertAlmostEqual(comp["evidence_kernel_provenance"], 1.0)

    def test_evidence_missing_provenance_zero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_trace(root, "qcloud-cvm-ops", "PASS")
            # No evidence-*.json file
            report = build_report(root)
            comp = report["by_skill"]["qcloud-cvm-ops"]["components"]
            self.assertEqual(comp["evidence_kernel_provenance"], 0.0)

    def test_evidence_unknown_provenance_source_zero(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_trace(root, "qcloud-cvm-ops", "PASS")
            _write_evidence(root, "qcloud-cvm-ops", source="rogue_actor")
            report = build_report(root)
            comp = report["by_skill"]["qcloud-cvm-ops"]["components"]
            self.assertEqual(comp["evidence_kernel_provenance"], 0.0)

    def test_read_evidence_records_filters_by_skill(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_evidence(root, "qcloud-cvm-ops")
            _write_evidence(root, "qcloud-cdb-ops")
            records = read_evidence_records(root, skill="qcloud-cvm-ops")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["skill"], "qcloud-cvm-ops")


class UpgradeSignalTests(unittest.TestCase):
    """upgrade_signal triggers below quality threshold (default 0.6)."""

    def test_low_pass_rate_triggers_upgrade(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # 1 PASS, 3 SAFETY_FAIL → pass_rate = 0.25 → triggers
            _write_trace(root, "qcloud-bad-ops", "PASS")
            _write_trace(root, "qcloud-bad-ops", "SAFETY_FAIL")
            _write_trace(root, "qcloud-bad-ops", "SAFETY_FAIL")
            _write_trace(root, "qcloud-bad-ops", "SAFETY_FAIL")
            report = build_report(root)
            self.assertIn("qcloud-bad-ops", report["upgrade_signal"])
            entry = report["by_skill"]["qcloud-bad-ops"]
            self.assertTrue(entry["upgrade_signal"])
            self.assertLess(entry["quality_score"], UPGRADE_THRESHOLD)

    def test_high_pass_rate_does_not_trigger(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_trace(root, "qcloud-good-ops", "PASS")
            _write_trace(root, "qcloud-good-ops", "PASS")
            report = build_report(root)
            self.assertNotIn("qcloud-good-ops", report["upgrade_signal"])
            self.assertFalse(report["by_skill"]["qcloud-good-ops"]["upgrade_signal"])


class JsonCliTests(unittest.TestCase):
    """CLI output is valid JSON when --json is set (smoke via direct function)."""

    def test_build_report_is_json_serializable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_trace(root, "qcloud-cvm-ops", "PASS")
            report = build_report(root)
            # Must serialize without raising and round-trip
            text = json.dumps(report, default=str)
            reparsed = json.loads(text)
            self.assertIn("by_skill", reparsed)
            self.assertIn("summary", reparsed)
            self.assertIn("qcloud-cvm-ops", reparsed["by_skill"])

    def test_main_json_flag_emits_valid_json(self):
        """Run the CLI directly and verify stdout is valid JSON."""
        import contextlib
        import io

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_trace(root, "qcloud-cvm-ops", "PASS")
            _write_evidence(root, "qcloud-cvm-ops")
            from skill_quality_score import main

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = main(["--root", str(root), "--json"])
            self.assertEqual(rc, 0, f"main() exited {rc}, expected 0")
            out = buf.getvalue()
            parsed = json.loads(out)  # raises if not valid JSON
            self.assertIn("by_skill", parsed)
            self.assertIn("qcloud-cvm-ops", parsed["by_skill"])


class WeightComponentTests(unittest.TestCase):
    """Weighted sum math + boundary cases."""

    def test_perfect_inputs_yield_quality_one(self):
        components = {
            "gcl_pass_rate": 1.0,
            "evidence_kernel_provenance": 1.0,
            "reflexion_failure_recurrence": 1.0,
            "distribution_drift_severity": 1.0,
        }
        score = quality_score_from_components(components)
        self.assertAlmostEqual(score, 1.0, places=6)

    def test_zero_inputs_yield_quality_zero(self):
        components = {
            "gcl_pass_rate": 0.0,
            "evidence_kernel_provenance": 0.0,
            "reflexion_failure_recurrence": 0.0,
            "distribution_drift_severity": 0.0,
        }
        score = quality_score_from_components(components)
        self.assertAlmostEqual(score, 0.0, places=6)

    def test_weights_sum_to_one(self):
        # Weights are documented as 40/20/20/20; the score must
        # land between 0 and 1 (any convex combination of 0..1).
        components = {
            "gcl_pass_rate": 0.5,
            "evidence_kernel_provenance": 0.7,
            "reflexion_failure_recurrence": 0.9,
            "distribution_drift_severity": 0.3,
        }
        score = quality_score_from_components(components)
        self.assertGreater(score, 0.0)
        self.assertLess(score, 1.0)
        # Verify the exact weighted value: 0.5*0.4 + 0.7*0.2 + 0.9*0.2 + 0.3*0.2
        expected = 0.4 * 0.5 + 0.2 * 0.7 + 0.2 * 0.9 + 0.2 * 0.3
        self.assertAlmostEqual(score, round(expected, 4), places=4)

    def test_compute_components_keys(self):
        """compute_components must always return all 4 named keys."""
        components = compute_components(traces=[], evidence=[], patterns={}, drift={})
        self.assertEqual(
            set(components.keys()),
            {"gcl_pass_rate", "evidence_kernel_provenance",
             "reflexion_failure_recurrence", "distribution_drift_severity"},
        )
        for v in components.values():
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)


class SummaryTests(unittest.TestCase):
    """Top-level summary fields populated correctly."""

    def test_summary_total_executions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for _ in range(5):
                _write_trace(root, "qcloud-cvm-ops", "PASS")
            report = build_report(root)
            self.assertEqual(report["summary"]["total_executions"], 5)

    def test_summary_skill_count(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_trace(root, "qcloud-cvm-ops", "PASS")
            _write_trace(root, "qcloud-cdb-ops", "PASS")
            _write_trace(root, "qcloud-redis-ops", "SAFETY_FAIL")
            report = build_report(root)
            self.assertEqual(report["summary"]["skill_count"], 3)
            self.assertEqual(report["summary"]["upgrade_skill_count"], 1)


class RecurrencePatternTests(unittest.TestCase):
    """_load_pattern_counts caches failure-patterns.md; recurrence impacts score."""

    def test_load_pattern_counts_aggregates_by_skill(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_patterns(root, [("qcloud-cvm-ops", 2), ("qcloud-cvm-ops", 3),
                                   ("qcloud-cdb-ops", 1), ("qcloud-redis-ops", 0)])
            counts = _load_pattern_counts(root)
            self.assertEqual(counts, {"qcloud-cvm-ops": 5, "qcloud-cdb-ops": 1,
                                      "qcloud-redis-ops": 0})

    def test_recurring_pattern_count_matches_load_map(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_patterns(root, [("qcloud-cvm-ops", 2), ("qcloud-cdb-ops", 1)])
            self.assertEqual(_recurring_pattern_count("qcloud-cvm-ops", root), 2)
            self.assertEqual(_recurring_pattern_count("qcloud-cdb-ops", root), 1)
            # Skill with no rows → 0
            self.assertEqual(_recurring_pattern_count("qcloud-unknown-ops", root), 0)

    def test_recurring_pattern_count_missing_file_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.assertEqual(_recurring_pattern_count("qcloud-cvm-ops", root), 0)
            self.assertEqual(_load_pattern_counts(root), {})

    def test_recurrence_drags_score_down_in_aggregate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_trace(root, "qcloud-cvm-ops", "PASS")
            _write_evidence(root, "qcloud-cvm-ops", source="gcl_runner")
            # High recurring count saturates the recurrence component → score < 1
            _write_patterns(root, [("qcloud-cvm-ops", 10)])
            report = build_report(root)
            comp = report["by_skill"]["qcloud-cvm-ops"]["components"]
            self.assertEqual(comp["reflexion_failure_recurrence"], 0.0)
            self.assertLess(report["by_skill"]["qcloud-cvm-ops"]["quality_score"], 1.0)


if __name__ == "__main__":
    unittest.main()