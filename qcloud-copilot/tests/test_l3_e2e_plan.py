"""Level 3 Phase 2 E2E: multi-step plan + blackboard + V4 gate (P2-T7)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from copilot.blackboard import BlackboardClient
from copilot.engine import CopilotEngine
from copilot.integration.skills import SkillDispatcher
from copilot.models import StepResult
from copilot.plan_gen import generate
from copilot.models import ClassifiedIntent, IntentType
from copilot.plan_schema import load_plan_file

FIXTURE = Path(__file__).parent / "fixtures" / "plan-vpc-cruise-alert-report.json"


@pytest.fixture
def board_dir(tmp_path):
    repo_schema = Path(__file__).resolve().parents[2] / ".runtime" / "blackboard" / "schema.json"
    target_dir = tmp_path / "blackboard"
    target_dir.mkdir()
    target_dir.joinpath("schema.json").write_text(
        repo_schema.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return target_dir


def test_plan_gen_four_step_risk_plan():
    """V2: NL risk assessment produces 4-step plan matching fixture shape."""
    intent = ClassifiedIntent(
        primary=IntentType.REPORT,
        targets=[],
        secondary=[IntentType.CRUISE],
    )
    plan = generate(
        intent,
        context={"user_query": "VPC 风险巡检和告警报告", "customer": "朔州天源"},
    )
    assert len(plan.steps) == 4
    assert [s.id for s in plan.steps] == ["vpc-0", "cruise-1", "alert-2", "report-3"]


def test_e2e_plan_execution_order(board_dir):
    """V3: report-3 runs after cruise-1 and alert-2."""
    plan = load_plan_file(FIXTURE)
    session_id = "ses-l3-plan-e2e"

    with patch.object(BlackboardClient, "__init__", lambda self, board_dir=None: None):
        client = BlackboardClient()
        client.board_dir = board_dir
        client.board_dir.mkdir(parents=True, exist_ok=True)

    client = BlackboardClient(board_dir=board_dir)
    client.create(session_id, "e2e plan")

    finish_times: dict[str, float] = {}

    class TrackingEngine(CopilotEngine):
        def __init__(self):
            super().__init__()
            skill = MagicMock(spec=SkillDispatcher)
            skill.execute.return_value = StepResult(
                step_id="vpc-0",
                status="success",
                output={"data": {}},
            )
            self._plan_dispatcher._skill_dispatcher = skill

            cruise_runner = MagicMock()

            def fake_cruise(step, context, blackboard=None, session_id=None):
                if blackboard and session_id:
                    blackboard.write_contribution(
                        session_id,
                        "qcloud-proactive-inspection",
                        {
                            "version": "3.0.0",
                            "verdict": "PASS",
                            "findings": [],
                            "topology_hints": [],
                            "metadata": {},
                        },
                    )
                return StepResult(step_id=step.id, status="success", output={"inspected": []})

            cruise_runner.execute.side_effect = fake_cruise
            self._plan_dispatcher._cruise_runner = cruise_runner

            alert_runner = MagicMock()

            def fake_analyze(params, blackboard, session_id):
                contribution = {
                    "version": "0.4.0",
                    "verdict": "PASS",
                    "findings": [],
                    "topology_hints": [],
                    "metadata": {},
                }
                blackboard.write_contribution(
                    session_id, "qcloud-monitor-ops", contribution
                )
                return contribution

            alert_runner.analyze.side_effect = fake_analyze
            self._plan_dispatcher._alert_runner = alert_runner

        def _run_execution(self, plan, *, audience, l3_reviewed):
            import time

            original = self._plan_dispatcher._execute_step

            def tracked(step, p, bb, sid):
                result = original(step, p, bb, sid)
                finish_times[step.id] = time.time()
                return result

            self._plan_dispatcher._execute_step = tracked
            return super()._run_execution(plan, audience=audience, l3_reviewed=l3_reviewed)

    with patch("copilot.engine.SessionManager") as sm_mock:
        sm = sm_mock.return_value
        sm.blackboard_client.return_value = client
        sm.init_blackboard.return_value = client.create(session_id, "e2e")

        engine = TrackingEngine()
        engine._session_id = session_id
        report = engine.run_plan(plan, session_id=session_id, l3_reviewed=True)

    assert report.title
    assert finish_times["report-3"] >= finish_times["cruise-1"]
    assert finish_times["report-3"] >= finish_times["alert-2"]

    board = client.load(session_id)
    assert "qcloud-monitor-ops" in board["shared_context"]["contributions"]


def test_critical_awaiting_confirmation(board_dir):
    """V4: CRITICAL contribution blocks delivery without --reviewed."""
    plan = load_plan_file(FIXTURE)
    session_id = "ses-l3-critical"

    client = BlackboardClient(board_dir=board_dir)
    client.create(session_id, "critical gate")

    skill = MagicMock(spec=SkillDispatcher)
    skill.execute.return_value = StepResult(
        step_id="vpc-0",
        status="success",
        output={},
    )

    with patch("copilot.engine.SessionManager") as sm_mock:
        sm = sm_mock.return_value
        sm.blackboard_client.return_value = client
        sm.init_blackboard.return_value = client.create(session_id, "critical")

        engine = CopilotEngine()
        engine._plan_dispatcher._skill_dispatcher = skill

        cruise_runner = MagicMock()
        cruise_runner.execute.return_value = StepResult(
            step_id="cruise-1", status="success", output={"inspected": []}
        )
        engine._plan_dispatcher._cruise_runner = cruise_runner

        with patch.object(
            engine._plan_dispatcher._alert_runner,
            "analyze",
            return_value={
                "version": "0.4.0",
                "verdict": "CRITICAL",
                "findings": [{"id": "x", "severity": "P0", "summary": "critical alarm"}],
                "topology_hints": ["i-dead"],
                "metadata": {},
            },
        ):
            report_blocked = engine.run_plan(plan, session_id=session_id, l3_reviewed=False)

    assert "L3 gate failed" in report_blocked.summary or any(
        s.severity == "critical" for s in report_blocked.sections
    )

    with patch("copilot.engine.SessionManager") as sm_mock:
        sm = sm_mock.return_value
        sm.blackboard_client.return_value = client
        sm.init_blackboard.return_value = client.create(session_id, "critical-reviewed")

        engine = CopilotEngine()
        engine._plan_dispatcher._skill_dispatcher = skill

        cruise_runner = MagicMock()
        cruise_runner.execute.return_value = StepResult(
            step_id="cruise-1", status="success", output={"inspected": []}
        )
        engine._plan_dispatcher._cruise_runner = cruise_runner

        with patch.object(
            engine._plan_dispatcher._alert_runner,
            "analyze",
            return_value={
                "version": "0.4.0",
                "verdict": "CRITICAL",
                "findings": [{"id": "x", "severity": "P0", "summary": "critical alarm"}],
                "topology_hints": [],
                "metadata": {},
            },
        ):
            report_ok = engine.run_plan(plan, session_id=session_id, l3_reviewed=True)

    assert "L3 gate failed" not in report_ok.summary
