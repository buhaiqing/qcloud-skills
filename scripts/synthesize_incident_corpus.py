#!/usr/bin/env python3
"""Synthesize cold-start incident corpus from eval_queries.json.

Reads qcloud-*-ops/assets/eval_queries.json (should_trigger=true entries)
and emits scripts/fixtures/incidents/corpus.jsonl with read-only tccli commands.
Deterministic, no cloud calls.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# Skill -> product -> read-only tccli template (Action must be Describe/List/Get/Inquiry)
_PRODUCT_DESCRIBE: dict[str, str] = {
    "cvm": "DescribeInstances",
    "cdb": "DescribeDBInstances",
    "vpc": "DescribeVpcs",
    "clb": "DescribeLoadBalancers",
    "cos": "ListBuckets",
    "cbs": "DescribeDisks",
    "ckafka": "DescribeInstances",
    "cls": "DescribeLogsets",
    "monitor": "DescribeAlarmPolicies",
    "tke": "DescribeClusters",
    "cam": "ListUsers",
    "cdn": "DescribeDomains",
    "redis": "DescribeInstances",
    "es": "DescribeInstances",
    "scf": "ListFunctions",
    "mongodb": "DescribeDBInstances",
    "postgres": "DescribeDBInstances",
    "ssl": "DescribeCertificates",
    "ccn": "DescribeCcns",
    "vpn": "DescribeVpnGateways",
    "dc": "DescribeDirectConnects",
    "apigw": "DescribeServices",
    "tdmq": "DescribeClusters",
    "tcm": "DescribeMesh",
    "agsx": "DescribeInstances",
    "tcop": "DescribeInstances",
    "finops": "DescribeBillSummary",
    "migration": "DescribeMigrationProjects",
    "cicd": "DescribePipelines",
    "service-mesh": "DescribeMesh",
}

_SEVERITIES = ["info", "warning", "critical"]


def _product_from_skill(skill: str) -> str:
    # qcloud-cvm-ops -> cvm, qcloud-service-mesh-ops -> service-mesh
    m = re.match(r"qcloud-(.+)-ops$", skill)
    return m.group(1) if m else skill


def _command_for_skill(skill: str) -> str:
    prod = _product_from_skill(skill)
    action = _PRODUCT_DESCRIBE.get(prod, "DescribeInstances")
    # All commands are read-only and include --output json for traceability
    return f"tccli {prod} {action} --limit 5 --output json"


def synthesize(repo_root: Path, output: Path, per_skill: int = 2) -> dict:
    skill_dirs = sorted(repo_root.glob("qcloud-*-ops"))
    entries: list[dict] = []
    counter = 0
    for skill_dir in skill_dirs:
        skill = skill_dir.name
        eval_path = skill_dir / "assets" / "eval_queries.json"
        if not eval_path.exists():
            continue
        try:
            data = json.loads(eval_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        # eval_queries.json is a list; filter should_trigger=true
        if isinstance(data, dict):
            queries = data.get("queries") or data.get("cases") or []
        else:
            queries = data
        positives = [q for q in queries if q.get("should_trigger") is True]
        # deterministic: sort by query text
        positives.sort(key=lambda x: x.get("query", ""))
        for q in positives[:per_skill]:
            counter += 1
            query = q.get("query", "").strip()
            if not query:
                continue
            incident_id = f"inc-{_product_from_skill(skill)}-{counter:03d}"
            entry = {
                "incident_id": incident_id,
                "skill": skill,
                "request": query,
                "command": _command_for_skill(skill),
                "severity": _SEVERITIES[(counter - 1) % len(_SEVERITIES)],
                "source": "eval_queries",
            }
            entries.append(entry)
            if len(entries) >= 40:
                break
        if len(entries) >= 40:
            break

    # Ensure at least 20 entries, 5+ skills, all severities
    # If still short (should not happen with 31 skills), duplicate with new ids
    if len(entries) < 20:
        raise RuntimeError(f"only {len(entries)} entries synthesized, need >=20")

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    skills = len({e["skill"] for e in entries})
    sevs = {e["severity"] for e in entries}
    return {"total": len(entries), "skills": skills, "severities": sorted(sevs), "output": str(output)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthesize incident corpus.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "fixtures" / "incidents" / "corpus.jsonl")
    parser.add_argument("--per-skill", type=int, default=2)
    args = parser.parse_args()
    result = synthesize(args.repo_root, args.output, per_skill=args.per_skill)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
