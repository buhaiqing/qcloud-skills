"""P1.4 — Trace metadata builder for skill/runtime into TraceRecord.

Tests cover:
  - build_runtime_info() captures python/tccli/sdk/git/deployment with safe defaults
  - build_skill_info(name) maps SkillVersion (P1.2) into SkillInfo (P1.3)
  - audit_trace() persists skill + runtime JSON in the audit file when supplied
  - audit_trace() keeps backward compat when skill/runtime omitted
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch


def test_build_runtime_info_returns_runtime_info():
    from copilot.trace_metadata import build_runtime_info
    from copilot.trace_records import RuntimeInfo

    rt = build_runtime_info()
    assert isinstance(rt, RuntimeInfo)
    # python_version is always available
    assert rt.python_version
    assert ".".join(rt.python_version.split(".")[:2])  # at least major.minor


def test_build_runtime_info_handles_missing_subprocess():
    """When tccli/sdk/subprocess missing, fields are None not crash."""
    from copilot.trace_metadata import build_runtime_info

    with patch("copilot.trace_metadata._detect_tccli_version", return_value=None):
        with patch(
            "copilot.trace_metadata._detect_sdk_version",
            side_effect=lambda: (None, None),
        ):
            with patch("copilot.trace_metadata._detect_git_commit", return_value=None):
                rt = build_runtime_info()
    assert rt.tccli_version is None
    assert rt.sdk_name is None
    assert rt.sdk_version is None
    assert rt.git_commit is None
def test_build_skill_info_maps_skill_version():
    from copilot.trace_metadata import build_skill_info
    from copilot.skill_version import SkillVersion
    from copilot.trace_records import SkillInfo

    sv = SkillVersion(
        skill_name="qcloud-foo-ops",
        version="2.5.0",
        last_updated="2026-07-25",
        sha="abcd123456",
        cli_applicability="dual-path",
    )
    si = build_skill_info(sv, source="workspace")
    assert isinstance(si, SkillInfo)
    assert si.name == "qcloud-foo-ops"
    assert si.version == "2.5.0"
    assert si.skill_file_sha256 in {"sha256:abcd123456", "abcd123456"}
    assert si.source == "workspace"


def test_build_skill_info_with_incomplete_version():
    from copilot.trace_metadata import build_skill_info

    si = build_skill_info(None)
    assert si.name is None
    assert si.version is None


def test_audit_trace_persists_skill_and_runtime(tmp_path: Path):
    """audit_trace writes skill/runtime blocks when supplied."""
    from copilot.quality.audit import audit_trace
    from copilot.trace_records import RuntimeInfo, SkillInfo

    skill = SkillInfo(
        name="qcloud-test-ops",
        version="1.0.0",
        source="workspace",
        skill_file_sha256="abc123",
    )
    runtime = RuntimeInfo(python_version="3.12.1", git_commit="deadbeef")
    session_id = "ses-p14-001"

    with patch("copilot.quality.audit.Path.cwd", return_value=tmp_path):
        audit_trace(
            session_id=session_id,
            step_id="s1",
            trace_data={"status": "pass", "duration_ms": 5},
            skill="qcloud-test-ops",
            skill_info=skill,
            runtime_info=runtime,
        )
    audit_dir = tmp_path / ".runtime" / "gcl" / "copilot" / "audit" / session_id
    files = sorted(audit_dir.glob("step-*.json"))
    assert files, "audit file not written"
    payload = json.loads(files[-1].read_text())
    assert payload["skill"]["name"] == "qcloud-test-ops"
    assert payload["skill"]["version"] == "1.0.0"
    assert payload["skill"]["skill_file_sha256"] == "abc123"
    assert payload["runtime"]["python_version"] == "3.12.1"
    assert payload["runtime"]["git_commit"] == "deadbeef"


def test_audit_trace_backward_compat_no_skill_runtime(tmp_path: Path):
    """When skill_info/runtime_info are omitted, audit file is unchanged."""
    from copilot.quality.audit import audit_trace

    session_id = "ses-p14-002"
    with patch("copilot.quality.audit.Path.cwd", return_value=tmp_path):
        audit_trace(
            session_id=session_id,
            step_id="s1",
            trace_data={"status": "pass", "duration_ms": 7},
        )
    audit_dir = tmp_path / ".runtime" / "gcl" / "copilot" / "audit" / session_id
    files = sorted(audit_dir.glob("step-*.json"))
    assert files
    payload = json.loads(files[-1].read_text())
    assert "skill" not in payload
    assert "runtime" not in payload
