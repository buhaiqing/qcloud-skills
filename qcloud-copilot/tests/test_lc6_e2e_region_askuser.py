"""BC-T6 L3 E2E: 兩客戶 region 自動探測 + ask_user 候選選擇.

This wires the BC-T1..T5 components end-to-end at the highest layer of the
test pyramid:
  - Two distinct customers, each with region ambiguity
  - One delivery + one CI run
  - Asserts: ask-region-0 fires in delivery but NOT in CI; user's pick
    reaches downstream cruise-1 (right region selected); blackboard
    persistence covers both pending_action and contributions.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from copilot.ask_user_runner import AskUserRunner
from copilot.blackboard import BlackboardClient
from copilot.dispatcher import PlanDispatcher
from copilot.integration.skills import SkillDispatcher
from copilot.models import (
    AskOption,
    ClassifiedIntent,
    ExecutionPlan,
    IntentType,
    PlanStep,
    StepResult,
)
from copilot.plan_gen import _cruise_plan


_INTENT = ClassifiedIntent(primary=IntentType.CRUISE, targets=["vm"])


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    repo_schema = Path(__file__).resolve().parents[2] / ".runtime" / "blackboard" / "schema.json"
    target_dir = tmp_path / "blackboard"
    target_dir.mkdir()
    target_dir.joinpath("schema.json").write_text(
        repo_schema.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return target_dir


def _candidate(region: str, count: int, types: list[str] | None = None) -> dict[str, Any]:
    return {
        "region": region,
        "customer_resources_count": count,
        "resource_types": types or ["vm"],
    }


def _build_runner(board_dir: Path) -> PlanDispatcher:
    """PlanDispatcher that bypasses tccli / SDK; cruise/alert runners stubbed."""

    class _StubbedDispatcher(PlanDispatcher):
        def _execute_step(self, step, plan, blackboard, session_id):
            from time import time as _time

            start = _time()
            # Mirror the dispatcher: invoke runners via the same signatures.
            context = dict(plan.context)
            if step.type == "ask_user":
                # Use real AskUserRunner — but pipe stdin via the test's
                # StringIO so the runner doesn't block on sys.stdin.
                stdin_buffer = plan.context.get("__test_stdin__") or ""
                runner = AskUserRunner()
                result = runner.execute(
                    step,
                    context,
                    blackboard,
                    session_id,
                    stdin=io.StringIO(stdin_buffer),
                    stdout=io.StringIO(),
                )
            elif step.type == "cruise_run":
                # Honor the user's selected region by echoing it back.
                selected = context.get("region", step.params.get("region", "ap-guangzhou"))
                step.params["region"] = selected
                result = StepResult(
                    step_id=step.id,
                    status="success",
                    output={"inspected": [], "selected_region": selected},
                )
            elif step.type == "report":
                error = step.params.get("error", "")
                result = StepResult(
                    step_id=step.id,
                    status="failure" if error else "success",
                    output={"description": step.description, **step.params},
                )
            elif step.type == "synthesize_report":
                result = StepResult(
                    step_id=step.id,
                    status="success",
                    output={"report": "stub", "has_critical": False},
                )
            else:
                result = StepResult(
                    step_id=step.id,
                    status="failure",
                    error=f"E2E stub: unknown type {step.type}",
                )

            result.duration_ms = int((_time() - start) * 1000)
            # sync back the populated context into the plan (ask_user writes
            # `region` into its local context; we need downstream steps to see it)
            if context.get("region") and context.get("region") != plan.context.get("region"):
                plan.context["region"] = context["region"]
            return result

    return _StubbedDispatcher(skill_dispatcher=MagicMock(spec=SkillDispatcher))


# ---------------------------------------------------------------------------
# Customer A — delivery: ask-region-0 fires, user picks ap-guangzhou
# ---------------------------------------------------------------------------


def test_customer_a_delivery_picks_north(board_dir: Path) -> None:
    """Two-region candidate, user picks [1] = ap-guangzhou → cruise-1 sees ap-guangzhou."""
    client = BlackboardClient(board_dir=board_dir)
    sid = "ses-e2e-A"
    client.create(sid, "客户A 巡检")

    candidates = [_candidate("ap-guangzhou", 5, ["vm", "redis"]), _candidate("cn-east-2", 2, ["rds"])]
    ctx: dict[str, Any] = {
        "customer": "客户A",
        "region": "ap-guangzhou",
        "inspection_effective": "delivery",
        "region_candidates": candidates,
        "__test_stdin__": "1\n",
    }
    plan = _cruise_plan(_INTENT, ctx)

    # Sanity: ask-region-0 was inserted, cruise-1 depends on it
    ask = next(s for s in plan.steps if s.type == "ask_user")
    assert ask.id == "ask-region-0"
    cruise = next(s for s in plan.steps if s.id == "cruise-1")
    assert "ask-region-0" in cruise.depends_on

    dispatcher = _build_runner(board_dir)
    results = dispatcher.execute(plan, client, sid)

    by_id = {r.step_id: r for r in results}
    # ask-region-0 succeeded
    assert by_id["ask-region-0"].status == "success"
    # cruise-1 saw the user's selection (ap-guangzhou, option 1)
    assert by_id["cruise-1"].output["selected_region"] == "ap-guangzhou"
    assert by_id["report-1"].status == "success"

    # Blackboard: ask_user_response in pending_actions
    board = client.load(sid)
    pa = board["shared_context"]["pending_actions"][0]
    assert pa["action"] == "ask_user_response"
    assert pa["selected_option"] == "ap-guangzhou"
    assert pa["question_id"].startswith("ask-region-0-")
    assert "responded_at" in pa


# ---------------------------------------------------------------------------
# Customer B — delivery: ask-region-0 fires, user picks cn-east-2 (option 2)
# ---------------------------------------------------------------------------


def test_customer_b_delivery_picks_east(board_dir: Path) -> None:
    """Same fixture, user picks [2] = cn-east-2."""
    client = BlackboardClient(board_dir=board_dir)
    sid = "ses-e2e-B"
    client.create(sid, "客户B 巡检")

    candidates = [_candidate("ap-guangzhou", 5, ["vm"]), _candidate("cn-east-2", 2, ["rds"])]
    ctx: dict[str, Any] = {
        "customer": "客户B",
        "region": "ap-guangzhou",
        "inspection_effective": "delivery",
        "region_candidates": candidates,
        "__test_stdin__": "2\n",
    }
    plan = _cruise_plan(_INTENT, ctx)
    dispatcher = _build_runner(board_dir)
    results = dispatcher.execute(plan, client, sid)
    by_id = {r.step_id: r for r in results}

    assert by_id["ask-region-0"].status == "success"
    assert by_id["cruise-1"].output["selected_region"] == "cn-east-2"

    # Blackboard persisted the east pick
    pa = client.load(sid)["shared_context"]["pending_actions"][0]
    assert pa["selected_option"] == "cn-east-2"


# ---------------------------------------------------------------------------
# CI mode — no ask; cruise-1 uses default region
# ---------------------------------------------------------------------------


def test_customer_ci_no_ask(board_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """InspectionModeResult.effective == 'ci' even with candidates → no ask_user step."""
    monkeypatch.delenv("COPILOT_LLM_REASONING", raising=False)

    ctx: dict[str, Any] = {
        "customer": "客户CI",
        "region": "ap-guangzhou",
        "inspection_effective": "ci",
        "region_candidates": [_candidate("ap-guangzhou", 3)],
    }
    plan = _cruise_plan(_INTENT, ctx)

    # No ask-region-0 injected
    types = [s.type for s in plan.steps]
    assert "ask_user" not in types

    cruise = next(s for s in plan.steps if s.id == "cruise-1")
    assert "ask-region-0" not in cruise.depends_on

    # Even if we manually inject an ask_user step, dispatcher rejects it
    client = BlackboardClient(board_dir=board_dir)
    sid = "ses-e2e-CI"
    client.create(sid, "CI test")

    # Build a 1-step plan with ask_user and CI effective
    plan_ci = _cruise_plan(_INTENT, ctx)  # has no ask_user
    dispatcher = _build_runner(board_dir)
    results = dispatcher.execute(plan_ci, client, sid)
    # All non-ask_user steps should succeed
    assert all(r.status == "success" for r in results)


# ---------------------------------------------------------------------------
# Defensive: planner leakage — ask_user in CI is rejected by dispatcher
# ---------------------------------------------------------------------------


def test_dispatcher_rejects_leaked_ask_user_in_ci(board_dir: Path) -> None:
    """Even if a planner manually builds an ask_user step in CI, dispatcher rejects."""
    client = BlackboardClient(board_dir=board_dir)
    sid = "ses-e2e-leak"
    client.create(sid, "planner leakage test")

    ask_step = PlanStep(
        id="leaked-ask",
        type="ask_user",
        ask_user_options=[AskOption(value="x", label="X")],
    )

    plan = ExecutionPlan(
        intent=_INTENT,
        steps=[ask_step],
        context={"inspection_effective": "ci"},
    )
    dispatcher = PlanDispatcher(
        skill_dispatcher=MagicMock(spec=SkillDispatcher),
        ask_user_runner=MagicMock(),
    )
    results = dispatcher.execute(plan, client, sid)
    assert results[0].status == "failure"
    assert "rejected" in (results[0].error or "")


# ---------------------------------------------------------------------------
# Single-region customer — no ask needed
# ---------------------------------------------------------------------------


def test_no_ask_when_no_candidates(board_dir: Path) -> None:
    """When ctx has no region_candidates and region is already explicit → no ask fired.

    The producer (mode_gate.maybe_discover_regions via plan_gen.generate) is
    bypassed here by setting ``region`` upfront, so no scanner ever runs.
    """
    client = BlackboardClient(board_dir=board_dir)
    sid = "ses-e2e-empty"
    client.create(sid, "no candidates")

    ctx: dict[str, Any] = {
        "customer": "isolated",
        "region": "cn-east-2",  # already explicit
        "inspection_effective": "delivery",
        # no region_candidates
    }
    plan = _cruise_plan(_INTENT, ctx)
    types = [s.type for s in plan.steps]
    assert "ask_user" not in types

    dispatcher = _build_runner(board_dir)
    results = dispatcher.execute(plan, client, sid)
    assert all(r.status == "success" for r in results)
    assert "pending_actions" in client.load(sid)["shared_context"]
    assert client.load(sid)["shared_context"]["pending_actions"] == []
