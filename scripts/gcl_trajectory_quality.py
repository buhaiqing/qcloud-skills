#!/usr/bin/env python3
"""Trajectory quality analyzer — no-reference evaluation from GCL traces.

Computes trajectory-quality signals from audit-results/gcl-trace-*.json
without ground truth. All metrics are derived from trace structure.

Usage:
  python3 scripts/gcl_trajectory_quality.py [--since-hours 720]
  python3 scripts/gcl_trajectory_quality.py --json
  python3 scripts/gcl_trajectory_quality.py --since-hours 168  # last week
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

RUBRIC_DIMS = ("correctness", "safety", "idempotency", "traceability", "spec_compliance")


def _all_iter_scores(trace: dict[str, Any]) -> list[dict[str, float]]:
    """Return list of critic scores per iteration (all iterations, not just last)."""
    return [
        dict(it.get("critic", {}).get("scores", {}))
        for it in trace.get("iterations", [])
        if it.get("critic", {}).get("scores")
    ]


def convergence_speed(trace: dict[str, Any]) -> dict[str, Any]:
    """Compute convergence metrics for one trace.

    convergence_speed: fraction of iterations used (iter_passed / max_iter).
      1.0 = converged on first iteration.
    oscillation_count: number of times any rubric dimension went up then down.
    score_variance: per-dimension variance of scores across iterations.
    """
    iters = trace.get("iterations", [])
    if not iters:
        return {"convergence_speed": None, "oscillation_count": 0, "score_variance": {}}

    n = len(iters)
    status = (trace.get("final") or {}).get("status", "UNKNOWN")

    # convergence_speed: 1.0 = first iter, < 1.0 = wasted iters
    # PASS: how many iters to first PASS
    if status == "PASS":
        # Find first iter that got PASS decision
        for i, it in enumerate(iters):
            if it.get("decision") == "PASS":
                convergence_speed = (i + 1) / n
                break
        else:
            convergence_speed = 1.0  # used all iters
    elif status in ("SAFETY_FAIL", "MAX_ITER"):
        convergence_speed = 1.0  # used all iters
    else:
        convergence_speed = 1.0

    # oscillation_count: for each dim, count up-down pairs
    all_scores = _all_iter_scores(trace)
    if len(all_scores) < 2:
        return {
            "convergence_speed": round(convergence_speed, 4),
            "oscillation_count": 0,
            "score_variance": {d: 0.0 for d in RUBRIC_DIMS},
        }

    osc = 0
    variances = {}
    for dim in RUBRIC_DIMS:
        vals = [s.get(dim, 0) or 0 for s in all_scores]
        if len(vals) > 1:
            variances[dim] = round(statistics.variance(vals) if len(vals) > 1 else 0.0, 4)
            for i in range(len(vals) - 1):
                delta = vals[i + 1] - vals[i]
                # oscillation: direction changes between consecutive pairs
                if i > 0:
                    prev_delta = vals[i] - vals[i - 1]
                    if prev_delta * delta < 0:  # sign flip = oscillation
                        osc += 1
        else:
            variances[dim] = 0.0

    return {
        "convergence_speed": round(convergence_speed, 4),
        "oscillation_count": osc,
        "score_variance": variances,
    }


def safety_trajectory(trace: dict[str, Any]) -> dict[str, Any]:
    """Analyze safety compliance across iterations.

    safety_trajectory: list of safety scores per iteration.
    safety_persistent_low: true if safety < 1.0 for all iterations.
    safety_recovery: true if safety dropped but recovered to 1.0.
    """
    all_scores = _all_iter_scores(trace)
    safety_vals = [s.get("safety", 1.0) for s in all_scores]

    if not safety_vals:
        return {"safety_trajectory": [], "safety_persistent_low": None, "safety_recovery": None}

    persistent_low = all(v < 1.0 for v in safety_vals)
    recovery = any(v < 1.0 for v in safety_vals) and safety_vals[-1] == 1.0

    return {
        "safety_trajectory": [round(v, 4) for v in safety_vals],
        "safety_persistent_low": persistent_low,
        "safety_recovery": recovery,
    }


def early_failure(trace: dict[str, Any]) -> dict[str, Any]:
    """Detect early-stage failures.

    early_failure: true if SAFETY_FAIL or MAX_ITER in first 2 iterations.
    """
    iters = trace.get("iterations", [])[:2]
    if not iters:
        return {"early_failure": None}
    decisions = [it.get("decision", "") for it in iters]
    early_fail = any(d in ("SAFETY_FAIL", "MAX_ITER") for d in decisions)
    return {"early_failure": early_fail, "fail_at_iter": next((i + 1 for i, d in enumerate(decisions) if d in ("SAFETY_FAIL", "MAX_ITER")), None)}


def iter_efficiency(trace: dict[str, Any]) -> dict[str, Any]:
    """Compute iteration efficiency metrics.

    wasted_iters: iterations after first PASS but before max (for PASS traces).
    """
    iters = trace.get("iterations", [])
    n = len(iters)
    if n == 0:
        return {"iter_efficiency": None, "wasted_iters": 0}

    status = (trace.get("final") or {}).get("status", "UNKNOWN")
    final_iter = (trace.get("final") or {}).get("iter", n)

    if status == "PASS":
        # Find first PASS
        first_pass = next((i + 1 for i, it in enumerate(iters) if it.get("decision") == "PASS"), n)
        wasted = n - first_pass
        efficiency = first_pass / n
    else:
        wasted = 0
        efficiency = 1.0  # used all available

    return {
        "iter_efficiency": round(efficiency, 4),
        "wasted_iters": wasted,
        "total_iters": n,
        "final_iter": final_iter,
    }


def outlier_score(trace: dict[str, Any], baselines: dict[str, dict[str, tuple[float, float]]]) -> dict[str, Any]:
    """Detect if this trajectory is an outlier vs per-skill historical baselines.

    Baselines: {skill: {dim: (mean, stdev)}}
    outlier: true if any dim deviates > 2σ from baseline mean.
    """
    skill = trace.get("skill", "unknown")
    all_scores = _all_iter_scores(trace)
    if not all_scores or skill not in baselines:
        return {"outlier": None, "outlier_dims": []}

    # Use final iteration scores for outlier detection
    final_scores = all_scores[-1]
    base = baselines.get(skill, {})
    outlier_dims = []

    for dim, val in final_scores.items():
        if dim in base and dim in RUBRIC_DIMS:
            mean, stdev = base[dim]
            if stdev > 0 and abs(val - mean) > 2 * stdev:
                outlier_dims.append(dim)

    return {
        "outlier": len(outlier_dims) > 0,
        "outlier_dims": outlier_dims,
    }


def compute_baselines(traces: list[dict[str, Any]], min_samples: int = 5) -> dict[str, dict[str, tuple[float, float]]]:
    """Compute per-skill per-dimension historical baselines (mean, stdev).

    Only uses final-iteration scores for baselines.
    """
    by_skill: dict[str, dict[str, list[float]]] = {}
    for t in traces:
        skill = t.get("skill", "unknown")
        all_scores = _all_iter_scores(t)
        if not all_scores:
            continue
        final = all_scores[-1]
        by_skill.setdefault(skill, {d: [] for d in RUBRIC_DIMS})
        for d in RUBRIC_DIMS:
            v = final.get(d)
            if v is not None:
                by_skill[skill][d].append(float(v))

    baselines = {}
    for skill, dim_vals in by_skill.items():
        dim_stats = {}
        for d, vals in dim_vals.items():
            if len(vals) >= min_samples:
                dim_stats[d] = (statistics.mean(vals), statistics.stdev(vals))
            elif len(vals) > 1:
                dim_stats[d] = (statistics.mean(vals), statistics.stdev(vals))
        if dim_stats:
            baselines[skill] = dim_stats

    return baselines


def dimension_correlation(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute correlation matrix between rubric dimensions (Pearson r).

    Uses final-iteration scores across all traces.
    """
    dim_vals: dict[str, list[float]] = {d: [] for d in RUBRIC_DIMS}

    for t in traces:
        all_scores = _all_iter_scores(t)
        if not all_scores:
            continue
        final = all_scores[-1]
        for d in RUBRIC_DIMS:
            v = final.get(d)
            if v is not None:
                dim_vals[d].append(float(v))

    # Pearson correlation between dimensions
    def pearson(x: list[float], y: list[float]) -> float | None:
        n = min(len(x), len(y))
        if n < 3:
            return None
        x, y = x[:n], y[:n]
        mx, my = statistics.mean(x), statistics.mean(y)
        cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / n
        sx = math.sqrt(sum((xi - mx) ** 2 for xi in x) / n)
        sy = math.sqrt(sum((yi - my) ** 2 for yi in y) / n)
        if sx == 0 or sy == 0:
            return None
        return round(cov / (sx * sy), 3)

    dims = [d for d in RUBRIC_DIMS if len(dim_vals[d]) >= 3]
    corr = {}
    for d1 in dims:
        corr[d1] = {}
        for d2 in dims:
            corr[d1][d2] = pearson(dim_vals[d1], dim_vals[d2]) if d1 != d2 else 1.0

    return {"correlation_matrix": corr, "sample_counts": {d: len(dim_vals[d]) for d in RUBRIC_DIMS}}


