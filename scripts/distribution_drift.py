#!/usr/bin/env python3
"""distribution_drift.py — Detect GCL quality drift between time windows.

Compares a recent window (last 7 days) against a baseline window (8-30 days)
of GCL traces and reports per-metric / per-skill distribution drift using only
the Python standard library (no scipy/numpy).

CLI usage::

    python3 scripts/distribution_drift.py --trace-dir audit-results
    python3 scripts/distribution_drift.py --dry-run
    python3 scripts/distribution_drift.py --self-verify

Modules such as gcl_runner.py may import ``load_traces`` / ``compute_drift`` /
``analyze_drift`` without triggering side effects.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

_METRICS = ("pass_rate", "convergence_speed", "safety_score")
_RECENT_DAYS = 7
_RECENT_HOURS = _RECENT_DAYS * 24
_TOTAL_WINDOW_HOURS = 30 * 24  # recent 7d + baseline 8-30d
_KS_THRESHOLD = 0.3
# Finite stand-in for "infinite" drift_sigma against a constant baseline, so
# direction/severity thresholds still fire (the spec self-verify depends on it).
_SIGMA_INF = 1e9


def load_traces(trace_dir: Path, since_days: int) -> list[dict[str, Any]]:
    cutoff = datetime.now() - timedelta(days=since_days)
    mtime_cutoff = datetime.now(tz=UTC) - timedelta(days=since_days)
    traces = []
    for f in sorted(trace_dir.glob("gcl-trace-*.json")):
        # Perf: skip files whose mtime predates the cutoff before reading/parsing
        # (JSON timestamp filtering below is preserved for exactness).
        try:
            if datetime.fromtimestamp(f.stat().st_mtime, tz=UTC) < mtime_cutoff:
                continue
        except OSError:
            continue
        try:
            t = json.loads(f.read_text())
            ts = t.get("timestamp", "")
            if ts and datetime.fromisoformat(ts) < cutoff:
                continue
            traces.append(t)
        except (ImportError, OSError, ValueError, KeyError, AttributeError, TypeError):
            pass
    return traces


def _trace_pass_value(trace: dict[str, Any]) -> float | None:
    """1.0 for a PASS trace, 0.0 for a definite non-PASS, None if malformed."""
    final = trace.get("final")
    if not isinstance(final, dict) or not isinstance(final.get("status"), str):
        return None
    return 1.0 if final["status"] == "PASS" else 0.0


def _trace_convergence_speed(trace: dict[str, Any]) -> float | None:
    """1 / iteration_count — fewer iterations means faster convergence."""
    iters = trace.get("iterations")
    if not isinstance(iters, list) or not iters:
        return None
    return 1.0 / len(iters)


def _trace_safety_score(trace: dict[str, Any]) -> float | None:
    """Mean of per-iteration critic ``safety`` scores; None when absent."""
    vals = []
    for it in trace.get("iterations", []):
        if not isinstance(it, dict):
            continue
        critic = it.get("critic")
        if not isinstance(critic, dict):
            continue
        scores = critic.get("scores")
        if not isinstance(scores, dict):
            continue
        s = scores.get("safety")
        if isinstance(s, (int, float)) and not isinstance(s, bool):
            vals.append(float(s))
    return statistics.fmean(vals) if vals else None


def _compute_window_metrics(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Phase 1 — aggregate one window: global metrics, per-skill, per-dimension.

    Returns::

        {
            "n": int,
            "metrics": {"<metric>": {"values": [...], "mean": float | None}, ...},
            "per_skill": {"<skill>": {"<metric>": {"values": [...], "mean": ...}}},
            "per_dimension": {"<dim>": {"values": [...], "mean": ...}},
        }
    """
    metrics: dict[str, list[float]] = {m: [] for m in _METRICS}
    per_skill: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {m: [] for m in _METRICS}
    )
    per_dimension: dict[str, list[float]] = defaultdict(list)

    for tr in traces:
        if not isinstance(tr, dict):
            continue
        skill = tr.get("skill") if isinstance(tr.get("skill"), str) else ""
        values = {
            "pass_rate": _trace_pass_value(tr),
            "convergence_speed": _trace_convergence_speed(tr),
            "safety_score": _trace_safety_score(tr),
        }
        for metric, value in values.items():
            if value is None:
                continue
            metrics[metric].append(value)
            if skill:
                per_skill[skill][metric].append(value)
        for it in tr.get("iterations", []):
            if not isinstance(it, dict):
                continue
            critic = it.get("critic")
            if not isinstance(critic, dict):
                continue
            scores = critic.get("scores")
            if not isinstance(scores, dict):
                continue
            for dim, val in scores.items():
                if isinstance(val, (int, float)) and not isinstance(val, bool):
                    per_dimension[dim].append(float(val))

    def _summarize(vals: list[float]) -> dict[str, Any]:
        return {
            "values": vals,
            "mean": round(statistics.fmean(vals), 4) if vals else None,
        }

    return {
        "n": len(traces),
        "metrics": {m: _summarize(v) for m, v in metrics.items()},
        "per_skill": {
            skill: {m: _summarize(vals) for m, vals in mets.items() if vals}
            for skill, mets in per_skill.items()
        },
        "per_dimension": {dim: _summarize(vals) for dim, vals in per_dimension.items()},
    }


