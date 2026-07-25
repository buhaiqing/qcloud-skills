"""P4.2 — LLM vs Cloud API cost split + scope in aggregate.

Adds cost_by_event_type bucket inside aggregate() output so a downstream
CLI / script can answer "what fraction of a trace's priced cost came from
LLM tokens vs Cloud API calls?". No events are mutated; the split is derived
from each CostRecord.metadata["priced_count"] + per-event-type counts.
"""

from __future__ import annotations


def _llm(provider="openai", model="gpt-4o", input_tokens=1000, output_tokens=0):
    from copilot.trace_records import UsageEvent
    return UsageEvent(
        id=f"ue-llm-{provider}",
        trace_id="trc-p4-2",
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
        id=f"ue-api-{product}",
        trace_id="trc-p4-2",
        event_type="cloud_api",
        timestamp="2026-07-25T00:00:00Z",
        product=product,
        action=action,
    )


def _cost(
    cost_id: str,
    total: float,
    status: str = "actual",
    trace_id: str = "trc-p4-2",
    pricing_version: str = "v1",
    usage_ids: list[str] | None = None,
    *,
    llm_count: int = 0,
    api_count: int = 0,
    data_count: int = 0,
):
    from copilot.trace_records import CostRecord, CostStatus
    return CostRecord(
        id=cost_id,
        trace_id=trace_id,
        usage_event_ids=usage_ids or [],
        cost_status=CostStatus(status),
        total_cost=total,
        pricing_snapshot_version=pricing_version,
        metadata={
            "priced_count": llm_count + api_count,
            "total_events": llm_count + api_count + data_count,
            "by_event_type": {"llm": llm_count, "cloud_api": api_count, "data": data_count},
        },
    )


def test_cost_by_event_type_basic():
    """aggregate() emits cost_by_event_type with llm/cloud_api/data buckets."""
    from copilot.trace_cost_aggregate import aggregate

    records = [
        _cost("c1", 3.0, llm_count=2, api_count=1),
    ]
    events = [
        _llm(input_tokens=1000),
        _llm(input_tokens=2000),
        _api(product="cvm"),
    ]
    out = aggregate(
        records=records,
        events=events,
        cost_dimensions=["trace_id"],
        usage_dimensions=["event_type"],
    )
    split = out["cost_by_event_type"]
    # Single record shared; bucket proportions follow event-type counts (2:1).
    assert "llm" in split
    assert "cloud_api" in split
    # Weights: llm 2, api 1 -> llm 2/3 of 3.0 = 2.0, api 1/3 of 3.0 = 1.0.
    assert abs(split["llm"] - 2.0) < 1e-9
    assert abs(split["cloud_api"] - 1.0) < 1e-9


def test_cost_by_event_type_unpriced_record_excluded():
    """cost_by_event_type only allocates from priced records."""
    from copilot.trace_cost_aggregate import aggregate

    records = [
        _cost("c1", 0.0, status="unpriced", llm_count=5),
        _cost("c2", 4.0, status="actual", llm_count=2, api_count=2),
    ]
    out = aggregate(
        records=records,
        events=[_llm(), _api()],
        cost_dimensions=["trace_id"],
        usage_dimensions=["event_type"],
    )
    split = out["cost_by_event_type"]
    # Only c2 contributes; 50/50 split
    assert abs(split["llm"] - 2.0) < 1e-9
    assert abs(split["cloud_api"] - 2.0) < 1e-9


def test_cost_by_event_type_no_event_type_breakdown_in_metadata():
    """When metadata lacks by_event_type, allocation is single-bucket equal across types observed."""
    from copilot.trace_cost_aggregate import aggregate
    from copilot.trace_records import CostRecord, CostStatus

    rec = CostRecord(
        id="c1",
        trace_id="trc-p4-2",
        usage_event_ids=[],
        cost_status=CostStatus.ACTUAL,
        total_cost=9.0,
        pricing_snapshot_version="v1",
        metadata={"priced_count": 3, "total_events": 3},  # no by_event_type
    )
    out = aggregate(
        records=[rec],
        events=[_llm(), _api(), _api(product="cls")],
        cost_dimensions=["trace_id"],
        usage_dimensions=["event_type"],
    )
    split = out["cost_by_event_type"]
    # 3 priced, 2 types in events => llm: 1/2 share=4.5, cloud_api: 1/2 share=4.5
    assert abs(split["llm"] - 4.5) < 1e-9
    assert abs(split["cloud_api"] - 4.5) < 1e-9


def test_cost_by_event_type_empty_record_list():
    """Empty records yields empty split (no cost to allocate)."""
    from copilot.trace_cost_aggregate import aggregate

    out = aggregate(
        records=[],
        events=[],
        cost_dimensions=["trace_id"],
        usage_dimensions=["event_type"],
    )
    assert out["cost_by_event_type"] == {}


def test_cost_by_event_type_data_only_paid_record():
    """A priced record with only data events allocates only to data (not llm/api)."""
    from copilot.trace_cost_aggregate import aggregate
    from copilot.trace_records import UsageEvent

    rec = _cost("c1", 5.0, status="actual", llm_count=0, api_count=0, data_count=3)
    out = aggregate(
        records=[rec],
        events=[UsageEvent(
            id="ue-data", trace_id="trc-p4-2", event_type="data",
            timestamp="2026-07-25T00:00:00Z", metric_points=10,
        )],
        cost_dimensions=["trace_id"],
        usage_dimensions=["event_type"],
    )
    split = out["cost_by_event_type"]
    assert split.get("data") == 5.0
    assert "llm" not in split
    assert "cloud_api" not in split
