#!/usr/bin/env python3
"""Aggregate harness evidence KPIs and gate against targets.

Loads one or more evidence JSON files, aggregates KPIs, prints a JSON report
to stdout, and exits 1 if any target is unmet (0 otherwise). No argv -> usage
to stderr, exit 2.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


TARGETS = {"leak": 0, "destructive_coverage": 1.0, "provenance": 1.0, "mixing": 0.0}


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(records)
    if n == 0:
        return {
            "kpi": {
                "leak": 0,
                "destructive_coverage": 1.0,
                "provenance": 1.0,
                "mixing": 0.0,
                "p95_ms": 0,
            },
            "records": 0,
        }
    # Malformed records (missing required keys) must not crash the whole gate,
    # but they must still FAIL it — count them as leakers with no provenance.
    KNOWN_SOURCES = {"gcl_runner", "sandbox_e2e", "ci"}
    leak = 0
    dest = []
    prov_hits = 0
    mixing = 0
    wall = []
    for r in records:
        if not isinstance(r, dict):
            leak += 1
            continue
        safety = r.get("safety") or {}
        if not safety.get("leak_checked", False):
            leak += 1
        if safety.get("destructive"):
            dest.append(r)
        prov = r.get("provenance")
        if isinstance(prov, dict) and prov.get("source") in KNOWN_SOURCES:
            prov_hits += 1
        if r.get("phase") == "self-test" and isinstance(prov, dict) and prov.get("source") == "production":
            mixing += 1
        budgets = r.get("budgets") or {}
        if isinstance(budgets.get("wall_clock_ms"), (int, float)):
            wall.append(budgets["wall_clock_ms"])
    dest_cov = (sum(1 for r in dest if (r.get("safety") or {}).get("token_bound")) / len(dest)) if dest else 1.0
    prov = prov_hits / n
    p95 = sorted(wall)[max(0, int(0.95 * len(wall)) - 1)] if wall else 0
    return {
        "kpi": {
            "leak": leak,
            "destructive_coverage": dest_cov,
            "provenance": prov,
            "mixing": mixing,
            "p95_ms": p95,
        },
        "records": n,
    }


def _load_records(paths: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for p in paths:
        with Path(p).open(encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            records.extend(data)
        else:
            records.append(data)
    return records


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: aggregate_kpi.py <evidence.json> [<evidence.json> ...]", file=sys.stderr)
        return 2

    records = _load_records(args)
    report = aggregate(records)
    print(json.dumps(report, indent=2))

    k = report["kpi"]
    if (
        k["leak"] > TARGETS["leak"]
        or k["destructive_coverage"] < TARGETS["destructive_coverage"]
        or k["provenance"] < TARGETS["provenance"]
        or k["mixing"] > TARGETS["mixing"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
