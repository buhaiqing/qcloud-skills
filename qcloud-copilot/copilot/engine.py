from __future__ import annotations

import time
from contextlib import suppress

from copilot.classifier import classify
from copilot.dispatcher import PlanDispatcher
from copilot.models import (
    ExecutionPlan,
    ExecutionResult,
    Report,
    StepResult,
)
from copilot.parser import parse
from copilot.plan_gen import generate as gen_plan
from copilot.plan_schema import load_plan_file
from copilot.report_gen import synthesize
from copilot.integration.skills import SkillDispatcher
from copilot.integration.cruise import CruiseRunner
from copilot.safety.l0 import check_l0
from copilot.safety.l1 import check_l1
from copilot.safety.l2 import check_l2
from copilot.safety.l3 import check_l3
from copilot.quality.health import record_health
from copilot.quality.audit import audit_trace
from copilot.session import SessionManager
from copilot.mode_resolver import resolve_inspection_mode, strip_ci_trigger_words
from copilot.env_loader import ensure_runtime_env


class CopilotEngine:
    """Main orchestrator: NL → Parse → Classify → Plan → Execute → Report."""

    def __init__(self):
        self._skill_dispatcher = SkillDispatcher()
        self._cruise_runner = CruiseRunner()
        self._plan_dispatcher = PlanDispatcher(
            skill_dispatcher=self._skill_dispatcher,
            cruise_runner=self._cruise_runner,
        )

    def ask(
        self,
        query: str,
        session_id: str | None = None,
        audience: str = "detailed",
        l2_confirmed: bool = False,
        l3_reviewed: bool = False,
        inspection_mode: str | None = None,
    ) -> Report:
        ensure_runtime_env()
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

        parsed = parse(parse_query)
        intent = classify(parsed)

        l0_result = check_l0(parsed, intent)
        if not l0_result["passed"]:
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
        if not l2_result["passed"]:
            return self._deliver_report(
                self._error_report(
                    f"L2 gate failed: {', '.join(l2_result['issues'])}",
                    parsed,
                    intent,
                    duration_ms=0,
                    audience=audience,
                )
            )

        exec_result = self._run_execution(plan, audience=audience, l3_reviewed=l3_reviewed)
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

        return self._deliver_report(exec_result.final_report)

    def run_plan(
        self,
        plan: ExecutionPlan | str,
        session_id: str,
        *,
        audience: str = "detailed",
        dry_run: bool = False,
        l3_reviewed: bool = False,
    ) -> Report | dict:
        if isinstance(plan, str):
            plan = load_plan_file(plan)

        if dry_run:
            return self._dry_run_plan(plan, session_id)

        self._session_id = session_id
        sm = SessionManager()
        sm.init_blackboard(session_id, plan.context.get("user_request", "plan execution"))
        self._plan_context = plan.context
        exec_result = self._run_execution(plan, audience=audience, l3_reviewed=l3_reviewed)
        return self._deliver_report(exec_result.final_report)

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

    def _run_execution(
        self,
        plan: ExecutionPlan,
        *,
        audience: str,
        l3_reviewed: bool,
    ) -> ExecutionResult:
        session_id = getattr(self, "_session_id", "inline")
        self._plan_context = plan.context
        bb_client = SessionManager().blackboard_client()
        bb_client.get_or_create(session_id, plan.context.get("user_request", "copilot execution"))
        step_results = self._plan_dispatcher.execute(
            plan,
            bb_client,
            session_id,
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
            exec_result.status = "aborted"
            exec_result.safety_violations = l3_result["issues"]
            exec_result.final_report = self._error_report(
                f"L3 gate failed: {', '.join(l3_result['issues'])}",
                None,
                plan.intent,
                duration_ms=0,
                audience=audience,
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
            from copilot.report_gen import synthesize_from_blackboard

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
            detailed = synthesize_from_blackboard(contributions, audience="detailed", **common)
            summary = synthesize_from_blackboard(contributions, audience="summary", **common)
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
        return report

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
