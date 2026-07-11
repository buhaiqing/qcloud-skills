"""BC-T4 mode_gate + plan_gen tests.

mode_gate was renamed (and is now an active producer wired into
``plan_gen.generate``). These tests cover both the gate's hard rules and the
end-to-end planner wiring through ``generate``.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from copilot.blackboard import BlackboardClient
from copilot.dispatcher import PlanDispatcher
from copilot.integration.cruise import CruiseRunner
from copilot.integration.skills import SkillDispatcher
from copilot.models import (
    AskOption,
    ClassifiedIntent,
    ExecutionPlan,
    IntentType,
    PlanStep,
    StepResult,
)
from copilot.mode_gate import maybe_discover_regions
from copilot.plan_gen import (
    _build_region_ask_options,
    _cruise_plan,
    _is_region_ambiguous,
    generate,
)
from copilot.region_scanner import RegionCandidate


# ---------------------------------------------------------------------------
# mode_gate
# ---------------------------------------------------------------------------


class _FakeModeResult:
    def __init__(self, effective: str) -> None:
        self.effective = effective


def _intent() -> ClassifiedIntent:
    return ClassifiedIntent(primary=IntentType.CRUISE, targets=["vm"])


def test_mode_gate_returns_none_for_ci() -> None:
    result = maybe_discover_regions(
        intent=_intent(),
        customer="A",
        region="",
        context={},
        mode_result=_FakeModeResult("ci"),
        client_factory=lambda: None,
    )
    assert result is None


def test_mode_gate_returns_none_for_fallback() -> None:
    result = maybe_discover_regions(
        intent=_intent(),
        customer="A",
        region="",
        context={},
        mode_result=_FakeModeResult("fallback"),
        client_factory=lambda: None,
    )
    assert result is None


def test_mode_gate_returns_none_for_explicit_region_in_context() -> None:
    """Region supplied via context short-circuits discovery."""
    result = maybe_discover_regions(
        intent=_intent(),
        customer="A",
        region="cn-east-2",
        context={},
        mode_result=_FakeModeResult("delivery"),
        client_factory=lambda: None,
    )
    assert result is None


def test_mode_gate_returns_none_when_context_has_prior_region() -> None:
    result = maybe_discover_regions(
        intent=_intent(),
        customer="A",
        region="",
        context={"region": "ap-guangzhou"},
        mode_result=_FakeModeResult("delivery"),
        client_factory=lambda: None,
    )
    assert result is None


def test_mode_gate_skips_non_cruise_intents() -> None:
    """Region discovery is only useful for cruise-shaped intents."""
    diag = ClassifiedIntent(primary=IntentType.DIAGNOSE, targets=["vm"])
    result = maybe_discover_regions(
        intent=diag,
        customer="A",
        region="",
        context={},
        mode_result=_FakeModeResult("delivery"),
        client_factory=lambda: None,
    )
    assert result is None


def test_mode_gate_skips_when_no_customer() -> None:
    result = maybe_discover_regions(
        intent=_intent(),
        customer="",
        region="",
        context={},
        mode_result=_FakeModeResult("delivery"),
        client_factory=lambda: None,
    )
    assert result is None


def test_mode_gate_uses_existing_region_candidates() -> None:
    """Upstream pre-populated candidates are honored without re-scanning."""
    pre = [RegionCandidate(region="cn-east-2", customer_resources_count=2)]
    scanner_called = {"n": 0}

    def _spy_scanner(*a, **kw):
        scanner_called["n"] += 1
        return []

    result = maybe_discover_regions(
        intent=_intent(),
        customer="A",
        region="",
        context={"region_candidates": [c.__dict__ for c in pre]},
        mode_result=_FakeModeResult("delivery"),
        client_factory=lambda: "fake",
        scanner=_spy_scanner,
    )
    assert result is not None
    assert result[0].region == "cn-east-2"
    assert scanner_called["n"] == 0  # no re-scan


def test_mode_gate_calls_scanner_in_delivery_mode() -> None:
    seen: dict = {}

    def fake_scanner(client, customer, regions=None, **kwargs):
        seen["client"] = client
        seen["customer"] = customer
        return [RegionCandidate(region="ap-guangzhou", customer_resources_count=3)]

    result = maybe_discover_regions(
        intent=_intent(),
        customer="客户A",
        region="",
        context={},
        mode_result=_FakeModeResult("delivery"),
        client_factory=lambda: "fake-client",
        scanner=fake_scanner,
    )
    assert result is not None
    assert seen["customer"] == "客户A"
    assert seen["client"] == "fake-client"
    assert result[0].region == "ap-guangzhou"


# ---------------------------------------------------------------------------
# plan_gen._is_region_ambiguous
# ---------------------------------------------------------------------------


def test_region_not_ambiguous_in_ci_mode() -> None:
    ctx = {"region_candidates": [{"region": "ap-guangzhou"}], "inspection_effective": "ci"}
    assert _is_region_ambiguous(customer="A", region="ap-guangzhou", ctx=ctx) is False


def test_region_not_ambiguous_in_fallback_mode() -> None:
    ctx = {"region_candidates": [{"region": "ap-guangzhou"}], "inspection_effective": "fallback"}
    assert _is_region_ambiguous(customer="A", region="ap-guangzhou", ctx=ctx) is False


def test_region_not_ambiguous_without_candidates() -> None:
    assert _is_region_ambiguous(customer="A", region="ap-guangzhou", ctx={}) is False


def test_region_ambiguous_with_candidates_in_delivery() -> None:
    ctx = {
        "region_candidates": [{"region": "ap-guangzhou", "customer_resources_count": 3}],
        "inspection_effective": "delivery",
    }
    assert _is_region_ambiguous(customer="A", region="ap-guangzhou", ctx=ctx) is True


# ---------------------------------------------------------------------------
# plan_gen._build_region_ask_options
# ---------------------------------------------------------------------------


def test_build_options_from_candidates() -> None:
    ctx = {
        "region_candidates": [
            {
                "region": "ap-guangzhou",
                "customer_resources_count": 3,
                "resource_types": ["vm", "redis"],
            },
            {"region": "cn-east-2", "customer_resources_count": 1, "resource_types": []},
        ]
    }
    opts = _build_region_ask_options(ctx)
    assert len(opts) == 2
    assert opts[0].value == "ap-guangzhou"
    assert "3" in opts[0].description
    assert "vm" in opts[0].description


def test_build_options_respects_allowlist_from_ctx() -> None:
    ctx = {
        "region_candidates": [
            {"region": "ap-guangzhou", "customer_resources_count": 3},
            {"region": "cn-east-2", "customer_resources_count": 1},
        ],
        "region_allowlist": ["ap-guangzhou"],
    }
    opts = _build_region_ask_options(ctx)
    assert [o.value for o in opts] == ["ap-guangzhou"]


def test_build_options_respects_allowlist_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """COPILOT_REGION_ALLOWLIST (CSV) narrows candidates when ctx has none."""
    monkeypatch.setenv("COPILOT_REGION_ALLOWLIST", "cn-east-2, cn-south-1")
    ctx = {
        "region_candidates": [
            {"region": "ap-guangzhou", "customer_resources_count": 3},
            {"region": "cn-east-2", "customer_resources_count": 1},
        ]
    }
    opts = _build_region_ask_options(ctx)
    assert [o.value for o in opts] == ["cn-east-2"]


def test_build_options_empty_when_no_candidates() -> None:
    assert _build_region_ask_options({}) == []


# ---------------------------------------------------------------------------
# plan_gen._cruise_plan ask-region-0 insertion
# ---------------------------------------------------------------------------


_INTENT = ClassifiedIntent(primary=IntentType.CRUISE, targets=["vm"])


def test_cruise_plan_no_ask_when_region_explicit() -> None:
    ctx = {"customer": "A", "region": "cn-east-2"}
    plan = _cruise_plan(_INTENT, ctx)
    types = [s.type for s in plan.steps]
    assert "ask_user" not in types
    cruise = [s for s in plan.steps if s.id == "cruise-1"][0]
    assert cruise.parallel_group == 0
    assert cruise.depends_on == []


def test_cruise_plan_no_ask_in_ci_mode() -> None:
    ctx = {
        "customer": "A",
        "region": "ap-guangzhou",
        "inspection_effective": "ci",
        "region_candidates": [{"region": "ap-guangzhou"}],
    }
    plan = _cruise_plan(_INTENT, ctx)
    types = [s.type for s in plan.steps]
    assert "ask_user" not in types


def test_cruise_plan_no_ask_without_candidates() -> None:
    ctx = {"customer": "A", "region": "ap-guangzhou", "inspection_effective": "delivery"}
    plan = _cruise_plan(_INTENT, ctx)
    types = [s.type for s in plan.steps]
    assert "ask_user" not in types


def test_cruise_plan_inserts_ask_region_in_delivery_with_candidates() -> None:
    ctx = {
        "customer": "客户A",
        "region": "ap-guangzhou",
        "inspection_effective": "delivery",
        "region_candidates": [
            {"region": "ap-guangzhou", "customer_resources_count": 5, "resource_types": ["vm"]},
            {"region": "cn-east-2", "customer_resources_count": 2, "resource_types": ["redis"]},
        ],
    }
    plan = _cruise_plan(_INTENT, ctx)
    ask_steps = [s for s in plan.steps if s.type == "ask_user"]
    assert len(ask_steps) == 1
    ask = ask_steps[0]
    assert ask.id == "ask-region-0"
    assert ask.parallel_group == 0
    assert len(ask.ask_user_options) == 2
    assert {o.value for o in ask.ask_user_options} == {"ap-guangzhou", "cn-east-2"}

    cruise = [s for s in plan.steps if s.id == "cruise-1"][0]
    assert cruise.parallel_group == 1
    assert cruise.depends_on == ["ask-region-0"]


# ---------------------------------------------------------------------------
# plan_gen.generate wiring — mode_gate is called and writes region_candidates
# ---------------------------------------------------------------------------


class _ModeResult:
    """Mimics copilot.mode_resolver.InspectionModeResult.to_context shape."""

    def __init__(self, effective: str) -> None:
        self.effective = effective

    def to_context(self) -> dict:
        return {"inspection_effective": self.effective}


def test_generate_wires_region_candidates_in_delivery() -> None:
    """End-to-end: plan_gen.generate calls mode_gate and writes candidates."""
    fake_mode = _ModeResult("delivery")
    seen: dict = {}

    def fake_scanner(client, customer, regions=None, **kwargs):
        seen["customer"] = customer
        return [
            RegionCandidate(region="ap-guangzhou", customer_resources_count=4),
            RegionCandidate(region="cn-east-2", customer_resources_count=1),
        ]

    ctx = {
        "customer": "客户E",
        "region": "",
        "inspection_mode_result": fake_mode,
        "user_query": "客户E 巡检",
    }
    plan = generate(_INTENT, ctx, scanner=fake_scanner)
    assert seen["customer"] == "客户E"
    # generate shallow-copies ctx, so the populated region_candidates land on
    # plan.context (the source of truth that downstream steps read).
    assert plan.context.get("region_candidates"), (
        "generate should populate region_candidates on plan.context"
    )
    types = [s.type for s in plan.steps]
    assert "ask_user" in types
    ask = next(s for s in plan.steps if s.type == "ask_user")
    assert ask.id == "ask-region-0"


def test_generate_skips_discovery_in_ci_mode() -> None:
    fake_mode = _ModeResult("ci")
    scanner_called = {"n": 0}

    def fake_scanner(*a, **kw):
        scanner_called["n"] += 1
        return []

    ctx = {
        "customer": "客户F",
        "region": "",
        "inspection_mode_result": fake_mode,
        "user_query": "客户F CI 巡检",
    }
    plan = generate(_INTENT, ctx, scanner=fake_scanner)
    assert scanner_called["n"] == 0
    assert not plan.context.get("region_candidates")
    types = [s.type for s in plan.steps]
    assert "ask_user" not in types


def test_generate_without_mode_info_is_conservative() -> None:
    """No inspection_mode_result → skip discovery (callers can supply ctx directly)."""
    ctx = {"customer": "客户G", "region": "ap-guangzhou", "user_query": "客户G"}
    plan = generate(_INTENT, ctx)
    types = [s.type for s in plan.steps]
    assert "ask_user" not in types


# ---------------------------------------------------------------------------
# dispatcher.ask_user branch + CI rejection
# ---------------------------------------------------------------------------


def _stub_cruise_runner():
    runner = CruiseRunner()
    runner._execute_targeted = lambda *a, **kw: None  # type: ignore[assignment]
    return runner


def _board(tmp_path: Path) -> BlackboardClient:
    repo_schema = Path(__file__).resolve().parents[2] / ".runtime" / "blackboard" / "schema.json"
    target_dir = tmp_path / "blackboard"
    target_dir.mkdir()
    target_dir.joinpath("schema.json").write_text(
        repo_schema.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return BlackboardClient(board_dir=target_dir)


def _ask_step() -> PlanStep:
    return PlanStep(
        id="ask-region-0",
        type="ask_user",
        ask_user_options=[AskOption(value="ap-guangzhou", label="北京")],
        ask_timeout_seconds=10,
    )


def test_dispatcher_dispatches_ask_user_in_delivery(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Delivery mode → ask_user runs through AskUserRunner and succeeds."""
    captured: dict = {}

    class FakeRunner:
        def execute(self, step, context, blackboard, session_id, **kw):
            captured["called"] = True
            context["region"] = "ap-guangzhou"
            return StepResult(
                step_id=step.id,
                status="success",
                output={"selection": {"value": "ap-guangzhou"}},
            )

    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    dispatcher = PlanDispatcher(
        skill_dispatcher=_stub_cruise_runner() or SkillDispatcher(),
        cruise_runner=_stub_cruise_runner(),
        ask_user_runner=FakeRunner(),
    )

    board = _board(tmp_path)
    plan = ExecutionPlan(
        intent=_INTENT,
        steps=[_ask_step(), PlanStep(id="cruise-1", type="report")],
        context={"inspection_effective": "delivery"},
    )
    results = dispatcher.execute(plan, board, "ses-x")
    assert captured["called"] is True
    assert results[0].status == "success"


