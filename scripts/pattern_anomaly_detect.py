#!/usr/bin/env python3
"""pattern_anomaly_detect.py — Detect emerging failure patterns."""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import statistics

DAYS_RECENT = 7
DAYS_HISTORICAL = 30
Z_THRESHOLD = 2.0


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


def detect_anomalies(traces: list):
    recent = Counter()
    historical = Counter()
    key_map = {}
    now = datetime.now()
    for t in traces:
        ts = t.get("timestamp", "")
        try:
            age = (now - datetime.fromisoformat(ts.replace("Z", "+00:00"))).days
        except Exception:
            age = 0
        fp = t.get("final", {}).get("failure_pattern", {})
        if not fp:
            continue
        key = (fp.get("skill", ""), fp.get("command", ""), fp.get("error", ""))
        key_map[key] = fp
        if age <= DAYS_RECENT:
            recent[key] += 1
        else:
            historical[key] += 1

    results = []
    all_keys = set(recent) | set(historical)
    for key in all_keys:
        r = recent.get(key, 0)
        h_vals = [historical.get(k, 0) for k in all_keys if k != key]
        if not h_vals:
            continue
        hist_mean = statistics.mean(h_vals)
        hist_std = statistics.stdev(h_vals) if len(h_vals) > 1 else 1.0
        z = (r - hist_mean) / max(hist_std, 0.1)
        if z > Z_THRESHOLD:
            fp = key_map[key]
            results.append({
                "type": "emerging",
                "skill": key[0],
                "command": key[1],
                "error": key[2],
                "recent_count": r,
                "historical_mean": round(hist_mean, 2),
                "z_score": round(z, 2),
                "severity": "major",
                "recommendation": "Investigate root cause or add to failure-patterns.md",
            })
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace-dir", default="audit-results", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    traces = load_traces(args.trace_dir, DAYS_HISTORICAL)
    anomalies = detect_anomalies(traces)
    print(json.dumps(anomalies, indent=2))
    if args.dry_run:
        print(f"[dry-run] {len(anomalies)} anomalies", file=sys.stderr)


if __name__ == "__main__":
    main()
