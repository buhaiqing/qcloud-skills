"""P4.4 — recompute_cost_diff: re-price UsageEvents under a new PricingSnapshot
and report the diff vs the original CostRecord.

For each trace_id with both old CostRecord(s) and a fresh compute pass under
the new snapshot:
  - old_total_cost (priced only)
  - new_total_cost
  - delta = new - old
  - new_priced_count / old_priced_count
  - newly_priced: events UNPRICED before but priced now
  - newly_unpriced: events priced before but UNPRICED now

Pure function. Original UsageEvents are never mutated.
"""

from __future__ import annotations


def _llm(provider="openai", model="gpt-4o", input_tokens=1000, output_tokens=500, trace_id="trc-p4-4"):
    from copilot.trace_records import UsageEvent
    return UsageEvent(
        id=f"ue-llm-{provider}-{trace_id}",
        trace_id=trace_id,
        event_type="llm",
        timestamp="2026-07-25T00:00:00Z",
        provider=provider,
        model=model,
        usage={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
    )


def _api(product="cvm", trace_id="trc-p4-4"):
    from copilot.trace_records import UsageEvent
    return UsageEvent(
        id=f"ue-api-{product}-{trace_id}",
        trace_id=trace_id,
        event_type="cloud_api",
        timestamp="2026-07-25T00:00:00Z",
        product=product,
        action="DescribeInstances",
        region="ap-guangzhou",
        client_type="tccli",
    )


def _cost_from_compute(events, pricing, trace_id="trc-p4-4"):
    from copilot.cost import compute_cost
    return compute_cost(events=events, pricing=pricing, trace_id=trace_id)


def test_recompute_no_diff_when_pricing_unchanged():
    from copilot.cost import compute_cost
    from copilot.trace_cost_diff import recompute_cost_diff
    from copilot.trace_records import PricingSnapshot

    snap = PricingSnapshot(
        version="v1", timestamp="2026-07-25T00:00:00Z",
        prices={"llm:openai:gpt-4o:input_per_1k": 0.005, "llm:openai:gpt-4o:output_per_1k": 0.015},
    )
    events = [_llm(provider="openai", model="gpt-4o", input_tokens=1000, output_tokens=500)]
    old = compute_cost(events=events, pricing=snap, trace_id="trc-p4-4")
    diff = recompute_cost_diff(old_records=[old], events_per_trace={"trc-p4-4": events}, new_snapshot=snap)
    assert diff["by_trace_id"]["trc-p4-4"]["delta"] == 0.0
    assert diff["by_trace_id"]["trc-p4-4"]["newly_priced"] == []
    assert diff["by_trace_id"]["trc-p4-4"]["newly_unpriced"] == []


def test_recompute_price_increase_increases_delta():
    from copilot.trace_cost_diff import recompute_cost_diff
    from copilot.trace_records import PricingSnapshot

    snap_old = PricingSnapshot(
        version="v-old", timestamp="2026-07-25T00:00:00Z",
        prices={"llm:openai:gpt-4o:input_per_1k": 0.005, "llm:openai:gpt-4o:output_per_1k": 0.015},
    )
    snap_new = PricingSnapshot(
        version="v-new", timestamp="2026-07-25T01:00:00Z",
        prices={"llm:openai:gpt-4o:input_per_1k": 0.010, "llm:openai:gpt-4o:output_per_1k": 0.030},  # 2x
    )
    events = [_llm(provider="openai", model="gpt-4o", input_tokens=1000, output_tokens=500)]
    from copilot.cost import compute_cost
    old = compute_cost(events=events, pricing=snap_old, trace_id="trc-p4-4")
    diff = recompute_cost_diff(old_records=[old], events_per_trace={"trc-p4-4": events}, new_snapshot=snap_new)
    by_t = diff["by_trace_id"]["trc-p4-4"]
    assert by_t["old_total_cost"] == old.total_cost
    assert by_t["new_total_cost"] == old.total_cost * 2
    assert abs(by_t["delta"] - old.total_cost) < 1e-9


def test_recompute_newly_priced_event_promoted():
    """Snapshot adds new pricing entry -> event moves from UNPRICED to priced."""
    from copilot.trace_cost_diff import recompute_cost_diff
    from copilot.trace_records import PricingSnapshot

    snap_old = PricingSnapshot(
        version="v-old", timestamp="2026-07-25T00:00:00Z", prices={},
    )
    snap_new = PricingSnapshot(
        version="v-new", timestamp="2026-07-25T01:00:00Z",
        prices={"api:cvm:DescribeInstances:per_call": 0.001},
    )
    api_event = _api(product="cvm")
    from copilot.cost import compute_cost
    old = compute_cost(events=[api_event], pricing=snap_old, trace_id="trc-p4-4")
    assert old.cost_status.value == "unpriced"

    diff = recompute_cost_diff(
        old_records=[old], events_per_trace={"trc-p4-4": [api_event]}, new_snapshot=snap_new,
    )
    by_t = diff["by_trace_id"]["trc-p4-4"]
    assert by_t["old_priced_count"] == 0
    assert by_t["new_priced_count"] == 1
    assert api_event.id in by_t["newly_priced"]
    assert by_t["new_total_cost"] == 0.001


def test_recompute_keeps_original_records_intact():
    """P3.2 invariant: original CostRecord is not mutated; UsageEvent unchanged."""
    from copilot.cost import compute_cost
    from copilot.trace_cost_diff import recompute_cost_diff
    from copilot.trace_records import PricingSnapshot

    snap_old = PricingSnapshot(
        version="v-old", timestamp="2026-07-25T00:00:00Z", prices={},
    )
    snap_new = PricingSnapshot(
        version="v-new", timestamp="2026-07-25T01:00:00Z",
        prices={"llm:openai:gpt-4o:input_per_1k": 0.005, "llm:openai:gpt-4o:output_per_1k": 0.015},
    )
    events = [_llm(provider="openai", model="gpt-4o", input_tokens=1000, output_tokens=500)]
    old = compute_cost(events=events, pricing=snap_old, trace_id="trc-p4-4")

    before_total = old.total_cost
    before_status = old.cost_status
    before_meta = dict(old.metadata or {})

    _ = recompute_cost_diff(
        old_records=[old], events_per_trace={"trc-p4-4": events}, new_snapshot=snap_new,
    )
    assert old.total_cost == before_total
    assert old.cost_status == before_status
    assert dict(old.metadata or {}) == before_meta
    # UsageEvent untouched (no extra keys)
    assert events[0].metadata == {}


def test_recompute_summary_aggregates_deltas():
    from copilot.cost import compute_cost
    from copilot.trace_cost_diff import recompute_cost_diff
    from copilot.trace_records import PricingSnapshot

    snap_old = PricingSnapshot(
        version="v-old", timestamp="2026-07-25T00:00:00Z",
        prices={"llm:openai:gpt-4o:input_per_1k": 0.005, "llm:openai:gpt-4o:output_per_1k": 0.015},
    )
    snap_new = PricingSnapshot(
        version="v-new", timestamp="2026-07-25T01:00:00Z",
        prices={"llm:openai:gpt-4o:input_per_1k": 0.010, "llm:openai:gpt-4o:output_per_1k": 0.030},
    )
    e_a = [_llm(provider="openai", model="gpt-4o", input_tokens=1000, output_tokens=0)]
    e_b = [_llm(provider="openai", model="gpt-4o", input_tokens=2000, output_tokens=0)]
    old_a = compute_cost(events=e_a, pricing=snap_old, trace_id="trc-a")
    old_b = compute_cost(events=e_b, pricing=snap_old, trace_id="trc-b")
    diff = recompute_cost_diff(
        old_records=[old_a, old_b],
        events_per_trace={"trc-a": e_a, "trc-b": e_b},
        new_snapshot=snap_new,
    )
    summary = diff["summary"]
    assert summary["trace_count"] == 2
    # Both doubled, so delta == old_total
    assert abs(summary["total_delta"] - (old_a.total_cost + old_b.total_cost)) < 1e-9
    assert summary["trace_count"] == 2
