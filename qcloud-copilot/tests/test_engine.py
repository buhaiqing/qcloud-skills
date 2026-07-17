from pathlib import Path

from copilot.engine import CopilotEngine
from copilot.models import Report


def test_engine_ask_simple_query():
    engine = CopilotEngine()
    report = engine.ask("查 ins-abc 的状态")
    assert isinstance(report, Report)
    assert report.summary
    assert report.report_path == ""
    assert report.aggregated is False


def test_engine_ask_cruise_writes_aggregated_report(tmp_path, monkeypatch):
    reports_dir = tmp_path / "reports"
    monkeypatch.setattr(
        "copilot.report_gen.default_reports_dir",
        lambda: reports_dir,
    )

    class FakeDispatcher:
        def execute(self, plan, blackboard, session_id, parallel=True, **kwargs):
            from copilot.models import StepResult
            from copilot.report_gen import synthesize_from_blackboard

            contributions = {
                "qcloud-proactive-inspection": {
                    "verdict": "WARNING",
                    "findings": [{"summary": "磁盘未加密"}],
                }
            }
            report = synthesize_from_blackboard(contributions)
            return [
                StepResult(step_id="cruise-1", status="success", output={"has_critical": False}),
                StepResult(
                    step_id="report-1",
                    status="success",
                    output={"report": report, "has_critical": False},
                ),
            ]

    engine = CopilotEngine()
    engine._plan_dispatcher = FakeDispatcher()
    report = engine.ask(
        "巡检朔州天源全部资源",
        session_id="test-cruise-report",
        audience="summary",
        l3_reviewed=True,
    )
    assert report.aggregated is True
    assert report.report_path.endswith("final-report.md")
    assert Path(report.report_path).is_file()
    assert "磁盘未加密" in Path(report.report_path).read_text(encoding="utf-8")


def test_engine_ask_diagnose():
    engine = CopilotEngine()
    report = engine.ask("为什么我的 VM 慢")
    assert isinstance(report, Report)
    assert len(report.sections) > 0


def test_engine_ask_unknown():
    engine = CopilotEngine()
    report = engine.ask("你好")
    assert "unknown" in report.summary.lower() or "unknown" in str(report.sections).lower()
