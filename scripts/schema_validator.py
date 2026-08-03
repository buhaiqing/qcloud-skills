#!/usr/bin/env python3
"""schema_validator.py — Validate tccli response JSON structure against knowledge base.

Three-layer check #2: JSON 结构合规
对照 OpenAPI / tccli schema 验证响应字段是否符合预期。

Knowledge base: skill -> action -> (required_fields, expected_fields).
Only validates structure; does not check values.

CLI usage::

    python3 scripts/schema_validator.py --trace-dir audit-results
    python3 scripts/schema_validator.py --command 'tccli cvm DescribeInstances' --response '{"Response":{"RequestId":"x"}}'
    python3 scripts/schema_validator.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Schema knowledge base: skill -> action -> schema spec
# ---------------------------------------------------------------------------
# required: fields that MUST be present in a successful response
# data_field: the key under Response that holds the actual data (or empty for no data wrap)
# request_id: field name for request tracking
# error_in_response: whether Error may appear in Response (some APIs put it there)
_SCHEMA_KB: dict[str, dict[str, dict[str, Any]]] = {
    "qcloud-cvm-ops": {
        "DescribeInstances": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.InstanceSet",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "TerminateInstances": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.TerminateInstanceSet",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "StopInstances": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "StartInstances": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "RebootInstances": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "DescribeInstancesModified": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.InstanceSet",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
    },
    "qcloud-cdb-ops": {
        "DescribeDBInstances": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.InstanceSet",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "DeleteDBInstance": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "IsolateDBInstance": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "CreateAccount": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
    },
    "qcloud-redis-ops": {
        "DescribeCacheInstances": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.InstanceSet",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "DeleteInstance": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "RestartInstance": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "FlushInstance": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
    },
    "qcloud-clb-ops": {
        "DescribeLoadBalancers": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.LoadBalancerSet",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "DeleteLoadBalancers": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "CreateListener": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.ListenerIds",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
    },
    "qcloud-cos-ops": {
        "ListBuckets": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.Buckets",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "DeleteBucket": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "PutObject": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "GetObject": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "DeleteObject": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "ListObjects": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.ObjectList",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
    },
    "qcloud-tke-ops": {
        "DescribeClusters": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.Clusters",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "DeleteCluster": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "DescribeClusterInstances": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.InstanceSet",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "DescribeNodeGroups": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.NodePoolSet",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "ScaleNodeGroup": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
    },
    "qcloud-vpc-ops": {
        "DescribeVpcs": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.VpcSet",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "DeleteVpc": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "DescribeEips": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.AddressSet",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "AllocateAddresses": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.AddressSet",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "ReleaseAddresses": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
    },
    "qcloud-cbs-ops": {
        "DescribeDisks": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.DiskSet",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "AttachDisk": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "DetachDisk": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "TerminateDisks": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
    },
    "qcloud-cam-ops": {
        "DescribeUsers": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.Data",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "CreateUser": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "DeleteUser": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "AttachPolicy": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
    },
    "qcloud-cdn-ops": {
        "DescribeDomains": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.Distributions",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "DeleteDomain": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "PurgePathCache": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
    },
    "qcloud-scf-ops": {
        "DescribeFunctions": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.Functions",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "DeleteFunction": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "InvokeFunction": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.Result",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
    },
    "qcloud-monitor-ops": {
        "DescribeAlarmPolicies": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.Policies",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "DeleteAlarmPolicy": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
        "CreateAlarmPolicy": {
            "required": ["Response", "Response.RequestId"],
            "data_field": "Response.PolicyId",
            "request_id": "Response.RequestId",
            "error_in_response": False,
        },
    },
}


def _detect_action(cmd: str) -> tuple[str, str]:
    """Parse tccli command to (skill, action)."""
    m = re.search(r"tccli\s+(\w+)\s+(\w+)", cmd)
    if not m:
        return "", ""
    product, action = m.group(1), m.group(2)
    skill_map = {
        "cvm": "qcloud-cvm-ops", "cdb": "qcloud-cdb-ops", "redis": "qcloud-redis-ops",
        "clb": "qcloud-clb-ops", "cos": "qcloud-cos-ops", "tke": "qcloud-tke-ops",
        "vpc": "qcloud-vpc-ops", "cbs": "qcloud-cbs-ops", "cam": "qcloud-cam-ops",
        "cdn": "qcloud-cdn-ops", "scf": "qcloud-scf-ops", "monitor": "qcloud-monitor-ops",
    }
    return skill_map.get(product.lower(), f"qcloud-{product}-ops"), action


def _get_nested(d: dict, path: str) -> Any:
    """Get value from nested dict via dot-notation path."""
    for key in path.split("."):
        if not isinstance(d, dict) or key not in d:
            return None
        d = d[key]
    return d


def validate_response_schema(cmd: str, response: dict, skill: str = "") -> list[dict[str, Any]]:
    """Validate a parsed JSON response against the schema KB.

    Returns list of violations (empty = valid).
    Each violation: {type, path, severity, suggestion}
    """
    if not skill:
        skill, action = _detect_action(cmd)
    else:
        _, action = _detect_action(cmd)

    violations = []
    schema = _SCHEMA_KB.get(skill, {}).get(action)
    if schema is None:
        return []  # unknown API — pass silently

    resp = response.get("Response", {})

    # 1. Required top-level fields
    for req in schema.get("required", []):
        val = _get_nested(response, req)
        if val is None:
            violations.append({
                "type": "missing_required_field",
                "path": req,
                "severity": "critical",
                "suggestion": f"Response missing required field '{req}' — check API version compatibility",
            })

    # 2. RequestId presence
    req_id_path = schema.get("request_id", "Response.RequestId")
    if _get_nested(response, req_id_path) is None:
        violations.append({
            "type": "missing_request_id",
            "path": req_id_path,
            "severity": "high",
            "suggestion": "Response missing RequestId — cannot correlate with logs",
        })

    # 3. Data field consistency for list queries
    data_field = schema.get("data_field", "")
    is_list = any(k in action.lower() for k in ["describe", "list", "query", "search"])
    if is_list and data_field and "Error" not in resp:
        data = _get_nested(response, data_field)
        if data is None:
            violations.append({
                "type": "null_data_on_list_query",
                "path": data_field,
                "severity": "medium",
                "suggestion": f"List query '{action}' returned no data; possible pagination issue or API drift",
            })
        elif isinstance(data, (list, dict)) and not data:
            violations.append({
                "type": "empty_data_on_list_query",
                "path": data_field,
                "severity": "low",
                "suggestion": f"List query '{action}' returned empty result — confirm this is expected",
            })

    # 4. Error without RequestId (indicates hallucination or malformed response)
    if (
        "Error" in resp
        and not schema.get("error_in_response")
        and _get_nested(response, req_id_path) is None
    ):
            violations.append({
                "type": "error_without_request_id",
                "path": "Response.Error",
                "severity": "critical",
                "suggestion": "Error in response without RequestId — possible hallucinated response",
            })

    return violations


def validate_trace(trace: dict) -> list[dict[str, Any]]:
    """Validate all iterations in a GCL trace."""
    results = []
    skill = trace.get("skill", "")
    for i, it in enumerate(trace.get("iterations", [])):
        cmd = it.get("generator", {}).get("command", "")
        if not cmd or not cmd.startswith("tccli"):
            continue
        raw = it.get("generator", {}).get("result_excerpt", "")
        if not raw:
            continue
        try:
            resp = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue
        violations = validate_response_schema(cmd, resp, skill)
        if violations:
            results.append({
                "iter": i + 1,
                "skill": skill,
                "command": cmd[:80],
                "violations": violations,
            })
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="Schema validator — layer 2 of 3")
    ap.add_argument("--trace-dir", default="audit-results", type=Path)
    ap.add_argument("--command", default=None, help="tccli command")
    ap.add_argument("--response", default=None, help="JSON response string")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.command and args.response:
        resp = json.loads(args.response)
        violations = validate_response_schema(args.command, resp)
        if violations:
            print(json.dumps(violations, indent=2))
            return 1
        print("SCHEMA: OK")
        return 0

    traces = [
        json.loads(f.read_text())
        for f in sorted(args.trace_dir.glob("gcl-trace-*.json"))
        if f.stat().st_size > 0
    ]
    total = 0
    for trace in traces:
        results = validate_trace(trace)
        for r in results:
            for v in r["violations"]:
                total += 1
                print(
                    f"[{r['skill']}] iter={r['iter']} "
                    f"type={v['type']} path={v['path']} sev={v['severity']} "
                    f"sug={v['suggestion'][:60]}",
                    file=sys.stderr,
                )
    if args.dry_run:
        print(f"[dry-run] {total} violations", file=sys.stderr)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
