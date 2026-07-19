#!/usr/bin/env python3
"""rubric_calibrate.py — Generate per-skill adaptive threshold recommendations."""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict
import statistics


def load_traces(trace_dir: Path):
    traces = []
    for f in sorted(trace_dir.glob("gcl-trace-*.json")):
        try:
            traces.append(json.loads(f.read_text()))
        except Exception:
            pass
    return traces


def classify_op(command: str) -> str:
    cmd_lower = command.lower()
    if any(k in cmd_lower for k in ["delete", "destroy", "release", "terminate", "drop"]):
        return "delete"
    if any(k in cmd_lower for k in ["create", "start", "run"]):
        return "create"
    if any(k in cmd_lower for k in ["describe", "query", "list", "get", "search", "lookup"]):
        return "read"
    if any(k in cmd_lower for k in ["modify", "update", "set", "change", "attach"]):
        return "write"
    return "other"


def compute_stats(traces: list) -> dict:
    by_key = defaultdict(list)
    for t in traces:
        skill = t.get("skill", "unknown")
        for iteration in t.get("iterations", []):
            cmd = iteration.get("generator", {}).get("command", "")
            op = classify_op(cmd)
            scores = iteration.get("critic", {}).get("scores", {})
            if scores:
                key = (skill, op)
                by_key[key].append(scores)

    results = []
    for (skill, op), score_list in sorted(by_key.items()):
        dims = ["correctness", "safety", "idempotency", "traceability", "spec_compliance"]
        for dim in dims:
            vals = [s.get(dim, 0.5) for s in score_list]
            if len(vals) < 3:
                continue
            mean = statistics.mean(vals)
            std = statistics.stdev(vals) if len(vals) > 1 else 0.0
            results.append({
                "skill": skill,
                "op_type": op,
                "dimension": dim,
                "n_samples": len(vals),
                "mean": round(mean, 4),
                "stddev": round(std, 4),
                "default_threshold": {
                    "correctness": 0.5,
                    "safety": 1.0,
                    "idempotency": 0.5,
                    "traceability": 0.5,
                    "spec_compliance": 0.5,
                }.get(dim, 0.5),
            })
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace-dir", default="audit-results", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    traces = load_traces(args.trace_dir)
    stats = compute_stats(traces)
    print(json.dumps(stats, indent=2))

    if args.dry_run:
        print(f"[dry-run] Would generate {len(stats)} recommendations", file=sys.stderr)


if __name__ == "__main__":
    main()
