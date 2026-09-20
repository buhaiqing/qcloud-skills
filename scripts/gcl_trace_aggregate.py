#!/usr/bin/env python3
"""Aggregate GCL trace files into a quality summary (AGENTS.md GCL Phase 3).

Usage:
  python3 scripts/gcl_trace_aggregate.py
  python3 scripts/gcl_trace_aggregate.py --input audit-results/gcl-trace-*.json
  python3 scripts/gcl_trace_aggregate.py --since-hours 24
  python3 scripts/gcl_trace_aggregate.py --cross-skill --run-id <id> [--since ISO8601]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

FINAL_STATUSES = ("PASS", "SAFETY_FAIL", "MAX_ITER")
RUBRIC_DIMS = ("correctness", "safety", "idempotency", "traceability", "spec_compliance")

# --- F14: Critic provenance (`critic._mode`, written by gcl_runner.py) ---------
# `gcl_runner.py` tags every Critic payload with `_mode`:
#   "llm-builtin"                — real LLM Critic scores
#   "structural-only"            — CI/local smoke rule-based critic (--structural-critic-only)
#   "structural-only-fallback"   — LLM Critic failed (timeout/ratelimit/bad JSON); rule scores
#                                  were substituted and the run must NOT count as LLM-scored
#   "missing"                    — legacy trace with no `_mode` at all
CRITIC_MODE_MISSING = "missing"
STRUCTURAL_FALLBACK_MODE = "structural-only-fallback"
KNOWN_CRITIC_MODES = ("llm-builtin", "structural-only", STRUCTURAL_FALLBACK_MODE, CRITIC_MODE_MISSING)

# Shared threshold (assets/shared/thresholds.json). A ratio above this means the
# quality summary is dominated by rule-based scores and must not be read as an
# LLM-Critic verdict.
STRUCTURAL_FALLBACK_MAX_RATIO_KEY = "gcl_structural_fallback_max_ratio"
# Fail-closed (L21): missing/unreadable/invalid threshold → 0.0, i.e. ANY fallback
# run breaches. Warning goes to stderr; a broken config must never crash the gate.
STRUCTURAL_FALLBACK_MAX_RATIO_FAIL_CLOSED = 0.0


def parse_trace(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"WARN: skip {path}: {e}", file=sys.stderr)
        return None
    if "skill" not in data or "final" not in data:
        print(f"WARN: skip {path}: missing skill/final", file=sys.stderr)
        return None
    return data


def last_scores(trace: dict[str, Any]) -> dict[str, float]:
    iters = trace.get("iterations") or []
    if not iters:
        return {}
    return dict(iters[-1].get("critic", {}).get("scores") or {})


def critic_mode(trace: dict[str, Any]) -> str:
    """Critic provenance mode of a trace's final iteration (F14).

    Reads ``iterations[-1].critic._mode`` — the field written by
    ``gcl_runner.py``. Legacy traces without the field return
    ``CRITIC_MODE_MISSING`` so they are visible rather than silently
    bucketed as LLM-scored.
    """
    iters = trace.get("iterations") or []
    if not iters:
        return CRITIC_MODE_MISSING
    critic = iters[-1].get("critic")
    if not isinstance(critic, dict):
        return CRITIC_MODE_MISSING
    mode = critic.get("_mode")
    if isinstance(mode, str) and mode:
        return mode
    return CRITIC_MODE_MISSING


def _count_critic_modes(traces: list[dict[str, Any]]) -> dict[str, int]:
    """Bucket traces by Critic mode; known modes always present, even at 0."""
    counts: dict[str, int] = {mode: 0 for mode in KNOWN_CRITIC_MODES}
    for t in traces:
        mode = critic_mode(t)
        counts[mode] = counts.get(mode, 0) + 1
    return counts


def load_fallback_max_ratio(root: Path) -> tuple[float, bool]:
    """Read ``gcl_structural_fallback_max_ratio`` from shared thresholds.

    Returns ``(ratio, configured)``. Missing file/key or an invalid value
    (non-numeric, bool, or outside [0, 1]) is fail-closed: ``(0.0, False)``
    with a stderr warning — never an exception (F14 / L21).
    """
    fail_closed = STRUCTURAL_FALLBACK_MAX_RATIO_FAIL_CLOSED
    path = root / "assets" / "shared" / "thresholds.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(
            f"WARN: cannot read {path}: {e}; {STRUCTURAL_FALLBACK_MAX_RATIO_KEY}"
            f" fails closed to {fail_closed} (any structural fallback run breaches)",
            file=sys.stderr,
        )
        return fail_closed, False
    if not isinstance(data, dict):
        print(
            f"WARN: {path} is not a JSON object; {STRUCTURAL_FALLBACK_MAX_RATIO_KEY}"
            f" fails closed to {fail_closed}",
            file=sys.stderr,
        )
        return fail_closed, False
    value = data.get(STRUCTURAL_FALLBACK_MAX_RATIO_KEY)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        print(
            f"WARN: {STRUCTURAL_FALLBACK_MAX_RATIO_KEY} missing or non-numeric in {path}"
            f" (got {value!r}); fails closed to {fail_closed}",
            file=sys.stderr,
        )
        return fail_closed, False
    ratio = float(value)
    if not 0.0 <= ratio <= 1.0:
        print(
            f"WARN: {STRUCTURAL_FALLBACK_MAX_RATIO_KEY}={ratio} outside [0, 1];"
            f" fails closed to {fail_closed}",
            file=sys.stderr,
        )
        return fail_closed, False
    return ratio, True


def aggregate(traces: list[dict[str, Any]], root: Path | None = None) -> dict[str, Any]:
    by_skill: dict[str, dict[str, Any]] = {}
    totals = {s: 0 for s in FINAL_STATUSES}
    totals["total_runs"] = len(traces)
    score_sums: dict[str, float] = {d: 0.0 for d in RUBRIC_DIMS}
    score_count = 0

    for t in traces:
        skill = t.get("skill", "unknown")
        status = (t.get("final") or {}).get("status", "UNKNOWN")
        if status in totals:
            totals[status] += 1

        bucket = by_skill.setdefault(
            skill,
            {"total": 0, "PASS": 0, "SAFETY_FAIL": 0, "MAX_ITER": 0, "avg_iterations": 0.0},
        )
        bucket["total"] += 1
        if status in bucket:
            bucket[status] += 1
        iters = len(t.get("iterations") or [])
        bucket["avg_iterations"] = (
            (bucket["avg_iterations"] * (bucket["total"] - 1) + iters) / bucket["total"]
        )

        scores = last_scores(t)
        if scores:
            score_count += 1
            for d in RUBRIC_DIMS:
                score_sums[d] += float(scores.get(d, 0))

    pass_rate = totals["PASS"] / totals["total_runs"] if totals["total_runs"] else 0.0
    avg_scores = {
        d: round(score_sums[d] / score_count, 3) if score_count else None for d in RUBRIC_DIMS
    }

    # F14: surface rule-based Critic substitutions instead of letting them pass
    # as real Critic scores. Existing fields above are unchanged.
    mode_counts = _count_critic_modes(traces)
    fallback_runs = mode_counts.get(STRUCTURAL_FALLBACK_MODE, 0)
    fallback_ratio = fallback_runs / totals["total_runs"] if totals["total_runs"] else 0.0
    max_ratio, threshold_configured = load_fallback_max_ratio(
        root if root is not None else Path(__file__).resolve().parents[1]
    )
    breach = fallback_ratio > max_ratio
    if breach:
        print(
            f"ALERT: structural critic fallback {fallback_runs}/{totals['total_runs']} runs"
            f" ({fallback_ratio:.4f}) > {STRUCTURAL_FALLBACK_MAX_RATIO_KEY} {max_ratio}"
            " — summary scores are rule-based, not LLM-Critic scores",
            file=sys.stderr,
        )

    return {
        "version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "window": {"trace_count": totals["total_runs"]},
        "totals": totals,
        "pass_rate": round(pass_rate, 4),
        "avg_rubric_scores": avg_scores,
        "by_skill": by_skill,
        "critic_mode_counts": mode_counts,
        "structural_fallback_runs": fallback_runs,
        "structural_fallback_ratio": round(fallback_ratio, 4),
        "structural_fallback_max_ratio": max_ratio,
        "structural_fallback_breach": breach,
        "structural_fallback_threshold_configured": threshold_configured,
        "trace_files": [t.get("_source_path") for t in traces],
    }


def collect_paths(root: Path, inputs: list[str] | None, since_hours: int | None) -> list[Path]:
    if inputs:
        out: list[Path] = []
        for pattern in inputs:
            out.extend(sorted(root.glob(pattern) if "*" in pattern else [Path(pattern)]))
        return [p for p in out if p.is_file()]

    audit = root / "audit-results"
    if not audit.is_dir():
        return []
    paths = sorted(audit.glob("gcl-trace-*.json"))
    if since_hours is None:
        return paths
    cutoff = datetime.now(UTC) - timedelta(hours=since_hours)
    filtered = []
    for p in paths:
        if datetime.fromtimestamp(p.stat().st_mtime, tz=UTC) >= cutoff:
            filtered.append(p)
    return filtered


def persist_summary(root: Path, summary: dict[str, Any]) -> Path:
    out_dir = root / "audit-results"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"gcl-quality-summary-{ts}.json"
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _span_start_time(span: dict[str, Any]) -> str | None:
    """Return span start_time as ISO8601 string, or None if absent."""
    v = span.get("start_time")
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v, tz=UTC).isoformat()
    return str(v)


def cross_skill_chain(root: Path, run_id: str, since: str | None = None) -> dict[str, Any]:
    """Phase 1.4 — read spans.jsonl for a run, build parent-child chain.

    Args:
        root: Project root.
        run_id: Run id to inspect.
        since: ISO8601 timestamp; if set, filter out spans with start_time < since.

    Output:

    * ``chain``: list of nodes with parent_span_id + span_id + skill + status
    * ``skills_invoked``: ordered skill sequence (delegation aware)
    * ``total_duration_ms``: wall-clock duration of the run
    * ``delegations``: list of {from_skill, to_skill, error_code}

    Used by ``gcl_trace_aggregate --cross-skill --run-id X [--since ISO8601]``
    to surface the cross-skill call DAG for an end-to-end run.
    """
    spans_path = root / ".runtime" / "traces" / run_id / "spans.jsonl"
    if not spans_path.exists():
        return {"run_id": run_id, "error": "spans.jsonl not found"}
    spans: list[dict[str, Any]] = []
    for line in spans_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            spans.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    # Filter by start_time when --since is set.
    if since is not None:
        spans = [
            s for s in spans
            if (_span_start_time(s) or "") >= since
        ]

    # Order by start_time when available; fall back to insertion order.
    spans.sort(key=lambda s: s.get("start_time", ""))
    skills_invoked: list[str] = []
    delegations: list[dict[str, Any]] = []
    total_duration = 0
    for s in spans:
        skill = s.get("skill") or "?"
        if not skills_invoked or skills_invoked[-1] != skill:
            skills_invoked.append(skill)
        if s.get("delegate_to"):
            delegations.append({
                "from_skill": skill,
                "to_skill": s["delegate_to"],
                "error_code": s.get("error_code"),
                "span_id": s.get("span_id"),
            })
        total_duration += int(s.get("duration_ms") or 0)
    return {
        "run_id": run_id,
        "span_count": len(spans),
        "skills_invoked": skills_invoked,
        "delegations": delegations,
        "total_duration_ms": total_duration,
        "chain": [
            {
                "span_id": s.get("span_id"),
                "parent_span_id": s.get("parent_span_id"),
                "skill": s.get("skill"),
                "operation": s.get("operation"),
                "status": s.get("status"),
                "duration_ms": s.get("duration_ms"),
                "error_code": s.get("error_code"),
                "delegate_to": s.get("delegate_to"),
            }
            for s in spans
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--input", nargs="*", help="Trace file(s) or glob under --root")
    parser.add_argument("--since-hours", type=int, default=None, help="Only traces modified within N hours")
    # Phase 1.4 — cross-skill DAG view for a specific run.
    parser.add_argument("--cross-skill", action="store_true",
                        help="Print the cross-skill delegation chain for --run-id")
    parser.add_argument("--run-id", type=str, default=None,
                        help="Run id to inspect with --cross-skill")
    parser.add_argument("--since", type=str, default=None,
                        help="ISO8601 timestamp; filter spans with start_time < since (cross-skill only)")
    args = parser.parse_args()

    if args.cross_skill:
        if not args.run_id:
            print("ERROR: --cross-skill requires --run-id", file=sys.stderr)
            return 2
        chain = cross_skill_chain(args.root, args.run_id, since=args.since)
        print(json.dumps(chain, indent=2, ensure_ascii=False))
        return 0

    paths = collect_paths(args.root, args.input, args.since_hours)
    if not paths:
        print("No gcl-trace files found.", file=sys.stderr)
        return 1

    traces: list[dict[str, Any]] = []
    for p in paths:
        t = parse_trace(p)
        if t:
            t["_source_path"] = str(p.relative_to(args.root))
            traces.append(t)

    if not traces:
        print("No valid traces parsed.", file=sys.stderr)
        return 1

    summary = aggregate(traces, root=args.root)
    out = persist_summary(args.root, summary)
    print(json.dumps({
        "summary_path": str(out),
        "pass_rate": summary["pass_rate"],
        "total_runs": summary["totals"]["total_runs"],
        "structural_fallback_runs": summary["structural_fallback_runs"],
        "structural_fallback_breach": summary["structural_fallback_breach"],
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
