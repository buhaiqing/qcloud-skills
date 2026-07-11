"""Parallel PlanDispatcher tests (P3-T1)."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

from copilot.blackboard import BlackboardClient
from copilot.dispatcher import PlanDispatcher
from copilot.integration.skills import SkillDispatcher
from copilot.models import ExecutionPlan, StepResult
from copilot.plan_schema import load_plan_file

FIXTURE = Path(__file__).parent / "fixtures" / "plan-vpc-cruise-alert-report.json"
SLEEP_SEC = 0.2


def _board_dir(tmp_path):
    repo_schema = Path(__file__).resolve().parents[2] / ".runtime" / "blackboard" / "schema.json"
    target_dir = tmp_path / "blackboard"
    target_dir.mkdir()
    target_dir.joinpath("schema.json").write_text(
        repo_schema.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return target_dir


def _parallel_plan() -> ExecutionPlan:
    plan = load_plan_file(FIXTURE)
    plan.dispatch_config = dict(plan.dispatch_config)
    plan.dispatch_config["max_parallel_groups"] = 3
    return plan


def test_parallel_group_faster_than_serial(tmp_path):
    """cruise-1 + alert-2 same group: parallel < 350ms, serial > 380ms."""
    board_dir = _board_dir(tmp_path)
    client = BlackboardClient(board_dir=board_dir)
    session_id = "ses-parallel-timing"
    client.create(session_id, "parallel timing")

    skill = MagicMock(spec=SkillDispatcher)
    skill.execute.return_value = StepResult(
        step_id="vpc-0",
        status="success",
        output={},
    )

    class SlowDispatcher(PlanDispatcher):
        def _execute_step(self, step, plan, blackboard, session_id):
            if step.id == "cruise-1":
                time.sleep(SLEEP_SEC)
                return StepResult(step_id=step.id, status="success", output={"inspected": []})
            if step.id == "alert-2":
                time.sleep(SLEEP_SEC)
                return StepResult(step_id=step.id, status="success", output={})
            if step.id == "report-3":
                return StepResult(
                    step_id=step.id,
                    status="success",
                    output={"report": None, "has_critical": False},
                )
            return super()._execute_step(step, plan, blackboard, session_id)

    dispatcher = SlowDispatcher(skill_dispatcher=skill)
    plan = _parallel_plan()

    t0 = time.perf_counter()
    dispatcher.execute(plan, client, session_id, parallel=True)
    parallel_ms = (time.perf_counter() - t0) * 1000

    client.create("ses-serial-timing", "serial timing")
    t1 = time.perf_counter()
    dispatcher.execute(plan, client, "ses-serial-timing", parallel=False)
    serial_ms = (time.perf_counter() - t1) * 1000

    assert parallel_ms < 350, f"parallel took {parallel_ms:.0f}ms"
    assert serial_ms > 380, f"serial took {serial_ms:.0f}ms"


def test_parallel_group_order(tmp_path):
    """group0 → group1 → group2 execution waves."""
    board_dir = _board_dir(tmp_path)
    client = BlackboardClient(board_dir=board_dir)
    session_id = "ses-parallel-order"
    client.create(session_id, "parallel order")

    skill = MagicMock(spec=SkillDispatcher)
    skill.execute.return_value = StepResult(
        step_id="vpc-0",
        status="success",
        output={},
    )

    waves: list[int] = []

    class WaveDispatcher(PlanDispatcher):
        def _execute_batch(self, batch, plan, blackboard, session_id, completed, *, parallel):
            if batch:
                waves.append(batch[0].parallel_group)
            return super()._execute_batch(
                batch, plan, blackboard, session_id, completed, parallel=parallel
            )

    PlanDispatcher(skill_dispatcher=skill).execute(
        _parallel_plan(), client, session_id, parallel=True
    )
    # Re-run with wave tracking
    waves.clear()
    client.create("ses-parallel-order-2", "order 2")
    WaveDispatcher(skill_dispatcher=skill).execute(
        _parallel_plan(),
        client,
        "ses-parallel-order-2",
        parallel=True,
    )

    assert waves == [0, 1, 2]
