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

# ---------------------------------------------------------------------------
# P1.5: Trace aggregate root + Summary reference model
# ---------------------------------------------------------------------------


def test_trace_aggregate_root_no_span_fields():
    """TraceRecord must NOT have span_id, parent_span_id, or trace_type fields."""
    from copilot.trace_records import TraceRecord
    trace = TraceRecord(
        id="trc-test-p15",
        name="p1.5-test",
        timestamp=NOW,
        started_at=NOW,
        ended_at=NOW,
        status="success",
    )
    assert not hasattr(trace, "span_id")
    assert not hasattr(trace, "parent_span_id")
    assert not hasattr(trace, "trace_type")


def test_trace_aiops_summary_nested():
    """TraceRecord.aiops_summary must be an AIOpsSummary dataclass instance (not a raw dict)."""
    from copilot.trace_records import TraceRecord, AIOpsSummary
    trace = TraceRecord(
        id="trc-aiops-001",
        name="aiops-trace",
        timestamp=NOW,
        started_at=NOW,
        ended_at=NOW,
        status="success",
        aiops_summary=AIOpsSummary(
            incident_id="inc-001",
            severity="critical",
            signals=["high_cpu", "memory_pressure"],
            evidence=["log_entry_1", "metric_spike"],
            topology=["node-a", "node-b"],
            rca="root_cause_x",
            impact="service_degradation",
            response="restart_initiated",
            quality=0.95,
        ),
    )
    # aiops_summary is the typed dataclass, not a plain dict
    assert isinstance(trace.aiops_summary, AIOpsSummary)
    assert trace.aiops_summary.incident_id == "inc-001"
    assert trace.aiops_summary.severity == "critical"
    assert "high_cpu" in trace.aiops_summary.signals
    # Serialization roundtrip
    d = trace.to_dict()
    assert d["aiops_summary"]["incident_id"] == "inc-001"
    assert d["aiops_summary"]["severity"] == "critical"
    # Deserialization roundtrip
    restored = TraceRecord.from_dict(d)
    assert isinstance(restored.aiops_summary, AIOpsSummary)
    assert restored.aiops_summary.incident_id == "inc-001"


def test_trace_finops_summary_nested():
    """TraceRecord.finops_summary must be a FinOpsSummary dataclass instance (not a raw dict)."""
    from copilot.trace_records import TraceRecord, FinOpsSummary
    trace = TraceRecord(
        id="trc-finops-001",
        name="finops-trace",
        timestamp=NOW,
        started_at=NOW,
        ended_at=NOW,
        status="success",
        finops_summary=FinOpsSummary(
            usage_summary={"input_tokens": 1000, "output_tokens": 500},
            cost_summary={"total_cost": 0.05, "currency": "CNY"},
            allocation={"model": "gpt-4", "share": 1.0},
            value={"quality_score": 0.92, "efficiency": 0.88},
        ),
    )
    # finops_summary is the typed dataclass, not a plain dict
    assert isinstance(trace.finops_summary, FinOpsSummary)
    assert trace.finops_summary.usage_summary["input_tokens"] == 1000
    assert trace.finops_summary.cost_summary["total_cost"] == 0.05
    # Serialization roundtrip
    d = trace.to_dict()
    assert d["finops_summary"]["usage_summary"]["input_tokens"] == 1000
    # Deserialization roundtrip
    restored = TraceRecord.from_dict(d)
    assert isinstance(restored.finops_summary, FinOpsSummary)
    assert restored.finops_summary.usage_summary["input_tokens"] == 1000


