"""TRACE-1 v3 data model: Trace, Observation, UsageEvent, Score, CostRecord.

Architecture:
  - Trace: aggregate root, no span_id/parent_span_id/trace_type
  - Observation: execution tree node (Skill/GCL/LLM/API/Verification)
  - UsageEvent: immutable usage facts (LLM tokens, API requests, data reads)
  - Score: feedback on RCA accuracy, data quality, verification results
  - CostRecord: cost result derived from UsageEvent + PricingSnapshot
  - IdentityTree: fixed identity shape; missing values serialize as JSON null

Legacy adapters:
  - legacy_gcl_to_observation(): GCL trace JSON → ObservationRecord
  - legacy_audit_to_observation(): Copilot audit JSON → ObservationRecord

Schema version: 3.0 (freeze per SPEC §14.7)
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ObservationType(str, Enum):
    SPAN = "SPAN"
    GENERATION = "GENERATION"
    EVENT = "EVENT"


class CostStatus(str, Enum):
    ACTUAL = "actual"
    ESTIMATED = "estimated"
    PARTIAL = "partial"
    UNPRICED = "unpriced"
    NOT_APPLICABLE = "not_applicable"


# ---------------------------------------------------------------------------
# Identity tree
# ---------------------------------------------------------------------------


@dataclass
class IdentityTree:
    """Fixed identity shape; missing values must be None (JSON null), never '' or 'unknown'."""

    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    customer_id: Optional[str] = None
    operator_id: Optional[str] = None
    service_account_id: Optional[str] = None
    account_id_hash: Optional[str] = None
    actor_type: Optional[str] = None
    initiator_type: Optional[str] = None
    identity_source: Optional[str] = None
    identity_confidence: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AutomationTree:
    job_id: Optional[str] = None
    schedule_id: Optional[str] = None
    run_id: Optional[str] = None
    agent_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Runtime / Skill version info (P1.3)
# ---------------------------------------------------------------------------


@dataclass
class RuntimeInfo:
    """Runtime environment version info for traceability (SPEC P1.3)."""

    python_version: Optional[str] = None
    tccli_version: Optional[str] = None
    sdk_name: Optional[str] = None
    sdk_version: Optional[str] = None
    git_commit: Optional[str] = None
    deployment_version: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuntimeInfo:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SkillInfo:
    """Skill version info for traceability (SPEC P1.3)."""

    name: Optional[str] = None
    version: Optional[str] = None
    source: Optional[str] = None
    skill_file_sha256: Optional[str] = None
    skill_commit: Optional[str] = None
    references: Optional[dict[str, Any]] = None
    prompt_version: Optional[str] = None
    rubric_version: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillInfo:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Trace aggregate root
# ---------------------------------------------------------------------------


@dataclass
class TraceRecord:
    """Trace aggregate root (SPEC §14.4). No span_id/parent_span_id/trace_type fields."""

    id: str
    name: str
    timestamp: str
    started_at: str
    ended_at: str
    status: str  # success|error|partial
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None  # JSON null when absent
    session_id: Optional[str] = None
    release: Optional[str] = None
    version: Optional[str] = None
    environment: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    # Skill version info (P1.3)
    skill: Optional[SkillInfo] = None
    # Runtime environment info (P1.3)
    runtime: Optional[RuntimeInfo] = None
    # AIOps Summary (nested dataclass, not raw dict)
    aiops_summary: Optional[AIOpsSummary] = None
    # FinOps Summary (nested dataclass, not raw dict)
    finops_summary: Optional[FinOpsSummary] = None
    # Foreign keys
    observation_ids: list[str] = field(default_factory=list)
    usage_event_ids: list[str] = field(default_factory=list)
    score_ids: list[str] = field(default_factory=list)
    summary_version: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TraceRecord:
        known = {
            k: v
            for k, v in data.items()
            if k
            in {
                "id",
                "name",
                "timestamp",
                "started_at",
                "ended_at",
                "status",
                "input",
                "output",
                "user_id",
                "session_id",
                "release",
                "version",
                "environment",
                "tags",
                "metadata",
                "observation_ids",
                "usage_event_ids",
                "score_ids",
                "summary_version",
            }
        }
        # Deserialize nested dataclasses
        if "aiops_summary" in data and data["aiops_summary"] is not None:
            known["aiops_summary"] = AIOpsSummary(**data["aiops_summary"])
        if "finops_summary" in data and data["finops_summary"] is not None:
            known["finops_summary"] = FinOpsSummary(**data["finops_summary"])
        if "skill" in data and data["skill"] is not None:
            known["skill"] = SkillInfo(**data["skill"])
        if "runtime" in data and data["runtime"] is not None:
            known["runtime"] = RuntimeInfo(**data["runtime"])
        return cls(**known)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Serialize nested dataclasses to plain dicts
        for field_name, cls_type in [
            ("aiops_summary", AIOpsSummary),
            ("finops_summary", FinOpsSummary),
            ("skill", SkillInfo),
            ("runtime", RuntimeInfo),
        ]:
            val = getattr(self, field_name, None)
            if val is not None:
                d[field_name] = val.to_dict() if hasattr(val, "to_dict") else val
        return d


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------


@dataclass
class ObservationRecord:
    """Execution tree node (SPEC §14.5)."""

    id: str
    trace_id: str
    parent_observation_id: Optional[str] = None
    type: ObservationType = ObservationType.SPAN
    name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: str = "success"  # success|error|partial|skipped
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    version: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    usage_refs: list[str] = field(default_factory=list)
    score_refs: list[str] = field(default_factory=list)
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ObservationRecord:
        obs_type = data.get("type", "SPAN")
        if isinstance(obs_type, str):
            obs_type = ObservationType(obs_type)
        known = {
            k: v
            for k, v in data.items()
            if k
            in {
                "id",
                "trace_id",
                "parent_observation_id",
                "type",
                "name",
                "start_time",
                "end_time",
                "status",
                "input",
                "output",
                "version",
                "metadata",
                "usage_refs",
                "score_refs",
                "error",
            }
        }
        known["type"] = obs_type
        return cls(**known)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["type"] = self.type.value
        return d


# ---------------------------------------------------------------------------
# UsageEvent
# ---------------------------------------------------------------------------


@dataclass
class UsageEvent:
    """Immutable usage fact (SPEC §5.2–5.4). Joinable by trace_id + observation_id."""

    id: str
    trace_id: str
    event_type: str  # llm|cloud_api|data
    timestamp: str
    observation_id: Optional[str] = None
    # LLM
    provider: Optional[str] = None
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    usage: Optional[dict[str, Any]] = None
    # Cloud API
    product: Optional[str] = None
    action: Optional[str] = None
    region: Optional[str] = None
    client_type: Optional[str] = None
    api_request_id: Optional[str] = None
    request_bytes: Optional[int] = None
    response_bytes: Optional[int] = None
    resource_count: Optional[int] = None
    retry_index: Optional[int] = None
    rate_limited: Optional[bool] = None
    # Data read
    metric_points: Optional[int] = None
    log_bytes: Optional[int] = None
    log_records: Optional[int] = None
    audit_events: Optional[int] = None
    topology_nodes: Optional[int] = None
    topology_edges: Optional[int] = None
    # Common
    latency_ms: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------


@dataclass
class ScoreRecord:
    """Feedback on RCA accuracy, data quality, verification results."""

    id: str
    trace_id: str
    score_type: str  # rca_accuracy|data_quality|verification_result|...
    value: float
    timestamp: str
    observation_id: Optional[str] = None
    model: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# CostRecord
# ---------------------------------------------------------------------------


@dataclass
class CostRecord:
    """Cost result derived from UsageEvent + PricingSnapshot (SPEC §5.5)."""

    id: str
    trace_id: str
    usage_event_ids: list[str]
    cost_status: CostStatus = CostStatus.UNPRICED
    total_cost: float = 0.0
    currency: str = "CNY"
    pricing_snapshot_version: Optional[str] = None
    allocation_keys: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["cost_status"] = self.cost_status.value
        return d


# ---------------------------------------------------------------------------
# PricingSnapshot
# ---------------------------------------------------------------------------


@dataclass
class PricingSnapshot:
    """Price version snapshot; UsageEvent is immutable, cost is recomputable."""

    version: str
    timestamp: str
    prices: dict[str, float] = field(default_factory=dict)  # key → price per unit

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

# ---------------------------------------------------------------------------
# AIOps Summary (SPEC §20)
# ---------------------------------------------------------------------------


@dataclass
class AIOpsSummary:
    """AIOps summary fields embedded in TraceRecord (SPEC §20)."""

    incident_id: Optional[str] = None
    severity: Optional[str] = None
    signals: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    topology: list[str] = field(default_factory=list)
    rca: Optional[str] = None
    impact: Optional[str] = None
    response: Optional[str] = None
    quality: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# FinOps Summary (SPEC §21)
# ---------------------------------------------------------------------------


@dataclass
class FinOpsSummary:
    """FinOps summary fields embedded in TraceRecord (SPEC §21)."""

    usage_summary: dict[str, Any] = field(default_factory=dict)
    cost_summary: dict[str, Any] = field(default_factory=dict)
    allocation: dict[str, Any] = field(default_factory=dict)
    value: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

# ---------------------------------------------------------------------------
# Summary (rebuilt from Observation/UsageEvent/Score, not a source of truth)
# ---------------------------------------------------------------------------


@dataclass
class SummaryRecord:
    """Rebuildable AIOps/FinOps summary (SPEC §14.6)."""

    trace_id: str
    version: str = "1.0"
    # AIOps
    incident_id: Optional[str] = None
    severity: Optional[str] = None
    lifecycle_state: Optional[str] = None
    root_cause_confidence: Optional[str] = None
    evidence_count: int = 0
    data_quality_status: Optional[str] = None
    # FinOps
    usage_event_count: int = 0
    total_cost: float = 0.0
    currency: str = "CNY"
    cost_status: Optional[str] = None
    priced_usage_ratio: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Legacy adapters
# ---------------------------------------------------------------------------


def legacy_gcl_to_observation(
    gcl_record: dict[str, Any], trace_id: str
) -> ObservationRecord:
    """Map GCL trace v1 JSON to ObservationRecord (GENERATION type)."""
    return ObservationRecord(
        id=_new_id("obs"),
        trace_id=trace_id,
        type=ObservationType.GENERATION,
        name=f"gcl-{gcl_record.get('generator', 'unknown')}",
        status="success" if gcl_record.get("passed") else "error",
        start_time=gcl_record.get("timestamp", _utc_now()),
        end_time=gcl_record.get("timestamp", _utc_now()),
        metadata={
            "gcl_run_id": gcl_record.get("run_id"),
            "gcl_generator": gcl_record.get("generator"),
            "gcl_critic": gcl_record.get("critic"),
            "gcl_iteration": gcl_record.get("iteration"),
            "gcl_safety_score": gcl_record.get("safety_score"),
            "gcl_score": gcl_record.get("score"),
        },
        error=None if gcl_record.get("passed") else "gcl_failed",
    )


def legacy_audit_to_observation(
    audit_record: dict[str, Any], trace_id: str
) -> ObservationRecord:
    """Map Copilot audit JSON to ObservationRecord (SPAN type)."""
    skill = audit_record.get("skill", "unknown")
    return ObservationRecord(
        id=_new_id("obs"),
        trace_id=trace_id,
        type=ObservationType.SPAN,
        name=skill,
        status=audit_record.get("status", "success"),
        start_time=audit_record.get("timestamp", _utc_now()),
        end_time=audit_record.get("timestamp", _utc_now()),
        metadata={
            "skill_name": skill,
            "audit_step_id": audit_record.get("step_id"),
        },
        error=None if audit_record.get("status") == "success" else "audit_failed",
    )
