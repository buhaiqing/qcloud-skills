"""P4.1 — trace_cost_aggregate(): multi-dimensional CostRecord aggregation.

Aggregate CostRecords by one or more grouping keys (trace / incident / skill /
product / region / tenant / model). Returns:
  {
    "by_<dim>": {dim_value: {cost, events, priced_ratio, ...}},
    "by_<dim>_<dim2>": { "<v1>|<v2>": {...} },
    "summary": { total_cost, total_events, priced_count, unpriced_count }
  }
"""

from __future__ import annotations


def _llm(provider="openai", model="gpt-4o", region=None, tenant_id=None, input_tokens=1000):
    from copilot.trace_records import UsageEvent
    md = {}
    if tenant_id:
        md["tenant_id"] = tenant_id
    return UsageEvent(
        id=f"ue-llm-{provider}-{model}-{input_tokens}",
        trace_id=f"trc-{provider}",
        event_type="llm",
        timestamp="2026-07-25T00:00:00Z",
        provider=provider,
        model=model,
        usage={
            "input_tokens": input_tokens,
            "output_tokens": 0,
            "total_tokens": input_tokens,
        },
        metadata=md,
    )


def _api(product="cvm", action="DescribeInstances", region=None, tenant_id=None, resource_count=1):
    from copilot.trace_records import UsageEvent
    md = {}
    if tenant_id:
        md["tenant_id"] = tenant_id
    return UsageEvent(
        id=f"ue-api-{product}-{action}",
        trace_id=f"trc-{product}",
        event_type="cloud_api",
        timestamp="2026-07-25T00:00:00Z",
        product=product,
        action=action,
        resource_count=resource_count,
        region=region,
        metadata=md,
    )


def _cost(
    cost_id: str,
    total: float,
    status: str = "actual",
    trace_id: str = "trc-1",
    pricing_version: str = "v1",
    usage_ids: list[str] | None = None,
):
    from copilot.trace_records import CostRecord, CostStatus

    return CostRecord(
        id=cost_id,
        trace_id=trace_id,
        usage_event_ids=usage_ids or [],
        cost_status=CostStatus(status),
        total_cost=total,
        pricing_snapshot_version=pricing_version,
    )


def test_aggregate_by_trace_id_basic():
    """Two costs under different traces aggregate into independent buckets."""
    from copilot.trace_cost_aggregate import aggregate_costs

    records = [
        _cost("c1", 5.0, trace_id="trc-a"),
        _cost("c2", 3.0, trace_id="trc-a"),
        _cost("c3", 7.0, trace_id="trc-b"),
    ]
    out = aggregate_costs(records, by=["trace_id"])
    by_trace = out["by_trace_id"]
    assert by_trace["trc-a"]["total_cost"] == 8.0
    assert by_trace["trc-a"]["count"] == 2
    assert by_trace["trc-b"]["total_cost"] == 7.0
    assert by_trace["trc-b"]["count"] == 1


def test_aggregate_by_pricing_snapshot_version():
    """Group by pricing_snapshot_version to spot snapshot drift costs."""
    from copilot.trace_cost_aggregate import aggregate_costs

    records = [
        _cost("c1", 5.0, pricing_version="v1"),
        _cost("c2", 4.0, pricing_version="v2"),
        _cost("c3", 1.0, pricing_version="v1"),
    ]
    out = aggregate_costs(records, by=["pricing_snapshot_version"])
    by_v = out["by_pricing_snapshot_version"]
    assert by_v["v1"]["total_cost"] == 6.0
    assert by_v["v1"]["count"] == 2
    assert by_v["v2"]["total_cost"] == 4.0


def test_aggregate_by_cost_status():
    """Group by status; UNPRICED bucket should accumulate zero-cost counters."""
    from copilot.trace_cost_aggregate import aggregate_costs

    records = [
        _cost("c1", 5.0, status="actual"),
        _cost("c2", 0.0, status="unpriced"),
        _cost("c3", 0.0, status="not_applicable"),
        _cost("c4", 2.0, status="partial"),
    ]
    out = aggregate_costs(records, by=["cost_status"])
    by_s = out["by_cost_status"]
    assert by_s["actual"]["total_cost"] == 5.0
    assert by_s["unpriced"]["total_cost"] == 0.0
    assert by_s["unpriced"]["count"] == 1
    assert by_s["not_applicable"]["total_cost"] == 0.0
    assert by_s["partial"]["total_cost"] == 2.0


