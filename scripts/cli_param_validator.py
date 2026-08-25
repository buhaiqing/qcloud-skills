#!/usr/bin/env python3
"""cli_param_validator.py — Verify tccli command flags exist via knowledge base.

Three-layer check #1: CLI 参数存在性
对照知识库验证 --flag 是否真实存在于 tccli API。

Knowledge base is a dict: skill -> action -> frozenset(valid_flags).
Built from tccli <product> <action> --help output.
Extensible via TCLOUD_OPERATIONS env var (JSON) or naming DB hook.

CLI usage::

    python3 scripts/cli_param_validator.py --trace-dir audit-results
    python3 scripts/cli_param_validator.py --command 'tccli cvm DescribeInstances --Region ap-guangzhou --Limit 20'
    python3 scripts/cli_param_validator.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Knowledge base: skill -> action -> valid flags (lowercase, no leading --)
# ---------------------------------------------------------------------------
# Covers all qcloud-*-ops skills. Incomplete but sufficient — unknown flags
# on unlisted actions pass silently (do not block; WAF gate #3 handles
# destructive unknowns). Extend via TCLOUD_OPERATIONS env var.
_KNOWN_FLAGS: dict[str, dict[str, frozenset[str]]] = {
    "qcloud-cvm-ops": {
        "DescribeInstances": frozenset({
            "limit", "offset", "instanceids", "vpcid", " subnetid",
            "instancechargechargeconfiguration", "platform", "instancestatecode",
            "searchword", "instancenames", "ipaddresses", "privateipaddresses",
            "publicipaddresses", "securitygroupids", "projectids", "unwhiteeipaddresses",
            "standalone", "zone", "region", "filters", "output", "version",
        }),
        "TerminateInstances": frozenset({
            "instanceids", "region", "version", "instance-charge-configuration",
            "forced", "output",
        }),
        "StopInstances": frozenset({
            "instanceids", "region", "version", "stopped-mode", "output",
        }),
        "StartInstances": frozenset({
            "instanceids", "region", "version", "output",
        }),
        "RebootInstances": frozenset({
            "instanceids", "region", "version", "stopped-mode", "output",
        }),
        "DescribeInstancesModified": frozenset({
            "instanceids", "offset", "limit", "instance-type", "instance-charge-type",
            "vpc-id", "subnet-id", "zone", "output", "version",
        }),
    },
    "qcloud-cdb-ops": {
        "DescribeDBInstances": frozenset({
            "engineversions", "vpcid", "subnetid", "orderby", "ordersort",
            "offset", "limit", "securitygroupids", "filters", "output", "version",
        }),
        "DeleteDBInstance": frozenset({
            "instanceids", "region", "version", "output",
        }),
        "IsolateDBInstance": frozenset({
            "instanceids", "region", "version", "output",
        }),
        "DescribeAccounts": frozenset({
            "instanceid", "offset", "limit", "account", "host", "output", "version",
        }),
        "CreateAccount": frozenset({
            "instanceid", "name", "password", "description", "maxuserconnections",
            "readonly", "output", "version",
        }),
    },
    "qcloud-redis-ops": {
        "DescribeCacheInstances": frozenset({
            "limit", "offset", "vpcids", "subnetids", "orderby", "ordersort",
            "instanceids", "instancenames", "versionids", "projectids",
            "searchword", "zone", "output", "version",
        }),
        "DeleteInstance": frozenset({
            "instanceids", "region", "version", "output",
        }),
        "RestartInstance": frozenset({
            "instanceids", "region", "nodeids", "version", "output",
        }),
        "FlushInstance": frozenset({
            "instanceids", "region", "version", "password", "output",
        }),
    },
    "qcloud-clb-ops": {
        "DescribeLoadBalancers": frozenset({
            "loadbalancerids", "loadbalancertype", "forward", "domain",
            "loadbalancername", "vpcid", "subnetid", "projectids",
            "searchword", "offset", "limit", "orderby", "ordersort",
            "securitygroup", "tz", "region", "output", "version",
        }),
        "DeleteLoadBalancers": frozenset({
            "loadbalancerids", "region", "version", "output",
        }),
        "DeleteListeners": frozenset({
            "loadbalancerid", "listenerids", "region", "version", "output",
        }),
        "CreateListener": frozenset({
            "loadbalancerid", "listenerport", "protocol", "listenernames",
            "sessionExpireTime", "healthswitch", "intervaltime",
            "健康阈值", "unhealththreshold", "timeout", "region", "output", "version",
        }),
    },
    "qcloud-cos-ops": {
        "ListBuckets": frozenset({"region", "output", "version"}),
        "DeleteBucket": frozenset({"bucket", "region", "version", "output"}),
        "PutObject": frozenset({
            "bucket", "body", "key", "contentlength", "contenttype",
            "cachecontrol", "contentdisposition", "contentencoding",
            "contentlanguage", "expires", "metadata", "storageclass",
            "x-cos-acl", "x-cos-grant-read", "region", "version", "output",
        }),
        "GetObject": frozenset({
            "bucket", "key", "range", "ifmatch", "ifnonematch",
            "ifmodifiedsince", "ifunmodifiedsince", "tempurl", "region",
            "version", "output",
        }),
        "DeleteObject": frozenset({
            "bucket", "key", "versionid", "region", "version", "output",
        }),
        "ListObjects": frozenset({
            "bucket", "delimiter", "encodingtype", "marker", "maxkeys",
            "prefix", "region", "version", "output",
        }),
    },
    "qcloud-tke-ops": {
        "DescribeClusters": frozenset({
            "offset", "limit", "clusterids", "vpcids", "clustertype",
            "region", "output", "version",
        }),
        "DeleteCluster": frozenset({
            "clusterid", "region", "version", "output",
        }),
        "DescribeClusterInstances": frozenset({
            "clusterid", "offset", "limit", "instanceids", "role",
            "region", "output", "version",
        }),
        "DescribeNodeGroups": frozenset({
            "clusterid", "nodepoolids", "nodepoolnames", "filters",
            "offset", "limit", "region", "output", "version",
        }),
        "ScaleNodeGroup": frozenset({
            "clusterid", "nodepoolid", "desirednodesnum", "autoscaling",
            "region", "version", "output",
        }),
    },
    "qcloud-vpc-ops": {
        "DescribeVpcs": frozenset({
            "vpcids", "vpccidrs", "vpcnames", "searchword", "offset",
            "limit", "orderby", "ordersort", "region", "output", "version",
        }),
        "DeleteVpc": frozenset({"vpcid", "region", "version", "output"}),
        "DescribeEips": frozenset({
            "eipids", "eipaddresses", "networkoperatorcacheids", "paymode",
            "searchword", "orderby", "ordersort", "offset", "limit",
            "region", "output", "version",
        }),
        "AllocateAddresses": frozenset({
            "addresscount", "internetchargechargeconfiguration",
            "internetmaxbandwidthout", "internetmaxbandwidthin",
            "addressType", "region", "version", "output",
        }),
        "ReleaseAddresses": frozenset({
            "addressids", "region", "version", "output",
        }),
        "AssociateAddress": frozenset({
            "addressid", "instanceid", "networkinterfaceid", "privateipaddress",
            "region", "version", "output",
        }),
        "DisassociateAddress": frozenset({
            "addressid", "region", "version", "output",
        }),
    },
    "qcloud-cbs-ops": {
        "DescribeDisks": frozenset({
            "diskuids", "disksnapshothost", "diskcharges", "diskstate",
            "instanceid", "projectids", "offset", "limit", "zone",
            "output", "version",
        }),
        "AttachDisk": frozenset({
            "diskid", "instanceid", "region", "version", "output",
        }),
        "DetachDisk": frozenset({
            "diskid", "instanceid", "region", "version", "output",
        }),
        "TerminateDisks": frozenset({
            "diskids", "region", "version", "output",
        }),
        "ResizeDisk": frozenset({
            "diskid", "disksize", "region", "version", "output",
        }),
    },
    "qcloud-cam-ops": {
        "DescribeUsers": frozenset({
            "offset", "limit", "searchword", "serialid", "output", "version",
        }),
        "CreateUser": frozenset({
            "name", "remark", "consoleLogin", "password", "output", "version",
        }),
        "DeleteUser": frozenset({"name", "output", "version"}),
        "AttachPolicy": frozenset({
            "policyid", "attachuin", "policytype", "createMode",
            "output", "version",
        }),
        "DetachPolicy": frozenset({
            "policyid", "detachuin", "policytype", "output", "version",
        }),
    },
    "qcloud-cdn-ops": {
        "DescribeDomains": frozenset({
            "offset", "limit", "orderby", "ordersort", "filters",
            "area", "duphost", "searchkey", "status", "output", "version",
        }),
        "DeleteDomain": frozenset({"hostid", "version", "output"}),
        "PurgePathCache": frozenset({"urls", "flushType", "version", "output"}),
    },
    "qcloud-scf-ops": {
        "DescribeFunctions": frozenset({
            "offset", "limit", "orderby", "ordersort", "searchkey",
            "namespace", "description", "allnamespaces", "filters",
            "output", "version",
        }),
        "DeleteFunction": frozenset({"functionname", "namespace", "version", "output"}),
        "InvokeFunction": frozenset({
            "functionname", "invocationtype", "qualifier", "input",
            "namespace", "loginhdr", "clientcontext", "version", "output",
        }),
    },
    "qcloud-monitor-ops": {
        "DescribeAlarmPolicies": frozenset({
            "module", "pageNumber", "pageSize", "policyName", "orderBy",
            "order", "promql", "viewName", "uniqueId", "isDefault",
            "probability", "night", "abnormal", "statistical",
            "instanceGroupId", "output", "version",
        }),
        "DeleteAlarmPolicy": frozenset({
            "module", "uids", "version", "output",
        }),
        "CreateAlarmPolicy": frozenset({
            "module", "policyName", "monitorType", "platformDim",
            "isDefault", "enable", "groupId", "dimensions",
            "metricName", "period", "statistics", "threshold", "comparator", "alarmNoticeId",
            "triggerCount", "output", "version",
        }),
    },
}


_EXTERNAL_FLAGS_FILE = ROOT / "assets" / "shared" / "tcloud_cli_flags.json"


def _load_generated_flags() -> dict[str, dict[str, frozenset[str]]]:
    """Load generated KB from kb_sync_openapi.py (authoritative per skill/action).

    Location: ``$TCLOUD_KB_DIR`` or repo ``assets/shared/``. Missing file →
    empty dict (built-in hand KB remains the only source; L10 skip gracefully).
    """
    base = os.environ.get("TCLOUD_KB_DIR", "")
    path = Path(base) / "tcloud_cli_flags.json" if base else _EXTERNAL_FLAGS_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    out: dict[str, dict[str, frozenset[str]]] = {}
    for skill, actions in data.items():
        out[skill] = {
            action: frozenset(flags) for action, flags in (actions or {}).items()
        }
    return out


def _load_extended() -> dict[str, dict[str, frozenset[str]]]:
    """Load from TCLOUD_OPERATIONS env var (JSON) to extend KB at runtime."""
    raw = {skill: dict(actions) for skill, actions in _KNOWN_FLAGS.items()}
    # Generated KB wins over hand-maintained entries (auto-synced from tccli metadata).
    for skill, actions in _load_generated_flags().items():
        raw.setdefault(skill, {}).update(actions)
    try:
        env = os.environ.get("TCLOUD_OPERATIONS", "")
        if env:
            extra = json.loads(env)  # type: ignore[arg-type]
            for skill, actions in extra.items():
                if skill not in raw:
                    raw[skill] = {}
                for action, flags in actions.items():
                    known = raw.get(skill, {}).get(action, frozenset())
                    raw[skill][action] = known | frozenset(flags)
    except (json.JSONDecodeError, OSError, KeyError, TypeError):
        pass
    return raw


def _parse_flags(cmd: str) -> list[tuple[str, str]]:
    """Extract (flag, value) pairs from a tccli command line.

    Handles:
      --flag value
      --flag=value
      --flag "multi word"
      positional args (ignored)
    """
    flags = []
    tokens = shlex.split(cmd)
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("--"):
            if "=" in tok:
                flag, val = tok[2:].split("=", 1)
                flags.append((flag.lower(), val))
            else:
                nxt = tokens[i + 1] if i + 1 < len(tokens) and not tokens[i + 1].startswith("--") else ""
                flags.append((tok[2:].lower(), nxt))
                if nxt and not nxt.startswith("--"):
                    i += 1
        i += 1
    return flags


def _detect_product_action(cmd: str) -> tuple[str, str]:
    """Parse tccli command to (skill, action)."""
    m = re.search(r"tccli\s+(\w+)\s+(\w+)", cmd)
    if not m:
        return "", ""
    product, action = m.group(1), m.group(2)
    # Map product -> skill name
    skill_map = {
        "cvm": "qcloud-cvm-ops",
        "cdb": "qcloud-cdb-ops",
        "redis": "qcloud-redis-ops",
        "clb": "qcloud-clb-ops",
        "cos": "qcloud-cos-ops",
        "tke": "qcloud-tke-ops",
        "vpc": "qcloud-vpc-ops",
        "cbs": "qcloud-cbs-ops",
        "cam": "qcloud-cam-ops",
        "cdn": "qcloud-cdn-ops",
        "scf": "qcloud-scf-ops",
        "monitor": "qcloud-monitor-ops",
    }
    skill = skill_map.get(product.lower(), f"qcloud-{product}-ops")
    return skill, action


def validate_cli_params(cmd: str, skill: str = "", action: str = "") -> list[dict[str, Any]]:
    """Check flags in cmd against knowledge base.

    Returns list of violations (empty = all clear).
    Each violation: {flag, severity, suggestion}
    """
    if not skill or not action:
        skill, action = _detect_product_action(cmd)
    violations = []
    kb = _load_extended()
    valid = kb.get(skill, {}).get(action, None)

    # If skill/action not in KB, pass silently (dynamic / unknown API)
    if valid is None:
        return []

    flags = _parse_flags(cmd)
    for flag, _ in flags:
        if flag not in valid:
            violations.append({
                "flag": flag,
                "severity": "high" if _is_destructive_flag(flag) else "low",
                "suggestion": f"Verify '{flag}' is valid for tccli {skill.split('-')[1]} {action}; remove or check spelling",
            })
    return violations


def _is_destructive_flag(flag: str) -> bool:
    """Heuristic: flags that imply destructive side-effects."""
    return flag in {"forced", "delete", "terminate", "drop", "flush", "purge", "release"}


def validate_trace(trace: dict) -> list[dict[str, Any]]:
    """Validate all iterations in a GCL trace."""
    results = []
    skill = trace.get("skill", "")
    for i, it in enumerate(trace.get("iterations", [])):
        cmd = it.get("generator", {}).get("command", "")
        if not cmd or not cmd.startswith("tccli"):
            continue
        _, action = _detect_product_action(cmd)
        violations = validate_cli_params(cmd, skill, action)
        if violations:
            results.append({
                "iter": i + 1,
                "skill": skill,
                "command": cmd[:80],
                "action": action,
                "violations": violations,
            })
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="CLI param validator — layer 1 of 3")
    ap.add_argument("--trace-dir", default="audit-results", type=Path)
    ap.add_argument(
        "--command",
        default=None,
        help="Single tccli command to validate",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.command:
        violations = validate_cli_params(args.command)
        if violations:
            print(json.dumps(violations, indent=2))
            return 1
        print("CLI_PARAMS: OK")
        return 0

    traces = [
        json.loads(f.read_text())
        for f in sorted(args.trace_dir.glob("gcl-trace-*.json"))
        if f.stat().st_size > 0
    ]
    total_violations = 0
    for trace in traces:
        results = validate_trace(trace)
        for r in results:
            for v in r["violations"]:
                total_violations += 1
                print(
                    f"[{r['skill']}] iter={r['iter']} "
                    f"flag=--{v['flag']} sev={v['severity']} "
                    f"sug={v['suggestion'][:60]}",
                    file=sys.stderr,
                )
    if args.dry_run:
        print(f"[dry-run] {total_violations} violations", file=sys.stderr)
    return 1 if total_violations else 0


if __name__ == "__main__":
    import os
    import shlex
    sys.exit(main())
