from __future__ import annotations

import os
import re
from typing import Any

from copilot.models import AskOption, ClassifiedIntent, ExecutionPlan, IntentType, PlanStep
from copilot.mode_gate import maybe_discover_regions

TARGET_TO_SKILL: dict[str, str] = {
    "vm": "qcloud-cvm-ops",
    "redis": "qcloud-redis-ops",
    "mysql": "qcloud-cdb-ops",
    "rds": "qcloud-cdb-ops",
    "k8s": "qcloud-tke-ops",
    "disk": "qcloud-cbs-ops",
    "eip": "qcloud-vpc-ops",
    "clb": "qcloud-clb-ops",
    "oss": "qcloud-cos-ops",
    "iam": "qcloud-cam-ops",
    "vpc": "qcloud-vpc-ops",
}


def _resolve_target_skill(target: str) -> str:
    if target.startswith("qcloud-"):
        return target
    return TARGET_TO_SKILL.get(target, "qcloud-cvm-ops")


def _env_allowlist() -> list[str] | None:
    """Read COPILOT_REGION_ALLOWLIST env var (CSV) → list, or None if unset."""
    raw = os.environ.get("COPILOT_REGION_ALLOWLIST", "").strip()
    if not raw:
        return None
    return [r.strip() for r in raw.split(",") if r.strip()]


def _step_id(prefix: str, n: int) -> str:
    return f"{prefix}-{n}"


def _is_risk_assessment(text: str, intent: ClassifiedIntent) -> bool:
    has_vpc = "vpc" in text.lower() or "专有网络" in text
    has_risk = bool(re.search(r"风险|巡检|健康", text))
    has_alert = bool(re.search(r"告警|报警|alert", text, re.I))
    if has_vpc and has_risk and has_alert:
        return True
    return intent.primary == IntentType.REPORT and IntentType.CRUISE in intent.secondary


def _risk_assessment_plan(intent: ClassifiedIntent, ctx: dict) -> ExecutionPlan:
    customer = ctx.get("customer", "朔州天源")
    region = ctx.get("region", "ap-guangzhou")
    ctx = {**ctx, "customer": customer, "region": region}
    steps = [
        PlanStep(
            id="vpc-0",
            type="skill_call",
            skill="qcloud-vpc-ops",
            operation="describe-vpcs",
            params={"operation": "describe-vpcs", "region": region},
            depends_on=[],
            parallel_group=0,
            writes_to_blackboard=False,
            description="List VPCs",
        ),
        PlanStep(
            id="cruise-1",
            type="cruise_run",
            skill="qcloud-proactive-inspection",
            operation="cruise",
            params={"customer": customer, "region": region},
            depends_on=["vpc-0"],
            parallel_group=1,
            writes_to_blackboard=True,
            description="Targeted/full cruise",
        ),
        PlanStep(
            id="alert-2",
            type="alert_analyze",
            skill="qcloud-monitor-ops",
            operation="analyze",
            params={"time_window": "最近24h", "severity_filter": "P0,P1"},
            depends_on=[],
            parallel_group=1,
            writes_to_blackboard=True,
            description="Alert intelligence",
        ),
        PlanStep(
            id="report-3",
            type="synthesize_report",
            skill="qcloud-copilot",
            operation="synthesize-report",
            params={"audience": ctx.get("audience", "detailed")},
            depends_on=["cruise-1", "alert-2"],
            parallel_group=2,
            reads_from_blackboard=[
                "contributions.qcloud-proactive-inspection",
                "contributions.qcloud-monitor-ops",
            ],
            writes_to_blackboard=False,
            description="Unified report from blackboard",
        ),
    ]
    return ExecutionPlan(
        intent=intent,
        steps=steps,
        context=ctx,
        safety_level=0,
        plan_id="risk-assessment-plan",
    )


def _inspect_plan(intent: ClassifiedIntent, ctx: dict) -> ExecutionPlan:
    target = intent.targets[0] if intent.targets else "vm"
    target_skill = _resolve_target_skill(target)
    steps = [
        PlanStep(
            id=_step_id("inspect", 1),
            type="skill_call",
            skill=target_skill,
            params={"operation": "describe", "target": intent.targets},
            description=f"Describe {', '.join(intent.targets)} resources",
        ),
    ]
    return ExecutionPlan(intent=intent, steps=steps, context=ctx, safety_level=0)


