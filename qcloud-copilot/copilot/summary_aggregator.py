"""P2.9 — Rebuild AIOpsSummary / FinOpsSummary from raw observations / usage events.

Both aggregators are pure functions and idempotent: same input -> same output.
They never mutate input; callers decide whether to write back to TraceRecord.

Two functions:
  - aggregate_aiops_summary(observations, trace_id=None) -> AIOpsSummary
  - aggregate_finops_summary(usage_events, trace_id=None) -> FinOpsSummary
"""
from __future__ import annotations

from typing import Any, Iterable, Optional

from copilot.trace_records import (
    AIOpsSummary,
    FinOpsSummary,
    ObservationRecord,
    UsageEvent,
)


_SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def _collect_signals_from_metadata(observations: Iterable[ObservationRecord]) -> list[str]:
    out: list[str] = []
    for obs in observations:
        sigs = (obs.metadata or {}).get("signals") or []
        for sig in sigs:
            if isinstance(sig, str):
                out.append(sig)
    return list(dict.fromkeys(out))


def _collect_evidence_from_metadata(observations: Iterable[ObservationRecord]) -> list[str]:
    out: list[str] = []
    for obs in observations:
        evs = (obs.metadata or {}).get("evidence") or []
        for ev in evs:
            if isinstance(ev, str):
                out.append(ev)
    return list(dict.fromkeys(out))


def _collect_topology_from_metadata(observations: Iterable[ObservationRecord]) -> list[str]:
    out: set[str] = set()
    for obs in observations:
        nodes = (obs.metadata or {}).get("topology_nodes") or []
        for n in nodes:
            if isinstance(n, str):
                out.add(n)
    return sorted(out)


