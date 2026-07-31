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
from datetime import UTC, datetime
from enum import Enum
from typing import Any


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


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

    user_id: str | None = None
    tenant_id: str | None = None
    customer_id: str | None = None
    operator_id: str | None = None
    service_account_id: str | None = None
    account_id_hash: str | None = None
    actor_type: str | None = None
    initiator_type: str | None = None
    identity_source: str | None = None
    identity_confidence: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AutomationTree:
    job_id: str | None = None
    schedule_id: str | None = None
    run_id: str | None = None
    agent_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Runtime / Skill version info (P1.3)
# ---------------------------------------------------------------------------


@dataclass
class RuntimeInfo:
    """Runtime environment version info for traceability (SPEC P1.3)."""

    python_version: str | None = None
    tccli_version: str | None = None
    sdk_name: str | None = None
    sdk_version: str | None = None
    git_commit: str | None = None
    deployment_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuntimeInfo:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SkillInfo:
    """Skill version info for traceability (SPEC P1.3)."""

    name: str | None = None
    version: str | None = None
    source: str | None = None
    skill_file_sha256: str | None = None
    skill_commit: str | None = None
    references: dict[str, Any] | None = None
    prompt_version: str | None = None
    rubric_version: str | None = None

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
    user_id: str | None = None  # JSON null when absent
    session_id: str | None = None
    release: str | None = None
    version: str | None = None
    environment: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    # Skill version info (P1.3)
    skill: SkillInfo | None = None
    # Runtime environment info (P1.3)
    runtime: RuntimeInfo | None = None
    # AIOps Summary (nested dataclass, not raw dict)
    aiops_summary: AIOpsSummary | None = None
    # FinOps Summary (nested dataclass, not raw dict)
    finops_summary: FinOpsSummary | None = None
    # Foreign keys
    observation_ids: list[str] = field(default_factory=list)
    usage_event_ids: list[str] = field(default_factory=list)
    score_ids: list[str] = field(default_factory=list)
    summary_version: str | None = None

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
    parent_observation_id: str | None = None
    type: ObservationType = ObservationType.SPAN
    name: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    status: str = "success"  # success|error|partial|skipped
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    usage_refs: list[str] = field(default_factory=list)
    score_refs: list[str] = field(default_factory=list)
    error: str | None = None

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
    observation_id: str | None = None
    # LLM
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    usage: dict[str, Any] | None = None
    # Cloud API
    product: str | None = None
    action: str | None = None
    region: str | None = None
    client_type: str | None = None
    api_request_id: str | None = None
    request_bytes: int | None = None
    response_bytes: int | None = None
    resource_count: int | None = None
    retry_index: int | None = None
    rate_limited: bool | None = None
    # Data read
    metric_points: int | None = None
    log_bytes: int | None = None
    log_records: int | None = None
    audit_events: int | None = None
    topology_nodes: int | None = None
    topology_edges: int | None = None
    # Common
    latency_ms: int | None = None
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
    observation_id: str | None = None
    model: str | None = None
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
    pricing_snapshot_version: str | None = None
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

    incident_id: str | None = None
    severity: str | None = None
    signals: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    topology: list[str] = field(default_factory=list)
    rca: str | None = None
    impact: str | None = None
    response: str | None = None
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
    incident_id: str | None = None
    severity: str | None = None
    lifecycle_state: str | None = None
    root_cause_confidence: str | None = None
    evidence_count: int = 0
    data_quality_status: str | None = None
    # FinOps
    usage_event_count: int = 0
    total_cost: float = 0.0
    currency: str = "CNY"
    cost_status: str | None = None
    priced_usage_ratio: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Legacy adapters
# ---------------------------------------------------------------------------


def legacy_gcl_to_observation(
    gcl_record: dict[str, Any], trace_id: str
) -> ObservationRecord:
    """Map GCL trace JSON to ObservationRecord (GENERATION type).

    v0 (no iteration / no rubric_version) and v1 (with rubric_version /
    model_version / latency_ms) both supported. Missing optional fields
    serialize as None (not '' or 'unknown').
    """
    generator = gcl_record.get("generator")
    critic = gcl_record.get("critic")
    return ObservationRecord(
        id=_new_id("obs"),
        trace_id=trace_id,
        type=ObservationType.GENERATION,
        name=f"gcl-{generator}" if generator else "gcl-unknown",
        status="success" if gcl_record.get("passed") else "error",
        start_time=gcl_record.get("timestamp", _utc_now()),
        end_time=gcl_record.get("timestamp", _utc_now()),
        metadata={
            "_from_legacy": True,
            "gcl_run_id": gcl_record.get("run_id"),
            "gcl_generator": generator,
            "gcl_critic": critic,
            "gcl_iteration": gcl_record.get("iteration"),
            "gcl_passed": gcl_record.get("passed"),
            "gcl_safety_score": gcl_record.get("safety_score"),
            "gcl_score": gcl_record.get("score"),
            "gcl_rubric_version": gcl_record.get("rubric_version"),
            "gcl_model_version": gcl_record.get("model_version"),
            "gcl_latency_ms": gcl_record.get("latency_ms"),
        },
        output=gcl_record.get("output") or {},
        input=gcl_record.get("prompt") or {},
        error=None if gcl_record.get("passed") else "gcl_failed",
    )


def legacy_audit_to_observation(
    audit_record: dict[str, Any], trace_id: str
) -> ObservationRecord:
    """Map Copilot audit JSON to ObservationRecord (SPAN type).

    Missing `skill` / `operation` / `region` / `step_id` map to None, never
    'unknown' sentinel strings.
    """
    skill = audit_record.get("skill")
    operation = audit_record.get("operation")
    region = audit_record.get("region")
    return ObservationRecord(
        id=_new_id("obs"),
        trace_id=trace_id,
        type=ObservationType.SPAN,
        name=skill or "audit-step",
        status=audit_record.get("status", "success"),
        start_time=audit_record.get("timestamp", _utc_now()),
        end_time=audit_record.get("timestamp", _utc_now()),
        metadata={
            "_from_legacy": True,
            "skill_name": skill,
            "operation_name": operation,
            "region": region,
            "step_id": audit_record.get("step_id"),
        },
        error=None if audit_record.get("status") == "success" else "audit_failed",
    )


# ---------------------------------------------------------------------------
# Attribution & Allocation (P3.3, P3.4)
# ---------------------------------------------------------------------------


@dataclass
class AttributionTree:
    """Fixed attribution shape; missing values must be None (JSON null)."""

    tenant_id: str | None = None
    customer_id: str | None = None
    account_id_hash: str | None = None
    business_unit: str | None = None
    cost_center: str | None = None
    region: str | None = None
    service: str | None = None
    environment: str | None = None
    product: str | None = None
    resource_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AttributionTree:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AllocationRecord:
    """Per-attribution-key share slice of a CostRecord (P3.4)."""

    cost_id: str
    attribution_key: tuple[str, str]  # (scope, value), e.g. ("tenant", "t1")
    share: float  # 0..1
    allocated_cost: float
    method: str  # direct|shared|resource|request|usage|equal_split
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> tuple[str, str]:
        return self.attribution_key

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["attribution_key"] = list(self.attribution_key)
        return d
