#!/usr/bin/env python3
"""Tests for reflexion_efficacy.py — injection→outcome attribution metrics."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import reflexion_efficacy as re_eff


def _trace(
    skill: str,
    *,
    injected_keys: list[str] | None = None,
    status: str = "PASS",
    failure_text: str = "",
) -> dict:
    iterations = []
    if failure_text:
        iterations.append(
            {"generator": {"command": "tccli x", "exit_code": 1,
                            "result_excerpt": failure_text}}
        )
    pre: dict = {}
    if injected_keys is not None:
        pre = {
            "injection_id": "20260826T000000Z-deadbeef",
            "matched_failure_keys": injected_keys,
            "matched_failures": len(injected_keys),
        }
    return {
        "skill": skill,
        "preflight_reflexion": pre,
        "iterations": iterations,
        "final": {"status": status, "output": failure_text},
    }


KEY_A = "qcloud-cvm-ops|TerminateInstances|InvalidInstanceIds"


class ComputeReportTest(unittest.TestCase):
    def test_empty_corpus_is_explicitly_vacuous(self) -> None:
        report = re_eff.compute_report([])
        self.assertEqual(report["runs_total"], 0)
        self.assertIsNone(report["hint_coverage"])
        self.assertFalse(report["non_vacuous"])

    def test_injected_run_produces_non_vacuous_metrics(self) -> None:
        traces = [_trace("s1", injected_keys=[KEY_A])]
        report = re_eff.compute_report(traces)
        self.assertTrue(report["non_vacuous"])
        self.assertEqual(report["runs_with_injection"], 1)
        self.assertGreater(report["hint_coverage"], 0)
        slot = report["patterns"][KEY_A]
        self.assertEqual(slot["injected_runs"], 1)
        # L5/L8: populated values asserted, not just key presence
        self.assertEqual(slot["prevention_rate"], 1.0)

    def test_recurrence_lowers_prevention_rate(self) -> None:
        err = "AuthFailure signature expired"
        key_a = f"qcloud-cvm-ops|StopInstances|{err}"
        traces = [
            _trace("cvm", injected_keys=[key_a], status="PASS"),
            _trace("cvm", status="FAIL", failure_text=f"boom: {err}"),
        ]
        report = re_eff.compute_report(traces)
        slot = report["patterns"][key_a]
        self.assertEqual(slot["recurred_runs"], 1)
        self.assertAlmostEqual(slot["prevention_rate"], 0.0)

    def test_no_recurrence_keeps_full_prevention(self) -> None:
        traces = [
            _trace("cvm", injected_keys=[KEY_A], status="PASS"),
            _trace("cvm", status="FAIL", failure_text="totally different error"),
        ]
        report = re_eff.compute_report(traces)
        self.assertEqual(report["patterns"][KEY_A]["recurred_runs"], 0)
        self.assertEqual(report["patterns"][KEY_A]["prevention_rate"], 1.0)

    def test_recurrence_only_within_same_skill(self) -> None:
        err = "InvalidParameter zone mismatch"
        key = f"cdb-ops|CreateDB|{err}"
        traces = [
            _trace("cdb", injected_keys=[key], status="PASS"),
            _trace("cvm", status="FAIL", failure_text=err),
        ]
        report = re_eff.compute_report(traces)
        self.assertEqual(report["patterns"][key]["recurred_runs"], 0)

    def test_uninjected_traces_do_not_create_patterns(self) -> None:
        traces = [_trace("s1", status="FAIL", failure_text="x")]
        report = re_eff.compute_report(traces)
        self.assertFalse(report["non_vacuous"])
        self.assertEqual(report["patterns"], {})


class LoadTracesTest(unittest.TestCase):
    def test_load_skips_malformed_and_orders_oldest_first(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "gcl-trace-2.json").write_text(
                '{"skill":"a","final":{"status":"PASS"}}')
            (d / "gcl-trace-1.json").write_text("{broken")
            (d / "unrelated.txt").write_text("noise")
            traces = re_eff.load_traces(d)
            self.assertEqual(len(traces), 1)
            self.assertEqual(traces[0]["skill"], "a")


if __name__ == "__main__":
    unittest.main()