def _diagnose_plan(intent: ClassifiedIntent, ctx: dict) -> ExecutionPlan:
    steps = [
        PlanStep(
            id=_step_id("diag", 1),
            type="skill_call",
            skill="qcloud-monitor-ops",
            params={"operation": "describe-metrics", "target": intent.targets},
            description="Fetch monitoring metrics",
        ),
        PlanStep(
            id=_step_id("diag", 2),
            type="skill_call",
            skill="qcloud-cvm-ops",
            params={"operation": "describe-instance", "target": intent.targets},
            description="Describe instance state",
            depends_on=[_step_id("diag", 1)],
        ),
    ]
    return ExecutionPlan(intent=intent, steps=steps, context=ctx, safety_level=0)


def _act_plan(intent: ClassifiedIntent, ctx: dict) -> ExecutionPlan:
    target = intent.targets[0] if intent.targets else "vm"
    target_skill = _resolve_target_skill(target)
    act_op = ctx.get("operation", "modify")
    steps = [
        PlanStep(
            id=_step_id("act", 1),
            type="skill_call",
            skill=target_skill,
            params={"operation": act_op, "target": intent.targets},
            description=f"Execute {act_op} on {', '.join(intent.targets)}",
            destructive=True,
        ),
        PlanStep(
            id=_step_id("act", 2),
            type="skill_call",
            skill=target_skill,
            params={"operation": "describe", "target": intent.targets},
            description="Verify post-operation state",
            depends_on=[_step_id("act", 1)],
        ),
    ]
    return ExecutionPlan(intent=intent, steps=steps, context=ctx, safety_level=2)


def _cruise_plan(intent: ClassifiedIntent, ctx: dict) -> ExecutionPlan:
    customer = ctx.get("customer", "")
    region = ctx.get("region", "ap-guangzhou")
    steps: list[PlanStep] = []

    # BC-T4: Insert ask-region-0 ahead of cruise-1 when region is ambiguous
    # AND inspection mode is delivery (not CI). CI gets the same skip:
    #   - explicit region (param or context) → no ask
    #   - CI / fallback mode → no ask, no probing
    if _is_region_ambiguous(customer=customer, region=region, ctx=ctx):
        ask_options = _build_region_ask_options(ctx)
        if ask_options:
            steps.append(
                PlanStep(
                    id="ask-region-0",
                    type="ask_user",
                    description=f"客户「{customer}」存在多个 Region，请选择巡检范围",
                    depends_on=[],
                    parallel_group=0,
                    writes_to_blackboard=False,
                    ask_user_options=ask_options,
                    ask_timeout_seconds=60,
                    ask_user_context_key="region",
                )
            )
            # ask-region-0 owns group 0; cruise-1 shifts to group 1
            cruise_group = 1
        else:
            cruise_group = 0
    else:
        cruise_group = 0

    steps.append(
        PlanStep(
            id="cruise-1",
            type="cruise_run",
            skill="qcloud-proactive-inspection",
            operation="cruise",
            params={"customer": customer, "region": region},
            depends_on=["ask-region-0"] if steps else [],
            parallel_group=cruise_group,
            writes_to_blackboard=True,
            description="Run full-link inspection",
        )
    )
    steps.append(
        PlanStep(
            id="report-1",
            type="synthesize_report",
            skill="qcloud-copilot",
            operation="synthesize-report",
            params={"audience": ctx.get("audience", "detailed")},
            depends_on=["cruise-1"],
            parallel_group=cruise_group + 1,
            reads_from_blackboard=["contributions.qcloud-proactive-inspection"],
            writes_to_blackboard=False,
            description="Unified cruise report",
        )
    )
    return ExecutionPlan(
        intent=intent,
        steps=steps,
        context=ctx,
        safety_level=0,
        plan_id="cruise-plan",
    )


def _is_region_ambiguous(*, customer: str, region: str, ctx: dict) -> bool:
    """Decide whether to inject ask-region-0 before cruise-1.

    Returns True (= inject ask) only when region discovery ran and produced
    multiple candidates. The presence of region_candidates in ctx is itself
    proof that the planner ran region_scanner; explicit user-supplied region
    (whether defaulted or not) and CI/fallback short-circuit discovery
    upstream, leaving ctx["region_candidates"] unset.

    Hard rules (spec §3.7):
      - CI / fallback → no ask (non-interactive)
      - no candidates → no ask (nothing to choose from)
    """
    effective = ctx.get("inspection_effective", "delivery")
    if effective in ("ci", "fallback"):
        return False
    candidates = ctx.get("region_candidates") or []
    return bool(candidates)


