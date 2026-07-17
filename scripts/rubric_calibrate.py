#!/usr/bin/env python3
"""Rubric adaptive threshold calibrator.

Reads GCL traces from audit-results/gcl-trace-*.json, computes per-skill + per-dimension
statistics, and suggests calibrated thresholds.

Usage:
  python3 scripts/rubric_calibrate.py                          # all skills, table output
  python3 scripts/rubric_calibrate.py --skill qcloud-cos-ops   # one skill
  python3 scripts/rubric_calibrate.py --json                  # JSON output
  python3 scripts/rubric_calibrate.py --days 30               # last 30 days only
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Default thresholds (mirror gcl_runner.py RUBRIC_THRESHOLDS)
DEFAULT_THRESHOLDS: dict[str, float] = {
    "correctness": 0.5,
    "safety": 1.0,
    "idempotency": 0.5,
    "traceability": 0.5,
    "spec_compliance": 0.5,
}
K_FACTOR = 1.0  # 1-sigma tolerance
MIN_SAMPLES = 10
HIGH_SAMPLES = 50
SAFETY_FLOOR = 0.5


def _load_traces(root: Path, days: int | None) -> list[dict]:
    """Load all gcl-trace-*.json under root, optionally filtered by days."""
    traces_dir = root / "audit-results"
    if not traces_dir.exists():
        return []
    cutoff = None
    if days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    traces = []
    for f in sorted(traces_dir.glob("gcl-trace-*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        # Parse timestamp from filename: gcl-trace-YYYYMMDD-HHMMSS.json
        ts_str = f.stem.replace("gcl-trace-", "")
        try:
            ts = datetime.strptime(ts_str, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if cutoff and ts < cutoff:
            continue
        traces.append(data)
    return traces


def _extract_iteration_scores(traces: list[dict], skill_filter: str | None) -> dict[str, dict[str, list[float]]]:
    """Extract per-skill + per-dimension score lists.

    Returns:
        {skill: {dimension: [score, ...]}}
    Only uses the final iteration of each trace (PASS iter or last RETRY iter).
    """
    result: dict[str, dict[str, list[float]]] = {}
    dims = list(DEFAULT_THRESHOLDS.keys())
    for trace in traces:
        skill = trace.get("skill", "unknown")
        if skill_filter and skill_filter != skill:
            continue
        iters = trace.get("iterations", [])
        if not iters:
            continue
        # Use last iteration's critic scores
        last = iters[-1]
        scores = last.get("critic", {}).get("scores", {})
        if not scores:
            continue
        result.setdefault(skill, {d: [] for d in dims})
        for d in dims:
            v = scores.get(d)
            if v is not None:
                result[skill][d].append(float(v))
    return result


def _suggested_with_safety(dim: str, mean: float, std: float) -> tuple[float, str]:
    """Return (suggested_threshold, status) with safety floor applied."""
    if dim == "safety":
        # safety never drops below 0.5
        suggested = max(SAFETY_FLOOR, mean - K_FACTOR * std)
        return round(suggested, 4), "locked"
    suggested = max(0.0, mean - K_FACTOR * std)
    return round(suggested, 4), "ok"


def _confidence(n: int) -> str:
    if n >= HIGH_SAMPLES:
        return "HIGH"
    if n >= MIN_SAMPLES:
        return "MEDIUM"
    return "LOW"


def generate_report(root: Path, skill_filter: str | None, days: int | None) -> dict:
    traces = _load_traces(root, days)
    if not traces:
        print("No traces found.", file=sys.stderr)
        return {}
    per_skill = _extract_iteration_scores(traces, skill_filter)
    output: dict = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "period_days": days,
        "total_traces": len(traces),
        "skills": {},
    }
    for skill, dim_scores in sorted(per_skill.items()):
        total = sum(len(v) for v in dim_scores.values())
        if total == 0:
            continue
        dims_out: dict = {}
        skill_out: dict = {
            "sample_count": total,
            "confidence": _confidence(total),
            "dimensions": dims_out,
        }
        for dim in DEFAULT_THRESHOLDS:
            vals = dim_scores.get(dim, [])
            if not vals:
                dims_out[dim] = {
                    "default": DEFAULT_THRESHOLDS[dim],
                    "mean": None,
                    "std": None,
                    "suggested": None,
                    "deviation": None,
                    "status": "no_data",
                }
                continue
            mean = statistics.mean(vals)
            std = statistics.stdev(vals) if len(vals) > 1 else 0.0
            suggested, status = _suggested_with_safety(dim, mean, std)
            default = DEFAULT_THRESHOLDS[dim]
            dev = round(suggested - default, 4)
            dims_out[dim] = {
                "default": default,
                "mean": round(mean, 4),
                "std": round(std, 4),
                "suggested": suggested,
                "deviation": dev,
                "status": status,
                "count": len(vals),
            }
        output["skills"][skill] = skill_out
    return output


def print_table(report: dict) -> None:
    skills = report.get("skills", {})
    if not skills:
        print("No data.")
        return
    period = report.get("period_days")
    period_str = f"最近 {period} 天" if period else "全部历史"
    print(f"\n{'='*70}")
    print(f"=== Rubric 阈值校准报告 ({period_str}) ===")
    print(f"{'='*70}")
    for skill, data in skills.items():
        dims = data["dimensions"]
        total = data["sample_count"]
        conf = data["confidence"]
        print(f"\nSkill: {skill}  |  样本: {total}  |  可信度: {conf}")
        print(f"{'-'*70}")
        print(f"{'维度':<18} {'默认阈值':>9} {'均值':>7} {'σ':>6} {'建议阈值':>9} {'偏离度':>8} {'状态':>12}")
        print(f"{'-'*70}")
        for dim, d in dims.items():
            default_s = f"{d['default']:.2f}"
            mean_s = f"{d['mean']:.2f}" if d["mean"] is not None else "N/A"
            std_s = f"{d['std']:.2f}" if d["std"] is not None else "N/A"
            sug_s = f"{d['suggested']:.2f}" if d["suggested"] is not None else "N/A"
            dev_s = f"{d['deviation']:.2f}" if d["deviation"] is not None else "N/A"
            status_s = d["status"]
            print(
                f"{dim:<18} {default_s:>9} {mean_s:>7} {std_s:>6} {sug_s:>9} {dev_s:>8} {status_s:>12}"
            )
        # Safety note
        if dims.get("safety", {}).get("status") == "locked":
            print("\n  💡 safety 维度永远不降，建议值仅供参考")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (default: parent of scripts/)",
    )
    p.add_argument("--skill", help="Only analyze this skill")
    p.add_argument("--days", type=int, default=90, help="Analyze traces from last N days (default: 90)")
    p.add_argument("--json", action="store_true", help="Output JSON instead of table")
    p.add_argument("--dry-run", action="store_true", help="Self-verify with synthetic data")
    return p


def self_verify() -> bool:
    """Self-check: synthetic data → known expected outputs."""
    # Synthetic trace with 5 iterations, known scores
    synth = {
        "skill": "qcloud-test-ops",
        "iterations": [
            {
                "critic": {
                    "scores": {
                        "correctness": 1.0,
                        "safety": 1.0,
                        "idempotency": 0.5,
                        "traceability": 1.0,
                        "spec_compliance": 0.0,
                    }
                }
            },
            {
                "critic": {
                    "scores": {
                        "correctness": 1.0,
                        "safety": 1.0,
                        "idempotency": 0.5,
                        "traceability": 1.0,
                        "spec_compliance": 0.0,
                    }
                }
            },
            {
                "critic": {
                    "scores": {
                        "correctness": 1.0,
                        "safety": 1.0,
                        "idempotency": 0.5,
                        "traceability": 1.0,
                        "spec_compliance": 0.5,
                    }
                }
            },
        ],
    }
    per_skill = _extract_iteration_scores([synth], "qcloud-test-ops")
    scores = per_skill.get("qcloud-test-ops", {})
    # correctness: all 1.0 → suggested = max(0.5, 1.0 - 1.0*0) = 1.0
    c_mean = statistics.mean(scores["correctness"])
    c_std = statistics.stdev(scores["correctness"]) if len(scores["correctness"]) > 1 else 0.0
    c_sug, _ = _suggested_with_safety("correctness", c_mean, c_std)
    assert c_sug == 1.0, f"correctness suggested={c_sug}, want 1.0"
    # spec_compliance: last iter = 0.5 → mean=0.5, std=0 → suggested=max(0,0.5-0)=0.5
    sc_vals = scores["spec_compliance"]
    sc_mean = statistics.mean(sc_vals)
    sc_std = statistics.stdev(sc_vals) if len(sc_vals) > 1 else 0.0
    sc_sug, _ = _suggested_with_safety("spec_compliance", sc_mean, sc_std)
    assert sc_sug == 0.5, f"spec_compliance suggested={sc_sug}, want 0.5"
    # safety: mean=1.0 → suggested=max(0.5, 1.0-0)=1.0 (locked)
    s_mean = statistics.mean(scores["safety"])
    s_std = 0.0
    s_sug, s_status = _suggested_with_safety("safety", s_mean, s_std)
    assert s_sug == 1.0 and s_status == "locked", f"safety suggested={s_sug}, status={s_status}"
    # spec_compliance mean-std < 0: [0.0, 0.5] → mean=0.25, std=0.25, suggested=max(0,0)=0
    sug_zero, _ = _suggested_with_safety("spec_compliance", 0.25, 0.25)
    assert sug_zero == 0.0, f"mean-std<0 should clamp to 0, got {sug_zero}"
    # no data → no crash
    empty = _extract_iteration_scores([], None)
    assert empty == {}, "empty traces should return empty dict"
    print("Self-verify: all assertions passed ✓")
    return True


def main() -> int:
    p = build_parser()
    args = p.parse_args()
    if args.dry_run:
        ok = self_verify()
        return 0 if ok else 1
    report = generate_report(args.root, args.skill, args.days)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_table(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
