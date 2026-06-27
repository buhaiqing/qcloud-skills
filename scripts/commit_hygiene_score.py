#!/usr/bin/env python3
"""Score commit-hygiene trial entries.

Pure functions over jsonl records. No I/O, no side effects.
Inputs are dicts shaped like:
    {"commit": "abc123", "ts": "2026-06-27T...", "verdict": "ok"|"partial"|"red-line-stop",
     "products": ["cvm"], "files_modified": 3, "files_added": 1, "reason": "..."}

Output is a dict with M1 / M2 metrics:
    {"m1_violations": int, "m2_total": int, "m2_rollback": int, "m2_rate": float}
"""

from __future__ import annotations

from typing import Any


def is_m1_violation(record: dict[str, Any]) -> bool:
    """M1 = red-line-stop verdict == hard-stop violation."""
    return record.get("verdict") == "red-line-stop"


def is_m2_rollback(record: dict[str, Any]) -> bool:
    """M2 = operator 👎 OR partial verdict OR red-line-stop.

    red-line-stop counts because by definition the agent paused a commit
    that should not have been staged — that's a granularity / judgment
    failure regardless of the safety reason.
    """
    verdict = record.get("verdict", "")
    return verdict in ("partial", "rollback", "red-line-stop")


def score_window(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate M1 / M2 over a window of records."""
    m1 = sum(1 for r in records if is_m1_violation(r))
    m2_total = len(records)
    m2_rollback = sum(1 for r in records if is_m2_rollback(r))
    m2_rate = (m2_rollback / m2_total) if m2_total else 0.0
    return {
        "m1_violations": m1,
        "m2_total": m2_total,
        "m2_rollback": m2_rollback,
        "m2_rate": round(m2_rate, 4),
    }


def recommend(metrics: dict[str, Any], min_commits: int = 5) -> str:
    """Return one of: 'promote' | 'extend' | 'rollback' | 'observe'."""
    if metrics["m1_violations"] > 0:
        return "rollback"
    if metrics["m2_total"] < min_commits:
        return "observe"
    if metrics["m2_rate"] <= 0.20:
        return "promote"
    return "extend"