from __future__ import annotations

import json
from pathlib import Path

from copilot.observ import Metric, MetricKind, ObservableSink, Span


def _sink(tmp_path: Path) -> ObservableSink:
    return ObservableSink(runtime_root=tmp_path / ".runtime")


def test_emit_span_writes_run_index_preserving_order(tmp_path: Path):
    sink = _sink(tmp_path)
    run_id = "run-abc"
    for i in range(3):
        sink.emit_span(Span(run_id=run_id, step_id=f"step-{i}", status="success"))

    index_path = tmp_path / ".runtime" / "audit" / run_id / "_index.jsonl"
    assert index_path.is_file()
    records = [json.loads(line) for line in index_path.read_text().splitlines() if line]
    assert [r["step_id"] for r in records] == ["step-0", "step-1", "step-2"]


def test_emit_span_writes_prom_duration_line(tmp_path: Path):
    sink = _sink(tmp_path)
    sink.emit_span(Span(run_id="run-1", step_id="qcloud-cvm-ops", status="success", duration_ms=1234))

    prom = (tmp_path / ".runtime" / "metrics" / "metrics.prom").read_text()
    assert 'copilot_step_duration_ms{run_id="run-1",step_id="qcloud-cvm-ops",status="success"} 1234' in prom
    # success counts the copilot skill itself, not the individual step (spec O4)
    assert 'copilot_skill_success_total{skill="qcloud-copilot"} 1' in prom


def test_emit_gate_writes_counter_to_jsonl(tmp_path: Path):
    sink = _sink(tmp_path)
    sink.emit_gate("run-1", "l0", "fail", "unknown skill")

    jsonl = (tmp_path / ".runtime" / "metrics" / "metrics.jsonl").read_text()
    lines = [json.loads(line) for line in jsonl.splitlines() if line]
    gate_records = [r for r in lines if r.get("kind") == "gate"]
    assert gate_records
    assert gate_records[-1]["gate"] == "l0"
    assert gate_records[-1]["decision"] == "fail"

    prom = (tmp_path / ".runtime" / "metrics" / "metrics.prom").read_text()
    assert 'copilot_gate_decision_total{gate="l0",decision="fail"} 1' in prom


def test_emit_metric_writes_structured_record(tmp_path: Path):
    sink = _sink(tmp_path)
    sink.emit_metric(Metric(name="copilot_inflight", kind=MetricKind.GAUGE, value=2.0, tags={"skill": "x"}))

    jsonl = (tmp_path / ".runtime" / "metrics" / "metrics.jsonl").read_text()
    record = json.loads([line for line in jsonl.splitlines() if line][-1])
    assert record["name"] == "copilot_inflight"
    assert record["metric_kind"] == "gauge"
