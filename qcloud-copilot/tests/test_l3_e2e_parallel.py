"""Level 3 Phase 3 E2E: parallel plan execution (P3-T3 GATE)."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from copilot.blackboard import BlackboardClient
from copilot.engine import CopilotEngine
from copilot.integration.skills import SkillDispatcher
from copilot.models import StepResult
from copilot.plan_schema import load_plan_file

FIXTURE = Path(__file__).parent / "fixtures" / "plan-vpc-cruise-alert-report.json"
SLEEP_SEC = 0.15


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


def _parallel_plan():
    plan = load_plan_file(FIXTURE)
    plan.dispatch_config = dict(plan.dispatch_config)
    plan.dispatch_config["max_parallel_groups"] = 3
    return plan


def test_e2e_parallel_cruise_and_alert(board_dir):
    plan = _parallel_plan()
    session_id = "ses-l3-parallel-e2e"
    client = BlackboardClient(board_dir=board_dir)
    client.create(session_id, "parallel e2e")

    skill = MagicMock(spec=SkillDispatcher)
    skill.execute.return_value = StepResult(
        step_id="vpc-0",
        status="success",
        output={},
    )

    cruise_runner = MagicMock()

    def slow_cruise(step, context, blackboard=None, session_id=None):
        time.sleep(SLEEP_SEC)
        if blackboard and session_id:
            blackboard.write_contribution(
                session_id,
                "qcloud-proactive-inspection",
                {
                    "version": "3.0.0",
                    "verdict": "PASS",
                    "findings": [{"id": "c1", "severity": "INFO", "summary": "cruise ok"}],
                    "topology_hints": ["i-cruise"],
                    "metadata": {},
                },
            )
        return StepResult(step_id=step.id, status="success", output={"inspected": ["i-cruise"]})

    cruise_runner.execute.side_effect = slow_cruise

    alert_runner = MagicMock()

    def slow_alert(params, blackboard, session_id):
        time.sleep(SLEEP_SEC)
        contribution = {
            "version": "0.4.0",
            "verdict": "PASS",
            "findings": [{"id": "a1", "severity": "INFO", "summary": "alert ok"}],
            "topology_hints": ["i-alert"],
            "metadata": {},
        }
        blackboard.write_contribution(session_id, "qcloud-monitor-ops", contribution)
        return contribution

    alert_runner.analyze.side_effect = slow_alert

    with patch("copilot.engine.SessionManager") as sm_mock:
        sm = sm_mock.return_value
        sm.blackboard_client.return_value = client
        sm.init_blackboard.return_value = client.create(session_id, "parallel e2e")

        engine = CopilotEngine()
        engine._plan_dispatcher._skill_dispatcher = skill
        engine._plan_dispatcher._cruise_runner = cruise_runner
        engine._plan_dispatcher._alert_runner = alert_runner

        t0 = time.perf_counter()
        report = engine.run_plan(plan, session_id=session_id, l3_reviewed=True)
        elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms < 350, f"parallel e2e took {elapsed_ms:.0f}ms (expected < 350)"
    assert report.title
    assert "2 skill contributions" in report.summary or len(report.sections) >= 2

    board = client.load(session_id)
    contribs = board["shared_context"]["contributions"]
    assert "qcloud-proactive-inspection" in contribs
    assert "qcloud-monitor-ops" in contribs
