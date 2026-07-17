from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from contextlib import suppress

from copilot.ask_user_runner import AskUserRunner
from copilot.blackboard import BlackboardClient
from copilot.integration.alert_intel import AlertIntelRunner
from copilot.integration.cruise import CruiseRunner
from copilot.integration.skills import SkillDispatcher
from copilot.models import ExecutionPlan, PlanStep, StepResult
from copilot.plan_schema import resolve_blackboard_paths
from copilot.quality.audit import audit_trace
from copilot.quality.health import record_health
from copilot.quality.hallucination import check_h
from copilot.quality.reflexion import write_reflexion
from copilot.report_gen import synthesize_from_blackboard

STEP_TIMEOUT = 300


class PlanDispatcher:
    """Execute multi-step plans with blackboard read/write (Phase 3: parallel groups)."""

    def __init__(
        self,
        skill_dispatcher: SkillDispatcher | None = None,
        cruise_runner: CruiseRunner | None = None,
        alert_runner: AlertIntelRunner | None = None,
        ask_user_runner: AskUserRunner | None = None,
    ) -> None:
        self._skill_dispatcher = skill_dispatcher or SkillDispatcher()
        self._cruise_runner = cruise_runner or CruiseRunner()
        self._alert_runner = alert_runner or AlertIntelRunner()
        self._ask_user_runner = ask_user_runner or AskUserRunner()

    def execute(
        self,
        plan: ExecutionPlan,
        blackboard: BlackboardClient,
        session_id: str,
        *,
        parallel: bool | None = None,
        l2_confirmed: bool = False,
    ) -> list[StepResult]:
        if plan.plan_id:
            blackboard.write_plan_snapshot(session_id, plan)

        if parallel is None:
            parallel = int(plan.dispatch_config.get("max_parallel_groups", 1)) > 1

        step_index = {step.id: idx for idx, step in enumerate(plan.steps)}
        results: list[StepResult] = []
        completed: dict[str, StepResult] = {}
        remaining = {step.id: step for step in plan.steps}
        stop_on_critical = bool(plan.dispatch_config.get("stop_on_first_critical", True))

        while remaining:
            ready = [
                step
                for step in remaining.values()
                if all(dep in completed for dep in step.depends_on)
            ]
            if not ready:
                for step in remaining.values():
                    results.append(
                        StepResult(
                            step_id=step.id,
                            status="skipped",
                            error=f"Dependency not met: {step.depends_on}",
                        )
                    )
                break

            ready.sort(key=lambda s: (s.parallel_group, step_index[s.id]))
            min_group = ready[0].parallel_group
            batch = [step for step in ready if step.parallel_group == min_group]
            use_parallel = parallel and len(batch) > 1

            batch_outcomes = self._execute_batch(
                batch,
                plan,
                blackboard,
                session_id,
                completed,
                parallel=use_parallel,
                l2_confirmed=l2_confirmed,
            )
            batch_outcomes.sort(key=lambda item: step_index[item[0].id])

            critical_stop = False
            for step, result in batch_outcomes:
                results.append(result)
                completed[step.id] = result
                remaining.pop(step.id)
                if stop_on_critical and self._step_is_critical(blackboard, session_id, result):
                    critical_stop = True

            if critical_stop:
                for pending in list(remaining.values()):
                    results.append(
                        StepResult(
                            step_id=pending.id,
                            status="skipped",
                            error="Stopped after CRITICAL contribution",
                        )
                    )
                    remaining.pop(pending.id)
                break

        return results

    def _execute_batch(
        self,
        batch: list[PlanStep],
        plan: ExecutionPlan,
        blackboard: BlackboardClient,
        session_id: str,
        completed: dict[StepResult],
        *,
        parallel: bool,
        l2_confirmed: bool = False,
    ) -> list[tuple[PlanStep, StepResult]]:
        outcomes: list[tuple[PlanStep, StepResult]] = []

        def run_step(step: PlanStep) -> tuple[PlanStep, StepResult]:
            dep_failures = [
                completed[dep]
                for dep in step.depends_on
                if completed[dep].status in ("failure", "skipped")
            ]
            if dep_failures:
                return step, StepResult(
                    step_id=step.id,
                    status="skipped",
                    error=(
                        f"Depends on failed/skipped step(s): {[f.step_id for f in dep_failures]}"
                    ),
                )
            return step, self._execute_step(
                step, plan, blackboard, session_id, l2_confirmed=l2_confirmed
            )

        runnable = list(batch)
        if parallel and len(runnable) > 1:
            with ThreadPoolExecutor(max_workers=len(runnable)) as pool:
                futures = {pool.submit(run_step, step): step for step in runnable}
                for future in as_completed(futures):
                    outcomes.append(future.result())
        else:
            for step in runnable:
                outcomes.append(run_step(step))

        return outcomes

    def _step_is_critical(
        self,
        blackboard: BlackboardClient,
        session_id: str,
        result: StepResult,
    ) -> bool:
        if result.output and result.output.get("has_critical"):
            return True
        with suppress(Exception):
            contributions = blackboard.read_contributions(session_id)
            return any(c.get("verdict") == "CRITICAL" for c in contributions.values())
        return False

    def _execute_step(
        self,
        step: PlanStep,
        plan: ExecutionPlan,
        blackboard: BlackboardClient,
        session_id: str,
        *,
        l2_confirmed: bool = False,
    ) -> StepResult:
        start = time.time()
        context = dict(plan.context)
        h_result: dict | None = None

        if step.reads_from_blackboard:
            board = blackboard.load(session_id) or {}
            context.update(resolve_blackboard_paths(board, step.reads_from_blackboard))

        if step.type == "skill_call":
            # Emit a per-step L2 confirmation trace for destructive operations so
            # the trajectory-evaluation layer can see whether the destructive
            # op was confirmed (fixes C7 safety blind spot at step granularity).
            if step.destructive:
                with suppress(Exception):
                    audit_trace(
                        session_id=session_id,
                        step_id=f"{step.id}.l2",
                        trace_data={
                            "step_type": "safety_gate",
                            "status": "pass" if l2_confirmed else "unconfirmed",
                            "destructive": True,
                            "skill": step.skill,
                            "operation": step.operation,
                        },
                        provenance={
                            "eval_id": f"{session_id}:{step.id}.l2:safety.l2_confirm",
                            "rule": "safety.l2_confirm",
                            "input_ref": f"step.skill={step.skill}, step.operation={step.operation}",
                            "decision": "pass" if l2_confirmed else "fail",
                            "reason": "destructive op confirmed via L2 gate"
                            if l2_confirmed
                            else "destructive op executed without L2 confirmation",
                        },
                    )
            h_result = check_h(step)
            if not h_result["passed"]:
                result = StepResult(
                    step_id=step.id,
                    status="failure",
                    error=f"H gate failed: {', '.join(h_result['issues'])}",
                )
            else:
                result = self._execute_with_timeout(
                    lambda: self._skill_dispatcher.execute(step, context),
                    step.id,
                )
        elif step.type == "cruise_run":
            result = self._execute_with_timeout(
                lambda: self._cruise_runner.execute(
                    step,
                    context,
                    blackboard=blackboard,
                    session_id=session_id,
                ),
                step.id,
            )
        elif step.type == "alert_analyze":
            result = self._execute_with_timeout(
                lambda: self._run_alert(step, blackboard, session_id),
                step.id,
            )
        elif step.type == "synthesize_report":
            result = self._execute_with_timeout(
                lambda: self._run_synthesize(step, blackboard, session_id),
                step.id,
            )
        elif step.type == "report":
            error_msg = step.params.get("error", "")
            result = StepResult(
                step_id=step.id,
                status="failure" if error_msg else "success",
                output={"description": step.description, **step.params},
                error=error_msg if error_msg else None,
            )
        elif step.type == "ask_user":
            # Defense in depth: spec §3.7 requires CI to refuse ask_user.
            # mode_gate.plan_gen.generate() skips region discovery in CI so
            # _cruise_plan never inserts ask-region-0 in CI; this branch is
            # the second line of defense if a planner slips an ask_user in.
            inspection_effective = (
                plan.context.get("inspection_effective", "delivery")
                if isinstance(plan.context, dict)
                else "delivery"
            )
            if inspection_effective in ("ci", "fallback"):
                result = StepResult(
                    step_id=step.id,
                    status="failure",
                    error=(
                        f"ask_user step '{step.id}' rejected: inspection mode "
                        f"'{inspection_effective}' is non-interactive. Re-plan "
                        "without ask_user or switch to delivery mode."
                    ),
                )
            else:
                result = self._execute_with_timeout(
                    lambda: self._ask_user_runner.execute(
                        step,
                        context,
                        blackboard,
                        session_id,
                    ),
                    step.id,
                )
        else:
            # Unknown step type → fail-fast (spec §3.7). Previously this was a
            # silent success which masked planner bugs.
            result = StepResult(
                step_id=step.id,
                status="failure",
                error=(
                    f"Unknown step type: {step.type!r}. Plan dispatch cannot "
                    "fall through silently — fix the planner."
                ),
            )

        if (
            step.writes_to_blackboard
            and step.skill
            and step.type not in ("cruise_run", "alert_analyze")
            and result.status == "success"
        ):
            self._write_step_contribution(blackboard, session_id, step, result)

        result.duration_ms = int((time.time() - start) * 1000)

        provenance: dict | None = None
        if step.type == "skill_call" and h_result is not None:
            op = step.params.get("operation", "") if step.params else ""
            h_passed = h_result["passed"]
            provenance = {
                "eval_id": f"{session_id}:{step.id}:check_h",
                "rule": "hallucination.KNOWN_OPERATIONS",
                "input_ref": f"step.skill={step.skill}, step.params.operation={op}",
                "decision": "pass" if h_passed else "fail",
                "reason": (
                    "operation in whitelist"
                    if h_passed
                    else "; ".join(h_result.get("issues", []))
                ),
            }

        self._emit_trace(session_id, step, result, provenance=provenance)
        self._emit_health(step, result, session_id)

        if result.status == "failure":
            with suppress(Exception):
                write_reflexion(
                    category="engine_step",
                    skill=step.skill or step.type,
                    command=f"{step.type}:{step.id}",
                    error=result.error or "unknown",
                    fix="See step trace",
                )

        return result

    def _run_alert(
        self,
        step: PlanStep,
        blackboard: BlackboardClient,
        session_id: str,
    ) -> StepResult:
        contribution = self._alert_runner.analyze(step.params, blackboard, session_id)
        has_critical = contribution.get("verdict") == "CRITICAL"
        return StepResult(
            step_id=step.id,
            status="success",
            output={"contribution": contribution, "has_critical": has_critical},
        )

    def _run_synthesize(
        self,
        step: PlanStep,
        blackboard: BlackboardClient,
        session_id: str,
    ) -> StepResult:
        audience = step.params.get("audience", "detailed")
        contributions = blackboard.read_contributions(session_id)
        board = blackboard.load(session_id)
        report = synthesize_from_blackboard(
            contributions,
            audience=audience,
            user_request=board.get("user_request", ""),
        )
        has_critical = any(c.get("verdict") == "CRITICAL" for c in contributions.values())
        return StepResult(
            step_id=step.id,
            status="success",
            output={
                "report": report,
                "has_critical": has_critical,
            },
        )

    def _write_step_contribution(
        self,
        blackboard: BlackboardClient,
        session_id: str,
        step: PlanStep,
        result: StepResult,
    ) -> None:
        skill = step.skill or ""
        if not skill:
            return
        contribution = {
            "version": "0.0.0",
            "verdict": "PASS" if result.status == "success" else "WARNING",
            "findings": [],
            "topology_hints": [],
            "metadata": {"output": result.output or {}},
        }
        blackboard.write_contribution(session_id, skill, contribution)

    def _execute_with_timeout(self, fn, step_id: str) -> StepResult:
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(fn)
                return future.result(timeout=STEP_TIMEOUT)
        except TimeoutError:
            return StepResult(
                step_id=step_id,
                status="failure",
                error=f"Step timed out after {STEP_TIMEOUT}s",
            )

    def _emit_trace(
        self,
        session_id: str,
        step: PlanStep,
        result: StepResult,
        provenance: dict | None = None,
    ) -> None:
        # P1: generic step path gets a default exec.step provenance so every
        # audit trace carries eval_id == <session_id>:<step_id>:exec.step,
        # matching the L2 gate's safety.l2_confirm shape. Caller-supplied
        # provenance (e.g. L2) is preserved untouched.
        if provenance is None:
            provenance = {
                "eval_id": f"{session_id}:{step.id}:exec.step",
                "rule": "exec.step",
                "input_ref": "step.result",
                "decision": result.status,
            }
        with suppress(Exception):
            audit_trace(
                session_id=session_id,
                step_id=step.id,
                trace_data={
                    "step_type": step.type,
                    "status": result.status,
                    "duration_ms": result.duration_ms,
                    "error": result.error,
                    "output": result.output,
                },
                provenance=provenance,
            )

    def _emit_health(self, step: PlanStep, result: StepResult, session_id: str) -> None:
        with suppress(Exception):
            record_health(
                skill=step.skill or "qcloud-copilot",
                operation=step.operation or step.type,
                status="ok" if result.status == "success" else "error",
                duration_ms=result.duration_ms,
                trace_id=session_id,
            )
