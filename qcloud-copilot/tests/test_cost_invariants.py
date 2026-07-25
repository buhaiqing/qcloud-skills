"""P3.1 + P3.2 — cost computation + invariants enforcement.

Pricing key format:
  - LLM:    "llm:<provider>:<model>:<input_per_1k|output_per_1k|cached_per_1k|reasoning_per_1k>"
  - API:    "api:<product>:<action>:per_call"
  - Data:   no pricing entries (data reads default to NOT_APPLICABLE)

Invariant (P3.5):
  total_cost == 0  <=>  cost_status in {UNPRICED, NOT_APPLICABLE}
"""

from __future__ import annotations


def _llm(provider="openai", model="gpt-4o", input_tokens=1000, output_tokens=0):
    from copilot.trace_records import UsageEvent
    return UsageEvent(
        id=f"ue-llm-{provider}",
        trace_id="trc-cost",
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


def _api(product="cvm", action="DescribeInstances"):
    from copilot.trace_records import UsageEvent
    return UsageEvent(
        id="ue-api-cvm",
        trace_id="trc-cost",
        event_type="cloud_api",
        timestamp="2026-07-25T00:00:00Z",
        product=product,
        action=action,
    )


def _data():
    from copilot.trace_records import UsageEvent
    return UsageEvent(
        id="ue-data",
        trace_id="trc-cost",
        event_type="data",
        timestamp="2026-07-25T00:00:00Z",
        metric_points=10,
    )


# ---------------------------------------------------------------------------
# P3.1 — compute_cost status logic
# ---------------------------------------------------------------------------


def test_compute_cost_actual_when_all_priced():
    from copilot.cost import compute_cost
    from copilot.trace_records import PricingSnapshot
    from copilot.trace_records import CostStatus

    snap = PricingSnapshot(
        version="v1",
        timestamp="2026-07-25T00:00:00Z",
        prices={
            "llm:openai:gpt-4o:input_per_1k": 0.005,
            "llm:openai:gpt-4o:output_per_1k": 0.015,
        },
    )
    rec = compute_cost(
        events=[_llm(provider="openai", model="gpt-4o", input_tokens=1000, output_tokens=500)],
        pricing=snap,
    )
    assert rec.cost_status == CostStatus.ACTUAL
    assert rec.total_cost > 0
    assert rec.currency == "CNY"
    assert rec.pricing_snapshot_version == "v1"


def test_compute_cost_unpriced_when_no_price_entries():
    from copilot.cost import compute_cost
    from copilot.trace_records import PricingSnapshot, CostStatus

    empty = PricingSnapshot(version="v1", timestamp="2026-07-25T00:00:00Z", prices={})
    rec = compute_cost(events=[_llm()], pricing=empty)
    assert rec.cost_status == CostStatus.UNPRICED
    assert rec.total_cost == 0.0


def test_compute_cost_partial_when_some_priced():
    from copilot.cost import compute_cost
    from copilot.trace_records import PricingSnapshot, CostStatus

    snap = PricingSnapshot(
        version="v1",
        timestamp="2026-07-25T00:00:00Z",
        prices={"llm:openai:gpt-4o:input_per_1k": 0.005},
    )
    rec = compute_cost(
        events=[
            _llm(provider="openai", model="gpt-4o", input_tokens=1000, output_tokens=0),
            _llm(provider="anthropic", model="claude-3.5-sonnet", input_tokens=500, output_tokens=0),
        ],
        pricing=snap,
    )
    assert rec.cost_status == CostStatus.PARTIAL
    assert abs(rec.total_cost - 0.005) < 1e-12


def test_compute_cost_not_applicable_for_data_only():
    from copilot.cost import compute_cost
    from copilot.trace_records import PricingSnapshot, CostStatus

    snap = PricingSnapshot(version="v1", timestamp="2026-07-25T00:00:00Z", prices={})
    rec = compute_cost(events=[_data()], pricing=snap)
    assert rec.cost_status == CostStatus.NOT_APPLICABLE
    assert rec.total_cost == 0.0


# ---------------------------------------------------------------------------
# P3.5 — assert_cost_invariants
# ---------------------------------------------------------------------------


def test_assert_invariants_accepts_consistent_actual():
    from copilot.cost import assert_cost_invariants
    from copilot.trace_records import CostRecord, CostStatus

    ok = CostRecord(
        id="c1", trace_id="t", usage_event_ids=["u1"],
        cost_status=CostStatus.ACTUAL, total_cost=0.5,
    )
    assert_cost_invariants(ok)


def test_assert_invariants_accepts_zero_with_unpriced():
    from copilot.cost import assert_cost_invariants
    from copilot.trace_records import CostRecord, CostStatus

    ok = CostRecord(
        id="c1", trace_id="t", usage_event_ids=["u1"],
        cost_status=CostStatus.UNPRICED, total_cost=0.0,
    )
    assert_cost_invariants(ok)


def test_assert_invariants_rejects_actual_with_zero():
    from copilot.cost import assert_cost_invariants
    from copilot.trace_records import CostRecord, CostStatus
    import pytest

    bad = CostRecord(
        id="c1", trace_id="t", usage_event_ids=["u1"],
        cost_status=CostStatus.ACTUAL, total_cost=0.0,
    )
    with pytest.raises(AssertionError, match="total_cost"):
        assert_cost_invariants(bad)


def test_assert_invariants_rejects_unpriced_with_nonzero():
    from copilot.cost import assert_cost_invariants
    from copilot.trace_records import CostRecord, CostStatus
    import pytest

    bad = CostRecord(
        id="c1", trace_id="t", usage_event_ids=["u1"],
        cost_status=CostStatus.UNPRICED, total_cost=0.5,
    )
    with pytest.raises(AssertionError, match="UNPRICED"):
        assert_cost_invariants(bad)


def test_assert_invariants_rejects_na_with_nonzero():
    from copilot.cost import assert_cost_invariants
    from copilot.trace_records import CostRecord, CostStatus
    import pytest

    ok = CostRecord(
        id="c1", trace_id="t", usage_event_ids=["u1"],
        cost_status=CostStatus.NOT_APPLICABLE, total_cost=0.0,
    )
    assert_cost_invariants(ok)

    bad = CostRecord(
        id="c1", trace_id="t", usage_event_ids=["u1"],
        cost_status=CostStatus.NOT_APPLICABLE, total_cost=0.1,
    )
    with pytest.raises(AssertionError, match="NOT_APPLICABLE"):
        assert_cost_invariants(bad)


# ---------------------------------------------------------------------------
# P3.2 — PricingSnapshot behavior
# ---------------------------------------------------------------------------


def test_pricing_snapshot_zero_prices_treated_as_unpriced():
    from copilot.cost import compute_cost, assert_cost_invariants
    from copilot.trace_records import PricingSnapshot, CostStatus

    snap = PricingSnapshot(
        version="v1",
        timestamp="2026-07-25T00:00:00Z",
        prices={
            "llm:openai:gpt-4o:input_per_1k": 0.0,
            "llm:openai:gpt-4o:output_per_1k": 0.0,
        },
    )
    rec = compute_cost(events=[_llm()], pricing=snap)
    assert rec.cost_status == CostStatus.UNPRICED
    assert_cost_invariants(rec)


def test_pricing_snapshot_recompute_keeps_usage_immutable():
    from copilot.cost import compute_cost
    from copilot.trace_records import PricingSnapshot

    original = _llm(input_tokens=1000, output_tokens=500)
    snap_empty = PricingSnapshot(version="v-old", timestamp="2026-07-25T00:00:00Z", prices={})
    rec_old = compute_cost(events=[original], pricing=snap_empty)
    assert rec_old.cost_status.value == "unpriced"

    snap_paid = PricingSnapshot(
        version="v2",
        timestamp="2026-07-25T01:00:00Z",
        prices={
            "llm:openai:gpt-4o:input_per_1k": 0.005,
            "llm:openai:gpt-4o:output_per_1k": 0.015,
        },
    )
    rec_new = compute_cost(events=[original], pricing=snap_paid)
    assert rec_new.cost_status.value == "actual"
    assert original.metadata == {}
