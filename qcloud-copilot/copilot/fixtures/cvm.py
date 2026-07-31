"""CVM (Cloud Virtual Machine) fixtures."""
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
        id=f"ue-cvm-{action}-test",
        trace_id=trace_id,
        event_type="cloud_api",
        timestamp="2026-07-25T00:00:00Z",
        product="cvm",
        action=action,
        region="ap-guangzhou",
        client_type="tccli",
        resource_count=resource_count,
        retry_index=retry_index,
        rate_limited=rate_limited,
        metadata={"error_code": error_code} if error_code else {},
    )


def cvm_describe_instances_success(*, trace_id: str) -> list[UsageEvent]:
    return [_make(trace_id=trace_id, action="DescribeInstances")]


def cvm_describe_instances_failure(*, trace_id: str) -> list[UsageEvent]:
    return [
        _make(
            trace_id=trace_id,
            action="DescribeInstances",
            error_code="InvalidParameter",
        )
    ]


def cvm_describe_instances_retry_then_success(*, trace_id: str) -> list[UsageEvent]:
    return [
        _make(trace_id=trace_id, action="DescribeInstances", retry_index=1, error_code="InternalError"),
        _make(trace_id=trace_id, action="DescribeInstances", retry_index=2, error_code="InternalError"),
        _make(trace_id=trace_id, action="DescribeInstances", retry_index=0),
    ]


def cvm_run_instances_rate_limited(*, trace_id: str) -> list[UsageEvent]:
    return [
        _make(
            trace_id=trace_id,
            action="RunInstances",
            rate_limited=True,
        )
    ]


def cvm_no_pricing_set(*, trace_id: str) -> list[UsageEvent]:
    """Mixed call set where some are billable but no entry exists in pricing snapshot."""
    return [
        _make(trace_id=trace_id, action="DescribeInstances"),
        _make(trace_id=trace_id, action="StopInstances"),
    ]
