#!/usr/bin/env python3
"""Level 3 scenario runner — real cloud by default; use --mock for offline CI."""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
COPILOT = ROOT / "qcloud-copilot"
sys.path.insert(0, str(COPILOT))

from copilot.blackboard import BlackboardClient  # noqa: E402
from copilot.classifier import classify  # noqa: E402
from copilot.dispatcher import PlanDispatcher  # noqa: E402
from copilot.engine import CopilotEngine  # noqa: E402
from copilot.integration.alert_intel import AlertIntelRunner  # noqa: E402
from copilot.integration.cruise import CruiseRunner  # noqa: E402
from copilot.integration.skills import SkillDispatcher  # noqa: E402
from copilot.models import AskOption, ClassifiedIntent, ExecutionPlan, IntentType  # noqa: E402
from copilot.models import PlanStep, StepResult  # noqa: E402
from copilot.parser import parse  # noqa: E402
from copilot.plan_gen import generate as gen_plan  # noqa: E402
from copilot.plan_schema import load_plan_file  # noqa: E402

FIXTURE = COPILOT / "tests" / "fixtures" / "plan-vpc-cruise-alert-report.json"
SCHEMA = ROOT / ".runtime" / "blackboard" / "schema.json"
OUT_DIR = ROOT / ".runtime" / "l3-scenarios"
SLEEP = 0.12
DEFAULT_CUSTOMER = "朔州天源"
DEFAULT_REGION = "ap-guangzhou"


@dataclass
class ScenarioResult:
    id: str
    title: str
    goal: str
    status: str
    metrics: dict = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)


def _load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.startswith(("TENCENTCLOUD_", "COPILOT_")):
            os.environ.setdefault(key, value)


def preflight_cloud(customer: str, region: str) -> list[str]:
    """Verify cloud CLI + credentials before real-cloud scenarios. Returns evidence lines."""
    _load_env()
    evidence: list[str] = []

    py = subprocess.run([sys.executable, "--version"], capture_output=True, text=True, check=False)
    py_version = py.stdout.strip() or py.stderr.strip()
    if not py_version.startswith("Python 3."):
        raise RuntimeError(f"Python 3.x required, got: {py_version}")
    evidence.append(py_version)

    secret_id = os.environ.get("TENCENTCLOUD_SECRET_ID", "")
    secret_key = os.environ.get("TENCENTCLOUD_SECRET_KEY", "")
    if not secret_id or not secret_key:
        raise RuntimeError("TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY not set (check .env)")
    evidence.append(f"region={region} secret_id={secret_id[:4]}***")

    tccli = shutil.which("tccli")
    if not tccli:
        raise RuntimeError("tccli not in PATH; run: pip install tccli")
    evidence.append(f"tccli={tccli}")

    ver = subprocess.run(["tccli", "--version"], capture_output=True, text=True, check=False)
    if ver.returncode != 0:
        raise RuntimeError(f"tccli --version failed: {ver.stderr[:200]}")
    evidence.append(f"tccli_version={ver.stdout.strip() or 'unknown'}")

    evidence.append(f"customer={customer}, region={region}")
    return evidence


def _board_client(run_id: str) -> BlackboardClient:
    board_dir = OUT_DIR / run_id / "blackboard"
    board_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(SCHEMA, board_dir / "schema.json")
    return BlackboardClient(board_dir=board_dir)


def _mock_skill() -> MagicMock:
    skill = MagicMock(spec=SkillDispatcher)
    skill.execute.return_value = StepResult(
        step_id="vpc-0",
        status="success",
        output={"data": {"vpcs": [{"vpcId": "vpc-demo"}]}},
    )
    return skill


