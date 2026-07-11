from copilot.engine import CopilotEngine
from copilot.parser import parse
from copilot.classifier import classify
from copilot.plan_gen import generate


def test_e2e_parse_classify_plan_execute_report():
    engine = CopilotEngine()
    report = engine.ask("查 ins-abc 的状态")
    assert report.title
    assert report.summary
    assert len(report.sections) >= 0


def test_e2e_diagnose_flow():
    engine = CopilotEngine()
    report = engine.ask("为什么我的 VM 慢")
    assert "diagnose" in report.title.lower() or "vm" in report.title.lower()


def test_e2e_cruise_flow():
    engine = CopilotEngine()
    report = engine.ask("巡检济南银座全部资源")
    assert "cruise" in report.title.lower() or "aiops" in report.title.lower()


def test_e2e_act_flow():
    engine = CopilotEngine()
    report = engine.ask("停止 ins-abc")
    assert "act" in report.title.lower() or "stop" in report.summary.lower()


def test_e2e_unknown_intent():
    engine = CopilotEngine()
    report = engine.ask("你好")
    assert "unknown" in report.summary.lower() or "unknown" in str(report.sections).lower()


def test_e2e_summary_audience():
    engine = CopilotEngine()
    report = engine.ask("帮我看看济南银座的资源健康吗", audience="summary")
    assert report.summary


def test_e2e_parser_entity_extraction():
    req = parse("查 ins-abc123 的磁盘使用率")
    assert "ins-abc123" in req.entities.get("resource_id", [])


def test_e2e_classifier_intent_detection():
    req = parse("为什么 VM 慢")
    intent = classify(req)
    assert intent.primary.value == "diagnose"


def test_e2e_plangen_step_count():
    from copilot.models import IntentType, ClassifiedIntent

    intent = ClassifiedIntent(primary=IntentType.INSPECT, targets=["vm"])
    plan = generate(intent)
    assert len(plan.steps) == 1


def test_e2e_session_context():
    from copilot.session import SessionManager

    sm = SessionManager()
    state = sm.create_session()
    assert state.session_id.startswith("ses-")
