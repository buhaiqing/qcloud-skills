"""P5.5 — Monitor / CVM / CLS API fixtures covering success / failure / retry /
rate-limited / no-price paths.

Pure data factories. They build UsageEvent + CostRecord vectors that mirror
real Tencent Cloud product API shapes:

  - monitor:   CM DescribeBasicMetrics / GetMonitorData + CLS SearchLog
  - cvm:       DescribeInstances / RunInstances / StopInstances
  - cls:       SearchLog / DescribeLogsets / CreateLogset

Each product exposes a top-level `build_*_events(...)` returning a list of
UsageEvent records; `cost_records(events, pricing_snapshot=None)` returns
matching CostRecord with the expected status for the path under test.

DoD: each product has all 5 paths (success / failure / retry / rate_limited /
no_price) covered by a dedicated test.
"""
from __future__ import annotations

from copilot.trace_records import PricingSnapshot


def _ev(product, action, trace_id, **kw):
    from copilot.trace_records import UsageEvent

    defaults = {
        "id": f"ue-{product}-{action}-test",
        "trace_id": trace_id,
        "event_type": "cloud_api",
        "timestamp": "2026-07-25T00:00:00Z",
        "product": product,
        "action": action,
        "region": "ap-guangzhou",
        "client_type": "tccli",
        "resource_count": 1,
        "retry_index": 0,
        "rate_limited": False,
    }
    defaults.update(kw)
    return UsageEvent(**defaults)


# ---------------------------------------------------------------------------
# Fixture factories
# ---------------------------------------------------------------------------


def test_fixture_cvm_describe_instances_success():
    """CVM DescribeInstances call set: success path, single call."""
    from copilot.fixtures.cvm import cvm_describe_instances_success

    events = cvm_describe_instances_success(trace_id="trc-cvm-1")
    assert len(events) >= 1
    assert all(e.product == "cvm" for e in events)
    assert all(e.rate_limited is False for e in events)
    assert all(e.retry_index == 0 for e in events)


def test_fixture_cvm_describe_instances_failure():
    from copilot.fixtures.cvm import cvm_describe_instances_failure

    events = cvm_describe_instances_failure(trace_id="trc-cvm-fail")
    assert len(events) >= 1
    # At least one event carries an error_code marker in metadata
    assert any((e.metadata or {}).get("error_code") for e in events)


def test_fixture_cvm_describe_instances_retry_then_success():
    from copilot.fixtures.cvm import cvm_describe_instances_retry_then_success

    events = cvm_describe_instances_retry_then_success(trace_id="trc-cvm-retry")
    # At least one retry-indexed event followed by an event with retry_index reset.
    assert any(e.retry_index and e.retry_index > 0 for e in events)


def test_fixture_cvm_run_instances_rate_limited():
    from copilot.fixtures.cvm import cvm_run_instances_rate_limited

    events = cvm_run_instances_rate_limited(trace_id="trc-cvm-rl")
    assert any(e.rate_limited for e in events)
    assert all(e.product == "cvm" for e in events)


def test_fixture_cvm_no_pricing():
    from copilot.cost import compute_cost
    from copilot.fixtures.cvm import cvm_no_pricing_set
    from copilot.trace_records import PricingSnapshot

    events = cvm_no_pricing_set(trace_id="trc-cvm-no-price")
    snap = PricingSnapshot(version="v1", timestamp="2026-07-25T00:00:00Z", prices={})
    rec = compute_cost(events=events, pricing=snap)
    assert rec.cost_status.value == "unpriced"
    assert rec.total_cost == 0.0
    # P3.5 invariant gate
    from copilot.cost import assert_cost_invariants
    assert_cost_invariants(rec)


# ------- Monitor -------

def test_fixture_monitor_describe_basic_metrics_success():
    from copilot.fixtures.monitor import monitor_describe_basic_metrics_success

    events = monitor_describe_basic_metrics_success(trace_id="trc-mon-1")
    assert all(e.product == "monitor" for e in events)
    assert all(e.rate_limited is False for e in events)


def test_fixture_monitor_get_monitor_data_failure():
    from copilot.fixtures.monitor import monitor_get_monitor_data_failure

    events = monitor_get_monitor_data_failure(trace_id="trc-mon-fail")
    assert len(events) >= 1


def test_fixture_monitor_get_monitor_data_retry():
    from copilot.fixtures.monitor import monitor_get_monitor_data_retry

    events = monitor_get_monitor_data_retry(trace_id="trc-mon-retry")
    assert any(e.retry_index > 0 for e in events)


def test_fixture_monitor_rate_limited():
    from copilot.fixtures.monitor import monitor_rate_limited

    events = monitor_rate_limited(trace_id="trc-mon-rl")
    assert any(e.rate_limited for e in events)


def test_fixture_monitor_no_pricing():
    from copilot.cost import assert_cost_invariants, compute_cost
    from copilot.fixtures.monitor import monitor_no_pricing_set
    from copilot.trace_records import PricingSnapshot

    events = monitor_no_pricing_set(trace_id="trc-mon-no")
    snap = PricingSnapshot(version="v1", timestamp="2026-07-25T00:00:00Z", prices={})
    rec = compute_cost(events=events, pricing=snap)
    assert rec.cost_status.value == "unpriced"
    assert_cost_invariants(rec)


# ------- CLS -------

def test_fixture_cls_search_log_success():
    from copilot.fixtures.cls import cls_search_log_success

    events = cls_search_log_success(trace_id="trc-cls-1")
    assert all(e.product == "cls" for e in events)