def _simplified_ks_test(recent: list[float], baseline: list[float]) -> float:
    """Phase 2 — simplified KS: max |CDF diff| across 10 equal-width buckets.

    Returns 0.0 when either sample has < 2 values or all values coincide.
    KS > 0.3 marks a significant distribution difference.
    """
    if len(recent) < 2 or len(baseline) < 2:
        return 0.0
    all_vals = recent + baseline
    lo, hi = min(all_vals), max(all_vals)
    if hi == lo:
        return 0.0
    ks_stat = 0.0
    for i in range(11):
        boundary = lo + (hi - lo) * i / 10
        cdf_recent = sum(1 for v in recent if v <= boundary) / len(recent)
        cdf_baseline = sum(1 for v in baseline if v <= boundary) / len(baseline)
        ks_stat = max(ks_stat, abs(cdf_recent - cdf_baseline))
    return round(ks_stat, 4)


def _drift_sigma(drift: float, baseline_values: list[float]) -> float:
    """Normalize drift by baseline stdev.

    A constant baseline (stdev == 0) with non-zero drift is a total regime
    change: report a signed sentinel instead of 0.0 so the direction and
    severity thresholds still fire (the spec's self-verify depends on this).
    """
    stdev = statistics.stdev(baseline_values) if len(baseline_values) >= 2 else 0.0
    if stdev > 0:
        return drift / stdev
    if drift != 0:
        return _SIGMA_INF if drift > 0 else -_SIGMA_INF
    return 0.0


def _drift_block(recent_values: list[float], baseline_values: list[float]) -> dict[str, Any]:
    """Per-metric drift stats: means, raw drift, sigma, direction, KS stat."""
    recent_mean = statistics.fmean(recent_values) if recent_values else 0.0
    baseline_mean = statistics.fmean(baseline_values) if baseline_values else 0.0
    drift = recent_mean - baseline_mean
    sigma = _drift_sigma(drift, baseline_values)
    direction = "↑" if sigma > 1.0 else ("↓" if sigma < -1.0 else "→")
    return {
        "recent": round(recent_mean, 4),
        "baseline": round(baseline_mean, 4),
        "drift": round(drift, 4),
        "drift_sigma": round(sigma, 4),
        "direction": direction,
        "ks_stat": _simplified_ks_test(recent_values, baseline_values),
    }


