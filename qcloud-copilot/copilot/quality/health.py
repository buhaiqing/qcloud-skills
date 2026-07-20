from __future__ import annotations

import json
from datetime import datetime, timezone
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
) -> None:
    """Append a skill-health event (backward-compatible jsonl) and emit a span.

    `error_code` is the real failure signal (gate name or step error token);
    previously hardcoded to None so failures were invisible (O4).
    """
    SKILL_HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "skill": skill,
        "operation": operation,
        "status": status,
        "duration_ms": duration_ms,
        "trace_id": trace_id,
        "error_code": error_code,
    }
    with SKILL_HEALTH_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    ObservableSink().emit_span(
        Span(
            run_id=trace_id,
            step_id=skill,
            status="success" if status == "ok" else "fail",
            duration_ms=duration_ms,
            error_code=error_code,
            # Gate rejections (engine L0/L1/L2 failures) are copilot-scoped, not
            # step executions; tag them so step-failure queries can exclude them.
            source="gate" if status != "ok" else "step",
        )
    )
