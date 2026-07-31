"""P4.4 — recompute_cost_diff.

Re-price UsageEvents under a new PricingSnapshot and report per-trace delta.

Inputs:
  - old_records: iterable of CostRecord (one per trace)
  - events_per_trace: {trace_id: [UsageEvent]}
  - new_snapshot: PricingSnapshot

Output:
  {
    "by_trace_id": {trace_id: {old_total_cost, new_total_cost, delta,
                                old_priced_count, new_priced_count,
                                newly_priced: [event_id],
                                newly_unpriced: [event_id]}},
    "summary": {trace_count, total_delta, total_old, total_new}
  }

Pure function. Original UsageEvents / CostRecords never mutated.

Approximation note: when the old snapshot is no longer available, we use
the recorded `metadata.priced_count` to infer which usage_event_ids were
priced before (taking the first N ids in order). Newly_priced is the
residual priced-now ∧ previously-not-priced; newly_unpriced is the
billable-now-unpriced set.
"""
from __future__ import annotations

from collections.abc import Iterable

from copilot.cost import _event_cost, compute_cost
from copilot.trace_records import (
    CostRecord,
    PricingSnapshot,
)


def recompute_cost_diff(
    *,
    old_records: Iterable[CostRecord],
    events_per_trace: dict[str, list],
    new_snapshot: PricingSnapshot,
) -> dict:
    by_trace: dict[str, dict] = {}
    total_old = 0.0
    total_new = 0.0

    for rec in old_records:
        trace_id = rec.trace_id
        events = list(events_per_trace.get(trace_id, []))
        new_rec = compute_cost(events=events, pricing=new_snapshot, trace_id=trace_id)
        md = rec.metadata or {}
        old_priced_count = int(md.get("priced_count", 0) or 0)
        new_metadata = new_rec.metadata or {}
        new_priced_count = int(new_metadata.get("priced_count", 0) or 0)

        priced_now: set[str] = set()
        not_priced_now: list[str] = []
        for evt in events:
            cost, priced = _event_cost(evt, new_snapshot)
            if priced and cost > 0:
                priced_now.add(evt.id)
            elif evt.event_type != "data":
                not_priced_now.append(evt.id)

        all_ids = list(rec.usage_event_ids or [])
        old_priced_id_set = set(all_ids[:old_priced_count])
        newly_priced_ids = [
            uid for uid in all_ids if uid in priced_now and uid not in old_priced_id_set
        ]
        newly_unpriced_ids = [
            uid for uid in not_priced_now if uid in old_priced_id_set
        ]

        delta = round(new_rec.total_cost - rec.total_cost, 9)
        by_trace[trace_id] = {
            "old_total_cost": round(rec.total_cost, 9),
            "new_total_cost": round(new_rec.total_cost, 9),
            "delta": delta,
            "old_priced_count": old_priced_count,
            "new_priced_count": new_priced_count,
            "old_pricing_snapshot_version": rec.pricing_snapshot_version,
            "new_pricing_snapshot_version": new_snapshot.version,
            "newly_priced": newly_priced_ids,
            "newly_unpriced": newly_unpriced_ids,
            "old_cost_status": rec.cost_status.value,
            "new_cost_status": new_rec.cost_status.value,
        }
        total_old += rec.total_cost
        total_new += new_rec.total_cost

    return {
        "by_trace_id": by_trace,
        "summary": {
            "trace_count": len(by_trace),
            "total_old": round(total_old, 9),
            "total_new": round(total_new, 9),
            "total_delta": round(total_new - total_old, 9),
        },
    }
