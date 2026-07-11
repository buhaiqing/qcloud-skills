"""PlanDispatcher serial execution tests (P2-T3)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from copilot.blackboard import BlackboardClient
from copilot.dispatcher import PlanDispatcher
from copilot.integration.skills import SkillDispatcher
from copilot.models import PlanStep, StepResult
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


def test_dispatcher_serial_order(board_dir):
    plan = load_plan_file(FIXTURE)
    client = BlackboardClient(board_dir=board_dir)
    session_id = "ses-dispatch-order"
    client.create(session_id, "fixture plan")

    skill = MagicMock(spec=SkillDispatcher)
    skill.execute.return_value = StepResult(
        step_id="vpc-0",
        status="success",
        output={"skill": "qcloud-vpc-ops"},
    )

    order: list[str] = []

    class TrackingDispatcher(PlanDispatcher):
        def _execute_step(self, step, plan, blackboard, session_id):
            order.append(step.id)
            if step.type == "skill_call":
                return skill.execute(step, plan.context)
            if step.type == "cruise_run":
                return StepResult(step_id=step.id, status="success", output={"inspected": []})
            if step.type == "alert_analyze":
                return StepResult(step_id=step.id, status="success", output={"contribution": {}})
            if step.type == "synthesize_report":
                return StepResult(
                    step_id=step.id,
                    status="success",
                    output={"report": None, "has_critical": False},
                )
            return StepResult(step_id=step.id, status="success")

    dispatcher = TrackingDispatcher(skill_dispatcher=skill)
    dispatcher.execute(plan, client, session_id, parallel=False)

    assert order == ["vpc-0", "cruise-1", "alert-2", "report-3"]


def test_missing_dependency_skipped(board_dir):
    client = BlackboardClient(board_dir=board_dir)
    session_id = "ses-skip-dep"
    client.create(session_id, "skip test")

    from copilot.models import ExecutionPlan, ClassifiedIntent, IntentType

    plan = ExecutionPlan(
        intent=ClassifiedIntent(primary=IntentType.REPORT, targets=[]),
        steps=[
            PlanStep(id="a", type="report", depends_on=["missing"]),
        ],
    )
    results = PlanDispatcher().execute(plan, client, session_id)
    assert results[0].status == "skipped"
    assert "Dependency not met" in (results[0].error or "")


def test_failure_skips_dependents(board_dir):
    client = BlackboardClient(board_dir=board_dir)
    session_id = "ses-fail-chain"
    client.create(session_id, "fail chain")

    from copilot.models import ExecutionPlan, ClassifiedIntent, IntentType

    skill = MagicMock(spec=SkillDispatcher)
    skill.execute.return_value = StepResult(step_id="fail-0", status="failure", error="boom")

    plan = ExecutionPlan(
        intent=ClassifiedIntent(primary=IntentType.REPORT, targets=[]),
        steps=[
            PlanStep(id="fail-0", type="skill_call", skill="qcloud-vpc-ops", depends_on=[]),
            PlanStep(id="child-1", type="report", depends_on=["fail-0"]),
        ],
    )
    results = PlanDispatcher(skill_dispatcher=skill).execute(plan, client, session_id)
    by_id = {r.step_id: r for r in results}
    assert by_id["fail-0"].status == "failure"
    assert by_id["child-1"].status == "skipped"