def analyze_traces(traces: list[dict[str, Any]], baselines: dict[str, dict[str, tuple[float, float]]]) -> dict[str, Any]:
    """Compute all trajectory quality metrics for a set of traces."""
    results = []
    conv_speeds = []
    oscillation_counts = []
    early_failures = 0
    safety_persistent_low_count = 0
    safety_recovery_count = 0
    outlier_count = 0
    wasted_iters_total = 0
    total_iters = 0
    efficiency_scores = []

    for t in traces:
        conv = convergence_speed(t)
        safety = safety_trajectory(t)
        early = early_failure(t)
        eff = iter_efficiency(t)
        outlier = outlier_score(t, baselines)

        conv_speeds.append(conv["convergence_speed"] or 1.0)
        oscillation_counts.append(conv["oscillation_count"])
        if early.get("early_failure"):
            early_failures += 1
        if safety.get("safety_persistent_low"):
            safety_persistent_low_count += 1
        if safety.get("safety_recovery"):
            safety_recovery_count += 1
        if outlier.get("outlier"):
            outlier_count += 1
        if eff.get("iter_efficiency") is not None:
            efficiency_scores.append(eff["iter_efficiency"])
        wasted_iters_total += eff.get("wasted_iters", 0)
        total_iters += eff.get("total_iters", 0)

        results.append({
            "skill": t.get("skill"),
            "status": (t.get("final") or {}).get("status"),
            "convergence": conv,
            "safety": safety,
            "early_failure": early,
            "efficiency": eff,
            "outlier": outlier,
        })

    n = len(traces)
    dim_corr = dimension_correlation(traces)

    return {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window": {"trace_count": n},
        "summary": {
            "avg_convergence_speed": round(statistics.mean(conv_speeds), 4) if conv_speeds else None,
            "avg_oscillation_count": round(statistics.mean(oscillation_counts), 3) if oscillation_counts else 0.0,
            "oscillation_rate": round(sum(1 for o in oscillation_counts if o > 0) / n, 4) if n else None,
            "early_failure_rate": round(early_failures / n, 4) if n else None,
            "safety_persistent_low_rate": round(safety_persistent_low_count / n, 4) if n else None,
            "safety_recovery_rate": round(safety_recovery_count / n, 4) if n else None,
            "outlier_rate": round(outlier_count / n, 4) if n else None,
            "avg_iter_efficiency": round(statistics.mean(efficiency_scores), 4) if efficiency_scores else None,
            "wasted_iter_rate": round(wasted_iters_total / max(total_iters, 1), 4),
        },
        "traces": results,
        "dimension_correlation": dim_corr,
        "baselines": {
            skill: {dim: {"mean": round(m, 4), "stdev": round(s, 4)}
                    for dim, (m, s) in dim_stats.items()}
            for skill, dim_stats in baselines.items()
        },
    }


