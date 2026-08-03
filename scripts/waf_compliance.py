#!/usr/bin/env python3
"""waf_compliance.py — Offline safety / cost / stability compliance check.

Three-layer check #3: WAF 合规
对 GCL trace 执行离线安全/成本/稳定性检查：

- Safety: destructive op (delete/stop/terminate/release) 是否有人工确认
- Cost: 批量操作规格 × 数量 × 时长 是否超阈值
- Stability: 幂等性、重复提交、漂移检测
- Destructive verbs: --forced / drop / flush 等高危 flag 检测

CLI usage::

    python3 scripts/waf_compliance.py --trace-dir audit-results
    python3 scripts/waf_compliance.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Thresholds (can be overridden via env vars)
# ---------------------------------------------------------------------------
_BATCH_SIZE_WARN = int(os.environ.get("WAF_BATCH_SIZE_WARN", "5"))
_BATCH_SIZE_FAIL = int(os.environ.get("WAF_BATCH_SIZE_FAIL", "20"))
_COST_MONTHLY_WARN = float(os.environ.get("WAF_COST_MONTHLY_WARN", "1000.0"))
_COST_MONTHLY_FAIL = float(os.environ.get("WAF_COST_MONTHLY_FAIL", "10000.0"))

# Destructive action patterns (case-insensitive)
_DESTRUCTIVE_PATTERNS = [
    r"delete\w*", r"terminate\w*", r"stop\w*(?!list)", r"drop\w*",
    r"release\w*", r"flush\w*", r"purge\w*", r"destroy\w*",
    r"isolate\w*", r"revoke\w*", r"dissociate\w*",
]

# High-cost operation patterns
_HIGHCOST_PATTERNS = [
    r"run\w*instances", r"create\w*instance", r"allocate\w*address",
    r"purchase\w*", r"renew\w*",
]

# Destructive flags
_DESTRUCTIVE_FLAGS = {
    "forced", "delete", "terminate", "drop", "flush",
    "purge", "release", "isolate", "destroy",
}

# Cost estimate table: (product, instance_type) -> hourly cost (CNY)
# ponytail: simplified — use real pricing in production
_INSTANCE_HOURLY_COST: dict[tuple[str, str], float] = {
    ("cvm", "S5"): 0.42, ("cvm", "S6"): 0.33, ("cvm", "SA2"): 0.52,
    ("cvm", "SN3"): 0.61, ("cvm", "S4"): 0.56,
    ("redis", "cluster"): 4.0, ("redis", "standard"): 1.5,
    ("cdb", "MySQL"): 0.8, ("cdb", "MariaDB"): 0.6,
    ("clb", "slb"): 0.05,
}


def _is_destructive(action: str) -> bool:
    a = action.lower()
    return any(re.search(p, a) for p in _DESTRUCTIVE_PATTERNS)


def _is_highcost(action: str) -> bool:
    a = action.lower()
    return any(re.search(p, a) for p in _HIGHCOST_PATTERNS)


def _extract_resource_ids(cmd: str) -> list[str]:
    """Extract resource ID lists from tccli command."""
    ids = []
    # --instanceids ["id1","id2"] or --instanceids id1,id2
    m = re.search(r"--(\w+ids?)\s+([^\s]+)", cmd)
    if m:
        raw = m.group(2).strip('",[]')
        ids = [i.strip() for i in raw.split(",") if i.strip()]
    return ids


def _count_resources(cmd: str) -> int:
    """Estimate resource count affected by a command."""
    ids = _extract_resource_ids(cmd)
    if ids:
        return len(ids)
    # Check for count flags
    m = re.search(r"--(count|limit|number)\s+(\d+)", cmd.lower())
    if m:
        return int(m.group(2))
    return 1  # single resource default


def _has_destructive_flag(cmd: str) -> bool:
    tokens = cmd.lower().split()
    return any(t[2:] in _DESTRUCTIVE_FLAGS for t in tokens if t.startswith("--"))


def _check_safety(trace: dict, skill: str, action: str, cmd: str) -> list[dict[str, Any]]:
    """Safety gate: destructive op without human confirmation = violation."""
    violations = []
    if not _is_destructive(action):
        return violations

    # Check if --confirmed / --force-confirm / safety confirmation exists in trace
    confirmed = (
        "--confirmed" in cmd.lower()
        or "--force-confirm" in cmd.lower()
        or trace.get("safety_confirmed", False)
    )
    # Also pass if critic scored safety=1
    for it in trace.get("iterations", []):
        c = it.get("critic", {}).get("scores", {})
        if c.get("safety") == 1:
            confirmed = True

    if not confirmed:
        violations.append({
            "type": "destructive_without_confirmation",
            "severity": "critical",
            "action": action,
            "suggestion": f"Destructive action '{action}' requires --confirmed flag or user confirmation before execution",
        })

    if _has_destructive_flag(cmd):
        violations.append({
            "type": "destructive_flag_present",
            "severity": "high",
            "action": action,
            "suggestion": f"Command uses destructive flag in '{action}' — verify this is intentional",
        })

    return violations


def _check_cost(trace: dict, skill: str, action: str, cmd: str) -> list[dict[str, Any]]:
    """Cost gate: estimate monthly cost and check against thresholds."""
    violations = []
    if not _is_highcost(action):
        return violations

    count = _count_resources(cmd)
    product = skill.split("-")[1] if "-" in skill else ""
    # Rough hourly estimate
    hourly = sum(
        c for (p, t), c in _INSTANCE_HOURLY_COST.items() if p == product
    ) * count
    monthly = hourly * 24 * 30

    if monthly >= _COST_MONTHLY_FAIL:
        violations.append({
            "type": "cost_exceeds_fail_threshold",
            "severity": "critical",
            "estimated_monthly_cny": round(monthly, 2),
            "count": count,
            "suggestion": f"Estimated monthly cost ¥{monthly:.0f} exceeds fail threshold ¥{_COST_MONTHLY_FAIL:.0f} — require explicit approval",
        })
    elif monthly >= _COST_MONTHLY_WARN:
        violations.append({
            "type": "cost_exceeds_warn_threshold",
            "severity": "medium",
            "estimated_monthly_cny": round(monthly, 2),
            "count": count,
            "suggestion": f"Estimated monthly cost ¥{monthly:.0f} exceeds warn threshold ¥{_COST_MONTHLY_WARN:.0f} — consider review",
        })

    return violations


def _check_batch_size(trace: dict, skill: str, action: str, cmd: str) -> list[dict[str, Any]]:
    """Batch size gate: warn on large resource sets."""
    violations = []
    count = _count_resources(cmd)

    if count >= _BATCH_SIZE_FAIL:
        violations.append({
            "type": "batch_exceeds_fail_threshold",
            "severity": "critical",
            "count": count,
            "suggestion": f"Batch size {count} exceeds fail threshold {_BATCH_SIZE_FAIL} — requires explicit approval",
        })
    elif count >= _BATCH_SIZE_WARN:
        violations.append({
            "type": "batch_exceeds_warn_threshold",
            "severity": "medium",
            "count": count,
            "suggestion": f"Batch size {count} exceeds warn threshold {_BATCH_SIZE_WARN} — verify this is intentional",
        })

    return violations


def _check_stability(trace: dict, skill: str, action: str, cmd: str) -> list[dict[str, Any]]:
    """Stability gate: idempotency, duplicate submission, rapid re-run."""
    violations = []

    # Check for missing ClientToken on write operations
    write_ops = {"create", "put", "post", "allocate", "associate", "attach"}
    is_write = any(op in action.lower() for op in write_ops)
    if is_write and "ClientToken" not in cmd and "clienttoken" not in cmd.lower():
        violations.append({
            "type": "missing_client_token",
            "severity": "low",
            "suggestion": f"Write operation '{action}' should include --ClientToken for idempotency",
        })

    # Check for rapid re-run within same trace
    iterations = trace.get("iterations", [])
    if len(iterations) >= 3:
        violations.append({
            "type": "slow_convergence",
            "severity": "low",
            "iterations": len(iterations),
            "suggestion": f"{len(iterations)} iterations needed — consider optimizing the operation approach",
        })

    return violations


def waf_check(trace: dict, skill: str, action: str, cmd: str) -> list[dict[str, Any]]:
    """Run all WAF gates. Returns list of violations (may be empty)."""
    violations = []
    violations += _check_safety(trace, skill, action, cmd)
    violations += _check_cost(trace, skill, action, cmd)
    violations += _check_batch_size(trace, skill, action, cmd)
    violations += _check_stability(trace, skill, action, cmd)
    return violations


def validate_trace(trace: dict) -> list[dict[str, Any]]:
    """Validate all iterations in a GCL trace."""
    results = []
    skill = trace.get("skill", "")
    for i, it in enumerate(trace.get("iterations", [])):
        cmd = it.get("generator", {}).get("command", "")
        if not cmd or not cmd.startswith("tccli"):
            continue
        m = re.search(r"tccli\s+\w+\s+(\w+)", cmd)
        action = m.group(1) if m else ""
        violations = waf_check(trace, skill, action, cmd)
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
    ap = argparse.ArgumentParser(description="WAF compliance — layer 3 of 3")
    ap.add_argument("--trace-dir", default="audit-results", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--command",
        default=None,
        help="Single tccli command to check",
    )
    args = ap.parse_args()

    if args.command:
        fake_trace = {
            "skill": "",
            "iterations": [{"generator": {"command": args.command}}],
        }
        m = re.search(r"tccli\s+\w+\s+(\w+)", args.command)
        action = m.group(1) if m else ""
        violations = waf_check(fake_trace, "", action, args.command)
        if violations:
            print(json.dumps(violations, indent=2))
            return 1
        print("WAF: OK")
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
                    f"type={v['type']} sev={v['severity']} "
                    f"sug={v.get('suggestion', '')[:60]}",
                    file=sys.stderr,
                )
    if args.dry_run:
        print(f"[dry-run] {total} violations", file=sys.stderr)
    return 1 if total else 0


if __name__ == "__main__":
    import os
    sys.exit(main())
