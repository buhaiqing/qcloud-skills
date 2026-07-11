from copilot.models import (
    ClassifiedIntent,
    ExecutionPlan,
    ExecutionResult,
    IntentType,
    PlanStep,
    StepResult,
)
from copilot.report_gen import render_markdown, save_report_markdown, synthesize


def _make_result(status="completed") -> ExecutionResult:
    intent = ClassifiedIntent(primary=IntentType.INSPECT, targets=["vm"])
    step = PlanStep(
        id="step-1",
        type="skill_call",
        skill="qcloud-cvm-ops",
        params={"operation": "describe"},
        depends_on=[],
    )
    plan = ExecutionPlan(intent=intent, steps=[step], context={})
    step_result = StepResult(
        step_id="step-1",
        status="success",
        output={"instances": [{"id": "ins-abc", "status": "running"}]},
    )
    return ExecutionResult(plan=plan, step_results=[step_result], status=status)


def test_detailed_report_contains_raw_data():
    result = _make_result()
    report = synthesize(result, audience="detailed")
    assert "instances" in str(report.sections)
    assert report.sections[0].severity in ("critical", "warning", "info", "success")


def test_summary_report_contains_summary():
    result = _make_result()
    report = synthesize(result, audience="summary")
    assert len(report.sections) > 0
    assert report.summary


def test_error_result_has_critical_section():
    result = _make_result("completed")
    result.step_results[0].status = "failure"
    result.step_results[0].error = "Connection failed"
    report = synthesize(result)
    severities = [s.severity for s in report.sections]
    assert "critical" in severities


def test_report_execution_trace_present():
    result = _make_result()
    report = synthesize(result)
    assert len(report.execution_trace) > 0


def test_render_markdown_includes_title_and_findings():
    result = _make_result()
    report = synthesize(result, audience="detailed")
    md = render_markdown(report)
    assert report.title in md
    assert "instances:" in md


def test_save_report_markdown_writes_file(tmp_path):
    result = _make_result()
    report = synthesize(result)
    report.aggregated = True
    path = save_report_markdown(report, session_id="test-session", output_path=tmp_path / "out.md")
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert report.title in text
    assert text.startswith("# ")