def _build_region_ask_options(ctx: dict) -> list[AskOption]:
    """Convert ctx["region_candidates"] into AskOption list. Empty → no ask.

    Region allowlist precedence: ctx["region_allowlist"] (explicit) > env
    COPILOT_REGION_ALLOWLIST (CSV) > no filter. Either source may be a list
    or a comma-separated string.
    """
    allowlist = ctx.get("region_allowlist") or _env_allowlist()
    candidates = ctx.get("region_candidates") or []
    options: list[AskOption] = []
    for cand in candidates:
        # Normalize RegionCandidate dataclass → dict-like attribute access.
        if not isinstance(cand, dict):
            region = getattr(cand, "region", None)
            if not region:
                continue
            count = getattr(cand, "customer_resources_count", "?")
            rt = getattr(cand, "resource_types", {}) or {}
        else:
            region = cand.get("region")
            if not region:
                continue
            count = cand.get("customer_resources_count", "?")
            rt = cand.get("resource_types", []) or []
        if allowlist and region not in allowlist:
            continue
        # resource_types may be dict (from RegionCandidate) or list (legacy
        # fixtures). Normalize: take keys for dict, items for list.
        if isinstance(rt, dict):
            type_keys = list(rt.keys())
        else:
            type_keys = list(rt or [])
        types = ", ".join(type_keys[:3])
        desc = f"命中 {count} 资源" + (f"（{types}）" if types else "")
        options.append(AskOption(value=region, label=region, description=desc))
    return options


def _report_plan(intent: ClassifiedIntent, ctx: dict) -> ExecutionPlan:
    return ExecutionPlan(intent=intent, steps=[], context=ctx, safety_level=0)


PLAN_TEMPLATES = {
    IntentType.INSPECT: _inspect_plan,
    IntentType.DIAGNOSE: _diagnose_plan,
    IntentType.ACT: _act_plan,
    IntentType.CRUISE: _cruise_plan,
    IntentType.COMPARE: _inspect_plan,
    IntentType.REPORT: _report_plan,
}


def generate(
    intent: ClassifiedIntent,
    context: dict | None = None,
    *,
    scanner: Any | None = None,
    client_factory: Any | None = None,
) -> ExecutionPlan:
    ctx = dict(context or {})  # shallow copy so we can mutate region_candidates
    user_query = ctx.get("user_query", "")
    if _is_risk_assessment(user_query, intent):
        return _risk_assessment_plan(intent, ctx)
    # BC-T4 wiring: in delivery mode with no explicit region, probe region
    # candidates so _cruise_plan can inject ask-region-0. CI / fallback / explicit
    # region / prior round → None (skip). mode_gate writes ctx["region_candidates"].
    _populate_region_candidates(intent, ctx, scanner=scanner, client_factory=client_factory)
    builder = PLAN_TEMPLATES.get(intent.primary)
    if builder is None:
        steps = [
            PlanStep(
                id="fallback-1",
                type="report",
                params={"error": f"Unknown intent: {intent.primary}"},
                description="Unknown intent — cannot generate plan",
            ),
        ]
        return ExecutionPlan(intent=intent, steps=steps, context=ctx, safety_level=0)
    return builder(intent, ctx)


def _populate_region_candidates(
    intent: ClassifiedIntent,
    ctx: dict,
    *,
    scanner: Any | None = None,
    client_factory: Any | None = None,
) -> None:
    """Wire mode_gate → ctx["region_candidates"]; failure-isolated.

    Region discovery is best-effort: any error (no TccliClient, no customer,
    network, empty result) leaves ctx unchanged so downstream sees no
    ambiguity rather than a broken plan.
    """
    mode_result = ctx.get("inspection_mode_result")
    if mode_result is None:
        return  # No mode info → conservative skip; callers can still supply ctx directly.
    customer = ctx.get("customer", "")
    region = ctx.get("region", "")
    candidates = maybe_discover_regions(
        intent=intent,
        customer=customer,
        region=region,
        context=ctx,
        mode_result=mode_result,
        scanner=scanner,  # None → use maybe_discover_regions default
        client_factory=client_factory,
    )
    if candidates is None:
        return  # gate skipped (CI / explicit / prior / unsupported intent)
    # Keep RegionCandidate objects; _build_region_ask_options handles both shapes.
    ctx["region_candidates"] = list(candidates)
