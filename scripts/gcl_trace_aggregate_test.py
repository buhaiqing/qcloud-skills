#!/usr/bin/env python3
"""Unit tests for scripts/gcl_trace_aggregate.py."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import gcl_trace_aggregate as gta

SCORES = {
    "correctness": 1,
    "safety": 1,
    "idempotency": 0.5,
    "traceability": 1,
    "spec_compliance": 1,
}


def trace(skill: str, status: str, iterations: int = 1) -> dict:
    return {
        "skill": skill,
        "iterations": [
            {"iter": idx + 1, "critic": {"scores": SCORES}}
            for idx in range(iterations)
        ],
        "final": {"status": status, "iter": iterations, "output": "..."},
    }


def write_trace(root: Path, name: str, payload: dict | str) -> Path:
    audit = root / "audit-results"
    audit.mkdir(parents=True, exist_ok=True)
    path = audit / name
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def quiet_main(argv: list[str]) -> int:
    old_argv = sys.argv
    try:
        sys.argv = argv
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return gta.main()
    finally:
        sys.argv = old_argv


class ParseTests(unittest.TestCase):
    def test_invalid_json_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text("{bad", encoding="utf-8")
            self.assertIsNone(gta.parse_trace(p))


class AggregateTests(unittest.TestCase):
    def test_status_counts_and_pass_rate(self) -> None:
        result = gta.aggregate([
            trace("qcloud-cvm-ops", "PASS"),
            trace("qcloud-cvm-ops", "PASS"),
            trace("qcloud-cvm-ops", "MAX_ITER"),
        ])
        self.assertEqual(result["totals"]["PASS"], 2)
        self.assertEqual(result["totals"]["MAX_ITER"], 1)
        self.assertAlmostEqual(result["pass_rate"], 2 / 3, places=4)

    def test_empty_traces_have_zero_pass_rate(self) -> None:
        summary = gta.aggregate([])
        self.assertEqual(summary["totals"]["total_runs"], 0)
        self.assertEqual(summary["pass_rate"], 0.0)


class CollectPathTests(unittest.TestCase):
    def test_no_trace_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(gta.collect_paths(Path(tmp), None, None), [])

    def test_since_hours_filters_old_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            recent = write_trace(root, "gcl-trace-recent.json", trace("qcloud-cvm-ops", "PASS"))
            old = write_trace(root, "gcl-trace-old.json", trace("qcloud-cvm-ops", "PASS"))
            old_time = time.time() - 72 * 3600
            os.utime(old, (old_time, old_time))

            paths = gta.collect_paths(root, None, since_hours=24)
            self.assertEqual(paths, [recent])

    def test_input_glob(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = write_trace(root, "gcl-trace-a.json", trace("x", "PASS"))
            second = write_trace(root, "gcl-trace-b.json", trace("x", "PASS"))
            paths = gta.collect_paths(root, ["audit-results/gcl-trace-*.json"], None)
            self.assertEqual(sorted(paths), sorted([first, second]))


class MainTests(unittest.TestCase):
    def test_main_no_trace_returns_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(quiet_main(["gcl_trace_aggregate.py", "--root", tmp]), 1)

    def test_main_skips_invalid_json_and_persists_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_trace(root, "gcl-trace-good.json", trace("qcloud-cvm-ops", "PASS"))
            write_trace(root, "gcl-trace-bad.json", "{bad")
            self.assertEqual(quiet_main(["gcl_trace_aggregate.py", "--root", tmp]), 0)
            summaries = sorted((root / "audit-results").glob("gcl-quality-summary-*.json"))
            self.assertEqual(len(summaries), 1)
            data = json.loads(summaries[0].read_text(encoding="utf-8"))
            self.assertEqual(data["totals"]["PASS"], 1)


class CrossSkillChainTests(unittest.TestCase):
    def test_failure_status_yields_no_scores(self) -> None:
        # Emit a TraceSpan with status='failure' — failure run has no iterations
        trace_record = {"skill": "qcloud-cvm-ops", "final": {"status": "failure"}, "iterations": []}
        self.assertEqual(gta.last_scores(trace_record), {})

    def test_halted_status_yields_no_scores(self) -> None:
        # Emit a TraceSpan with status='halted' — halted run has no iterations
        trace_record = {"skill": "qcloud-redis-ops", "final": {"status": "halted"}, "iterations": []}
        self.assertEqual(gta.last_scores(trace_record), {})

class PersistSummaryTests(unittest.TestCase):
    def test_persisted_file_contains_rubric_scores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = {
                "version": "1.0",
                "generated_at": "2026-08-24T12:00:00+00:00",
                "window": {"trace_count": 1},
                "totals": {"PASS": 1, "SAFETY_FAIL": 0, "MAX_ITER": 0, "total_runs": 1},
                "pass_rate": 1.0,
                "avg_rubric_scores": {
                    "correctness": 0.9,
                    "safety": 1.0,
                    "idempotency": 0.5,
                    "traceability": 1.0,
                    "spec_compliance": 0.95,
                },
                "by_skill": {},
                "trace_files": [],
            }
            path = gta.persist_summary(root, summary)
            self.assertTrue(path.exists())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("avg_rubric_scores", data)
            self.assertEqual(data["avg_rubric_scores"]["correctness"], 0.9)
            self.assertEqual(data["avg_rubric_scores"]["safety"], 1.0)


class CrossSkillSinceFilterTests(unittest.TestCase):
    """Tests for cross_skill_chain --since ISO8601 filtering."""

    def _write_spans(self, root: Path, run_id: str, spans: list[dict]) -> None:
        spans_dir = root / ".runtime" / "traces" / run_id
        spans_dir.mkdir(parents=True, exist_ok=True)
        (spans_dir / "spans.jsonl").write_text(
            "\n".join(json.dumps(s) for s in spans) + "\n",
            encoding="utf-8",
        )

    def test_since_filters_out_old_spans(self) -> None:
        """Spans older than --since must be excluded from chain and span_count."""
        root = Path(tempfile.mkdtemp())
        run_id = "since-filter-test"
        self._write_spans(root, run_id, [
            {
                "span_id": "span-old",
                "parent_span_id": None,
                "skill": "qcloud-cvm-ops",
                "operation": "DescribeInstances",
                "status": "success",
                "start_time": "2026-01-01T00:00:00+00:00",
                "duration_ms": 100,
            },
            {
                "span_id": "span-new",
                "parent_span_id": "span-old",
                "skill": "qcloud-vpc-ops",
                "operation": "DescribeVpcEx",
                "status": "success",
                "start_time": "2026-08-25T00:00:00+00:00",
                "duration_ms": 200,
            },
        ])
        result = gta.cross_skill_chain(root, run_id, since="2026-06-01T00:00:00+00:00")
        self.assertEqual(result["span_count"], 1)
        self.assertEqual(result["chain"][0]["span_id"], "span-new")
        self.assertEqual(result["skills_invoked"], ["qcloud-vpc-ops"])
        self.assertEqual(result["total_duration_ms"], 200)

    def test_since_iso8601_z_suffix_parsed(self) -> None:
        """--since with 'Z' suffix must be parsed correctly."""
        root = Path(tempfile.mkdtemp())
        run_id = "since-z-test"
        self._write_spans(root, run_id, [
            {
                "span_id": "span-old",
                "skill": "qcloud-cvm-ops",
                "operation": "op",
                "status": "success",
                "start_time": "2026-01-01T00:00:00Z",
                "duration_ms": 50,
            },
            {
                "span_id": "span-new",
                "skill": "qcloud-cvm-ops",
                "operation": "op",
                "status": "success",
                "start_time": "2026-08-25T12:00:00Z",
                "duration_ms": 50,
            },
        ])
        result = gta.cross_skill_chain(root, run_id, since="2026-06-01T00:00:00Z")
        self.assertEqual(result["span_count"], 1)
        self.assertEqual(result["chain"][0]["span_id"], "span-new")

    def test_no_since_returns_all_spans(self) -> None:
        """Without --since, all spans must be returned."""
        root = Path(tempfile.mkdtemp())
        run_id = "no-since-test"
        self._write_spans(root, run_id, [
            {
                "span_id": "span-a",
                "skill": "qcloud-cvm-ops",
                "operation": "op",
                "status": "success",
                "start_time": "2026-01-01T00:00:00+00:00",
                "duration_ms": 10,
            },
            {
                "span_id": "span-b",
                "skill": "qcloud-vpc-ops",
                "operation": "op",
                "status": "success",
                "start_time": "2026-08-25T00:00:00+00:00",
                "duration_ms": 20,
            },
        ])
        result = gta.cross_skill_chain(root, run_id, since=None)
        self.assertEqual(result["span_count"], 2)
        self.assertEqual(result["skills_invoked"], ["qcloud-cvm-ops", "qcloud-vpc-ops"])

    def test_since_epoch_float_also_filtered(self) -> None:
        """Spans with epoch float start_time must also be filtered correctly."""
        root = Path(tempfile.mkdtemp())
        run_id = "since-epoch-test"
        now = time.time()
        self._write_spans(root, run_id, [
            {
                "span_id": "span-old",
                "skill": "qcloud-cvm-ops",
                "operation": "op",
                "status": "success",
                "start_time": now - 86400 * 30,  # 30 days ago
                "duration_ms": 10,
            },
            {
                "span_id": "span-new",
                "skill": "qcloud-cvm-ops",
                "operation": "op",
                "status": "success",
                "start_time": now,
                "duration_ms": 10,
            },
        ])
        since_iso = datetime.fromtimestamp(now - 86400, tz=UTC).isoformat()
        result = gta.cross_skill_chain(root, run_id, since=since_iso)
        self.assertEqual(result["span_count"], 1)
        self.assertEqual(result["chain"][0]["span_id"], "span-new")


if __name__ == "__main__":
    unittest.main()
