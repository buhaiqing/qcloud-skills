from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from copilot.blackboard import BlackboardClient, find_repo_root
from copilot.models import PlanStep, StepResult

CRUISE_SKILL = "qcloud-proactive-inspection"
CRUISE_VERSION = "3.1.0"

_SAVED_PATH_RE = re.compile(r"\[已保存\].*?:\s*(.+\.json)\s*$")

# All analyzers in qcloud-proactive-inspection (create_all); used for coverage reporting.
_ANALYZER_CATALOG: list[tuple[str, str, str, str | None]] = [
    ("vm", "云主机 ECS", "qcloud-cvm-ops", "vms"),
    ("clb", "负载均衡 CLB", "qcloud-clb-ops", "lbs"),
    ("eip", "弹性公网 IP", "qcloud-vpc-ops", "eips"),
    ("redis", "Redis 缓存", "qcloud-redis-ops", "redis"),
    ("rds_mysql", "RDS MySQL", "qcloud-cdb-ops", "rds"),
    ("rds_postgresql", "RDS PostgreSQL", "qcloud-postgres-ops", "rds"),
    ("mongodb", "MongoDB", "qcloud-mongodb-ops", "mongodb"),
    ("elasticsearch", "Elasticsearch", "qcloud-es-ops", "es"),
    ("nat", "NAT 网关", "qcloud-vpc-ops", None),
    ("k8s", "Kubernetes 节点", "qcloud-tke-ops", "vms"),
    ("security_group", "安全组", "qcloud-vpc-ops", None),
]

_RESOURCE_ID_KEYS = (
    "resource_id",
    "instanceId",
    "cacheInstanceId",
    "dbInstanceId",
    "loadBalancerId",
    "elasticIpId",
    "id",
    "resourceId",
)


def _resource_id_from_dict(item: dict[str, Any]) -> str:
    for key in _RESOURCE_ID_KEYS:
        value = item.get(key)
        if value:
            return str(value)
    return ""


