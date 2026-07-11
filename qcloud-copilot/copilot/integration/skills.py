from __future__ import annotations

import json
import subprocess

from copilot.models import PlanStep, StepResult

KNOWN_SKILLS = {
    "qcloud-cvm-ops",
    "qcloud-redis-ops",
    "qcloud-cdb-ops",
    "qcloud-postgres-ops",
    "qcloud-mongodb-ops",
    "qcloud-es-ops",
    "qcloud-tke-ops",
    "qcloud-monitor-ops",
    "qcloud-cam-ops",
    "qcloud-vpc-ops",
    "qcloud-clb-ops",
    "qcloud-cbs-ops",
    "qcloud-cos-ops",
    "qcloud-cdn-ops",
    "qcloud-scf-ops",
    "qcloud-ssl-ops",
    "qcloud-finops-ops",
    "qcloud-cls-ops",
    "qcloud-ckafka-ops",
    "qcloud-apigw-ops",
    "qcloud-proactive-inspection",
    "qcloud-aiops-diagnosis",
    "qcloud-copilot",
}

# tccli product name (lowercase) per skill.
SKILL_TO_PRODUCT = {
    "qcloud-cvm-ops": "cvm",
    "qcloud-redis-ops": "redis",
    "qcloud-cdb-ops": "cdb",
    "qcloud-postgres-ops": "postgres",
    "qcloud-mongodb-ops": "mongodb",
    "qcloud-es-ops": "es",
    "qcloud-tke-ops": "tke",
    "qcloud-monitor-ops": "monitor",
    "qcloud-cam-ops": "cam",
    "qcloud-vpc-ops": "vpc",
    "qcloud-clb-ops": "clb",
    "qcloud-cbs-ops": "cbs",
    "qcloud-cos-ops": "cos",
    "qcloud-cdn-ops": "cdn",
    "qcloud-scf-ops": "scf",
    "qcloud-ssl-ops": "ssl",
    "qcloud-finops-ops": "billing",
    "qcloud-cls-ops": "cls",
    "qcloud-ckafka-ops": "ckafka",
    "qcloud-apigw-ops": "apigateway",
    "qcloud-proactive-inspection": "monitor",
    "qcloud-aiops-diagnosis": "monitor",
}

# kebab-case plan op → tccli PascalCase API.
OPERATION_TO_TCCLI: dict[str, str] = {
    "describe": "DescribeInstances",
    "describe-instances": "DescribeInstances",
    "describe-instance": "DescribeInstances",
    "describe-vpcs": "DescribeVpcs",
    "describe-vpc": "DescribeVpcs",
    "describe-subnets": "DescribeSubnets",
    "describe-load-balancers": "DescribeLoadBalancers",
    "describe-alarms": "DescribeAlarmPolicies",
    "describe-alarm": "DescribeAlarmPolicies",
    "describe-alarm-history": "DescribeAlarmHistories",
    "describe-alerts": "DescribeAlarmHistories",
    "describe-metrics": "GetMonitorData",
    "describe-metric-data": "GetMonitorData",
    "describe-cache-instances": "DescribeInstances",
    "describe-cache-instance": "DescribeInstances",
    "describe-db-instances": "DescribeDBInstances",
    "describe-db-instance": "DescribeDBInstances",
    "describe-clusters": "DescribeClusters",
    "describe-cluster": "DescribeClusters",
    "describe-disks": "DescribeDisks",
    "describe-disk": "DescribeDisks",
    "describe-eips": "DescribeAddresses",
    "describe-certificates": "DescribeCertificates",
    "describe-bills": "DescribeBillDetail",
    "describe-account-balance": "DescribeAccountBalance",
    "list-buckets": "ListBuckets",
}

SAFE_OPERATIONS = set(OPERATION_TO_TCCLI.keys())

OPERATION_ALIAS = {
    ("qcloud-cvm-ops", "describe"): "describe-instances",
    ("qcloud-redis-ops", "describe"): "describe-cache-instances",
    ("qcloud-cdb-ops", "describe"): "describe-db-instances",
    ("qcloud-postgres-ops", "describe"): "describe-db-instances",
    ("qcloud-mongodb-ops", "describe"): "describe-instances",
    ("qcloud-es-ops", "describe"): "describe-instances",
    ("qcloud-tke-ops", "describe"): "describe-clusters",
    ("qcloud-monitor-ops", "describe"): "describe-alarms",
    ("qcloud-cbs-ops", "describe"): "describe-disks",
    ("qcloud-vpc-ops", "describe"): "describe-vpcs",
    ("qcloud-clb-ops", "describe"): "describe-load-balancers",
    ("qcloud-cos-ops", "describe"): "list-buckets",
    ("qcloud-ssl-ops", "describe"): "describe-certificates",
    ("qcloud-finops-ops", "describe"): "describe-bills",
}

