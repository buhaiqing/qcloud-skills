"""P4.7 — Langfuse exporter.

Maps local TraceRecord / ObservationRecord / ScoreRecord / UsageEvent into a
Langfuse-shaped trace payload:

    {
      "id":            <trace_id>,
      "name":          <trace.name or trace_id>,
      "timestamp":     <iso>,
      "metadata":      {...},
      "input":         {...},
      "output":        {...},
      "scores":        [{id, name, value, timestamp, observation_id, trace_id}, ...],
      "observations":  [{id, name, type, start_time, end_time,
                         parent_observation_id, metadata, input, output, ...}, ...]
    }

Export never raises: missing observation ids are silently skipped.
"""
from __future__ import annotations

from collections.abc import Iterable

from copilot.trace_records import (
    ObservationRecord,
    RuntimeInfo,
    ScoreRecord,
    SkillInfo,
    TraceRecord,
    UsageEvent,
)


def _obs_to_dict(obs: ObservationRecord) -> dict:
    d = obs.to_dict() if hasattr(obs, "to_dict") else {}
    return {
        "id": d.get("id", ""),
        "name": d.get("name"),
        "type": d.get("type", "SPAN").lower(),
        "start_time": d.get("start_time"),
        "end_time": d.get("end_time"),
        "parent_observation_id": d.get("parent_observation_id"),
        "status": d.get("status"),
        "metadata": d.get("metadata") or {},
        "input": d.get("input") or {},
        "output": d.get("output") or {},
        "version": d.get("version"),
        "error": d.get("error"),
    }


def _score_to_dict(sc: ScoreRecord) -> dict:
    return {
        "id": sc.id,
        "name": sc.score_type,
        "value": sc.value,
        "timestamp": sc.timestamp,
        "observation_id": sc.observation_id,
        "trace_id": sc.trace_id,
        "metadata": dict(getattr(sc, "metadata", {}) or {}),
    }


def _usage_to_generation(evt: UsageEvent) -> dict:
    usage = dict(evt.usage or {})
    metadata = dict(evt.metadata or {})
    metadata.update({
        "usage_event_id": evt.id,
        "provider": evt.provider,
        "model": evt.model,
        "prompt_version": evt.prompt_version,
        "latency_ms": evt.latency_ms,
        "retry_index": evt.retry_index,
        "rate_limited": evt.rate_limited,
    })
    return {
        "id": evt.id,
        "name": f"llm:{evt.provider or 'unknown'}:{evt.model or 'unknown'}",
        "type": "generation",
        "start_time": evt.timestamp,
        "end_time": evt.timestamp,
        "parent_observation_id": evt.observation_id,
        "status": "success",
        "metadata": {k: v for k, v in metadata.items() if v is not None},
        "usage": usage,
        "input": {},
        "output": {},
    }


def export_trace_to_langfuse(
    trace: TraceRecord,
    *,
    observations: Iterable[ObservationRecord] | None = None,
    scores: Iterable[ScoreRecord] | None = None,
    usage_events: Iterable[UsageEvent] | None = None,
) -> dict:
    """Convert a TraceRecord (+ optional sub-records) into Langfuse trace payload."""
    md: dict = {}
    if trace.skill is not None and isinstance(trace.skill, SkillInfo):
        md["skill"] = trace.skill.to_dict() if hasattr(trace.skill, "to_dict") else {}
    if trace.runtime is not None and isinstance(trace.runtime, RuntimeInfo):
        md["runtime"] = trace.runtime.to_dict() if hasattr(trace.runtime, "to_dict") else {}

    obs_payload: list[dict] = []
    obs_list = list(observations or [])
    obs_ids = set(trace.observation_ids or [])
    obs_by_id: dict[str, ObservationRecord] = {o.id: o for o in obs_list if getattr(o, "id", None)}

    # Emit observations referenced in trace.observation_ids (skip missing)
    for obs_id in trace.observation_ids or []:
        if obs_id in obs_by_id:
            obs_payload.append(_obs_to_dict(obs_by_id[obs_id]))
    explicit_ids_added: set[str] = set()
    for o in obs_list:
        if o.id not in obs_ids and o.id not in explicit_ids_added:
            obs_payload.append(_obs_to_dict(o))
            explicit_ids_added.add(o.id)
    # Append usage events as generations
    for evt in (usage_events or []):
        obs_payload.append(_usage_to_generation(evt))

    score_payload = [_score_to_dict(sc) for sc in (scores or [])]

    return {
        "id": trace.id,
        "name": trace.name or trace.id,
        "timestamp": trace.timestamp,
        "started_at": trace.started_at,
        "ended_at": trace.ended_at,
        "status": trace.status,
        "metadata": md,
        "input": trace.input or {},
        "output": trace.output or {},
        "scores": score_payload,
        "observations": obs_payload,
    }
