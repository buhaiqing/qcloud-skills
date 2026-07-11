from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from copilot.blackboard import find_repo_root
from copilot.models import (
    ExecutionPlan,
    ExecutionResult,
    PlanStep,
    Report,
    ReportSection,
    StepResult,
)


def default_reports_dir() -> Path:
    path = find_repo_root() / ".runtime" / "copilot" / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_report_path(session_id: str, *, customer: str | None = None) -> Path:
    """One stable detailed final report per customer or session (overwrite on re-run)."""
    if customer:
        safe_customer = "".join(c if c.isalnum() or c in "-_" else "-" for c in customer).strip(
            "-"
        )[:32]
        if safe_customer:
            return default_reports_dir() / safe_customer / "final-report.md"
    safe_session = "".join(c if c.isalnum() or c in "-_" else "-" for c in session_id).strip("-")[
        :64
    ]
    if not safe_session:
        safe_session = "inline"
    return default_reports_dir() / safe_session / "final-report.md"


def summary_report_path(session_id: str, *, customer: str | None = None) -> Path:
    """Management-facing one-pager; stable path per customer."""
    if customer:
        safe_customer = "".join(c if c.isalnum() or c in "-_" else "-" for c in customer).strip(
            "-"
        )[:32]
        if safe_customer:
            return default_reports_dir() / safe_customer / "summary-report.md"
    safe_session = "".join(c if c.isalnum() or c in "-_" else "-" for c in session_id).strip("-")[
        :64
    ]
    if not safe_session:
        safe_session = "inline"
    return default_reports_dir() / safe_session / "summary-report.md"


def _format_step_value(value: object) -> str:
    if isinstance(value, (dict, list)):
        size = len(value)
        return f"<{type(value).__name__} items={size}>"
    text = str(value)
    if len(text) > 240:
        return text[:240] + "..."
    return text


def render_markdown(report: Report) -> str:
    if report.aggregated:
        return _render_final_report_markdown(report)

    lines = [f"# {report.title}", "", f"_{report.summary}_", ""]
    for section in report.sections:
        lines.append(f"## {section.title} ({section.severity})")
        lines.append("")
        for finding in section.findings:
            lines.append(f"- {finding}")
        if section.recommendations:
            lines.append("")
            lines.append("**Recommendations:**")
            for rec in section.recommendations:
                lines.append(f"- {rec}")
        lines.append("")
    if report.execution_trace:
        lines.append("## Execution Trace")
        lines.append("")
        for entry in report.execution_trace:
            lines.append(
                f"- {entry.get('step', '?')}: {entry.get('status', '?')} "
                f"({entry.get('duration_ms', 0)} ms)"
            )
        lines.append("")
    if report.duration_ms:
        lines.append(f"_Duration: {report.duration_ms} ms_")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_final_report_markdown(report: Report) -> str:
    is_summary = report.audience == "summary"
    title = report.title
    if is_summary and "简报" not in title:
        title = title.replace("Final Report", "巡检简报").replace("AIOps Report", "AIOps 巡检简报")
    lines = [f"# {title}", ""]

    gate = next((s for s in report.sections if s.title == "人工确认"), None)
    conclusion = next((s for s in report.sections if s.title == "巡检结论"), None)
    other_sections = [s for s in report.sections if s.title not in ("巡检结论", "人工确认")]

    if gate:
        lines.append("## 人工确认")
        lines.append("")
        for finding in gate.findings:
            lines.append(f"- {finding}")
        lines.append("")

    if conclusion:
        lines.append("## 巡检结论")
        lines.append("")
        for finding in conclusion.findings:
            if finding == "":
                lines.append("")
            else:
                lines.append(finding)
        if conclusion.recommendations:
            lines.append("")
            for rec in conclusion.recommendations:
                lines.append(f"- {rec}")
        lines.append("")
        lines.append("---")
        lines.append("")

    if report.user_request:
        lines.extend([f"> {report.user_request}", ""])
    meta = [f"**{report.summary}**"]
    meta.append(f"生成于 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    if report.duration_ms:
        meta.append(f"耗时 {report.duration_ms // 1000}s")
    if is_summary:
        meta.append("受众：管理层简报")
    else:
        meta.append("受众：运维工程师详版")
    lines.append(" · ".join(meta))
    lines.append("")

    for section in other_sections:
        lines.append(f"## {section.title}")
        lines.append("")
        if section.title == "Agent Skill 调用链" and section.findings:
            lines.append("| 步骤 | Skill | 操作 | 说明 | 状态 | 耗时 |")
            lines.append("|---|---|---|---|---|---|")
            for finding in section.findings:
                lines.append(finding)
            lines.append("")
            continue
        if section.title in ("拓扑资源巡检覆盖", "Skill 调用链") and section.findings:
            for finding in section.findings:
                if finding == "":
                    lines.append("")
                else:
                    lines.append(finding)
            lines.append("")
            continue
        if section.title in ("自动化修复路径", "下一步行动") and section.findings:
            if section.findings[0].startswith("|"):
                lines.append("| 问题类型 | 推荐 Skill | 操作 | 前置条件 |")
                lines.append("|---|---|---|---|")
                for finding in section.findings:
                    lines.append(finding)
            else:
                for finding in section.findings:
                    if not finding:
                        lines.append("")
                    elif finding.startswith(("### ", "- ", "**", "| ")):
                        lines.append(finding)
                    else:
                        lines.append(f"- {finding}")
            lines.append("")
            if section.recommendations:
                for rec in section.recommendations:
                    lines.append(f"- {rec}")
                lines.append("")
            continue
        if section.findings:
            for finding in section.findings:
                if not finding:
                    lines.append("")
                    continue
                if section.title.startswith("需处理项"):
                    if finding.startswith("### ") or finding.startswith("- "):
                        lines.append(finding)
                    else:
                        lines.append(f"- {finding}")
                elif (
                    finding.startswith("### ")
                    or finding.startswith("| ")
                    or finding.startswith("- ")
                    or finding.startswith("  - ")
                    or finding.startswith("**")
                ):
                    lines.append(finding)
                else:
                    lines.append(f"- {finding}")
        if section.recommendations and section.title not in ("自动化修复路径", "下一步行动"):
            lines.append("")
            for rec in section.recommendations:
                lines.append(f"- {rec}")
        lines.append("")

    footer = (
        "_本报告为 Copilot 聚合后的 Final Report，仅供人工审阅。"
        if not is_summary
        else "_管理层简报：仅含结论与行动项；技术细节见同目录 `final-report.md`。"
    )
    lines.append("---")
    lines.append(footer)
    if not is_summary:
        lines.append("_中间采集数据见 `.runtime/proactive-inspection/`._")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def save_report_markdown(
    report: Report,
    *,
    session_id: str,
    output_path: Path | str | None = None,
    customer: str | None = None,
) -> Path:
    if not report.aggregated:
        raise ValueError("Refusing to save non-aggregated report; use aggregated final report only")
    path = Path(output_path) if output_path else default_report_path(session_id, customer=customer)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(report), encoding="utf-8")
    return path


