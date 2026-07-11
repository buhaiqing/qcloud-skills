#!/usr/bin/env python3
"""Phase 2: selective deep inspection via 11 analyzers (tccli-backed)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_REASON_DIR = Path(__file__).resolve().parent
for path in (_SCRIPTS_DIR, _REASON_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from lib.env_loader import ensure_runtime_env  # noqa: E402
from lib.tccli_client import TccliClient  # noqa: E402
from analyzers import create_by_names  # noqa: E402
from analyzers.selective import resolve_analyzer_names  # noqa: E402

ensure_runtime_env()


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "qcloud-copilot").is_dir() and (parent / "AGENTS.md").is_file():
            return parent
    return Path.cwd()


def _resource_id(item: dict) -> str | None:
    for key in (
        "instanceId",
        "cacheInstanceId",
        "dbInstanceId",
        "loadBalancerId",
        "elasticIpId",
        "id",
        "resourceId",
    ):
        value = item.get(key)
        if value:
            return str(value)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 2: selective cruise analysis")
    parser.add_argument("--customer", required=True)
    parser.add_argument("--sniff-file", default=None)
    parser.add_argument("--hours", type=int, default=6)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--resource-ids", nargs="*", default=None)
    parser.add_argument("--analyzers", default=None, help="CSV analyzer names")
    parser.add_argument("--strategy-file", default=None)
    args = parser.parse_args()

    region = os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou")
    client = TccliClient(region=region)
    output_dir = args.output_dir or str(_repo_root() / ".runtime" / "proactive-inspection")

    if args.sniff_file:
        topology_data = json.loads(Path(args.sniff_file).read_text(encoding="utf-8"))
    else:
        sniff_script = _SCRIPTS_DIR.parent / "01-perceive" / "cruise_sniff.py"
        import subprocess

        proc = subprocess.run(
            [sys.executable, str(sniff_script), "--customer", args.customer, "--output-dir", output_dir],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout)
            return 1
        sniff_files = sorted(
            Path(output_dir).glob(f"sniff-{args.customer}-*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not sniff_files:
            print("sniff output not found")
            return 1
        topology_data = json.loads(sniff_files[0].read_text(encoding="utf-8"))

    strategy = None
    if args.strategy_file:
        strategy = json.loads(Path(args.strategy_file).read_text(encoding="utf-8"))

    explicit = None
    if args.analyzers:
        explicit = [s.strip() for s in args.analyzers.split(",") if s.strip()]

    analyzer_names, skipped, selection_mode = resolve_analyzer_names(
        topology_data,
        explicit=explicit,
        strategy=strategy,
    )
    print(
        f"\n[检索] 选择性巡检 ({args.hours}h) mode={selection_mode} "
        f"analyzers={','.join(analyzer_names) or '(none)'}"
    )
    for item in skipped:
        print(f"  [策略跳过] {item['service']}: {item['reason']}")

    analyzers = create_by_names(analyzer_names)
    all_reports: list[dict] = []
    executed: list[str] = []

    for analyzer in analyzers:
        svc = analyzer.service_name
        try:
            resources = analyzer.discover(topology_data)
            if args.resource_ids:
                id_set = set(args.resource_ids)
                resources = [r for r in resources if _resource_id(r) in id_set]
                analyzer.resources = resources
            if not resources:
                print(f"  [跳过] {svc}: 无相关资源")
                continue

            executed.append(svc)
            print(f"  [分析] {svc}: {len(resources)} 个资源，采集监控...")
            analyzer.query_metrics(client, hours=args.hours)
            findings = analyzer.analyze()
            report = analyzer.report()
            all_reports.append(report)

            for finding in findings:
                icon = {"critical": "[严重]", "warning": "[警告]", "info": "[信息]"}.get(
                    finding.get("severity", ""), "[待确认]"
                )
                print(
                    f"    {icon} [{finding.get('severity')}] "
                    f"{finding.get('resource')}: {finding.get('message')}"
                )
        except Exception as exc:
            print(f"  [禁止] {svc}: 分析失败 — {exc}")
            continue

    all_findings: list[dict] = []
    for report in all_reports:
        for finding in report.get("findings", []):
            finding = dict(finding)
            finding["service"] = report["service"]
            all_findings.append(finding)

    criticals = [f for f in all_findings if f.get("severity") == "critical"]
    warnings = [f for f in all_findings if f.get("severity") == "warning"]
    infos = [f for f in all_findings if f.get("severity") == "info"]

    print(f"\n[严重] Critical: {len(criticals)}  [警告] Warning: {len(warnings)}  [信息] Info: {len(infos)}")

    report_data = {
        "customer": args.customer,
        "timestamp": datetime.now().isoformat(),
        "hours": args.hours,
        "analyzer_selection": {
            "mode": selection_mode,
            "requested": analyzer_names,
            "executed": executed,
            "skipped": skipped,
        },
        "summary": {
            "total_findings": len(all_findings),
            "critical": len(criticals),
            "warning": len(warnings),
            "info": len(infos),
        },
        "service_reports": all_reports,
        "all_findings": all_findings,
    }

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = out_dir / f"cruise-{args.customer}-{ts}.json"
    report_path.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[已保存] 巡检分析结果: {report_path}")
    if args.json:
        print(json.dumps(report_data["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
