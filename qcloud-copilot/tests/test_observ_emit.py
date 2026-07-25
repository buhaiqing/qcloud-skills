"""P2.2 — ObservableSink accepts ObservationRecord / UsageEvent and writes them.

Verifies:
  - emit_observation() writes one line to audit/<trace_id>/observations.jsonl
  - emit_usage_event() writes one line to audit/<trace_id>/usage_events.jsonl
  - Type classifier defaults: SPAN/GENERATION/EVENT writes still pass through
  - Custom runtime_root does not pollute cwd
"""

from __future__ import annotations

import json
from pathlib import Path


def test_emit_observation_writes_jsonl(tmp_path: Path):
    from copilot.observ import ObservableSink
    from copilot.trace_records import ObservationRecord, ObservationType

    sink = ObservableSink(runtime_root=tmp_path)
    obs = ObservationRecord(
        id="obs-emit-001",
        trace_id="trc-emit-001",
        type=ObservationType.SPAN,
        name="skill_call:qcloud-cvm-ops",
        start_time="2026-07-25T00:00:00Z",
        end_time="2026-07-25T00:00:01Z",
        status="success",
    )
    sink.emit_observation(obs)

    obs_path = tmp_path / "audit" / "trc-emit-001" / "observations.jsonl"
    assert obs_path.exists()
    lines = [json.loads(line) for line in obs_path.read_text().splitlines()]
    assert len(lines) == 1
    assert lines[0]["id"] == "obs-emit-001"
    assert lines[0]["trace_id"] == "trc-emit-001"
    assert lines[0]["type"] == "SPAN"
    assert lines[0]["name"] == "skill_call:qcloud-cvm-ops"


def test_emit_observation_indexes_by_trace(tmp_path: Path):
    from copilot.observ import ObservableSink
    from copilot.trace_records import ObservationRecord, ObservationType

    sink = ObservableSink(runtime_root=tmp_path)
    for i in range(3):
        obs = ObservationRecord(
            id=f"obs-{i}",
            trace_id="trc-multi",
            type=ObservationType.EVENT,
            name=f"step-{i}",
        )
        sink.emit_observation(obs)
    obs_path = tmp_path / "audit" / "trc-multi" / "observations.jsonl"
    lines = [json.loads(line) for line in obs_path.read_text().splitlines()]
    assert [line["id"] for line in lines] == ["obs-0", "obs-1", "obs-2"]


def test_emit_usage_event_writes_jsonl(tmp_path: Path):
    from copilot.observ import ObservableSink
    from copilot.trace_records import UsageEvent

    sink = ObservableSink(runtime_root=tmp_path)
    evt = UsageEvent(
        id="ue-emit-001",
        trace_id="trc-emit-002",
        event_type="llm",
        timestamp="2026-07-25T00:00:00Z",
        observation_id="obs-1",
        provider="openai",
        model="gpt-4o",
        usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    )
    sink.emit_usage_event(evt)

    p = tmp_path / "audit" / "trc-emit-002" / "usage_events.jsonl"
    assert p.exists()
    lines = [json.loads(line) for line in p.read_text().splitlines()]
    assert len(lines) == 1
    assert lines[0]["event_type"] == "llm"
    assert lines[0]["provider"] == "openai"
    assert lines[0]["observation_id"] == "obs-1"


def test_emit_observation_does_not_touch_cwd(tmp_path: Path):
    """runtime_root override prevents accidental cwd writes."""
    cwd = Path.cwd()
    cwd_runtime = cwd / ".runtime"
    before = list(cwd_runtime.glob("**/*")) if cwd_runtime.exists() else []
    from copilot.observ import ObservableSink
    from copilot.trace_records import ObservationRecord

    sink = ObservableSink(runtime_root=tmp_path)
    sink.emit_observation(
        ObservationRecord(
            id="obs-isolated",
            trace_id="trc-isol",
            name="test",
        )
    )
    if cwd_runtime.exists():
        after = list(cwd_runtime.glob("**/*"))
        new = [p for p in after if p not in before]
        assert all(str(p).startswith(str(tmp_path.resolve())) for p in new)


def test_emit_methods_dont_crash_on_minimal_payload(tmp_path: Path):
    from copilot.observ import ObservableSink
    from copilot.trace_records import ObservationRecord, UsageEvent

    sink = ObservableSink(runtime_root=tmp_path)
    sink.emit_observation(ObservationRecord(id="x", trace_id="y"))
    sink.emit_usage_event(UsageEvent(id="u", trace_id="y", event_type="data", timestamp="2026-07-25"))
