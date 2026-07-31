"""P3.1 + P3.2 — cost computation + invariant enforcement.

Pricing key format:
  - LLM:    "llm:<provider>:<model>:<input_per_1k|output_per_1k|cached_per_1k|reasoning_per_1k>"
  - API:    "api:<product>:<action>:per_call"
  - Data:   no pricing entries (data reads default to NOT_APPLICABLE)

Invariant (P3.5):
  total_cost == 0   <=>   cost_status in {UNPRICED, NOT_APPLICABLE}
"""
from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import UTC, datetime

from copilot.trace_records import (
    CostRecord,
    CostStatus,
    PricingSnapshot,
    UsageEvent,
)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _llm_input_key(evt: UsageEvent) -> str | None:
    if not (evt.provider and evt.model):
        return None
    return f"llm:{evt.provider}:{evt.model}:input_per_1k"


def _llm_output_key(evt: UsageEvent) -> str | None:
    if not (evt.provider and evt.model):
        return None
    return f"llm:{evt.provider}:{evt.model}:output_per_1k"


def _llm_cached_key(evt: UsageEvent) -> str | None:
    if not (evt.provider and evt.model):
        return None
    return f"llm:{evt.provider}:{evt.model}:cached_per_1k"


def _llm_reasoning_key(evt: UsageEvent) -> str | None:
    if not (evt.provider and evt.model):
        return None
    return f"llm:{evt.provider}:{evt.model}:reasoning_per_1k"


def _api_call_key(evt: UsageEvent) -> str | None:
    if not (evt.product and evt.action):
        return None
    return f"api:{evt.product}:{evt.action}:per_call"


def _llm_total_tokens(evt: UsageEvent) -> int:
    usage = evt.usage or {}
    return sum(int(usage.get(k, 0) or 0) for k in
               ("input_tokens", "output_tokens", "cached_tokens", "reasoning_tokens"))


def _event_cost(evt: UsageEvent, pricing: PricingSnapshot) -> tuple[float, bool]:
    """Return (cost, priced) for one event.

    LLM rules: input_per_1k and output_per_1k are MANDATORY buckets; cached /
    reasoning are OPTIONAL — missing or zero prices skip that bucket without
    dragging `priced` to False.
    """
    prices = pricing.prices or {}
    if evt.event_type == "llm":
        if _llm_total_tokens(evt) == 0:
            return 0.0, False
        usage = evt.usage or {}
        inp = int(usage.get("input_tokens", 0) or 0)
        out = int(usage.get("output_tokens", 0) or 0)
        cached = int(usage.get("cached_tokens", 0) or 0)
        reasoning = int(usage.get("reasoning_tokens", 0) or 0)

        inp_k = _llm_input_key(evt)
        out_k = _llm_output_key(evt)
        if not (inp_k and out_k):
            return 0.0, False
        inp_p = prices.get(inp_k) if inp > 0 else None
        out_p = prices.get(out_k) if out > 0 else None
        # Per-bucket mandatory: if the bucket has tokens, its price must be > 0.
        if inp > 0 and (inp_p is None or inp_p == 0):
            return 0.0, False
        if out > 0 and (out_p is None or out_p == 0):
            return 0.0, False

        cost = (inp / 1000.0) * (inp_p or 0.0) + (out / 1000.0) * (out_p or 0.0)


        # Optional buckets: only add when price is positive.
        cache_k = _llm_cached_key(evt)
        if cached > 0 and cache_k:
            cache_p = prices.get(cache_k)
            if cache_p and cache_p > 0:
                cost += (cached / 1000.0) * cache_p
        reasoning_k = _llm_reasoning_key(evt)
        if reasoning > 0 and reasoning_k:
            r_p = prices.get(reasoning_k)
            if r_p and r_p > 0:
                cost += (reasoning / 1000.0) * r_p
        return cost, True

    if evt.event_type == "cloud_api":
        k = _api_call_key(evt)
        if not k:
            return 0.0, False
        p = prices.get(k)
        if p is None or p == 0:
            return 0.0, False
        return p, True

    return 0.0, False


def compute_cost(
    *,
    events: Iterable[UsageEvent],
    pricing: PricingSnapshot,
    currency: str = "CNY",
    trace_id: str | None = None,
) -> CostRecord:
    """Compute a CostRecord from usage events and a pricing snapshot.

    Status logic:
      - empty event list                                -> NOT_APPLICABLE
      - all events data-reads + none priced             -> NOT_APPLICABLE
      - all billable events priced                      -> ACTUAL
      - some billable events priced, others not         -> PARTIAL
      - no billable events priced at all                -> UNPRICED
    """
    ev_list = list(events)
    total = 0.0
    priced_count = 0
    has_billable = False
    has_data_only = True
    for evt in ev_list:
        if evt.event_type != "data":
            has_data_only = False
            has_billable = True
        cost, priced = _event_cost(evt, pricing)
        total += cost
        if priced:
            priced_count += 1

    if not ev_list:
        status = CostStatus.NOT_APPLICABLE
    elif priced_count == 0:
        if not has_billable and has_data_only:
            status = CostStatus.NOT_APPLICABLE
        else:
            status = CostStatus.UNPRICED
    elif priced_count == len(ev_list):
        status = CostStatus.ACTUAL
    else:
        status = CostStatus.PARTIAL

    if abs(total) < 1e-12 and status in {CostStatus.ACTUAL, CostStatus.PARTIAL}:
        status = CostStatus.UNPRICED if has_billable else CostStatus.NOT_APPLICABLE

    return CostRecord(
        id=f"cost-{uuid.uuid4().hex[:12]}",
        trace_id=trace_id or (ev_list[0].trace_id if ev_list else "unknown"),
        usage_event_ids=[e.id for e in ev_list],
        cost_status=status,
        total_cost=total,
        currency=currency,
        pricing_snapshot_version=pricing.version,
        allocation_keys={},
        metadata={
            "priced_count": priced_count,
            "total_events": len(ev_list),
            "computed_at": _utc_now(),
            "pricing_snapshot_timestamp": pricing.timestamp,
        },
    )


def assert_cost_invariants(cost: CostRecord) -> None:
    """Enforce the 5-state / total_cost invariant."""
    zero = abs(cost.total_cost) < 1e-12
    if zero and cost.cost_status not in {CostStatus.UNPRICED, CostStatus.NOT_APPLICABLE}:
        raise AssertionError(
            f"cost invariant violated: total_cost=0 with cost_status="
            f"{cost.cost_status.value.upper()}; UNPRICED or NOT_APPLICABLE expected."
        )
    if not zero and cost.cost_status in {CostStatus.UNPRICED, CostStatus.NOT_APPLICABLE}:
        raise AssertionError(
            f"cost invariant violated: {cost.cost_status.value.upper()} but total_cost="
            f"{cost.total_cost}; ACTUAL / PARTIAL / ESTIMATED expected."
        )
