"""P2.6.c — bootstrap_trace_metadata(): emit a session-startup emission event.

Writes a single ObservationRecord marked `event:session.startup` carrying
RuntimeInfo (Python / tccli / SDK / git commit) into the v3 audit tree, so a
later query can answer: which Python + which tccli + which skill version
+ which git commit was running when the invocation began.

Usage:
    from copilot.step_recording import bootstrap_trace_metadata
    bootstrap_trace_metadata(sink=ObservableSink(), trace_id="t1")
"""

from __future__ import annotations

import json
from pathlib import Path


def test_bootstrap_emits_startup_observation(tmp_path: Path):
    from copilot.observ import ObservableSink
    from copilot.step_recording import bootstrap_trace_metadata

    sink = ObservableSink(runtime_root=tmp_path)
    bootstrap_trace_metadata(sink=sink, trace_id="trc-bootstrap-001")

    obs_path = tmp_path / "audit" / "trc-bootstrap-001" / "observations.jsonl"
    assert obs_path.exists()
    lines = [json.loads(line) for line in obs_path.read_text().splitlines()]
    assert len(lines) == 1
    obs = lines[0]
    assert obs["trace_id"] == "trc-bootstrap-001"
    assert obs["name"] == "event:session.startup"
    assert obs["type"] == "EVENT"
    assert "runtime" in obs["metadata"]
    runtime = obs["metadata"]["runtime"]
    assert "python_version" in runtime
    # python_version is always detectable
    assert runtime["python_version"]


def test_bootstrap_runtime_metadata_has_required_keys(tmp_path: Path):
    from copilot.observ import ObservableSink
    from copilot.step_recording import bootstrap_trace_metadata

    sink = ObservableSink(runtime_root=tmp_path)
    bootstrap_trace_metadata(sink=sink, trace_id="trc-keys")

    obs_path = tmp_path / "audit" / "trc-keys" / "observations.jsonl"
    runtime = json.loads(obs_path.read_text().splitlines()[0])["metadata"]["runtime"]
    for key in (
        "python_version",
        "tccli_version",
        "sdk_name",
        "sdk_version",
        "git_commit",
        "deployment_version",
    ):
        # value may be None when not detected
        assert key in runtime


def test_bootstrap_idempotent_writes_two_observations(tmp_path: Path):
    """Calling twice yields two observations (one per invocation) — both are
    valid since each is an independent invocation lifecycle marker."""
    from copilot.observ import ObservableSink
    from copilot.step_recording import bootstrap_trace_metadata

    sink = ObservableSink(runtime_root=tmp_path)
    bootstrap_trace_metadata(sink=sink, trace_id="trc-idem")
    bootstrap_trace_metadata(sink=sink, trace_id="trc-idem")

    obs_path = tmp_path / "audit" / "trc-idem" / "observations.jsonl"
    lines = [json.loads(line) for line in obs_path.read_text().splitlines()]
    assert len(lines) == 2
