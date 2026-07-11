from copilot.models import ExecutionPlan, ClassifiedIntent, IntentType, PlanStep
from copilot.safety.l1 import check_l1


def _make_plan(step_count: int, has_cycle: bool = False) -> ExecutionPlan:
    intent = ClassifiedIntent(primary=IntentType.INSPECT, targets=["vm"])
    steps = [
        PlanStep(
            id=f"step-{i}",
            type="skill_call",
            skill="qcloud-cvm-ops",
            params={"operation": "describe"},
            depends_on=[],
        )
        for i in range(step_count)
    ]
    if has_cycle:
        steps[1].depends_on = ["step-2"]
    return ExecutionPlan(intent=intent, steps=steps, context={}, safety_level=1)


def test_l1_valid_plan():
    plan = _make_plan(3)
    result = check_l1(plan)
    assert result["passed"] is True
    assert result["issues"] == []


def test_l1_too_many_steps():
    plan = _make_plan(15)
    result = check_l1(plan)
    assert result["passed"] is False
    assert any("budget" in i.lower() or "too many" in i.lower() for i in result["issues"])


def test_l1_within_budget():
    plan = _make_plan(10)
    result = check_l1(plan)
    assert result["passed"] is True
