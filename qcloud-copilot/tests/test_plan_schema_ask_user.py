"""BC-T5 plan_schema ask_user field parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from copilot.models import (
    AskOption,
    PlanStep,
    _ASK_DEFAULT_UNSET,
)
from copilot.plan_schema import (
    load_plan_file,
    plan_step_from_dict,
)


# ---------------------------------------------------------------------------
# Fixtures (literal JSON → plan_step_from_dict coverage)
# ---------------------------------------------------------------------------


@pytest.fixture
def ask_step_data() -> dict:
    return {
        "id": "ask-1",
        "type": "ask_user",
        "ask_user_options": [
            {"value": "ap-guangzhou", "label": "北京", "description": "主 region"},
            {"value": "cn-east-2", "label": "宿迁"},
        ],
        "ask_timeout_seconds": 30,
        "ask_user_context_key": "region",
        "ask_default_on_timeout": "first",
    }


def test_plan_step_from_dict_parses_ask_user_fields(ask_step_data: dict) -> None:
    step = plan_step_from_dict(ask_step_data)
    assert isinstance(step, PlanStep)
    assert step.type == "ask_user"
    assert len(step.ask_user_options) == 2
    assert step.ask_user_options[0] == AskOption(
        value="ap-guangzhou", label="北京", description="主 region"
    )
    assert step.ask_user_options[1] == AskOption(value="cn-east-2", label="宿迁", description=None)
    assert step.ask_timeout_seconds == 30
    assert step.ask_user_context_key == "region"
    assert step.ask_default_on_timeout == "first"


def test_plan_step_from_dict_unset_default_via_sentinel() -> None:
    """Fixture using '__unset__' sentinel — must map back to _ASK_DEFAULT_UNSET."""
    data = {
        "id": "ask-1",
        "type": "ask_user",
        "ask_user_options": [{"value": "x", "label": "X"}],
        "ask_default_on_timeout": "__unset__",
    }
    step = plan_step_from_dict(data)
    assert step.ask_default_on_timeout is _ASK_DEFAULT_UNSET


def test_plan_step_from_dict_omitted_default_is_unset() -> None:
    """No ask_default_on_timeout field → sentinel (inherit env)."""
    data = {
        "id": "ask-1",
        "type": "ask_user",
        "ask_user_options": [{"value": "x", "label": "X"}],
    }
    step = plan_step_from_dict(data)
    assert step.ask_default_on_timeout is _ASK_DEFAULT_UNSET


def test_plan_step_from_dict_explicit_none_default() -> None:
    """Explicit JSON null → translated back to None (fail-fast)."""
    data = {
        "id": "ask-1",
        "type": "ask_user",
        "ask_user_options": [{"value": "x", "label": "X"}],
        "ask_default_on_timeout": None,
    }
    step = plan_step_from_dict(data)
    assert step.ask_default_on_timeout is None


def test_plan_step_from_dict_empty_options_yields_empty_list() -> None:
    """No ask_user_options key → empty list (default)."""
    data = {"id": "ask-1", "type": "ask_user"}
    step = plan_step_from_dict(data)
    assert step.ask_user_options == []


def test_plan_step_from_dict_skips_options_without_value() -> None:
    data = {
        "id": "ask-1",
        "type": "ask_user",
        "ask_user_options": [
            {"label": "orphan"},
            {"value": "real", "label": "Real"},
            {"value": "", "label": "Empty value"},
        ],
    }
    step = plan_step_from_dict(data)
    assert [o.value for o in step.ask_user_options] == ["real"]


def test_plan_step_from_dict_lowercase_default() -> None:
    data = {
        "id": "ask-1",
        "type": "ask_user",
        "ask_user_options": [{"value": "x", "label": "X"}],
        "ask_default_on_timeout": "FIRST",
    }
    step = plan_step_from_dict(data)
    assert step.ask_default_on_timeout == "first"


# ---------------------------------------------------------------------------
# Existing-fixture backward compatibility (no ask_user fields)
# ---------------------------------------------------------------------------


def test_skill_call_step_unchanged() -> None:
    data = {
        "id": "vpc-0",
        "type": "skill_call",
        "skill": "qcloud-vpc-ops",
        "operation": "describe-vpcs",
        "params": {"region": "ap-guangzhou"},
    }
    step = plan_step_from_dict(data)
    assert step.ask_user_options == []
    assert step.ask_timeout_seconds == 60
    assert step.ask_default_on_timeout is _ASK_DEFAULT_UNSET


# ---------------------------------------------------------------------------
# Fixture file (whole-plan) load
# ---------------------------------------------------------------------------


def test_load_plan_with_ask_region_fixture() -> None:
    plan_path = Path(__file__).resolve().parent / "fixtures" / "plan-with-ask-region.json"
    plan = load_plan_file(plan_path)
    ask_step = next(s for s in plan.steps if s.type == "ask_user")
    assert ask_step.id == "ask-region-0"
    assert len(ask_step.ask_user_options) == 2
    assert ask_step.ask_user_context_key == "region"
    assert ask_step.ask_timeout_seconds == 30

    cruise = next(s for s in plan.steps if s.id == "cruise-1")
    assert "ask-region-0" in cruise.depends_on

    plan_id = plan.plan_id or ""
    assert "ask-region" in plan_id


def test_existing_4_step_fixture_loads_without_ask() -> None:
    """Existing 4-step fixture is preserved (no ask-region-0 appended).
    The ask-region-0 fixture is its own file: plan-with-ask-region.json.
    """
    plan_path = Path(__file__).resolve().parent / "fixtures" / "plan-vpc-cruise-alert-report.json"
    plan = load_plan_file(plan_path)
    types = [s.type for s in plan.steps]
    assert "ask_user" not in types
    assert len(plan.steps) == 4

    cruise = next(s for s in plan.steps if s.id == "cruise-1")
    assert cruise.depends_on == ["vpc-0"]  # original dep, no ask prepend
