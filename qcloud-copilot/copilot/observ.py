from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

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
    ts: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class Span:
    run_id: str
    step_id: str
    status: str  # started|success|fail|skipped
    duration_ms: int = 0
    error_code: str | None = None
    source: str = "step"  # step | gate — distinguishes execution failures from gate rejections
    ts: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


# Phase 1.4 — unified TraceSpan used by both GCL runner and Copilot
# dispatcher. Carries parent_span_id so cross-skill delegation produces a
# traceable parent-child chain. Persisted by ObservableSink.emit_trace_span()
# to .runtime/traces/{run_id}/spans.jsonl + _summary.json.

@dataclass
class TraceSpan:
    """One node in the cross-skill trace DAG.

    Fields are intentionally flat and JSON-friendly so spans.jsonl stays
    grep-able and round-trippable.
    """
    span_id: str
    trace_id: str
    parent_span_id: str | None
    run_id: str
    skill: str
    operation: str
    step_id: str | None
    status: str  # success | failure | halted | delegated | pending
    start_time: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    end_time: str | None = None
    duration_ms: int = 0
    error_code: str | None = None
    gcl_scores: dict[str, float] | None = None
    evidence: dict[str, Any] | None = None
    delegate_to: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a dict. Computes ``end_time`` + ``duration_ms`` if missing."""
        end = self.end_time or datetime.now(UTC).isoformat()
        dur = self.duration_ms
        if not dur and self.start_time:
            try:
                t0 = datetime.fromisoformat(self.start_time)
                t1 = datetime.fromisoformat(end)
                dur = max(0, int((t1 - t0).total_seconds() * 1000))
            except ValueError:
                dur = self.duration_ms
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "run_id": self.run_id,
            "skill": self.skill,
            "operation": self.operation,
            "step_id": self.step_id,
            "start_time": self.start_time,
            "end_time": end,
            "duration_ms": dur,
            "status": self.status,
            "error_code": self.error_code,
            "gcl_scores": self.gcl_scores,
            "evidence": self.evidence,
            "delegate_to": self.delegate_to,
            "metadata": dict(self.metadata),
        }


def new_trace_id() -> str:
    return uuid.uuid4().hex


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
                "ts": datetime.now(UTC).isoformat(),
            },
        )
        self._append_prom(
            "copilot_gate_decision_total",
            {"gate": gate, "decision": decision},
            1,
        )

    # -- Phase 1.4: unified TraceSpan persistence --------------------------

    # Phase 1.4 — TraceSpan → spans.jsonl + _summary.json under
    # .runtime/traces/{run_id}/. The legacy audit/<run_id>/_index.jsonl path
    # is preserved for backward compatibility with existing observ_query.
    def emit_trace_span(self, span: TraceSpan) -> None:
        assert isinstance(span, TraceSpan), (
            f"emit_trace_span expects TraceSpan, got {type(span).__name__}"
        )
        trace_dir = self._root / "traces" / span.run_id
        trace_dir.mkdir(parents=True, exist_ok=True)
        record = span.to_dict()
        record["_kind"] = "trace_span"
        self._append_jsonl(trace_dir / "spans.jsonl", record)
        self._update_trace_summary(trace_dir, span.run_id)

    def _update_trace_summary(self, trace_dir: Path, run_id: str) -> None:
        """Rewrite ``_summary.json`` for the run with span_count + span_ids.

        Cheap because spans.jsonl is the source of truth; the summary is just
        a quick lookup for cross-skill queries (gcl_trace_aggregate --cross-skill).
        """
        spans_path = trace_dir / "spans.jsonl"
        if not spans_path.exists():
            return
        spans = []
        for line in spans_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                spans.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        skill_set: set[str] = set()
        delegated_to: set[str] = set()
        for s in spans:
            if s.get("skill"):
                skill_set.add(s["skill"])
            if s.get("delegate_to"):
                delegated_to.add(s["delegate_to"])
        summary = {
            "run_id": run_id,
            "span_count": len(spans),
            "skill_set": sorted(skill_set),
            "delegate_to_set": sorted(delegated_to),
            "span_ids": [s.get("span_id") for s in spans],
            "last_updated": datetime.now(UTC).isoformat(),
        }
        (trace_dir / "_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
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
