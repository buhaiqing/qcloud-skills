"""CLS (Cloud Log Service) fixtures."""
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
        id=f"ue-cls-{action}-test",
        trace_id=trace_id,
        event_type="cloud_api",
        timestamp="2026-07-25T00:00:00Z",
        product="cls",
        action=action,
        region="ap-shanghai",
        client_type="sdk",
        resource_count=resource_count,
        retry_index=retry_index,
        rate_limited=rate_limited,
        metadata={"error_code": error_code} if error_code else {},
    )


def cls_search_log_success(*, trace_id: str) -> list[UsageEvent]:
    return [_make(trace_id=trace_id, action="SearchLog")]


def cls_describe_logset_failure(*, trace_id: str) -> list[UsageEvent]:
    return [
        _make(
            trace_id=trace_id,
            action="DescribeLogsets",
            error_code="TopicNotExist",
        )
    ]


def cls_create_logset_retry(*, trace_id: str) -> list[UsageEvent]:
    return [
        _make(
            trace_id=trace_id,
            action="CreateLogset",
            retry_index=1,
            error_code="Conflict",
        ),
        _make(trace_id=trace_id, action="CreateLogset", retry_index=0),
    ]


def cls_search_log_rate_limited(*, trace_id: str) -> list[UsageEvent]:
    return [
        _make(trace_id=trace_id, action="SearchLog", rate_limited=True)
    ]


def cls_no_pricing_set(*, trace_id: str) -> list[UsageEvent]:
    return [
        _make(trace_id=trace_id, action="SearchLog"),
        _make(trace_id=trace_id, action="DescribeLogsets"),
    ]
