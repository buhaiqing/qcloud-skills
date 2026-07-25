"""P2.6.a — with_step_recording(): bundle audit + observation + usage events.

Context-manager approach: caller wraps a unit of work; on exit the bundle
writes a single ObservationRecord (with start/end timestamps and status),
plus any UsageEvent instances the caller attached via `add_usage`.

Usage:
    from copilot.step_recording import with_step_recording
    sink = ObservableSink()
    with with_step_recording(sink=sink, trace_id="t1", step_id="s1", name="...") as ctx:
        evt = emit_llm_usage(trace_id="t1", observation_id=ctx.observation.id, ...)
        ctx.add_usage(evt)
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

from copilot.observation_classifier import classify_observation_type
from copilot.trace_records import (
    ObservationRecord,
    ObservationType,
    UsageEvent,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StepContext:
    """Carries per-step state during the `with` block."""

    observation: ObservationRecord
    sink: Any
    _usage_events: list[UsageEvent] = field(default_factory=list)
    status: str = "in_progress"
    error: Optional[str] = None

    def add_usage(self, evt: UsageEvent) -> None:
        """Attach a UsageEvent to be flushed on context exit."""
        if not isinstance(evt, UsageEvent):
            raise TypeError(f"add_usage expects UsageEvent, got {type(evt).__name__}")
        self._usage_events.append(evt)


def _flush(sink: Any, ctx: StepContext) -> None:
    """Write observation + queued usage events on context exit."""
    obs = ctx.observation
    obs.end_time = _utc_now()
    obs.status = ctx.status
    if ctx.error is not None:
        obs.error = ctx.error
    sink.emit_observation(obs)
    for evt in ctx._usage_events:
        sink.emit_usage_event(evt)


@contextmanager
def with_step_recording(
    *,
    sink,
    trace_id: str,
    step_id: str,
    name: str,
    kind: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    input_data: Optional[dict[str, Any]] = None,
    output_data: Optional[dict[str, Any]] = None,
) -> Iterator[StepContext]:
    """Context manager that bundles audit + observation + usage emission.

    Auto-classifies the ObservationType via P2.7 classifier unless `kind` given.
    """
    obs_type: ObservationType = classify_observation_type(name=name, kind=kind)
    obs = ObservationRecord(
        id=f"obs-{uuid.uuid4().hex[:12]}",
        trace_id=trace_id,
        type=obs_type,
        name=name,
        start_time=_utc_now(),
        status="in_progress",
        metadata=dict(metadata or {}),
        input=dict(input_data or {}),
        output=dict(output_data or {}),
    )
    ctx = StepContext(observation=obs, sink=sink)
    try:
        yield ctx
        if ctx.status == "in_progress":
            ctx.status = "success"
    except BaseException as exc:
        ctx.status = "error"
        ctx.error = exc.__class__.__name__ + ": " + str(exc)
        raise
    finally:
        obs.metadata["step_id"] = step_id  # join key for downstream queries
        _flush(sink, ctx)
