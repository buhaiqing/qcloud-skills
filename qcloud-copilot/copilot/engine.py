from __future__ import annotations

import time
from contextlib import suppress

from copilot.classifier import classify
from copilot.dispatcher import PlanDispatcher
from copilot.integration.cruise import CruiseRunner
from copilot.integration.skills import SkillDispatcher
from copilot.mode_resolver import resolve_inspection_mode, strip_ci_trigger_words
from copilot.models import (
    ExecutionPlan,
    ExecutionResult,
    Report,
    StepResult,
)
from copilot.observ import Metric, MetricKind, ObservableSink
from copilot.parser import parse
from copilot.plan_gen import generate as gen_plan
from copilot.plan_schema import load_plan_file
from copilot.quality.audit import audit_trace, audit_trace_v3
from copilot.quality.health import record_health
from copilot.report_gen import synthesize
from copilot.safety.l0 import check_l0
from copilot.safety.l1 import check_l1
from copilot.safety.l2 import check_l2
from copilot.safety.l3 import check_l3
from copilot.session import SessionManager


class CopilotEngine:
    """Main orchestrator: NL → Parse → Classify → Plan → Execute → Report."""

    def __init__(self):
        self._skill_dispatcher = SkillDispatcher()
        self._cruise_runner = CruiseRunner()
        self._plan_dispatcher = PlanDispatcher(
            skill_dispatcher=self._skill_dispatcher,
            cruise_runner=self._cruise_runner,
        )
        # EVO-1: lazy-init EvolutionPolicy so it does not force a
        # docs/ dependency when the copilot is imported as a library.
        self._evolution_policy = None  # type: ignore[assignment]

    def _init_evolution_policy(self) -> None:
        """Lazily bootstrap EvolutionPolicy (EVO-1 Generator component)."""
        if self._evolution_policy is not None:
            return
        try:
            from copilot import observ_query  # type: ignore[attr-defined]
            from copilot.evolution import EvolutionPolicy, EvolutionStore
            store = EvolutionStore()
            query_mod = getattr(observ_query, "query_metrics", None)
            self._evolution_policy = EvolutionPolicy(store=store, query=query_mod)
        except Exception:  # noqa: BLE001
            self._evolution_policy = None

    # -------------------------------------------------------------------------
    # EVO-1 subagent fan-out — 3 parallel subagents query one signal each
    # -------------------------------------------------------------------------

    def _query_evolution(self, skill: str, intent) -> EvolutionSignals:  # noqa: F821
        """Fan out 3 subagents in parallel; aggregate into EvolutionSignals.

        Subagent 1 → route_hint    (EvolutionPolicy.route_hint)
        Subagent 2 → calibrated thresholds (recommend_threshold per dim)
        Subagent 3 → op_allowlist  (op_allowlist)

        Runs via thread pool so all 3 queries execute concurrently.
        Each subagent degrades gracefully when policy is None or raises.
        """
        from concurrent.futures import ThreadPoolExecutor

        from copilot.evolution import (
            query_calibrated_thresholds,
            query_op_allowlist,
            query_route_hint,
        )
        from copilot.models import EvolutionSignals

        policy = self._evolution_policy
        # EVO-1: pass policy into SkillDispatcher so route_advice() can use it
        self._skill_dispatcher._evolution_policy = policy
        default_dims = ["correctness", "safety", "idempotency", "traceability", "spec_compliance"]

        with ThreadPoolExecutor(max_workers=3) as pool:
            f_route = pool.submit(query_route_hint, policy, intent)
            f_thresh = pool.submit(query_calibrated_thresholds, policy, skill, default_dims)
            f_allow = pool.submit(query_op_allowlist, policy, skill)

        route_hint = f_route.result()
        thresholds = f_thresh.result()
        allowlist = f_allow.result()

        source: str
        if policy is None:
            source = "none"
        elif thresholds or route_hint or allowlist:
            source = "evolution_policy"
        else:
            source = "store_only"

        return EvolutionSignals(
            skill=skill,
            route_hint=route_hint,
            calibrated_thresholds=thresholds,
            allowlist=allowlist,
            source=source,
        )

    def _apply_evo_signals(self, signals: EvolutionSignals) -> None:  # noqa: F821
        """Write EVO-1 signals into runtime state.

        - calibrated_thresholds  → EvolutionRegistry (read by gcl_runner)
        - route_hint           → stored on self._last_evo_signals (for injection)
        """
        from copilot.evolution import set_calibration_for_skill

        if signals.calibrated_thresholds:
            set_calibration_for_skill(signals.skill, signals.calibrated_thresholds)
        self._last_evo_signals = signals  # type: ignore[assignment]

    def _build_evo_context(self, signals: EvolutionSignals | None) -> dict:  # noqa: F821
        """Build evolution_context dict passed to PlanDispatcher."""
        if signals is None:
            return {}
        return {
            "evolution_warning": signals.route_hint,
            "evolution_source": signals.source,
            "evolution_allowlist": sorted(signals.allowlist) if signals.allowlist else [],
        }

    def ask(
        self,
        query: str,
        session_id: str | None = None,
        audience: str = "detailed",
        l2_confirmed: bool = False,
        l3_reviewed: bool = False,
        inspection_mode: str | None = None,
    ) -> Report:
        start = time.time()
        self._session_id = session_id or f"inline-{int(start * 1000)}"

        mode_result = resolve_inspection_mode(query, cli_mode=inspection_mode)
        self._inspection_mode_result = mode_result
        parse_query = strip_ci_trigger_words(query, mode_result.matched_keyword)

        prior_context = {}
        if session_id:
            sm = SessionManager()
            state = sm.load_session(session_id)
            if state:
                prior_context = state.context
            sm.init_blackboard(session_id, query)
            audit_trace(
                session_id=session_id,
                step_id="blackboard-init",
                trace_data={
                    "step_type": "blackboard_init",
                    "status": "success",
                    "user_request": query[:500],
                },
            )
            with suppress(Exception):
                audit_trace_v3(
                    sink=ObservableSink(),
                    session_id=session_id,
                    trace_id=session_id,
                    step_id="blackboard-init",
                    trace_data={
                        "step_type": "blackboard_init",
                        "status": "success",
                        "user_request": query[:500],
                    },
                    skill=None,
                    observation_name="event:blackboard-init",
                )
        parsed = parse(parse_query)
        intent = classify(parsed)

        l0_result = check_l0(parsed, intent)
        if not l0_result["passed"]:
            with suppress(Exception):
                ObservableSink().emit_gate(
                    self._session_id, "l0", "fail", "; ".join(l0_result["issues"])
                )
            with suppress(Exception):
                record_health(
                    skill="qcloud-copilot",
                    operation="ask",
                    status="error",
                    duration_ms=0,
                    trace_id=self._session_id,
                    error_code="l0",
                    source="gate",
                )
            return self._deliver_report(
                self._error_report(
                    f"L0 gate failed: {', '.join(l0_result['issues'])}",
                    parsed,
                    intent,
                    duration_ms=0,
                    audience=audience,
                )
            )

        plan = gen_plan(
            intent,
            context={
                **prior_context,
                **mode_result.to_context(),
                "user_query": query,
                "user_request": query,
                "audience": audience,
                **{k: (v[0] if len(v) == 1 else v) for k, v in parsed.entities.items() if v},
            },
        )

        self._plan_context = plan.context

        l1_result = check_l1(plan)
        if not l1_result["passed"]:
            with suppress(Exception):
                ObservableSink().emit_gate(
                    self._session_id, "l1", "fail", "; ".join(l1_result["issues"])
                )
            with suppress(Exception):
                record_health(
                    skill="qcloud-copilot",
                    operation="ask",
                    status="error",
                    duration_ms=0,
                    trace_id=self._session_id,
                    error_code="l1",
                    source="gate",
                )
            return self._deliver_report(
                self._error_report(
                    f"L1 gate failed: {', '.join(l1_result['issues'])}",
                    parsed,
                    intent,
                    duration_ms=0,
                    audience=audience,
                )
            )

        l2_result = check_l2(plan, confirmed=l2_confirmed)
        self._emit_l2_trace(
            session_id,
            plan,
            passed=l2_result["passed"],
            issues=l2_result["issues"],
        )
        if not l2_result["passed"]:
            with suppress(Exception):
                ObservableSink().emit_gate(
                    self._session_id, "l2", "fail", "; ".join(l2_result["issues"])
                )
            with suppress(Exception):
                record_health(
                    skill="qcloud-copilot",
                    operation="ask",
                    status="error",
                    duration_ms=0,
                    trace_id=self._session_id,
                    error_code="l2",
                    source="gate",
                )
            return self._deliver_report(
                self._error_report(
                    f"L2 gate failed: {', '.join(l2_result['issues'])}",
                    parsed,
                    intent,
                    duration_ms=0,
                    audience=audience,
                )
            )
        # EVO-1: bootstrap + fan-out before execution
        self._init_evolution_policy()
        skill = (intent.targets or ["qcloud-copilot"])[0]
        evo_signals = self._query_evolution(skill, intent)
        self._apply_evo_signals(evo_signals)

        exec_result = self._run_execution(
            plan, audience=audience, l3_reviewed=l3_reviewed, l2_confirmed=l2_confirmed,
            evo_signals=evo_signals,
        )
        exec_result.final_report.duration_ms = int((time.time() - start) * 1000)

        if exec_result.status == "aborted":
            return self._deliver_report(exec_result.final_report)

        with suppress(Exception):
            record_health(
                skill="qcloud-copilot",
                operation="ask",
                status="ok",
                duration_ms=exec_result.final_report.duration_ms,
                trace_id=self._session_id,
            )

        if session_id:
            sm = SessionManager()
            sm.get_or_create(session_id)
            sm.append_history(
                session_id,
                {
                    "query": query,
                    "intent": intent.primary.value,
                    "targets": intent.targets,
                },
            )
            context_updates = {}
            for k, v in parsed.entities.items():
                if v:
                    context_updates[k] = v[0] if len(v) == 1 else v
            if context_updates:
                sm.update_context(session_id, context_updates)

        report = self._deliver_report(exec_result.final_report)
        if session_id:
            self.record_feedback(session_id=session_id, adopted=True)
        return report

    def run_plan(
        self,
        plan: ExecutionPlan | str,
        session_id: str,
        *,
        audience: str = "detailed",
        dry_run: bool = False,
        l3_reviewed: bool = False,
        l2_confirmed: bool = False,
    ) -> Report | dict:
        if isinstance(plan, str):
            plan = load_plan_file(plan)

        if dry_run:
            return self._dry_run_plan(plan, session_id)

        self._init_evolution_policy()
        skill = (plan.intent.targets or ["qcloud-copilot"])[0]
        evo_signals = self._query_evolution(skill, plan.intent)
        self._apply_evo_signals(evo_signals)
        report = self._deliver_report(
            self._run_execution(
                plan, audience=audience, l3_reviewed=l3_reviewed, l2_confirmed=l2_confirmed,
                evo_signals=evo_signals,
            ).final_report
        )
        self.record_feedback(session_id=session_id, adopted=l3_reviewed)
        return report

    def _dry_run_plan(self, plan: ExecutionPlan, session_id: str) -> dict:
        order = [step.id for step in plan.steps]
        reads = {step.id: step.reads_from_blackboard for step in plan.steps}
        writes = {step.id: step.writes_to_blackboard for step in plan.steps}
        return {
            "session_id": session_id,
            "plan_id": plan.plan_id,
            "step_order": order,
            "reads_from_blackboard": reads,
            "writes_to_blackboard": writes,
        }

    def _emit_l2_trace(
        self,
        session_id: str | None,
        plan: ExecutionPlan,
        *,
        passed: bool,
        issues: list[str],
    ) -> None:
        """Persist the L2 destructive-confirmation gate result as a trace.

        Records rule=safety.l2_confirm so the trajectory-evaluation layer has a
        signal for whether destructive operations were confirmed (fixes the
        C7 safety blind spot — destructive ops previously left no trace).
        """
        if not session_id:
            return
        destructive_steps = [s.id for s in plan.steps if s.destructive]
        with suppress(Exception):
            audit_trace(
                session_id=session_id,
                step_id="l2-gate",
                trace_data={
                    "step_type": "safety_gate",
                    "status": "pass" if passed else "fail",
                    "destructive_steps": destructive_steps,
                    "issues": issues,
                },
                provenance={
                    "eval_id": f"{session_id}:l2-gate:safety.l2_confirm",
                    "rule": "safety.l2_confirm",
                    "input_ref": f"plan={plan.plan_id}, destructive_steps={destructive_steps}",
                    "decision": "pass" if passed else "fail",
                    "reason": "destructive operations confirmed via --confirm"
                    if passed
                    else "; ".join(issues),
                },
            )

    def _run_execution(
        self,
        plan: ExecutionPlan,
        *,
        audience: str,
        l3_reviewed: bool,
        l2_confirmed: bool = False,
        evo_signals: EvolutionSignals | None = None,  # noqa: F821
    ) -> ExecutionResult:
        session_id = getattr(self, "_session_id", "inline")
        self._plan_context = plan.context
        bb_client = SessionManager().blackboard_client()
        bb_client.get_or_create(session_id, plan.context.get("user_request", "copilot execution"))
        step_results = self._plan_dispatcher.execute(
            plan,
            bb_client,
            session_id,
            l2_confirmed=l2_confirmed,
            evolution_context=self._build_evo_context(evo_signals),
        )

        status, report = self._build_final_report(
            plan, step_results, audience, bb_client, session_id
        )
        exec_result = ExecutionResult(
            plan=plan,
            step_results=step_results,
            final_report=report,
            status=status,
        )

        l3_result = check_l3(exec_result, reviewed=l3_reviewed)
        if not l3_result["passed"]:
            with suppress(Exception):
                ObservableSink().emit_gate(
                    session_id, "l3", "fail", "; ".join(l3_result["issues"])
                )
            exec_result.status = "aborted"
            exec_result.safety_violations = l3_result["issues"]
            exec_result.final_report = self._error_report(
                f"L3 gate failed: {', '.join(l3_result['issues'])}",
                None,
                plan.intent,
                duration_ms=0,
                audience=audience,
            )
        else:
            # Record the PASS decision too so critical-finding approval is
            # traceable (mirrors L2, which emits both pass and fail traces).
            with suppress(Exception):
                ObservableSink().emit_gate(
                    session_id,
                    "l3",
                    "pass",
                    "reviewed" if l3_reviewed else "no_critical_or_approved",
                )

        return exec_result

    def _build_final_report(
        self,
        plan: ExecutionPlan,
        step_results: list[StepResult],
        audience: str,
        blackboard,
        session_id: str,
    ) -> tuple[str, Report]:
        synth = next(
            (
                sr
                for sr in step_results
                if sr.status == "success" and sr.output and "report" in sr.output
            ),
            None,
        )
        has_critical = any(
            sr.output and sr.output.get("has_critical")
            for sr in step_results
            if sr.status == "success"
        )
        contributions: dict = {}
        user_request = plan.context.get("user_request") or plan.context.get("user_query", "")
        if blackboard is not None:
            with suppress(Exception):
                board = blackboard.load(session_id)
                user_request = user_request or board.get("user_request", "")
                contributions = blackboard.read_contributions(session_id)
                has_critical = has_critical or any(
                    c.get("verdict") == "CRITICAL" for c in contributions.values()
                )

        if contributions:
            from copilot.evidence import build_evidence_chain, load_sniff_for_session

            sniff_data = load_sniff_for_session(contributions)
            preset_strategy = None
            with suppress(Exception):
                existing_chain = blackboard.read_evidence_chain(session_id)
                if existing_chain:
                    candidate = existing_chain.get("strategy") or {}
                    if candidate.get("decision_maker") in (
                        "agent_session_v1",
                        "llm_reasoner_v1",
                    ):
                        preset_strategy = candidate
            evidence_chain = build_evidence_chain(
                user_request=user_request,
                plan=plan,
                step_results=step_results,
                contributions=contributions,
                sniff_data=sniff_data,
                agent_strategy=preset_strategy,
            )
            with suppress(Exception):
                blackboard.write_evidence_chain(session_id, evidence_chain)

            common = {
                "customer": plan.context.get("customer"),
                "user_request": user_request,
                "plan": plan,
                "step_results": step_results,
                "evidence_chain": evidence_chain,
            }
            from copilot.report_gen import (
                _precompute_blackboard_context,
                _synthesize_with_context,
            )

            ctx = _precompute_blackboard_context(
                contributions, common["customer"], plan
            )
            detailed = _synthesize_with_context(
                ctx,
                audience="detailed",
                user_request=common["user_request"],
                plan=common["plan"],
                step_results=common["step_results"],
                evidence_chain=common["evidence_chain"],
                contributions=contributions,
            )
            summary = _synthesize_with_context(
                ctx,
                audience="summary",
                user_request=common["user_request"],
                plan=common["plan"],
                step_results=common["step_results"],
                evidence_chain=common["evidence_chain"],
                contributions=contributions,
            )
            self._report_pair = (detailed, summary)
            report = summary if audience == "summary" else detailed
        elif synth and synth.output and synth.output.get("report") is not None:
            report = synth.output["report"]
        else:
            exec_result = ExecutionResult(plan=plan, step_results=step_results, status="completed")
            report = synthesize(exec_result, audience=audience)

        status = "awaiting_confirmation" if has_critical else "completed"
        return status, report

    def _deliver_report(self, report: Report) -> Report:
        if not report.aggregated:
            return report
        session_id = getattr(self, "_session_id", "inline")
        plan_context = getattr(self, "_plan_context", {})
        customer = report.customer or plan_context.get("customer")
        pair = getattr(self, "_report_pair", None)
        with suppress(Exception):
            from copilot.report_gen import (
                default_report_path,
                save_report_markdown,
                summary_report_path,
            )

            if pair:
                detailed, summary = pair
                detailed.duration_ms = report.duration_ms or detailed.duration_ms
                summary.duration_ms = report.duration_ms or summary.duration_ms
                detailed_path = save_report_markdown(
                    detailed,
                    session_id=session_id,
                    customer=customer,
                    output_path=default_report_path(session_id, customer=customer),
                )
                summary_path = save_report_markdown(
                    summary,
                    session_id=session_id,
                    customer=customer,
                    output_path=summary_report_path(session_id, customer=customer),
                )
                detailed.report_path = str(detailed_path)
                summary.summary_report_path = str(summary_path)
                if report.audience == "summary":
                    report.report_path = str(summary_path)
                    report.summary_report_path = str(detailed_path)
                else:
                    report.report_path = str(detailed_path)
                    report.summary_report_path = str(summary_path)
            else:
                report.report_path = str(
                    save_report_markdown(
                        report,
                        session_id=session_id,
                        customer=customer,
                    )
                )
        with suppress(Exception):
            ObservableSink().emit_metric(
                Metric(
                    name="copilot_report_delivered",
                    kind=MetricKind.COUNTER,
                    value=1.0,
                    tags={"session_id": str(session_id)},
                )
            )
        return report

    def record_feedback(
        self, session_id: str, *, adopted: bool = False, overridden: bool = False
    ) -> None:
        """Emit user-adoption / override signals consumed by the EVO-1 feedback loop.

        Called by the host after the user acts on a delivered report. Best-effort:
        any failure is swallowed so feedback never blocks the main flow.
        """
        with suppress(Exception):
            sink = ObservableSink()
            if adopted:
                sink.emit_metric(
                    Metric(
                        name="copilot_user_adopt",
                        kind=MetricKind.COUNTER,
                        value=1.0,
                        tags={"session_id": str(session_id)},
                    )
                )
            if overridden:
                sink.emit_metric(
                    Metric(
                        name="copilot_report_override",
                        kind=MetricKind.COUNTER,
                        value=1.0,
                        tags={"session_id": str(session_id)},
                    )
                )

    def _error_report(self, message, parsed, intent, duration_ms, audience):
        from copilot.models import ExecutionPlan

        plan = ExecutionPlan(intent=intent, steps=[], context={})
        result = ExecutionResult(
            plan=plan,
            step_results=[],
            status="aborted",
            safety_violations=[message],
        )
        report = synthesize(result, audience=audience)
        report.duration_ms = duration_ms
        return report
