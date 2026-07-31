#!/usr/bin/env python3
"""Skill quality score — aggregate GCL/evidence/reflexion history into 0-1 score.

CLI:
  python3 scripts/skill_quality_score.py [--json] [--root PATH]
                                          [--since-hours N]
                                          [--threshold F]
                                          [--persist]

The score is a weighted sum of four components, each in [0, 1]:

  gcl_pass_rate (40%)              — fraction of PASS over total traces
  evidence_kernel_provenance (20%) — fraction of evidence-*.json with
                                     provenance.source ∈ KNOWN_SOURCES
  reflexion_failure_recurrence (20%) — 1.0 - clamp(recurring_pattern_count /
                                                  threshold, 0, 1)
  distribution_drift_severity (20%) — 1.0 - clamp(degraded_dim_count /
                                                 threshold, 0, 1)

Per-skill `upgrade_signal` flips to True when quality_score < threshold
(default 0.6). The script never raises on missing data — empty inputs
return an empty report with summary.total_executions=0.

Stdlib-only. No new dependencies.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

# Component weights — sum to 1.0
WEIGHTS: dict[str, float] = {
    "gcl_pass_rate": 0.40,
    "evidence_kernel_provenance": 0.20,
    "reflexion_failure_recurrence": 0.20,
    "distribution_drift_severity": 0.20,
}

# Sources the evidence kernel vouches for (L11 lesson — must be a closed enum).
KNOWN_PROVENANCE_SOURCES = frozenset({"gcl_runner", "sandbox_e2e", "ci"})

# Recurrence/drift thresholds for the bounded linear mapping. Higher count
# of recurring patterns / degraded dims drags the score toward 0; 0 counts
# leave the component at 1.0.
RECURRENCE_SATURATION = 5      # 5+ recurring patterns → recurrence=0
DRIFT_SATURATION = 3           # 3+ degraded dims → drift=0

# Default upgrade threshold (L4 / L8 — must be tunable from CLI).
UPGRADE_THRESHOLD = 0.6

# Rubric dimensions tracked in trace final-iteration scores.
RUBRIC_DIMS = ("correctness", "safety", "idempotency", "traceability", "spec_compliance")


def read_traces(root: Path, since_hours: int | None = 168) -> list[dict[str, Any]]:
    """Load gcl-trace-*.json files under audit-results/, windowed by mtime.

    Returns an empty list (not raises) when the audit-results/ directory is
    missing or no files match — per L10 (convergence gate on runtime
    artifacts must skip gracefully).
    """
    audit = root / "audit-results"
    if not audit.is_dir():
        return []
    paths = sorted(audit.glob("gcl-trace-*.json"))
    if since_hours is None:
        out: list[dict[str, Any]] = []
        for p in paths:
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                continue
        return out
    cutoff = datetime.now(UTC) - timedelta(hours=since_hours)
    out = []
    for p in paths:
        try:
            ts = datetime.fromtimestamp(p.stat().st_mtime, tz=UTC)
        except OSError:
            continue
        if ts < cutoff:
            continue
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return out


def read_evidence_records(
    root: Path, skill: str | None = None, since_hours: int | None = None,
) -> list[dict[str, Any]]:
    """Load evidence-*.json under audit-results/, optionally filtered by skill."""
    audit = root / "audit-results"
    if not audit.is_dir():
        return []
    paths = sorted(audit.glob("evidence-*.json"))
    out: list[dict[str, Any]] = []
    for p in paths:
        if since_hours is not None:
            try:
                ts = datetime.fromtimestamp(p.stat().st_mtime, tz=UTC)
            except OSError:
                continue
            cutoff = datetime.now(UTC) - timedelta(hours=since_hours)
            if ts < cutoff:
                continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        if skill is not None and data.get("skill") != skill:
            continue
        out.append(data)
    return out


def _last_scores(trace: dict[str, Any]) -> dict[str, float]:
    iters = trace.get("iterations") or []
    if not iters:
        return {}
    return dict(iters[-1].get("critic", {}).get("scores") or {})


def _by_skill(traces: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    bucket: dict[str, list[dict[str, Any]]] = {}
    for t in traces:
        skill = t.get("skill", "unknown")
        bucket.setdefault(skill, []).append(t)
    return bucket


def _recurring_pattern_count(skill: str, root: Path) -> int:
    """Count failure-pattern rows in docs/failure-patterns.md that target `skill`.

    Counts rows whose first column equals `skill` and whose `Count` field
    is > 0 (recurring == active). Returns 0 when the file is missing or
    has no rows for this skill.
    """
    path = root / "docs" / "failure-patterns.md"
    if not path.is_file():
        return 0
    total = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue
        if cells[0] != skill:
            continue
        try:
            total += int(cells[5])
        except ValueError:
            continue
    return total


def _drift_summary(traces: list[dict[str, Any]]) -> dict[str, int]:
    """Compute a coarse drift signal: degraded-dim count per skill.

    A dimension is "degraded" when its last-iteration score is < 0.6 in
    any trace. Returns {skill: degraded_dim_count}.
    """
    result: dict[str, int] = {}
    for t in traces:
        skill = t.get("skill", "unknown")
        scores = _last_scores(t)
        degraded = sum(1 for d in RUBRIC_DIMS if scores.get(d, 1.0) < 0.6)
        result[skill] = result.get(skill, 0) + degraded
    return result


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def compute_components(
    *,
    traces: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    patterns: dict[str, int],
    drift: dict[str, int],
) -> dict[str, float]:
    """Compute the four weighted components for a single skill.

    Args:
        traces:   gcl-trace entries matching this skill
        evidence: evidence-*.json entries matching this skill
        patterns: {skill: recurring_pattern_count} for reflexion
        drift:    {skill: degraded_dim_count} for distribution drift
    """
    if traces:
        pass_n = sum(1 for t in traces if (t.get("final") or {}).get("status") == "PASS")
        gcl_pass_rate = pass_n / len(traces)
    else:
        gcl_pass_rate = 0.0

    if evidence:
        prov_hits = sum(
            1 for r in evidence
            if isinstance(r.get("provenance"), dict)
            and r["provenance"].get("source") in KNOWN_PROVENANCE_SOURCES
        )
        provenance = prov_hits / len(evidence)
    else:
        provenance = 0.0

    # Recurrence component: more recurring failures → lower score.
    # No patterns (or all-zero count) → 1.0 (no recurring failures observed).
    rec_count = sum(patterns.values())
    recurrence = 1.0 - _clamp01(rec_count / RECURRENCE_SATURATION)

    drift_total = sum(drift.values())
    drift_score = 1.0 - _clamp01(drift_total / DRIFT_SATURATION)

    return {
        "gcl_pass_rate": round(_clamp01(gcl_pass_rate), 4),
        "evidence_kernel_provenance": round(_clamp01(provenance), 4),
        "reflexion_failure_recurrence": round(_clamp01(recurrence), 4),
        "distribution_drift_severity": round(_clamp01(drift_score), 4),
    }


def quality_score_from_components(components: dict[str, float]) -> float:
    """Weighted sum of the four components. Returns a value in [0, 1]."""
    total = 0.0
    for name, weight in WEIGHTS.items():
        total += weight * float(components.get(name, 0.0))
    return round(_clamp01(total), 4)


def _aggregate_dim_avg(traces: list[dict[str, Any]]) -> dict[str, float]:
    """Average per-dimension score across this skill's traces (last iter)."""
    sums: dict[str, float] = {d: 0.0 for d in RUBRIC_DIMS}
    counts: dict[str, int] = {d: 0 for d in RUBRIC_DIMS}
    for t in traces:
        scores = _last_scores(t)
        for d in RUBRIC_DIMS:
            v = scores.get(d)
            if v is not None:
                sums[d] += float(v)
                counts[d] += 1
    return {
        d: round(sums[d] / counts[d], 4) if counts[d] else 0.0
        for d in RUBRIC_DIMS
    }


