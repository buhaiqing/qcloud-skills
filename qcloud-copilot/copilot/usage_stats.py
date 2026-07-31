"""P4.3 — usage stats aggregation across UsageEvent types.

Canonical buckets per event_type:

  llm:        calls / input_tokens / output_tokens / cached_tokens /
              reasoning_tokens / by_provider
  cloud_api:  call_count / rate_limited / retry_total / resource_units /
              request_bytes / response_bytes / by_product
  data:       event_count / metric_points / log_bytes / log_records /
              audit_events / topology_nodes / topology_edges
"""
from __future__ import annotations

from collections.abc import Iterable

from copilot.trace_records import UsageEvent


def _empty_llm() -> dict:
    return {
        "calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_tokens": 0,
        "reasoning_tokens": 0,
        "by_provider": {},
    }


def _empty_api() -> dict:
    return {
        "call_count": 0,
        "rate_limited": 0,
        "retry_total": 0,
        "resource_units": 0,
        "request_bytes": 0,
        "response_bytes": 0,
        "by_product": {},
    }


def _empty_data() -> dict:
    return {
        "event_count": 0,
        "metric_points": 0,
        "log_bytes": 0,
        "log_records": 0,
        "audit_events": 0,
        "topology_nodes": 0,
        "topology_edges": 0,
    }


def usage_stats(events: Iterable[UsageEvent]) -> dict:
    out = {
        "summary": {"event_count": 0},
        "llm": _empty_llm(),
        "cloud_api": _empty_api(),
        "data": _empty_data(),
    }
    for evt in events:
        out["summary"]["event_count"] += 1
        if evt.event_type == "llm":
            llm = out["llm"]
            llm["calls"] += 1
            usage = evt.usage or {}
            llm["input_tokens"] += int(usage.get("input_tokens", 0) or 0)
            llm["output_tokens"] += int(usage.get("output_tokens", 0) or 0)
            llm["cached_tokens"] += int(usage.get("cached_tokens", 0) or 0)
            llm["reasoning_tokens"] += int(usage.get("reasoning_tokens", 0) or 0)
            prov = evt.provider or "unknown"
            llm["by_provider"][prov] = llm["by_provider"].get(prov, 0) + 1
        elif evt.event_type == "cloud_api":
            api = out["cloud_api"]
            api["call_count"] += 1
            if evt.rate_limited:
                api["rate_limited"] += 1
            api["retry_total"] += int(evt.retry_index or 0)
            if evt.resource_count:
                api["resource_units"] += int(evt.resource_count)
            if evt.request_bytes:
                api["request_bytes"] += int(evt.request_bytes)
            if evt.response_bytes:
                api["response_bytes"] += int(evt.response_bytes)
            prod = evt.product or "unknown"
            api["by_product"][prod] = api["by_product"].get(prod, 0) + 1
        elif evt.event_type == "data":
            data = out["data"]
            data["event_count"] += 1
            if evt.metric_points:
                data["metric_points"] += int(evt.metric_points)
            if evt.log_bytes:
                data["log_bytes"] += int(evt.log_bytes)
            if evt.log_records:
                data["log_records"] += int(evt.log_records)
            if evt.audit_events:
                data["audit_events"] += int(evt.audit_events)
            if evt.topology_nodes:
                data["topology_nodes"] += int(evt.topology_nodes)
            if evt.topology_edges:
                data["topology_edges"] += int(evt.topology_edges)
    return out
