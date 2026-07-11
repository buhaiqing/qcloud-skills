from __future__ import annotations

from copilot.models import PlanStep
from copilot.integration.skills import KNOWN_SKILLS

# Each skill maps to a set of known operations.
# Partial coverage is acceptable — when skill_ops is non-empty but incomplete,
# only enumerated operations are validated (others pass silently).
# Skills not in this dict have skill_ops=set() and skip operation-level check.
KNOWN_OPERATIONS = {
    "qcloud-cvm-ops": {
        "describe",
        "describe-instance",
        "describe-instances",
        "stop-instance",
        "start-instance",
        "restart-instance",
        "delete-instance",
        "reboot-instance",
        "associate-eip",
        "dissociate-eip",
        "modify-instance-attribute",
    },
    "qcloud-redis-ops": {
        "describe",
        "describe-cache-instances",
        "describe-cache-instance",
        "delete-instance",
        "restart-instance",
        "modify-instance-attribute",
    },
    "qcloud-cdb-ops": {
        "describe",
        "describe-instances",
        "describe-instance",
        "delete-instance",
        "restart-instance",
        "modify-instance-attribute",
    },
    "qcloud-tke-ops": {
        "describe",
        "describe-clusters",
        "describe-node-groups",
        "delete-cluster",
        "scale-node-group",
        "upgrade-cluster",
    },
    "qcloud-cam-ops": {
        "describe",
        "describe-users",
        "create-user",
        "delete-user",
        "attach-policy",
        "detach-policy",
        "create-access-key",
        "delete-access-key",
    },
    "qcloud-vpc-ops": {
        "describe",
        "describe-vpcs",
        "describe-eips",
        "allocate-eip",
        "associate-eip",
        "dissociate-eip",
        "release-eip",
        "modify-bandwidth",
        "describe-nat-gateways",
        "create-nat-gateway",
        "delete-nat-gateway",
        "describe-snat-rules",
        "create-snat-rule",
        "delete-snat-rule",
    },
    "qcloud-cbs-ops": {
        "describe",
        "describe-disks",
        "attach-disk",
        "detach-disk",
        "delete-disk",
        "resize-disk",
        "create-snapshot",
        "delete-snapshot",
    },
    "qcloud-cos-ops": {
        "describe",
        "list-buckets",
        "create-bucket",
        "delete-bucket",
        "put-object",
        "get-object",
        "delete-object",
        "list-objects",
        "set-bucket-acl",
    },
    "qcloud-cdn-ops": {
        "describe",
        "describe-instances",
        "describe-domains",
        "create-domain",
        "delete-domain",
        "create-rule",
        "delete-rule",
        "describe-attack-logs",
        "describe-records",
        "create-record",
        "update-record",
        "delete-record",
    },
    "qcloud-scf-ops": {
        "describe",
        "describe-services",
        "create-service",
        "delete-service",
        "describe-functions",
        "invoke-function",
        "create-version",
        "create-trigger",
    },
    "qcloud-ssl-ops": {
        "describe",
        "describe-certificates",
        "upload-certificate",
        "delete-certificate",
        "download-certificate",
    },
    "qcloud-finops-ops": {
        "describe",
        "describe-account-balance",
        "describe-bills",
        "describe-consumption",
        "describe-vouchers",
    },
    "qcloud-monitor-ops": {
        "describe",
        "describe-metrics",
        "describe-alarms",
        "describe-alarm",
        "describe-alarm-history",
        "describe-alarm-rules",
        "describe-alarm-rule",
        "describe-alerts",
        "aggregate-alerts",
        "suppress-alerts",
        "describe-resources",
        "describe-expiring-resources",
        "check-resource-inventory",
        "create-alarm-rule",
        "delete-alarm-rule",
    },
    "qcloud-proactive-inspection": {"cruise", "sniff", "link"},
}


def check_h(step: PlanStep) -> dict:
    issues = []

    if not step.skill:
        issues.append("Step missing skill name")

    if step.type == "skill_call" and step.skill:
        if step.skill not in KNOWN_SKILLS:
            issues.append(f"Unknown skill: {step.skill}")

        skill_ops = KNOWN_OPERATIONS.get(step.skill, set())
        op = step.params.get("operation", "")
        if skill_ops and op and op not in skill_ops:
            issues.append(f"Unknown operation '{op}' for skill {step.skill}")

    return {"passed": len(issues) == 0, "issues": issues}
