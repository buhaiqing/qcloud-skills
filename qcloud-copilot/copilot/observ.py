from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

# Prometheus label values must not contain quotes, newlines, or backslashes.
# Anything outside the safe charset is replaced to keep the exposition format valid.
_SAFE_LABEL = re.compile(r"[^A-Za-z0-9_:\-./]")


def _sanitize_label(value: str) -> str:
    """Make a string safe to embed inside a Prometheus label value."""
    return _SAFE_LABEL.sub("_", value)


class MetricKind(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


@dataclass
class Metric:
    name: str
    kind: MetricKind
    value: float
    tags: dict[str, str] = field(default_factory=dict)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Span:
    run_id: str
    step_id: str
    status: str  # started|success|fail|skipped
    duration_ms: int = 0
    error_code: str | None = None
    source: str = "step"  # step | gate — distinguishes execution failures from gate rejections
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ObservableSink:
    """Unified observability facade: writes three sinks atomically per event.

    - metrics.jsonl: structured metric stream (query source for observ_query)
    - audit/{run_id}/_index.json: append-only span list for O(1) trace rebuild
    - metrics.prom: Prometheus text exposition
    """

    def __init__(self, runtime_root: Path | None = None):
        self._root = runtime_root or (Path.cwd() / ".runtime")
        self._metrics_dir = self._root / "metrics"
        self._audit_dir = self._root / "audit"
        self._metrics_dir.mkdir(parents=True, exist_ok=True)

    # -- public API ---------------------------------------------------------

    def emit_metric(self, m: Metric) -> None:
        self._append_jsonl(self._metrics_dir / "metrics.jsonl", self._metric_record(m))

    def emit_span(self, s: Span) -> None:
        self._append_jsonl(
            self._metrics_dir / "metrics.jsonl",
            {
                "kind": "span",
                "run_id": s.run_id,
                "step_id": s.step_id,
                "status": s.status,
                "duration_ms": s.duration_ms,
                "error_code": s.error_code,
                "source": s.source,
                "ts": s.ts,
            },
        )
        self._append_run_index(s)
        if s.duration_ms:
            self._append_prom(
                "copilot_step_duration_ms",
                {"run_id": s.run_id, "step_id": s.step_id, "status": s.status},
                s.duration_ms,
            )
        if s.status == "success":
            # Fixed skill name per spec: success counts the copilot skill itself,
            # not the individual step (which would conflate "step" with "skill").
            self._append_prom(
                "copilot_skill_success_total",
                {"skill": "qcloud-copilot"},
                1,
            )

    def emit_gate(self, run_id: str, gate: str, decision: str, reason: str) -> None:
        self._append_jsonl(
            self._metrics_dir / "metrics.jsonl",
            {
                "kind": "gate",
                "run_id": run_id,
                "gate": gate,
                "decision": decision,
                "reason": reason,
                "ts": datetime.now(timezone.utc).isoformat(),
            },
        )
        self._append_prom(
            "copilot_gate_decision_total",
            {"gate": gate, "decision": decision},
            1,
        )
    # -- TRACE-1 v3 write entry points (P2.2) -----------------------------

    def emit_observation(self, obs) -> None:
        """Persist an `ObservationRecord` to ``audit/<trace_id>/observations.jsonl``."""
        from copilot.trace_records import ObservationRecord  # local to avoid cycle

        assert isinstance(obs, ObservationRecord), (
            f"emit_observation expects ObservationRecord, got {type(obs).__name__}"
        )
        trace_dir = self._audit_dir / obs.trace_id
        trace_dir.mkdir(parents=True, exist_ok=True)
        record = obs.to_dict()
        record["_kind"] = "observation"
        self._append_jsonl(
            trace_dir / "observations.jsonl",
            record,
        )

    def emit_usage_event(self, evt) -> None:
        """Persist a `UsageEvent` to ``audit/<trace_id>/usage_events.jsonl``."""
        from copilot.trace_records import UsageEvent  # local to avoid cycle

        assert isinstance(evt, UsageEvent), (
            f"emit_usage_event expects UsageEvent, got {type(evt).__name__}"
        )
        trace_dir = self._audit_dir / evt.trace_id
        trace_dir.mkdir(parents=True, exist_ok=True)
        record = evt.to_dict()
        record["_kind"] = "usage_event"
        self._append_jsonl(
            trace_dir / "usage_events.jsonl",
            record,
        )

    # -- internal writers ---------------------------------------------------
    def _metric_record(self, m: Metric) -> dict:
        return {
            "kind": "metric",
            "name": m.name,
            "metric_kind": m.kind.value,
            "value": m.value,
            "tags": m.tags,
            "ts": m.ts,
        }

    def _append_jsonl(self, path: Path, record: dict) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _append_run_index(self, s: Span) -> None:
        # Append-only JSONL keeps the write O(1) and avoids rewriting the whole
        # index on every span (atomic per-line, no partial-read risk for readers).
        index_path = self._audit_dir / s.run_id / "_index.jsonl"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "run_id": s.run_id,
            "step_id": s.step_id,
            "status": s.status,
            "ts": s.ts,
        }
        with index_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _append_prom(self, name: str, labels: dict[str, str], value: float) -> None:
        prom_path = self._metrics_dir / "metrics.prom"
        label_str = ",".join(
            f'{k}="{_sanitize_label(v)}"' for k, v in labels.items()
        )
        line = f"{name}{{{label_str}}} {value}\n"
        with prom_path.open("a", encoding="utf-8") as f:
            f.write(line)


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]