def aggregate_skill_scores(
    root: Path,
    since_hours: int | None = 168,
    threshold: float = UPGRADE_THRESHOLD,
) -> dict[str, Any]:
    """Build the full quality report from disk artifacts."""
    traces = read_traces(root, since_hours=since_hours)
    all_evidence = read_evidence_records(root, since_hours=since_hours)
    drift_map = _drift_summary(traces)

    by_skill_traces = _by_skill(traces)
    by_skill_evidence: dict[str, list[dict[str, Any]]] = {}
    for r in all_evidence:
        skill = r.get("skill", "unknown")
        by_skill_evidence.setdefault(skill, []).append(r)

    skills: dict[str, dict[str, Any]] = {}
    upgrade_signal: list[str] = []

    for skill, skill_traces in sorted(by_skill_traces.items()):
        total = len(skill_traces)
        pass_n = sum(1 for t in skill_traces if (t.get("final") or {}).get("status") == "PASS")
        safety_fail = sum(1 for t in skill_traces if (t.get("final") or {}).get("status") == "SAFETY_FAIL")
        max_iter = sum(1 for t in skill_traces if (t.get("final") or {}).get("status") == "MAX_ITER")
        pass_rate = pass_n / total if total else 0.0

        components = compute_components(
            traces=skill_traces,
            evidence=by_skill_evidence.get(skill, []),
            patterns={skill: _recurring_pattern_count(skill, root)},
            drift={skill: drift_map.get(skill, 0)},
        )
        score = quality_score_from_components(components)
        upgrade = score < threshold
        if upgrade:
            upgrade_signal.append(skill)

        skills[skill] = {
            "total": total,
            "pass": pass_n,
            "safety_fail": safety_fail,
            "max_iter": max_iter,
            "pass_rate": round(pass_rate, 4),
            "dimensions_avg": _aggregate_dim_avg(skill_traces),
            "components": components,
            "quality_score": score,
            "upgrade_signal": upgrade,
        }

    # Skills present only in evidence (no GCL traces) get a placeholder row
    # so evidence-only skills are visible in the report.
    for skill in sorted(by_skill_evidence.keys()):
        if skill in skills:
            continue
        ev_list = by_skill_evidence[skill]
        components = compute_components(
            traces=[],
            evidence=ev_list,
            patterns={skill: _recurring_pattern_count(skill, root)},
            drift={skill: drift_map.get(skill, 0)},
        )
        score = quality_score_from_components(components)
        upgrade = score < threshold
        if upgrade:
            upgrade_signal.append(skill)
        skills[skill] = {
            "total": 0,
            "pass": 0,
            "safety_fail": 0,
            "max_iter": 0,
            "pass_rate": 0.0,
            "dimensions_avg": {d: 0.0 for d in RUBRIC_DIMS},
            "components": components,
            "quality_score": score,
            "upgrade_signal": upgrade,
        }

    total_exec = sum(s["total"] for s in skills.values())
    scores = [s["quality_score"] for s in skills.values()]
    summary = {
        "total_executions": total_exec,
        "skill_count": len(skills),
        "upgrade_skill_count": len(upgrade_signal),
        "avg_quality_score": round(statistics.mean(scores), 4) if scores else 0.0,
    }

    return {
        "version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "window": {"trace_count": len(traces), "since_hours": since_hours},
        "by_skill": skills,
        "upgrade_signal": sorted(upgrade_signal),
        "summary": summary,
    }


