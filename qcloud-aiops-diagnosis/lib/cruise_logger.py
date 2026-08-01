"""Cruise Audit Logger — structured event stream for human diagnosis + AI training data.

Every phase of the cruise/inspection process emits structured events that are:
1. Human-readable: operators trace the entire cruise step by step
2. Structured: consistent schema — phase/step/event_type/data/duration_ms
3. AI training data: event sequences → (context, decision) pairs for fine-tuning cruise agents

Output: `.runtime/cruise/{cruise_id}-{ts}.jsonl` (JSONL, one event per line)

Usage:
    logger = CruiseLogger(cruise_id="cruise-20260727-001", region="ap-guangzhou")
    logger.start_phase(Phase.TOPOLOGY_DISCOVERY)
    # ... do work ...
    logger.end_phase(Phase.TOPOLOGY_DISCOVERY, data={"nodes_discovered": 12})
    logger.log_decision("run_cvm_analyzer", "CVM nodes found",
                       options=["run", "skip"], chosen="run")
    logger.emit_finding({"resource_id": "ins-123", "anomaly": True})
    logger.skip_step("clb_analyzer", reason="no CLB in topology")
    logger.save()

AI Training Data:
    pairs = logger.to_training_pairs()
    # [{input: {prior_events, current_event}, output: {decision, rationale, chosen}}, ...]
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from types import TracebackType
from typing import Any, Self


class Phase(str, Enum):
    TOPOLOGY_DISCOVERY = "topology_discovery"
    SELECTIVE_WORKFLOW = "selective_workflow"
    ML_DETECTION = "ml_detection"
    CAPACITY_FORECAST = "capacity_forecast"
    FINGERPRINT = "fingerprint"
    FINDING_FILTER = "finding_filter"
    REPORT = "report"
    CRUISE_DIFF = "cruise_diff"


class EventType(str, Enum):
    START = "start"       # phase/step began
    COMPLETE = "complete"  # phase/step finished
    SKIP = "skip"        # intentionally skipped
    ERROR = "error"       # fatal error
    WARNING = "warning"     # non-fatal warning
    METRIC = "metric"     # quantitative measurement
    FINDING = "finding"   # anomaly finding emitted
    DECISION = "decision"   # agent decision point ← key for AI training data


@dataclass
class CruiseLogEvent:
    event_id: str
    timestamp: str           # ISO 8601 with timezone
    cruise_id: str
    phase: str              # Phase enum value
    step: str               # sub-step within phase
    event_type: str         # EventType enum value
    data: dict[str, Any]   # structured payload
    duration_ms: int | None = None
    error: str | None = None
    trace_id: str | None = None
    model: str | None = None  # LLM model used
    tokens_used: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @property
    def is_error(self) -> bool:
        return self.event_type == EventType.ERROR.value


class CruiseLogger:
    """Structured audit logger for cruise/inspection runs.

    Events are buffered in memory and flushed to disk on `save()` or context exit.
    Output: `.runtime/cruise/{cruise_id}-{ts}.jsonl`
    Format: one JSON-serialized CruiseLogEvent per line (JSONL).

    JSONL advantages:
    - Human-readable: `grep` / `jq` friendly
    - Streaming: events readable incrementally
    - AI training data: each event is a structured record
    """

    VERSION = "1.0"

    def __init__(
        self,
        cruise_id: str | None = None,
        region: str = "ap-guangzhou",
        output_dir: str | Path = ".runtime/cruise",
        trace_id: str | None = None,
    ):
        self.cruise_id = cruise_id or f"cruise-{datetime.now(UTC):%Y%m%d-%H%M%S}"
        self.region = region
        self.output_dir = Path(output_dir)
        self.trace_id = trace_id or str(uuid.uuid4())[:8]
        self._events: list[CruiseLogEvent] = []
        self._phase_stack: list[str] = []
        self._start_time: float = time.monotonic()
        self._event_count: int = 0

        # Emit run-start event
        self._emit(
            phase="__root__",
            step="cruise_start",
            event_type=EventType.START,
            data={
                "cruise_id": self.cruise_id,
                "region": self.region,
                "logger_version": self.VERSION,
            },
        )

    # ── Phase lifecycle ──────────────────────────────────────────────────────

    def start_phase(self, phase: str | Phase, data: dict[str, Any] | None = None) -> None:
        phase_str = phase.value if isinstance(phase, Phase) else phase
        self._phase_stack.append(phase_str)
        self._emit(
            phase=phase_str,
            step=f"{phase_str}.start",
            event_type=EventType.START,
            data=data or {},
        )

    def end_phase(
        self,
        phase: str | Phase,
        data: dict[str, Any] | None = None,
        *,
        summary: dict[str, Any] | None = None,
    ) -> None:
        phase_str = phase.value if isinstance(phase, Phase) else phase
        if self._phase_stack and self._phase_stack[-1] == phase_str:
            self._phase_stack.pop()
        duration_ms = self._elapsed_ms()
        self._emit(
            phase=phase_str,
            step=f"{phase_str}.complete",
            event_type=EventType.COMPLETE,
            data=data or {},
            duration_ms=duration_ms,
            metadata={"summary": summary} if summary else {},
        )

    def skip_step(
        self,
        step: str,
        reason: str,
        *,
        phase: str | Phase | None = None,
    ) -> None:
        p = self._resolve_phase(phase)
        self._emit(
            phase=p,
            step=step,
            event_type=EventType.SKIP,
            data={"reason": reason},
        )

    def log_error(
        self,
        step: str,
        error: str | Exception,
        *,
        phase: str | Phase | None = None,
        recoverable: bool = True,
    ) -> None:
        p = self._resolve_phase(phase)
        err_msg = str(error) if isinstance(error, Exception) else error
        self._emit(
            phase=p,
            step=step,
            event_type=EventType.ERROR,
            data={"error": err_msg, "recoverable": recoverable},
            error=err_msg,
        )

    def log_warning(
        self,
        step: str,
        message: str,
        *,
        phase: str | Phase | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        p = self._resolve_phase(phase)
        self._emit(
            phase=p,
            step=step,
            event_type=EventType.WARNING,
            data={"message": message, **(context or {})},
        )

    # ── Data events ──────────────────────────────────────────────────────────

    def log_metric(
        self,
        metric: str,
        value: float | dict[str, Any],
        tags: dict[str, str] | None = None,
        *,
        phase: str | Phase | None = None,
    ) -> None:
        p = self._resolve_phase(phase)
        self._emit(
            phase=p,
            step="__metric__",
            event_type=EventType.METRIC,
            data={"metric": metric, "value": value, "tags": tags or {}},
        )

    def emit_finding(
        self,
        finding: dict[str, Any],
        *,
        phase: str | Phase | None = None,
    ) -> None:
        p = self._resolve_phase(phase) or Phase.ML_DETECTION.value
        self._emit(
            phase=p,
            step="finding",
            event_type=EventType.FINDING,
            data={"finding": finding},
        )

    def log_decision(
        self,
        decision: str,
        rationale: str,
        options: list[str] | None = None,
        chosen: str | None = None,
        *,
        phase: str | Phase | None = None,
        model: str | None = None,
        tokens_used: int | None = None,
    ) -> None:
        """Log an agent decision point — primary AI training data source.

        Generates (context, decision) pairs via `to_training_pairs()`.
        """
        p = self._resolve_phase(phase)
        self._emit(
            phase=p,
            step="decision",
            event_type=EventType.DECISION,
            data={
                "decision": decision,
                "rationale": rationale,
                "options": options or [],
                "chosen": chosen,
            },
            model=model,
            tokens_used=tokens_used,
        )

    # ── Persistence ────────────────────────────────────────────────────────

    def save(self, *, path: str | Path | None = None) -> Path:
        """Flush all buffered events to JSONL file. Returns the file path."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        filepath = Path(path) if path else self.output_dir / f"{self.cruise_id}-{ts}.jsonl"
        total_ms = int((time.monotonic() - self._start_time) * 1000)

        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "type": "cruise_audit_header",
                "version": self.VERSION,
                "cruise_id": self.cruise_id,
                "trace_id": self.trace_id,
                "region": self.region,
                "event_count": self._event_count,
                "total_duration_ms": total_ms,
            }, ensure_ascii=False) + "\n")
            fh.writelines(json.dumps(ev.to_dict(), ensure_ascii=False) + "\n" for ev in self._events)
            fh.write(json.dumps({
                "type": "cruise_audit_footer",
                "cruise_id": self.cruise_id,
                "trace_id": self.trace_id,
                "event_count": self._event_count,
                "total_duration_ms": total_ms,
            }, ensure_ascii=False) + "\n")

        return filepath

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        """Flush events on exit. Re-raises any exception from the with-block."""
        try:
            self.save()
        except Exception:
            # Re-raise after saving — don't silently lose audit data.
            # If save itself fails we raise the save error, preserving exc_val.
            try:
                self.save(path=self.output_dir / f"EMERGENCY-{self.cruise_id}.jsonl")
            except Exception:  # noqa: BLE001, S110  # last-resort: never swallow the with-block exception
                pass  # Last-resort: at least try not to swallow the original
            if exc_val is not None:
                raise exc_val.with_traceback(exc_tb)
            raise
        return False

    # ── Internals ─────────────────────────────────────────────────────────

    def _emit(
        self,
        *,
        phase: str,
        step: str,
        event_type: EventType | str,
        data: dict[str, Any],
        duration_ms: int | None = None,
        error: str | None = None,
        model: str | None = None,
        tokens_used: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._event_count += 1
        ev = CruiseLogEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(UTC).isoformat(),
            cruise_id=self.cruise_id,
            phase=phase,
            step=step,
            event_type=event_type.value if isinstance(event_type, EventType) else event_type,
            data=data,
            duration_ms=duration_ms,
            error=error,
            trace_id=self.trace_id,
            model=model,
            tokens_used=tokens_used,
            metadata=metadata or {},
        )
        self._events.append(ev)

    def _elapsed_ms(self) -> int:
        return int((time.monotonic() - self._start_time) * 1000)

    def _resolve_phase(self, phase: str | Phase | None) -> str:
        if phase is None:
            return self._phase_stack[-1] if self._phase_stack else "__root__"
        return phase.value if isinstance(phase, Phase) else phase

    # ── Analysis ───────────────────────────────────────────────────────────

    def phase_summary(self) -> dict[str, dict[str, Any]]:
        """Aggregate events by phase for dashboarding."""
        summary: dict[str, dict[str, Any]] = {}
        for ev in self._events:
            if ev.phase == "__root__":
                continue
            if ev.phase not in summary:
                summary[ev.phase] = {"count": 0, "errors": 0, "skips": 0,
                                     "warnings": 0, "duration_ms": 0}
            summary[ev.phase]["count"] += 1
            if ev.event_type == EventType.ERROR.value:
                summary[ev.phase]["errors"] += 1
            if ev.event_type == EventType.SKIP.value:
                summary[ev.phase]["skips"] += 1
            if ev.event_type == EventType.WARNING.value:
                summary[ev.phase]["warnings"] += 1
            if ev.duration_ms is not None:
                summary[ev.phase]["duration_ms"] = max(summary[ev.phase]["duration_ms"], ev.duration_ms)
        return summary

    def to_training_pairs(self) -> list[dict[str, Any]]:
        """Convert event sequence to (context, decision) pairs for AI fine-tuning.

        Each pair:
        - input: {cruise_id, region, prior_events (up to 10), current_event}
        - output: {decision, rationale, chosen}

        Usage for training:
            pairs = logger.to_training_pairs()
            for pair in pairs:
                # pair["input"]  → model input context
                # pair["output"] → expected model output
        """
        pairs = []
        for i, ev in enumerate(self._events):
            if ev.event_type == EventType.DECISION.value:
                start = max(0, i - 10)
                context = [self._events[j].to_dict() for j in range(start, i + 1)]
                pairs.append({
                    "input": {
                        "cruise_id": self.cruise_id,
                        "region": self.region,
                        "prior_events": context[:-1],
                        "current_event": context[-1],
                    },
                    "output": {
                        "decision": ev.data.get("decision"),
                        "rationale": ev.data.get("rationale"),
                        "chosen": ev.data.get("chosen"),
                    },
                })
        return pairs
