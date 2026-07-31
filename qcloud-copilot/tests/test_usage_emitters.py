"""P2.3 / P2.4 / P2.5 — UsageEvent emitters for LLM / Cloud API / Data.

Tests:
  - emit_llm_usage() returns UsageEvent with event_type='llm' and proper fields
  - emit_cloud_api_usage() returns UsageEvent with event_type='cloud_api'
  - emit_data_usage() returns UsageEvent with event_type='data'
  - All three round-trip through to_dict
  - All three honour RetryIndex (increments on retry) and persist observation_id
"""
from __future__ import annotations

import json


def test_emit_llm_usage_basic():
    from copilot.usage_emitters import emit_llm_usage

    evt = emit_llm_usage(
        trace_id="trc-llm-001",
        observation_id="obs-1",
        provider="openai",
        model="gpt-4o",
        prompt_version="rca-v2",
        input_tokens=1200,
        output_tokens=350,
        cached_tokens=200,
        reasoning_tokens=50,
        retry_index=0,
        latency_ms=420,
    )
    assert evt.event_type == "llm"
    assert evt.trace_id == "trc-llm-001"
    assert evt.observation_id == "obs-1"
    assert evt.provider == "openai"
    assert evt.model == "gpt-4o"
    assert evt.prompt_version == "rca-v2"
    assert evt.usage["input_tokens"] == 1200
    assert evt.usage["output_tokens"] == 350
    assert evt.usage["reasoning_tokens"] == 50
    # total = input + output (cached / reasoning distinct buckets)
    assert evt.usage["total_tokens"] == 1550
    assert evt.retry_index == 0


def test_emit_llm_usage_retry_index():
    from copilot.usage_emitters import emit_llm_usage

    evt = emit_llm_usage(
        trace_id="trc-llm-002",
        provider="anthropic",
        model="claude-3.5-sonnet",
        input_tokens=10,
        output_tokens=5,
        retry_index=2,
        latency_ms=100,
    )
    assert evt.event_type == "llm"
    assert evt.retry_index == 2
    assert evt.observation_id is None


def test_emit_cloud_api_usage():
    from copilot.usage_emitters import emit_cloud_api_usage

    evt = emit_cloud_api_usage(
        trace_id="trc-api-001",
        observation_id="obs-cvm-1",
        product="cvm",
        service="cvm",
        action="DescribeInstances",
        api_version="2017-03-12",
        region="ap-guangzhou",
        client_type="tccli",
        api_request_id="req-abc123",
        request_bytes=2048,
        response_bytes=8192,
        resource_count=15,
        retry_index=0,
        rate_limited=False,
        latency_ms=350,
    )
    assert evt.event_type == "cloud_api"
    assert evt.product == "cvm"
    assert evt.action == "DescribeInstances"
    assert evt.metadata["api_version"] == "2017-03-12"
    assert evt.region == "ap-guangzhou"
    assert evt.client_type == "tccli"
    assert evt.request_bytes == 2048
    assert evt.response_bytes == 8192
    assert evt.resource_count == 15
    assert evt.retry_index == 0
    assert evt.rate_limited is False
    assert evt.latency_ms == 350


def test_emit_cloud_api_usage_rate_limited():
    from copilot.usage_emitters import emit_cloud_api_usage

    evt = emit_cloud_api_usage(
        trace_id="trc-api-002",
        product="cls",
        service="cls",
        action="SearchLog",
        region="ap-shanghai",
        client_type="sdk",
        rate_limited=True,
    )
    assert evt.rate_limited is True


def test_emit_data_usage_metrics_logs():
    from copilot.usage_emitters import emit_data_usage

    evt = emit_data_usage(
        trace_id="trc-data-001",
        observation_id="obs-data-1",
        metric_points=120,
        log_bytes=4096,
        log_records=89,
        audit_events=4,
        topology_nodes=20,
        topology_edges=35,
        latency_ms=80,
    )
    assert evt.event_type == "data"
    assert evt.metric_points == 120
    assert evt.log_bytes == 4096
    assert evt.log_records == 89
    assert evt.audit_events == 4
    assert evt.topology_nodes == 20
    assert evt.topology_edges == 35
    assert evt.latency_ms == 80


def test_emit_data_usage_minimal():
    from copilot.usage_emitters import emit_data_usage

    evt = emit_data_usage(trace_id="trc-data-002")
    assert evt.event_type == "data"
    assert evt.metric_points is None
    assert evt.log_bytes is None
    assert evt.latency_ms is None


def test_emitter_returns_serializeable_dict():
    from copilot.usage_emitters import emit_cloud_api_usage, emit_data_usage, emit_llm_usage

    for evt in [
        emit_llm_usage(trace_id="t1", provider="p", model="m", input_tokens=1, output_tokens=1),
        emit_cloud_api_usage(trace_id="t2", product="p", service="s", action="a"),
        emit_data_usage(trace_id="t3", metric_points=5),
    ]:
        d = evt.to_dict()
        s = json.dumps(d)
        restored = json.loads(s)
        assert restored["trace_id"]
        assert restored["id"]
        assert restored["timestamp"]


def test_emitter_returns_unique_ids():
    """Two emits produce distinct event IDs for downstream join."""
    from copilot.usage_emitters import emit_llm_usage

    a = emit_llm_usage(trace_id="t", provider="p", model="m", input_tokens=1, output_tokens=1)
    b = emit_llm_usage(trace_id="t", provider="p", model="m", input_tokens=1, output_tokens=1)
    assert a.id != b.id
    assert a.id.startswith("ue-") or "ue-" in a.id
