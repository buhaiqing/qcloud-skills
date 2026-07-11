"""AskUserRunner tests (BC-T3)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from copilot.ask_user_runner import (
    DEFAULT_TIMEOUT_SECONDS,
    AskUserResult,
    AskUserRunner,
)
from copilot.blackboard import BlackboardClient
from copilot.models import AskOption, PlanStep


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_no_options_returns_failure() -> None:
    runner = AskUserRunner()
    step = PlanStep(id="ask-x", type="ask_user")
    assert step.ask_user_options == []
    result = runner.execute(step, {}, None, "ses-1")
    assert result.status == "failure"
    assert "non-empty ask_user_options" in result.error


def test_empty_options_returns_failure() -> None:
    runner = AskUserRunner()
    step = PlanStep(id="ask-x", type="ask_user", ask_user_options=[])
    result = runner.execute(step, {}, None, "ses-1")
    assert result.status == "failure"


# ---------------------------------------------------------------------------
# Numeric selection + literal value selection
# ---------------------------------------------------------------------------


def test_numeric_selection_injects_context() -> None:
    runner = AskUserRunner()
    step = PlanStep(
        id="ask-region",
        type="ask_user",
        description="Pick region",
        ask_user_options=[
            AskOption(value="ap-guangzhou", label="北京"),
            AskOption(value="cn-east-2", label="宿迁"),
        ],
    )
    ctx: dict = {}
    stdout = io.StringIO()
    stdin = io.StringIO("2\n")
    result = runner.execute(step, ctx, None, "ses-x", stdin=stdin, stdout=stdout)

    assert result.status == "success"
    assert result.output["selection"]["value"] == "cn-east-2"
    assert ctx["region"] == "cn-east-2"
    assert "ask_user_history" in ctx
    assert ctx["ask_user_history"][-1]["selected_value"] == "cn-east-2"


def test_literal_value_selection() -> None:
    runner = AskUserRunner()
    step = PlanStep(
        id="ask-region",
        type="ask_user",
        ask_user_options=[
            AskOption(value="ap-guangzhou", label="北京"),
            AskOption(value="cn-east-2", label="宿迁"),
        ],
    )
    ctx: dict = {}
    stdin = io.StringIO("ap-guangzhou\n")
    result = runner.execute(step, ctx, None, "ses-x", stdin=stdin, stdout=io.StringIO())
    assert result.status == "success"
    assert ctx["region"] == "ap-guangzhou"


def test_invalid_input_treated_as_timeout_failure() -> None:
    runner = AskUserRunner()
    step = PlanStep(
        id="ask-region",
        type="ask_user",
        ask_user_options=[AskOption(value="ap-guangzhou", label="北京")],
    )
    stdin = io.StringIO("bogus\n")
    result = runner.execute(step, {}, None, "ses-x", stdin=stdin, stdout=io.StringIO())
    # No default configured, so timeout path returns failure
    assert result.status == "failure"
    assert "timed out" in result.error


# ---------------------------------------------------------------------------
# Rendering on stdout (Agent Runtime captures)
# ---------------------------------------------------------------------------


def test_stdout_renders_all_options() -> None:
    runner = AskUserRunner()
    step = PlanStep(
        id="ask-rgn",
        type="ask_user",
        description="巡检 region 选择",
        ask_user_options=[
            AskOption(value="ap-guangzhou", label="北京", description="主 region"),
            AskOption(value="cn-east-2", label="宿迁"),
        ],
    )
    stdout = io.StringIO()
    stdin = io.StringIO("1\n")
    runner.execute(step, {}, None, "ses-x", stdin=stdin, stdout=stdout)

    text = stdout.getvalue()
    assert "=== ASK_USER: ask-rgn ===" in text
    assert "[1] ap-guangzhou  北京" in text
    assert "主 region" in text
    assert "[2] cn-east-2  宿迁" in text
    assert "选择" in text  # prompt tail


# ---------------------------------------------------------------------------
# Timeout + COPILOT_ASK_DEFAULT + ask_default_on_timeout
# ---------------------------------------------------------------------------


def test_empty_stdin_triggers_timeout_failure_without_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COPILOT_ASK_DEFAULT", raising=False)
    runner = AskUserRunner()
    step = PlanStep(
        id="ask-rgn",
        type="ask_user",
        ask_user_options=[AskOption(value="ap-guangzhou", label="北京")],
        ask_timeout_seconds=1,
    )
    stdin = io.StringIO("")  # empty read → _AskTimeout
    result = runner.execute(step, {}, None, "ses-x", stdin=stdin, stdout=io.StringIO())
    assert result.status == "failure"
    assert "timed out" in result.error
    assert "COPILOT_ASK_DEFAULT" in result.error


def test_env_default_first_auto_selects_first_option(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COPILOT_ASK_DEFAULT", "first")
    runner = AskUserRunner()
    step = PlanStep(
        id="ask-rgn",
        type="ask_user",
        ask_user_options=[
            AskOption(value="ap-guangzhou", label="北京"),
            AskOption(value="cn-east-2", label="宿迁"),
        ],
        ask_timeout_seconds=1,
    )
    ctx: dict = {}
    stdin = io.StringIO("")  # empty → triggers timeout → default first
    result = runner.execute(step, ctx, None, "ses-x", stdin=stdin, stdout=io.StringIO())
    assert result.status == "success"
    assert result.output["selection"]["defaulted_via"] == "first"
    assert ctx["region"] == "ap-guangzhou"


def test_step_default_on_timeout_overrides_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COPILOT_ASK_DEFAULT", "first")
    runner = AskUserRunner()
    step = PlanStep(
        id="ask-rgn",
        type="ask_user",
        ask_user_options=[AskOption(value="only", label="Only")],
        ask_timeout_seconds=1,
        ask_default_on_timeout=None,  # explicit fail-fast overrides env
    )
    result = runner.execute(step, {}, None, "ses-x", stdin=io.StringIO(""), stdout=io.StringIO())
    assert result.status == "failure"


# ---------------------------------------------------------------------------
# Blackboard persistence (schema 1.2 ask_user_response)
# ---------------------------------------------------------------------------


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    repo_schema = Path(__file__).resolve().parents[2] / ".runtime" / "blackboard" / "schema.json"
    target_dir = tmp_path / "blackboard"
    target_dir.mkdir()
    target_dir.joinpath("schema.json").write_text(
        repo_schema.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return target_dir


def test_persists_pending_action_to_blackboard(board_dir: Path) -> None:
    runner = AskUserRunner()
    step = PlanStep(
        id="ask-rgn",
        type="ask_user",
        description="巡检 region 选择",
        ask_user_options=[
            AskOption(value="ap-guangzhou", label="北京"),
            AskOption(value="cn-east-2", label="宿迁"),
        ],
    )
    client = BlackboardClient(board_dir=board_dir)
    client.create("ses-bb", "x")

    ctx: dict = {}
    result = runner.execute(
        step,
        ctx,
        client,
        "ses-bb",
        stdin=io.StringIO("1\n"),
        stdout=io.StringIO(),
        question_id="q-test-001",
    )
    assert result.status == "success"

    board = client.load("ses-bb")
    actions = board["shared_context"]["pending_actions"]
    assert len(actions) == 1
    pa = actions[0]
    assert pa["action"] == "ask_user_response"
    assert pa["skill"] == "qcloud-copilot"
    assert pa["question_id"] == "q-test-001"
    assert pa["selected_option"] == "ap-guangzhou"
    assert pa["selected_label"] == "北京"
    assert pa["timeout_seconds"] == DEFAULT_TIMEOUT_SECONDS
    assert "responded_at" in pa


def test_no_blackboard_still_succeeds() -> None:
    """No blackboard passed (None) — context injection still works."""
    runner = AskUserRunner()
    step = PlanStep(
        id="ask-rgn",
        type="ask_user",
        ask_user_options=[AskOption(value="ap-guangzhou", label="北京")],
    )
    ctx: dict = {}
    result = runner.execute(
        step, ctx, None, "ses-x", stdin=io.StringIO("1\n"), stdout=io.StringIO()
    )
    assert result.status == "success"
    assert ctx["region"] == "ap-guangzhou"


# ---------------------------------------------------------------------------
# AskUserResult dataclass
# ---------------------------------------------------------------------------


def test_ask_user_result_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    r = AskUserResult(
        question_id="q",
        selected_option="v",
        selected_label="L",
        timeout_seconds=60,
        responded_at="2026-07-11T00:00:00+00:00",
    )
    with pytest.raises(FrozenInstanceError):
        r.selected_option = "x"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# context_key override
# ---------------------------------------------------------------------------


def test_custom_context_key() -> None:
    runner = AskUserRunner()
    step = PlanStep(
        id="ask-vpc",
        type="ask_user",
        ask_user_options=[AskOption(value="vpc-1", label="VPC 1")],
        ask_user_context_key="vpc_id",
    )
    ctx: dict = {}
    runner.execute(step, ctx, None, "ses-x", stdin=io.StringIO("1\n"), stdout=io.StringIO())
    assert ctx.get("vpc_id") == "vpc-1"
    assert "region" not in ctx  # default key not used
