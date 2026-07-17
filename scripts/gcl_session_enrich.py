#!/usr/bin/env python3
"""Session log → trajectory enrichment: tool efficiency + agent role from pi session files.

Reads pi session logs (JSONL) and enriches gcl-trace analysis with:
1. Tool call counts per role (bash/read/edit/subagent/wait)
2. Subagent orchestration depth
3. Total tool calls per trace

Usage:
  python3 scripts/gcl_session_enrich.py [--since-hours 720]
  python3 scripts/gcl_session_enrich.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TOOL_CATEGORIES = {
    "read_only": {"read", "grep", "find", "ls", "hypa_read", "hypa_grep", "hypa_find", "hypa_ls"},
    "write": {"edit", "write"},
    "subagent": {"subagent", "wait"},
    "bash": {"bash", "hypa_shell"},
    "safety": {"codegraph_codegraph_explore"},
}

RUBRIC_DIMS = ("correctness", "safety", "idempotency", "traceability", "spec_compliance")


def _extract_tool_calls(events: list[dict]) -> list[dict[str, Any]]:
    """Extract tool calls from session events."""
    calls = []
    for e in events:
        if e.get("type") != "message":
            continue
        msg = e.get("message", {})
        if msg.get("role") != "assistant":
            continue
        for c in msg.get("content", []):
            if isinstance(c, dict) and c.get("type") == "toolCall":
                args = c.get("arguments", {})
                calls.append({
                    "name": c.get("name"),
                    "tool": c.get("name", "").split("_")[0] if c.get("name") else "",
                    "subagent": args.get("agent") if c.get("name") == "subagent" else None,
                    "async": args.get("async", False),
                })
    return calls


def _extract_session_metadata(events: list[dict]) -> dict[str, Any]:
    """Extract session metadata: turns, tool counts, subagent calls."""
    calls = _extract_tool_calls(events)
    tool_counts = {}
    for c in calls:
        n = c["name"]
        tool_counts[n] = tool_counts.get(n, 0) + 1

    subagents = [c for c in calls if c["name"] == "subagent"]
    async_subs = [s for s in subagents if s.get("async")]
    sync_subs = [s for s in subagents if not s.get("async")]

    # Orchestration depth: count subagent calls within subagent events (nested)
    # Simple proxy: number of subagent calls
    sub_depth = len(subagents)

    # Wait calls (parent waiting on children)
    wait_calls = sum(1 for c in calls if c["name"] == "wait")

    # Turn count
    assistant_msgs = sum(
        1 for e in events
        if e.get("type") == "message" and e.get("message", {}).get("role") == "assistant"
    )

    # Model info
    model_changes = [e for e in events if e.get("type") == "model_change"]
    models = list({e.get("modelId") for e in model_changes if e.get("modelId")})

    return {
        "total_tool_calls": len(calls),
        "tool_counts": tool_counts,
        "tool_counts_by_category": {
            cat: sum(tool_counts.get(t, 0) for t in tools)
            for cat, tools in TOOL_CATEGORIES.items()
        },
        "subagent_count": len(subagents),
        "async_subagent_count": len(async_subs),
        "sync_subagent_count": len(sync_subs),
        "subagent_depth": sub_depth,
        "wait_count": wait_calls,
        "assistant_turns": assistant_msgs,
        "models": models,
    }


def _score_trajectory_shape(traces: list[dict]) -> list[dict[str, Any]]:
    """Classify each trajectory into a shape type based on score patterns.

    Shape types:
    - fast_pass:       PASS in first iteration
    - slow_converge:   PASS after retry (≥2 iters), monotonically improving
    - oscillating:     oscillation_count > 0
    - early_fail:       SAFETY_FAIL/MAX_ITER in first 2 iters
    - persistent_fail: SAFETY_FAIL/MAX_ITER after oscillation
    - plateau:         scores stabilize but never reach PASS
    """
    def all_iter_scores(t: dict) -> list[dict]:
        return [dict(it.get("critic", {}).get("scores", {})) for it in t.get("iterations", [])]

    def oscillation_count(t: dict) -> int:
        scores = all_iter_scores(t)
        if len(scores) < 2:
            return 0
        total = 0
        for dim in RUBRIC_DIMS:
            vals = [s.get(dim, 0) or 0 for s in scores]
            for i in range(1, len(vals)):
                prev = vals[i-1] - vals[i-2] if i > 1 else 0
                cur = vals[i] - vals[i-1]
                if prev and cur and prev * cur < 0:
                    total += 1
        return total

    def is_monotonic(t: dict) -> bool:
        scores = all_iter_scores(t)
        if len(scores) < 2:
            return True
        for dim in RUBRIC_DIMS:
            vals = [s.get(dim, 0) or 0 for s in scores]
            for i in range(1, len(vals)):
                if vals[i] < vals[i-1]:
                    return False
        return True

    results = []
    for t in traces:
        iters = t.get("iterations", [])
        n = len(iters)
        status = (t.get("final") or {}).get("status", "UNKNOWN")
        osc = oscillation_count(t)
        mono = is_monotonic(t)

        if status == "PASS" and n == 1:
            shape = "fast_pass"
        elif status == "PASS" and n > 1 and osc > 0:
            shape = "oscillating"
        elif status == "PASS" and n > 1 and mono:
            shape = "slow_converge"
        elif status == "SAFETY_FAIL" and n <= 2:
            shape = "early_fail"
        elif status == "SAFETY_FAIL" and n > 2:
            shape = "persistent_fail"
        elif status == "MAX_ITER":
            shape = "plateau"
        else:
            shape = "unknown"

        results.append({
            "skill": t.get("skill"),
            "status": status,
            "shape": shape,
            "oscillation_count": osc,
            "is_monotonic": mono,
            "iter_count": n,
        })
    return results


def _cross_skill_benchmark(traces: list[dict]) -> dict[str, Any]:
    """Benchmark quality metrics grouped by skill family.

    Skill families:
    - storage:   cos, cbs
    - compute:    cvm, tke
    - database:  cdb, postgres, mongodb, redis, es
    - network:   clb, vpc, ccn, vpn, dc
    - infra:      monitor, cls, ckafka, scf, ssl, cdn, cam
    - ops:        finops, proactive-inspection, aiops-diagnosis, well-architected-review
    """
    FAMILIES = {
        "storage":    ["qcloud-cos-ops", "qcloud-cbs-ops"],
        "compute":   ["qcloud-cvm-ops", "qcloud-tke-ops"],
        "database":  ["qcloud-cdb-ops", "qcloud-postgres-ops", "qcloud-mongodb-ops", "qcloud-redis-ops", "qcloud-es-ops"],
        "network":   ["qcloud-clb-ops", "qcloud-vpc-ops", "qcloud-ccn-ops", "qcloud-vpn-ops", "qcloud-dc-ops"],
        "infra":     ["qcloud-monitor-ops", "qcloud-cls-ops", "qcloud-ckafka-ops", "qcloud-scf-ops", "qcloud-ssl-ops", "qcloud-cdn-ops", "qcloud-cam-ops"],
        "ops":       ["qcloud-finops-ops", "qcloud-proactive-inspection", "qcloud-aiops-diagnosis", "qcloud-well-architected-review"],
    }

    def skill_family(skill: str) -> str:
        for family, skills in FAMILIES.items():
            if skill in skills:
                return family
        return "other"

    # Per-family aggregation
    family_stats: dict[str, dict[str, Any]] = {}
    for t in traces:
        fam = skill_family(t.get("skill", "unknown"))
        status = (t.get("final") or {}).get("status", "UNKNOWN")
        n = len(t.get("iterations", []))

        family_stats.setdefault(fam, {"total": 0, "PASS": 0, "SAFETY_FAIL": 0, "MAX_ITER": 0, "total_iters": 0})
        family_stats[fam]["total"] += 1
        if status in family_stats[fam]:
            family_stats[fam][status] += 1
        family_stats[fam]["total_iters"] += n

    # Per-family summary
    summary = {}
    for fam, stats in family_stats.items():
        total = stats["total"]
        pass_rate = stats["PASS"] / total if total else 0
        avg_iters = stats["total_iters"] / total if total else 0
        summary[fam] = {
            "total": total,
            "pass_rate": round(pass_rate, 4),
            "avg_iters": round(avg_iters, 2),
            "pass_count": stats["PASS"],
            "safety_fail_count": stats["SAFETY_FAIL"],
            "max_iter_count": stats["MAX_ITER"],
        }

    # Individual skill stats
    skill_stats = {}
    for t in traces:
        skill = t.get("skill", "unknown")
        status = (t.get("final") or {}).get("status", "UNKNOWN")
        n = len(t.get("iterations", []))
        skill_stats.setdefault(skill, {"total": 0, "PASS": 0, "SAFETY_FAIL": 0, "MAX_ITER": 0, "total_iters": 0})
        skill_stats[skill]["total"] += 1
        if status in skill_stats[skill]:
            skill_stats[skill][status] += 1
        skill_stats[skill]["total_iters"] += n

    skill_summary = {}
    for skill, stats in skill_stats.items():
        total = stats["total"]
        skill_summary[skill] = {
            "total": total,
            "pass_rate": round(stats["PASS"] / total, 4) if total else 0,
            "avg_iters": round(stats["total_iters"] / total, 2) if total else 0,
        }

    return {
        "by_family": summary,
        "by_skill": skill_summary,
        "families": list(FAMILIES.keys()),
    }


def _load_session_events(session_path: Path) -> list[dict]:
    """Load events from a pi session JSONL file."""
    try:
        lines = [line for line in session_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return [json.loads(line) for line in lines]
    except Exception:
        return []


def _find_session_for_trace(trace: dict, sessions_dir: Path, hours_tolerance: int = 2) -> Path | None:
    """Find the pi session file that corresponds to a gcl-trace.

    Heuristic: match by skill + approximate timestamp.
    Session dirs are named with timestamps.
    """
    skill = trace.get("skill", "")
    # Session dir timestamps are embedded in the path
    # We scan recent session dirs and check skill in events
    sessions = sorted(sessions_dir.glob("*qcloud-skills*/**/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    for sp in sessions[:50]:  # check most recent 50
        # Simple heuristic: trace is recent if session file mtime is close to now
        events = _load_session_events(sp)
        # Check if session contains subagent calls for this skill
        for e in events:
            if e.get("type") == "message":
                msg = e.get("message", {})
                content = str(msg.get("content", ""))
                if skill in content or f"qcloud-{skill.split('-')[1]}" in content:
                    return sp
    return None


def collect_session_metrics(root: Path, since_hours: int) -> dict[str, Any]:
    """Collect tool efficiency metrics from pi session logs."""
    sessions_dir = Path.home() / ".pi/agent/sessions"
    if not sessions_dir.exists():
        return {"error": "sessions dir not found", "metrics": {}}

    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)

    # Find recent qcloud-skills session dirs
    skill_sessions = []
    for sd in sessions_dir.glob("*qcloud-skills*"):
        mtime = datetime.fromtimestamp(sd.stat().st_mtime, tz=timezone.utc)
        if mtime >= cutoff:
            for sp in sd.rglob("*.jsonl"):
                skill_sessions.append(sp)

    metrics: dict[str, Any] = {}
    for sp in skill_sessions[:100]:  # cap at 100 most recent
        events = _load_session_events(sp)
        if not events:
            continue
        meta = _extract_session_metadata(events)
        # Use session dir name as key
        session_key = sp.parent.name + "/" + sp.stem
        metrics[session_key] = meta

    return metrics


def analyze_enrichment(traces: list[dict], root: Path, since_hours: int) -> dict[str, Any]:
    """Compute all enrichment metrics."""
    shapes = _score_trajectory_shape(traces)
    benchmark = _cross_skill_benchmark(traces)
    session_metrics = collect_session_metrics(root, since_hours)

    # Shape distribution
    shape_counts: dict[str, int] = {}
    for s in shapes:
        shape_counts[s["shape"]] = shape_counts.get(s["shape"], 0) + 1

    # Per-shape metrics
    shape_metrics = {}
    for shape in set(s["shape"] for s in shapes):
        matching = [s for s in shapes if s["shape"] == shape]
        shape_metrics[shape] = {
            "count": len(matching),
            "rate": round(len(matching) / len(shapes), 4) if shapes else 0,
            "avg_oscillation": round(sum(s["oscillation_count"] for s in matching) / len(matching), 3),
        }



    return {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window": {"trace_count": len(traces)},
        "trajectory_shapes": {
            "distribution": shape_counts,
            "metrics": shape_metrics,
        },
        "cross_skill_benchmark": benchmark,
        "tool_efficiency": {
            "source": "pi_session_logs",
            "sessions_analyzed": len(session_metrics.get("metrics", {})) if isinstance(session_metrics, dict) else 0,
            "sample_metrics": dict(list(session_metrics.items())[:10]) if isinstance(session_metrics, dict) else {},
        } if isinstance(session_metrics, dict) else {"error": session_metrics.get("error", "unknown")},
    }


def self_verify() -> bool:
    """Self-check with synthetic data."""
    traces = [
        {
            "skill": "qcloud-cvm-ops",
            "iterations": [
                {"decision": "PASS", "critic": {"scores": {"correctness": 1.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 1.0}}},
            ],
            "final": {"status": "PASS", "iter": 1},
        },
        {
            "skill": "qcloud-cos-ops",
            "iterations": [
                {"decision": "RETRY", "critic": {"scores": {"correctness": 0.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 0.0}}},
                {"decision": "PASS", "critic": {"scores": {"correctness": 1.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 1.0}}},
            ],
            "final": {"status": "PASS", "iter": 2},
        },
        {
            "skill": "qcloud-vpc-ops",
            "iterations": [
                {"decision": "SAFETY_FAIL", "critic": {"scores": {"correctness": 0.0, "safety": 0.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 0.0}}},
            ],
            "final": {"status": "SAFETY_FAIL", "iter": 1},
        },
    ]

    shapes = _score_trajectory_shape(traces)
    shape_names = {s["shape"] for s in shapes}
    assert "fast_pass" in shape_names, f"expected fast_pass, got {shape_names}"
    assert "slow_converge" in shape_names, f"expected slow_converge, got {shape_names}"
    assert "early_fail" in shape_names, f"expected early_fail, got {shape_names}"

    benchmark = _cross_skill_benchmark(traces)
    assert "by_family" in benchmark
    assert "by_skill" in benchmark
    assert "compute" in benchmark["by_family"]

    # Oscillation detection
    osc_trace = {
        "skill": "qcloud-test",
        "iterations": [
            {"decision": "RETRY", "critic": {"scores": {"correctness": 0.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 0.0}}},
            {"decision": "RETRY", "critic": {"scores": {"correctness": 1.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 1.0}}},
            {"decision": "RETRY", "critic": {"scores": {"correctness": 0.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 0.0}}},
            {"decision": "PASS", "critic": {"scores": {"correctness": 1.0, "safety": 1.0, "idempotency": 0.5, "traceability": 1.0, "spec_compliance": 1.0}}},
        ],
        "final": {"status": "PASS", "iter": 4},
    }
    shapes2 = _score_trajectory_shape([osc_trace])
    assert shapes2[0]["shape"] == "oscillating"
    assert shapes2[0]["oscillation_count"] > 0

    print("Self-verify: all assertions passed ✓")
    return True


def _load_traces(root: Path, since_hours: int | None) -> list[dict]:
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

    result = analyze_enrichment(traces, args.root, args.since_hours)

    shapes = result["trajectory_shapes"]
    print(f"\nTrajectory enrichment summary ({len(traces)} traces):")
    print("\n  Trajectory shapes:")
    for shape, m in shapes["metrics"].items():
        print(f"    {shape}: {m['count']} ({m['rate']:.1%}), avg_oscillation={m['avg_oscillation']:.2f}")

    print("\n  Cross-skill benchmark:")
    for fam, m in result["cross_skill_benchmark"]["by_family"].items():
        print(f"    {fam}: pass_rate={m['pass_rate']:.1%}, avg_iters={m['avg_iters']:.2f}")

    te = result["tool_efficiency"]
    if "error" in te:
        print(f"\n  Tool efficiency: {te['error']}")
    else:
        print(f"\n  Tool efficiency: {te['sessions_analyzed']} sessions analyzed")

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
