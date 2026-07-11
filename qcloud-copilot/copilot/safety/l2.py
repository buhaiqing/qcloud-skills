from __future__ import annotations

from copilot.models import ExecutionPlan


def requires_confirmation(plan: ExecutionPlan) -> bool:
    return any(step.destructive for step in plan.steps)


def check_l2(plan: ExecutionPlan, confirmed: bool = False) -> dict:
    issues = []

    if requires_confirmation(plan) and not confirmed:
        issues.append("Destructive operation requires user confirmation before execution")

    return {"passed": len(issues) == 0, "issues": issues}
