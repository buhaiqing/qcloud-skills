from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from copilot.models import (
    AskOption,
    ClassifiedIntent,
    DEFAULT_DISPATCH_CONFIG,
    ExecutionPlan,
    IntentType,
    PlanStep,
    _ASK_DEFAULT_UNSET,
)

# Plan-fixture JSON cannot represent Python's `object()` sentinel, so we
# encode it as the string sentinel below. The PlanStep default for the field
# is _ASK_DEFAULT_UNSET; an absent / sentinel string maps back; explicit JSON
# null maps to None (fail-fast); explicit strings map to their lowercase form.
_JSON_UNSET_SENTINEL = "__unset__"


class PlanValidationError(ValueError):
    """Raised when plan structure or dependencies are invalid."""


def _decode_ask_default_on_timeout(raw: Any) -> Any:
    """Translate a plan-fixture ask_default_on_timeout value into the
    in-memory Python representation.

    Mapping table (JSON → Python):
      absent key         → _ASK_DEFAULT_UNSET (inherit env)
      "__unset__" string → _ASK_DEFAULT_UNSET (inherit env, explicit)
      JSON null          → None (fail-fast)
      "first" / "never"  → "first" / "never" (lowercased)
      "" / whitespace    → _ASK_DEFAULT_UNSET (defensive)
      other types        → _ASK_DEFAULT_UNSET (defensive)
    """
    if raw is None:
        # JSON null IS representable in JSON, so we honor it as fail-fast.
        return None
    if raw == _JSON_UNSET_SENTINEL:
        return _ASK_DEFAULT_UNSET
    if isinstance(raw, str):
        return raw.strip().lower() or _ASK_DEFAULT_UNSET
    return _ASK_DEFAULT_UNSET


def _safe_int(raw: Any, *, default: int) -> int:
    """Coerce to int, falling back to ``default`` on TypeError/ValueError.

    A corrupted plan fixture should not crash the loader; downstream code
    treats the default as a sane bound (parallel_group=0, timeout=60s).
    """
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def plan_step_from_dict(data: dict[str, Any]) -> PlanStep:
    params = dict(data.get("params") or {})
    operation = data.get("operation") or params.get("operation", "")
    if operation and "operation" not in params:
        params["operation"] = operation

    # ask_user fields (BC-T1) — omitted fields fall back to PlanStep defaults.
    ask_options_data = data.get("ask_user_options") or []
    ask_options = [
        AskOption(
            value=str(opt.get("value", "")),
            label=str(opt.get("label", opt.get("value", ""))),
            description=opt.get("description"),
        )
        for opt in ask_options_data
        if isinstance(opt, dict) and opt.get("value")
    ]

    default_on_timeout: Any
    if "ask_default_on_timeout" in data:
        default_on_timeout = _decode_ask_default_on_timeout(data.get("ask_default_on_timeout"))
    else:
        default_on_timeout = _ASK_DEFAULT_UNSET

    return PlanStep(
        id=data["id"],
        type=data["type"],
        skill=data.get("skill"),
        operation=operation,
        params=params,
        depends_on=list(data.get("depends_on") or []),
        description=data.get("description", ""),
        destructive=bool(data.get("destructive", False)),
        parallel_group=_safe_int(data.get("parallel_group"), default=0),
        reads_from_blackboard=list(data.get("reads_from_blackboard") or []),
        writes_to_blackboard=bool(data.get("writes_to_blackboard", False)),
        ask_user_options=ask_options,
        ask_timeout_seconds=_safe_int(data.get("ask_timeout_seconds"), default=60),
        ask_user_context_key=data.get("ask_user_context_key", "region"),
        ask_default_on_timeout=default_on_timeout,
    )


def execution_plan_from_dict(
    data: dict[str, Any],
    intent: ClassifiedIntent | None = None,
) -> ExecutionPlan:
    steps = [plan_step_from_dict(s) for s in data.get("steps", [])]
    dispatch_config = dict(DEFAULT_DISPATCH_CONFIG)
    dispatch_config.update(data.get("dispatch_config") or {})
    return ExecutionPlan(
        intent=intent
        or ClassifiedIntent(primary=IntentType.REPORT, targets=[], secondary=[IntentType.CRUISE]),
        steps=steps,
        context=dict(data.get("context") or {}),
        safety_level=_safe_int(data.get("safety_level"), default=0),
        plan_id=data.get("plan_id"),
        dispatch_config=dispatch_config,
    )


def load_plan_file(path: str | Path) -> ExecutionPlan:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    plan = execution_plan_from_dict(data)
    validate_execution_plan(plan)
    return plan


def validate_execution_plan(plan: ExecutionPlan) -> None:
    step_ids = {step.id for step in plan.steps}
    if len(step_ids) != len(plan.steps):
        raise PlanValidationError("duplicate step ids in plan")

    for step in plan.steps:
        for dep in step.depends_on:
            if dep not in step_ids:
                raise PlanValidationError(f"step {step.id} depends on missing step {dep}")

    _assert_acyclic(plan)


def _assert_acyclic(plan: ExecutionPlan) -> None:
    deps = {step.id: step.depends_on for step in plan.steps}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise PlanValidationError(f"dependency cycle detected at {node}")
        if node in visited:
            return
        visiting.add(node)
        for dep in deps.get(node, []):
            visit(dep)
        visiting.remove(node)
        visited.add(node)

    for step_id in deps:
        visit(step_id)


def resolve_blackboard_paths(board: dict[str, Any], paths: list[str]) -> dict[str, Any]:
    """Resolve dotted paths like contributions.qcloud-monitor-ops."""
    resolved: dict[str, Any] = {}
    for path in paths:
        value: Any = board
        for part in path.split("."):
            if not isinstance(value, dict) or part not in value:
                value = None
                break
            value = value[part]
        resolved[path] = value
    return resolved
