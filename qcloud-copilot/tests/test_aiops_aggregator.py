"""P2.9.a — aggregate_aiops_summary(): build AIOpsSummary from observation list.

Inputs: list of ObservationRecord (already joined by trace_id).
Outputs: AIOpsSummary dataclass.

Rules:
  - severity from `metadata["severity"]`, worst wins
  - signals / evidence derived from `metadata["signals"|"evidence"]`
  - rca / impact / response derived from observation output["rca"|"impact"|"response"]
  - quality = count(success) / count(total)
  - empty input -> empty AIOpsSummary with quality=0.0
  - operation is idempotent (same input -> same output)
"""

from __future__ import annotations

from typing import Optional


def _mk_obs(
    obs_id: str,
    *,
    status: str = "success",
    obs_type: str = "SPAN",
    signals: Optional[list[str]] = None,
    evidence: Optional[list[str]] = None,
    metadata: Optional[dict] = None,
    output: Optional[dict] = None,
):
    from copilot.trace_records import ObservationRecord, ObservationType

    md = dict(metadata or {})
    if signals is not None:
        md["signals"] = list(signals)
    if evidence is not None:
        md["evidence"] = list(evidence)
    return ObservationRecord(
        id=obs_id,
        trace_id="trc-aiaggr",
        type=ObservationType(obs_type),
        name=obs_id,
        status=status,
        metadata=md,
        output=output or {},
    )


def test_aggregate_aiops_empty():
    from copilot.summary_aggregator import aggregate_aiops_summary

    summary = aggregate_aiops_summary([], trace_id="trc-empty")
    assert summary.incident_id == "trc-empty"
    assert summary.severity is None
    assert summary.signals == []
    assert summary.evidence == []
    assert summary.topology == []
    assert summary.rca is None
    assert summary.impact is None
    assert summary.response is None
    assert summary.quality == 0.0


def test_aggregate_aiops_quality_basic():
    from copilot.summary_aggregator import aggregate_aiops_summary

    obs_list = [
        _mk_obs("a", status="success"),
        _mk_obs("b", status="success"),
        _mk_obs("c", status="error"),
    ]
    summary = aggregate_aiops_summary(obs_list, trace_id="trc-q")
    assert abs(summary.quality - (2 / 3)) < 0.001


def test_aggregate_aiops_quality_full_success():
    from copilot.summary_aggregator import aggregate_aiops_summary

    obs_list = [_mk_obs(f"ok-{i}", status="success") for i in range(5)]
    summary = aggregate_aiops_summary(obs_list, trace_id="t")
    assert summary.quality == 1.0


def test_aggregate_aiops_quality_all_error():
    from copilot.summary_aggregator import aggregate_aiops_summary

    obs_list = [_mk_obs(f"e-{i}", status="error") for i in range(3)]
    summary = aggregate_aiops_summary(obs_list, trace_id="t")
    assert summary.quality == 0.0


def test_aggregate_aiops_signals_collected():
    from copilot.summary_aggregator import aggregate_aiops_summary

    obs_list = [
        _mk_obs("a", signals=["cpu", "memory"], evidence=["vm-1", "vm-2"]),
        _mk_obs("b", signals=["disk-io"], evidence=["clb-1"]),
    ]
    summary = aggregate_aiops_summary(obs_list, trace_id="t")
    assert "cpu" in summary.signals
    assert "disk-io" in summary.signals
    assert "vm-1" in summary.evidence
    assert "clb-1" in summary.evidence


def test_aggregate_aiops_rca_impact_response():
    from copilot.summary_aggregator import aggregate_aiops_summary

    obs_list = [
        _mk_obs(
            "rca-1",
            output={"rca": "network-congestion", "impact": "10% requests delayed", "response": "scale-up"},
        ),
        _mk_obs(
            "rca-2",
            output={"rca": "memory-leak", "impact": "OOM on vm-2", "response": "restart"},
        ),
    ]
    summary = aggregate_aiops_summary(obs_list, trace_id="t")
    assert "network-congestion" in (summary.rca or "")
    assert "memory-leak" in (summary.rca or "")
    assert "10% requests delayed" in (summary.impact or "")
    assert "OOM on vm-2" in (summary.impact or "")


def test_aggregate_aiops_topology_from_metadata():
    from copilot.summary_aggregator import aggregate_aiops_summary

    obs_list = [
        _mk_obs("t-1", metadata={"topology_nodes": ["vm-1", "vm-2"]}),
        _mk_obs("t-2", metadata={"topology_nodes": ["vm-2", "clb-1"]}),
    ]
    summary = aggregate_aiops_summary(obs_list, trace_id="t")
    assert set(summary.topology) == {"vm-1", "vm-2", "clb-1"}


def test_aggregate_aiops_idempotent():
    from copilot.summary_aggregator import aggregate_aiops_summary

    obs_list = [
        _mk_obs("x", status="success", signals=["a"]),
        _mk_obs("y", status="error", output={"rca": "boom"}),
    ]
    a1 = aggregate_aiops_summary(obs_list, trace_id="t")
    a2 = aggregate_aiops_summary(obs_list, trace_id="t")
    assert a1.to_dict() == a2.to_dict()


def test_aggregate_aiops_severity_from_metadata():
    from copilot.summary_aggregator import aggregate_aiops_summary

    obs_list = [
        _mk_obs("sev-1", metadata={"severity": "high"}),
        _mk_obs("sev-2", metadata={"severity": "critical"}),
    ]
    summary = aggregate_aiops_summary(obs_list, trace_id="t")
    assert summary.severity == "critical"


def test_aggregate_aiops_returns_dataclass_instance():
    from copilot.summary_aggregator import aggregate_aiops_summary
    from copilot.trace_records import AIOpsSummary

    summary = aggregate_aiops_summary([_mk_obs("a")], trace_id="t")
    assert isinstance(summary, AIOpsSummary)
