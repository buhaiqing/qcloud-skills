#!/usr/bin/env python3
"""hallucination_detection.py — Detect potential hallucinations in GCL traces."""

import argparse
import json
import sys
from pathlib import Path


def detect_hallucinations(traces: list):
    results = []
    for t in traces:
        skill = t.get("skill", "unknown")
        for i, it in enumerate(t.get("iterations", [])):
            cmd = it.get("generator", {}).get("command", "")
            resp = it.get("generator", {}).get("result_excerpt", "")
            if not resp:
                continue
            try:
                result = json.loads(resp)
            except Exception:
                continue
            checks = []
            req_id = "RequestId" in str(result)
            if not req_id:
                checks.append("missing_request_id")
            is_list = any(k in cmd.lower() for k in ["describe", "list", "query", "search"])
            data = result.get("Response", {}).get("Data", result.get("Response", {}).get("Items", []))
            if is_list and not data and "Error" not in str(result):
                checks.append("null_result_on_list_query")
            if "Error" in str(result) and req_id:
                checks.append("error_with_request_id")
            if checks:
                results.append({
                    "skill": skill,
                    "command": cmd[:80],
                    "iter": i + 1,
                    "types": checks,
                    "suspect": True,
                })
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace-dir", default="audit-results", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    traces = [
        json.loads(f.read_text())
        for f in sorted(args.trace_dir.glob("gcl-trace-*.json"))
        if f.stat().st_size > 0
    ]
    suspects = detect_hallucinations(traces)
    print(json.dumps(suspects, indent=2))
    if args.dry_run:
        print(f"[dry-run] {len(suspects)} suspects", file=sys.stderr)


if __name__ == "__main__":
    main()
