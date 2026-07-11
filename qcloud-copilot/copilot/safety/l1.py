from __future__ import annotations

from copilot.models import ExecutionPlan


MAX_STEP_BUDGET = 10


def check_l1(plan: ExecutionPlan) -> dict:
    issues = []

    if len(plan.steps) > MAX_STEP_BUDGET:
        issues.append(f"Step budget exceeded: {len(plan.steps)} > {MAX_STEP_BUDGET}")

    seen = set()
    for step in plan.steps:
        if step.id in seen:
            issues.append(f"Duplicate step ID: {step.id}")
        seen.add(step.id)

    return {"passed": len(issues) == 0, "issues": issues}
