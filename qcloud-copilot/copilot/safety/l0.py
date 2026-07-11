from __future__ import annotations

import re
from copilot.models import ParsedRequest, ClassifiedIntent
from copilot.integration.skills import KNOWN_SKILLS
from copilot.context_manager import ContextManager

RESOURCE_ID_PATTERN = re.compile(
    r"^(ins|cdb|cdbro|redis|mongodb|postgres|"
    r"lb|clb|vpc|subnet|sg|nat|"
    r"disk|cbs|cos|scf|cls|"
    r"ssl|cdn|cam|tke|es|"
    r"apigw|ckafka)-[\w-]+$",
    re.IGNORECASE,
)


def check_l0(request: ParsedRequest, intent: ClassifiedIntent) -> dict:
    issues = []
    for target in intent.targets:
        if "qcloud-" in target and target not in KNOWN_SKILLS:
            issues.append(f"Unknown skill: {target}")
    for rid in request.entities.get("resource_id", []):
        if not RESOURCE_ID_PATTERN.match(rid):
            issues.append(f"Malformed resource ID: {rid}")
    cm = ContextManager()
    for region in request.entities.get("region", []):
        if cm.resolve_region(region) is None:
            issues.append(f"Unknown region: {region}")

    return {"passed": len(issues) == 0, "issues": issues}
