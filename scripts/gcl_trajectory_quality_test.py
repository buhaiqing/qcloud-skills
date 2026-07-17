#!/usr/bin/env python3
"""Unit tests for scripts/gcl_trajectory_quality.py."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import gcl_trajectory_quality as gtq  # noqa: E402


def quiet_main(argv: list[str]) -> int:
    old_argv = sys.argv
    try:
        sys.argv = argv
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return gtq.main()
    finally:
        sys.argv = old_argv


def write_trace(root: Path, name: str, payload: dict) -> Path:
    audit = root / "audit-results"
    audit.mkdir(parents=True, exist_ok=True)
    p = audit / name
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


class ConvergenceSpeedTests(unittest.TestCase):
    def _trace(self, status: str, decisions: list[str]) -> dict:
        return {
            "skill": "qcloud-test",
            "iterations": [
                {"iter": i + 1, "decision": d, "critic": {"scores": {"correctness": 1.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 1.0}}}
                for i, d in enumerate(decisions)
            ],
            "final": {"status": status, "iter": len(decisions)},
        }

    def test_single_iter_converges(self):
        t = self._trace("PASS", ["PASS"])
        r = gtq.convergence_speed(t)
        self.assertEqual(r["convergence_speed"], 1.0)
        self.assertEqual(r["oscillation_count"], 0)

    def test_multi_iter_converges(self):
        t = self._trace("PASS", ["RETRY", "RETRY", "PASS"])
        r = gtq.convergence_speed(t)
        self.assertEqual(r["convergence_speed"], 1.0)

    def test_no_iters(self):
        r = gtq.convergence_speed({})
        self.assertIsNone(r["convergence_speed"])

    def test_score_variance(self):
        t = {
            "skill": "qcloud-test",
            "iterations": [
                {"critic": {"scores": {"correctness": 1.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 1.0}}},
                {"critic": {"scores": {"correctness": 0.5, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 0.5}}},
            ],
            "final": {"status": "PASS", "iter": 2},
        }
        r = gtq.convergence_speed(t)
        self.assertGreater(r["score_variance"]["correctness"], 0)


class SafetyTrajectoryTests(unittest.TestCase):
    def test_all_safe(self):
        t = {
            "iterations": [
                {"critic": {"scores": {"safety": 1.0}}},
                {"critic": {"scores": {"safety": 1.0}}},
            ]
        }
        r = gtq.safety_trajectory(t)
        self.assertEqual(r["safety_trajectory"], [1.0, 1.0])
        self.assertFalse(r["safety_persistent_low"])

    def test_persistent_low(self):
        t = {
            "iterations": [
                {"critic": {"scores": {"safety": 0.0}}},
                {"critic": {"scores": {"safety": 0.5}}},
            ]
        }
        r = gtq.safety_trajectory(t)
        self.assertTrue(r["safety_persistent_low"])

    def test_recovery(self):
        t = {
            "iterations": [
                {"critic": {"scores": {"safety": 0.0}}},
                {"critic": {"scores": {"safety": 1.0}}},
            ]
        }
        r = gtq.safety_trajectory(t)
        self.assertTrue(r["safety_recovery"])

    def test_empty(self):
        r = gtq.safety_trajectory({})
        self.assertEqual(r["safety_trajectory"], [])


class EarlyFailureTests(unittest.TestCase):
    def test_early_safety_fail(self):
        t = {
            "iterations": [
                {"decision": "SAFETY_FAIL", "critic": {"scores": {"safety": 0.0}}},
            ]
        }
        r = gtq.early_failure(t)
        self.assertTrue(r["early_failure"])

    def test_late_pass(self):
        t = {
            "iterations": [
                {"decision": "RETRY"},
                {"decision": "PASS"},
            ]
        }
        r = gtq.early_failure(t)
        self.assertFalse(r["early_failure"])


class IterEfficiencyTests(unittest.TestCase):
    def test_first_iter_pass(self):
        t = {
            "iterations": [
                {"decision": "PASS", "critic": {"scores": {"correctness": 1.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 1.0}}},
            ],
            "final": {"status": "PASS", "iter": 1},
        }
        r = gtq.iter_efficiency(t)
        self.assertEqual(r["iter_efficiency"], 1.0)
        self.assertEqual(r["wasted_iters"], 0)

    def test_wasted_iters(self):
        # PASS at iter 2 of 3 → wasted = 3 - 2 = 1
        t = {
            "iterations": [
                {"decision": "RETRY", "critic": {"scores": {"correctness": 0.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 0.0}}},
                {"decision": "PASS", "critic": {"scores": {"correctness": 1.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 1.0}}},
                {"decision": "PASS", "critic": {"scores": {"correctness": 1.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 1.0}}},
            ],
            "final": {"status": "PASS", "iter": 3},
        }
        r = gtq.iter_efficiency(t)
        self.assertEqual(r["wasted_iters"], 1)


class OutlierScoreTests(unittest.TestCase):
    def test_no_baselines(self):
        t = {"skill": "qcloud-test", "iterations": [{"critic": {"scores": {"correctness": 1.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 1.0}}}]}
        r = gtq.outlier_score(t, {})
        self.assertIsNone(r["outlier"])

    def test_outlier_detected(self):
        # mean=1.0, stdev=0.1, value=0.5 → deviation=0.5 > 2*0.1=0.2 → outlier
        baselines = {"qcloud-test": {"correctness": (1.0, 0.1), "safety": (1.0, 0.0), "idempotency": (0.5, 0.0), "traceability": (1.0, 0.0), "spec_compliance": (1.0, 0.0)}}
        t = {"skill": "qcloud-test", "iterations": [{"critic": {"scores": {"correctness": 0.5, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 1.0}}}]}
        r = gtq.outlier_score(t, baselines)
        self.assertTrue(r["outlier"])
        self.assertIn("correctness", r["outlier_dims"])

    def test_no_outlier(self):
        baselines = {"qcloud-test": {"correctness": (1.0, 0.1), "safety": (1.0, 0.0), "idempotency": (0.5, 0.0), "traceability": (1.0, 0.0), "spec_compliance": (1.0, 0.0)}}
        t = {"skill": "qcloud-test", "iterations": [{"critic": {"scores": {"correctness": 0.95, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 1.0}}}]}
        r = gtq.outlier_score(t, baselines)
        self.assertFalse(r["outlier"])


class BaselinesTests(unittest.TestCase):
    def test_min_samples(self):
        traces = [
            {"skill": "qcloud-test", "iterations": [{"critic": {"scores": {"correctness": 1.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 1.0}}}]},
            {"skill": "qcloud-test", "iterations": [{"critic": {"scores": {"correctness": 0.5, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 1.0}}}]},
        ]
        b = gtq.compute_baselines(traces)
        self.assertIn("qcloud-test", b)
        self.assertIn("correctness", b["qcloud-test"])

    def test_single_trace(self):
        # Single trace: compute_baselines needs n>1, so no baseline computed
        traces = [
            {"skill": "qcloud-test", "iterations": [{"critic": {"scores": {"correctness": 1.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 1.0}}}]},
        ]
        b = gtq.compute_baselines(traces)
        self.assertNotIn("qcloud-test", b)  # n=1 < min_samples, no baseline


class DimensionCorrelationTests(unittest.TestCase):
    def test_correlation_matrix(self):
        traces = [
            {"skill": "qcloud-test", "iterations": [{"critic": {"scores": {"correctness": 1.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 1.0}}}]},
            {"skill": "qcloud-test", "iterations": [{"critic": {"scores": {"correctness": 0.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 0.0}}}]},
            {"skill": "qcloud-test", "iterations": [{"critic": {"scores": {"correctness": 0.5, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 0.5}}}]},
        ]
        r = gtq.dimension_correlation(traces)
        self.assertIn("correlation_matrix", r)


class MainTests(unittest.TestCase):
    def test_no_traces_returns_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = quiet_main(["gcl_trajectory_quality.py", "--root", tmp])
            self.assertEqual(r, 1)

    def test_dry_run_passes_even_no_traces(self):
        # --dry-run uses synthetic data, ignores real traces
        with tempfile.TemporaryDirectory() as tmp:
            r = quiet_main(["gcl_trajectory_quality.py", "--root", tmp, "--dry-run"])
            self.assertEqual(r, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
