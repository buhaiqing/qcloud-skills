"""P2.3 / P2.4 / P2.5 — UsageEvent emitters for LLM / Cloud API / Data.

Three factories produce immutable UsageEvent instances with consistent fields
and joinable IDs (id prefixed `ue-`).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from copilot.trace_records import UsageEvent


def _new_id() -> str:
    return f"ue-{uuid.uuid4().hex[:12]}"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _base_kwargs(trace_id: str, observation_id: str | None, latency_ms: int | None, metadata: dict | None) -> dict[str, Any]:
    return {
        "id": _new_id(),
        "trace_id": trace_id,
        "timestamp": _utc_now(),
        "observation_id": observation_id,
        "latency_ms": latency_ms,
        "metadata": dict(metadata or {}),
    }


# ---------------------------------------------------------------------------
# P2.3 — LLM usage emitter
# ---------------------------------------------------------------------------


def emit_llm_usage(
    *,
    trace_id: str,
    observation_id: str | None = None,
    provider: str,
    model: str,
    prompt_version: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_tokens: int = 0,
    reasoning_tokens: int = 0,
    retry_index: int = 0,
    latency_ms: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> UsageEvent:
    """Emit an LLM usage event.

    Total tokens = input + output (cached / reasoning subtractions kept distinct
    so callers can compute their own pricing per bucket).
    """
    usage = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cached_tokens": cached_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": input_tokens + output_tokens,
    }
    kwargs = _base_kwargs(trace_id, observation_id, latency_ms, metadata)
    return UsageEvent(
        **kwargs,
        event_type="llm",
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        usage=usage,
        retry_index=retry_index,
    )


# ---------------------------------------------------------------------------
# P2.4 — Cloud API usage emitter
# ---------------------------------------------------------------------------


def emit_cloud_api_usage(
    *,
    trace_id: str,
    observation_id: str | None = None,
    product: str,
    service: str,
    action: str,
    api_version: str | None = None,
    region: str | None = None,
    client_type: str | None = None,
    api_request_id: str | None = None,
    request_bytes: int | None = None,
    response_bytes: int | None = None,
    resource_count: int | None = None,
    retry_index: int = 0,
    rate_limited: bool = False,
    latency_ms: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> UsageEvent:
    """Emit a Cloud API usage event covering tccli / SDK invocations.

    `service` and `api_version` go into the metadata side-channel since
    UsageEvent does not have dedicated fields for them in the v3 schema.
    """
    merged_metadata = dict(metadata or {})
    merged_metadata.setdefault("service", service)
    if api_version is not None:
        merged_metadata.setdefault("api_version", api_version)

    kwargs = _base_kwargs(trace_id, observation_id, latency_ms, merged_metadata)
    return UsageEvent(
        **kwargs,
        event_type="cloud_api",
        product=product,
        action=action,
        region=region,
        client_type=client_type,
        api_request_id=api_request_id,
        request_bytes=request_bytes,
        response_bytes=response_bytes,
        resource_count=resource_count,
        retry_index=retry_index,
        rate_limited=rate_limited,
    )


# ---------------------------------------------------------------------------
# P2.5 — Data usage emitter
# ---------------------------------------------------------------------------


def emit_data_usage(
    *,
    trace_id: str,
    observation_id: str | None = None,
    metric_points: int | None = None,
    log_bytes: int | None = None,
    log_records: int | None = None,
    audit_events: int | None = None,
    topology_nodes: int | None = None,
    topology_edges: int | None = None,
    latency_ms: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> UsageEvent:
    """Emit a Data usage event covering metric/log/audit/topology reads."""
    kwargs = _base_kwargs(trace_id, observation_id, latency_ms, metadata)
    return UsageEvent(
        **kwargs,
        event_type="data",
        metric_points=metric_points,
        log_bytes=log_bytes,
        log_records=log_records,
        audit_events=audit_events,
        topology_nodes=topology_nodes,
        topology_edges=topology_edges,
    )
