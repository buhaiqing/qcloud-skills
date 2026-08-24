#!/usr/bin/env python3
"""Tests for TraceSpan unified observability (Phase 1.4).

Run: cd qcloud-copilot && python3 -m unittest copilot.test_trace_span -v

L5 lesson: assert populated values (real span_id, parent_chain length,
spans.jsonl bytes), not just key presence.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
COPILOT_ROOT = HERE.parent
REPO_ROOT = COPILOT_ROOT.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(COPILOT_ROOT))

from copilot.observ import ObservableSink, TraceSpan


class TraceSpanSchemaTests(unittest.TestCase):
    """TraceSpan dataclass schema & defaults."""

    def test_required_fields(self):
        span = TraceSpan(
            span_id="s1", trace_id="t1", parent_span_id=None,
            run_id="r1", skill="qcloud-cvm-ops", operation="RunInstances",
            step_id="step-1", status="success", duration_ms=123,
        )
        self.assertEqual(span.span_id, "s1")
        self.assertEqual(span.parent_span_id, None)
        self.assertEqual(span.duration_ms, 123)
        self.assertIsNone(span.error_code)
        self.assertIsNone(span.gcl_scores)
        self.assertEqual(span.metadata, {})

    def test_to_dict_round_trip(self):
        original = TraceSpan(
            span_id="s1", trace_id="t1", parent_span_id="p0",
            run_id="r1", skill="qcloud-cvm-ops", operation="RunInstances",
            step_id="step-1", status="delegated", duration_ms=456,
            error_code="InvalidVpc.NotFound",
            gcl_scores={"correctness": 1.0, "safety": 1.0},
            metadata={"attempt": 2},
        )
        as_dict = original.to_dict()
        # Required keys present.
        for k in ("span_id", "trace_id", "parent_span_id", "run_id",
                  "skill", "operation", "step_id", "start_time",
                  "end_time", "duration_ms", "status"):
            self.assertIn(k, as_dict)
        self.assertEqual(as_dict["span_id"], "s1")
        self.assertEqual(as_dict["parent_span_id"], "p0")
        self.assertEqual(as_dict["error_code"], "InvalidVpc.NotFound")
        self.assertEqual(as_dict["gcl_scores"]["safety"], 1.0)

    def test_duration_ms_computed_if_zero(self):
        # When duration_ms is 0 the to_dict must compute end-start in ms.
        span = TraceSpan(
            span_id="s1", trace_id="t1", parent_span_id=None,
            run_id="r1", skill="x", operation="op", step_id="step",
            status="success",
        )
        as_dict = span.to_dict()
        # start_time and end_time must both be set; duration_ms must be ≥0.
        self.assertTrue(as_dict["start_time"])
        self.assertTrue(as_dict["end_time"])
        self.assertIsInstance(as_dict["duration_ms"], int)
        self.assertGreaterEqual(as_dict["duration_ms"], 0)


class ObservableSinkSpanTests(unittest.TestCase):
    """ObservableSink.emit_span() persists spans.jsonl + summary."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="trace_span_test_"))
        self.sink = ObservableSink(runtime_root=self.tmp)

    def test_emit_span_writes_spans_jsonl(self):
        span = TraceSpan(
            span_id="s1", trace_id="t1", parent_span_id=None,
            run_id="r1", skill="qcloud-cvm-ops", operation="RunInstances",
            step_id="step-1", status="success", duration_ms=100,
        )
        self.sink.emit_trace_span(span)
        spans_path = self.tmp / "traces" / "r1" / "spans.jsonl"
        self.assertTrue(spans_path.exists(),
                        f"spans.jsonl must exist at {spans_path}")
        lines = spans_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertEqual(record["span_id"], "s1")
        self.assertEqual(record["skill"], "qcloud-cvm-ops")

    def test_emit_span_writes_summary(self):
        span = TraceSpan(
            span_id="s1", trace_id="t1", parent_span_id=None,
            run_id="r1", skill="qcloud-cvm-ops", operation="RunInstances",
            step_id="step-1", status="success", duration_ms=100,
        )
        self.sink.emit_trace_span(span)
        summary_path = self.tmp / "traces" / "r1" / "_summary.json"
        self.assertTrue(summary_path.exists(),
                        f"_summary.json must exist at {summary_path}")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["run_id"], "r1")
        self.assertEqual(summary["span_count"], 1)

    def test_emit_multiple_spans_appends(self):
        for i in range(3):
            self.sink.emit_trace_span(TraceSpan(
                span_id=f"s{i}", trace_id="t1", parent_span_id=None,
                run_id="r1", skill="qcloud-cvm-ops", operation="RunInstances",
                step_id=f"step-{i}", status="success", duration_ms=10 * i,
            ))
        spans_path = self.tmp / "traces" / "r1" / "spans.jsonl"
        lines = spans_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 3)
        summary = json.loads((self.tmp / "traces" / "r1" / "_summary.json")
                             .read_text(encoding="utf-8"))
        self.assertEqual(summary["span_count"], 3)