def _collect_rca_impact_response(
    observations: Iterable[ObservationRecord],
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    rca_bits: list[str] = []
    impact_bits: list[str] = []
    response_bits: list[str] = []
    for obs in observations:
        out = obs.output or {}
        for key, sink in (("rca", rca_bits), ("impact", impact_bits), ("response", response_bits)):
            v = out.get(key)
            if isinstance(v, str) and v.strip():
                sink.append(v.strip())
    return (
        "\n".join(rca_bits) if rca_bits else None,
        "\n".join(impact_bits) if impact_bits else None,
        "\n".join(response_bits) if response_bits else None,
    )


def _worst_severity(observations: Iterable[ObservationRecord]) -> Optional[str]:
    worst: Optional[tuple[int, str]] = None
    for obs in observations:
        sev = (obs.metadata or {}).get("severity")
        if isinstance(sev, str):
            rank = _SEVERITY_ORDER.get(sev.lower())
            if rank is not None:
                if worst is None or rank > worst[0]:
                    worst = (rank, sev.lower())
    return worst[1] if worst else None


def _quality_ratio(observations: Iterable[ObservationRecord]) -> float:
    total = 0
    success = 0
    for obs in observations:
        total += 1
        if (obs.status or "").lower() == "success":
            success += 1
    return (success / total) if total else 0.0


def aggregate_aiops_summary(
    observations: Iterable[ObservationRecord],
    trace_id: Optional[str] = None,
) -> AIOpsSummary:
    """Build an AIOpsSummary from a trace's observations (idempotent)."""
    obs_list = list(observations)
    rca, impact, response = _collect_rca_impact_response(obs_list)
    return AIOpsSummary(
        incident_id=trace_id,
        severity=_worst_severity(obs_list),
        signals=_collect_signals_from_metadata(obs_list),
        evidence=_collect_evidence_from_metadata(obs_list),
        topology=_collect_topology_from_metadata(obs_list),
        rca=rca,
        impact=impact,
        response=response,
        quality=_quality_ratio(obs_list),
    )


# ---------------------------------------------------------------------------
# P2.9.b — FinOps aggregator
# ---------------------------------------------------------------------------


def _sum_tokens(usage_events: list[UsageEvent]) -> dict[str, Any]:
    total_input = 0
    total_output = 0
    total_cached = 0
    total_reasoning = 0
    total_all = 0
    by_provider: dict[str, dict[str, int]] = {}
    for evt in usage_events:
        if evt.event_type != "llm":
            continue
        usage = evt.usage or {}
        inp = int(usage.get("input_tokens", 0) or 0)
        out_tok = int(usage.get("output_tokens", 0) or 0)
        cached = int(usage.get("cached_tokens", 0) or 0)
        reasoning = int(usage.get("reasoning_tokens", 0) or 0)
        total = int(usage.get("total_tokens", 0) or 0)
        total_input += inp
        total_output += out_tok
        total_cached += cached
        total_reasoning += reasoning
        total_all += total
        prov = evt.provider or "unknown"
        bucket = by_provider.setdefault(
            prov, {"input": 0, "output": 0, "cached": 0, "reasoning": 0, "total": 0}
        )
        bucket["input"] += inp
        bucket["output"] += out_tok
        bucket["cached"] += cached
        bucket["reasoning"] += reasoning
        bucket["total"] += total
    return {
        "input_tokens": total_input,
        "output_tokens": total_output,
        "cached_tokens": total_cached,
        "reasoning_tokens": total_reasoning,
        "total_tokens": total_all,
        "by_provider": by_provider,
    }


def _api_call_stats(usage_events: list[UsageEvent]) -> dict[str, Any]:
    total_calls = 0
    rate_limited = 0
    retry_count = 0
    resource_units = 0
    bytes_in = 0
    bytes_out = 0
    by_product: dict[str, int] = {}
    for evt in usage_events:
        if evt.event_type != "cloud_api":
            continue
        total_calls += 1
        if evt.rate_limited:
            rate_limited += 1
        retry_count += int(evt.retry_index or 0)
        if evt.resource_count:
            resource_units += int(evt.resource_count)
        if evt.request_bytes:
            bytes_in += int(evt.request_bytes)
        if evt.response_bytes:
            bytes_out += int(evt.response_bytes)
        prod = evt.product or "unknown"
        by_product[prod] = by_product.get(prod, 0) + 1
    return {
        "total_calls": total_calls,
        "rate_limited": rate_limited,
        "retry_count": retry_count,
        "resource_units": resource_units,
        "request_bytes": bytes_in,
        "response_bytes": bytes_out,
        "calls_by_product": by_product,
    }


def _data_read_stats(usage_events: list[UsageEvent]) -> dict[str, Any]:
    metric_points = 0
    log_bytes = 0
    log_records = 0
    audit_events = 0
    topo_nodes = 0
    topo_edges = 0
    for evt in usage_events:
        if evt.event_type != "data":
            continue
        metric_points += int(evt.metric_points or 0)
        log_bytes += int(evt.log_bytes or 0)
        log_records += int(evt.log_records or 0)
        audit_events += int(evt.audit_events or 0)
        topo_nodes += int(evt.topology_nodes or 0)
        topo_edges += int(evt.topology_edges or 0)
    return {
        "metric_points": metric_points,
        "log_bytes": log_bytes,
        "log_records": log_records,
        "audit_events": audit_events,
        "topology_nodes": topo_nodes,
        "topology_edges": topo_edges,
    }


def _cost_summary() -> dict[str, Any]:
    """Cost summary is derived from UsageEvent + PricingSnapshot; left
    empty here because CostRecord reconciliation belongs to P3 (pricing layer).
    """
    return {
        "events_pending_pricing": 0,
        "status": "not_applicable",
    }


def aggregate_finops_summary(
    usage_events: Iterable[UsageEvent],
    trace_id: Optional[str] = None,
) -> FinOpsSummary:
    """Build a FinOpsSummary from a trace's usage events (idempotent)."""
    events = list(usage_events)
    usage_summary = {
        "llm": _sum_tokens(events),
        "cloud_api": _api_call_stats(events),
        "data": _data_read_stats(events),
    }
    return FinOpsSummary(
        usage_summary=usage_summary,
        cost_summary=_cost_summary(),
        allocation={},
        value={},
    )
