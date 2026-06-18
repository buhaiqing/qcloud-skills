#!/usr/bin/env python3
"""GCL Phase 4 — Wire rubric pass-rate to Cloud Monitor alarms (AGENTS.md §10.10).

Consumes the latest ``audit-results/gcl-quality-summary-*.json`` (emitted by
``scripts/gcl_trace_aggregate.py``) and ensures Cloud Monitor alarm policies
exist for the GCL quality SLOs. Used as the runtime gate that closes the loop
between runtime trace quality and ops alerting.

Defaults match ``qcloud-monitor-ops/assets/example-config.yaml`` → ``gcl_quality``:
- ``pass_rate_warn`` (default 0.85)
- ``pass_rate_critical`` (default 0.70)
- ``max_iter_warn_count`` (default 3)
- ``safety_fail_alert`` (default True — any ``SAFETY_FAIL`` triggers critical alarm)

Usage:
  # Preview without mutating cloud (CI / first-time setup)
  python3 scripts/gcl_alarm_wire.py plan --summary audit-results/gcl-quality-summary-LATEST.json

  # Apply (create / update alarm policies via tccli)
  python3 scripts/gcl_alarm_wire.py apply \\
    --config qcloud-monitor-ops/assets/example-config.yaml \\
    --summary audit-results/gcl-quality-summary-LATEST.json

Exit codes:
  0 — no breach / plan OK / policies ensured
  1 — quality SLO breached (caller may want to page on this)
  2 — invalid input (missing summary / config)
  3 — tccli invocation failed (network / auth / perms)

Execution path: PRIMARY tccli monitor CreateAlarmPolicy / CreateAlarmNotice /
DescribeAlarmPolicies. SDK fallback documented in qcloud-monitor-ops
references/api-sdk-usage.md (not exercised here).
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_THRESHOLDS = {
    "pass_rate_warn": 0.85,
    "pass_rate_critical": 0.70,
    "max_iter_warn_count": 3,
    "safety_fail_alert": True,
}

# Default alarm-policy name and metric namespace for custom GCL metrics.
# Custom metric namespace `qce/gcl_custom` — chosen because it is not a Tencent
# Cloud first-party namespace; the operator registers it via Cloud Monitor
# console once, after which PutMonitorData writes into it.
GCL_NAMESPACE = "qce/gcl_custom"
GCL_PASS_RATE_METRIC = "GCLPassRate"
GCL_SAFETY_FAIL_METRIC = "GCLSafetyFailCount"

# Standard tccli flags we always pass.
_REGION_FLAGS = ("--region", "ap-guangzhou")


def load_latest_summary(audit_dir: Path) -> Path | None:
    """Return the most recent gcl-quality-summary-*.json under audit_dir, or None."""
    paths = sorted(audit_dir.glob("gcl-quality-summary-*.json"))
    return paths[-1] if paths else None


def parse_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_thresholds_from_config(config_path: Path) -> dict[str, Any]:
    """Tiny YAML-ish extractor — avoids pulling in PyYAML for a 4-key block.

    Reads the ``gcl_quality:`` block line-by-line and pulls ``key: value``
    pairs that look numeric or boolean. Lines starting with ``#`` are ignored.
    Unknown keys fall back to DEFAULT_THRESHOLDS so config evolution is
    backwards-compatible.
    """
    out: dict[str, Any] = dict(DEFAULT_THRESHOLDS)
    if not config_path.exists():
        return out
    in_block = False
    for line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("gcl_quality:"):
            in_block = True
            continue
        if in_block:
            if not line.startswith(" ") and ":" in stripped:
                # left the block
                break
            if ":" not in stripped:
                continue
            key, _, raw = stripped.partition(":")
            key = key.strip()
            raw = raw.strip().split("#")[0].strip()
            if key not in DEFAULT_THRESHOLDS:
                continue
            if raw.lower() in ("true", "false"):
                out[key] = raw.lower() == "true"
            else:
                try:
                    out[key] = float(raw)
                except ValueError:
                    pass
    return out


def evaluate(summary: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
    """Compare summary against thresholds. Returns breach report + per-policy plan."""
    totals = summary.get("totals", {}) or {}
    pass_rate = float(summary.get("pass_rate", 0.0))
    safety_fail = int(totals.get("SAFETY_FAIL", 0))
    max_iter = int(totals.get("MAX_ITER", 0))

    breaches: list[dict[str, str]] = []
    if pass_rate < float(thresholds["pass_rate_critical"]):
        breaches.append({
            "severity": "CRITICAL",
            "metric": "pass_rate",
            "value": str(pass_rate),
            "threshold": f"< {thresholds['pass_rate_critical']}",
            "message": f"GCL pass_rate {pass_rate} below critical {thresholds['pass_rate_critical']}",
        })
    elif pass_rate < float(thresholds["pass_rate_warn"]):
        breaches.append({
            "severity": "WARN",
            "metric": "pass_rate",
            "value": str(pass_rate),
            "threshold": f"< {thresholds['pass_rate_warn']}",
            "message": f"GCL pass_rate {pass_rate} below warn {thresholds['pass_rate_warn']}",
        })

    if bool(thresholds["safety_fail_alert"]) and safety_fail > 0:
        breaches.append({
            "severity": "CRITICAL",
            "metric": "safety_fail_count",
            "value": str(safety_fail),
            "threshold": "== 0",
            "message": f"GCL observed {safety_fail} SAFETY_FAIL trace(s)",
        })

    if max_iter > int(thresholds["max_iter_warn_count"]):
        breaches.append({
            "severity": "WARN",
            "metric": "max_iter_count",
            "value": str(max_iter),
            "threshold": f"<= {thresholds['max_iter_warn_count']}",
            "message": f"GCL hit MAX_ITER {max_iter} time(s)",
        })

    return {
        "pass_rate": pass_rate,
        "safety_fail": safety_fail,
        "max_iter": max_iter,
        "breaches": breaches,
        "ok": not any(b["severity"] == "CRITICAL" for b in breaches),
    }


def render_plan(evaluation: dict[str, Any]) -> list[dict[str, Any]]:
    """Translate evaluation into alarm-policy operations (idempotent)."""
    plan: list[dict[str, Any]] = []

    # CRITICAL: pass_rate drop
    plan.append({
        "op": "CreateAlarmPolicy",
        "name": "gcl-quality-pass-rate-critical",
        "namespace": GCL_NAMESPACE,
        "metric_name": GCL_PASS_RATE_METRIC,
        "calc_type": "Less",
        "calc_value": str(evaluation.get("_pass_rate_critical", 0.70)),
        "continue_time": 300,
        "severity": "CRITICAL",
        "description": "Fires when GCL pass_rate < critical threshold (default 0.70).",
    })
    # WARN: pass_rate drop
    plan.append({
        "op": "CreateAlarmPolicy",
        "name": "gcl-quality-pass-rate-warn",
        "namespace": GCL_NAMESPACE,
        "metric_name": GCL_PASS_RATE_METRIC,
        "calc_type": "Less",
        "calc_value": str(evaluation.get("_pass_rate_warn", 0.85)),
        "continue_time": 600,
        "severity": "WARN",
        "description": "Fires when GCL pass_rate < warn threshold (default 0.85).",
    })
    # CRITICAL: any SAFETY_FAIL
    plan.append({
        "op": "CreateAlarmPolicy",
        "name": "gcl-safety-fail-critical",
        "namespace": GCL_NAMESPACE,
        "metric_name": GCL_SAFETY_FAIL_METRIC,
        "calc_type": "Greater",
        "calc_value": "0",
        "continue_time": 60,
        "severity": "CRITICAL",
        "description": "Fires on ANY GCL SAFETY_FAIL (rubric safety dimension = 0).",
    })
    return plan


def cmd_plan(args: argparse.Namespace) -> int:
    summary_path = args.summary
    if not summary_path:
        summary_path = load_latest_summary(args.root / "audit-results")
        if not summary_path:
            print("ERROR: No gcl-quality-summary-*.json found under audit-results/", file=sys.stderr)
            return 2

    summary = parse_summary(summary_path)
    thresholds = load_thresholds_from_config(args.config)
    evaluation = evaluate(summary, thresholds)
    evaluation["_pass_rate_warn"] = thresholds["pass_rate_warn"]
    evaluation["_pass_rate_critical"] = thresholds["pass_rate_critical"]

    plan = render_plan(evaluation)
    report = {
        "summary_path": str(summary_path),
        "thresholds": thresholds,
        "evaluation": {k: v for k, v in evaluation.items() if not k.startswith("_")},
        "alarm_plan": plan,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if not evaluation["ok"]:
        print(f"\n⚠️  SLO breach detected — {len(evaluation['breaches'])} item(s).", file=sys.stderr)
        return 1
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    """Render plan, then invoke tccli monitor CreateAlarmPolicy for each entry."""
    # First, run the plan logic by re-using cmd_plan's evaluation
    summary_path = args.summary
    if not summary_path:
        summary_path = load_latest_summary(args.root / "audit-results")
        if not summary_path:
            print("ERROR: No gcl-quality-summary-*.json found.", file=sys.stderr)
            return 2

    summary = parse_summary(summary_path)
    thresholds = load_thresholds_from_config(args.config)
    evaluation = evaluate(summary, thresholds)
    evaluation["_pass_rate_warn"] = thresholds["pass_rate_warn"]
    evaluation["_pass_rate_critical"] = thresholds["pass_rate_critical"]
    plan = render_plan(evaluation)

    if args.dry_run:
        print(json.dumps({"dry_run": True, "plan": plan}, indent=2, ensure_ascii=False))
        return 0

    rc = 0
    for entry in plan:
        cmd = [
            "tccli", "monitor", "CreateAlarmPolicy",
            *_REGION_FLAGS,
            "--Module", "monitor",
            "--Name", entry["name"],
            "--Namespace", entry["namespace"],
            "--MonitorType", "MT_QCE",
            "--PolicyType", entry["severity"],
            "--Remark", entry["description"],
            "--Conditions", json.dumps([{
                "MetricName": entry["metric_name"],
                "CalcType": entry["calc_type"],
                "CalcValue": entry["calc_value"],
                "ContinueTime": entry["continue_time"],
            }]),
        ]
        print(f"[apply] {' '.join(shlex.quote(c) for c in cmd)}")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            print(f"[apply] TIMEOUT on {entry['name']}", file=sys.stderr)
            rc = 3
            continue
        if proc.returncode != 0:
            print(f"[apply] FAILED ({proc.returncode}): {proc.stderr or proc.stdout}", file=sys.stderr)
            rc = 3
            continue
        print(f"[apply] OK: {entry['name']}")
    return rc


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    sub = p.add_subparsers(dest="cmd", required=True)

    plan_p = sub.add_parser("plan", help="Evaluate summary, render alarm plan (no mutations)")
    plan_p.add_argument("--config", type=Path, default=Path("qcloud-monitor-ops/assets/example-config.yaml"))
    plan_p.add_argument("--summary", type=Path, default=None)
    plan_p.set_defaults(func=cmd_plan)

    apply_p = sub.add_parser("apply", help="Apply alarm plan via tccli")
    apply_p.add_argument("--config", type=Path, default=Path("qcloud-monitor-ops/assets/example-config.yaml"))
    apply_p.add_argument("--summary", type=Path, default=None)
    apply_p.add_argument("--dry-run", action="store_true", help="Print plan without invoking tccli")
    apply_p.set_defaults(func=cmd_apply)

    return p


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())