def test_dispatcher_rejects_ask_user_in_ci(tmp_path: Path) -> None:
    """CI mode → ask_user step is rejected up-front without invoking runner."""
    called = {"ask": False, "cruise": False}

    class SpyAskRunner:
        def execute(self, *a, **kw):
            called["ask"] = True
            return None  # never reached

    class SpyCruiseRunner:
        def execute(self, *a, **kw):
            called["cruise"] = True
            return StepResult(step_id="x", status="success")

    dispatcher = PlanDispatcher(
        skill_dispatcher=SpyCruiseRunner() or SkillDispatcher(),
        cruise_runner=SpyCruiseRunner(),
        ask_user_runner=SpyAskRunner(),
    )

    board = _board(tmp_path)
    ask_step = _ask_step()
    plan = ExecutionPlan(
        intent=_INTENT,
        steps=[ask_step],
        context={"inspection_effective": "ci"},
    )
    results = dispatcher.execute(plan, board, "ses-x")
    assert called["ask"] is False
    assert results[0].status == "failure"
    assert "rejected" in (results[0].error or "")


# ---------------------------------------------------------------------------
# dispatcher unknown step type → fail-fast
# ---------------------------------------------------------------------------


def test_dispatcher_rejects_unknown_step_type(tmp_path: Path) -> None:
    dispatcher = PlanDispatcher()
    board = _board(tmp_path)
    plan = ExecutionPlan(
        intent=_INTENT,
        steps=[PlanStep(id="x", type="this_type_does_not_exist")],
        context={"inspection_effective": "delivery"},
    )
    results = dispatcher.execute(plan, board, "ses-x")
    assert results[0].status == "failure"
    assert "Unknown step type" in (results[0].error or "")
