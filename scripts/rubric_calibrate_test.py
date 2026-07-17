#!/usr/bin/env python3
"""Unit tests for rubric_calibrate.py."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Import directly so tests run against the live source file
sys.path.insert(0, str(Path(__file__).parent))

from rubric_calibrate import (
    DEFAULT_THRESHOLDS,
    _extract_iteration_scores,
    _load_traces,
    _suggested_with_safety,
    _confidence,
    generate_report,
    print_table,
)


class TestSuggestedWithSafety(unittest.TestCase):
    def test_safety_locked_above_floor(self):
        sug, status = _suggested_with_safety("safety", 1.0, 0.0)
        self.assertEqual(sug, 1.0)
        self.assertEqual(status, "locked")

    def test_safety_floor_enforced(self):
        sug, status = _suggested_with_safety("safety", 0.3, 0.5)
        self.assertEqual(sug, 0.5)
        self.assertEqual(status, "locked")

    def test_non_safety_positive(self):
        sug, status = _suggested_with_safety("correctness", 0.9, 0.1)
        self.assertAlmostEqual(sug, 0.8)
        self.assertEqual(status, "ok")

    def test_non_safety_clamp_zero(self):
        sug, status = _suggested_with_safety("spec_compliance", 0.2, 0.4)
        self.assertEqual(sug, 0.0)
        self.assertEqual(status, "ok")


class TestConfidence(unittest.TestCase):
    def test_low(self):
        self.assertEqual(_confidence(5), "LOW")
        self.assertEqual(_confidence(9), "LOW")

    def test_medium(self):
        self.assertEqual(_confidence(10), "MEDIUM")
        self.assertEqual(_confidence(49), "MEDIUM")

    def test_high(self):
        self.assertEqual(_confidence(50), "HIGH")
        self.assertEqual(_confidence(100), "HIGH")


class TestExtractIterationScores(unittest.TestCase):
    def test_last_iter_only(self):
        traces = [
            {
                "skill": "qcloud-cvm-ops",
                "iterations": [
                    {"critic": {"scores": {"correctness": 1.0}}},
                    {"critic": {"scores": {"correctness": 0.5}}},
                ],
            }
        ]
        result = _extract_iteration_scores(traces, None)
        # Only last iteration
        self.assertEqual(result["qcloud-cvm-ops"]["correctness"], [0.5])

    def test_skill_filter(self):
        traces = [
            {"skill": "qcloud-cvm-ops", "iterations": [{"critic": {"scores": {"correctness": 1.0}}}]},
            {"skill": "qcloud-cos-ops", "iterations": [{"critic": {"scores": {"correctness": 0.0}}}]},
        ]
        result = _extract_iteration_scores(traces, "qcloud-cvm-ops")
        self.assertIn("qcloud-cvm-ops", result)
        self.assertNotIn("qcloud-cos-ops", result)

    def test_missing_scores(self):
        traces = [{"skill": "qcloud-cvm-ops", "iterations": [{}]}]
        result = _extract_iteration_scores(traces, None)
        self.assertNotIn("qcloud-cvm-ops", result)

    def test_empty_traces(self):
        self.assertEqual(_extract_iteration_scores([], None), {})


class TestLoadTraces(unittest.TestCase):
    def test_dir_does_not_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "no-such-dir"
            result = _load_traces(root, None)
            self.assertEqual(result, [])

    def test_one_valid_trace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            trace = {"skill": "qcloud-test-ops", "iterations": [{"critic": {"scores": {}}}]}
            audit = root / "audit-results"
            audit.mkdir()
            (audit / "gcl-trace-20250710-120000.json").write_text(
                json.dumps(trace), encoding="utf-8"
            )
            result = _load_traces(root, None)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["skill"], "qcloud-test-ops")

    def test_malformed_json_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audit = root / "audit-results"
            audit.mkdir()
            (audit / "gcl-trace-20250710-120000.json").write_text("not valid json{", encoding="utf-8")
            (audit / "gcl-trace-20250711-120000.json").write_text(
                json.dumps({"skill": "qcloud-good-ops", "iterations": [{"critic": {"scores": {}}}]}),
                encoding="utf-8",
            )
            result = _load_traces(root, None)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["skill"], "qcloud-good-ops")

    def test_bad_filename_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audit = root / "audit-results"
            audit.mkdir()
            (audit / "gcl-trace-badname.json").write_text(
                json.dumps({"skill": "qcloud-bad-ops", "iterations": [{"critic": {"scores": {}}}]}),
                encoding="utf-8",
            )
            (audit / "gcl-trace-20250711-120000.json").write_text(
                json.dumps({"skill": "qcloud-good-ops", "iterations": [{"critic": {"scores": {}}}]}),
                encoding="utf-8",
            )
            result = _load_traces(root, None)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["skill"], "qcloud-good-ops")

    def test_days_cutoff_excludes_old(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audit = root / "audit-results"
            audit.mkdir()
            now = datetime.now(timezone.utc)
            old_date = (now - timedelta(days=60)).strftime("%Y%m%d")
            recent_date = now.strftime("%Y%m%d")
            (audit / f"gcl-trace-{old_date}-120000.json").write_text(
                json.dumps({"skill": "qcloud-old-ops", "iterations": [{"critic": {"scores": {}}}]}),
                encoding="utf-8",
            )
            (audit / f"gcl-trace-{recent_date}-120000.json").write_text(
                json.dumps({"skill": "qcloud-recent-ops", "iterations": [{"critic": {"scores": {}}}]}),
                encoding="utf-8",
            )
            result = _load_traces(root, 30)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["skill"], "qcloud-recent-ops")

    def test_mixed_old_new(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audit = root / "audit-results"
            audit.mkdir()
            now = datetime.now(timezone.utc)
            old_date = (now - timedelta(days=60)).strftime("%Y%m%d")
            recent_date = (now - timedelta(days=5)).strftime("%Y%m%d")
            (audit / f"gcl-trace-{old_date}-120000.json").write_text(
                json.dumps({"skill": "old", "iterations": [{"critic": {"scores": {}}}]}),
                encoding="utf-8",
            )
            (audit / f"gcl-trace-{recent_date}-120000.json").write_text(
                json.dumps({"skill": "recent1", "iterations": [{"critic": {"scores": {}}}]}),
                encoding="utf-8",
            )
            result = _load_traces(root, 30)
            skills = [t["skill"] for t in result]
            self.assertEqual(skills, ["recent1"])


class TestGenerateReport(unittest.TestCase):
    def test_no_traces(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            report = generate_report(root, None, None)
            self.assertEqual(report, {})

    def test_real_trace(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            trace = {
                "skill": "qcloud-test-ops",
                "iterations": [{"critic": {"scores": {
                    "correctness": 1.0, "safety": 1.0,
                    "idempotency": 0.5, "traceability": 1.0,
                    "spec_compliance": 0.5,
                }}}],
            }
            audit = root / "audit-results"
            audit.mkdir()
            (audit / "gcl-trace-20250710-120000.json").write_text(
                json.dumps(trace), encoding="utf-8"
            )
            report = generate_report(root, None, None)
            self.assertIn("qcloud-test-ops", report["skills"])
            dims = report["skills"]["qcloud-test-ops"]["dimensions"]
            self.assertEqual(dims["correctness"]["suggested"], 1.0)
            self.assertEqual(dims["safety"]["suggested"], 1.0)
            self.assertEqual(dims["safety"]["status"], "locked")

    def test_all_dims_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            trace = {
                "skill": "qcloud-test-ops",
                "iterations": [{"critic": {"scores": {
                    "correctness": 1.0, "safety": 1.0,
                    "idempotency": 0.5, "traceability": 1.0,
                    "spec_compliance": 0.5,
                }}}],
            }
            audit = root / "audit-results"
            audit.mkdir()
            (audit / "gcl-trace-20250710-120000.json").write_text(
                json.dumps(trace), encoding="utf-8"
            )
            report = generate_report(root, None, None)
            dims = report["skills"]["qcloud-test-ops"]["dimensions"]
            for dim in DEFAULT_THRESHOLDS:
                self.assertIn(dim, dims, f"{dim} missing from output")


class TestPrintTable(unittest.TestCase):
    def test_empty_report(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            print_table({})
        self.assertIn("No data.", out.getvalue())

    def test_non_empty_report(self):
        report = {
            "period_days": 90,
            "skills": {
                "qcloud-test-ops": {
                    "sample_count": 5,
                    "confidence": "MEDIUM",
                    "dimensions": {
                        "correctness": {
                            "default": 0.5,
                            "mean": 0.8,
                            "std": 0.2,
                            "suggested": 0.6,
                            "deviation": 0.1,
                            "status": "ok",
                        },
                        "safety": {
                            "default": 1.0,
                            "mean": 1.0,
                            "std": 0.0,
                            "suggested": 1.0,
                            "deviation": 0.0,
                            "status": "locked",
                        },
                        "idempotency": {
                            "default": 0.5,
                            "mean": None,
                            "std": None,
                            "suggested": None,
                            "deviation": None,
                            "status": "no_data",
                        },
                        "traceability": {
                            "default": 0.5,
                            "mean": 1.0,
                            "std": 0.0,
                            "suggested": 1.0,
                            "deviation": 0.5,
                            "status": "ok",
                        },
                        "spec_compliance": {
                            "default": 0.5,
                            "mean": 0.3,
                            "std": 0.3,
                            "suggested": 0.0,
                            "deviation": -0.5,
                            "status": "ok",
                        },
                    },
                }
            },
        }
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            print_table(report)
        output = out.getvalue()
        self.assertIn("qcloud-test-ops", output)
        self.assertIn("MEDIUM", output)
        self.assertIn("locked", output)


if __name__ == "__main__":
    import contextlib

    unittest.main(verbosity=2)