def build_report(root: Path, since_hours: int | None = 168) -> dict[str, Any]:
    """Build the quality report. Convenience wrapper for tests/CLI."""
    return aggregate_skill_scores(root, since_hours=since_hours)


def persist_report(root: Path, report: dict[str, Any]) -> Path:
    """Write the report to audit-results/skill-quality-<ts>.json."""
    out_dir = root / "audit-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"skill-quality-{ts}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path,
                        default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON report to stdout")
    parser.add_argument("--since-hours", type=int, default=168,
                        help="Window for trace/evidence mtime filter (default: 168 = 7d)")
    parser.add_argument("--threshold", type=float, default=UPGRADE_THRESHOLD,
                        help=f"Upgrade-signal threshold (default: {UPGRADE_THRESHOLD})")
    parser.add_argument("--persist", action="store_true",
                        help="Also write audit-results/skill-quality-<ts>.json")
    # Accept `score` as a no-op positional (validate_local.py wires
    # `scripts/skill_quality_score.py score --json`). Unknown positionals
    # (e.g. legacy subcommand names) are tolerated via parse_known_args.
    args, _unknown = parser.parse_known_args(argv)

    report = aggregate_skill_scores(
        args.root, since_hours=args.since_hours, threshold=args.threshold,
    )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.persist:
        out = persist_report(args.root, report)
        if not args.json:
            print(f"Persisted: {out.relative_to(args.root)}")

    # Always print a short summary to stderr (helps live use without --json).
    summary = report["summary"]
    print(
        f"quality_score: {summary['avg_quality_score']:.4f} "
        f"skills={summary['skill_count']} "
        f"upgrade={summary['upgrade_skill_count']} "
        f"executions={summary['total_executions']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())