def _detailed_template(result: ExecutionResult) -> Report:
    sections: list[ReportSection] = []
    for sr in result.step_results:
        if sr.status == "success" and sr.output:
            sections.append(
                ReportSection(
                    title=f"Step {sr.step_id} — Result",
                    severity="info",
                    findings=[f"{k}: {_format_step_value(v)}" for k, v in sr.output.items()],
                )
            )
        elif sr.status == "failure":
            sections.append(
                ReportSection(
                    title=f"Step {sr.step_id} — Failed",
                    severity="critical",
                    findings=[sr.error or "Unknown error"],
                )
            )

    if not sections:
        if result.safety_violations:
            sections.append(
                ReportSection(
                    title="Safety Violations",
                    severity="critical",
                    findings=result.safety_violations,
                )
            )
        else:
            sections.append(
                ReportSection(
                    title="No Results",
                    severity="info",
                    findings=["No step results to report."],
                )
            )

    step_count = len(result.step_results)
    success_count = sum(1 for s in result.step_results if s.status == "success")
    summary = f"Completed {success_count}/{step_count} steps — {result.status}"

    trace = [
        {"step": sr.step_id, "status": sr.status, "duration_ms": sr.duration_ms}
        for sr in result.step_results
    ]

    return Report(
        title=f"AIOps Report — {result.plan.intent.primary.value}",
        summary=summary,
        sections=sections,
        execution_trace=trace,
    )


def _summary_template(result: ExecutionResult) -> Report:
    sections: list[ReportSection] = []
    sev_counts: dict[str, int] = {"critical": 0, "warning": 0, "info": 0}

    findings: list[str] = []
    recommendations: list[str] = []

    for sr in result.step_results:
        if sr.status == "success" and sr.output:
            for k, v in sr.output.items():
                findings.append(f"{k}: {_format_step_value(v)}")
        elif sr.status == "failure":
            findings.append(f"⚠️ {sr.step_id}: {sr.error or 'Failed'}")
            sev_counts["critical"] += 1

    exec_summary = [
        f"Status: {result.status}",
        f"Steps completed: {sum(1 for s in result.step_results if s.status == 'success')}/{len(result.step_results)}",
        f"Critical findings: {sev_counts['critical']}",
    ]
    if result.safety_violations:
        exec_summary.append(f"Safety violations: {len(result.safety_violations)}")
    sections.append(
        ReportSection(
            title="Executive Summary",
            severity="critical" if result.safety_violations else "info",
            findings=exec_summary,
            recommendations=recommendations,
        )
    )
    if result.safety_violations:
        sections.append(
            ReportSection(
                title="Safety Violations",
                severity="critical",
                findings=result.safety_violations,
            )
        )

    if findings:
        sections.append(
            ReportSection(
                title="Details",
                severity="warning" if sev_counts["critical"] else "info",
                findings=findings,
            )
        )

    summary = f"{result.status.capitalize()}: {sev_counts['critical']} critical items"
    return Report(
        title="AIOps Summary",
        summary=summary,
        sections=sections,
    )


def synthesize(result: ExecutionResult, audience: str = "detailed") -> Report:
    if audience == "summary":
        return _summary_template(result)
    return _detailed_template(result)


_VERDICT_SEVERITY = {
    "CRITICAL": "critical",
    "WARNING": "warning",
    "PASS": "info",
}

_ACTION_SEVERITIES = frozenset({"P0", "P1", "P2", "CRITICAL", "WARNING"})
_EXPIRY_WARN_DAYS_P1 = 30
_EXPIRY_WARN_DAYS_P2 = 60
_EXPIRY_ISO_RE = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z|\d{4}-\d{2}-\d{2})")
_NOISE_SUBSTRINGS = ("未获取到", "定向巡检已覆盖", "verdict=")
_OVERALL_VERDICT = {"CRITICAL": 0, "WARNING": 1, "PASS": 2}

_VERDICT_HEADLINE: dict[str, str] = {
    "PASS": "通过（无必修项）",
    "WARNING": "存在需处理风险",
    "CRITICAL": "严重，需立即处理",
}

_SKILL_LABELS: dict[str, str] = {
    "qcloud-vpc-ops": "VPC 网络发现",
    "qcloud-proactive-inspection": "全链路 AIOps 巡检",
    "qcloud-monitor-ops": "云监控与告警分析",
    "qcloud-copilot": "Copilot 报告聚合",
    "qcloud-cvm-ops": "云主机运维",
    "qcloud-cbs-ops": "云盘运维",
}

_CRUISE_CHECK_ITEMS = [
    "云主机 VM：运行状态、磁盘加密、到期时间、冗余度",
    "RDS MySQL：实例规格、存储容量、慢查询风险",
    "CLB 负载均衡：部署模式、后端健康、入口带宽",
    "EIP / NAT：公网绑定关系、带宽配置、流量指标",
    "Redis / 其他数据层：按拓扑优先级深度检查",
    "跨资源拓扑关联与传播链（Topology-first）",
]

