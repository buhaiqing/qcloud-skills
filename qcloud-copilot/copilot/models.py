from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Sentinel for ask_default_on_timeout: distinguishes "planner never declared"
# (inherit env) from "planner set explicit value" (None or "first").
_ASK_DEFAULT_UNSET: Any = object()


class IntentType(str, Enum):
    DIAGNOSE = "diagnose"
    INSPECT = "inspect"
    CRUISE = "cruise"
    ACT = "act"
    COMPARE = "compare"
    REPORT = "report"
    UNKNOWN = "unknown"


@dataclass
class ParsedRequest:
    raw: str
    normalized: str
    entities: dict[str, list[str]] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class ClassifiedIntent:
    primary: IntentType
    targets: list[str]
    secondary: list[IntentType] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class AskOption:
    """One option in an ask_user plan step (BC-T1 schema 1.2)."""

    value: str
    label: str
    description: str = ""


@dataclass
class PlanStep:
    id: str
    type: str  # skill_call | cruise_run | alert_analyze | synthesize_report | report | ask_user
    skill: str | None = None
    operation: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    description: str = ""
    destructive: bool = False
    parallel_group: int = 0
    reads_from_blackboard: list[str] = field(default_factory=list)
    writes_to_blackboard: bool = False
    # ask_user dedicated fields (used when type == "ask_user", BC-T1 schema 1.2)
    ask_user_options: list[AskOption] = field(default_factory=list)
    ask_timeout_seconds: int = 60
    ask_user_context_key: str = "region"
    # Default sentinel distinguishing "planner never declared" from
    # "planner explicitly wants fail-fast". ask_user_runner.py reads this
    # via `is _ASK_DEFAULT_UNSET` to decide whether to consult the env.
    # Explicit values: "first" (auto-select first option), None (fail-fast).
    ask_default_on_timeout: str | None = _ASK_DEFAULT_UNSET  # type: ignore[assignment]


DEFAULT_DISPATCH_CONFIG: dict[str, Any] = {
    "max_parallel_groups": 1,
    "stop_on_first_critical": True,
    "human_review_on": ["verdict == CRITICAL"],
}


@dataclass
class ExecutionPlan:
    intent: ClassifiedIntent
    steps: list[PlanStep]
    context: dict[str, Any] = field(default_factory=dict)
    safety_level: int = 0
    plan_id: str | None = None
    dispatch_config: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_DISPATCH_CONFIG))


@dataclass
class StepResult:
    step_id: str
    status: str  # "success" | "failure" | "skipped" | "pending_confirmation"
    output: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: int = 0


@dataclass
class ExecutionResult:
    plan: ExecutionPlan
    step_results: list[StepResult]
    final_report: Report | None = None
    status: str = "completed"  # "completed" | "partial" | "aborted" | "awaiting_confirmation"
    safety_violations: list[str] = field(default_factory=list)


@dataclass
class ReportSection:
    title: str
    severity: str  # "critical" | "warning" | "info" | "success"
    findings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] | None = None


@dataclass
class Report:
    title: str
    summary: str
    sections: list[ReportSection] = field(default_factory=list)
    execution_trace: list[dict] = field(default_factory=list)
    duration_ms: int = 0
    report_path: str = ""
    summary_report_path: str = ""
    aggregated: bool = False
    customer: str = ""
    user_request: str = ""
    audience: str = "detailed"


@dataclass
class SessionState:
    session_id: str
    created_at: str
    history: list[dict] = field(default_factory=list)
    current_plan: ExecutionPlan | None = None
    context: dict[str, Any] = field(default_factory=dict)
