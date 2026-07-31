"""P4.5 — quality_coverage_report.

Aggregate CostRecord coverage status from a collection of records plus an
optional AllocationRecord set for allocation_coverage.

Returns per-trace ratios + score (good/fair/poor/unpriced) and a summary
breakdown of score distribution.
"""
from __future__ import annotations

from collections.abc import Iterable

from copilot.trace_records import AllocationRecord, CostRecord, CostStatus


def _score(priced_ratio: float, total: int) -> str:
    if total == 0 or priced_ratio == 0:
        return "unpriced"
    if priced_ratio >= 0.9:
        return "good"
    if priced_ratio >= 0.5:
        return "fair"
    return "poor"


def _overall(scores: list[str]) -> str:
    if not scores:
        return "unpriced"
    bad = sum(1 for s in scores if s in {"poor", "unpriced"})
    fair = sum(1 for s in scores if s == "fair")
    if bad > fair:
        return "poor"
    if fair > 0 and bad == 0:
        return "fair"
    return "good"


def quality_coverage_report(
    records: Iterable[CostRecord],
    *,
    allocations: Iterable[AllocationRecord] | None = None,
) -> dict:
    by_trace: dict[str, dict] = {}
    alloc_keys_per_cost: dict[str, set[tuple[str, str]]] = {}
    for alloc in (allocations or []):
        alloc_keys_per_cost.setdefault(alloc.cost_id, set()).add(alloc.attribution_key)

    priced_count_sum: dict[str, int] = {}
    total_events_sum: dict[str, int] = {}
    partial_count: dict[str, int] = {}
    unpriced_count: dict[str, int] = {}
    not_applicable_count: dict[str, int] = {}
    priced_total: dict[str, float] = {}
    event_ids: dict[str, set[str]] = {}
    distinct_alloc_keys_per_trace: dict[str, set[tuple[str, str]]] = {}
    alloc_total_count_per_trace: dict[str, int] = {}
    event_total_per_trace: dict[str, int] = {}

    for rec in records:
        t = rec.trace_id
        md = rec.metadata or {}
        pc = int(md.get("priced_count", 0) or 0)
        te = int(md.get("total_events", 0) or 0)
        priced_count_sum[t] = priced_count_sum.get(t, 0) + pc
        total_events_sum[t] = total_events_sum.get(t, 0) + te
        if rec.cost_status in {CostStatus.ACTUAL, CostStatus.ESTIMATED}:
            priced_total[t] = priced_total.get(t, 0.0) + rec.total_cost
        if rec.cost_status == CostStatus.PARTIAL:
            partial_count[t] = partial_count.get(t, 0) + 1
        if rec.cost_status == CostStatus.UNPRICED:
            unpriced_count[t] = unpriced_count.get(t, 0) + 1
        if rec.cost_status == CostStatus.NOT_APPLICABLE:
            not_applicable_count[t] = not_applicable_count.get(t, 0) + 1
        event_ids.setdefault(t, set()).update(rec.usage_event_ids or [])
        distinct_alloc_keys_per_trace.setdefault(t, set()).update(
            alloc_keys_per_cost.get(rec.id, set())
        )
        alloc_total_count_per_trace[t] = alloc_total_count_per_trace.get(t, 0) + len(
            alloc_keys_per_cost.get(rec.id, set())
        )
        event_total_per_trace[t] = event_total_per_trace.get(t, 0) + te

    for t in priced_count_sum:  # noqa: PLC0206 - keep dict lookup pattern for symmetry with sibling dicts
        pc = priced_count_sum[t]
        te = total_events_sum[t]
        ratio = (pc / te) if te > 0 else 0.0
        distinct = distinct_alloc_keys_per_trace.get(t, set())
        alloc_coverage = (len(distinct) / te) if te > 0 else 0.0
        by_trace[t] = {
            "total_cost": round(priced_total.get(t, 0.0), 9),
            "priced_count": pc,
            "unpriced_count": unpriced_count.get(t, 0),
            "partial_count": partial_count.get(t, 0),
            "not_applicable_count": not_applicable_count.get(t, 0),
            "priced_ratio": round(ratio, 6),
            "unpriced_ratio": round(1 - ratio, 6) if te > 0 else 0.0,
            "allocation_coverage": round(alloc_coverage, 6),
            "score": _score(ratio, te),
        }

    scores = [v["score"] for v in by_trace.values()]
    summary = {
        "trace_count": len(by_trace),
        "good": sum(1 for s in scores if s == "good"),
        "fair": sum(1 for s in scores if s == "fair"),
        "poor": sum(1 for s in scores if s == "poor"),
        "unpriced": sum(1 for s in scores if s == "unpriced"),
        "overall_score": _overall(scores),
    }
    return {"by_trace": by_trace, "summary": summary}