_ISSUE_PLAYBOOK: dict[str, dict[str, str | list[str]]] = {
    "磁盘未加密": {
        "analysis": "生产 VM 数据盘或系统盘未开启静态加密，静态数据缺少密钥保护。",
        "impact": "合规审计（等保/行业规范）可能不通过；磁盘快照泄露风险上升。",
        "recommendation": "评估业务窗口后为数据盘启用加密；系统盘加密通常需重建或镜像迁移。",
        "auto_skill": "qcloud-cbs-ops",
        "auto_operation": "describe-disk → encrypt / 加密快照迁移",
        "auto_steps": [
            "`qcloud-cvm-ops` describe-instance 确认 vol-id 与挂载关系",
            "`qcloud-cbs-ops` 评估加密方案（在线/离线）",
            "人工确认后执行加密变更（L2 Safety Gate）",
            "`qcloud-proactive-inspection` 复查加密状态",
        ],
        "gate": "人工确认 + L2",
    },
    "资源即将到期": {
        "analysis": "预付费资源临近到期，到期后可能被停服或释放。",
        "impact": "业务中断、数据不可访问。",
        "recommendation": "30 天内到期资源优先续费；纳入例行到期巡航。",
        "auto_skill": "qcloud-monitor-ops",
        "auto_operation": "expiry-cruise → 委托产品 Skill 续费",
        "auto_steps": [
            "`qcloud-monitor-ops` expiry-cruise 拉取全量到期清单",
            "人工审批续费周期与预算",
            "委托对应 `qcloud-*-ops` 执行续费",
        ],
        "gate": "人工确认",
    },
    "计算资源压力": {
        "analysis": "CPU/内存/连接数等指标异常或告警活跃。",
        "impact": "响应变慢、超时、雪崩风险。",
        "recommendation": "结合 `qcloud-monitor-ops` 拉取 6h 指标，定向 `proactive-inspection` 深挖。",
        "auto_skill": "qcloud-monitor-ops",
        "auto_operation": "describe-metrics + qcloud-proactive-inspection targeted",
        "auto_steps": [
            "`qcloud-monitor-ops` 定位告警资源",
            "`qcloud-proactive-inspection` targeted 模式沿拓扑深挖",
            "必要时 `qcloud-cvm-ops` 扩容或 `qcloud-clb-ops` 后端调整",
        ],
        "gate": "变更需人工确认",
    },
    "活跃告警": {
        "analysis": "Cloud Monitor 存在 P0/P1 未恢复告警。",
        "impact": "已知异常未闭环，可能正在影响业务。",
        "recommendation": "告警驱动定向巡检：alert → topology_hints → cruise targeted。",
        "auto_skill": "qcloud-monitor-ops",
        "auto_operation": "analyze → proactive-inspection targeted",
        "auto_steps": [
            "`qcloud-monitor-ops` 拉取 24h 告警与 topology_hints",
            "`qcloud-proactive-inspection` 仅检查 hints 关联资源",
            "`qcloud-copilot` 汇总二次报告",
        ],
        "gate": "只读；修复委托产品 Skill",
    },
    "其他风险": {
        "analysis": "巡检发现需关注的配置或容量项。",
        "impact": "视具体资源类型而定。",
        "recommendation": "人工复核后决定是否需要变更。",
        "auto_skill": "qcloud-proactive-inspection",
        "auto_operation": "re-cruise with narrowed scope",
        "auto_steps": ["`qcloud-proactive-inspection` 针对单资源定向复查"],
        "gate": "人工确认",
    },
}


def _classify_issue(summary: str) -> str:
    if "未加密" in summary:
        return "磁盘未加密"
    if "到期" in summary:
        return "资源即将到期"
    if "慢查询" in summary or "slow" in summary.lower():
        return "数据库慢查询"
    if "CPU" in summary.upper() or "内存" in summary or "告警" in summary:
        return "计算资源压力"
    return "其他风险"


def _build_conclusion_findings(
    *,
    overall: str,
    customer_name: str,
    action_items: list[dict[str, str]],
    issue_groups: dict[str, list[dict[str, str]]],
    alert: dict,
    alarm_count: int | None,
    time_window: str,
) -> list[str]:
    """结论先行：文档开头展示的明确巡检结论。"""
    headline = _VERDICT_HEADLINE.get(overall, overall)
    count = len(action_items)
    alert_verdict = str(alert.get("verdict", "PASS")).upper() if alert else "PASS"

    if count:
        sub = f"存在 **{count}** 项需处理的必修问题"
    else:
        sub = "未发现需处理的必修项"

    p0_n = sum(1 for i in action_items if _action_bucket(i["severity"]) == "P0")
    p1_n = sum(1 for i in action_items if _action_bucket(i["severity"]) == "P1")
    p2_n = sum(1 for i in action_items if _action_bucket(i["severity"]) == "P2")
    if count:
        breakdown = f"（P0 {p0_n} / P1 {p1_n} / P2 {p2_n}）"
    else:
        breakdown = ""

    lines: list[str] = [f"> **整体评估：{overall}** — {headline}，{sub}{breakdown}。"]

    # 一句话结论
    target = customer_name or "目标环境"
    if not action_items:
        if overall == "PASS":
            narrative = (
                f"**结论**：{target}云资源巡检通过，当前无必修项"
                f"{'；告警侧正常' if alert_verdict == 'PASS' else f'；告警侧 {alert_verdict}'}。"
                "建议保持每周定期巡检。"
            )
        else:
            narrative = f"**结论**：{target}云资源整体评估为 {overall}，当前无 P0/P1 必修项，建议关注环境参考项并持续观察。"
    else:
        categories = sorted(issue_groups.keys(), key=lambda k: -len(issue_groups[k]))
        main_issues = "、".join(f"{c}（{len(issue_groups[c])} 项）" for c in categories[:3])
        alert_clause = (
            f"告警侧 {alert_verdict}（{time_window} 内 {alarm_count or 0} 条 P0/P1）；"
            if alert
            else ""
        )
        top_pb = _ISSUE_PLAYBOOK.get(categories[0], _ISSUE_PLAYBOOK["其他风险"])
        narrative = (
            f"**结论**：{target}云环境整体评估为 **{overall}**。{alert_clause}"
            f"本次发现 {count} 项必修问题，主要为 {main_issues}。"
            f"**建议行动**：{top_pb['recommendation']}"
        )
    lines.append("")
    lines.append(narrative)
    lines.append("")

    # 关键指标表
    lines.append("| 指标 | 结果 |")
    lines.append("|---|---|")
    lines.append(f"| 整体评估 | **{overall}** — {headline} |")
    if alert:
        alarm_n = alarm_count if alarm_count is not None else 0
        lines.append(f"| 告警（{time_window}） | **{alert_verdict}**，{alarm_n} 条 P0/P1 |")
    lines.append(f"| 必修项 | **{count}** 条 {breakdown if count else ''} |")
    if issue_groups:
        top_cat = max(issue_groups, key=lambda k: len(issue_groups[k]))
        lines.append(f"| 首要问题 | {top_cat}（{len(issue_groups[top_cat])} 项） |")
        pb = _ISSUE_PLAYBOOK.get(top_cat, _ISSUE_PLAYBOOK["其他风险"])
        lines.append(f"| 建议路径 | `{pb['auto_skill']}` → {pb['auto_operation']} |")

    if action_items:
        lines.append("")
        lines.append("**首要处理项**（Top 3）：")
        for idx, item in enumerate(action_items[:3], 1):
            lines.append(f"{idx}. {_format_action_item(item)}")
        if count > 3:
            lines.append(f"- … 另有 {count - 3} 项，详见下文「需处理项」")

    return lines