def test_trace_observation_ids_foreign_key():
    """observation_ids is a list of observation record IDs (foreign keys)."""
    from copilot.trace_records import TraceRecord
    trace = TraceRecord(
        id="trc-fk-001",
        name="fk-test",
        timestamp=NOW,
        started_at=NOW,
        ended_at=NOW,
        status="success",
        observation_ids=["obs-001", "obs-002", "obs-003"],
    )
    assert trace.observation_ids == ["obs-001", "obs-002", "obs-003"]
    assert isinstance(trace.observation_ids, list)
    # roundtrip
    d = trace.to_dict()
    assert d["observation_ids"] == ["obs-001", "obs-002", "obs-003"]
    restored = TraceRecord.from_dict(d)
    assert restored.observation_ids == ["obs-001", "obs-002", "obs-003"]


def test_trace_summary_references_usable():
    """Summary references (observation_ids, usage_event_ids, score_ids) are usable for lookups."""
    from copilot.trace_records import TraceRecord
    trace = TraceRecord(
        id="trc-refs-001",
        name="refs-test",
        timestamp=NOW,
        started_at=NOW,
        ended_at=NOW,
        status="success",
        observation_ids=["obs-a", "obs-b"],
        usage_event_ids=["ue-x", "ue-y", "ue-z"],
        score_ids=["sc-1", "sc-2"],
    )
    # These fields exist and are accessible for JOIN-style lookups
    assert len(trace.observation_ids) == 2
    assert len(trace.usage_event_ids) == 3
    assert len(trace.score_ids) == 2
    # roundtrip
    d = trace.to_dict()
    restored = TraceRecord.from_dict(d)
    assert restored.observation_ids == ["obs-a", "obs-b"]
    assert restored.usage_event_ids == ["ue-x", "ue-y", "ue-z"]
    assert restored.score_ids == ["sc-1", "sc-2"]
# ---------------------------------------------------------------------------
# P1.3: Skill version / runtime写入 TraceRecord
# ---------------------------------------------------------------------------


def test_runtime_info_dataclass():
    """RuntimeInfo captures Python/ tccli/ SDK/ git version for traceability."""
    from copilot.trace_records import RuntimeInfo

    rt = RuntimeInfo(
        python_version="3.12.1",
        tccli_version="3.1.98.0",
        sdk_name="tencentcloud-sdk-python",
        sdk_version="3.1.598.0",
        git_commit="abcdef123456",
        deployment_version="release-1.2.3",
    )
    assert rt.python_version == "3.12.1"
    assert rt.tccli_version == "3.1.98.0"
    assert rt.sdk_name == "tencentcloud-sdk-python"
    assert rt.sdk_version == "3.1.598.0"
    assert rt.git_commit == "abcdef123456"
    assert rt.deployment_version == "release-1.2.3"
    # All fields nullable
    rt2 = RuntimeInfo()
    assert rt2.python_version is None
    assert rt2.tccli_version is None


def test_runtime_info_serialization_roundtrip():
    """RuntimeInfo must roundtrip through to_dict / from_dict."""
    from copilot.trace_records import RuntimeInfo

    rt = RuntimeInfo(
        python_version="3.12.1",
        git_commit="abc123",
        deployment_version="v2.0.0",
    )
    d = rt.to_dict()
    assert d["python_version"] == "3.12.1"
    assert d["git_commit"] == "abc123"
    assert d["deployment_version"] == "v2.0.0"
    # From dict
    restored = RuntimeInfo.from_dict(d)
    assert restored.python_version == "3.12.1"
    assert restored.git_commit == "abc123"


def test_skill_info_dataclass():
    """SkillInfo captures skill name/version/sha/references/prompt/rubric versions."""
    from copilot.trace_records import SkillInfo

    si = SkillInfo(
        name="qcloud-cvm-ops",
        version="2.5.0",
        source="workspace",
        skill_file_sha256="sha256:abc123",
        skill_commit="def456",
        references={
            "cli-usage": {"version": "1.0.0", "sha256": "sha256:ref1"},
        },
        prompt_version="rca-v2",
        rubric_version="v3",
    )
    assert si.name == "qcloud-cvm-ops"
    assert si.version == "2.5.0"
    assert si.source == "workspace"
    assert si.skill_file_sha256 == "sha256:abc123"
    assert si.skill_commit == "def456"
    assert si.references["cli-usage"]["version"] == "1.0.0"
    assert si.prompt_version == "rca-v2"
    assert si.rubric_version == "v3"
    # All fields nullable
    si2 = SkillInfo()
    assert si2.name is None
    assert si2.version is None
    assert si2.references is None


