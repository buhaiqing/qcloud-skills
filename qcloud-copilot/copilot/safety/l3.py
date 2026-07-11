from __future__ import annotations

from copilot.models import ExecutionResult, IntentType


def check_l3(result: ExecutionResult, reviewed: bool = False) -> dict:
    issues = []

    if result.status == "awaiting_confirmation" and not reviewed:
        issues.append(
            "CRITICAL findings require human review before delivery. "
            "Use --reviewed to confirm review and proceed."
        )

    if result.final_report is None:
        return {"passed": len(issues) == 0, "issues": issues}

    if result.plan.intent.primary == IntentType.UNKNOWN:
        return {"passed": True, "issues": []}

    has_critical_section = any(s.severity == "critical" for s in result.final_report.sections)
    if has_critical_section and not reviewed:
        issues.append(
            "Critical findings in report require human review before delivery. "
            "Use --reviewed to confirm review and proceed."
        )

    return {"passed": len(issues) == 0, "issues": issues}
