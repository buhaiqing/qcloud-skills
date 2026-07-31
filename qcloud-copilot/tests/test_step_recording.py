"""P2.6.a — with_step_recording wrapper that bundles audit + observation + usage.

Use:
    from copilot.step_recording import with_step_recording
    with with_step_recording(trace_id="trc-1", step_id="s1", name="skill_call", sink=sink) as ctx:
        ...
        ctx.add_usage(emit_llm_usage(trace_id="trc-1", ...))
    # on exit: audit + observation + usage are all written; usage joined by observation_id
"""

from __future__ import annotations

import json
from pathlib import Path


def test_with_step_recording_writes_audit_observation_usage(tmp_path: Path):
    from copilot.observ import ObservableSink
    from copilot.step_recording import with_step_recording
    from copilot.usage_emitters import emit_cloud_api_usage, emit_llm_usage

    sink = ObservableSink(runtime_root=tmp_path)
    with with_step_recording(
        sink=sink,
        trace_id="trc-rec-001",
        step_id="step-1",
        name="skill_call:qcloud-cvm-ops",
    ) as ctx:
        ctx.observation.metadata["status"] = "ok"
        ctx.add_usage(
            emit_llm_usage(
                trace_id="trc-rec-001",
                observation_id=ctx.observation.id,
                provider="openai",
                model="gpt-4o",
                input_tokens=10,
                output_tokens=5,
            )
        )
        ctx.add_usage(
            emit_cloud_api_usage(
                trace_id="trc-rec-001",
                observation_id=ctx.observation.id,
                product="cvm",
                service="cvm",
                action="DescribeInstances",
                region="ap-guangzhou",
            )
        )

    obs_path = tmp_path / "audit" / "trc-rec-001" / "observations.jsonl"
    use_path = tmp_path / "audit" / "trc-rec-001" / "usage_events.jsonl"
    assert obs_path.exists()
    assert use_path.exists()

    obs_lines = [json.loads(line) for line in obs_path.read_text().splitlines()]
    use_lines = [json.loads(line) for line in use_path.read_text().splitlines()]

    assert len(obs_lines) == 1
    assert obs_lines[0]["trace_id"] == "trc-rec-001"
    assert obs_lines[0]["name"] == "skill_call:qcloud-cvm-ops"
    assert obs_lines[0]["type"] in {"SPAN", "GENERATION", "EVENT"}
    assert obs_lines[0]["metadata"]["step_id"] == "step-1"

    assert len(use_lines) == 2
    for u in use_lines:
        assert u["trace_id"] == "trc-rec-001"
        assert u["observation_id"] == obs_lines[0]["id"]


def test_with_step_recording_records_status_error_on_exception(tmp_path: Path):
    from copilot.observ import ObservableSink
    from copilot.step_recording import with_step_recording

    sink = ObservableSink(runtime_root=tmp_path)
    try:
        with with_step_recording(
            sink=sink,
            trace_id="trc-err",
            step_id="step-fail",
            name="skill_call:qcloud-x-ops",
        ):
            raise RuntimeError("deliberate")
    except RuntimeError:
        pass

    obs_path = tmp_path / "audit" / "trc-err" / "observations.jsonl"
    assert obs_path.exists()
    obs_lines = [json.loads(line) for line in obs_path.read_text().splitlines()]
    assert obs_lines[0]["status"] == "error"
    assert "RuntimeError" in obs_lines[0]["error"]


def test_with_step_recording_records_status_success_normally(tmp_path: Path):
    from copilot.observ import ObservableSink
    from copilot.step_recording import with_step_recording

    sink = ObservableSink(runtime_root=tmp_path)
    with with_step_recording(
        sink=sink,
        trace_id="trc-ok",
        step_id="step-ok",
        name="event:step-start",
    ):
        pass

    obs_path = tmp_path / "audit" / "trc-ok" / "observations.jsonl"
    obs_lines = [json.loads(line) for line in obs_path.read_text().splitlines()]
    assert obs_lines[0]["status"] == "success"


def test_with_step_recording_no_usage_writes_observation_only(tmp_path: Path):
    from copilot.observ import ObservableSink
    from copilot.step_recording import with_step_recording

    sink = ObservableSink(runtime_root=tmp_path)
    with with_step_recording(
        sink=sink,
        trace_id="trc-no-use",
        step_id="step-pure",
        name="event:trace.end",
    ):
        pass

    obs_path = tmp_path / "audit" / "trc-no-use" / "observations.jsonl"
    use_path = tmp_path / "audit" / "trc-no-use" / "usage_events.jsonl"
    assert obs_path.exists()
    assert not use_path.exists()


def test_step_recording_kind_override(tmp_path: Path):
    from copilot.observ import ObservableSink
    from copilot.step_recording import with_step_recording

    sink = ObservableSink(runtime_root=tmp_path)
    # Force GENERATION via kind= override despite matching SPAN by name.
    with with_step_recording(
        sink=sink,
        trace_id="trc-kind",
        step_id="step-k",
        name="skill_call:anything",
        kind="GENERATION",
    ):
        pass

    obs_path = tmp_path / "audit" / "trc-kind" / "observations.jsonl"
    obs_lines = [json.loads(line) for line in obs_path.read_text().splitlines()]
    assert obs_lines[0]["type"] == "GENERATION"