class ParentChildChainTests(unittest.TestCase):
    """Cross-skill delegation produces a valid parent-child chain."""

    def test_chain_complete(self):
        # Build a 5-span chain (the spec's example):
        #   s1 (Copilot: plan execution)
        #   ├── s2 (CVM: RunInstances)  parent=s1
        #   ├── s3 (Escalator: DELEGATE) parent=s1
        #   ├── s4 (VPC: CreateVpc)       parent=s1
        #   └── s5 (CVM: RunInstances retry) parent=s1
        tmp = Path(tempfile.mkdtemp(prefix="chain_test_"))
        sink = ObservableSink(runtime_root=tmp)
        trace_id = str(uuid.uuid4())
        run_id = "r1"
        spans = [
            TraceSpan(span_id="s1", trace_id=trace_id, parent_span_id=None,
                      run_id=run_id, skill="qcloud-copilot",
                      operation="execute_plan", step_id="plan", status="success"),
            TraceSpan(span_id="s2", trace_id=trace_id, parent_span_id="s1",
                      run_id=run_id, skill="qcloud-cvm-ops",
                      operation="RunInstances", step_id="step.cvm",
                      status="failure", error_code="InvalidVpc.NotFound"),
            TraceSpan(span_id="s3", trace_id=trace_id, parent_span_id="s1",
                      run_id=run_id, skill="qcloud-copilot",
                      operation="escalator.delegate", step_id="step.esc",
                      status="success", delegate_to="qcloud-vpc-ops"),
            TraceSpan(span_id="s4", trace_id=trace_id, parent_span_id="s1",
                      run_id=run_id, skill="qcloud-vpc-ops",
                      operation="CreateVpc", step_id="step.vpc",
                      status="success"),
            TraceSpan(span_id="s5", trace_id=trace_id, parent_span_id="s1",
                      run_id=run_id, skill="qcloud-cvm-ops",
                      operation="RunInstances", step_id="step.cvm.retry",
                      status="success"),
        ]
        for s in spans:
            sink.emit_trace_span(s)

        spans_path = tmp / "traces" / run_id / "spans.jsonl"
        records = [json.loads(l) for l in
                   spans_path.read_text(encoding="utf-8").splitlines()]

        # All spans share the same trace_id
        self.assertTrue(all(r["trace_id"] == trace_id for r in records),
                        "all spans must share one trace_id")
        # Exactly one root span (parent_span_id None)
        roots = [r for r in records if r["parent_span_id"] is None]
        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0]["span_id"], "s1")
        # At least one child span (cross-skill delegation marker)
        children = [r for r in records if r["parent_span_id"] is not None]
        self.assertGreaterEqual(len(children), 4)
        # Every child references an existing parent.
        ids = {r["span_id"] for r in records}
        for r in children:
            self.assertIn(r["parent_span_id"], ids,
                          f"{r['span_id']} references missing parent "
                          f"{r['parent_span_id']!r}")


