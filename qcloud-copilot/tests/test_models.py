from copilot.models import (
    ParsedRequest,
    ClassifiedIntent,
    IntentType,
    PlanStep,
    ExecutionPlan,
    ReportSection,
    SessionState,
)


def test_parsed_request_defaults():
    req = ParsedRequest(raw="test", normalized="test")
    assert req.raw == "test"
    assert req.normalized == "test"
    assert req.entities == {}
    assert req.confidence == 1.0


def test_classified_intent():
    intent = ClassifiedIntent(primary=IntentType.INSPECT, targets=["vm"])
    assert intent.primary == IntentType.INSPECT
    assert intent.targets == ["vm"]
    assert intent.secondary == []
    assert intent.confidence == 1.0


def test_plan_step_non_destructive_by_default():
    step = PlanStep(
        id="step-1", type="skill_call", skill="qcloud-cvm-ops", params={}, depends_on=[]
    )
    assert not step.destructive


def test_plan_step_destructive_when_act_intent():
    step = PlanStep(
        id="step-1",
        type="skill_call",
        skill="qcloud-cvm-ops",
        params={"operation": "stop-instance"},
        depends_on=[],
        destructive=True,
    )
    assert step.destructive


def test_execution_plan_defaults():
    intent = ClassifiedIntent(primary=IntentType.INSPECT, targets=["vm"])
    plan = ExecutionPlan(intent=intent, steps=[], context={})
    assert plan.safety_level == 0


def test_report_section_severity_valid():
    for sev in ("critical", "warning", "info", "success"):
        section = ReportSection(title="t", severity=sev, findings=[], recommendations=[])
        assert section.severity == sev


def test_session_state_fields():
    state = SessionState(
        session_id="ses-001", created_at="2026-07-06T00:00:00Z", history=[], context={}
    )
    assert state.session_id == "ses-001"


def test_intent_type_enum_values():
    assert {e.value for e in IntentType} == {
        "diagnose",
        "inspect",
        "cruise",
        "act",
        "compare",
        "report",
        "unknown",
    }