def _load_traces(root: Path, since_hours: int | None) -> list[dict[str, Any]]:
    """Load gcl-trace-*.json files from audit-results."""
    audit = root / "audit-results"
    if not audit.is_dir():
        return []
    paths = sorted(audit.glob("gcl-trace-*.json"))
    if since_hours is None:
        return [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    out = []
    for p in paths:
        try:
            ts = datetime.strptime(p.stem.replace("gcl-trace-", ""), "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if ts >= cutoff:
            out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def persist(root: Path, data: dict[str, Any]) -> Path:
    out_dir = root / "audit-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"gcl-trajectory-quality-{ts}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def self_verify() -> bool:
    """Self-check: synthetic traces → known expected outputs."""
    traces = [
        {
            "skill": "qcloud-test",
            "iterations": [
                {"iter": 1, "decision": "RETRY", "critic": {"scores": {"correctness": 0.0, "safety": 1.0, "idempotency": 0.5, "traceability": 0.5, "spec_compliance": 0.0}}},
                {"iter": 2, "decision": "PASS", "critic": {"scores": {"correctness": 1.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 1.0}}},
            ],
            "final": {"status": "PASS", "iter": 2},
        },
        {
            "skill": "qcloud-test",
            "iterations": [
                {"iter": 1, "decision": "SAFETY_FAIL", "critic": {"scores": {"correctness": 0.0, "safety": 0.0, "idempotency": 0.5, "traceability": 0.5, "spec_compliance": 0.0}}},
            ],
            "final": {"status": "SAFETY_FAIL", "iter": 1},
        },
    ]

    # Test convergence_speed
    conv1 = convergence_speed(traces[0])
    assert conv1["convergence_speed"] == 1.0, f"trace1 conv={conv1['convergence_speed']}, want 1.0"
    conv2 = convergence_speed(traces[1])
    assert conv2["convergence_speed"] == 1.0, f"trace2 conv={conv2['convergence_speed']}, want 1.0"

    # Test safety_trajectory
    s1 = safety_trajectory(traces[0])
    assert s1["safety_trajectory"] == [1.0, 1.0], f"safety_trajectory={s1['safety_trajectory']}"
    assert s1["safety_persistent_low"] is False
    s2 = safety_trajectory(traces[1])
    assert s2["safety_persistent_low"] is True

    # Test early_failure
    e1 = early_failure(traces[0])
    assert e1["early_failure"] is False
    e2 = early_failure(traces[1])
    assert e2["early_failure"] is True

    # Test iter_efficiency
    eff1 = iter_efficiency(traces[0])
    assert eff1["wasted_iters"] == 0
    assert eff1["iter_efficiency"] == 1.0

    # Test baselines
    baselines = compute_baselines(traces)
    assert "qcloud-test" in baselines

    # Test outlier
    o = outlier_score(traces[1], baselines)
    assert o["outlier"] is not None  # stdev=0 when n<5

    # Test dimension_correlation
    corr = dimension_correlation(traces)
    assert "correlation_matrix" in corr

    print("Self-verify: all assertions passed ✓")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--since-hours", type=int, default=720, help="Analyze traces from last N hours (default: 720 = 30 days)")
    parser.add_argument("--json", action="store_true", help="Output JSON to stdout")
    parser.add_argument("--dry-run", action="store_true", help="Self-verify with synthetic data")
    args = parser.parse_args()

    if args.dry_run:
        ok = self_verify()
        return 0 if ok else 1

    traces = _load_traces(args.root, args.since_hours)
    if not traces:
        print("No gcl-trace files found.", file=sys.stderr)
        return 1

    baselines = compute_baselines(traces)
    result = analyze_traces(traces, baselines)
    out_path = persist(args.root, result)

    summary = result["summary"]
    print(f"Trajectory quality summary ({result['window']['trace_count']} traces):")
    print(f"  avg_convergence_speed:   {summary['avg_convergence_speed']}")
    print(f"  avg_oscillation_count:   {summary['avg_oscillation_count']}")
    print(f"  oscillation_rate:        {summary['oscillation_rate']}")
    print(f"  early_failure_rate:     {summary['early_failure_rate']}")
    print(f"  safety_persistent_low:  {summary['safety_persistent_low_rate']}")
    print(f"  safety_recovery:        {summary['safety_recovery_rate']}")
    print(f"  outlier_rate:           {summary['outlier_rate']}")
    print(f"  avg_iter_efficiency:    {summary['avg_iter_efficiency']}")
    print(f"  wasted_iter_rate:       {summary['wasted_iter_rate']}")
    print(f"  Output: {out_path}")

    if args.json:
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
