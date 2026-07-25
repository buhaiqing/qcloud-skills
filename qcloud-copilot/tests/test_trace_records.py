"""TDD tests for trace_records.py — TRACE-1 v3 data model."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "qcloud-copilot"))

NOW = datetime.now(timezone.utc).isoformat()


@pytest.fixture
def minimal_trace() -> dict[str, Any]:
    return {
        "id": "trc-test-001",
        "name": "test-trace",
        "timestamp": NOW,
        "started_at": NOW,
        "ended_at": NOW,
        "status": "success",
        "input": {"type": "diagnose", "summary": "test"},
        "output": {"status": "success", "finding_count": 0},
        "user_id": None,
        "session_id": "ses-test-001",
        "release": None,
        "version": "1.0.0",
        "environment": "test",
        "tags": [],
        "metadata": {
            "trace_schema_version": "3.0",
            "tenant_id": None,
            "incident_id": None,
            "business_unit": None,
            "region": "ap-guangzhou",
            "products": [],
        },
        "aiops_summary": None,
        "finops_summary": None,
        "observation_refs": [],
        "usage_refs": [],
        "score_refs": [],
        "summary_version": None,
    }


@pytest.fixture
def minimal_observation() -> dict[str, Any]:
    return {
        "id": "obs-test-001",
        "trace_id": "trc-test-001",
        "parent_observation_id": None,
        "type": "SPAN",
        "name": "GetMonitorData",
        "start_time": NOW,
        "end_time": NOW,
        "status": "success",
        "input": {"action": "GetMonitorData", "parameters_hash": "sha256:test"},
        "output": {"request_id_hash": "sha256:test", "resource_count": 0},
        "version": "1.0.0",
        "metadata": {
            "skill_name": "qcloud-monitor-ops",
            "skill_version": "1.0.0",
            "provider": "tencent_cloud",
            "product": "monitor",
            "action": "GetMonitorData",
            "region": "ap-guangzhou",
            "client_type": "tccli",
            "operation_type": "read",
            "retry_index": 0,
        },
        "usage_refs": [],
        "score_refs": [],
        "error": None,
    }


def test_trace_has_no_span_fields(minimal_trace):
    from copilot.trace_records import TraceRecord
    trace = TraceRecord.from_dict(minimal_trace)
    assert not hasattr(trace, "span_id")
    assert not hasattr(trace, "parent_span_id")
    assert not hasattr(trace, "trace_type")


def test_trace_roundtrip(minimal_trace):
    from copilot.trace_records import TraceRecord
    trace = TraceRecord.from_dict(minimal_trace)
    data = trace.to_dict()
    assert data["id"] == minimal_trace["id"]
    assert data["metadata"]["trace_schema_version"] == "3.0"


def test_trace_serializes_null_identity_fields(minimal_trace):
    from copilot.trace_records import TraceRecord
    trace = TraceRecord.from_dict(minimal_trace)
    data = trace.to_dict()
    assert data["user_id"] is None
    json_str = json.dumps(data)
    assert '"user_id": null' in json_str
    assert '"user_id": "null"' not in json_str
    assert '"user_id": ""' not in json_str


def test_observation_has_trace_id(minimal_observation):
    from copilot.trace_records import ObservationRecord
    obs = ObservationRecord.from_dict(minimal_observation)
    assert obs.trace_id == "trc-test-001"


def test_observation_type_enum(minimal_observation):
    from copilot.trace_records import ObservationRecord, ObservationType
    obs = ObservationRecord.from_dict(minimal_observation)
    assert obs.type == ObservationType.SPAN


def test_usage_event_has_join_keys():
    from copilot.trace_records import UsageEvent
    ue = UsageEvent(
        id="use-test-001",
        trace_id="trc-test-001",
        observation_id="obs-test-001",
        event_type="llm",
        timestamp=NOW,
    )
    assert ue.trace_id == "trc-test-001"
    assert ue.observation_id == "obs-test-001"


def test_usage_event_json_roundtrip():
    from copilot.trace_records import UsageEvent
    ue = UsageEvent(
        id="use-test-001",
        trace_id="trc-test-001",
        observation_id="obs-test-001",
        event_type="llm",
        timestamp=NOW,
        usage={"input_tokens": 100, "output_tokens": 50},
    )
    data = ue.to_dict()
    assert data["usage"]["input_tokens"] == 100


def test_score_has_trace_ref():
    from copilot.trace_records import ScoreRecord
    score = ScoreRecord(
        id="score-test-001",
        trace_id="trc-test-001",
        observation_id="obs-test-001",
        score_type="rca_accuracy",
        value=0.85,
        timestamp=NOW,
    )
    assert score.trace_id == "trc-test-001"


def test_identity_tree_null_not_string():
    from copilot.trace_records import IdentityTree
    identity = IdentityTree()
    data = identity.to_dict()
    assert data["user_id"] is None
    json_str = json.dumps(data)
    assert '"user_id": null' in json_str
    assert '"user_id": "null"' not in json_str


def test_identity_tree_accepted_values():
    from copilot.trace_records import IdentityTree
    identity = IdentityTree(
        user_id="user-123",
        tenant_id="tenant-456",
        initiator_type="cli",
        identity_source="config",
        identity_confidence="declared",
    )
    data = identity.to_dict()
    assert data["user_id"] == "user-123"
    assert data["tenant_id"] == "tenant-456"
    assert data["initiator_type"] == "cli"


def test_cost_record_cost_status_enum():
    from copilot.trace_records import CostRecord, CostStatus
    cr = CostRecord(
        id="cost-test-001",
        trace_id="trc-test-001",
        usage_event_ids=["use-test-001"],
        cost_status=CostStatus.ACTUAL,
        total_cost=0.05,
        currency="CNY",
        pricing_snapshot_version="1.0",
    )
    assert cr.cost_status == CostStatus.ACTUAL
    assert cr.total_cost == 0.05


def test_cost_record_unknown_price_not_zero():
    from copilot.trace_records import CostRecord, CostStatus
    cr = CostRecord(
        id="cost-test-002",
        trace_id="trc-test-001",
        usage_event_ids=[],
        cost_status=CostStatus.UNPRICED,
        total_cost=0.0,
        currency="CNY",
        pricing_snapshot_version="1.0",
    )
    data = cr.to_dict()
    assert data["cost_status"] == CostStatus.UNPRICED.value


def test_legacy_gcl_to_observation():
    from copilot.trace_records import legacy_gcl_to_observation
    gcl_record = {
        "run_id": "gcl-run-001",
        "iteration": 1,
        "generator": "Generator",
        "critic": "DataQualityCritic",
        "safety_score": 0.9,
        "score": 0.75,
        "passed": True,
        "duration_ms": 1200,
        "timestamp": NOW,
    }
    obs = legacy_gcl_to_observation(gcl_record, "trc-test-001")
    assert obs.trace_id == "trc-test-001"
    assert obs.metadata["gcl_run_id"] == "gcl-run-001"
    assert obs.metadata["gcl_generator"] == "Generator"


def test_legacy_audit_to_observation():
    from copilot.trace_records import legacy_audit_to_observation
    audit_record = {
        "step_id": "cvm-1",
        "skill": "qcloud-cvm-ops",
        "status": "success",
        "duration_ms": 500,
        "timestamp": NOW,
    }
    obs = legacy_audit_to_observation(audit_record, "trc-test-001")
    assert obs.trace_id == "trc-test-001"
    assert obs.metadata["skill_name"] == "qcloud-cvm-ops"
    assert obs.status == "success"
