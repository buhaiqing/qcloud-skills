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
    leak = sum(0 if r["safety"]["leak_checked"] else 1 for r in records)
    dest = [r for r in records if r["safety"]["destructive"]]
    dest_cov = (sum(1 for r in dest if r["safety"]["token_bound"]) / len(dest)) if dest else 1.0
    # Non-vacuous provenance: require a populated, known source enum — a bare/empty
    # provenance dict must NOT pass (otherwise the gate is always 1.0, see L8).
    KNOWN_SOURCES = {"gcl_runner", "sandbox_e2e", "ci"}
    prov = (
        sum(
            1
            for r in records
            if isinstance(r.get("provenance"), dict) and r["provenance"].get("source") in KNOWN_SOURCES
        )
        / n
    )
    mixing = (
        sum(
            1
            for r in records
            if r["phase"] == "self-test" and r["provenance"].get("source") == "production"
        )
        / n
    )
    p95 = sorted(r["budgets"]["wall_clock_ms"] for r in records)[max(0, int(0.95 * n) - 1)]
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
