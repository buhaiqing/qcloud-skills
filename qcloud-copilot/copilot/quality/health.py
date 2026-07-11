from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone


SKILL_HEALTH_FILE = Path.cwd() / ".runtime" / "health" / "skill-metrics.jsonl"


def record_health(skill: str, operation: str, status: str, duration_ms: int, trace_id: str) -> None:
    SKILL_HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "skill": skill,
        "operation": operation,
        "status": status,
        "duration_ms": duration_ms,
        "trace_id": trace_id,
        "error_code": None,
    }
    with SKILL_HEALTH_FILE.open("a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
