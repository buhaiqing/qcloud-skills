"""PlanStep ask_user field tests (BC-T1 schema 1.2)."""

from __future__ import annotations

import pytest

from copilot.models import AskOption, PlanStep


def test_planstep_default_ask_user_fields() -> None:
    """Default values match design doc BC-T1."""
    from copilot.models import _ASK_DEFAULT_UNSET

    step = PlanStep(id="ask-1", type="ask_user")
    assert step.ask_user_options == []
    assert step.ask_timeout_seconds == 60
    assert step.ask_user_context_key == "region"
    # ask_default_on_timeout default is the unset sentinel, NOT None:
    # None means "explicit fail-fast" (plan-level), sentinel means "inherit env".
    assert step.ask_default_on_timeout is _ASK_DEFAULT_UNSET


def test_planstep_ask_user_with_options() -> None:
    options = [
        AskOption(value="ap-guangzhou", label="华北-北京 (ap-guangzhou)", description="主 region"),
        AskOption(value="cn-east-2", label="华东-宿迁 (cn-east-2)"),
    ]
    step = PlanStep(
        id="ask-region",
        type="ask_user",
        skill="qcloud-proactive-inspection",
        ask_user_options=options,
        ask_timeout_seconds=120,
        ask_user_context_key="region",
        ask_default_on_timeout="first",
    )
    assert len(step.ask_user_options) == 2
    assert step.ask_user_options[0].value == "ap-guangzhou"
    assert step.ask_timeout_seconds == 120
    assert step.ask_default_on_timeout == "first"


def test_planstep_existing_callers_unchanged() -> None:
    """Backwards-compat: existing PlanStep constructions still work with all defaults."""
    step = PlanStep(id="cruise-1", type="cruise_run", skill="qcloud-proactive-inspection")
    assert step.id == "cruise-1"
    assert step.parallel_group == 0
    assert step.destructive is False
    assert step.ask_user_options == []  # new fields default


def test_ask_option_minimal() -> None:
    opt = AskOption(value="x", label="X")
    assert opt.description == ""


def test_ask_option_with_description() -> None:
    opt = AskOption(value="cn-east-2", label="华东-宿迁", description="备选")
    assert opt.description == "备选"


@pytest.mark.parametrize(
    "step_type",
    ["skill_call", "cruise_run", "alert_analyze", "synthesize_report", "report", "ask_user"],
)
def test_planstep_all_step_types_construct(step_type: str) -> None:
    """PlanStep.type union is preserved (skill_call | cruise_run | ... | ask_user)."""
    step = PlanStep(id="x", type=step_type)
    assert step.type == step_type
