"""P2.3 / P2.4 / P2.5 — UsageEvent emitters for LLM / Cloud API / Data.

Three factories produce immutable UsageEvent instances with consistent fields
and joinable IDs (id prefixed `ue-`).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from copilot.trace_records import UsageEvent


def _new_id() -> str:
    return f"ue-{uuid.uuid4().hex[:12]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _base_kwargs(trace_id: str, observation_id: Optional[str], latency_ms: Optional[int], metadata: Optional[dict]) -> dict[str, Any]:
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
    observation_id: Optional[str] = None,
    provider: str,
    model: str,
    prompt_version: Optional[str] = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_tokens: int = 0,
    reasoning_tokens: int = 0,
    retry_index: int = 0,
    latency_ms: Optional[int] = None,
    metadata: Optional[dict[str, Any]] = None,
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
    observation_id: Optional[str] = None,
    product: str,
    service: str,
    action: str,
    api_version: Optional[str] = None,
    region: Optional[str] = None,
    client_type: Optional[str] = None,
    api_request_id: Optional[str] = None,
    request_bytes: Optional[int] = None,
    response_bytes: Optional[int] = None,
    resource_count: Optional[int] = None,
    retry_index: int = 0,
    rate_limited: bool = False,
    latency_ms: Optional[int] = None,
    metadata: Optional[dict[str, Any]] = None,
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
    observation_id: Optional[str] = None,
    metric_points: Optional[int] = None,
    log_bytes: Optional[int] = None,
    log_records: Optional[int] = None,
    audit_events: Optional[int] = None,
    topology_nodes: Optional[int] = None,
    topology_edges: Optional[int] = None,
    latency_ms: Optional[int] = None,
    metadata: Optional[dict[str, Any]] = None,
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
