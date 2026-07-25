"""P4 — trace_cost_aggregate: multi-dimensional CostRecord + UsageEvent aggregation.

Pure functions. Idempotent. Returns dict-shaped reports suitable for CLI / script
or Langfuse exporter consumption.
"""
from typing import Iterable

from copilot.trace_records import (
    CostRecord,
    CostStatus,
    UsageEvent,
)


# ---------------------------------------------------------------------------
# Dimensions supported on CostRecord
# ---------------------------------------------------------------------------


_COST_DIMS = {
    "trace_id": lambda r: r.trace_id,
    "cost_status": lambda r: r.cost_status.value,
    "pricing_snapshot_version": lambda r: r.pricing_snapshot_version or "unknown",
    "currency": lambda r: r.currency,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _key_for(record: CostRecord, dims: list[str]) -> str:
    parts = []
    for d in dims:
        getter = _COST_DIMS.get(d)
        if getter is None:
            parts.append("?")
            continue
        parts.append(str(getter(record)))
    return "|".join(parts)


def _ensure_bucket(store: dict, key: str) -> dict:
    if key not in store:
        store[key] = {"total_cost": 0.0, "count": 0, "priced_count": 0, "unpriced_count": 0}
    return store[key]


def _is_priced(status: CostStatus) -> bool:
    return status in {CostStatus.ACTUAL, CostStatus.PARTIAL, CostStatus.ESTIMATED}


def _is_unpriced(status: CostStatus) -> bool:
    return status in {CostStatus.UNPRICED, CostStatus.NOT_APPLICABLE}


def _summary(costs: Iterable[CostRecord]) -> dict:
    total = 0.0
    count = 0
    priced = 0
    unpriced = 0
    for r in costs:
        total += r.total_cost
        count += 1
        if _is_priced(r.cost_status):
            priced += 1
        if _is_unpriced(r.cost_status):
            unpriced += 1
    return {
        "total_cost": round(total, 9),
        "count": count,
        "priced_count": priced,
        "unpriced_count": unpriced,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def aggregate_costs(
    records: Iterable[CostRecord],
    *,
    by: list[str],
) -> dict:
    """Aggregate CostRecords by `by` (1 or more dimensions, joined by '|')."""
    recs = list(records)
    by_key = "by_" + "|".join(by)
    store: dict[str, dict] = {}
    for r in recs:
        k = _key_for(r, by)
        bucket = _ensure_bucket(store, k)
        bucket["total_cost"] += r.total_cost
        bucket["count"] += 1
        if _is_priced(r.cost_status):
            bucket["priced_count"] += 1
        if _is_unpriced(r.cost_status):
            bucket["unpriced_count"] += 1
    out = {
        "summary": _summary(recs),
    }
    out[by_key] = {k: {**v, "total_cost": round(v["total_cost"], 9)} for k, v in store.items()}
    return out


def aggregate_usage_events(
    events: Iterable[UsageEvent],
    *,
    by: list[str],
) -> dict:
    """Aggregate UsageEvents by event-level dimensions.

    Supports dimensions: event_type, provider, model, product, action,
    region, trace_id.
    """
    ev_list = list(events)
    by_key = "by_" + "|".join(by)

    def getter(d: str):
        if d == "event_type":
            return lambda e: e.event_type
        if d == "provider":
            return lambda e: e.provider or "unknown"
        if d == "model":
            return lambda e: e.model or "unknown"
        if d == "product":
            return lambda e: e.product or "unknown"
        if d == "action":
            return lambda e: e.action or "unknown"
        if d == "region":
            return lambda e: e.region or "unknown"
        if d == "trace_id":
            return lambda e: e.trace_id
        return lambda e: "?"

    raw_store: dict[str, dict] = {}
    for evt in ev_list:
        parts = [getter(d)(evt) for d in by]
        k = "|".join(parts)
        bucket = raw_store.setdefault(k, {"event_count": 0, "total_tokens": 0, "rate_limited": 0, "retry_index_sum": 0})
        bucket["event_count"] += 1
        if evt.usage:
            bucket["total_tokens"] += int(evt.usage.get("total_tokens", 0) or 0)
        if evt.rate_limited:
            bucket["rate_limited"] += 1
        bucket["retry_index_sum"] += int(evt.retry_index or 0)

    out = {"summary": {"event_count": len(ev_list)}}
    out[by_key] = {
        k: {**v, "total_tokens": int(v["total_tokens"])} for k, v in raw_store.items()
    }

    # When grouped by event_type, also emit a by_product / by_provider child summary
    if by == ["event_type"]:
        # enrich cloud_api / llm children
        by_et = out[by_key]
        by_et_llm: dict[str, int] = {}
        for evt in ev_list:
            if evt.event_type == "llm":
                prov = evt.provider or "unknown"
                by_et_llm[prov] = by_et_llm.get(prov, 0) + 1
        by_et_api: dict[str, int] = {}
        for evt in ev_list:
            if evt.event_type == "cloud_api":
                p = evt.product or "unknown"
                by_et_api[p] = by_et_api.get(p, 0) + 1
        if "llm" in by_et:
            by_et["llm"]["by_provider"] = by_et_llm
        if "cloud_api" in by_et:
            by_et["cloud_api"]["by_product"] = by_et_api

    return out


def _split_cost_by_event_type(
    records: Iterable[CostRecord], events: Iterable[UsageEvent]
) -> dict[str, float]:
    """Allocate each priced record's total_cost across LLM / Cloud API / Data.

    Allocation per record:
      - prefer CostRecord.metadata['by_event_type'] if present -> weighted share
      - else fall back to UsageEvent event_type counts observed in scope
      - skip priced records whose bucket has zero billable events
      - UNPRICED / NOT_APPLICABLE records contribute zero
    Returns {event_type_bucket: cost}. Empty dict if no priced records.
    """
    rec_list = list(records)
    ev_list = list(events)
    if not rec_list:
        return {}

    # Fallback event-type proportions from the events list.
    fallback_counts: dict[str, int] = {}
    for evt in ev_list:
        fallback_counts[evt.event_type] = fallback_counts.get(evt.event_type, 0) + 1

    out: dict[str, float] = {}
    for rec in rec_list:
        if rec.cost_status not in {CostStatus.ACTUAL, CostStatus.PARTIAL, CostStatus.ESTIMATED}:
            continue
        if abs(rec.total_cost) < 1e-12:
            continue
        breakdown = (rec.metadata or {}).get("by_event_type") or {}
        if not breakdown:
            # Fallback: equal split across distinct event_type buckets.
            breakdown = {et: 1 for et in sorted(fallback_counts.keys())}
        if not breakdown:
            continue
        total_weight = sum(int(v) for v in breakdown.values())
        if total_weight == 0:
            continue
        for k, v in breakdown.items():
            try:
                w = int(v)
            except Exception:
                continue
            if w <= 0:
                continue
            share = w / total_weight
            out[k] = out.get(k, 0.0) + round(rec.total_cost * share, 9)
    return out


def aggregate(
    *,
    records: Iterable[CostRecord],
    events: Iterable[UsageEvent],
    cost_dimensions: list[str],
    usage_dimensions: list[str],
) -> dict:
    """Combined aggregate: CostRecord reports + UsageEvent reports + joint summary +
    LLM vs Cloud API cost split (P4.2)."""
    rec_list = list(records)
    ev_list = list(events)
    cost_report = aggregate_costs(rec_list, by=cost_dimensions)
    usage_report = aggregate_usage_events(ev_list, by=usage_dimensions)
    out: dict = {"summary": cost_report["summary"]}
    out.update({k: v for k, v in cost_report.items() if k != "summary"})
    out.update({k: v for k, v in usage_report.items() if k != "summary"})
    out["usage_summary"] = usage_report["summary"]
    out["cost_by_event_type"] = _split_cost_by_event_type(rec_list, ev_list)
    return out
