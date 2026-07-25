from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from copilot.observ import ObservableSink, Span


def audit_trace(
    session_id: str,
    step_id: str,
    trace_data: dict,
    trace_id: str | None = None,
    provenance: dict | None = None,
    skill: str | None = None,
    skill_info: object | None = None,
    runtime_info: object | None = None,
) -> None:
    """Persist a step-level execution trace.

    `trace_id` is the cross-system join key: when provided it is written into
    the record and used as the audit directory name so copilot traces and GCL
    traces share one identifier namespace (fixes data-lineage break L3/L4).

    `provenance` (optional) carries the evaluation lineage for one or more
    gates that ran on this step, e.g. the H hallucination check. Each entry has
    shape ``{eval_id, rule, input_ref, decision, reason}`` so a trace can answer
    "why did this step get this verdict" (fixes data-lineage break L1/L2).

    `skill_info` (P1.4) and `runtime_info` (P1.4) attach SkillInfo /
    RuntimeInfo blobs so a trace can answer which Skill version + which code
    commit + which Python/tccli/SDK versions produced this step. Both objects
    are persisted as JSON via their `to_dict()` if available, else as-is.
    """
    run_id = trace_id or session_id
    audit_dir = Path.cwd() / ".runtime" / "gcl" / "copilot" / "audit" / run_id
    audit_dir.mkdir(parents=True, exist_ok=True)
    record = {"trace_id": run_id, "session_id": session_id, **trace_data}
    if provenance is not None:
        record["provenance"] = provenance
    if skill_info is not None:
        record["skill"] = skill_info.to_dict() if hasattr(skill_info, "to_dict") else skill_info
    if runtime_info is not None:
        record["runtime"] = runtime_info.to_dict() if hasattr(runtime_info, "to_dict") else runtime_info
    filename = (
        audit_dir / f"step-{step_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}.json"
    )
    filename.write_text(json.dumps(record, ensure_ascii=False, indent=2))

    # Emit a span only for non-step (system) traces: per-step dispatcher
    # traces already get a skill-keyed span from dispatcher._emit_span, so
    # emitting one here would duplicate it and double-count success_rate /
    # inflate the prom counter. System traces (e.g. "l2-gate",
    # "blackboard-init") pass no skill and are the sole emitter for their span.
    if skill is None:
        status = str(trace_data.get("status", "success"))
        ObservableSink().emit_span(
            Span(
                run_id=run_id,
                step_id=step_id,
                status="success" if status == "success" else "fail",
                duration_ms=int(trace_data.get("duration_ms", 0) or 0),
                error_code=trace_data.get("error"),
            )
        )