def _parse_expiry_datetime(summary: str) -> datetime | None:
    match = _EXPIRY_ISO_RE.search(summary)
    if not match:
        return None
    raw = match.group(1)
    if len(raw) == 10:
        raw = f"{raw}T00:00:00Z"
    try:
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _split_action_and_info(
    normalized: list[dict[str, str]],
    *,
    now: datetime | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Promote actionable INFO (e.g. expiry within 60d) into action items."""
    now = now or datetime.now(timezone.utc)
    action_items: list[dict[str, str]] = []
    info_items: list[dict[str, str]] = []

    for item in normalized:
        severity = item["severity"]
        summary = item["summary"]

        if severity in _ACTION_SEVERITIES:
            action_items.append(item)
            continue

        if "到期" in summary:
            expire_at = _parse_expiry_datetime(summary)
            if expire_at is not None:
                days_left = (expire_at.date() - now.date()).days
                if days_left < 0:
                    promoted = {
                        **item,
                        "severity": "P0",
                        "summary": f"已过期 {abs(days_left)} 天（{expire_at.date().isoformat()}）",
                    }
                    action_items.append(promoted)
                    continue
                if days_left <= _EXPIRY_WARN_DAYS_P1:
                    promoted = {
                        **item,
                        "severity": "P1",
                        "summary": f"仅剩 {days_left} 天到期（{expire_at.date().isoformat()}）",
                    }
                    action_items.append(promoted)
                    continue
                if days_left <= _EXPIRY_WARN_DAYS_P2:
                    promoted = {
                        **item,
                        "severity": "P2",
                        "summary": f"{days_left} 天后到期（{expire_at.date().isoformat()}）",
                    }
                    action_items.append(promoted)
                    continue

        info_items.append(item)

    action_items.sort(
        key=lambda item: (_severity_rank(item["severity"]), item["resource_id"], item["summary"])
    )
    info_items.sort(key=lambda item: (item["service"], item["summary"]))
    return action_items, info_items


def _action_bucket(severity: str) -> str:
    if severity in ("P0", "CRITICAL"):
        return "P0"
    if severity in ("P1", "WARNING"):
        return "P1"
    return "P2"


def _build_prioritized_actions(action_items: list[dict[str, str]]) -> list[str]:
    buckets: dict[str, list[dict[str, str]]] = {"P0": [], "P1": [], "P2": []}
    for item in action_items:
        buckets[_action_bucket(item["severity"])].append(item)

    lines: list[str] = []
    labels = {
        "P0": "P0 — 立即处理",
        "P1": "P1 — 本周内处理",
        "P2": "P2 — 计划内处理",
    }
    for key in ("P0", "P1", "P2"):
        items = buckets[key]
        if not items:
            continue
        lines.append(f"### {labels[key]}（{len(items)} 项）")
        for item in items:
            lines.append(f"- [{key}] {_format_action_item(item)}")
        lines.append("")
    return lines


def _build_next_actions(groups: dict[str, list[dict[str, str]]]) -> list[str]:
    """Management one-pager: merged recommendations + automation paths."""
    lines: list[str] = []
    for category in sorted(groups.keys(), key=lambda k: -len(groups[k])):
        pb = _ISSUE_PLAYBOOK.get(category, _ISSUE_PLAYBOOK["其他风险"])
        lines.append(f"### {category}")
        lines.append(f"- **做什么**：{pb['recommendation']}")
        lines.append(f"- **委托 Skill**：`{pb['auto_skill']}` — {pb['auto_operation']}")
        lines.append(f"- **审批门**：{pb['gate']}")
        lines.append("")
    return lines


def _build_appendix_findings(
    *,
    region: str,
    customer_name: str,
    overall: str,
    resources_checked: int,
    cruise_mode: str,
    alarm_count: int | None,
    time_window: str,
    action_count: int,
    plan: ExecutionPlan | None,
    contributions: dict[str, dict],
    step_results: list[StepResult] | None,
) -> list[str]:
    lines = [
        "### 执行概况",
        f"- 客户：**{customer_name or '—'}**，区域：**{region}**",
        f"- 整体结论：**{overall}**，必修项 **{action_count}** 条",
        f"- 巡检覆盖：**{resources_checked}** 个关联资源（{cruise_mode} 模式）",
        f"- 告警窗口 {time_window}：**{alarm_count or 0}** 条 P0/P1",
        "",
        "### 编排计划",
    ]
    lines.extend(_describe_plan(plan))
    lines.append("")
    lines.append("### 检查范围")
    lines.extend(_describe_scope(plan, contributions))
    skill_rows = _format_skill_table(plan, step_results)
    if skill_rows:
        lines.append("")
        lines.append("### Copilot 编排步骤")
        lines.append("| 步骤 | Skill | 操作 | 说明 | 状态 | 耗时 |")
        lines.append("|---|---|---|---|---|---|")
        lines.extend(skill_rows)
    cruise_rows = _build_cruise_internal_chain(contributions.get("qcloud-proactive-inspection", {}))
    if cruise_rows:
        lines.append("")
        lines.append("### proactive-inspection 内部分析器")
        lines.append("| 分析器 | 资源类型 | 分析数量 | 状态 |")
        lines.append("|---|---|---:|---|")
        for row in cruise_rows:
            parts = [p.strip() for p in row.split("|") if p.strip()]
            if len(parts) >= 5:
                lines.append(f"| {parts[1]} | {parts[3]} | {parts[4]} | {parts[5]} |")
    lines.append("")
    lines.append("### 各 Skill 结果")
    lines.append(f"- Blackboard 汇聚 **{len(contributions)}** 个 contribution")
    for skill_name, contrib in sorted(contributions.items()):
        verdict = contrib.get("verdict", "PASS")
        hint_n = len(contrib.get("topology_hints") or [])
        finding_n = len(contrib.get("findings") or [])
        label = _SKILL_LABELS.get(skill_name, skill_name)
        lines.append(
            f"- **{label}** (`{skill_name}`)：verdict={verdict}，"
            f"findings={finding_n}，topology_hints={hint_n}"
        )
    return lines


def _build_evidence_section(
    evidence_chain: dict[str, Any] | None,
    *,
    audience: str,
) -> list[str]:
    """Render Blackboard evidence_chain for human-readable audit trail."""
    if not evidence_chain:
        return ["Blackboard 尚未写入 `evidence_chain`（Copilot v1.5+ 执行后自动生成）。"]

    strategy = evidence_chain.get("strategy") or {}
    plan_snap = evidence_chain.get("plan") or {}
    process = evidence_chain.get("process") or []
    results = evidence_chain.get("results") or {}

    lines: list[str] = [
        "本节与 Blackboard `shared_context.evidence_chain` 同源，呈现策略→计划→过程→结果的完整证据链。",
        "",
        "### 1. 巡检策略（拓扑驱动，LLM-native 就绪）",
        f"- 决策器：**{strategy.get('decision_maker', '—')}** "
        f"（`llm_native_target={strategy.get('llm_native_target')}`）",
        f"- 模式：**{strategy.get('mode', '—')}** / 执行路径：**{strategy.get('execution_path', '—')}**",
    ]
    if strategy.get("llm_native_note"):
        lines.append(f"- 演进说明：{strategy['llm_native_note']}")
    topo = strategy.get("topology_summary") or {}
    if topo:
        parts = [f"{k}={v}" for k, v in sorted(topo.items()) if v]
        lines.append(f"- 客户拓扑摘要：{', '.join(parts)}")
    if strategy.get("agent_rationale"):
        lines.append(f"- Agent 决策理由：{strategy['agent_rationale']}")
    selected = strategy.get("selected_analyzers") or []
    if selected:
        lines.append(f"- 选定 analyzer：`{', '.join(selected)}`")
    skipped = strategy.get("skipped_analyzers") or []
    if skipped:
        skip_txt = ", ".join(f"{s.get('service', '?')}({s.get('reason', '')})" for s in skipped)
        lines.append(f"- 跳过 analyzer：{skip_txt}")

    priority_chain = strategy.get("priority_chain") or []
    if priority_chain:
        lines.append("")
        lines.append("| 层级 | 资源数 | 分析深度 | 依据 |")
        lines.append("|---|---:|---|---|")
        for item in priority_chain:
            lines.append(
                f"| {item.get('layer', '—')} | {item.get('resource_count', 0)} | "
                f"{item.get('analysis_depth', '—')} | {item.get('rationale', '—')[:80]} |"
            )
        if audience == "detailed":
            for item in priority_chain:
                samples = item.get("sample_resource_ids") or []
                if samples:
                    lines.append(f"- {item.get('layer')} 样本 ID：{', '.join(samples[:5])}")

    if audience == "summary":
        lines.extend(
            [
                "",
                "### 2–4. 计划 / 过程 / 结果（摘要）",
                f"- 编排步骤 **{len(plan_snap.get('steps') or [])}** 步，过程事件 **{len(process)}** 条",
                f"- 整体结论：**{results.get('overall_verdict', '—')}**",
            ]
        )
        artifacts = results.get("artifact_index") or []
        if artifacts:
            lines.append(f"- 中间产物 **{len(artifacts)}** 个（路径见 `final-report.md`）")
        return lines

    lines.extend(["", "### 2. 巡检计划（Copilot ExecutionPlan 快照）"])
    if plan_snap:
        lines.append(
            f"- plan_id：`{plan_snap.get('plan_id', '—')}`，"
            f"safety_level：{plan_snap.get('safety_level', '—')}"
        )
        lines.append(f"- 主意图：**{plan_snap.get('primary_intent', '—')}**")
        for step in plan_snap.get("steps") or []:
            lines.append(
                f"  - `{step.get('id')}` [{step.get('type')}] "
                f"{step.get('skill') or '—'}.{step.get('operation') or '—'} "
                f"— {step.get('description', '')}"
            )
    else:
        lines.append("- 无 Plan 快照")

    lines.extend(["", "### 3. 巡检过程（逐步执行证据）"])
    if process:
        lines.append("| step_id | phase | actor | status | 耗时(ms) | 产物/结论 |")
        lines.append("|---|---|---|---|---:|---|")
        for evt in process:
            extra = evt.get("artifact") or evt.get("artifact_sniff") or evt.get("verdict") or ""
            cov = evt.get("resource_coverage") or {}
            if cov.get("total_analyzed_resources"):
                extra = f"覆盖 {cov['total_analyzed_resources']} 资源"
            if evt.get("error"):
                extra = f"{extra} ⚠ {evt['error'][:60]}".strip()
            lines.append(
                f"| {evt.get('step_id', '—')} | {evt.get('phase', '—')} | "
                f"{evt.get('actor', '—')} | {evt.get('status', '—')} | "
                f"{evt.get('duration_ms', 0)} | {extra or '—'} |"
            )
    else:
        lines.append("- 无 step_results 过程记录")

    lines.extend(["", "### 4. 巡检结果（Blackboard contributions 汇聚）"])
    lines.append(f"- 整体 verdict：**{results.get('overall_verdict', '—')}**")
    for name, contrib in sorted((results.get("contributions") or {}).items()):
        lines.append(
            f"  - `{name}`：verdict={contrib.get('verdict')}，"
            f"findings={contrib.get('findings_count', 0)}，"
            f"topology_hints={contrib.get('topology_hints_count', 0)}"
        )
    artifacts = results.get("artifact_index") or []
    if artifacts:
        lines.append("")
        lines.append("**产物索引（artifact_index）**")
        for art in artifacts:
            suffix = f" service={art['service']}" if art.get("service") else ""
            lines.append(f"- [{art.get('type', '—')}] `{art.get('path', '')}`{suffix}")
    return lines


_COVERAGE_STATUS_LABEL = {
    "analyzed": "✅ 已深度分析",
    "no_resources": "⏭ 拓扑无资源",
    "discovered_not_analyzed": "⚠ 已发现未分析",
}


def _build_resource_coverage_section(cruise: dict) -> list[str]:
    """Show per-resource-type inspection inside qcloud-proactive-inspection."""
    meta = cruise.get("metadata") or {}
    coverage = meta.get("resource_coverage") or {}
    runs = coverage.get("analyzer_runs") or []
    if not runs:
        return [
            "未获取到 analyzer 覆盖明细（请检查 cruise JSON 是否包含 service_reports）。",
        ]

    lines = [
        "Copilot 层通过 **qcloud-proactive-inspection** 一次性完成拓扑内多类型资源分析；"
        "下表为各资源类型 analyzer 的实际执行情况（非独立调用 qcloud-cvm-ops 等变更 Skill）。",
        "",
        "| 资源类型 | 拓扑发现 | 深度分析 | 发现问题 | 状态 | 变更委托 Skill |",
        "|---|---:|---:|---:|---|---|",
    ]
    for run in runs:
        if run.get("analyzed_count", 0) == 0 and run.get("topology_count", 0) == 0:
            continue  # omit empty types from report noise
        status = _COVERAGE_STATUS_LABEL.get(run.get("status", ""), run.get("status", ""))
        lines.append(
            f"| {run.get('label', run.get('service', ''))} "
            f"| {run.get('topology_count', 0)} "
            f"| {run.get('analyzed_count', 0)} "
            f"| {run.get('findings_count', 0)} "
            f"| {status} "
            f"| `{run.get('ops_skill', '')}` |"
        )

    total_a = coverage.get("total_analyzed_resources", 0)
    total_t = coverage.get("total_topology_resources", 0)
    vpc_n = coverage.get("topology_vpc_count", 0)
    lines.append("")
    lines.append(
        f"**汇总**：拓扑共 **{total_t}** 个业务资源、**{vpc_n}** 个 VPC；"
        f"**{total_a}** 个资源完成指标采集与规则分析。"
    )
    sniff_path = meta.get("sniff_path", "")
    report_path = meta.get("report_path", "")
    if sniff_path or report_path:
        lines.append("")
        if sniff_path:
            lines.append(f"- 拓扑数据：`{sniff_path}`")
        if report_path:
            lines.append(f"- 分析结果：`{report_path}`")
    return lines


def _build_copilot_skill_chain(
    plan: ExecutionPlan | None, step_results: list[StepResult] | None
) -> list[str]:
    """Level-1 Copilot orchestration steps."""
    return _format_skill_table(plan, step_results)


def _build_cruise_internal_chain(cruise: dict) -> list[str]:
    """Level-2 analyzers executed inside proactive-inspection."""
    meta = cruise.get("metadata") or {}
    runs = (meta.get("resource_coverage") or {}).get("analyzer_runs") or []
    rows: list[str] = []
    for run in runs:
        if run.get("analyzed_count", 0) <= 0:
            continue
        rows.append(
            f"| cruise-analyzer | qcloud-proactive-inspection / {run.get('service', '')} "
            f"| analyze | {run.get('label', '')}（{run.get('analyzed_count', 0)} 个） "
            f"| ✅ analyzed | — |"
        )
    return rows


def _describe_plan(plan: ExecutionPlan | None) -> list[str]:
    if plan is None or not plan.steps:
        return ["无多步执行计划（单意图直查）。"]
    lines: list[str] = []
    if plan.plan_id:
        lines.append(f"计划 ID：**{plan.plan_id}**")
    intent = plan.intent
    lines.append(f"主意图：**{intent.primary.value}**")
    if intent.secondary:
        sec = ", ".join(s.value for s in intent.secondary)
        lines.append(f"附属意图：{sec}")
    lines.append(
        f"安全门级别：**L{plan.safety_level}**（L0 结构 → L1 语义 → L2 破坏性 → L3 报告审批）"
    )
    lines.append("执行 DAG（Copilot PlanDispatcher 串行/并行编排）：")
    for step in plan.steps:
        skill = step.skill or step.type
        label = _SKILL_LABELS.get(step.skill or "", step.description or step.type)
        deps = f"，依赖 `{', '.join(step.depends_on)}`" if step.depends_on else ""
        pg = f"，并行组 {step.parallel_group}" if step.parallel_group else ""
        lines.append(f"  - `{step.id}` → **{skill}** / {step.operation or '—'} — {label}{deps}{pg}")
    return lines


def _describe_scope(plan: ExecutionPlan | None, contributions: dict[str, dict]) -> list[str]:
    lines: list[str] = []
    if plan:
        for step in plan.steps:
            if step.type == "cruise_run":
                lines.append("**全链路巡检（qcloud-proactive-inspection）**")
                for item in _CRUISE_CHECK_ITEMS:
                    lines.append(f"  - {item}")
            elif step.type == "alert_analyze":
                meta = (contributions.get("qcloud-monitor-ops") or {}).get("metadata") or {}
                tw = meta.get("time_window", "最近24h")
                sf = meta.get("severity_filter", "P0,P1")
                lines.append(f"**告警分析**：{tw} 窗口内 {sf} 级别活跃告警与 topology_hints")
            elif step.type == "skill_call" and step.skill:
                if "vpc" in step.skill:
                    lines.append("**VPC 发现**：专有网络、子网、区域拓扑初判")
                else:
                    lines.append(f"**{step.skill}**：{step.description or step.operation}")
    if not lines:
        lines.append("单资源查询（inspect/diagnose 意图）。")
    return lines


def _format_skill_table(
    plan: ExecutionPlan | None, step_results: list[StepResult] | None
) -> list[str]:
    if not step_results:
        return []
    step_map: dict[str, PlanStep] = {}
    if plan:
        step_map = {s.id: s for s in plan.steps}
    rows: list[str] = []
    for sr in step_results:
        if (
            sr.step_id.endswith("-synthesize")
            or sr.step_id == "report-3"
            or sr.step_id == "report-1"
        ):
            continue
        step = step_map.get(sr.step_id)
        skill = (step.skill if step else "") or "—"
        op = (step.operation if step else "") or (step.type if step else "—")
        desc = (step.description if step else "") or "—"
        icon = "✅" if sr.status == "success" else "❌"
        rows.append(
            f"| {sr.step_id} | {skill} | {op} | {desc} | {icon} {sr.status} | {sr.duration_ms} ms |"
        )
    return rows


def _group_action_items(action_items: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    groups: dict[str, list[dict[str, str]]] = {}
    for item in action_items:
        key = _classify_issue(item["summary"])
        groups.setdefault(key, []).append(item)
    return groups


def _build_issue_analysis(groups: dict[str, list[dict[str, str]]]) -> list[str]:
    lines: list[str] = []
    for category, items in sorted(groups.items(), key=lambda x: -len(x[1])):
        playbook = _ISSUE_PLAYBOOK.get(category, _ISSUE_PLAYBOOK["其他风险"])
        lines.append(f"### {category}（{len(items)} 项）")
        lines.append(f"- **分析**：{playbook['analysis']}")
        lines.append(f"- **影响**：{playbook['impact']}")
        resources = ", ".join(
            dict.fromkeys(f"`{i['resource_id']}`" for i in items if i.get("resource_id"))
        )
        if resources:
            lines.append(f"- **涉及资源**：{resources}")
        for item in items[:6]:
            lines.append(f"  - {_format_action_item(item)}")
        if len(items) > 6:
            lines.append(f"  - … 另有 {len(items) - 6} 项同类问题")
        lines.append("")
    return lines


def _build_solution_section(groups: dict[str, list[dict[str, str]]]) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for category in groups:
        if category in seen:
            continue
        seen.add(category)
        pb = _ISSUE_PLAYBOOK.get(category, _ISSUE_PLAYBOOK["其他风险"])
        lines.append(f"### {category}")
        lines.append(f"- **建议**：{pb['recommendation']}")
        for step in pb.get("auto_steps", []):
            lines.append(f"  - {step}")
        lines.append("")
    return lines


def _build_automation_table(groups: dict[str, list[dict[str, str]]]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for category in groups:
        if category in seen:
            continue
        seen.add(category)
        pb = _ISSUE_PLAYBOOK.get(category, _ISSUE_PLAYBOOK["其他风险"])
        rows.append(
            f"| {category} | `{pb['auto_skill']}` | {pb['auto_operation']} | {pb['gate']} |"
        )
    if not rows:
        rows.append("| — | `qcloud-proactive-inspection` | 定期 re-cruise | 只读 |")
    return rows


def _resolve_customer(contributions: dict[str, dict], customer: str | None) -> str:
    if customer:
        return customer
    for contribution in contributions.values():
        meta = contribution.get("metadata") or {}
        if meta.get("customer"):
            return str(meta["customer"])
    return ""


def _collect_normalized_findings(contributions: dict[str, dict]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for skill, contribution in contributions.items():
        for raw in contribution.get("findings") or []:
            if isinstance(raw, str):
                summary, severity, resource_id, service = raw, "INFO", "", ""
            else:
                summary = str(raw.get("summary", "")).strip()
                severity = str(raw.get("severity", "INFO")).upper()
                resource_id = str(raw.get("resource_id", ""))
                service = str(raw.get("service", ""))
            if not summary or any(noise in summary for noise in _NOISE_SUBSTRINGS):
                continue
            items.append(
                {
                    "summary": summary,
                    "severity": severity,
                    "resource_id": resource_id,
                    "service": service,
                    "skill": skill,
                }
            )
    return items


def _dedupe_findings(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[dict[str, str]] = []
    for item in items:
        key = (item["severity"], item["resource_id"], item["summary"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _severity_rank(severity: str) -> int:
    order = {"P0": 0, "CRITICAL": 0, "P1": 1, "WARNING": 1, "P2": 2, "INFO": 3}
    return order.get(severity, 4)


def _format_action_item(item: dict[str, str]) -> str:
    parts = []
    if item["resource_id"]:
        label = item["resource_id"]
        if item["service"]:
            label = f"{item['resource_id']} ({item['service']})"
        parts.append(f"**{label}**")
    parts.append(item["summary"])
    return " — ".join(parts)


def _rollup_verdict(contributions: dict[str, dict]) -> str:
    verdicts = [str(c.get("verdict", "PASS")).upper() for c in contributions.values()]
    return min(verdicts, key=lambda v: _OVERALL_VERDICT.get(v, 2))


def _derive_recommendations(
    action_items: list[dict[str, str]],
    contributions: dict[str, dict],
) -> list[str]:
    blob = " ".join(item["summary"] for item in action_items)
    recs: list[str] = []
    if "未加密" in blob:
        recs.append("优先为生产 VM 数据盘启用加密（委托 `qcloud-cbs-ops`）。")
    if "到期" in blob:
        recs.append("核查 30 天内到期资源并安排续费（`qcloud-monitor-ops` 到期巡航）。")
    alert = contributions.get("qcloud-monitor-ops", {})
    if alert.get("verdict") == "CRITICAL":
        recs.append("针对 CRITICAL 告警资源做定向深度巡检（`qcloud-proactive-inspection` targeted）。")
    if not action_items and _rollup_verdict(contributions) == "PASS":
        recs.append("当前无必修项，建议保持每周定期巡检节奏。")
    elif not recs:
        recs.append("按优先级逐项确认上述需处理项，变更前走人工审批。")
    return recs[:5]


def synthesize_from_blackboard(
    contributions: dict[str, dict],
    audience: str = "detailed",
    *,
    customer: str | None = None,
    user_request: str = "",
    plan: ExecutionPlan | None = None,
    step_results: list[StepResult] | None = None,
    evidence_chain: dict[str, Any] | None = None,
) -> Report:
    """Aggregate skill contributions into a comprehensive human-facing Final Report."""
    customer_name = _resolve_customer(contributions, customer)
    region = (plan.context.get("region") if plan else None) or "ap-guangzhou"
    normalized = _dedupe_findings(_collect_normalized_findings(contributions))
    action_items, info_items = _split_action_and_info(normalized)
    issue_groups = _group_action_items(action_items)

    overall = _rollup_verdict(contributions)
    cruise = contributions.get("qcloud-proactive-inspection", {})
    alert = contributions.get("qcloud-monitor-ops", {})
    cruise_meta = cruise.get("metadata") or {}
    alert_meta = alert.get("metadata") or {}

    coverage = cruise_meta.get("resource_coverage") or {}
    resources_checked = coverage.get("total_analyzed_resources") or len(
        cruise.get("topology_hints") or []
    )
    cruise_mode = cruise_meta.get("mode", "full")
    alarm_count = alert_meta.get("alarm_count")
    if alarm_count is None and alert:
        alarm_count = len(alert.get("findings") or [])
    time_window = alert_meta.get("time_window", "最近24h")

    sections: list[ReportSection] = []

    if overall == "CRITICAL":
        sections.append(
            ReportSection(
                title="人工确认",
                severity="critical",
                findings=["存在 CRITICAL 级别结论，下发任何变更前必须人工审阅确认（L3 Gate）。"],
            )
        )

    sections.append(
        ReportSection(
            title="巡检结论",
            severity=_VERDICT_SEVERITY.get(overall, "info"),
            findings=_build_conclusion_findings(
                overall=overall,
                customer_name=customer_name,
                action_items=action_items,
                issue_groups=issue_groups,
                alert=alert,
                alarm_count=alarm_count,
                time_window=time_window,
            ),
        )
    )

    coverage_lines = _build_resource_coverage_section(cruise)
    if coverage_lines:
        sections.append(
            ReportSection(
                title="拓扑资源巡检覆盖",
                severity="info",
                findings=coverage_lines,
            )
        )

    evidence_lines = _build_evidence_section(evidence_chain, audience=audience)
    if evidence_lines:
        sections.append(
            ReportSection(
                title="巡检证据链",
                severity="info",
                findings=evidence_lines,
            )
        )

    chain_findings: list[str] = []
    copilot_rows = _build_copilot_skill_chain(plan, step_results)
    cruise_rows = _build_cruise_internal_chain(cruise)
    if copilot_rows or cruise_rows:
        if copilot_rows:
            chain_findings.append("**L1 — Copilot 编排层**（PlanDispatcher 调度的产品 Skill）")
            chain_findings.append("| 步骤 | Skill | 操作 | 说明 | 状态 | 耗时 |")
            chain_findings.append("|---|---|---|---|---|---|")
            chain_findings.extend(copilot_rows)
        if cruise_rows:
            chain_findings.append("")
            chain_findings.append(
                "**L2 — proactive-inspection 分析层**（拓扑内资源只读深度分析，非独立产品 Skill 调用）"
            )
            chain_findings.append("| 步骤 | Skill | 操作 | 说明 | 状态 | 耗时 |")
            chain_findings.append("|---|---|---|---|---|---|")
            chain_findings.extend(cruise_rows)
        sections.append(
            ReportSection(
                title="Skill 调用链",
                severity="info",
                findings=chain_findings,
            )
        )

    if action_items:
        sections.append(
            ReportSection(
                title="需处理项（按优先级）",
                severity="warning" if overall != "CRITICAL" else "critical",
                findings=_build_prioritized_actions(action_items),
            )
        )
        if audience == "detailed":
            sections.append(
                ReportSection(
                    title="问题发现与分析",
                    severity="warning",
                    findings=_build_issue_analysis(issue_groups),
                )
            )
            sections.append(
                ReportSection(
                    title="推荐解决方案",
                    severity="info",
                    findings=_build_solution_section(issue_groups),
                )
            )
            sections.append(
                ReportSection(
                    title="自动化修复路径",
                    severity="info",
                    findings=_build_automation_table(issue_groups),
                    recommendations=[
                        "以上路径均为 **建议编排**，实际变更须走 Copilot L2 确认 + 产品 Skill Safety Gate。",
                        '只读复查可立即执行：`python -m copilot ask "<客户> 定向巡检" --reviewed`',
                    ],
                )
            )
        else:
            sections.append(
                ReportSection(
                    title="下一步行动",
                    severity="info",
                    findings=_build_next_actions(issue_groups),
                    recommendations=[
                        "变更操作须人工审批（L2）；技术细节与调用链见 `final-report.md`。",
                    ],
                )
            )
    else:
        sections.append(
            ReportSection(
                title="需处理项（按优先级）",
                severity="success",
                findings=["未发现需处理的必修项（含 30 天内到期预警）。"],
            )
        )
        recs = _derive_recommendations(action_items, contributions)
        if recs:
            title = "下一步行动" if audience == "summary" else "推荐解决方案"
            sections.append(
                ReportSection(
                    title=title,
                    severity="info",
                    findings=[f"- {r}" for r in recs],
                )
            )

    if audience == "detailed":
        sections.append(
            ReportSection(
                title="附录：巡检过程",
                severity="info",
                findings=_build_appendix_findings(
                    region=region,
                    customer_name=customer_name,
                    overall=overall,
                    resources_checked=resources_checked,
                    cruise_mode=cruise_mode,
                    alarm_count=alarm_count,
                    time_window=time_window,
                    action_count=len(action_items),
                    plan=plan,
                    contributions=contributions,
                    step_results=step_results,
                ),
            )
        )
        if info_items:
            reference = [_format_action_item(item) for item in info_items[:10]]
            if len(info_items) > 10:
                reference.append(f"… 另有 {len(info_items) - 10} 条环境参考项未展开")
            sections.append(
                ReportSection(
                    title="环境参考",
                    severity="info",
                    findings=reference,
                )
            )

    p0_n = sum(1 for i in action_items if _action_bucket(i["severity"]) == "P0")
    p1_n = sum(1 for i in action_items if _action_bucket(i["severity"]) == "P1")
    summary = (
        f"整体 {overall}：{len(action_items)} 项需处理（P0 {p0_n} / P1 {p1_n}）"
        if action_items
        else f"整体 {overall}：无必修项"
    )
    if audience == "summary":
        title = f"AIOps 巡检简报 — {customer_name}" if customer_name else "AIOps 巡检简报"
    else:
        title = f"AIOps Final Report — {customer_name}" if customer_name else "AIOps Final Report"

    return Report(
        title=title,
        summary=summary,
        sections=sections,
        aggregated=True,
        customer=customer_name,
        user_request=user_request,
        audience=audience,
    )