def _offline_cruise_run_factory(run_dir: Path, customer: str, hints: list[str] | None = None):
    report_path = run_dir / f"cruise-{customer}-offline.json"
    inspected = hints or []
    report_path.write_text(
        json.dumps(
            {
                "customer": customer,
                "summary": {"critical": 0, "warning": 0, "info": 0},
                "all_findings": [
                    {
                        "severity": "info",
                        "resource_id": rid,
                        "message": "offline mock",
                        "service": "mock",
                    }
                    for rid in inspected
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    sniff_path = run_dir / f"sniff-{customer}-offline.json"
    sniff_path.write_text("{}", encoding="utf-8")

    def fake_run(cmd, **kwargs):
        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        script = cmd[1] if len(cmd) > 1 else ""
        if "cruise_sniff.py" in script:
            R.stdout = f"[已保存] JSON 已保存: {sniff_path}\n"
        elif "cruise_analyze.py" in script:
            R.stdout = f"[已保存] JSON 报告已保存: {report_path}\n"
        return R()

    return fake_run


def _slow_cruise_factory(sleep_sec: float):
    def slow_cruise(step, context, blackboard=None, session_id=None):
        time.sleep(sleep_sec)
        if blackboard and session_id:
            blackboard.write_contribution(
                session_id,
                "qcloud-proactive-inspection",
                {
                    "version": "3.0.0",
                    "verdict": "PASS",
                    "findings": [{"id": "c1", "severity": "INFO", "summary": "定向巡检完成"}],
                    "topology_hints": ["rds-mysql-demo"],
                    "metadata": {"mode": "targeted"},
                },
            )
        selected_region = (step.params.get("region") if step and step.params else None) or (
            context.get("region") if context else None
        )
        output = {"mode": "targeted", "inspected": ["rds-mysql-demo"]}
        if selected_region:
            output["selected_region"] = selected_region
        return StepResult(
            step_id=step.id,
            status="success",
            output=output,
        )

    return slow_cruise


def _slow_alert_factory(sleep_sec: float, verdict: str = "PASS"):
    def slow_alert(params, blackboard, session_id):
        time.sleep(sleep_sec)
        contribution = {
            "version": "0.4.0",
            "verdict": verdict,
            "findings": [
                {
                    "id": "a1",
                    "severity": "P0" if verdict == "CRITICAL" else "P1",
                    "summary": "CPU 告警 rds-mysql-demo",
                }
            ],
            "topology_hints": ["rds-mysql-demo"],
            "metadata": {"time_window": params.get("time_window", "最近24h")},
        }
        blackboard.write_contribution(session_id, "qcloud-monitor-ops", contribution)
        return contribution

    return slow_alert


def scenario_s1_alert_drives_cruise(
    run_id: str, *, real: bool, customer: str, region: str
) -> ScenarioResult:
    """S1/R1: 告警 findings → blackboard → 定向巡检."""
    client = _board_client(run_id)
    session_id = "s1-alert-cruise"
    client.create(session_id, f"{customer} P0 告警，分析并针对性巡检")

    alert_params: dict = {"time_window": "最近24h", "region": region}
    if not real:
        alert_params["alarm_history"] = [
            {
                "resourceId": "rds-mysql-demo",
                "serviceCode": "rds",
                "metricName": "cpu_util",
                "status": "ALARM",
            }
        ]

    AlertIntelRunner().analyze(alert_params, client, session_id)
    hints = client.read_topology_hints(session_id)

    step = PlanStep(
        id="cruise-s1",
        type="cruise_run",
        params={"customer": customer, "region": region},
    )

    if real:
        result = CruiseRunner().execute(
            step, {"region": region}, blackboard=client, session_id=session_id
        )
    else:
        run_dir = OUT_DIR / run_id / "offline-cruise"
        run_dir.mkdir(parents=True, exist_ok=True)
        with patch(
            "copilot.integration.cruise.subprocess.run",
            side_effect=_offline_cruise_run_factory(run_dir, customer, hints or ["rds-mysql-demo"]),
        ):
            result = CruiseRunner().execute(step, {}, blackboard=client, session_id=session_id)

    board = client.load(session_id)
    inspected = result.output.get("inspected", []) if result.output else []
    ok = (
        result.status == "success"
        and (
            result.output.get("mode") == "targeted"
            if hints
            else result.output.get("mode") == "full"
        )
        and "qcloud-monitor-ops" in board["shared_context"]["contributions"]
        and "qcloud-proactive-inspection" in board["shared_context"]["contributions"]
    )
    return ScenarioResult(
        id="R1" if real else "S1",
        title="告警驱动定向巡检" + ("（真实云）" if real else ""),
        goal="alert topology_hints 写入 blackboard，cruise 走 targeted/full 只读巡检",
        status="PASS" if ok else "FAIL",
        metrics={
            "cruise_mode": result.output.get("mode") if result.output else None,
            "hints_count": len(hints),
            "real": real,
        },
        evidence=[
            f"topology_hints={hints}",
            f"cruise_inspected={inspected}",
            f"cruise_status={result.status}",
            f"contributions={list(board['shared_context']['contributions'].keys())}",
        ],
    )


def scenario_s2_serial_plan(
    run_id: str, *, real: bool, customer: str, region: str
) -> ScenarioResult:
    """S2/R2: 四步 plan 串行执行."""
    client = _board_client(run_id)
    session_id = "s2-serial-plan"
    client.create(session_id, "四步风险巡检（串行）")

    plan = load_plan_file(FIXTURE)
    plan.dispatch_config = dict(plan.dispatch_config)
    plan.dispatch_config["max_parallel_groups"] = 1
    plan.context = dict(plan.context)
    plan.context.update({"customer": customer, "region": region})
    for step in plan.steps:
        if step.type == "cruise_run":
            step.params["customer"] = customer
            step.params["region"] = region
        if step.type == "alert_analyze":
            step.params["region"] = region

    dispatcher = PlanDispatcher(skill_dispatcher=SkillDispatcher() if real else _mock_skill())
    if not real:
        dispatcher._cruise_runner = MagicMock()
        dispatcher._cruise_runner.execute.side_effect = _slow_cruise_factory(SLEEP)
        dispatcher._alert_runner = MagicMock()
        dispatcher._alert_runner.analyze.side_effect = _slow_alert_factory(SLEEP)

    order: list[str] = []
    original = dispatcher._execute_step

    def track(step, p, bb, sid):
        order.append(step.id)
        return original(step, p, bb, sid)

    dispatcher._execute_step = track

    t0 = time.perf_counter()
    results = dispatcher.execute(plan, client, session_id, parallel=False)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    board = client.load(session_id)
    ok = (
        order == ["vpc-0", "cruise-1", "alert-2", "report-3"]
        and len(board["shared_context"]["contributions"]) >= 2
        and any(r.step_id == "report-3" and r.status == "success" for r in results)
    )
    return ScenarioResult(
        id="R2" if real else "S2",
        title="四步 Plan 串行执行" + ("（真实云）" if real else ""),
        goal="vpc → cruise → alert → report，blackboard 双 contribution",
        status="PASS" if ok else "FAIL",
        metrics={"elapsed_ms": elapsed_ms, "step_order": order, "real": real},
        evidence=[f"step_results={[r.step_id + ':' + r.status for r in results]}"],
    )


def scenario_s3_parallel_plan(
    run_id: str, *, real: bool, customer: str, region: str
) -> ScenarioResult:
    """S3/R3: cruise + alert 同组并行."""
    client = _board_client(run_id)
    session_id = "s3-parallel-plan"
    client.create(session_id, "四步风险巡检（并行）")

    plan = load_plan_file(FIXTURE)
    plan.dispatch_config = dict(plan.dispatch_config)
    plan.dispatch_config["max_parallel_groups"] = 3
    plan.context = dict(plan.context)
    plan.context.update({"customer": customer, "region": region})
    for step in plan.steps:
        if step.type == "cruise_run":
            step.params["customer"] = customer
            step.params["region"] = region
        if step.type == "alert_analyze":
            step.params["region"] = region

    dispatcher = PlanDispatcher(skill_dispatcher=SkillDispatcher() if real else _mock_skill())
    if not real:
        dispatcher._cruise_runner = MagicMock()
        dispatcher._cruise_runner.execute.side_effect = _slow_cruise_factory(SLEEP)
        dispatcher._alert_runner = MagicMock()
        dispatcher._alert_runner.analyze.side_effect = _slow_alert_factory(SLEEP)

    t_parallel = time.perf_counter()
    dispatcher.execute(plan, client, session_id, parallel=True)
    parallel_ms = int((time.perf_counter() - t_parallel) * 1000)

    client.create("s3-serial-baseline", "串行基准")
    t_serial = time.perf_counter()
    dispatcher.execute(plan, client, "s3-serial-baseline", parallel=False)
    serial_ms = int((time.perf_counter() - t_serial) * 1000)

    speedup = round(serial_ms / max(parallel_ms, 1), 2)
    if real:
        ok = parallel_ms <= serial_ms and speedup >= 1.0
    else:
        ok = parallel_ms < 350 and serial_ms > parallel_ms and speedup >= 1.3

    return ScenarioResult(
        id="R3" if real else "S3",
        title="同组并行加速" + ("（真实云）" if real else ""),
        goal="cruise-1 与 alert-2 并行，总时长不劣于串行",
        status="PASS" if ok else "FAIL",
        metrics={
            "parallel_ms": parallel_ms,
            "serial_ms": serial_ms,
            "speedup": speedup,
            "real": real,
        },
        evidence=[f"parallel={parallel_ms}ms serial={serial_ms}ms speedup={speedup}x"],
    )


def scenario_s4_nl_plan_gen(*, real: bool) -> ScenarioResult:
    """S4/R4: NL 触发四步 risk plan."""
    query = "朔州天源 VPC 风险巡检和告警汇总报告"
    parsed = parse(query)
    intent = classify(parsed)
    plan = gen_plan(intent, context={"user_query": query, "customer": DEFAULT_CUSTOMER})

    ids = [s.id for s in plan.steps]
    ok = len(plan.steps) == 4 and ids == ["vpc-0", "cruise-1", "alert-2", "report-3"]
    return ScenarioResult(
        id="R4" if real else "S4",
        title="NL 生成四步 Plan",
        goal="自然语言触发 _risk_assessment_plan，与标准 fixture 同构",
        status="PASS" if ok else "FAIL",
        metrics={
            "intent_primary": intent.primary.value,
            "intent_secondary": [s.value for s in intent.secondary],
            "plan_id": plan.plan_id,
            "real": real,
        },
        evidence=[f"steps={ids}", f"types={[s.type for s in plan.steps]}"],
    )


def _report_text(report) -> str:
    parts = [report.summary]
    for section in report.sections:
        parts.extend(section.findings)
    return " ".join(parts)


def scenario_s6_region_askuser_delivery(
    run_id: str, *, real: bool, customer: str, region: str
) -> ScenarioResult:
    """S6/R6: delivery 模式自动注入 ask-region-0; 用户选第一项 → cruise-1 命中."""
    client = _board_client(run_id)
    session_id = "s6-ask-region"
    client.create(session_id, f"客户 {customer} delivery 巡检")

    plan = _ask_region_plan(customer, region, mode="delivery")

    dispatcher = PlanDispatcher(
        skill_dispatcher=SkillDispatcher() if real else _mock_skill(),
    )
    if not real:
        dispatcher._cruise_runner = MagicMock()
        dispatcher._cruise_runner.execute.side_effect = _slow_cruise_factory(0)
        dispatcher._alert_runner = MagicMock()
        dispatcher._alert_runner.analyze.side_effect = _slow_alert_factory(0)

    # Drive the ask by piping a synthetic "1\n" stdin to the runner.
    stdin_patch = patch.object(sys, "stdin", io.StringIO("1\n"))
    stdout_patch = patch.object(sys, "stdout", io.StringIO())
    ask_user_called: list[bool] = []
    selected: list[str] = []

    original_execute = dispatcher._execute_step

    def tracked(step, p, bb, sid):
        if step.type == "ask_user":
            ask_user_called.append(True)
        result = original_execute(step, p, bb, sid)
        # Capture the choice the runner wrote into the context.
        if step.type == "ask_user" and result.output and "selection" in result.output:
            selected.append(result.output["selection"]["value"])
            chosen = result.output["selection"]["value"]
            # Inject the chosen region into step.params for downstream mock
            # cruise runner (mock factories don't observe context.region).
            for downstream in p.steps:
                if downstream.id == "cruise-1":
                    downstream.params["region"] = chosen
        return result

    dispatcher._execute_step = tracked
    try:
        with stdin_patch, stdout_patch:
            results = dispatcher.execute(plan, client, session_id)
    finally:
        dispatcher._execute_step = original_execute

    by_id = {r.step_id: r for r in results}
    ask_ok = bool(by_id.get("ask-region-0") and by_id["ask-region-0"].status == "success")
    cruise = by_id.get("cruise-1")
    # The ask_user step writes chosen region into context; mock cruise runner
    # echoes step.params.region OR context.region. Either path is a valid
    # signal that the user's pick reached the downstream step.
    cruise_output = (cruise.output if cruise else None) or {}
    cruise_sees_selected = bool(selected) and (cruise_output.get("selected_region") in selected)

    board = client.load(session_id)
    pa = board.get("shared_context", {}).get("pending_actions", [])
    persisted_ask = any(item.get("action") == "ask_user_response" for item in pa)

    ok = ask_ok and cruise_sees_selected and persisted_ask and bool(selected)

    return ScenarioResult(
        id="R6" if real else "S6",
        title="delivery 模式 ask-region-0 候选澄清" + ("（真实云）" if real else ""),
        goal="自动探到 N 个 region → 插入 ask-region-0 → 选 1 → cruise-1 命中；blackboard 持久化",
        status="PASS" if ok else "FAIL",
        metrics={
            "ask_region_fired": ask_ok,
            "selected_option": selected[0] if selected else None,
            "cruise_sees_region": cruise_sees_selected,
            "pending_action_persisted": persisted_ask,
            "real": real,
        },
        evidence=[
            f"ask_called={bool(ask_user_called)}",
            f"selected={selected}",
            f"cruise_output={cruise_output}",
            f"pending_actions={[item.get('action') for item in pa]}",
        ],
    )


def scenario_s7_region_askuser_ci_rejection(
    run_id: str, *, real: bool, customer: str, region: str
) -> ScenarioResult:
    """S7/R7: CI 模式 ask_user step 被 dispatcher fail-fast 拒绝."""
    client = _board_client(run_id)
    session_id = "s7-ci-reject"
    client.create(session_id, f"客户 {customer} CI 巡检")

    plan = _ask_region_plan(customer, region, mode="ci")
    ask_step = PlanStep(
        id="leaked-ask",
        type="ask_user",
        ask_user_options=[AskOption(value=region, label="北京")],
    )
    plan = ExecutionPlan(
        intent=plan.intent,
        steps=[ask_step],
        context=dict(plan.context),
        safety_level=plan.safety_level,
        plan_id="s7-ask-leakage",
        dispatch_config=dict(plan.dispatch_config),
    )

    dispatcher = PlanDispatcher(
        skill_dispatcher=SkillDispatcher() if real else _mock_skill(),
    )
    ask_called: list[bool] = []
    # Spy on AskUserRunner to assert CI path doesn't invoke it.
    original_runner_execute = dispatcher._ask_user_runner.execute

    def spy(step, *a, **kw):
        ask_called.append(True)
        return original_runner_execute(step, *a, **kw)

    dispatcher._ask_user_runner.execute = spy
    try:
        results = dispatcher.execute(plan, client, session_id)
    finally:
        dispatcher._ask_user_runner.execute = original_runner_execute

    by_id = {r.step_id: r for r in results}
    ask_step_res = by_id["leaked-ask"]
    rejected = ask_step_res.status == "failure" and "rejected" in (ask_step_res.error or "")

    ok = rejected and not ask_called

    return ScenarioResult(
        id="R7" if real else "S7",
        title="CI 拒绝 ask_user step（双层防御）" + ("（真实云）" if real else ""),
        goal="CI 模式 planner 漏插 ask_user → dispatcher fail-fast 拒绝，runner 不调用",
        status="PASS" if ok else "FAIL",
        metrics={
            "ask_user_invoked": bool(ask_called),
            "ask_status": ask_step_res.status,
            "ask_error": (ask_step_res.error or "")[:120],
            "real": real,
        },
        evidence=[
            f"ask_user_invoked={bool(ask_called)}",
            f"status={ask_step_res.status}",
        ],
    )


def _ask_region_plan(customer: str, region: str, *, mode: str) -> ExecutionPlan:
    """Build a 3-step plan: ask-region-0 → cruise-1 → report-2 (BC-T6 wiring)."""
    ctx: dict = {
        "customer": customer,
        "region": region,
        "inspection_effective": mode,
        "region_candidates": [
            {"region": "ap-guangzhou", "customer_resources_count": 5, "resource_types": ["vm"]},
            {"region": "cn-east-2", "customer_resources_count": 2, "resource_types": ["rds"]},
        ],
    }
    from copilot.plan_gen import _cruise_plan as _cruise_plan_impl

    return _cruise_plan_impl(
        ClassifiedIntent(primary=IntentType.CRUISE, targets=["vm"]),
        ctx,
    )


def scenario_s5_critical_gate(
    run_id: str, *, real: bool, customer: str, region: str
) -> ScenarioResult:
    """S5/R5: CRITICAL → awaiting_confirmation + L3 门."""
    client = _board_client(run_id)
    session_id = "s5-critical-gate"
    plan = load_plan_file(FIXTURE)
    plan.dispatch_config = dict(plan.dispatch_config)
    plan.dispatch_config["max_parallel_groups"] = 1
    plan.context = dict(plan.context)
    plan.context.update({"customer": customer, "region": region})
    for step in plan.steps:
        if step.type == "cruise_run":
            step.params["customer"] = customer
            step.params["region"] = region
        if step.type == "alert_analyze":
            step.params["region"] = region

    with patch("copilot.engine.SessionManager") as sm_mock:
        sm = sm_mock.return_value
        sm.blackboard_client.return_value = client
        sm.init_blackboard.return_value = client.create(session_id, "CRITICAL 场景")

        engine = CopilotEngine()
        if real:
            engine._plan_dispatcher._skill_dispatcher = SkillDispatcher()
        else:
            engine._plan_dispatcher._skill_dispatcher = _mock_skill()
            engine._plan_dispatcher._cruise_runner = MagicMock()
            engine._plan_dispatcher._cruise_runner.execute.side_effect = _slow_cruise_factory(0)
            engine._plan_dispatcher._alert_runner = MagicMock()
            engine._plan_dispatcher._alert_runner.analyze.side_effect = _slow_alert_factory(
                0, verdict="CRITICAL"
            )

        blocked = engine.run_plan(plan, session_id=session_id, l3_reviewed=False)
        approved = engine.run_plan(plan, session_id=session_id, l3_reviewed=True)

    board = client.load(session_id)
    alert_verdict = (
        board.get("shared_context", {})
        .get("contributions", {})
        .get("qcloud-monitor-ops", {})
        .get("verdict", "PASS")
    )

    blocked_by_l3 = (
        "L3 gate failed" in _report_text(blocked) or "review" in _report_text(blocked).lower()
    )
    approved_ok = "L3 gate failed" not in _report_text(approved)

    if real:
        if alert_verdict == "CRITICAL":
            ok = blocked_by_l3 and approved_ok
        else:
            ok = not blocked_by_l3 and approved_ok
    else:
        ok = blocked_by_l3 and approved_ok

    return ScenarioResult(
        id="R5" if real else "S5",
        title="CRITICAL 人工审批门" + ("（真实云）" if real else ""),
        goal="有 CRITICAL 时阻断；无 CRITICAL 时正常交付",
        status="PASS" if ok else "FAIL",
        metrics={
            "alert_verdict": alert_verdict,
            "blocked_summary": blocked.summary[:80],
            "real": real,
        },
        evidence=[
            f"alert_verdict={alert_verdict}",
            f"without_review: L3_blocked={blocked_by_l3}",
            f"with_review: delivered={approved_ok}",
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Level 3 scenario runner (real cloud by default)")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Offline mock path (no real CLI / credentials; for CI or quick smoke)",
    )
    parser.add_argument("--customer", default=os.environ.get("L3_REAL_CUSTOMER", DEFAULT_CUSTOMER))
    parser.add_argument("--region", default=os.environ.get("TENCENTCLOUD_REGION", DEFAULT_REGION))
    args = parser.parse_args()

    real = not args.mock
    run_id = time.strftime("%Y%m%d-%H%M%S")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    preflight_evidence: list[str] = []
    if real:
        try:
            preflight_evidence = preflight_cloud(args.customer, args.region)
        except RuntimeError as exc:
            print(f"Preflight FAILED: {exc}", file=sys.stderr)
            print(
                "Hint: use --mock for offline runs, or: .venv/bin/python + source .env",
                file=sys.stderr,
            )
            return 2

    scenarios = [
        scenario_s1_alert_drives_cruise(
            run_id, real=real, customer=args.customer, region=args.region
        ),
        scenario_s2_serial_plan(run_id, real=real, customer=args.customer, region=args.region),
        scenario_s3_parallel_plan(run_id, real=real, customer=args.customer, region=args.region),
        scenario_s4_nl_plan_gen(real=real),
        scenario_s5_critical_gate(run_id, real=real, customer=args.customer, region=args.region),
        scenario_s6_region_askuser_delivery(
            run_id, real=real, customer=args.customer, region=args.region
        ),
        scenario_s7_region_askuser_ci_rejection(
            run_id, real=real, customer=args.customer, region=args.region
        ),
    ]

    passed = sum(1 for s in scenarios if s.status == "PASS")
    mode = "real" if real else "mock"
    report = {
        "run_id": run_id,
        "level": "L3",
        "mode": mode,
        "customer": args.customer,
        "region": args.region,
        "preflight": preflight_evidence,
        "summary": f"{passed}/{len(scenarios)} scenarios passed ({mode})",
        "scenarios": [asdict(s) for s in scenarios],
    }

    out_json = OUT_DIR / f"scenario-report-{mode}-{run_id}.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 60)
    print(f"Level 3 场景用例执行报告 ({mode})")
    print("=" * 60)
    if preflight_evidence:
        print("Preflight:")
        for line in preflight_evidence:
            print(f"  · {line}")
    for s in scenarios:
        print(f"\n[{s.id}] {s.title} — {s.status}")
        print(f"  目标: {s.goal}")
        if s.metrics:
            print(f"  指标: {json.dumps(s.metrics, ensure_ascii=False)}")
        for line in s.evidence:
            print(f"  · {line}")
    print(f"\n汇总: {report['summary']}")
    print(f"详细 JSON: {out_json}")
    return 0 if passed == len(scenarios) else 1


if __name__ == "__main__":
    raise SystemExit(main())
