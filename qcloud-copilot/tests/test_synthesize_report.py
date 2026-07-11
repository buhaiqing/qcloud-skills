from datetime import datetime, timezone

from copilot.models import ExecutionResult, ExecutionPlan, ClassifiedIntent, IntentType, StepResult
from copilot.report_gen import render_markdown, synthesize_from_blackboard
from copilot.safety.l3 import check_l3


def test_synthesize_aggregates_contributions():
    contributions = {
        "qcloud-monitor-ops": {
            "version": "0.4.0",
            "verdict": "WARNING",
            "findings": [{"id": "f1", "severity": "P1", "summary": "CPU high"}],
            "topology_hints": ["i-abc"],
            "metadata": {},
        },
        "qcloud-proactive-inspection": {
            "version": "3.0.0",
            "verdict": "PASS",
            "findings": [{"id": "f2", "severity": "INFO", "summary": "Cruise OK"}],
            "topology_hints": ["i-abc"],
            "metadata": {},
        },
    }
    report = synthesize_from_blackboard(contributions, audience="detailed")
    assert report.aggregated is True
    assert "需处理" in report.summary or "无必修项" in report.summary
    titles = {s.title for s in report.sections}
    assert "巡检结论" in titles
    assert "需处理项（按优先级）" in titles


def test_full_report_includes_plan_and_skills():
    from copilot.models import ClassifiedIntent, ExecutionPlan, IntentType, PlanStep, StepResult

    contributions = {
        "qcloud-proactive-inspection": {
            "verdict": "WARNING",
            "findings": [
                {
                    "severity": "P1",
                    "summary": "数据盘 test-disk 未加密",
                    "resource_id": "i-abc",
                    "service": "vm",
                }
            ],
            "topology_hints": ["i-abc"],
            "metadata": {"customer": "朔州天源", "mode": "full"},
        },
        "qcloud-monitor-ops": {
            "verdict": "PASS",
            "findings": [],
            "metadata": {"time_window": "最近24h", "alarm_count": 0},
        },
    }
    plan = ExecutionPlan(
        intent=ClassifiedIntent(
            primary=IntentType.REPORT, targets=[], secondary=[IntentType.CRUISE]
        ),
        steps=[
            PlanStep(
                id="vpc-0", type="skill_call", skill="qcloud-vpc-ops", operation="describe-vpcs"
            ),
            PlanStep(id="cruise-1", type="cruise_run", skill="qcloud-proactive-inspection"),
            PlanStep(id="alert-2", type="alert_analyze", skill="qcloud-monitor-ops"),
        ],
        plan_id="risk-assessment-plan",
        context={"customer": "朔州天源", "region": "ap-guangzhou"},
    )
    step_results = [
        StepResult(step_id="vpc-0", status="success", duration_ms=100),
        StepResult(step_id="cruise-1", status="success", duration_ms=35000),
        StepResult(step_id="alert-2", status="success", duration_ms=2000),
    ]
    report = synthesize_from_blackboard(
        contributions,
        plan=plan,
        step_results=step_results,
        user_request="朔州天源 VPC 风险巡检",
    )
    titles = {s.title for s in report.sections}
    assert "附录：巡检过程" in titles
    assert "拓扑资源巡检覆盖" in titles
    assert "Skill 调用链" in titles
    assert "问题发现与分析" in titles
    assert "自动化修复路径" in titles
    md = render_markdown(report)
    assert "qcloud-proactive-inspection" in md
    assert "磁盘未加密" in md
    assert md.index("## 巡检结论") < md.index("## 需处理项")
    assert "整体评估" in md


def test_summary_audience_is_management_one_pager():
    contributions = {
        "qcloud-proactive-inspection": {
            "verdict": "WARNING",
            "findings": [
                {
                    "severity": "P1",
                    "summary": "数据盘 test-disk 未加密",
                    "resource_id": "i-abc",
                    "service": "vm",
                }
            ],
            "metadata": {"customer": "朔州天源"},
        },
    }
    report = synthesize_from_blackboard(contributions, audience="summary", customer="朔州天源")
    titles = {s.title for s in report.sections}
    assert "巡检简报" in report.title
    assert "下一步行动" in titles
    assert "附录：巡检过程" not in titles
    assert "问题发现与分析" not in titles


def test_expiry_within_30_days_promoted_to_p1():
    from datetime import timedelta

    expire = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%dT15:59:59Z")
    contributions = {
        "qcloud-proactive-inspection": {
            "verdict": "WARNING",
            "findings": [
                {
                    "severity": "INFO",
                    "summary": f"到期时间: {expire}",
                    "resource_id": "i-testvm",
                    "service": "vm",
                }
            ],
            "metadata": {"customer": "朔州天源"},
        },
    }
    report = synthesize_from_blackboard(
        contributions,
        audience="detailed",
        customer="朔州天源",
    )
    action = next(s for s in report.sections if s.title.startswith("需处理项"))
    blob = "\n".join(action.findings)
    assert "P1" in blob
    assert "仅剩" in blob
    analysis = next(s for s in report.sections if s.title == "问题发现与分析")
    assert "资源即将到期" in "\n".join(analysis.findings)


def test_report_shows_resource_coverage_from_metadata():
    contributions = {
        "qcloud-proactive-inspection": {
            "verdict": "WARNING",
            "findings": [],
            "metadata": {
                "customer": "朔州天源",
                "mode": "full",
                "resource_coverage": {
                    "analyzer_runs": [
                        {
                            "service": "vm",
                            "label": "云主机 ECS",
                            "ops_skill": "qcloud-cvm-ops",
                            "topology_count": 4,
                            "analyzed_count": 4,
                            "findings_count": 8,
                            "status": "analyzed",
                            "via": "qcloud-proactive-inspection",
                        },
                        {
                            "service": "redis",
                            "label": "Redis 缓存",
                            "ops_skill": "qcloud-redis-ops",
                            "topology_count": 0,
                            "analyzed_count": 0,
                            "findings_count": 0,
                            "status": "no_resources",
                            "via": "qcloud-proactive-inspection",
                        },
                    ],
                    "total_analyzed_resources": 4,
                    "total_topology_resources": 9,
                    "topology_vpc_count": 1,
                },
            },
        },
    }
    report = synthesize_from_blackboard(contributions, customer="朔州天源")
    coverage = next(s for s in report.sections if s.title == "拓扑资源巡检覆盖")
    blob = "\n".join(coverage.findings)
    assert "云主机 ECS" in blob
    assert "qcloud-proactive-inspection" in blob
    chain = next(s for s in report.sections if s.title == "Skill 调用链")
    assert "L2" in "\n".join(chain.findings)


def test_critical_triggers_l3_gate():
    contributions = {
        "qcloud-monitor-ops": {
            "version": "0.4.0",
            "verdict": "CRITICAL",
            "findings": [{"id": "f1", "severity": "P0", "summary": "Disk full"}],
            "topology_hints": [],
            "metadata": {},
        },
    }
    report = synthesize_from_blackboard(contributions)
    assert any(s.severity == "critical" for s in report.sections)

    intent = ClassifiedIntent(primary=IntentType.REPORT, targets=[])
    plan = ExecutionPlan(intent=intent, steps=[])
    result = ExecutionResult(
        plan=plan,
        step_results=[StepResult(step_id="report-3", status="success")],
        final_report=report,
        status="awaiting_confirmation",
    )
    assert check_l3(result, reviewed=False)["passed"] is False
    assert check_l3(result, reviewed=True)["passed"] is True
