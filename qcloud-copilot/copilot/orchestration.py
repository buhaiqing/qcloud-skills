"""Phase 2.3: Cross-Skill Autonomous Orchestration.

OrchestrationSelector selects the best OrchestrationPattern based on blackboard
state and classified intent.  All trigger conditions must be true for a pattern
to match; on multiple matches the most specific (most conditions) wins.
"""
from __future__ import annotations

import re

from copilot.models import ClassifiedIntent, Condition, OrchestrationPattern

# ---------------------------------------------------------------------------
# Pre-defined patterns
# ---------------------------------------------------------------------------

_F1 = OrchestrationPattern(
    name="F1",
    description="FinOps 发现成本异常 + 资源 CPU 高 → 巡检 → AIOps RCA",
    trigger_conditions=[
        Condition(expression="blackboard.finops.anomaly_level == 'HIGH'"),
        Condition(expression="blackboard.finops.resource_cpu > 80"),
    ],
    skill_chain=["qcloud-proactive-inspection", "qcloud-aiops-diagnosis"],
    handoff_schema="qcloud-aiops-diagnosis/assets/finops-handoff.schema.json",
    fallback_pattern="A1",
)

_P1 = OrchestrationPattern(
    name="P1",
    description="巡检发现 CRITICAL 安全配置 → AIOps 深度诊断",
    trigger_conditions=[
        Condition(expression="blackboard.inspection.severity == 'CRITICAL'"),
        Condition(expression="blackboard.inspection.category == 'security'"),
    ],
    skill_chain=["qcloud-aiops-diagnosis"],
    handoff_schema="qcloud-aiops-diagnosis/assets/inspection-handoff.schema.json",
    fallback_pattern="A2",
)

_A1 = OrchestrationPattern(
    name="A1",
    description="意图为 DIAGNOSE → AIOps 诊断",
    trigger_conditions=[
        Condition(expression="intent.primary.value == 'diagnose'"),
    ],
    skill_chain=["qcloud-aiops-diagnosis"],
    handoff_schema="qcloud-aiops-diagnosis/assets/default-handoff.schema.json",
    fallback_pattern=None,
)

_A2 = OrchestrationPattern(
    name="A2",
    description="意图为 INSPECT → 主动巡检",
    trigger_conditions=[
        Condition(expression="intent.primary.value == 'inspect'"),
    ],
    skill_chain=["qcloud-proactive-inspection"],
    handoff_schema="qcloud-proactive-inspection/assets/default-handoff.schema.json",
    fallback_pattern=None,
)

_PREDEFINED_PATTERNS: list[OrchestrationPattern] = [_F1, _P1, _A1, _A2]


# ---------------------------------------------------------------------------
# Condition evaluation helpers
# ---------------------------------------------------------------------------

_IN_SET_RE = re.compile(r"^(.+?)\s+in\s+\((.+)\)$")


class _NotFound:
    """Sentinel returned by _resolve_dot when a key is not found."""


def _resolve_dot(key: str, blackboard_state: dict) -> object:
    """Resolve a dot-notation key into its value from blackboard_state.

    ``key`` is e.g. "blackboard.finops.anomaly_level".
    Returns _NotFound if the key is absent.
    """
    if not key.startswith("blackboard."):
        return _NotFound()
    parts = key[len("blackboard.") :].split(".")
    val: object = blackboard_state
    for part in parts:
        if isinstance(val, dict) and part in val:
            val = val[part]
        else:
            return _NotFound()
    return val


def _get_nested_attr(obj: object, path: str) -> object:
    """Traverse dotted attribute path on obj (e.g. intent.primary.value)."""
    for part in path.split("."):
        if isinstance(obj, _NotFound):
            return _NotFound()
        if not hasattr(obj, part):
            return _NotFound()
        obj = getattr(obj, part)
    return obj


def _eval_condition(condition: Condition, blackboard_state: dict, intent: ClassifiedIntent) -> bool:
    """Evaluate a single Condition against blackboard_state and intent.

    Supports two forms:
      1. dot-notation comparison:  ``blackboard.X.Y == <value>``
      2. in-set test:             ``blackboard.X.Y in ('a','b')``
    """
    expr = condition.expression.strip()

    # --- in-set form ---
    m = _IN_SET_RE.match(expr)
    if m:
        field_str = m.group(1).strip()
        values_str = m.group(2).strip()

        if field_str.startswith("intent."):
            field_val = _get_nested_attr(intent, field_str[len("intent."):])
        else:
            field_val = _resolve_dot(field_str, blackboard_state)
            if isinstance(field_val, _NotFound):
                return False

        members: list[str] = []
        for token in values_str.replace("(", "").replace(")", "").split(","):
            token = token.strip().strip("'\"").strip()
            if token:
                members.append(token)
        return str(field_val) in members if not isinstance(field_val, _NotFound) else False

    # --- comparison form ---
    for op in ["==", "!=", ">=", "<=", ">", "<"]:
        if op not in expr:
            continue
        left_str, right_str = expr.split(op, 1)
        left_str = left_str.strip()
        right_str = right_str.strip()

        if left_str.startswith("intent."):
            left_val: object = _get_nested_attr(intent, left_str[len("intent."):])
        else:
            left_val = _resolve_dot(left_str, blackboard_state)
            if isinstance(left_val, _NotFound):
                return False

        if right_str.startswith(("'", '"')) and right_str.endswith(("'", '"')):
            right_val: object = right_str[1:-1]
        else:
            try:
                right_val = int(right_str)
            except ValueError:
                try:
                    right_val = float(right_str)
                except ValueError:
                    right_val = right_str

        if isinstance(left_val, (int, float)) and isinstance(right_val, (int, float)):
            if op == ">":
                return left_val > right_val
            if op == ">=":
                return left_val >= right_val
            if op == "<":
                return left_val < right_val
            if op == "<=":
                return left_val <= right_val
        if op == "==":
            return str(left_val) == str(right_val)
        if op == "!=":
            return str(left_val) != str(right_val)
        return False

    return False


# ---------------------------------------------------------------------------
# OrchestrationSelector
# ---------------------------------------------------------------------------


class OrchestrationSelector:
    """Selects the best OrchestrationPattern given current blackboard state."""

    def __init__(self, patterns: list[OrchestrationPattern] | None = None) -> None:
        self.patterns = patterns if patterns is not None else list(_PREDEFINED_PATTERNS)

    def select(
        self, blackboard_state: dict, intent: ClassifiedIntent
    ) -> OrchestrationPattern | None:
        """Return the best matching OrchestrationPattern, or None if no match.

        Matching rules:
          1. All trigger conditions must evaluate to True.
          2. Multiple matches → highest specificity (most conditions) wins.
          3. No match → None (caller falls back to default plan generation).
        """
        candidates: list[tuple[int, OrchestrationPattern]] = []

        for pattern in self.patterns:
            if all(
                _eval_condition(cond, blackboard_state, intent)
                for cond in pattern.trigger_conditions
            ):
                candidates.append((len(pattern.trigger_conditions), pattern))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
