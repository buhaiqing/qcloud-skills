#!/usr/bin/env python3
"""distribution_drift.py — Detect GCL quality drift over time windows."""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
import statistics


def load_traces(trace_dir: Path, since_days: int):
    cutoff = datetime.now() - timedelta(days=since_days)
    traces = []
    for f in sorted(trace_dir.glob("gcl-trace-*.json")):
        try:
            t = json.loads(f.read_text())
            ts = t.get("timestamp", "")
            if ts and datetime.fromisoformat(ts.replace("Z", "+00:00")) < cutoff:
                continue
            traces.append(t)
        except Exception:
            pass
    return traces


def compute_drift(traces1, traces2):
    by_skill_dim = defaultdict(lambda: {"w1": [], "w2": []})
    for t, bucket in [(traces1, "w1"), (traces2, "w2")]:
        for tr in t:
            skill = tr.get("skill", "unknown")
            for it in tr.get("iterations", []):
                scores = it.get("critic", {}).get("scores", {})
                for dim, val in scores.items():
                    by_skill_dim[(skill, dim)][bucket].append(val)
    results = []
    for (skill, dim), vals in sorted(by_skill_dim.items()):
        w1, w2 = vals["w1"], vals["w2"]
        if len(w1) < 3 or len(w2) < 3:
            continue
        m1, m2 = statistics.mean(w1), statistics.mean(w2)
        delta = m1 - m2
        if abs(delta) > 0.15:
            results.append({
                "skill": skill,
                "dimension": dim,
                "window1_mean": round(m1, 4),
                "window2_mean": round(m2, 4),
                "delta": round(delta, 4),
                "alert": "DEGRADING" if delta < 0 else "IMPROVING",
                "n_w1": len(w1),
                "n_w2": len(w2),
            })
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace-dir", default="audit-results", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    w1 = load_traces(args.trace_dir, 7)
    w2 = load_traces(args.trace_dir, 30)
    drift = compute_drift(w1, w2)
    print(json.dumps(drift, indent=2))
    if args.dry_run:
        print(f"[dry-run] {len(drift)} drift signals", file=sys.stderr)


if __name__ == "__main__":
    main()
