from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

METRICS_JSONL = Path.cwd() / ".runtime" / "metrics" / "metrics.jsonl"
LEGACY_HEALTH_JSONL = Path.cwd() / ".runtime" / "health" / "skill-metrics.jsonl"


def _load_records() -> list[dict]:
    """Read structured metric stream, falling back to legacy health jsonl."""
    records: list[dict] = []
    if METRICS_JSONL.exists():
        with METRICS_JSONL.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    if not records and LEGACY_HEALTH_JSONL.exists():
        with LEGACY_HEALTH_JSONL.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    e = json.loads(line)
                    records.append(
                        {
                            "kind": "span",
                            "run_id": e.get("trace_id"),
                            "step_id": e.get("skill"),
                            "status": "success" if e.get("status") == "ok" else "fail",
                            "duration_ms": e.get("duration_ms", 0),
                            "error_code": e.get("error_code"),
                            "ts": e.get("ts"),
                        }
                    )
    return records


def _within_days(ts: str | None, days: int) -> bool:
    if not ts:
        return True
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt >= datetime.now(timezone.utc) - timedelta(days=days)


def skill_success_rate(skill: str, days: int = 7, by_skill: bool = False) -> float:
    """Success rate for a step (per-step_id, default) or the whole copilot skill.

    `by_skill=False` (default) matches on `step_id` for per-step breakdowns —
    this is the primary use case for the query API. `by_skill=True` returns the
    global copilot success ratio (every success belongs to qcloud-copilot per spec).
    """
    spans = [
        r for r in _load_records() if r.get("kind") == "span" and _within_days(r.get("ts"), days)
    ]
    if by_skill:
        if not spans:
            return 0.0
        ok = sum(1 for r in spans if r.get("status") == "success")
        return ok / len(spans)
    matched = [r for r in spans if r.get("step_id") == skill]
    if not matched:
        return 0.0
    ok = sum(1 for r in matched if r.get("status") == "success")
    return ok / len(matched)


def p_latency(op: str, p: int = 99, days: int = 7) -> int:
    durations = [
        int(r["duration_ms"])
        for r in _load_records()
        if r.get("kind") == "span"
        and r.get("step_id") == op
        and r.get("duration_ms")
        and _within_days(r.get("ts"), days)
    ]
    if not durations:
        return 0
    durations.sort()
    # nearest-rank percentile
    rank = max(0, min(len(durations) - 1, (p * len(durations) + 99) // 100 - 1))
    return durations[rank]


def gate_decision_rate(gate: str) -> dict[str, float]:
    gates = [r for r in _load_records() if r.get("kind") == "gate" and r.get("gate") == gate]
    if not gates:
        return {}
    total = len(gates)
    rates: dict[str, float] = {}
    for r in gates:
        decision = r.get("decision", "unknown")
        rates[decision] = rates.get(decision, 0.0) + 1.0 / total
    return rates


def top_failed_operations(days: int = 7, limit: int = 10) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for r in _load_records():
        # Only count step-execution failures; gate rejections (source="gate") are
        # copilot-scoped rejections, not per-step failures (Critic A major fix).
        if (
            r.get("kind") == "span"
            and r.get("status") == "fail"
            and r.get("source", "step") == "step"
            and _within_days(r.get("ts"), days)
        ):
            op = r.get("step_id") or "unknown"
            counts[op] = counts.get(op, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:limit]
