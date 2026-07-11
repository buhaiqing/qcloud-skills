from copilot.models import (
    ExecutionResult,
    ExecutionPlan,
    ClassifiedIntent,
    IntentType,
    PlanStep,
    Report,
    ReportSection,
    StepResult,
)
from copilot.safety.l3 import check_l3


def _make_result(has_critical: bool, final_report: Report | None = None) -> ExecutionResult:
    intent = ClassifiedIntent(primary=IntentType.ACT, targets=["vm"])
    steps = [
        PlanStep(
            id="act-1", type="skill_call", skill="qcloud-cvm-ops", params={}, destructive=True
        ),
    ]
    plan = ExecutionPlan(intent=intent, steps=steps, context={}, safety_level=3)
    sr = StepResult(step_id="act-1", status="success", output={"affected": 1})
    return ExecutionResult(
        plan=plan,
        step_results=[sr],
        status="completed",
        final_report=final_report,
    )


def test_l3_pass_for_clean_result():
    clean_report = Report(
        title="Test",
        summary="ok",
        sections=[
            ReportSection(title="OK", severity="info", findings=[], recommendations=[]),
        ],
    )
    result = _make_result(has_critical=False, final_report=clean_report)
    r = check_l3(result)
    assert r["passed"] is True


def test_l3_fail_for_critical_without_review():
    critical_report = Report(
        title="Test",
        summary="critical",
        sections=[
            ReportSection(
                title="FAIL", severity="critical", findings=["Error"], recommendations=[]
            ),
        ],
    )
    result = _make_result(has_critical=True, final_report=critical_report)
    r = check_l3(result)
    assert r["passed"] is False
    assert any("review" in i.lower() for i in r["issues"])
