"""P4.3 — usage stats: token / API request / metric / log byte / event /
topology counts across UsageEvent.

A single `usage_stats(events) -> dict` aggregates per-event-type stats into
canonical buckets:

    llm:        input_tokens / output_tokens / cached / reasoning / total / calls
    cloud_api:  call_count / rate_limited / retry_total / resource_units /
                request_bytes / response_bytes
    data:       metric_points / log_bytes / log_records / audit_events /
                topology_nodes / topology_edges

Plus `summary.event_count` totals.
"""

from __future__ import annotations


def _llm(provider="openai", input_tokens=1000, output_tokens=500, cached=0, reasoning=0):
    from copilot.trace_records import UsageEvent
    return UsageEvent(
        id=f"ue-llm-{provider}",
        trace_id="trc-p4-3",
        event_type="llm",
        timestamp="2026-07-25T00:00:00Z",
        provider=provider,
        model="gpt-4o",
        usage={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached,
            "reasoning_tokens": reasoning,
            "total_tokens": input_tokens + output_tokens + cached + reasoning,
        },
    )


def _api(product="cvm", retry_index=0, rate_limited=False, request_bytes=1024, response_bytes=2048, resource_count=1):
    from copilot.trace_records import UsageEvent
    return UsageEvent(
        id=f"ue-api-{product}",
        trace_id="trc-p4-3",
        event_type="cloud_api",
        timestamp="2026-07-25T00:00:00Z",
        product=product,
        action="DescribeInstances",
        region="ap-guangzhou",
        client_type="tccli",
        retry_index=retry_index,
        rate_limited=rate_limited,
        request_bytes=request_bytes,
        response_bytes=response_bytes,
        resource_count=resource_count,
    )


def _data(metric_points=0, log_bytes=0, log_records=0, audit_events=0, topology_nodes=0, topology_edges=0):
    from copilot.trace_records import UsageEvent
    return UsageEvent(
        id="ue-data-1",
        trace_id="trc-p4-3",
        event_type="data",
        timestamp="2026-07-25T00:00:00Z",
        metric_points=metric_points,
        log_bytes=log_bytes,
        log_records=log_records,
        audit_events=audit_events,
        topology_nodes=topology_nodes,
        topology_edges=topology_edges,
    )


def test_usage_stats_llm_token_aggregation():
    from copilot.usage_stats import usage_stats
    out = usage_stats([
        _llm(provider="openai", input_tokens=1000, output_tokens=500, cached=200),
        _llm(provider="openai", input_tokens=2000, output_tokens=0),
    ])
    assert out["llm"]["calls"] == 2
    assert out["llm"]["input_tokens"] == 3000
    assert out["llm"]["output_tokens"] == 500
    assert out["llm"]["cached_tokens"] == 200
    assert out["llm"]["reasoning_tokens"] == 0


def test_usage_stats_llm_by_provider():
    from copilot.usage_stats import usage_stats
    out = usage_stats([
        _llm(provider="openai", input_tokens=1000, output_tokens=0),
        _llm(provider="anthropic", input_tokens=500, output_tokens=0),
    ])
    by_prov = out["llm"]["by_provider"]
    assert by_prov["openai"] == 1
    assert by_prov["anthropic"] == 1


def test_usage_stats_cloud_api_call_metrics():
    from copilot.usage_stats import usage_stats
    out = usage_stats([
        _api(product="cvm", retry_index=0, rate_limited=False, request_bytes=2048, response_bytes=8192, resource_count=5),
        _api(product="cvm", retry_index=1, rate_limited=True, request_bytes=1024, response_bytes=0, resource_count=0),
        _api(product="cls", retry_index=0, rate_limited=False, request_bytes=0, response_bytes=4096, resource_count=10),
    ])
    api = out["cloud_api"]
    assert api["call_count"] == 3
    assert api["rate_limited"] == 1
    assert api["retry_total"] == 1
    assert api["request_bytes"] == 3072
    assert api["response_bytes"] == 12288
    assert api["resource_units"] == 15
    assert api["by_product"]["cvm"] == 2
    assert api["by_product"]["cls"] == 1


def test_usage_stats_data_subsystem_totals():
    from copilot.usage_stats import usage_stats
    out = usage_stats([
        _data(metric_points=120, log_bytes=4096, log_records=89),
        _data(audit_events=4, topology_nodes=20, topology_edges=35),
    ])
    data = out["data"]
    assert data["event_count"] == 2
    assert data["metric_points"] == 120
    assert data["log_bytes"] == 4096
    assert data["log_records"] == 89
    assert data["audit_events"] == 4
    assert data["topology_nodes"] == 20
    assert data["topology_edges"] == 35


def test_usage_stats_summary_event_count():
    from copilot.usage_stats import usage_stats
    out = usage_stats([
        _llm(), _llm(), _api(product="cvm"), _data(metric_points=5),
    ])
    assert out["summary"]["event_count"] == 4


def test_usage_stats_empty():
    from copilot.usage_stats import usage_stats
    out = usage_stats([])
    assert out["summary"]["event_count"] == 0
    assert out["llm"]["calls"] == 0
    assert out["cloud_api"]["call_count"] == 0
    assert out["data"]["event_count"] == 0
