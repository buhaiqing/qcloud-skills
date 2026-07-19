#!/usr/bin/env python3
"""Unit tests for scripts/l4_metrics_tracker.py."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import l4_metrics_tracker as l4  # noqa: E402


def make_trace(
    status: str = "PASS",
    iterations: int = 1,
    matched: int = 0,
    scores: dict | None = None,
    timestamp: str | None = None,
) -> dict:
    """Build a minimal gcl-trace dict for testing."""
    default_scores = {
        "correctness": 0.8,
        "safety": 1.0,
        "idempotency": 0.6,
        "traceability": 0.7,
        "spec_compliance": 0.6,
    }
    if scores is not None:
        default_scores.update(scores)

    iters = []
    for i in range(iterations):
        iters.append(
            {
                "iter": i + 1,
                "generator": {"command": "echo ok", "exit_code": 0},
                "critic": {
                    "scores": default_scores,
                    "suggestions": [],
                    "blocking": False,
                    "rubric_rule_hits": {k: [] for k in default_scores},
                },
                "decision": "PASS" if i < iterations - 1 or status == "PASS" else "FAIL",
            }
        )

    return {
        "skill": "qcloud-test-ops",
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "final": {"status": status, "iter": iterations},
        "iterations": iters,
        "preflight_reflexion": {
            "skill": "qcloud-test-ops",
            "command": "echo ok",
            "matched": matched,
            "injection": "",
        },
    }


def write_trace(dir: Path, name: str, payload: dict) -> Path:
    p = dir / name
    p.write_text(json.dumps(payload))
    return p


# =============================================================================
# TestAvgIterations
# =============================================================================


class TestAvgIterations(unittest.TestCase):
    def test_all_pass_single_iter(self) -> None:
        traces = [make_trace(status="PASS", iterations=1) for _ in range(5)]
        self.assertEqual(l4.get_avg_iterations(traces), 1.0)

    def test_mixed_iterations(self) -> None:
        traces = [
            make_trace(status="PASS", iterations=1),
            make_trace(status="PASS", iterations=2),
            make_trace(status="PASS", iterations=3),
        ]
        self.assertAlmostEqual(l4.get_avg_iterations(traces), 2.0)

    def test_ignores_non_pass(self) -> None:
        traces = [
            make_trace(status="PASS", iterations=1),
            make_trace(status="SAFETY_FAIL", iterations=5),
            make_trace(status="MAX_ITER", iterations=3),
        ]
        self.assertEqual(l4.get_avg_iterations(traces), 1.0)

    def test_empty_returns_none(self) -> None:
        self.assertIsNone(l4.get_avg_iterations([]))

    def test_no_pass_returns_none(self) -> None:
        traces = [
            make_trace(status="SAFETY_FAIL", iterations=2),
            make_trace(status="MAX_ITER", iterations=3),
        ]
        self.assertIsNone(l4.get_avg_iterations(traces))


# =============================================================================
# TestFailurePatternHitRate
# =============================================================================


class TestFailurePatternHitRate(unittest.TestCase):
    def test_no_traces(self) -> None:
        self.assertIsNone(l4.get_failure_pattern_hit_rate([]))

    def test_all_miss(self) -> None:
        traces = [make_trace(matched=0) for _ in range(5)]
        self.assertEqual(l4.get_failure_pattern_hit_rate(traces), 0.0)

    def test_all_hit(self) -> None:
        traces = [make_trace(matched=3) for _ in range(5)]
        self.assertEqual(l4.get_failure_pattern_hit_rate(traces), 1.0)

    def test_partial_hit(self) -> None:
        traces = [make_trace(matched=1 if i < 2 else 0) for i in range(5)]
        self.assertAlmostEqual(l4.get_failure_pattern_hit_rate(traces), 0.4)


# =============================================================================
# TestEmergingPatternLatency
# =============================================================================


class TestEmergingPatternLatency(unittest.TestCase):
    def test_no_logs_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(l4.get_emerging_pattern_latency(Path(td)))

    def test_returns_days_since_most_recent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            # Write a log 3 days ago
            old = d / "pattern-anomaly-20260716.json"
            old.write_text("[]")
            old_time = datetime.now(timezone.utc) - timedelta(days=3)
            os.utime(old, (old_time.timestamp(), old_time.timestamp()))

            # Write a log 1 day ago
            recent = d / "pattern-anomaly-20260718.json"
            recent.write_text("[]")
            recent_time = datetime.now(timezone.utc) - timedelta(days=1)
            os.utime(recent, (recent_time.timestamp(), recent_time.timestamp()))

            latency = l4.get_emerging_pattern_latency(d)
            self.assertIsNotNone(latency)
            self.assertEqual(latency, 1)


# =============================================================================
# TestSuccessPathReuseRate
# =============================================================================


class TestSuccessPathReuseRate(unittest.TestCase):
    def test_no_traces(self) -> None:
        self.assertIsNone(l4.get_success_path_reuse_rate([]))

    def test_no_pass_returns_none(self) -> None:
        traces = [
            make_trace(status="SAFETY_FAIL", matched=1),
            make_trace(status="MAX_ITER", matched=0),
        ]
        self.assertIsNone(l4.get_success_path_reuse_rate(traces))

    def test_all_pass_no_reuse(self) -> None:
        traces = [make_trace(status="PASS", matched=0) for _ in range(5)]
        self.assertEqual(l4.get_success_path_reuse_rate(traces), 0.0)

    def test_all_pass_with_reuse(self) -> None:
        traces = [make_trace(status="PASS", matched=2) for _ in range(5)]
        self.assertEqual(l4.get_success_path_reuse_rate(traces), 1.0)

    def test_partial_reuse(self) -> None:
        traces = [
            make_trace(status="PASS", matched=1) if i < 3
            else make_trace(status="PASS", matched=0)
            for i in range(5)
        ]
        self.assertAlmostEqual(l4.get_success_path_reuse_rate(traces), 0.6)


# =============================================================================
# TestRubricThresholdDeviation
# =============================================================================


class TestRubricThresholdDeviation(unittest.TestCase):
    def test_no_traces(self) -> None:
        self.assertIsNone(l4.get_rubric_threshold_deviation([]))

    def test_zero_deviation(self) -> None:
        scores = {dim: l4.DEFAULT_THRESHOLDS[dim] for dim in l4.RUBRIC_DIMS}
        traces = [make_trace(scores=scores)]
        self.assertEqual(l4.get_rubric_threshold_deviation(traces), 0.0)

    def test_positive_deviation(self) -> None:
        scores = {dim: 1.0 for dim in l4.RUBRIC_DIMS}
        traces = [make_trace(scores=scores)]
        dev = l4.get_rubric_threshold_deviation(traces)
        self.assertIsNotNone(dev)
        self.assertGreater(dev, 0)

    def test_ignores_missing_dims(self) -> None:
        scores = {"correctness": 0.8}
        traces = [make_trace(scores=scores)]
        dev = l4.get_rubric_threshold_deviation(traces)
        self.assertIsNotNone(dev)


# =============================================================================
# TestStatusFunctions
# =============================================================================


class TestStatusLowerIsBetter(unittest.TestCase):
    def test_at_target_is_check(self) -> None:
        self.assertEqual(l4._status_lower_is_better(1.0, 1.0), "✅")

    def test_below_target_is_check(self) -> None:
        self.assertEqual(l4._status_lower_is_better(0.5, 1.0), "✅")

    def test_above_target_is_cross(self) -> None:
        self.assertEqual(l4._status_lower_is_better(2.0, 1.0), "❌")


class TestStatusHigherIsBetter(unittest.TestCase):
    def test_at_target_is_check(self) -> None:
        self.assertEqual(l4._status_higher_is_better(0.6, 0.6), "✅")

    def test_above_target_is_check(self) -> None:
        self.assertEqual(l4._status_higher_is_better(0.9, 0.6), "✅")

    def test_way_below_target_is_cross(self) -> None:
        self.assertEqual(l4._status_higher_is_better(0.3, 0.6), "❌")

    def test_80_to_100_pct_is_warning(self) -> None:
        self.assertEqual(l4._status_higher_is_better(0.5, 0.6), "⚠️")


# =============================================================================
# TestBuildMetric
# =============================================================================


class TestBuildMetric(unittest.TestCase):
    def test_current_none(self) -> None:
        m = l4._build_metric(None, 0.5)
        self.assertIsNone(m["current"])
        self.assertEqual(m["target"], 0.5)
        self.assertEqual(m["status"], "❌")

    def test_full_fields(self) -> None:
        m = l4._build_metric(0.8, 0.5, note="foo")
        self.assertEqual(m["current"], 0.8)
        self.assertEqual(m["target"], 0.5)
        self.assertEqual(m["status"], "✅")
        self.assertEqual(m["note"], "foo")

    def test_lower_is_better_at_target(self) -> None:
        m = l4._build_metric(1.8, 1.8, lower_is_better=True)
        self.assertEqual(m["status"], "✅")

    def test_lower_is_better_above_target(self) -> None:
        m = l4._build_metric(2.0, 1.8, lower_is_better=True)
        self.assertEqual(m["status"], "❌")


# =============================================================================
# Integration: main with real temp dir
# =============================================================================


class TestMain(unittest.TestCase):
    def test_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            audit = root / "audit-results"
            audit.mkdir()

            for i in range(3):
                write_trace(audit, f"gcl-trace-20260719-{i:06d}.json", make_trace(iterations=2))

            old_argv = sys.argv
            sys.argv = ["l4", "--trace-dir", str(audit), "--since-days", "30"]
            try:
                ret = l4.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(ret, 0)
            out = audit / "l4-metrics.json"
            self.assertTrue(out.exists())
            data = json.loads(out.read_text())
            self.assertIn("generated_at", data)
            self.assertIn("metrics", data)
            m = data["metrics"]
            # avg_iterations: all 3 traces PASS with 2 iters each → 2.0
            self.assertEqual(m["avg_iterations"]["current"], 2.0)
            # failure_pattern_hit_rate: no matched → 0.0
            self.assertEqual(m["failure_pattern_hit_rate"]["current"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
