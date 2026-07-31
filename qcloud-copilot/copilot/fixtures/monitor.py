"""Monitor (CM) fixtures."""
from __future__ import annotations

from copilot.trace_records import UsageEvent


def _make(
    *,
    trace_id: str,
    action: str,
    retry_index: int = 0,
    rate_limited: bool = False,
    error_code: str | None = None,
    resource_count: int = 1,
) -> UsageEvent:
    return UsageEvent(
        id=f"ue-monitor-{action}-test",
        trace_id=trace_id,
        event_type="cloud_api",
        timestamp="2026-07-25T00:00:00Z",
        product="monitor",
        action=action,
        region="ap-guangzhou",
        client_type="sdk",
        resource_count=resource_count,
        retry_index=retry_index,
        rate_limited=rate_limited,
        metadata={"error_code": error_code} if error_code else {},
    )


def monitor_describe_basic_metrics_success(*, trace_id: str) -> list[UsageEvent]:
    return [_make(trace_id=trace_id, action="DescribeBasicMetrics")]


def monitor_get_monitor_data_failure(*, trace_id: str) -> list[UsageEvent]:
    return [
        _make(
            trace_id=trace_id,
            action="GetMonitorData",
            error_code="ResourceNotFound",
        )
    ]


def monitor_get_monitor_data_retry(*, trace_id: str) -> list[UsageEvent]:
    return [
        _make(trace_id=trace_id, action="GetMonitorData", retry_index=1, error_code="Throttled"),
        _make(trace_id=trace_id, action="GetMonitorData", retry_index=0),
    ]


def monitor_rate_limited(*, trace_id: str) -> list[UsageEvent]:
    return [
        _make(trace_id=trace_id, action="DescribeBasicMetrics", rate_limited=True)
    ]


def monitor_no_pricing_set(*, trace_id: str) -> list[UsageEvent]:
    return [
        _make(trace_id=trace_id, action="DescribeBasicMetrics"),
        _make(trace_id=trace_id, action="GetMonitorData"),
    ]