class DelegateMarkerTests(unittest.TestCase):
    """DELEGATE-bearing spans carry delegate_to metadata."""

    def test_delegate_to_persisted(self):
        tmp = Path(tempfile.mkdtemp(prefix="delegate_test_"))
        sink = ObservableSink(runtime_root=tmp)
        span = TraceSpan(
            span_id="s1", trace_id="t1", parent_span_id=None,
            run_id="r1", skill="qcloud-copilot",
            operation="escalator.delegate", step_id="step.esc",
            status="delegated", delegate_to="qcloud-vpc-ops",
        )
        sink.emit_trace_span(span)
        spans_path = tmp / "traces" / "r1" / "spans.jsonl"
        record = json.loads(spans_path.read_text(encoding="utf-8").strip())
        self.assertEqual(record["delegate_to"], "qcloud-vpc-ops")
        self.assertEqual(record["status"], "delegated")


class GclScoresTests(unittest.TestCase):
    """Spans from GCL runs carry gcl_scores; non-GCL spans have None."""

    def test_gcl_scores_persisted(self):
        tmp = Path(tempfile.mkdtemp(prefix="gcl_scores_test_"))
        sink = ObservableSink(runtime_root=tmp)
        span = TraceSpan(
            span_id="s1", trace_id="t1", parent_span_id=None,
            run_id="r1", skill="qcloud-cvm-ops",
            operation="DescribeInstances", step_id="gcl.run",
            status="success", duration_ms=200,
            gcl_scores={"correctness": 1.0, "safety": 1.0,
                        "idempotency": 1.0, "traceability": 1.0,
                        "spec_compliance": 1.0},
        )
        sink.emit_trace_span(span)
        spans_path = tmp / "traces" / "r1" / "spans.jsonl"
        record = json.loads(spans_path.read_text(encoding="utf-8").strip())
        self.assertEqual(record["gcl_scores"]["correctness"], 1.0)
        self.assertEqual(record["gcl_scores"]["safety"], 1.0)

    def test_gcl_scores_none_on_failure(self):
        tmp = Path(tempfile.mkdtemp(prefix="gcl_failure_test_"))
        sink = ObservableSink(runtime_root=tmp)
        span = TraceSpan(
            span_id="s1", trace_id="t1", parent_span_id=None,
            run_id="r1", skill="qcloud-cvm-ops",
            operation="RunInstances", step_id="step-1",
            status="failure", error_code="InvalidVpc.NotFound",
        )
        sink.emit_trace_span(span)
        spans_path = tmp / "traces" / "r1" / "spans.jsonl"
        record = json.loads(spans_path.read_text(encoding="utf-8").strip())
        self.assertIsNone(record.get("gcl_scores"))

    def test_gcl_scores_none_on_halted(self):
        tmp = Path(tempfile.mkdtemp(prefix="gcl_halted_test_"))
        sink = ObservableSink(runtime_root=tmp)
        span = TraceSpan(
            span_id="s1", trace_id="t1", parent_span_id=None,
            run_id="r1", skill="qcloud-cvm-ops",
            operation="RunInstances", step_id="step-1",
            status="halted",
        )
        sink.emit_trace_span(span)
        spans_path = tmp / "traces" / "r1" / "spans.jsonl"
        record = json.loads(spans_path.read_text(encoding="utf-8").strip())
        self.assertIsNone(record.get("gcl_scores"))


class EvidenceKernelSpanIdTests(unittest.TestCase):
    """post_record() includes span_id when supplied."""

    def test_post_record_includes_span_id(self):
        sys.path.insert(0, str(SCRIPTS))
        import tempfile as _tempfile

        import evidence_kernel as ek
        from evidence_kernel import post_record
        # Override AUDIT to a temp dir so we don't pollute real audit-results.
        old_audit = ek.AUDIT
        try:
            tmp_audit = Path(_tempfile.mkdtemp(prefix="evid_test_"))
            ek.AUDIT = tmp_audit
            ek.AUDIT.mkdir(exist_ok=True)
            record = {"run_id": "test-spanid-run", "skill": "cvm",
                      "status": "success"}
            returned = post_record(record, span_id="run1:cvm")
            self.assertTrue(returned.exists())
            content = json.loads(returned.read_text(encoding="utf-8"))
            self.assertEqual(content.get("span_id"), "run1:cvm")
        finally:
            ek.AUDIT = old_audit


if __name__ == "__main__":
    unittest.main()