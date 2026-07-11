from copilot.models import ExecutionPlan, PlanStep, ClassifiedIntent, IntentType
from copilot.safety.l2 import check_l2, requires_confirmation


def _plan_with_destructive(destructive: bool) -> ExecutionPlan:
    intent = ClassifiedIntent(primary=IntentType.ACT, targets=["vm"])
    steps = [
        PlanStep(
            id="act-1",
            type="skill_call",
            skill="qcloud-cvm-ops",
            params={"operation": "stop"},
            destructive=destructive,
            description="Stop VM",
        )
    ]
    return ExecutionPlan(intent=intent, steps=steps, context={}, safety_level=2)


def test_requires_confirmation_for_destructive():
    assert requires_confirmation(_plan_with_destructive(True)) is True


def test_no_confirmation_for_readonly():
    assert requires_confirmation(_plan_with_destructive(False)) is False


def test_l2_pass_for_readonly():
    plan = _plan_with_destructive(False)
    result = check_l2(plan, confirmed=True)
    assert result["passed"] is True


def test_l2_pass_for_destructive_confirmed():
    plan = _plan_with_destructive(True)
    result = check_l2(plan, confirmed=True)
    assert result["passed"] is True


def test_l2_fail_for_destructive_not_confirmed():
    plan = _plan_with_destructive(True)
    result = check_l2(plan, confirmed=False)
    assert result["passed"] is False
    assert any("confirm" in i.lower() for i in result["issues"])