def _append_alert(alerts: list[dict[str, Any]], name: str, block: dict[str, Any]) -> None:
    """Emit an alert for a drift block once it crosses the severity gates."""
    sigma = block.get("drift_sigma", 0.0)
    if abs(sigma) < 1.0 or block.get("ks_stat", 0.0) <= _KS_THRESHOLD:
        return
    severity = "high" if sigma < -1.5 else ("medium" if sigma < -1.0 else "low")
    alerts.append({
        "metric": name,
        "direction": block.get("direction", "→"),
        "drift": block.get("drift", 0.0),
        "drift_sigma": sigma,
        "severity": severity,
    })


def _build_alerts(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Phase 3 — alerts where |drift_sigma| >= 1.0 AND KS > 0.3."""
    alerts: list[dict[str, Any]] = []
    for metric in _METRICS:
        _append_alert(alerts, f"global/{metric}", result.get(metric, {}))
    for skill, metrics in result.get("per_skill", {}).items():
        for metric, block in metrics.items():
            _append_alert(alerts, f"{skill}/{metric}", block)
    return alerts


def compute_drift(
    recent_traces: list[dict],
    baseline_traces: list[dict],
) -> dict[str, Any]:
    """Phase 3 — compare recent vs baseline windows to detect drift.

    Returns::

        {
            "pass_rate": {drift block},
            "convergence_speed": {drift block},
            "safety_score": {drift block},
            "per_skill": {"<skill>": {"<metric>": {drift block}, ...}, ...},
            "alerts": [{"metric", "direction", "drift", "drift_sigma", "severity"}, ...],
        }

    Returns ``{"error": "insufficient_recent_data"}`` when the recent window has
    fewer than 3 traces.
    """
    recent = _compute_window_metrics(recent_traces)
    if recent["n"] < 3:
        return {"error": "insufficient_recent_data"}
    baseline = _compute_window_metrics(baseline_traces)

    result: dict[str, Any] = {
        metric: _drift_block(
            recent["metrics"][metric]["values"],
            baseline["metrics"][metric]["values"],
        )
        for metric in _METRICS
    }
    per_skill: dict[str, dict[str, Any]] = {}
    for skill in sorted(set(recent["per_skill"]) | set(baseline["per_skill"])):
        blocks: dict[str, Any] = {}
        for metric in _METRICS:
            rvals = recent["per_skill"].get(skill, {}).get(metric, {}).get("values", [])
            bvals = baseline["per_skill"].get(skill, {}).get(metric, {}).get("values", [])
            if rvals and bvals:
                blocks[metric] = _drift_block(rvals, bvals)
        if blocks:
            per_skill[skill] = blocks
    result["per_skill"] = per_skill
    result["alerts"] = _build_alerts(result)
    return result


def _split_windows(
    traces: list[dict[str, Any]], since_hours: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split traces into (recent, baseline) by ISO ``timestamp``.

    recent = last 7 days; baseline = 8 days .. since_hours ago. Traces without a
    usable timestamp fall back to a time-order half-split (gcl_runner style).
    """
    now = datetime.now()
    recent_cutoff = now - timedelta(hours=_RECENT_HOURS)
    total_cutoff = now - timedelta(hours=since_hours)
    recent: list[dict[str, Any]] = []
    baseline: list[dict[str, Any]] = []
    for tr in traces:
        if not isinstance(tr, dict):
            continue
        ts = tr.get("timestamp")
        if not isinstance(ts, str) or not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            continue
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        if dt > recent_cutoff:
            recent.append(tr)
        elif dt > total_cutoff:
            baseline.append(tr)
    if recent or baseline:
        return recent, baseline
    mid = len(traces) // 2
    return traces[mid:], traces[:mid]  # newer half as recent, older as baseline


def analyze_drift(traces: list[dict], since_hours: int) -> dict[str, Any]:
    """Phase 4 — split traces into windows and compute drift.

    ``since_hours`` bounds the total lookback; the recent window is always the
    last 7 days and the baseline window the preceding 8-30 days.
    """
    recent, baseline = _split_windows(traces, since_hours)
    return compute_drift(recent, baseline)


def _resolve_block(result: dict[str, Any], metric_path: str) -> dict[str, Any]:
    """Look up the drift block for a ``global/<m>`` or ``<skill>/<m>`` alert path."""
    if metric_path.startswith("global/"):
        return result.get(metric_path.split("/", 1)[1], {})
    skill, metric = metric_path.split("/", 1)
    return result.get("per_skill", {}).get(skill, {}).get(metric, {})


def _print_alerts(result: dict[str, Any]) -> None:
    """Console output — one alert line per drift signal (spec output format)."""
    if "error" in result:
        print(f"distribution_drift: {result['error']}", file=sys.stderr)
        return
    print("=== 分布漂移检测 (recent=7d vs baseline=8-30d) ===")
    for alert in result.get("alerts", []):
        block = _resolve_block(result, alert["metric"])
        recent = block.get("recent", 0.0) * 100
        baseline = block.get("baseline", 0.0) * 100
        drift = alert.get("drift", 0.0) * 100
        sign = "↑" if drift > 0 else "↓"
        marker = "⚠" if alert.get("severity") != "low" else "→"
        tail = f"⚠ {alert.get('severity')}" if alert.get("severity") != "low" else "stable"
        print(
            f"{marker}  {alert['metric']}: "
            f"recent={recent:.0f}%  baseline={baseline:.0f}%  "
            f"{sign}{drift:+.0f}%  {tail}"
        )
    pass_rate = result.get("pass_rate", {})
    if pass_rate:
        trend = {"↑": "改善", "↓": "下降", "→": "无显著变化"}.get(
            pass_rate.get("direction", "→")
        )
        print(
            f"\n最近7天通过率趋势: {pass_rate.get('recent', 0.0) * 100:.0f}% "
            f"(baseline={pass_rate.get('baseline', 0.0) * 100:.0f}%, {trend})"
        )


def self_verify() -> bool:
    """Phase 5 — run the spec's self-verify block and print the alert table.

    Returns True when all assertions pass (CLI exit 0), False otherwise.
    """
    traces_recent = [
        {"final": {"status": "PASS"}, "iterations": [{"critic": {"scores": {"safety": 1.0}}}]},
        {"final": {"status": "PASS"}, "iterations": [{"critic": {"scores": {"safety": 1.0}}}]},
        {"final": {"status": "FAIL"}, "iterations": [{"critic": {"scores": {"safety": 0.5}}}]},
    ]
    traces_baseline = [
        {"final": {"status": "PASS"}, "iterations": [{"critic": {"scores": {"safety": 1.0}}}]},
        {"final": {"status": "PASS"}, "iterations": [{"critic": {"scores": {"safety": 1.0}}}]},
        {"final": {"status": "PASS"}, "iterations": [{"critic": {"scores": {"safety": 1.0}}}]},
    ]
    result = compute_drift(traces_recent, traces_baseline)
    assert result["pass_rate"]["drift"] < 0
    assert result["pass_rate"]["direction"] == "↓"
    assert result["alerts"]
    _print_alerts(result)
    return True


def main() -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description="Detect GCL quality drift across time windows.")
    ap.add_argument("--trace-dir", default="audit-results", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--self-verify", action="store_true", help="Run self-verification and exit 0/1."
    )
    args = ap.parse_args()
    if args.self_verify:
        return 0 if self_verify() else 1
    traces = load_traces(args.trace_dir, _TOTAL_WINDOW_HOURS // 24)
    result = analyze_drift(traces, since_hours=_TOTAL_WINDOW_HOURS)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    _print_alerts(result)
    if args.dry_run:
        n_alerts = len(result.get("alerts", [])) if isinstance(result, dict) else 0
        print(f"[dry-run] {n_alerts} drift alert(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
