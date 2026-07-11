"""Blackboard evidence chain builder — strategy / plan / process / results."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from copilot.models import ExecutionPlan, StepResult
from copilot.topology_reasoner import reason_inspection_strategy


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _plan_snapshot(plan: ExecutionPlan | None) -> dict[str, Any]:
    if plan is None:
        return {}
    intent = plan.intent
    return {
        "plan_id": plan.plan_id,
        "safety_level": plan.safety_level,
        "primary_intent": intent.primary.value,
        "secondary_intents": [s.value for s in intent.secondary],
        "context": {k: v for k, v in (plan.context or {}).items() if k != "user_query"},
        "steps": [
            {
                "id": s.id,
                "type": s.type,
                "skill": s.skill,
                "operation": s.operation,
                "depends_on": s.depends_on,
                "parallel_group": s.parallel_group,
                "description": s.description,
            }
            for s in plan.steps
        ],
    }


def _process_from_steps(
    plan: ExecutionPlan | None, step_results: list[StepResult] | None
) -> list[dict[str, Any]]:
    if not step_results:
        return []
    step_map = {s.id: s for s in plan.steps} if plan else {}
    events: list[dict[str, Any]] = []
    for sr in step_results:
        step = step_map.get(sr.step_id)
        actor = (step.skill if step else None) or (step.type if step else "unknown")
        evt: dict[str, Any] = {
            "ts": _now(),
            "step_id": sr.step_id,
            "phase": _phase_for_step(step),
            "actor": actor,
            "status": sr.status,
            "duration_ms": sr.duration_ms,
        }
        if sr.error:
            evt["error"] = sr.error[:500]
        if sr.output:
            out = sr.output
            if out.get("report_path"):
                evt["artifact"] = out["report_path"]
            if out.get("sniff_output"):
                evt["artifact_sniff"] = out["sniff_output"]
            if out.get("resource_coverage"):
                evt["resource_coverage"] = out["resource_coverage"]
            if out.get("verdict"):
                evt["verdict"] = out["verdict"]
        events.append(evt)
    return events


def _phase_for_step(step: Any) -> str:
    if step is None:
        return "execute"
    mapping = {
        "skill_call": "perceive",
        "cruise_run": "reason",
        "alert_analyze": "perceive",
        "synthesize_report": "aggregate",
    }
    return mapping.get(step.type, "execute")


def _artifact_index(contributions: dict[str, dict]) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    cruise = contributions.get("qcloud-proactive-inspection", {})
    meta = cruise.get("metadata") or {}
    for key, kind in (
        ("sniff_path", "sniff_topology"),
        ("report_path", "cruise_analysis"),
    ):
        path = meta.get(key, "")
        if path and Path(path).is_file():
            artifacts.append({"type": kind, "path": path})
    cov = meta.get("resource_coverage") or {}
    for run in cov.get("analyzer_runs") or []:
        if run.get("analyzed_count", 0) > 0:
            artifacts.append(
                {
                    "type": "analyzer_run",
                    "path": meta.get("report_path", ""),
                    "service": run.get("service", ""),
                    "count": str(run.get("analyzed_count", 0)),
                }
            )
    return artifacts


def build_evidence_chain(
    *,
    user_request: str,
    plan: ExecutionPlan | None,
    step_results: list[StepResult] | None,
    contributions: dict[str, dict],
    sniff_data: dict[str, Any] | None = None,
    agent_strategy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Full evidence chain for Blackboard + report rendering."""
    customer = ""
    region = "ap-guangzhou"
    if plan and plan.context:
        customer = str(plan.context.get("customer") or "")
        region = str(plan.context.get("region") or region)
    cruise_meta = (contributions.get("qcloud-proactive-inspection") or {}).get("metadata") or {}
    coverage = cruise_meta.get("resource_coverage") or {}

    if agent_strategy and agent_strategy.get("decision_maker") in (
        "agent_session_v1",
        "llm_reasoner_v1",
    ):
        strategy = dict(agent_strategy)
    else:
        strategy = reason_inspection_strategy(
            customer=customer or str(cruise_meta.get("customer") or ""),
            region=region,
            user_request=user_request,
            sniff_data=sniff_data,
            resource_coverage=coverage,
        )

    verdicts = [str(c.get("verdict", "PASS")) for c in contributions.values()]
    overall = "PASS"
    if "CRITICAL" in verdicts:
        overall = "CRITICAL"
    elif "WARNING" in verdicts:
        overall = "WARNING"

    return {
        "schema_version": "1.1",
        "built_at": _now(),
        "strategy": strategy,
        "plan": _plan_snapshot(plan),
        "process": _process_from_steps(plan, step_results),
        "results": {
            "overall_verdict": overall,
            "contributions": {
                name: {
                    "verdict": c.get("verdict"),
                    "findings_count": len(c.get("findings") or []),
                    "topology_hints_count": len(c.get("topology_hints") or []),
                }
                for name, c in contributions.items()
            },
            "artifact_index": _artifact_index(contributions),
        },
    }


def load_sniff_for_session(contributions: dict[str, dict]) -> dict[str, Any] | None:
    meta = (contributions.get("qcloud-proactive-inspection") or {}).get("metadata") or {}
    sniff_path = meta.get("sniff_path", "")
    if not sniff_path:
        return None
    path = Path(sniff_path)
    if not path.is_file():
        return None
    import json

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
