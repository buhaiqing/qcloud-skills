"""P2.6.b — audit_trace_v3(): bundles legacy audit_trace + observation + usage.

The legacy `audit_trace()` writes step-level JSON to .runtime/gcl/copilot/audit/
(step semantics). The new TRACE-1 v3 layer wants `observations.jsonl` and
`usage_events.jsonl` per trace. This bridge fires both so existing callers that
already pass audit data get v3 emission too, without in-place rewriting the
legacy writer.

Behavior contract:
  - calls audit_trace() unchanged
  - emits one ObservationRecord via ObservableSink.emit_observation
  - if `usage_events=` provided, emits each via ObservableSink.emit_usage_event
  - observation_id on usage = step_id (legacy join key keeps trace lineage)
"""

from __future__ import annotations

import json
from pathlib import Path


def test_audit_trace_v3_writes_both_audit_and_observation(tmp_path: Path):
    from unittest.mock import patch

    from copilot.observ import ObservableSink
    from copilot.quality.audit import audit_trace_v3

    sink = ObservableSink(runtime_root=tmp_path)
    with patch("copilot.quality.audit.Path.cwd", return_value=tmp_path):
        audit_trace_v3(
            sink=sink,
            session_id="ses-bridge-001",
            trace_id="trc-bridge-001",
            step_id="step.l2",
            trace_data={"status": "pass", "duration_ms": 5, "skill": "qcloud-cvm-ops"},
            skill="qcloud-cvm-ops",
            observation_name="skill_call:qcloud-cvm-ops",
        )

    # Legacy audit file path
    legacy_dir = tmp_path / ".runtime" / "gcl" / "copilot" / "audit" / "trc-bridge-001"
    legacy_files = sorted(legacy_dir.glob("step-*.json"))
    assert legacy_files, "legacy audit not written"

    # v3 observation/usage paths
    obs_dir = tmp_path / "audit" / "trc-bridge-001"
    obs_path = obs_dir / "observations.jsonl"
    assert obs_path.exists()
    obs_lines = [json.loads(line) for line in obs_path.read_text().splitlines()]
    assert len(obs_lines) == 1
    assert obs_lines[0]["trace_id"] == "trc-bridge-001"
    assert obs_lines[0]["name"] == "skill_call:qcloud-cvm-ops"
    assert obs_lines[0]["metadata"]["step_id"] == "step.l2"
    assert obs_lines[0]["status"] == "success"


def test_audit_trace_v3_with_usage_events(tmp_path: Path):
    from unittest.mock import patch

    from copilot.observ import ObservableSink
    from copilot.quality.audit import audit_trace_v3
    from copilot.usage_emitters import emit_cloud_api_usage

    sink = ObservableSink(runtime_root=tmp_path)
    usage = emit_cloud_api_usage(
        trace_id="trc-bridge-002",
        product="cvm",
        service="cvm",
        action="DescribeInstances",
        region="ap-guangzhou",
    )
    with patch("copilot.quality.audit.Path.cwd", return_value=tmp_path):
        audit_trace_v3(
            sink=sink,
            session_id="ses-bridge-002",
            trace_id="trc-bridge-002",
            step_id="step.api",
            trace_data={"status": "success"},
            skill="qcloud-cvm-ops",
            observation_name="skill_call:qcloud-cvm-ops",
            usage_events=[usage],
        )

    use_path = tmp_path / "audit" / "trc-bridge-002" / "usage_events.jsonl"
    use_lines = [json.loads(line) for line in use_path.read_text().splitlines()]
    assert len(use_lines) == 1
    assert use_lines[0]["trace_id"] == "trc-bridge-002"
    assert use_lines[0]["event_type"] == "cloud_api"
    # observation_id on usage must join the emitted observation
    obs_path = tmp_path / "audit" / "trc-bridge-002" / "observations.jsonl"
    obs_lines = [json.loads(line) for line in obs_path.read_text().splitlines()]
    assert use_lines[0]["observation_id"] == obs_lines[0]["id"]


def test_audit_trace_v3_without_usage_writes_only_observation(tmp_path: Path):
    from unittest.mock import patch

    from copilot.observ import ObservableSink
    from copilot.quality.audit import audit_trace_v3

    sink = ObservableSink(runtime_root=tmp_path)
    with patch("copilot.quality.audit.Path.cwd", return_value=tmp_path):
        audit_trace_v3(
            sink=sink,
            session_id="ses-x",
            trace_id="trc-x",
            step_id="step-x",
            trace_data={"status": "pass"},
            skill=None,
            observation_name="event:trace.start",
        )
    assert (tmp_path / "audit" / "trc-x" / "observations.jsonl").exists()
    assert not (tmp_path / "audit" / "trc-x" / "usage_events.jsonl").exists()


def test_audit_trace_v3_legacy_callers_unaffected(tmp_path: Path):
    """Plain `audit_trace()` (legacy) must still work and write only the legacy file."""
    from unittest.mock import patch

    from copilot.quality.audit import audit_trace

    with patch("copilot.quality.audit.Path.cwd", return_value=tmp_path):
        audit_trace(
            session_id="ses-legacy",
            step_id="s1",
            trace_data={"status": "pass", "duration_ms": 5},
        )
    legacy_dir = tmp_path / ".runtime" / "gcl" / "copilot" / "audit" / "ses-legacy"
    assert any(legacy_dir.glob("step-*.json"))
    # No v3 audit dir at .runtime root because no sink touched
    v3_dir = tmp_path / "audit" / "ses-legacy"
    assert not v3_dir.exists()
