"""Dispatcher ↔ Blackboard integration tests (P2-T5)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from copilot.blackboard import BlackboardClient
from copilot.dispatcher import PlanDispatcher
from copilot.integration.skills import SkillDispatcher
from copilot.models import ClassifiedIntent, ExecutionPlan, IntentType, PlanStep, StepResult
from copilot.plan_schema import load_plan_file

FIXTURE = Path(__file__).parent / "fixtures" / "plan-vpc-cruise-alert-report.json"


def _board_dir(tmp_path):
    repo_schema = Path(__file__).resolve().parents[2] / ".runtime" / "blackboard" / "schema.json"
    target_dir = tmp_path / "blackboard"
    target_dir.mkdir()
    target_dir.joinpath("schema.json").write_text(
        repo_schema.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return target_dir


def test_alert_and_cruise_write_two_contributions(tmp_path):
    board_dir = _board_dir(tmp_path)
    plan = load_plan_file(FIXTURE)
    client = BlackboardClient(board_dir=board_dir)
    session_id = "ses-bb-dispatch"
    client.create(session_id, "blackboard dispatch")

    skill = MagicMock(spec=SkillDispatcher)
    skill.execute.return_value = StepResult(
        step_id="vpc-0",
        status="success",
        output={"data": {"vpcs": []}},
    )

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
                    "topology_hints": ["i-mock"],
                    "metadata": {},
                },
            )
        return StepResult(step_id=step.id, status="success", output={"inspected": ["i-mock"]})

    cruise_runner.execute.side_effect = fake_cruise

    alert_runner = MagicMock()

    def fake_analyze(params, blackboard, session_id):
        contribution = {
            "version": "0.4.0",
            "verdict": "PASS",
            "findings": [],
            "topology_hints": ["i-mock"],
            "metadata": {},
        }
        blackboard.write_contribution(session_id, "qcloud-monitor-ops", contribution)
        return contribution

    alert_runner.analyze.side_effect = fake_analyze

    dispatcher = PlanDispatcher(
        skill_dispatcher=skill,
        cruise_runner=cruise_runner,
        alert_runner=alert_runner,
    )
    dispatcher.execute(
        plan,
        client,
        session_id,
        parallel=False,
    )

    board = client.load(session_id)
    contributions = board["shared_context"]["contributions"]
    assert "qcloud-monitor-ops" in contributions
    assert "qcloud-proactive-inspection" in contributions

    hints = client.read_topology_hints(session_id)
    assert isinstance(hints, list)


def test_plan_snapshot_written(tmp_path):
    board_dir = _board_dir(tmp_path)
    client = BlackboardClient(board_dir=board_dir)
    session_id = "ses-plan-snap"
    client.create(session_id, "plan snapshot")

    plan = ExecutionPlan(
        intent=ClassifiedIntent(primary=IntentType.REPORT, targets=[]),
        steps=[PlanStep(id="only", type="report")],
        plan_id="test-plan-99",
    )
    PlanDispatcher().execute(plan, client, session_id)
    board = client.load(session_id)
    assert board["plan_id"] == "test-plan-99"
    assert board["plan"]["plan_id"] == "test-plan-99"
