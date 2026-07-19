#!/usr/bin/env python3
"""rubric_calibrate.py — Generate per-skill adaptive threshold recommendations."""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict
import statistics

DEFAULT_THRESHOLDS = {
    "correctness": 0.5,
    "safety": 1.0,
    "idempotency": 0.5,
    "traceability": 0.5,
    "spec_compliance": 0.5,
}

SAFETY_FLOOR = 1.0
SAFETY_FLOOR_ENFORCED = 0.5


def _extract_iteration_scores(traces: list, skill_filter: str | None = None) -> dict:
    """Extract scores from the last iteration of each trace, optionally filtered by skill."""
    by_skill = defaultdict(lambda: defaultdict(list))
    for trace in traces:
        skill = trace.get("skill", "unknown")
        if skill_filter and skill != skill_filter:
            continue
        iterations = trace.get("iterations", [])
        if not iterations:
            continue
        last = iterations[-1]
        scores = last.get("critic", {}).get("scores", {})
        for dim, val in scores.items():
            by_skill[skill][dim].append(val)
    return {k: dict(v) for k, v in by_skill.items()}


def _confidence(n_samples: int) -> str:
    """Return confidence tier based on sample size."""
    if n_samples < 10:
        return "LOW"
    if n_samples < 50:
        return "MEDIUM"
    return "HIGH"


def _suggested_with_safety(dimension: str, historical_mean: float, stddev: float) -> tuple:
    """Compute suggested threshold with safety floor logic.

    Returns (suggested_threshold, status).
    status: 'locked' if safety floor enforced, 'ok' otherwise.
    """
    if dimension == "safety":
        if historical_mean >= SAFETY_FLOOR:
            return (1.0, "locked")
        if historical_mean < SAFETY_FLOOR:
            return (SAFETY_FLOOR_ENFORCED, "locked")
        return (historical_mean, "ok")
    suggested = historical_mean - stddev
    if suggested < 0:
        suggested = 0.0
    return (round(suggested, 4), "ok")


def _load_traces(trace_dir: Path, since_days: int | None = None) -> list:
    """Load gcl-trace JSON files from trace_dir, optionally filtered by age.

    Args:
        trace_dir: directory containing gcl-trace-*.json files.
                   May be a bare directory or an /audit-results subdirectory.
        since_days: if set, only include traces newer than this many days.
    """
    # Normalise: if trace_dir/gcl-trace-*.json doesn't exist, try trace_dir/audit-results/
    glob_root = trace_dir
    candidates = list(glob_root.glob("gcl-trace-*.json"))
    if not candidates and (glob_root / "audit-results").exists():
        glob_root = glob_root / "audit-results"
        candidates = list(glob_root.glob("gcl-trace-*.json"))

    cutoff = None
    if since_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)

    traces = []
    for f in sorted(candidates):
        try:
            ts_str = f.stem.replace("gcl-trace-", "")  # e.g. "20250710-120000"
            ts = datetime.strptime(ts_str, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
            if cutoff and ts < cutoff:
                continue
        except ValueError:
            # Unrecognised filename pattern — skip
            continue
        try:
            traces.append(json.loads(f.read_text()))
        except Exception:
            pass
    return traces


def generate_report(traces_or_root, skill_filter: str | None = None,
                   thresholds: dict | None = None) -> dict:
    """Generate per-skill × per-dimension calibration report.

    Args:
        traces_or_root: either a list of trace dicts, or a Path to a directory
                        containing gcl-trace-*.json files.
        skill_filter: if set, only analyze this skill.
        thresholds: optional dict of dimension→threshold overrides.

    Returns:
        dict with 'skills', 'period_days', 'generated_at' keys.
        'skills' is a dict keyed by skill name, each containing
        'dimensions', 'confidence', 'sample_count'.
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS

    # Accept Path (directory) or list
    if isinstance(traces_or_root, Path):
        traces = _load_traces(traces_or_root, since_days=None)
    else:
        traces = traces_or_root

    scores_by_skill = _extract_iteration_scores(traces, skill_filter)

    skills_out = {}
    for skill, scores in sorted(scores_by_skill.items()):
        dims_out = {}
        sample_count = 0
        for dim in ["correctness", "safety", "idempotency", "traceability", "spec_compliance"]:
            vals = scores.get(dim, [])
            if not vals or len(vals) < 1:
                dims_out[dim] = {
                    "default": thresholds.get(dim, DEFAULT_THRESHOLDS.get(dim, 0.5)),
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
            default = thresholds.get(dim, DEFAULT_THRESHOLDS.get(dim, 0.5))
            dims_out[dim] = {
                "default": default,
                "mean": round(mean, 4),
                "std": round(std, 4),
                "suggested": suggested,
                "deviation": round(suggested - default, 4),
                "status": status,
            }
            sample_count = max(sample_count, len(vals))

        skills_out[skill] = {
            "dimensions": dims_out,
            "sample_count": sample_count,
            "confidence": _confidence(sample_count),
        }

    if not skills_out:
        return {}
    return {
        "skills": skills_out,
        "period_days": 90,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def print_table(report: dict) -> None:
    """Print a human-readable calibration table."""
    skills = report.get("skills", {})
    if not skills:
        print("No data.")
        return
    print(f"{'Skill':<22} {'Dim':<16} {'Default':>7} {'Mean':>6} {'Std':>5} {'Suggested':>9} {'Conf':<7} Status")
    print("-" * 85)
    for skill, info in sorted(skills.items()):
        dims = info.get("dimensions", {})
        conf = info.get("confidence", "")
        for dim in ["correctness", "safety", "idempotency", "traceability", "spec_compliance"]:
            d = dims.get(dim, {})
            suggested = d.get("suggested")
            mean = d.get("mean")
            std = d.get("std")
            status = d.get("status", "")
            default = d.get("default", "")
            if suggested is None:
                suggested_s = "N/A"
                mean_s = "N/A"
                std_s = "N/A"
            else:
                suggested_s = f"{suggested:.4f}"
                mean_s = f"{mean:.4f}" if mean else "N/A"
                std_s = f"{std:.4f}" if std else "N/A"
            print(
                f"{skill:<22} {dim:<16} {default:>7.4f} {mean_s:>6} "
                f"{std_s:>5} {suggested_s:>9} {conf:<7} {status}"
            )


def main():
    ap = argparse.ArgumentParser(description="Calibrate rubric thresholds from GCL trace data.")
    ap.add_argument("--trace-dir", default="audit-results", type=Path)
    ap.add_argument("--skill", default=None, help="Filter by skill name")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true", help="Output JSON report")
    args = ap.parse_args()

    # trace-dir may point to a parent dir or to the audit-results dir itself
    report = generate_report(args.trace_dir, skill_filter=args.skill)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_table(report)

    if args.dry_run:
        n = len(report.get("skills", {}))
        print(f"[dry-run] Would generate {n} skill recommendations", file=sys.stderr)


if __name__ == "__main__":
    main()
