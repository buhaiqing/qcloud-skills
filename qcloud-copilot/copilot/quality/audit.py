from __future__ import annotations

import json
from datetime import datetime, timezone


def audit_trace(
    session_id: str,
    step_id: str,
    trace_data: dict,
    trace_id: str | None = None,
) -> None:
    """Persist a step-level execution trace.

    `trace_id` is the cross-system join key: when provided it is written into
    the record and used as the audit directory name so copilot traces and GCL
    traces share one identifier namespace (fixes data-lineage break L3/L4).
    """
    from pathlib import Path

    run_id = trace_id or session_id
    audit_dir = Path.cwd() / ".runtime" / "gcl" / "copilot" / "audit" / run_id
    audit_dir.mkdir(parents=True, exist_ok=True)
    record = {"trace_id": run_id, "session_id": session_id, **trace_data}
    filename = (
        audit_dir / f"step-{step_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json"
    )
    filename.write_text(json.dumps(record, ensure_ascii=False, indent=2))