SKILL_PARAM_MAPPING = {
    ("qcloud-cvm-ops", "describe-instance"): "InstanceIds.0",
    ("qcloud-redis-ops", "describe-cache-instance"): "InstanceId",
    ("qcloud-cdb-ops", "describe-db-instance"): "InstanceId",
    ("qcloud-postgres-ops", "describe-db-instance"): "InstanceId",
    ("qcloud-mongodb-ops", "describe-instance"): "InstanceId",
    ("qcloud-cbs-ops", "describe-disk"): "DiskIds.0",
    ("qcloud-clb-ops", "describe-load-balancers"): "LoadBalancerIds.0",
    ("qcloud-vpc-ops", "describe-vpc"): "VpcIds.0",
    ("qcloud-monitor-ops", "describe-alarm"): "Module",
}

RESOURCE_ID_PREFIXES = (
    "ins-",
    "cdb-",
    "cdbro-",
    "redis-",
    "lb-",
    "vpc-",
    "subnet-",
    "sg-",
    "disk-",
    "cls-",
)


def _resolve_tccli_operation(skill: str, operation: str) -> str:
    operation = OPERATION_ALIAS.get((skill, operation), operation)
    if operation not in SAFE_OPERATIONS:
        raise ValueError(operation)
    return OPERATION_TO_TCCLI[operation]


class SkillDispatcher:
    def __init__(self):
        self._known_skills = KNOWN_SKILLS

    def validate_skill(self, skill: str) -> bool:
        return skill in self._known_skills

    def execute(self, step: PlanStep, context: dict) -> StepResult:
        skill = step.skill or ""
        if not self.validate_skill(skill):
            return StepResult(
                step_id=step.id,
                status="failure",
                error=f"Unknown skill: {skill}. Known skills: {sorted(self._known_skills)}",
            )

        operation = step.params.get("operation", "describe")
        try:
            operation = OPERATION_ALIAS.get((skill, operation), operation)
            if operation not in SAFE_OPERATIONS:
                raise ValueError(operation)
            tccli_op = _resolve_tccli_operation(skill, operation)
        except ValueError:
            return StepResult(
                step_id=step.id,
                status="failure",
                error=(
                    f"Operation '{operation}' is NOT in SAFE_OPERATIONS whitelist. "
                    "Refusing to dispatch. Caller must use L2 gate + explicit --confirm."
                ),
            )

        product = SKILL_TO_PRODUCT.get(skill)
        if product is None:
            return StepResult(
                step_id=step.id,
                status="failure",
                error=f"Skill {skill} has no SKILL_TO_PRODUCT mapping",
            )

        region = context.get("region") or step.params.get("region") or "ap-guangzhou"
        cmd = ["tccli", product, tccli_op, "--region", region, "--output", "json"]

        target = step.params.get("target")
        if target:
            target_str = target[0] if isinstance(target, list) else target
            looks_like_id = target_str.startswith(RESOURCE_ID_PREFIXES)
            id_flag = SKILL_PARAM_MAPPING.get((skill, operation))
            if id_flag and looks_like_id:
                cmd.extend([f"--{id_flag}", target_str])
            elif id_flag and not looks_like_id:
                pass
            elif not id_flag and looks_like_id:
                return StepResult(
                    step_id=step.id,
                    status="failure",
                    error=(
                        f"Skill {skill} operation {operation} needs resource-id but "
                        "no SKILL_PARAM_MAPPING entry."
                    ),
                )

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            return StepResult(
                step_id=step.id,
                status="failure",
                error=f"tccli command timed out after 30s: {' '.join(cmd[:6])}...",
            )
        except FileNotFoundError:
            return StepResult(
                step_id=step.id,
                status="failure",
                error="tccli not found in PATH; pip install tccli",
            )

        parsed: dict = {}
        if proc.stdout.strip():
            try:
                parsed = json.loads(proc.stdout)
            except json.JSONDecodeError as exc:
                return StepResult(
                    step_id=step.id,
                    status="failure",
                    error=f"tccli output is not valid JSON: {exc}. stdout[:200]={proc.stdout[:200]}",
                    output={"command_invoked": cmd, "raw_stdout": proc.stdout[:2000]},
                )

        if proc.returncode != 0:
            err_msg = proc.stderr[:500] or parsed.get("Error", {}).get("Message") or "unknown tccli failure"
            return StepResult(
                step_id=step.id,
                status="failure",
                error=f"tccli failed: {err_msg}",
                output={"command_invoked": cmd, "raw_response": parsed},
            )

        response = parsed.get("Response", parsed)
        return StepResult(
            step_id=step.id,
            status="success",
            output={
                "command_invoked": cmd,
                "skill": skill,
                "operation": operation,
                "data": response,
            },
            error=None,
        )
