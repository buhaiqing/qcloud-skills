#!/usr/bin/env python3
"""Unit tests for scripts/distribution_drift.py.

Maps 1:1 to the P1-E distribution-drift acceptance criteria
(docs/superpowers/specs/p1-e-distribution-drift-design.md) plus robustness.

Run: cd scripts && python3 -m unittest distribution_drift_test -v
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

# Ensure scripts/ is importable regardless of cwd (repo lesson L2).
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from distribution_drift import (
    _simplified_ks_test,
    analyze_drift,
    compute_drift,
    self_verify,
)


def _mk_trace(status, skill="qcloud-cvm-ops", safety=1.0, days_ago=0):
    """Build a minimal GCL trace dict with an ISO timestamp."""
    return {
        "timestamp": (datetime.now() - timedelta(days=days_ago)).isoformat(),
        "skill": skill,
        "final": {"status": status},
        "iterations": [
            {
                "critic": {
                    "scores": {
                        "correctness": safety,
                        "safety": safety,
                        "spec_compliance": safety,
                        "efficiency": safety,
                        "idempotency": safety,
                    }
                }
            }
        ],
    }


class DistributionDriftTest(unittest.TestCase):
    """Cover the 6 P1-E acceptance criteria plus robustness."""

    # --- Criterion 1: recent higher pass_rate => negative drift + down + alert ---
    def test_pass_rate_drift_recent_higher(self):
        # Spec SELF-VERIFY block is authoritative for criterion 1 semantics.
        recent = [_mk_trace("PASS"), _mk_trace("PASS"), _mk_trace("FAIL", safety=0.5)]
        baseline = [_mk_trace("PASS"), _mk_trace("PASS"), _mk_trace("PASS")]
        result = compute_drift(recent, baseline)
        # recent pass_rate = 2/3 ~ 0.667, baseline = 3/3 = 1.0
        self.assertLess(result["pass_rate"]["drift"], 0)
        self.assertEqual(result["pass_rate"]["direction"], "↓")
        self.assertTrue(result["alerts"])

    # --- Criterion 2: severe degradation => drift < 0 and drift_sigma < -1 ---
    def test_pass_rate_drift_severe_degradation(self):
        # Criterion-2 example uses 2 recent FAIL traces, which trips the
        # criterion-5 insufficient_recent_data guard (<3) — use 3 FAILs to keep
        # the degradation semantics testable. Baseline is [PASS,PASS,FAIL] so
        # its per-trace stdev is non-zero and drift_sigma is well-defined.
        recent = [_mk_trace("FAIL", safety=0.5)] * 3
        baseline = [_mk_trace("PASS"), _mk_trace("PASS"), _mk_trace("FAIL", safety=0.5)]
        result = compute_drift(recent, baseline)
        self.assertIn("safety_score", result)
        self.assertLess(result["pass_rate"]["drift"], 0)
        self.assertLess(result["pass_rate"]["drift_sigma"], -1)

    # --- Criterion 3: simplified KS distinguishes different distributions ---
    def test_simplified_ks_test_different_distributions(self):
        ks = _simplified_ks_test([1, 2, 3], [4, 5, 6])
        self.assertGreater(ks, 0.3)

    def test_simplified_ks_test_same_distribution(self):
        self.assertEqual(_simplified_ks_test([1, 1, 1, 1], [1, 1, 1, 1]), 0.0)
        self.assertEqual(_simplified_ks_test([], []), 0.0)

    # --- Criterion 4: qcloud-cos-ops pass_rate drop => high severity alert ---
    def test_high_severity_alert_when_cos_pass_rate_drops(self):
        # qcloud-cos-ops: recent 2/5 PASS (~40%) vs baseline 9/10 (~90%).
        # drift ~ -0.5 with baseline stdev ~0.30-0.32 => drift_sigma < -1.5,
        # which maps to severity == "high".
        recent = [_mk_trace("PASS", skill="qcloud-cos-ops")] * 2
        recent += [_mk_trace("FAIL", skill="qcloud-cos-ops", safety=0.5)] * 3
        baseline = [_mk_trace("PASS", skill="qcloud-cos-ops")] * 9
        baseline.append(_mk_trace("FAIL", skill="qcloud-cos-ops", safety=0.5))
        result = compute_drift(recent, baseline)
        cos_pass = result["per_skill"]["qcloud-cos-ops"]["pass_rate"]
        self.assertLess(cos_pass["drift_sigma"], -1.5)
        self.assertAlmostEqual(cos_pass["recent"], 0.4, places=1)
        alerts = [a for a in result["alerts"] if "qcloud-cos-ops" in a["metric"]]
        self.assertTrue(any(a["severity"] == "high" for a in alerts))

    # --- Criterion 5: <3 recent traces => insufficient_recent_data error ---
    def test_insufficient_recent_data(self):
        recent = [_mk_trace("PASS"), _mk_trace("FAIL", safety=0.5)]
        baseline = [_mk_trace("PASS") for _ in range(5)]
        result = compute_drift(recent, baseline)
        self.assertEqual(result.get("error"), "insufficient_recent_data")

    # --- Criterion 6: self-verify passes (direct call + CLI entry point) ---
    def test_self_verify(self):
        self.assertTrue(self_verify())
        proc = subprocess.run(
            [sys.executable, str(_HERE / "distribution_drift.py"), "--self-verify"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)

    # --- per-skill decomposition ---
    def test_per_skill_decomposition(self):
        recent = [_mk_trace("PASS", skill="qcloud-cvm-ops") for _ in range(3)]
        baseline = [_mk_trace("PASS", skill="qcloud-cvm-ops") for _ in range(3)]
        result = compute_drift(recent, baseline)
        per_skill = result["per_skill"]
        self.assertIn("qcloud-cvm-ops", per_skill)
        self.assertIn("pass_rate", per_skill["qcloud-cvm-ops"])

    # --- analyze_drift timestamp split: 3 recent vs 4 baseline ---
    def test_analyze_drift_split_by_timestamp(self):
        traces = [
            _mk_trace("PASS", days_ago=0),
            _mk_trace("PASS", days_ago=1),
            _mk_trace("FAIL", safety=0.5, days_ago=2),
        ] + [_mk_trace("PASS", days_ago=15) for _ in range(4)]
        result = analyze_drift(traces, 720)
        self.assertIsInstance(result, dict)
        self.assertNotIn("error", result)
        self.assertIn("pass_rate", result)
        # Only 2 recent traces => insufficient data.
        sparse = [_mk_trace("PASS"), _mk_trace("FAIL", safety=0.5)]
        sparse_result = analyze_drift(sparse, 720)
        self.assertEqual(sparse_result.get("error"), "insufficient_recent_data")

    # --- robustness: missing trace keys must be tolerated ---
    def test_robust_missing_keys_tolerated(self):
        recent = [
            {"timestamp": datetime.now().isoformat(), "skill": "qcloud-cvm-ops"},
            _mk_trace("PASS"),
            _mk_trace("PASS"),
        ]
        baseline = [_mk_trace("PASS") for _ in range(3)]
        result = compute_drift(recent, baseline)  # must not raise
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
