from __future__ import annotations

# Phase 1.3: ErrorEscalator bridges skill errors to runtime actions
# (HALT / RETRY / FIX / DELEGATE). Lazy-imported in _execute_step to
# avoid forcing a scripts/ import on package init.
import sys as _sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from contextlib import suppress
from pathlib import Path as _Path

from copilot.ask_user_runner import AskUserRunner
from copilot.blackboard import BlackboardClient
from copilot.integration.alert_intel import AlertIntelRunner
from copilot.integration.cruise import CruiseRunner
from copilot.integration.skills import SkillDispatcher
from copilot.models import ExecutionPlan, PlanStep, StepResult
from copilot.observ import ObservableSink, Span, TraceSpan
from copilot.plan_schema import resolve_blackboard_paths
from copilot.quality.audit import audit_trace
from copilot.quality.hallucination import check_h
from copilot.quality.health import record_health
from copilot.quality.reflexion import write_reflexion
from copilot.report_gen import synthesize_from_blackboard

_SCRIPTS = str(_Path(__file__).resolve().parents[2] / "scripts")
if _SCRIPTS not in _sys.path:
    _sys.path.insert(0, _SCRIPTS)
from error_escalator import Action as _EscalationAction
from error_escalator import ErrorEscalator as _ErrorEscalator
from tcloud_error_codes import (
    PRODUCT_ERROR_CODES as _PRODUCT_ERROR_CODES,
)
from tcloud_error_codes import (
    to_error_rule as _to_error_rule,
)

STEP_TIMEOUT = 300


