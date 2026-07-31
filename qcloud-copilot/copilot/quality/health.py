from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from copilot.observ import ObservableSink, Span

SKILL_HEALTH_FILE = Path.cwd() / ".runtime" / "health" / "skill-metrics.jsonl"


def record_health(
    skill: str,
    operation: str,
    status: str,
    duration_ms: int,
    trace_id: str,
    error_code: str | None = None,
    source: str = "step",
) -> None:
    """Append a skill-health event (backward-compatible jsonl) and emit a span.

    `error_code` is the real failure signal (gate name or step error token);
    previously hardcoded to None so failures were invisible (O4).

    `source` distinguishes a step execution ("step") from a copilot-scoped gate
    rejection ("gate"); callers must pass it explicitly so a step failure is
    never mislabeled as a gate rejection.
    """
    SKILL_HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "ts": datetime.now(UTC).isoformat(),
        "skill": skill,
        "operation": operation,
        "status": status,
        "duration_ms": duration_ms,
        "trace_id": trace_id,
        "error_code": error_code,
    }
    with SKILL_HEALTH_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    # Only gate rejections (source="gate") need a span here: a step execution's
    # span is already emitted by dispatcher._emit_span (keyed by the same skill
    # name), so emitting one here would duplicate it and inflate the prom
    # success counter and success-rate denominators.
    if source == "gate":
        ObservableSink().emit_span(
            Span(
                run_id=trace_id,
                step_id=skill,
                status="success" if status == "ok" else "fail",
                duration_ms=duration_ms,
                error_code=error_code,
                source=source,
            )
        )
