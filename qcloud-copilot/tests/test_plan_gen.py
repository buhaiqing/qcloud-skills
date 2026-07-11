from copilot.models import IntentType, ClassifiedIntent
from copilot.plan_gen import generate


def test_inspect_plan_has_one_skill_step():
    intent = ClassifiedIntent(primary=IntentType.INSPECT, targets=["vm"])
    plan = generate(intent)
    assert len(plan.steps) == 1
    assert plan.steps[0].type == "skill_call"


def test_diagnose_plan_has_two_skill_steps():
    intent = ClassifiedIntent(primary=IntentType.DIAGNOSE, targets=["vm", "monitor"])
    plan = generate(intent)
    assert len(plan.steps) == 2
    step_types = [s.type for s in plan.steps]
    assert all(t == "skill_call" for t in step_types)


def test_act_plan_includes_l2_confirmation():
    intent = ClassifiedIntent(primary=IntentType.ACT, targets=["vm"])
    plan = generate(intent)
    assert any(s.destructive for s in plan.steps)
    assert plan.safety_level >= 2


def test_cruise_plan_uses_cruise_run():
    intent = ClassifiedIntent(primary=IntentType.CRUISE, targets=[])
    plan = generate(intent)
    step_types = [s.type for s in plan.steps]
    assert "cruise_run" in step_types


def test_report_plan_produces_no_steps():
    intent = ClassifiedIntent(primary=IntentType.REPORT, targets=[])
    plan = generate(intent)
    assert len(plan.steps) == 0


def test_generates_four_step_risk_plan():
    intent = ClassifiedIntent(
        primary=IntentType.REPORT,
        targets=[],
        secondary=[IntentType.CRUISE],
    )
    plan = generate(intent, context={"user_query": "VPC 风险巡检和告警汇总"})
    assert len(plan.steps) == 4
    assert plan.steps[0].id == "vpc-0"
    assert plan.steps[-1].type == "synthesize_report"
    assert plan.plan_id == "risk-assessment-plan"