def test_skill_info_serialization_roundtrip():
    """SkillInfo must roundtrip through to_dict / from_dict."""
    from copilot.trace_records import SkillInfo

    si = SkillInfo(
        name="qcloud-monitor-ops",
        version="1.0.0",
        source="package",
    )
    d = si.to_dict()
    assert d["name"] == "qcloud-monitor-ops"
    assert d["version"] == "1.0.0"
    restored = SkillInfo.from_dict(d)
    assert restored.name == "qcloud-monitor-ops"
    assert restored.version == "1.0.0"


def test_trace_record_with_skill_and_runtime():
    """TraceRecord accepts optional skill and runtime fields."""
    from copilot.trace_records import TraceRecord, SkillInfo, RuntimeInfo

    trace = TraceRecord(
        id="trc-p13-001",
        name="p1.3-test",
        timestamp=NOW,
        started_at=NOW,
        ended_at=NOW,
        status="success",
        skill=SkillInfo(
            name="qcloud-aiops-diagnosis",
            version="2.5.2",
            source="workspace",
            skill_file_sha256="sha256:testhash",
            skill_commit="commitsha",
            references={"multi-source-rca": {"version": "1.4.0", "sha256": "sha256:ref1"}},
            prompt_version="aiops-rca-v2",
            rubric_version="v1",
        ),
        runtime=RuntimeInfo(
            python_version="3.12.1",
            tccli_version="3.1.98.0",
            git_commit="abcdef",
            deployment_version="release-1.2.3",
        ),
    )
    assert trace.skill is not None
    assert trace.skill.name == "qcloud-aiops-diagnosis"
    assert trace.skill.version == "2.5.2"
    assert trace.skill.skill_commit == "commitsha"
    assert trace.skill.references["multi-source-rca"]["version"] == "1.4.0"
    assert trace.runtime is not None
    assert trace.runtime.python_version == "3.12.1"
    assert trace.runtime.tccli_version == "3.1.98.0"
    assert trace.runtime.git_commit == "abcdef"


def test_trace_record_skill_runtime_roundtrip():
    """skill and runtime fields survive to_dict / from_dict roundtrip."""
    from copilot.trace_records import TraceRecord, SkillInfo, RuntimeInfo

    trace = TraceRecord(
        id="trc-p13-rt",
        name="roundtrip-test",
        timestamp=NOW,
        started_at=NOW,
        ended_at=NOW,
        status="success",
        skill=SkillInfo(name="qcloud-tke-ops", version="1.0.0", source="workspace"),
        runtime=RuntimeInfo(python_version="3.11.0", git_commit="xyz789"),
    )
    d = trace.to_dict()
    assert d["skill"]["name"] == "qcloud-tke-ops"
    assert d["skill"]["version"] == "1.0.0"
    assert d["runtime"]["python_version"] == "3.11.0"
    assert d["runtime"]["git_commit"] == "xyz789"
    # from_dict restores correctly
    restored = TraceRecord.from_dict(d)
    assert restored.skill.name == "qcloud-tke-ops"
    assert restored.skill.version == "1.0.0"
    assert restored.runtime.python_version == "3.11.0"
    assert restored.runtime.git_commit == "xyz789"


def test_trace_record_skill_null_by_default():
    """skill and runtime default to None when not provided."""
    from copilot.trace_records import TraceRecord

    trace = TraceRecord(
        id="trc-p13-none",
        name="null-skill-runtime",
        timestamp=NOW,
        started_at=NOW,
        ended_at=NOW,
        status="success",
    )
    assert trace.skill is None
    assert trace.runtime is None