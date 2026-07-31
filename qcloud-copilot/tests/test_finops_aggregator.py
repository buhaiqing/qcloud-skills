"""P2.9.b — aggregate_finops_summary: FinOps summary from raw usage events.

Rules:
  - LLM tokens aggregated by provider
  - Cloud API calls counted + by product + rate-limited + retry + bytes
  - Data reads summed (metric / log / audit / topology)
  - Operation idempotent
  - Empty input -> zeros across the board
"""

from __future__ import annotations


def _llm(provider: str = "openai", model: str = "gpt-4o", **tokens):
    from copilot.trace_records import UsageEvent

    usage = {}
    for k, v in tokens.items():
        usage[k] = v
    if "total_tokens" not in usage:
        usage["total_tokens"] = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
    return UsageEvent(
        id=f"ue-llm-{provider}",
        trace_id="trc-fin",
        event_type="llm",
        timestamp="2026-07-25T00:00:00Z",
        provider=provider,
        model=model,
        usage=usage,
    )


def _api(product: str = "cvm", **kwargs):
    from copilot.trace_records import UsageEvent

    defaults = {
        "id": f"ue-api-{product}",
        "trace_id": "trc-fin",
        "event_type": "cloud_api",
        "timestamp": "2026-07-25T00:00:00Z",
        "product": product,
        "action": "DescribeInstances",
        "retry_index": 0,
        "rate_limited": False,
    }
    defaults.update(kwargs)
    return UsageEvent(**defaults)


def _data(**kwargs):
    from copilot.trace_records import UsageEvent

    defaults = {
        "id": "ue-data-1",
        "trace_id": "trc-fin",
        "event_type": "data",
        "timestamp": "2026-07-25T00:00:00Z",
    }
    defaults.update(kwargs)
    return UsageEvent(**defaults)


def test_aggregate_finops_empty():
    from copilot.summary_aggregator import aggregate_finops_summary

    summary = aggregate_finops_summary([], trace_id="t")
    assert summary.usage_summary["llm"]["total_tokens"] == 0
    assert summary.usage_summary["llm"]["by_provider"] == {}
    assert summary.usage_summary["cloud_api"]["total_calls"] == 0
    assert summary.usage_summary["data"]["metric_points"] == 0
    assert summary.cost_summary["status"] == "not_applicable"


def test_aggregate_finops_llm_tokens_by_provider():
    from copilot.summary_aggregator import aggregate_finops_summary

    events = [
        _llm(provider="openai", input_tokens=100, output_tokens=50, cached_tokens=20),
        _llm(provider="openai", input_tokens=200, output_tokens=80, cached_tokens=30),
        _llm(provider="anthropic", input_tokens=300, output_tokens=100, reasoning_tokens=40),
    ]
    summary = aggregate_finops_summary(events, trace_id="t")
    llm = summary.usage_summary["llm"]
    assert llm["input_tokens"] == 600
    assert llm["output_tokens"] == 230
    assert llm["cached_tokens"] == 50
    assert llm["reasoning_tokens"] == 40
    assert llm["by_provider"]["openai"]["input"] == 300
    assert llm["by_provider"]["openai"]["output"] == 130
    assert llm["by_provider"]["anthropic"]["reasoning"] == 40


def test_aggregate_finops_cloud_api_counts():
    from copilot.summary_aggregator import aggregate_finops_summary

    events = [
        _api(product="cvm", retry_index=0, rate_limited=False, request_bytes=1024, response_bytes=2048),
        _api(product="cvm", retry_index=1, rate_limited=True, request_bytes=1024),
        _api(product="cls", retry_index=0, rate_limited=False, response_bytes=4096, resource_count=50),
    ]
    summary = aggregate_finops_summary(events, trace_id="t")
    api = summary.usage_summary["cloud_api"]
    assert api["total_calls"] == 3
    assert api["rate_limited"] == 1
    assert api["retry_count"] == 1
    assert api["resource_units"] == 50
    assert api["request_bytes"] == 2048
    assert api["response_bytes"] == 6144
    assert api["calls_by_product"] == {"cvm": 2, "cls": 1}


def test_aggregate_finops_data_read_stats():
    from copilot.summary_aggregator import aggregate_finops_summary

    events = [
        _data(metric_points=120, log_bytes=4096, log_records=89),
        _data(audit_events=4, topology_nodes=20, topology_edges=35),
    ]
    summary = aggregate_finops_summary(events, trace_id="t")
    data = summary.usage_summary["data"]
    assert data["metric_points"] == 120
    assert data["log_bytes"] == 4096
    assert data["log_records"] == 89
    assert data["audit_events"] == 4
    assert data["topology_nodes"] == 20
    assert data["topology_edges"] == 35


def test_aggregate_finops_idempotent():
    from copilot.summary_aggregator import aggregate_finops_summary

    events = [
        _llm(provider="openai", input_tokens=10, output_tokens=5),
        _api(product="cvm", retry_index=0),
        _data(metric_points=5),
    ]
    a1 = aggregate_finops_summary(events, trace_id="t")
    a2 = aggregate_finops_summary(events, trace_id="t")
    assert a1.to_dict() == a2.to_dict()


def test_aggregate_finops_returns_dataclass_instance():
    from copilot.summary_aggregator import aggregate_finops_summary
    from copilot.trace_records import FinOpsSummary

    summary = aggregate_finops_summary([], trace_id="t")
    assert isinstance(summary, FinOpsSummary)


def test_aggregate_finops_mixed_events_aggregated():
    """Combined event types aggregate independently into separate sub-dicts."""
    from copilot.summary_aggregator import aggregate_finops_summary

    events = [
        _llm(provider="openai", input_tokens=100, output_tokens=50),
        _api(product="cvm"),
        _data(metric_points=10),
    ]
    summary = aggregate_finops_summary(events, trace_id="t")
    usage = summary.usage_summary
    assert usage["llm"]["input_tokens"] == 100
    assert usage["cloud_api"]["total_calls"] == 1
    assert usage["data"]["metric_points"] == 10
