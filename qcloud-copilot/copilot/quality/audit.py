from __future__ import annotations

import json
from datetime import datetime, timezone


def audit_trace(session_id: str, step_id: str, trace_data: dict) -> None:
    from pathlib import Path

    audit_dir = Path.cwd() / ".runtime" / "gcl" / "copilot" / "audit" / session_id
    audit_dir.mkdir(parents=True, exist_ok=True)
    filename = (
        audit_dir / f"step-{step_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json"
    )
    filename.write_text(json.dumps(trace_data, ensure_ascii=False, indent=2))
