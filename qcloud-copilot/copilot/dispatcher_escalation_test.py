"""Tests for PlanDispatcher × ErrorEscalator integration (Phase 1.3).

TDD: written before the dispatcher modifications landed. Verifies:

* Unknown error codes → safe HALT default.
* ``HALT`` action short-circuits to failure (no further retries).
* ``DELEGATE`` action swaps step.skill and re-runs the skill dispatcher.
* ``RETRY`` action re-executes the step up to max_retries with backoff.

Run: cd qcloud-copilot && python3 -m unittest copilot.dispatcher_escalation_test -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
COPILOT_ROOT = HERE.parent  # qcloud-copilot/
REPO_ROOT = COPILOT_ROOT.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(COPILOT_ROOT))
sys.path.insert(0, str(SCRIPTS))

from error_escalator import Action, ErrorEscalator, ErrorRule

from copilot.dispatcher import PlanDispatcher
from copilot.integration.skills import SkillDispatcher
from copilot.models import PlanStep, StepResult


class _RecordingSkillDispatcher(SkillDispatcher):
    """SkillDispatcher stub that records every ``execute`` call and
    returns scripted results keyed by skill name.

    Each call appends to ``self.calls`` a tuple ``(skill, op, context_keys)``
    so tests can assert call ordering and skill-swap behaviour.
    """

    def __init__(self, script: dict[str, list[StepResult]]):
        super().__init__()
        self._script = script  # skill_name -> [StepResult, ...] (consumed in order)
        self.calls: list[tuple[str, str, dict]] = []

    def validate_skill(self, skill: str) -> bool:  # type: ignore[override]
        # All scripted skills are valid for these tests.
        return skill in self._script

    def get_product(self, skill: str) -> str | None:  # type: ignore[override]
        return {"qcloud-cvm-ops": "cvm", "qcloud-vpc-ops": "vpc"}.get(skill)

    def execute(self, step: PlanStep, context: dict) -> StepResult:  # type: ignore[override]
        skill = step.skill or ""
        ctx_keys = tuple(sorted((context or {}).keys()))
        self.calls.append((skill, step.operation, ctx_keys))
        queue = self._script.get(skill)
        assert queue is not None, f"no script for skill {skill!r}"
        assert queue, f"scripted results exhausted for {skill!r}"
        return queue.pop(0)


def _make_step(*, step_id: str = "s1", skill: str = "qcloud-cvm-ops",
               operation: str = "describe-instances",
               destructive: bool = False) -> PlanStep:
    # Use a whitelisted (SAFE_OPERATIONS) operation so the h-check passes
    # and the skill dispatcher is actually called.
    return PlanStep(
        id=step_id,
        type="skill_call",
        skill=skill,
        operation=operation,
        params={"operation": operation},
        destructive=destructive,
    )


def _failure(error: str, error_code: str | None = None) -> StepResult:
    out: dict[str, Any] = {}
    if error_code:
        out["error_code"] = error_code
    return StepResult(
        step_id="s1", status="failure", error=error, output=out,
    )


def _success() -> StepResult:
    return StepResult(step_id="s1", status="success", output={"ok": True})


def _make_plan(steps: list[PlanStep]) -> Any:
    from copilot.models import ClassifiedIntent, ExecutionPlan, IntentType
    return ExecutionPlan(
        intent=ClassifiedIntent(primary=IntentType.ACT, targets=[], confidence=1.0),
        steps=steps,
    )


class _FakeBlackboard:
    def load(self, _session_id: str) -> dict:
        return {}

    def read_contributions(self, _session_id: str) -> dict:
        return {}

    def write_contribution(self, *_args, **_kwargs) -> None:  # no-op
        return None

    def write_plan_snapshot(self, *_args, **_kwargs) -> None:
        return None


class EscalatorHaltTests(unittest.TestCase):
    """HALT action short-circuits to failure; no retry."""

    def test_unknown_code_default_halt(self):
        esc = ErrorEscalator()
        # No rules → resolve() returns safe HALT default.
        skill_disp = _RecordingSkillDispatcher({"qcloud-cvm-ops": [_failure("boom")]})
        d = PlanDispatcher(skill_dispatcher=skill_disp, error_escalator=esc)
        step = _make_step()
        result = d._execute_step(
            step, _make_plan([step]), _FakeBlackboard(), "session-x",
        )
        self.assertEqual(result.status, "failure")
        # Only the original call happened — no retry on HALT.
        self.assertEqual(len(skill_disp.calls), 1)
        self.assertEqual(skill_disp.calls[0][0], "qcloud-cvm-ops")

    def test_explicit_halt_rule_does_not_retry(self):
        esc = ErrorEscalator()
        esc.add_rule(ErrorRule(code="Boom", action=Action.HALT))
        skill_disp = _RecordingSkillDispatcher({"qcloud-cvm-ops": [_failure("Boom happened")]})
        d = PlanDispatcher(skill_dispatcher=skill_disp, error_escalator=esc)
        step = _make_step()
        result = d._execute_step(
            step, _make_plan([step]), _FakeBlackboard(), "session-x",
        )
        self.assertEqual(result.status, "failure")
        self.assertEqual(len(skill_disp.calls), 1,
                         "HALT must not trigger any retry")


class EscalatorRetryTests(unittest.TestCase):
    """RETRY action re-executes the step up to max_retries."""

    def test_retry_succeeds_on_second_attempt(self):
        # The skill fails twice then succeeds. The escalator must retry
        # until success or max_retries is exhausted.
        esc = ErrorEscalator()
        esc.add_rule(ErrorRule(
            code="Flaky", action=Action.RETRY,
            max_retries=3, backoff_strategy="fixed",
        ))
        skill_disp = _RecordingSkillDispatcher({
            "qcloud-cvm-ops": [_failure("Flaky timeout"), _success()],
        })
        d = PlanDispatcher(skill_dispatcher=skill_disp, error_escalator=esc)
        step = _make_step()
        result = d._execute_step(
            step, _make_plan([step]), _FakeBlackboard(), "session-x",
        )
        self.assertEqual(result.status, "success",
                         "RETRY must give up to max_retries attempts")
        self.assertEqual(len(skill_disp.calls), 2,
                         "should have made 1 initial + 1 retry call")
        self.assertEqual(result.retry_count, 1)

    def test_retry_exhausts_then_fails(self):
        esc = ErrorEscalator()
        esc.add_rule(ErrorRule(
            code="Flaky", action=Action.RETRY,
            max_retries=2, backoff_strategy="fixed",
        ))
        skill_disp = _RecordingSkillDispatcher({
            "qcloud-cvm-ops": [_failure("Flaky"), _failure("Flaky"), _failure("Flaky")],
        })
        d = PlanDispatcher(skill_dispatcher=skill_disp, error_escalator=esc)
        step = _make_step()
        result = d._execute_step(
            step, _make_plan([step]), _FakeBlackboard(), "session-x",
        )
        self.assertEqual(result.status, "failure",
                         "RETRY with all-fail attempts must return failure")
        # 1 initial + 2 retries = 3 calls
        self.assertEqual(len(skill_disp.calls), 3)


class EscalatorDelegateTests(unittest.TestCase):
    """DELEGATE action swaps step.skill and re-runs."""

    def test_cvm_invalidvpc_delegates_to_vpc_then_succeeds(self):
        """The headline scenario: CVM RunInstances hits InvalidVpc.NotFound,
        escalator returns DELEGATE → qcloud-vpc-ops, dispatcher swaps
        step.skill and re-runs CreateVpc, then CVM RunInstances succeeds."""
        esc = ErrorEscalator()
        esc.add_rule(ErrorRule(
            code="InvalidVpc.NotFound", product="cvm",
            action=Action.DELEGATE, delegate_to="qcloud-vpc-ops",
        ))
        # First CVM call: InvalidVpc.NotFound
        # Then VPC call: success
        # Then CVM call: success
        skill_disp = _RecordingSkillDispatcher({
            "qcloud-cvm-ops": [
                _failure("`InvalidVpc.NotFound` from tccli", "InvalidVpc.NotFound"),
                _success(),
            ],
            "qcloud-vpc-ops": [_success()],
        })
        d = PlanDispatcher(skill_dispatcher=skill_disp, error_escalator=esc)
        step = _make_step()
        result = d._execute_step(
            step, _make_plan([step]), _FakeBlackboard(), "session-x",
        )
        # Final result is success (CVM retry after VPC succeeded).
        self.assertEqual(result.status, "success")
        # Calls recorded: cvm(fail), vpc(success), cvm(success) = 3 total
        self.assertEqual(len(skill_disp.calls), 3)
        self.assertEqual(skill_disp.calls[0][0], "qcloud-cvm-ops")
        self.assertEqual(skill_disp.calls[1][0], "qcloud-vpc-ops")
        self.assertEqual(skill_disp.calls[2][0], "qcloud-cvm-ops")
        # step.skill must be restored to the original after delegation.
        self.assertEqual(step.skill, "qcloud-cvm-ops")

    def test_delegate_target_unknown_skill_halts(self):
        """A DELEGATE rule pointing at a non-existent skill must HALT
        safely rather than crash."""
        esc = ErrorEscalator()
        esc.add_rule(ErrorRule(
            code="BadCode", action=Action.DELEGATE, delegate_to="qcloud-bogus",
        ))
        skill_disp = _RecordingSkillDispatcher({
            "qcloud-cvm-ops": [_failure("BadCode happened")],
        })
        d = PlanDispatcher(skill_dispatcher=skill_disp, error_escalator=esc)
        step = _make_step()
        result = d._execute_step(
            step, _make_plan([step]), _FakeBlackboard(), "session-x",
        )
        self.assertEqual(result.status, "failure")
        self.assertIn("qcloud-bogus", result.error or "")


class EscalatorFixTests(unittest.TestCase):
    """FIX action retries once."""

    def test_fix_retries_once(self):
        esc = ErrorEscalator()
        esc.add_rule(ErrorRule(
            code="ImageIdMalformed", action=Action.FIX, max_retries=1,
        ))
        skill_disp = _RecordingSkillDispatcher({
            "qcloud-cvm-ops": [_failure("ImageIdMalformed"), _success()],
        })
        d = PlanDispatcher(skill_dispatcher=skill_disp, error_escalator=esc)
        step = _make_step()
        result = d._execute_step(
            step, _make_plan([step]), _FakeBlackboard(), "session-x",
        )
        self.assertEqual(result.status, "success")
        self.assertEqual(len(skill_disp.calls), 2,
                         "FIX should retry exactly once")
        self.assertEqual(result.retry_count, 1)


class EscalatorDestructiveRetryGuardTests(unittest.TestCase):
    """BLOCKER-2: destructive ops must NOT be re-executed on RETRY/FIX
    without a fresh L2 confirmation (double-apply of non-idempotent
    delete-instance / release-eip / delete-bucket style actions)."""

    def test_destructive_retry_halts_without_l2(self):
        esc = ErrorEscalator()
        esc.add_rule(ErrorRule(
            code="Flaky", action=Action.RETRY,
            max_retries=3, backoff_strategy="fixed",
        ))
        skill_disp = _RecordingSkillDispatcher({
            "qcloud-cvm-ops": [_failure("Flaky timeout")],
        })
        d = PlanDispatcher(skill_dispatcher=skill_disp, error_escalator=esc)
        step = _make_step(destructive=True)
        result = d._apply_escalation(
            _failure("Flaky timeout"), step, {}, l2_confirmed=False,
        )
        self.assertNotEqual(result.status, "success",
                            "destructive retry without L2 must not succeed")
        self.assertEqual(result.retry_count, 0,
                         "destructive step must not be re-executed on retry")
        self.assertIn("destructive", result.error or "")
        # No retry/dispatch call beyond the original failure.
        self.assertEqual(len(skill_disp.calls), 0,
                         "no skill dispatch should happen on guarded retry")

    def test_destructive_fix_halts_without_l2(self):
        esc = ErrorEscalator()
        esc.add_rule(ErrorRule(
            code="ImageIdMalformed", action=Action.FIX, max_retries=1,
        ))
        skill_disp = _RecordingSkillDispatcher({
            "qcloud-cvm-ops": [_failure("ImageIdMalformed")],
        })
        d = PlanDispatcher(skill_dispatcher=skill_disp, error_escalator=esc)
        step = _make_step(destructive=True)
        result = d._apply_escalation(
            _failure("ImageIdMalformed"), step, {}, l2_confirmed=False,
        )
        self.assertNotEqual(result.status, "success")
        self.assertEqual(result.retry_count, 0,
                         "destructive FIX must not fire a second call")
        self.assertIn("destructive", result.error or "")
        self.assertEqual(len(skill_disp.calls), 0)

    def test_destructive_retry_allowed_with_l2(self):
        """With l2_confirmed=True the normal RETRY path still runs."""
        esc = ErrorEscalator()
        esc.add_rule(ErrorRule(
            code="Flaky", action=Action.RETRY,
            max_retries=3, backoff_strategy="fixed",
        ))
        skill_disp = _RecordingSkillDispatcher({
            "qcloud-cvm-ops": [_success()],
        })
        d = PlanDispatcher(skill_dispatcher=skill_disp, error_escalator=esc)
        step = _make_step(destructive=True)
        result = d._apply_escalation(
            _failure("Flaky timeout"), step, {}, l2_confirmed=True,
        )
        self.assertEqual(result.status, "success",
                         "L2-confirmed destructive retry may proceed")
        self.assertEqual(result.retry_count, 1)
        self.assertEqual(len(skill_disp.calls), 1)


class EscalatorErrorCodeExtractionTests(unittest.TestCase):
    """Error code extraction from various error message shapes."""

    def test_backtick_code_extracted(self):
        esc = ErrorEscalator()
        esc.add_rule(ErrorRule(code="AuthFailure", action=Action.HALT))
        skill_disp = _RecordingSkillDispatcher({
            "qcloud-cvm-ops": [_failure("`AuthFailure` from API")],
        })
        d = PlanDispatcher(skill_dispatcher=skill_disp, error_escalator=esc)
        step = _make_step()
        result = d._execute_step(
            step, _make_plan([step]), _FakeBlackboard(), "session-x",
        )
        self.assertEqual(result.error_code, "AuthFailure")

    def test_explicit_error_code_field_used(self):
        esc = ErrorEscalator()
        esc.add_rule(ErrorRule(code="Inner.Code", action=Action.HALT))
        # When output["error_code"] is set, that wins over backtick parsing.
        skill_disp = _RecordingSkillDispatcher({
            "qcloud-cvm-ops": [
                StepResult(
                    step_id="s1", status="failure",
                    error="Some other message",
                    output={"error_code": "Inner.Code"},
                ),
            ],
        })
        d = PlanDispatcher(skill_dispatcher=skill_disp, error_escalator=esc)
        step = _make_step()
        result = d._execute_step(
            step, _make_plan([step]), _FakeBlackboard(), "session-x",
        )
        self.assertEqual(result.error_code, "Inner.Code")


if __name__ == "__main__":
    unittest.main()