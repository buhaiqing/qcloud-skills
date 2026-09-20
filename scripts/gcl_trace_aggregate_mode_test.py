#!/usr/bin/env python3
"""F14 — Critic provenance (`critic._mode`) bucketing in gcl_trace_aggregate.py.

Producer: ``gcl_runner.py`` tags each Critic payload with ``_mode``
(``llm-builtin`` / ``structural-only`` / ``structural-only-fallback``). Consumer:
``gcl_trace_aggregate.py`` must bucket runs by that mode so rule-based scores
substituted after an LLM Critic failure cannot masquerade as LLM verdicts in the
summary that feeds the Cloud Monitor alarm path.

These tests drive the real CLI (``--root`` / ``--since-hours``) against temp
trace directories and read the persisted ``gcl-quality-summary-*.json``; no
internal function is monkeypatched, so broken argument wiring or persistence
fails the test rather than passing silently.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# L2: cwd-independent — pytest may run from the repo root or elsewhere.
SCRIPT = Path(__file__).resolve().parent / "gcl_trace_aggregate.py"

SCORES = {
    "correctness": 1,
    "safety": 1,
    "idempotency": 1,
    "traceability": 1,
    "spec_compliance": 1,
}

FALLBACK_MODE = "structural-only-fallback"
LLM_MODE = "llm-builtin"


def make_trace(skill: str, mode: str | None, status: str = "PASS") -> dict:
    """Build a trace in the shape ``gcl_runner.py`` writes.

    ``mode=None`` omits ``_mode`` entirely (legacy trace).
    """
    critic: dict = {
        "scores": dict(SCORES),
        "suggestions": [],
        "blocking": False,
        "rubric_rule_hits": {},
    }
    if mode is not None:
        critic["_mode"] = mode
    return {
        "skill": skill,
        "started_at": "2026-09-20T00:00:00+00:00",
        "iterations": [
            {"iter": 1, "generator": {"exit_code": 0}, "critic": critic, "decision": "PASS"}
        ],
        "final": {"status": status, "iter": 1, "output": None, "failure_pattern": None},
    }


def write_trace(root: Path, name: str, payload: dict) -> Path:
    audit = root / "audit-results"
    audit.mkdir(parents=True, exist_ok=True)
    path = audit / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def write_threshold(root: Path, value: object) -> None:
    shared = root / "assets" / "shared"
    shared.mkdir(parents=True, exist_ok=True)
    (shared / "thresholds.json").write_text(
        json.dumps({"gcl_structural_fallback_max_ratio": value}), encoding="utf-8"
    )


def run_aggregate(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *extra],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def persisted_summary(proc: subprocess.CompletedProcess[str]) -> dict:
    """Read the summary the CLI actually persisted (stdout carries its path)."""
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    return json.loads(Path(payload["summary_path"]).read_text(encoding="utf-8"))


class FallbackBreachTests(unittest.TestCase):
    """① A fallback run must be counted and must trip the fail-closed threshold."""

    def test_fallback_run_counted_and_breaches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_trace(root, "gcl-trace-a.json", make_trace("cvm-ops", FALLBACK_MODE))
            write_trace(root, "gcl-trace-b.json", make_trace("cvm-ops", LLM_MODE))

            proc = run_aggregate(root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            summary = persisted_summary(proc)

            # Known modes always present, so a consumer can read 0 rather than
            # KeyError on a healthy window.
            self.assertEqual(summary["critic_mode_counts"][FALLBACK_MODE], 1)
            self.assertEqual(summary["critic_mode_counts"][LLM_MODE], 1)
            self.assertEqual(summary["critic_mode_counts"]["missing"], 0)
            self.assertEqual(summary["structural_fallback_runs"], 1)
            self.assertEqual(summary["structural_fallback_ratio"], 0.5)

            # No thresholds.json under this root → fail-closed to 0.0 (L21).
            self.assertFalse(summary["structural_fallback_threshold_configured"])
            self.assertEqual(summary["structural_fallback_max_ratio"], 0.0)
            self.assertIs(summary["structural_fallback_breach"], True)
            self.assertIn("ALERT", proc.stderr)

            # Existing consumer-visible fields must survive the change.
            for key in ("version", "generated_at", "totals", "pass_rate", "by_skill",
                        "avg_rubric_scores", "trace_files"):
                self.assertIn(key, summary)

    def test_invalid_threshold_fails_closed_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_threshold(root, "not-a-number")
            write_trace(root, "gcl-trace-a.json", make_trace("cvm-ops", FALLBACK_MODE))

            proc = run_aggregate(root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            summary = persisted_summary(proc)

            self.assertFalse(summary["structural_fallback_threshold_configured"])
            self.assertEqual(summary["structural_fallback_max_ratio"], 0.0)
            self.assertIs(summary["structural_fallback_breach"], True)
            self.assertIn("gcl_structural_fallback_max_ratio", proc.stderr)


class SilentSideTests(unittest.TestCase):
    """② All-LLM window → zero fallback, no breach, no alarm noise (L6)."""

    def test_all_llm_runs_do_not_breach_or_alert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_threshold(root, 0.5)
            write_trace(root, "gcl-trace-a.json", make_trace("cdn-ops", LLM_MODE))
            write_trace(root, "gcl-trace-b.json", make_trace("cdn-ops", LLM_MODE))

            proc = run_aggregate(root, "--since-hours", "24")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            summary = persisted_summary(proc)

            self.assertEqual(summary["critic_mode_counts"][LLM_MODE], 2)
            self.assertEqual(summary["structural_fallback_runs"], 0)
            self.assertEqual(summary["structural_fallback_ratio"], 0.0)
            self.assertTrue(summary["structural_fallback_threshold_configured"])
            self.assertEqual(summary["structural_fallback_max_ratio"], 0.5)
            self.assertIs(summary["structural_fallback_breach"], False)
            self.assertNotIn("ALERT", proc.stderr)


class MissingModeTests(unittest.TestCase):
    """③ Legacy trace without `_mode` → bucketed as missing, never a crash."""

    def test_missing_mode_is_its_own_bucket_not_a_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_threshold(root, 0.5)
            write_trace(root, "gcl-trace-legacy.json", make_trace("redis-ops", None))

            proc = run_aggregate(root, "--since-hours", "24")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            summary = persisted_summary(proc)

            self.assertEqual(summary["critic_mode_counts"]["missing"], 1)
            self.assertEqual(summary["critic_mode_counts"][LLM_MODE], 0)
            self.assertEqual(summary["structural_fallback_runs"], 0)
            self.assertIs(summary["structural_fallback_breach"], False)
            # Scores are still aggregated — legacy traces stay readable.
            self.assertEqual(summary["totals"]["total_runs"], 1)


if __name__ == "__main__":
    unittest.main()