class PlanDispatcher:
    """Execute multi-step plans with blackboard read/write (Phase 3: parallel groups)."""

    def __init__(
        self,
        skill_dispatcher: SkillDispatcher | None = None,
        cruise_runner: CruiseRunner | None = None,
        alert_runner: AlertIntelRunner | None = None,
        ask_user_runner: AskUserRunner | None = None,
        error_escalator: _ErrorEscalator | None = None,
    ) -> None:
        self._skill_dispatcher = skill_dispatcher or SkillDispatcher()
        self._cruise_runner = cruise_runner or CruiseRunner()
        self._alert_runner = alert_runner or AlertIntelRunner()
        self._ask_user_runner = ask_user_runner or AskUserRunner()
        # Phase 1.3: default ErrorEscalator is preloaded with the
        # product-level registry (InvalidVpc.NotFound → DELEGATE etc.).
        # Callers may inject a custom one for tests.
        if error_escalator is not None:
            self._error_escalator = error_escalator
        else:
            esc = _ErrorEscalator()
            for rec in _PRODUCT_ERROR_CODES:
                esc.add_rule(_to_error_rule(rec))
            self._error_escalator = esc

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
                        skill=step.skill,
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
                # Phase 1.3: classify failure via ErrorEscalator and act.
                # We do NOT swallow a "success" result here; only failures
                # get escalated. Success keeps the original output/error_code
                # unchanged so callers downstream see no behaviour drift.
                if result.status != "success":
                    result = self._apply_escalation(
                        result, step, context, l2_confirmed=l2_confirmed
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
        self._emit_span(session_id, step, result)

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

    # ---- Phase 1.3: ErrorEscalator integration -----------------------------

    # Backticked code (e.g. `InvalidVpc.NotFound`) is the most reliable
    # machine-readable signal in a free-text error message. Falls back to
    # the leading word, then None.
    _ERR_CODE_BACKTICK_RE = __import__("re").compile(r"`([A-Za-z][A-Za-z0-9_.]*)`")
    _ERR_CODE_FIRST_WORD_RE = __import__("re").compile(r"\b([A-Z][A-Za-z0-9_.]+)\b")

    def _extract_error_code(self, result: StepResult, step: PlanStep) -> str | None:
        """Best-effort extraction of a Tencent Cloud API error code.

        Sources, in priority order:

        1. ``result.output["error_code"]`` — when the skill dispatcher
           already parsed the API response and surfaced the code.
        2. Backticked token in ``result.error`` (most reliable prose signal).
        3. First CamelCase token in ``result.error``.
        4. ``None`` when nothing usable was found (escalator then falls
           back to its safe-default HALT rule).
        """
        out = result.output or {}
        if isinstance(out, dict) and out.get("error_code"):
            return str(out["error_code"])
        if result.error:
            m = self._ERR_CODE_BACKTICK_RE.search(result.error)
            if m:
                return m.group(1)
            m = self._ERR_CODE_FIRST_WORD_RE.search(result.error)
            if m:
                return m.group(1)
        return None

    def _apply_escalation(
        self,
        result: StepResult,
        step: PlanStep,
        context: dict,
        *,
        l2_confirmed: bool = False,
    ) -> StepResult:
        """Classify ``result`` via ErrorEscalator and branch on Action.

        Behaviour:

        * **HALT**       → return failure untouched (caller stops plan).
        * **RETRY**      → re-execute ``step`` up to ``rule.max_retries``
          times, sleeping ``compute_backoff(strategy, attempt)`` between
          attempts. Returns the last attempt's result.
        * **FIX**        → retry once (the skill itself is expected to
          patch the call; we just give it another shot).
        * **DELEGATE**   → swap ``step.skill`` for ``rule.delegate_to``,
          re-dispatch via the skill dispatcher, then restore the original
          skill name on the result. Up to ``max_retries`` delegate hops.
        """
        error_code = self._extract_error_code(result, step)
        product = self._skill_dispatcher.get_product(step.skill or "") or ""
        rule = self._error_escalator.resolve(error_code or "", product)
        result.error_code = error_code or rule.code
        result.delegate_to = rule.delegate_to

        if rule.action == _EscalationAction.HALT:
            # Caller will see the failure and stop the plan.
            return result

        if rule.action == _EscalationAction.DELEGATE and rule.delegate_to:
            delegate_to = rule.delegate_to
            if not self._skill_dispatcher.validate_skill(delegate_to):
                # Misconfigured delegate target — fail safe (HALT).
                result.error = (
                    f"{result.error or 'unknown'}; "
                    f"delegate_to={delegate_to!r} is not a known skill"
                )
                return result
            original_skill = step.skill
            # Phase 1.4: emit a "delegated" span for the cross-skill hop.
            # The DELEGATE marker span carries the parent_span_id so the
            # downstream VPC/CAM/etc. spans become children of the original
            # CVM step span. _current_parent_span_id is reset after.
            trace_id = getattr(self, "_trace_id", None) or ""
            parent_span_id = getattr(self, "_current_parent_span_id", None)
            with suppress(Exception):
                ObservableSink().emit_trace_span(
                    TraceSpan(
                        span_id=f"{trace_id}:{step.id}:delegate",
                        trace_id=trace_id,
                        parent_span_id=parent_span_id,
                        run_id=getattr(self, "_session_id", "local"),
                        skill="qcloud-copilot",
                        operation="escalator.delegate",
                        step_id=f"{step.id}.delegate",
                        status="delegated",
                        delegate_to=delegate_to,
                        error_code=result.error_code,
                    )
                )
            step.skill = delegate_to
            try:
                delegated = self._execute_with_timeout(
                    lambda: self._skill_dispatcher.execute(step, context),
                    step.id,
                )
                # Phase 1.4: emit child span for the delegated skill call.
                with suppress(Exception):
                    ObservableSink().emit_trace_span(
                        TraceSpan(
                            span_id=f"{trace_id}:{step.id}:{delegate_to}",
                            trace_id=trace_id,
                            parent_span_id=parent_span_id,
                            run_id=getattr(self, "_session_id", "local"),
                            skill=delegate_to,
                            operation=step.operation or step.type,
                            step_id=f"{step.id}.{delegate_to}",
                            status=delegated.status,
                            duration_ms=delegated.duration_ms,
                            error_code=delegated.error_code,
                        )
                    )
                result.retry_count += 1
                if delegated.status == "success":
                    # Delegate succeeded — now retry the ORIGINAL step
                    # (CVM RunInstances) once. The delegation's purpose is
                    # to fix the upstream state (VPC created), so the
                    # original call should be retried. If it still fails,
                    # HALT and surface the new error.
                    step.skill = original_skill
                    retried = self._execute_with_timeout(
                        lambda: self._skill_dispatcher.execute(step, context),
                        step.id,
                    )
                    retried.retry_count = result.retry_count
                    retried.delegate_to = delegate_to
                    if retried.status == "success":
                        return retried
                    # Original still failing — surface that result.
                    return retried
                # Delegated call itself failed — return that result so the
                # caller can decide whether to halt or fall through.
                return delegated
            finally:
                step.skill = original_skill

        # Destructive steps must not be silently re-executed on retry: the L2
        # confirmation ran once before the first attempt; a RETRY/FIX re-fires
        # the op with no fresh confirmation and can double-apply non-idempotent
        # actions (delete-instance / release-eip / delete-bucket). HALT instead.
        if (
            rule.action in (_EscalationAction.RETRY, _EscalationAction.FIX)
            and step.destructive
            and not l2_confirmed
        ):
            result.error = (
                f"{result.error or 'unknown'}; destructive op not re-executed "
                "without L2 confirmation"
            )
            return result

        if rule.action == _EscalationAction.RETRY and rule.max_retries > 0:
            last = result
            for attempt in range(rule.max_retries):
                backoff = self._error_escalator.compute_backoff(
                    rule.backoff_strategy, attempt
                )
                with suppress(Exception):
                    time.sleep(backoff)
                last = self._execute_with_timeout(
                    lambda: self._skill_dispatcher.execute(step, context),
                    step.id,
                )
                last.retry_count = attempt + 1
                if last.status == "success":
                    return last
            return last

        if rule.action == _EscalationAction.FIX:
            # FIX = skill self-corrected and asked for one more shot.
            fixed = self._execute_with_timeout(
                lambda: self._skill_dispatcher.execute(step, context),
                step.id,
            )
            fixed.retry_count = 1
            return fixed

        # Unknown action or no-op rule — leave the failure in place.
        return result

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
                skill=step.skill,
            )

    def _emit_health(self, step: PlanStep, result: StepResult, session_id: str) -> None:
        with suppress(Exception):
            record_health(
                skill=step.skill or "qcloud-copilot",
                operation=step.operation or step.type,
                status="ok" if result.status == "success" else "error",
                duration_ms=result.duration_ms,
                trace_id=session_id,
                source="step",
            )

    def _emit_span(self, session_id: str, step: PlanStep, result: StepResult) -> None:
        # Legacy v1 sink (kept for backward compat with observ_query).
        error_code = None
        if result.status != "success" and result.error:
            # First token of the step error is the machine-readable failure signal
            # (e.g. "H gate failed: ..." -> "H", "boom" -> "boom").
            error_code = result.error.split()[0] if result.error.split() else step.type
        with suppress(Exception):
            ObservableSink().emit_span(
                Span(
                    run_id=session_id,
                    # Key spans by skill name so the observ_query layer
                    # (skill_success_rate / p_latency / top_failed_operations)
                    # can match them; step.id is an internal plan identifier.
                    step_id=step.skill or "qcloud-copilot",
                    status=result.status,
                    duration_ms=result.duration_ms,
                    error_code=error_code,
                )
            )
        # Phase 1.4 — unified TraceSpan (parent-child chain; cross-skill
        # delegation is captured via step.skill swap in _apply_escalation).
        with suppress(Exception):
            ObservableSink().emit_trace_span(
                TraceSpan(
                    span_id=f"{session_id}:{step.id}",
                    trace_id=getattr(self, "_trace_id", None) or session_id,
                    parent_span_id=getattr(self, "_current_parent_span_id", None),
                    run_id=session_id,
                    skill=step.skill or "qcloud-copilot",
                    operation=step.operation or step.type,
                    step_id=step.id,
                    status=result.status,
                    duration_ms=result.duration_ms,
                    error_code=result.error_code or error_code,
                    delegate_to=result.delegate_to,
                    metadata={"destructive": step.destructive},
                )
            )
