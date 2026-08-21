from __future__ import annotations

import json
from datetime import UTC
from pathlib import Path

import copilot.observ_query as oq
from copilot.observ import Metric, MetricKind, ObservableSink, Span


def _seed(tmp_path: Path) -> None:
    sink = ObservableSink(runtime_root=tmp_path / ".runtime")
    # skill qcloud-cvm-ops: 3 success + 1 fail
    for _ in range(3):
        sink.emit_span(Span(run_id="r1", step_id="qcloud-cvm-ops", status="success", duration_ms=100))
    sink.emit_span(Span(run_id="r1", step_id="qcloud-cvm-ops", status="fail", error_code="boom", duration_ms=500))
    # another op for top_failed
    sink.emit_span(Span(run_id="r2", step_id="qcloud-vpc-ops", status="fail", error_code="H", duration_ms=200))
    sink.emit_gate("r1", "l0", "fail", "unknown skill")
    sink.emit_gate("r1", "l0", "pass", "ok")
    sink.emit_gate("r2", "l3", "fail", "critical")


def test_skill_success_rate(tmp_path: Path, monkeypatch):
    _seed(tmp_path)
    monkeypatch.setattr(oq, "METRICS_JSONL", tmp_path / ".runtime" / "metrics" / "metrics.jsonl")
    # by_skill=False aggregates per step_id (legacy step-level semantics)
    rate = oq.skill_success_rate("qcloud-cvm-ops", by_skill=False)
    assert rate == 0.75


def test_copilot_overall_success_rate(tmp_path: Path, monkeypatch):
    _seed(tmp_path)
    monkeypatch.setattr(oq, "METRICS_JSONL", tmp_path / ".runtime" / "metrics" / "metrics.jsonl")
    # by_skill=True = global copilot success ratio:
    # _seed writes 5 spans (3 success + 2 fail) -> 3/5 = 0.6
    rate = oq.skill_success_rate("qcloud-copilot", by_skill=True)
    assert rate == 0.6


def test_p_latency(tmp_path: Path, monkeypatch):
    _seed(tmp_path)
    monkeypatch.setattr(oq, "METRICS_JSONL", tmp_path / ".runtime" / "metrics" / "metrics.jsonl")
    # durations for qcloud-cvm-ops: [100,100,100,500] -> p99 = 500
    assert oq.p_latency("qcloud-cvm-ops", p=99) == 500
    assert oq.p_latency("qcloud-cvm-ops", p=50) == 100


def test_gate_decision_rate(tmp_path: Path, monkeypatch):
    _seed(tmp_path)
    monkeypatch.setattr(oq, "METRICS_JSONL", tmp_path / ".runtime" / "metrics" / "metrics.jsonl")
    rate = oq.gate_decision_rate("l0")
    assert rate == {"fail": 0.5, "pass": 0.5}


def test_feedback_adoption_rate(tmp_path: Path, monkeypatch):
    sink = ObservableSink(runtime_root=tmp_path / ".runtime")
    for _ in range(3):
        sink.emit_metric(Metric(name="copilot_user_adopt", kind=MetricKind.COUNTER, value=1.0, tags={}))
    sink.emit_metric(Metric(name="copilot_report_override", kind=MetricKind.COUNTER, value=1.0, tags={}))
    monkeypatch.setattr(oq, "METRICS_JSONL", tmp_path / ".runtime" / "metrics" / "metrics.jsonl")

    assert oq.feedback_adoption_rate() == {"adopt_rate": 0.75, "override_rate": 0.25, "n": 4}
    # empty -> zeros, not div-by-zero
    monkeypatch.setattr(oq, "METRICS_JSONL", tmp_path / ".runtime" / "metrics" / "none.jsonl")
    assert oq.feedback_adoption_rate() == {"adopt_rate": 0.0, "override_rate": 0.0, "n": 0}


def test_top_failed_operations(tmp_path: Path, monkeypatch):
    _seed(tmp_path)
    monkeypatch.setattr(oq, "METRICS_JSONL", tmp_path / ".runtime" / "metrics" / "metrics.jsonl")
    top = oq.top_failed_operations()
    by_op = dict(top)
    assert by_op["qcloud-cvm-ops"] == 1
    assert by_op["qcloud-vpc-ops"] == 1


def test_top_failed_operations_excludes_gate_rejections(tmp_path: Path, monkeypatch):
    sink = ObservableSink(runtime_root=tmp_path / ".runtime")
    # gate rejection flows through record_health -> emit_span(source="gate")
    sink.emit_span(Span(run_id="r1", step_id="qcloud-copilot", status="fail", error_code="l0", source="gate"))
    # a real step failure
    sink.emit_span(Span(run_id="r1", step_id="qcloud-cvm-ops", status="fail", error_code="boom", source="step"))
    monkeypatch.setattr(oq, "METRICS_JSONL", tmp_path / ".runtime" / "metrics" / "metrics.jsonl")

    top = oq.top_failed_operations()
    by_op = dict(top)
    # gate rejections must NOT appear as failed operations
    assert "qcloud-copilot" not in by_op
    assert by_op["qcloud-cvm-ops"] == 1


def test_backward_compat_legacy_health(tmp_path: Path, monkeypatch):
    legacy = tmp_path / ".runtime" / "health" / "skill-metrics.jsonl"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime

    now = datetime.now(UTC).isoformat()
    rows = [
        {"ts": now, "skill": "qcloud-cdb-ops", "status": "ok", "duration_ms": 50, "trace_id": "x", "error_code": None},
        {"ts": now, "skill": "qcloud-cdb-ops", "status": "error", "duration_ms": 70, "trace_id": "x", "error_code": "boom"},
    ]
    legacy.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    monkeypatch.setattr(oq, "METRICS_JSONL", tmp_path / ".runtime" / "metrics" / "metrics.jsonl")
    monkeypatch.setattr(oq, "LEGACY_HEALTH_JSONL", legacy)
    assert oq.skill_success_rate("qcloud-cdb-ops", by_skill=False) == 0.5
    assert oq.p_latency("qcloud-cdb-ops", p=99) == 70