def test_aggregate_summary_total():
    """summary block aggregates across all groups."""
    from copilot.trace_cost_aggregate import aggregate_costs

    records = [
        _cost("c1", 5.0, status="actual"),
        _cost("c2", 0.0, status="unpriced"),
        _cost("c3", 3.0, status="partial"),
    ]
    out = aggregate_costs(records, by=["trace_id"])
    summary = out["summary"]
    assert summary["total_cost"] == 8.0
    assert summary["count"] == 3
    assert summary["priced_count"] == 2
    assert summary["unpriced_count"] == 1


def test_aggregate_compound_dimension():
    """Compound key 'pricing_snapshot_version|cost_status' joins both."""
    from copilot.trace_cost_aggregate import aggregate_costs

    records = [
        _cost("c1", 5.0, status="actual", pricing_version="v1"),
        _cost("c2", 3.0, status="partial", pricing_version="v1"),
        _cost("c3", 0.0, status="unpriced", pricing_version="v2"),
    ]
    out = aggregate_costs(
        records,
        by=["pricing_snapshot_version", "cost_status"],
    )
    by = out["by_pricing_snapshot_version|cost_status"]
    assert by["v1|actual"]["total_cost"] == 5.0
    assert by["v1|partial"]["total_cost"] == 3.0
    assert by["v2|unpriced"]["total_cost"] == 0.0


def test_aggregate_empty_record_list():
    """Empty input -> all-zero summary, empty dimensions."""
    from copilot.trace_cost_aggregate import aggregate_costs

    out = aggregate_costs([], by=["trace_id"])
    assert out["summary"]["total_cost"] == 0.0
    assert out["summary"]["count"] == 0
    assert out["summary"]["priced_count"] == 0
    assert out["summary"]["unpriced_count"] == 0
    assert out["by_trace_id"] == {}


def test_aggregate_by_event_type_counts():
    """Usage events can be grouped by event_type alongside CostRecord buckets."""
    from copilot.trace_cost_aggregate import aggregate_usage_events

    events = [
        _llm(provider="openai", input_tokens=1000),
        _llm(provider="openai", input_tokens=2000),
        _api(product="cvm"),
        _api(product="cvm"),
        _api(product="cls"),
    ]
    out = aggregate_usage_events(events, by=["event_type"])
    by_et = out["by_event_type"]
    assert by_et["llm"]["event_count"] == 2
    assert by_et["llm"]["total_tokens"] == 3000
    assert by_et["cloud_api"]["event_count"] == 3
    # cloud_api by product child
    assert by_et["cloud_api"]["by_product"]["cvm"] == 2
    assert by_et["cloud_api"]["by_product"]["cls"] == 1


def test_aggregate_usage_by_provider_for_llm():
    """LLM breakdown by (provider, model) preserves granularity."""
    from copilot.trace_cost_aggregate import aggregate_usage_events

    events = [
        _llm(provider="openai", model="gpt-4o", input_tokens=1000),
        _llm(provider="openai", model="gpt-4o", input_tokens=2000),
        _llm(provider="anthropic", model="claude-3.5-sonnet", input_tokens=500),
    ]
    out = aggregate_usage_events(events, by=["provider", "model"])
    by = out["by_provider|model"]
    assert by["openai|gpt-4o"]["event_count"] == 2
    assert by["openai|gpt-4o"]["total_tokens"] == 3000
    assert by["anthropic|claude-3.5-sonnet"]["event_count"] == 1


def test_aggregate_accepts_dimensions_set_explicitly():
    """Caller can mix cost_dimensions and usage_dimensions; both reports returned."""
    from copilot.trace_cost_aggregate import aggregate

    records = [_cost("c1", 5.0, status="actual", trace_id="trc-a")]
    events = [_llm(provider="openai", input_tokens=1000)]
    out = aggregate(
        records=records,
        events=events,
        cost_dimensions=["trace_id"],
        usage_dimensions=["provider"],
    )
    assert "by_trace_id" in out
    assert "by_provider" in out
    assert out["summary"]["total_cost"] == 5.0
