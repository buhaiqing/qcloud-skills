"""P4.7 — Langfuse exporter.

Maps local TraceRecord / ObservationRecord / ScoreRecord / UsageEvent into
Langfuse-shaped trace payload.
"""

from __future__ import annotations


def _trace(name="qcloud-rca-1", **kw):
    from copilot.skill_version import SkillVersion  # noqa: F401
    from copilot.trace_metadata import build_runtime_info  # noqa: F401
    from copilot.trace_records import RuntimeInfo, SkillInfo, TraceRecord  # noqa: F401

    defaults = {
        "name": name,
        "id": "trc-fake-001",
        "timestamp": "2026-07-25T00:00:00Z",
        "started_at": "2026-07-25T00:00:00Z",
        "ended_at": "2026-07-25T00:00:05Z",
        "status": "success",
        "input": {"query": "demo"},
        "output": {"verdict": "ok"},
    }
    defaults.update(kw)
    return TraceRecord(**defaults)


def test_export_minimal_trace_record_produces_langfuse_shape():
    from copilot.langfuse_exporter import export_trace_to_langfuse

    tr = _trace()
    out = export_trace_to_langfuse(tr)
    assert out["name"] == "qcloud-rca-1"
    assert out["timestamp"] == "2026-07-25T00:00:00Z"
    assert out["input"] == {"query": "demo"}
    assert out["output"] == {"verdict": "ok"}
    assert isinstance(out["observations"], list)
    assert isinstance(out["metadata"], dict)


def test_export_observations_included_in_langfuse_payload():
    from copilot.langfuse_exporter import export_trace_to_langfuse
    from copilot.trace_records import ObservationRecord, ObservationType

    tr = _trace()
    tr.observation_ids = ["obs-x1", "obs-x2"]
    obs_a = ObservationRecord(
        id="obs-x1", trace_id="trc-fake-001", type=ObservationType.SPAN,
        name="skill_call:qcloud-cvm-ops",
        start_time="2026-07-25T00:00:00Z", end_time="2026-07-25T00:00:01Z",
        status="success",
    )
    obs_b = ObservationRecord(
        id="obs-x2", trace_id="trc-fake-001", type=ObservationType.GENERATION,
        name="gcl-generator",
        start_time="2026-07-25T00:00:01Z", end_time="2026-07-25T00:00:04Z",
        status="success",
    )
    out = export_trace_to_langfuse(tr, observations=[obs_a, obs_b])
    assert len(out["observations"]) == 2
    types = {o["type"] for o in out["observations"]}
    assert "span" in types
    assert "generation" in types
    ids = {o["id"] for o in out["observations"]}
    assert ids == {"obs-x1", "obs-x2"}


def test_export_attaches_scores():
    from copilot.langfuse_exporter import export_trace_to_langfuse
    from copilot.trace_records import ScoreRecord

    tr = _trace()
    tr.score_ids = ["sc-1"]
    sc = ScoreRecord(
        id="sc-1", trace_id="trc-fake-001",
        score_type="rca_accuracy", value=0.92,
        timestamp="2026-07-25T00:05:00Z",
    )
    out = export_trace_to_langfuse(tr, scores=[sc])
    assert len(out["scores"]) == 1
    payload = out["scores"][0]
    assert payload["id"] == "sc-1"
    assert payload["name"] == "rca_accuracy"
    assert payload["value"] == 0.92


def test_export_usage_event_becomes_generation():
    from copilot.langfuse_exporter import export_trace_to_langfuse
    from copilot.trace_records import UsageEvent

    tr = _trace()
    usage = UsageEvent(
        id="ue-llm-1", trace_id="trc-fake-001",
        event_type="llm", timestamp="2026-07-25T00:00:00Z",
        observation_id="obs-x2", provider="openai", model="gpt-4o",
        usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        prompt_version="rca-v1", latency_ms=300,
    )
    out = export_trace_to_langfuse(tr, usage_events=[usage])
    types = [o["type"] for o in out["observations"]]
    assert "generation" in types
    gen = next(
        o for o in out["observations"]
        if o.get("metadata", {}).get("usage_event_id") == "ue-llm-1"
    )
    assert gen["metadata"]["provider"] == "openai"
    assert gen["metadata"]["model"] == "gpt-4o"
    assert gen["usage"]["input_tokens"] == 100
    assert gen["usage"]["output_tokens"] == 50


def test_export_skill_runtime_info_flattened_into_trace_metadata():
    from copilot.langfuse_exporter import export_trace_to_langfuse
    from copilot.trace_records import RuntimeInfo, SkillInfo

    tr = _trace(
        skill=SkillInfo(name="qcloud-cvm-ops", version="2.5.0", source="workspace"),
        runtime=RuntimeInfo(python_version="3.12.1", git_commit="abc123"),
    )
    out = export_trace_to_langfuse(tr)
    md = out["metadata"]
    assert md["skill"]["name"] == "qcloud-cvm-ops"
    assert md["skill"]["version"] == "2.5.0"
    assert md["runtime"]["python_version"] == "3.12.1"
    assert md["runtime"]["git_commit"] == "abc123"


def test_export_idempotent():
    from copilot.langfuse_exporter import export_trace_to_langfuse

    tr = _trace()
    a = export_trace_to_langfuse(tr)
    b = export_trace_to_langfuse(tr)
    assert a == b


def test_export_failure_keeps_observation_in_payload_no_raise():
    from copilot.langfuse_exporter import export_trace_to_langfuse
    from copilot.trace_records import TraceRecord

    bad = TraceRecord(
        id="trc-bad", name="x",
        timestamp="t", started_at="t", ended_at="t", status="error",
    )
    bad.observation_ids = ["ghost-obs"]
    out = export_trace_to_langfuse(bad)
    assert out["name"] == "x"
    assert out["observations"] == []
