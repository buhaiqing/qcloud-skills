# Copyright (c) 2026. All rights reserved.
"""Cross-skill orchestration — automatic pattern selection.

Per ADR-0005 §2.3. Models the five orchestration patterns from
cross-skill-orchestration.md (F1, F2, P1, A1, A2) and selects
the best match based on Blackboard state.

Patterns:
  F1: FinOps HIGH anomaly → Proactive Inspection → AIOps RCA
  F2: FinOps + AIOps joint diagnosis
  P1: Inspection CRITICAL finding → AIOps validate/deepen
  A1: Post-incident → generate prevention items
  A2: RCA capacity signal → FinOps cost advisory
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TriggerCondition:
    """A single trigger condition for an orchestration pattern.

    expression is evaluated against Blackboard state:
        "blackboard.finops.anomaly_level == 'HIGH'"
    """

    expression: str


@dataclass
class OrchestrationPattern:
    """A named cross-skill orchestration pattern."""

    name: str  # "F1" | "F2" | "P1" | "A1" | "A2"
    description: str
    trigger_conditions: list[TriggerCondition] = field(default_factory=list)
    skill_chain: list[str] = field(default_factory=list)
    handoff_schema: str | None = None  # path to JSON Schema for context passing
    fallback_pattern: str | None = None  # name of fallback pattern on failure


# Canonical pattern definitions
PATTERNS: dict[str, OrchestrationPattern] = {
    "F1": OrchestrationPattern(
        name="F1",
        description="FinOps HIGH anomaly → Proactive Inspection → AIOps RCA",
        trigger_conditions=[
            TriggerCondition("blackboard.finops.anomaly_level == 'HIGH'"),
            TriggerCondition("blackboard.finops.resource_cpu > 80"),
        ],
        skill_chain=["qcloud-proactive-inspection", "qcloud-aiops-diagnosis"],
        handoff_schema="qcloud-aiops-diagnosis/assets/finops-handoff.schema.json",
        fallback_pattern="A1",
    ),
    "F2": OrchestrationPattern(
        name="F2",
        description="FinOps + AIOps joint diagnosis",
        trigger_conditions=[
            TriggerCondition("blackboard.finops.anomaly_level in ('MEDIUM', 'HIGH')"),
        ],
        skill_chain=["qcloud-aiops-diagnosis"],
        handoff_schema="qcloud-aiops-diagnosis/assets/finops-handoff.schema.json",
        fallback_pattern="A1",
    ),
    "P1": OrchestrationPattern(
        name="P1",
        description="Inspection CRITICAL finding → AIOps validate/deepen",
        trigger_conditions=[
            TriggerCondition("blackboard.inspection.severity == 'CRITICAL'"),
            TriggerCondition("blackboard.inspection.category == 'security'"),
        ],
        skill_chain=["qcloud-aiops-diagnosis"],
        handoff_schema="qcloud-aiops-diagnosis/assets/inspection-handoff.schema.json",
        fallback_pattern="A2",
    ),
    "A1": OrchestrationPattern(
        name="A1",
        description="Post-incident → generate prevention items for next inspection cycle",
        trigger_conditions=[],
        skill_chain=["qcloud-proactive-inspection"],
        fallback_pattern=None,
    ),
    "A2": OrchestrationPattern(
        name="A2",
        description="RCA capacity signal → FinOps cost advisory",
        trigger_conditions=[
            TriggerCondition("blackboard.aiops.capacity_risk == 'HIGH'"),
        ],
        skill_chain=["qcloud-finops-ops"],
        fallback_pattern=None,
    ),
}


__all__ = ["PATTERNS", "OrchestrationPattern", "TriggerCondition"]
