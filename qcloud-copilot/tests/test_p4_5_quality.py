"""P4.5 — quality_coverage_report.

Output CostRecord coverage status from a collection of CostRecord + UsageEvent
+ AllocationRecord inputs.

Returns:

    {
      "by_trace": {
          trace_id: {
              "total_cost": float,            # sum of priced-total-cost only
              "priced_count": int,
              "unpriced_count": int,
              "partial_count": int,
              "not_applicable_count": int,
              "priced_ratio": float,          # priced_count / total
              "unpriced_ratio": float,        # unpriced_count / total
              "allocation_coverage": float    # distinct attribution_keys / trace event count
              "score": "good | fair | poor | unpriced"
          }
      },
      "summary": {
          "trace_count": int,
          "good": int, "fair": int, "poor": int, "unpriced": int,
          "overall_score": "good | fair | poor"
      }
    }

Score rules (per-trace):
    good             priced_ratio >= 0.9
    fair             0.5 <= priced_ratio < 0.9
    poor             0 < priced_ratio < 0.5
    unpriced         priced_ratio == 0 (and total > 0 events)
"""

from __future__ import annotations


def _llm(provider="openai", model="gpt-4o", trace_id="trc-p4-5", input_tokens=1000, output_tokens=500):
    from copilot.trace_records import UsageEvent
    return UsageEvent(
        id=f"ue-llm-{trace_id}",
        trace_id=trace_id,
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


def _cost(cost_id: str, total: float, status: str, trace_id: str = "trc-p4-5",
          priced_count: int = 1, total_events: int = 1, event_ids: list[str] | None = None):
    from copilot.trace_records import CostRecord, CostStatus

    return CostRecord(
        id=cost_id,
        trace_id=trace_id,
        usage_event_ids=event_ids or [],
        cost_status=CostStatus(status),
        total_cost=total,
        pricing_snapshot_version="v1",
        metadata={"priced_count": priced_count, "total_events": total_events},
    )


def test_quality_report_basic_good():
    from copilot.quality_report import quality_coverage_report

    costs = [
        _cost("c1", 5.0, status="actual", trace_id="trc-A", priced_count=10, total_events=10,
              event_ids=[f"ue-{i}" for i in range(10)]),
    ]
    out = quality_coverage_report(costs)
    t = out["by_trace"]["trc-A"]
    assert t["priced_count"] == 10
    assert t["unpriced_count"] == 0
    assert t["priced_ratio"] == 1.0
    assert t["score"] == "good"


def test_quality_report_partial_yields_fair():
    from copilot.quality_report import quality_coverage_report

    costs = [
        _cost("c1", 5.0, status="actual", trace_id="trc-B", priced_count=7, total_events=10,
              event_ids=[f"ue-{i}" for i in range(10)]),
    ]
    out = quality_coverage_report(costs)
    assert out["by_trace"]["trc-B"]["priced_ratio"] == 0.7
    assert out["by_trace"]["trc-B"]["score"] == "fair"


def test_quality_report_mostly_unpriced_yields_poor():
    from copilot.quality_report import quality_coverage_report

    costs = [
        _cost("c1", 1.0, status="actual", trace_id="trc-C", priced_count=1, total_events=10,
              event_ids=[f"ue-{i}" for i in range(10)]),
    ]
    out = quality_coverage_report(costs)
    assert out["by_trace"]["trc-C"]["priced_ratio"] == 0.1
    assert out["by_trace"]["trc-C"]["score"] == "poor"


def test_quality_report_all_unpriced_yields_unpriced():
    from copilot.quality_report import quality_coverage_report

    costs = [
        _cost("c1", 0.0, status="unpriced", trace_id="trc-D", priced_count=0, total_events=10,
              event_ids=[f"ue-{i}" for i in range(10)]),
    ]
    out = quality_coverage_report(costs)
    assert out["by_trace"]["trc-D"]["score"] == "unpriced"


def test_quality_report_aggregates_multiple_records_per_trace():
    from copilot.quality_report import quality_coverage_report

    costs = [
        _cost("c1", 3.0, status="actual", trace_id="trc-E", priced_count=4, total_events=5,
              event_ids=["ue-1", "ue-2", "ue-3", "ue-4", "ue-5"]),
        _cost("c2", 0.0, status="unpriced", trace_id="trc-E", priced_count=0, total_events=3,
              event_ids=["ue-6", "ue-7", "ue-8"]),
    ]
    out = quality_coverage_report(costs)
    t = out["by_trace"]["trc-E"]
    assert t["priced_count"] == 4
    assert t["unpriced_count"] == 1
    assert t["partial_count"] == 0
    assert t["priced_ratio"] == 0.5
    assert t["score"] == "fair"


def test_quality_report_summary_aggregation():
    from copilot.quality_report import quality_coverage_report

    costs = [
        _cost("c1", 5.0, status="actual", trace_id="trc-good", priced_count=10, total_events=10,
              event_ids=[f"ue-good-{i}" for i in range(10)]),
        _cost("c2", 0.0, status="unpriced", trace_id="trc-none", priced_count=0, total_events=5,
              event_ids=[f"ue-none-{i}" for i in range(5)]),
    ]
    out = quality_coverage_report(costs)
    summary = out["summary"]
    assert summary["trace_count"] == 2
    assert summary["good"] == 1
    assert summary["unpriced"] == 1


def test_quality_report_empty_input():
    from copilot.quality_report import quality_coverage_report

    out = quality_coverage_report([])
    assert out["by_trace"] == {}
    assert out["summary"]["trace_count"] == 0
    assert out["summary"]["overall_score"] in {"good", "fair", "poor", "unpriced"}


def test_quality_report_allocation_coverage_supplied():
    """When Allocations are supplied, allocation_coverage = distinct keys / trace event count."""
    from copilot.quality_report import quality_coverage_report
    from copilot.trace_records import AllocationRecord

    costs = [
        _cost("c1", 5.0, status="actual", trace_id="trc-X", priced_count=4, total_events=4,
              event_ids=["ue-1", "ue-2", "ue-3", "ue-4"]),
    ]
    allocs = [
        AllocationRecord(
            cost_id="c1", attribution_key=("tenant", "t1"),
            share=0.5, allocated_cost=2.5, method="shared",
        ),
        AllocationRecord(
            cost_id="c1", attribution_key=("tenant", "t2"),
            share=0.5, allocated_cost=2.5, method="shared",
        ),
    ]
    out = quality_coverage_report(costs, allocations=allocs)
    assert out["by_trace"]["trc-X"]["allocation_coverage"] == 0.5