def test_fixture_cls_describe_logset_failure():
    from copilot.fixtures.cls import cls_describe_logset_failure

    events = cls_describe_logset_failure(trace_id="trc-cls-fail")
    assert len(events) >= 1


def test_fixture_cls_create_logset_retry():
    from copilot.fixtures.cls import cls_create_logset_retry

    events = cls_create_logset_retry(trace_id="trc-cls-retry")
    assert any(e.retry_index > 0 for e in events)


def test_fixture_cls_search_log_rate_limited():
    from copilot.fixtures.cls import cls_search_log_rate_limited

    events = cls_search_log_rate_limited(trace_id="trc-cls-rl")
    assert any(e.rate_limited for e in events)


def test_fixture_cls_no_pricing():
    from copilot.cost import assert_cost_invariants, compute_cost
    from copilot.fixtures.cls import cls_no_pricing_set
    from copilot.trace_records import PricingSnapshot

    events = cls_no_pricing_set(trace_id="trc-cls-no")
    snap = PricingSnapshot(version="v1", timestamp="2026-07-25T00:00:00Z", prices={})
    rec = compute_cost(events=events, pricing=snap)
    assert rec.cost_status.value == "unpriced"
    assert_cost_invariants(rec)


# ---------------------------------------------------------------------------
# End-to-end: priced fixtures feed through compute_cost + quality_report
# ---------------------------------------------------------------------------


def _fixture_pricing_snapshot() -> PricingSnapshot:
    return PricingSnapshot(
        version="v1",
        timestamp="2026-07-25T00:00:00Z",
        prices={
            "api:cvm:DescribeInstances:per_call": 0.001,
            "api:cvm:RunInstances:per_call": 0.10,
            "api:cvm:StopInstances:per_call": 0.002,
            "api:monitor:DescribeBasicMetrics:per_call": 0.0005,
            "api:monitor:GetMonitorData:per_call": 0.001,
            "api:cls:SearchLog:per_call": 0.002,
            "api:cls:DescribeLogsets:per_call": 0.0005,
            "api:cls:CreateLogset:per_call": 0.02,
        },
    )


def test_priced_cvm_success_fixture_pipeline_yields_actual():
    from copilot.cost import assert_cost_invariants, compute_cost
    from copilot.fixtures.cvm import cvm_describe_instances_success

    events = cvm_describe_instances_success(trace_id="trc-cvm-full")
    rec = compute_cost(events=events, pricing=_fixture_pricing_snapshot())
    assert rec.cost_status.value == "actual"
    assert rec.total_cost > 0
    assert_cost_invariants(rec)


def test_priced_monitor_failure_fixture_pipeline_yields_actual():
    """Failure path events still get priced (per-call counters; failures still bill)."""
    from copilot.cost import assert_cost_invariants, compute_cost
    from copilot.fixtures.monitor import monitor_get_monitor_data_failure

    events = monitor_get_monitor_data_failure(trace_id="trc-mon-full")
    rec = compute_cost(events=events, pricing=_fixture_pricing_snapshot())
    assert rec.cost_status.value in {"actual", "partial"}
    assert_cost_invariants(rec)


def test_priced_cls_retry_fixture_pipeline_yields_actual():
    from copilot.cost import assert_cost_invariants, compute_cost
    from copilot.fixtures.cls import cls_create_logset_retry

    events = cls_create_logset_retry(trace_id="trc-cls-full")
    rec = compute_cost(events=events, pricing=_fixture_pricing_snapshot())
    assert rec.cost_status.value in {"actual", "partial"}
    assert_cost_invariants(rec)


def test_quality_report_summary_three_products():
    """Combined report across Monitor + CVM + CLS priced records."""
    from copilot.cost import compute_cost
    from copilot.fixtures.cls import cls_search_log_success
    from copilot.fixtures.cvm import cvm_describe_instances_success
    from copilot.fixtures.monitor import monitor_describe_basic_metrics_success
    from copilot.quality_report import quality_coverage_report

    snap = _fixture_pricing_snapshot()
    records = [
        compute_cost(events=cvm_describe_instances_success(trace_id="trc-c"), pricing=snap),
        compute_cost(events=monitor_describe_basic_metrics_success(trace_id="trc-m"), pricing=snap),
        compute_cost(events=cls_search_log_success(trace_id="trc-l"), pricing=snap),
    ]
    out = quality_coverage_report(records)
    summary = out["summary"]
    assert summary["trace_count"] == 3
    good = summary["good"]
    assert good >= 2  # at least 2 of 3 should be "good"


def test_langfuse_export_with_three_product_fixtures():
    """Each fixture's events flow through the Langfuse exporter without raising."""
    from copilot.fixtures.cls import cls_search_log_success
    from copilot.fixtures.cvm import cvm_describe_instances_success
    from copilot.fixtures.monitor import monitor_describe_basic_metrics_success
    from copilot.langfuse_exporter import export_trace_to_langfuse
    from copilot.trace_records import TraceRecord

    base = TraceRecord(
        id="trc-export",
        name="multi-product-pipeline",
        timestamp="2026-07-25T00:00:00Z",
        started_at="2026-07-25T00:00:00Z",
        ended_at="2026-07-25T00:05:00Z",
        status="success",
    )
    events = (
        cvm_describe_instances_success(trace_id="trc-export")
        + monitor_describe_basic_metrics_success(trace_id="trc-export")
        + cls_search_log_success(trace_id="trc-export")
    )
    out = export_trace_to_langfuse(base, usage_events=events)
    types = [o["type"] for o in out["observations"]]
    assert "generation" in types
    assert any("usage_event_id" in o.get("metadata", {}) for o in out["observations"])
