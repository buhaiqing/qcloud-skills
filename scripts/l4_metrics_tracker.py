#!/usr/bin/env python3
"""L4 metrics tracker — Aggregate L4 acceptance criteria from GCL trace data.

Metrics computed:
  1. avg_iterations        — mean iteration count for PASS traces
  2. failure_pattern_hit_rate  — fraction of traces with preflight_reflexion.matched > 0
  3. emerging_pattern_latency — days since most recent pattern_anomaly Detect log
  4. success_path_reuse_rate  — fraction of PASS traces with preflight_reflexion.matched > 0
  5. rubric_threshold_deviation — stddev of (mean_dim_score - threshold) across dims

Output: audit-results/l4-metrics.json

Usage:
  python3 scripts/l4_metrics_tracker.py
  python3 scripts/l4_metrics_tracker.py --trace-dir audit-results
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DEFAULT_THRESHOLDS: dict[str, float] = {
    "correctness": 0.5,
    "safety": 1.0,
    "idempotency": 0.5,
    "traceability": 0.5,
    "spec_compliance": 0.5,
}
RUBRIC_DIMS = tuple(DEFAULT_THRESHOLDS.keys())


# ---------------------------------------------------------------------------
# 1. avg_iterations
# ---------------------------------------------------------------------------


def get_avg_iterations(traces: list[dict[str, Any]]) -> float | None:
    """Mean iteration count for PASS traces, or None if no PASS traces."""
    pass_iters = []
    for t in traces:
        if t.get("final", {}).get("status") == "PASS":
            pass_iters.append(len(t.get("iterations") or []))
    if not pass_iters:
        return None
    return round(statistics.mean(pass_iters), 4)


# ---------------------------------------------------------------------------
# 2. failure_pattern_hit_rate
# ---------------------------------------------------------------------------


def get_failure_pattern_hit_rate(traces: list[dict[str, Any]]) -> float | None:
    """Fraction of traces where preflight_reflexion.matched > 0.

    A non-zero matched count means at least one failure-pattern was retrieved
    and injected during preflight, so the hit is counted.
    """
    if not traces:
        return None
    hits = sum(
        1 for t in traces if t.get("preflight_reflexion", {}).get("matched", 0) > 0
    )
    return round(hits / len(traces), 4)


# ---------------------------------------------------------------------------
# 3. emerging_pattern_latency
# ---------------------------------------------------------------------------


def get_emerging_pattern_latency(trace_dir: Path) -> int | None:
    """Days since most recent pattern_anomaly Detect log was written.

    Returns None if no Detect log exists yet.
    """
    logs = sorted(
        trace_dir.glob("pattern-anomaly-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not logs:
        return None
    mtime = datetime.fromtimestamp(logs[0].stat().st_mtime, tz=timezone.utc)
    age = datetime.now(timezone.utc) - mtime
    return age.days


# ---------------------------------------------------------------------------
# 4. success_path_reuse_rate
# ---------------------------------------------------------------------------


def get_success_path_reuse_rate(traces: list[dict[str, Any]]) -> float | None:
    """Fraction of PASS traces with preflight_reflexion.matched > 0.

    A non-zero matched count during a PASS trace indicates the Generator
    retrieved and reused a success-pattern during preflight.
    """
    pass_traces = [t for t in traces if t.get("final", {}).get("status") == "PASS"]
    if not pass_traces:
        return None
    reused = sum(
        1
        for t in pass_traces
        if t.get("preflight_reflexion", {}).get("matched", 0) > 0
    )
    return round(reused / len(pass_traces), 4)


# ---------------------------------------------------------------------------
# 5. rubric_threshold_deviation
# ---------------------------------------------------------------------------


def get_rubric_threshold_deviation(traces: list[dict[str, Any]]) -> float | None:
    """Standard deviation of mean_score - threshold across all dimensions.

    Compares the empirical mean score per rubric dimension against the
    default static threshold; returns stddev of those deviations.
    Lower is better — approaching 0 means adaptive thresholds are well-calibrated.
    """
    if not traces:
        return None

    dim_scores: dict[str, list[float]] = {dim: [] for dim in RUBRIC_DIMS}
    for t in traces:
        iters = t.get("iterations") or []
        if not iters:
            continue
        scores = iters[-1].get("critic", {}).get("scores") or {}
        for dim in RUBRIC_DIMS:
            if dim in scores:
                dim_scores[dim].append(scores[dim])

    if not any(dim_scores[dim] for dim in RUBRIC_DIMS):
        return None

    deviations = []
    for dim in RUBRIC_DIMS:
        vals = dim_scores[dim]
        if vals:
            mean = statistics.mean(vals)
            deviations.append(mean - DEFAULT_THRESHOLDS[dim])

    if not deviations:
        return None
    return round(statistics.stdev(deviations), 4)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _load_traces(trace_dir: Path, since_days: int | None = None) -> list[dict[str, Any]]:
    """Load all gcl-trace-*.json files from trace_dir."""
    cutoff: datetime | None = None
    if since_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)

    traces: list[dict[str, Any]] = []
    for path in sorted(trace_dir.glob("gcl-trace-*.json")):
        try:
            t = json.loads(path.read_text())
        except Exception:
            continue
        if cutoff is not None:
            ts_str = t.get("timestamp", "")
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if ts < cutoff:
                        continue
                except Exception:
                    pass
        traces.append(t)
    return traces


def _status_lower_is_better(current: float, target: float) -> str:
    """Status for metrics where lower current value is better (≤ target)."""
    return "✅" if current <= target else "❌"


def _status_higher_is_better(current: float, target: float) -> str:
    """Status for metrics where higher current value is better (≥ target)."""
    if current >= target:
        return "✅"
    if current >= target * 0.8:
        return "⚠️"
    return "❌"


def _build_metric(
    current: float | None,
    target: float,
    unit: str = "",
    lower_is_better: bool = False,
    note: str = "",
) -> dict[str, Any]:
    if current is None:
        status = "❌"
    elif lower_is_better:
        status = _status_lower_is_better(current, target)
    else:
        status = _status_higher_is_better(current, target)

    return {
        "current": current,
        "target": target,
        "unit": unit or None,
        "status": status,
        "note": note or None,
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Track L4 acceptance metrics.")
    parser.add_argument(
        "--trace-dir",
        default="audit-results",
        type=Path,
        help="Directory containing gcl-trace-*.json files",
    )
    parser.add_argument(
        "--since-days",
        type=int,
        default=30,
        help="Consider traces from the last N days (default: 30)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write output to this path instead of audit-results/l4-metrics.json",
    )
    args = parser.parse_args()

    traces = _load_traces(args.trace_dir, since_days=args.since_days)

    avg_iter = get_avg_iterations(traces)
    fp_hit = get_failure_pattern_hit_rate(traces)
    emerg_lat = get_emerging_pattern_latency(args.trace_dir)
    reuse = get_success_path_reuse_rate(traces)
    rubric_dev = get_rubric_threshold_deviation(traces)

    fp_note = "尚未启用" if fp_hit == 0 else ""
    reuse_note = "尚未启用" if reuse == 0 else ""

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            # lower-is-better: ≤ 1.8
            "avg_iterations": _build_metric(avg_iter, 1.8, lower_is_better=True, note="20% reduction target"),
            # higher-is-better: ≥ 0.6
            "failure_pattern_hit_rate": _build_metric(fp_hit, 0.6, note=fp_note),
            # lower-is-better: < 7 days
            "emerging_pattern_latency": _build_metric(emerg_lat, 7, unit="days", lower_is_better=True),
            # higher-is-better: > 0.9
            "success_path_reuse_rate": _build_metric(reuse, 0.9, note=reuse_note),
            # lower-is-better: < 0.1
            "rubric_threshold_deviation": _build_metric(rubric_dev, 0.1, lower_is_better=True),
        },
    }

    output_path: Path = args.output or (args.trace_dir / "l4-metrics.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