def _inspected_from_report(report: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for sr in report.get("service_reports") or []:
        for finding in sr.get("findings") or []:
            rid = _resource_id_from_dict(finding) or str(finding.get("resource") or "")
            if rid and rid not in seen:
                seen.add(rid)
                ordered.append(rid)
    if ordered:
        return ordered
    for finding in report.get("all_findings") or []:
        rid = _resource_id_from_dict(finding) or str(finding.get("resource") or "")
        if rid and rid not in seen:
            seen.add(rid)
            ordered.append(rid)
    return ordered


def _load_sniff_data(sniff_file: str | None, output: dict[str, Any]) -> dict[str, Any] | None:
    candidates: list[Path] = []
    if sniff_file:
        candidates.append(Path(sniff_file))
    sniff_output = output.get("sniff_output")
    if sniff_output:
        candidates.append(Path(str(sniff_output)))
    for path in candidates:
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
    return None


def _build_resource_coverage(
    report: dict[str, Any], sniff_data: dict[str, Any] | None
) -> dict[str, Any]:
    analyzed_map: dict[str, dict[str, int]] = {}
    for sr in report.get("service_reports") or []:
        svc = str(sr.get("service", ""))
        analyzed_map[svc] = {
            "resources_count": int(sr.get("resources_count") or sr.get("resource_count") or 0),
            "findings_count": len(sr.get("findings") or []),
        }

    topology_raw = (sniff_data or {}).get("raw") or {}
    runs: list[dict[str, Any]] = []

    for svc_key, label, ops_skill, raw_key in _ANALYZER_CATALOG:
        analyzed = analyzed_map.get(svc_key, {})
        analyzed_count = analyzed.get("resources_count", 0)
        findings_count = analyzed.get("findings_count", 0)
        topology_count = len(topology_raw.get(raw_key) or []) if raw_key else 0
        if analyzed_count > 0:
            status = "analyzed"
        elif topology_count > 0:
            status = "discovered_not_analyzed"
        else:
            status = "no_resources"
        runs.append(
            {
                "service": svc_key,
                "label": label,
                "ops_skill": ops_skill,
                "topology_count": topology_count,
                "analyzed_count": analyzed_count,
                "findings_count": findings_count,
                "status": status,
                "via": "qcloud-proactive-inspection",
            }
        )

    vpc_count = len(topology_raw.get("vpcs") or [])
    return {
        "analyzer_runs": runs,
        "topology_vpc_count": vpc_count,
        "total_analyzed_resources": sum(r["analyzed_count"] for r in runs),
        "total_topology_resources": sum(
            len(topology_raw.get(key) or [])
            for key in ("vms", "lbs", "redis", "rds", "mongodb", "eips", "es")
        ),
    }


def _read_inspection_strategy(
    blackboard: BlackboardClient | None, session_id: str | None
) -> dict[str, Any] | None:
    if not session_id:
        return None

    file_strategy: dict[str, Any] | None = None
    strategy_path = find_repo_root() / ".runtime" / "blackboard" / f"strategy-{session_id}.json"
    if strategy_path.is_file():
        try:
            file_strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            file_strategy = None

    chain_strategy: dict[str, Any] | None = None
    if blackboard is not None:
        chain = blackboard.read_evidence_chain(session_id)
        chain_strategy = (chain or {}).get("strategy")

    preferred = ("agent_session_v1", "llm_reasoner_v1")
    for candidate in (file_strategy, chain_strategy):
        if candidate and candidate.get("decision_maker") in preferred:
            return candidate
    return file_strategy or chain_strategy


def _apply_ci_mode_strategy(
    context: dict[str, Any],
    blackboard: BlackboardClient | None,
    session_id: str | None,
    sniff_data: dict[str, Any],
    customer: str,
    region: str,
    existing: dict[str, Any] | None,
) -> dict[str, Any]:
    """Generate and persist CI/fallback strategy after sniff; never override agent."""
    if existing and existing.get("decision_maker") == "agent_session_v1":
        return existing

    from copilot.llm_reasoner import reason_inspection_strategy_llm
    from copilot.strategy import apply_strategy

    effective = str(context.get("inspection_effective") or "delivery")
    user_request = str(
        context.get("user_query") or context.get("user_request") or sniff_data.get("customer") or ""
    )
    mode_meta = {
        "mode": context.get("inspection_mode"),
        "effective": effective,
        "trigger": context.get("inspection_trigger"),
        "matched_keyword": context.get("inspection_matched_keyword"),
        "warnings": context.get("inspection_warnings") or [],
    }

    strategy, _warnings = reason_inspection_strategy_llm(
        customer=customer,
        region=region,
        user_request=user_request,
        sniff_data=sniff_data,
        mode_meta=mode_meta,
        force_topology_fallback=(effective == "fallback"),
    )
    decision_maker = str(strategy.get("decision_maker") or "topology_reasoner_v1")

    if blackboard is not None and session_id:
        apply_strategy(session_id, strategy, decision_maker=decision_maker, blackboard=blackboard)

    return strategy


def _write_strategy_temp(strategy: dict[str, Any], session_id: str) -> Path:
    output_dir = _cruise_runtime_dir()
    path = output_dir / f"strategy-{session_id}.json"
    path.write_text(json.dumps(strategy, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _cruise_runtime_dir() -> Path:
    path = find_repo_root() / ".runtime" / "proactive-inspection"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sniff_script() -> Path:
    root = find_repo_root()
    return root / "qcloud-proactive-inspection" / "scripts" / "01-perceive" / "cruise_sniff.py"


def _analyze_script() -> Path:
    root = find_repo_root()
    return root / "qcloud-proactive-inspection" / "scripts" / "02-reason" / "cruise_analyze.py"


def _parse_saved_json_path(stdout: str) -> str | None:
    for line in stdout.splitlines():
        match = _SAVED_PATH_RE.search(line.strip())
        if match:
            return match.group(1)
    return None


def _latest_json(output_dir: Path, pattern: str) -> Path | None:
    files = sorted(output_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _verdict_from_report(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    if summary.get("critical", 0) > 0:
        return "CRITICAL"
    if summary.get("warning", 0) > 0:
        return "WARNING"
    return "PASS"


def _findings_from_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for item in report.get("all_findings") or []:
        severity = str(item.get("severity", "info")).upper()
        if severity == "CRITICAL":
            sev = "P0"
        elif severity == "WARNING":
            sev = "P1"
        else:
            sev = "INFO"
        resource_id = item.get("resource_id") or item.get("resource") or ""
        findings.append(
            {
                "id": f"cruise-{resource_id or len(findings)}",
                "severity": sev,
                "summary": item.get("message", ""),
                "resource_id": resource_id,
                "service": item.get("service", ""),
            }
        )
    return findings


class CruiseRunner:
    """Execute cruise_run steps; reads topology_hints from blackboard when present."""

    def execute(
        self,
        step: PlanStep,
        context: dict,
        blackboard: BlackboardClient | None = None,
        session_id: str | None = None,
    ) -> StepResult:
        customer = step.params.get("customer", context.get("customer", ""))
        region = step.params.get("region", context.get("region", ""))
        hints: list[str] = []

        if blackboard is not None and session_id:
            hints = blackboard.read_topology_hints(session_id)

        if hints:
            result = self._execute_targeted(step, customer, region, hints)
        else:
            strategy = _read_inspection_strategy(blackboard, session_id)
            result = self._execute_full_cruise(
                step,
                customer,
                region,
                strategy=strategy,
                session_id=session_id,
                context=context,
                blackboard=blackboard,
            )

        if result.status == "success" and blackboard is not None and session_id and result.output:
            self._write_contribution(blackboard, session_id, result.output, hints)

        return result

    def _run_script(self, cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(find_repo_root()),
        )

    def _execute_analyze(
        self,
        step: PlanStep,
        customer: str,
        *,
        sniff_file: str | None = None,
        resource_ids: list[str] | None = None,
        strategy_file: str | None = None,
        analyzers: list[str] | None = None,
    ) -> StepResult:
        if not customer:
            return StepResult(
                step_id=step.id,
                status="failure",
                error="cruise_run requires customer in step.params or context",
            )

        analyze = _analyze_script()
        if not analyze.is_file():
            return StepResult(
                step_id=step.id,
                status="failure",
                error=f"cruise_analyze.py not found: {analyze}",
            )

        output_dir = _cruise_runtime_dir()
        hours = int(step.params.get("hours", 6))
        cmd = [
            sys.executable,
            str(analyze),
            "--customer",
            customer,
            "--hours",
            str(hours),
            "--json",
            "--output-dir",
            str(output_dir),
        ]
        if sniff_file:
            cmd.extend(["--sniff-file", sniff_file])
        if resource_ids:
            cmd.extend(["--resource-ids", *resource_ids])
        if analyzers:
            cmd.extend(["--analyzers", ",".join(analyzers)])
        elif strategy_file:
            cmd.extend(["--strategy-file", strategy_file])

        try:
            proc = self._run_script(cmd, timeout=300)
        except subprocess.TimeoutExpired:
            return StepResult(
                step_id=step.id,
                status="failure",
                error="cruise_analyze timed out after 300s",
            )
        except FileNotFoundError:
            return StepResult(
                step_id=step.id,
                status="failure",
                error="Python executable not found for cruise_analyze",
            )

        report_path_str = _parse_saved_json_path(proc.stdout or "")
        report_path = Path(report_path_str) if report_path_str else None
        if report_path is None or not report_path.is_file():
            report_path = _latest_json(output_dir, f"cruise-{customer}-*.json")

        if proc.returncode != 0 and report_path is None:
            return StepResult(
                step_id=step.id,
                status="failure",
                error=f"cruise_analyze failed: {(proc.stderr or proc.stdout or '')[:500]}",
            )

        report: dict[str, Any] = {}
        if report_path and report_path.is_file():
            report = json.loads(report_path.read_text(encoding="utf-8"))

        inspected = list(resource_ids or [])
        if not inspected and report:
            inspected = _inspected_from_report(report)

        sniff_data = _load_sniff_data(sniff_file, {"sniff_output": sniff_file or ""})
        resource_coverage = _build_resource_coverage(report, sniff_data) if report else {}

        mode = "targeted" if resource_ids else "selective"
        return StepResult(
            step_id=step.id,
            status="success",
            output={
                "cruise": True,
                "mode": mode,
                "customer": customer,
                "region": step.params.get("region", ""),
                "report_path": str(report_path) if report_path else "",
                "sniff_file": sniff_file or "",
                "verdict": _verdict_from_report(report) if report else "PASS",
                "findings": _findings_from_report(report) if report else [],
                "inspected": inspected,
                "resource_coverage": resource_coverage,
                "analyze_stdout": (proc.stdout or "")[:2000],
            },
        )

    def _execute_targeted(
        self,
        step: PlanStep,
        customer: str,
        region: str,
        hints: list[str],
    ) -> StepResult:
        del region  # cruise_analyze discovers regions via TccliClient
        return self._execute_analyze(step, customer, resource_ids=hints)

    def _execute_full_cruise(
        self,
        step: PlanStep,
        customer: str,
        region: str,
        *,
        strategy: dict[str, Any] | None = None,
        session_id: str | None = None,
        context: dict[str, Any] | None = None,
        blackboard: BlackboardClient | None = None,
    ) -> StepResult:
        sniff = _sniff_script()
        if not sniff.is_file():
            return StepResult(
                step_id=step.id,
                status="failure",
                error=f"cruise_sniff.py not found: {sniff}",
            )

        output_dir = _cruise_runtime_dir()
        sniff_cmd = [
            sys.executable,
            str(sniff),
            "--customer",
            customer,
            "--output-dir",
            str(output_dir),
        ]
        if region:
            sniff_cmd.extend(["--region", region])

        try:
            sniff_result = self._run_script(sniff_cmd, timeout=120)
        except subprocess.TimeoutExpired:
            return StepResult(
                step_id=step.id,
                status="failure",
                error="cruise_sniff timed out after 120s",
            )
        except FileNotFoundError:
            return StepResult(
                step_id=step.id,
                status="failure",
                error="qcloud-proactive-inspection not installed; cruise_run unavailable",
            )

        sniff_path_str = _parse_saved_json_path(sniff_result.stdout or "")
        sniff_path = Path(sniff_path_str) if sniff_path_str else None
        if sniff_path is None or not sniff_path.is_file():
            sniff_path = _latest_json(output_dir, f"sniff-{customer}-*.json")

        if sniff_path is None or not sniff_path.is_file():
            return StepResult(
                step_id=step.id,
                status="failure",
                error=f"cruise_sniff output not found: {(sniff_result.stderr or '')[:500]}",
            )

        sniff_data: dict[str, Any] = {}
        try:
            sniff_data = json.loads(sniff_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            sniff_data = {}

        effective = str((context or {}).get("inspection_effective") or "delivery")
        if effective in ("ci", "fallback") and context is not None:
            strategy = _apply_ci_mode_strategy(
                context,
                blackboard,
                session_id,
                sniff_data,
                customer,
                region,
                strategy,
            )

        strategy_file: str | None = None
        if strategy:
            key = session_id or customer
            strategy_path = _write_strategy_temp(strategy, key)
            strategy_file = str(strategy_path)

        analyze_result = self._execute_analyze(
            step,
            customer,
            sniff_file=str(sniff_path),
            strategy_file=strategy_file,
        )
        if analyze_result.status != "success" or not analyze_result.output:
            return analyze_result

        analyze_result.output["sniff_output"] = str(sniff_path)
        analyze_result.output["sniff_exit_code"] = sniff_result.returncode
        sniff_data = _load_sniff_data(str(sniff_path), analyze_result.output)
        report_path = analyze_result.output.get("report_path")
        if report_path and sniff_data:
            try:
                report = json.loads(Path(report_path).read_text(encoding="utf-8"))
                analyze_result.output["resource_coverage"] = _build_resource_coverage(
                    report, sniff_data
                )
            except (OSError, json.JSONDecodeError):
                pass
        return analyze_result

    def _write_contribution(
        self,
        blackboard: BlackboardClient,
        session_id: str,
        output: dict[str, Any],
        hints: list[str],
    ) -> None:
        inspected = output.get("inspected") or hints or []
        findings = output.get("findings")
        if not findings:
            findings = [
                {
                    "id": f"cruise-{resource_id}",
                    "severity": "INFO",
                    "summary": f"定向巡检已覆盖资源 {resource_id}",
                    "resource_id": resource_id,
                }
                for resource_id in inspected
            ]

        verdict = output.get("verdict")
        if not verdict:
            verdict = "WARNING" if output.get("mode") == "targeted" and inspected else "PASS"

        blackboard.write_contribution(
            session_id,
            CRUISE_SKILL,
            {
                "version": CRUISE_VERSION,
                "verdict": verdict,
                "findings": findings,
                "topology_hints": list(inspected),
                "metadata": {
                    "mode": output.get("mode", "full"),
                    "customer": output.get("customer", ""),
                    "report_path": output.get("report_path", ""),
                    "sniff_path": output.get("sniff_output") or output.get("sniff_file", ""),
                    "resource_coverage": output.get("resource_coverage") or {},
                },
            },
        )
