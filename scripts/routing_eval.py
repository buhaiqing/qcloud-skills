#!/usr/bin/env python3
"""Evaluate routing_decision.py against eval_queries.json — blueprint KPI gate.

Exit: 0=all pass, 1=partial fail, 2=no eval_queries found.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "routing_decision.py"
EVAL_FILE = ROOT / "docs" / "harness-engineering" / "agent-routing-blueprint" / "assets" / "eval_queries.json"


def run_decision(task: str) -> str:
    r = subprocess.run(
        ["python3", str(SCRIPT), task, "--json"],
        capture_output=True, text=True, timeout=10, check=False
    )
    try:
        return json.loads(r.stdout)["routing"]
    except (json.JSONDecodeError, KeyError):
        return "ERROR"


def main() -> int:
    if not EVAL_FILE.exists():
        print(f"ERROR: {EVAL_FILE} not found")
        return 2

    queries = json.loads(EVAL_FILE.read_text())
    passed = 0
    results = []
    for item in queries:
        actual = run_decision(item["task"])
        ok = actual == item["expected_routing"]
        if ok:
            passed += 1
        results.append({
            "id": item["id"],
            "expected": item["expected_routing"],
            "actual": actual,
            "pass": ok,
        })

    print(f"=== Blueprint routing KPI — {passed}/{len(results)} passed ===")
    for r in results:
        icon = "✅" if r["pass"] else "❌"
        print(f"  {icon} {r['id']:12s}  expected={r['expected']:20s}  actual={r['actual']}")
    print()

    if passed == len(results):
        print(f"All {len(results)} routing decisions correct — KPI PASS")
        return 0
    print(f"{len(results) - passed}/{len(results)} failed — KPI FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
