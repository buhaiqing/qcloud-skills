"""Tests for skill_version.py — P1.2."""
from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "qcloud-copilot"))

from copilot.skill_version import (
    parse_skill_version,
    copilot_version,
)


def test_parse_copilot_version():
    v = parse_skill_version(Path(__file__).resolve().parents[2] / "qcloud-copilot")
    assert v.skill_name == "qcloud-copilot"
    assert v.version is not None  # SKILL.md has version field
    assert v.sha is not None  # sha computed over content


def test_parse_monitor_ops_version():
    v = parse_skill_version(Path(__file__).resolve().parents[2] / "qcloud-monitor-ops")
    assert v.skill_name == "qcloud-monitor-ops"
    assert v.version is not None


def test_parse_nonexistent_skill_returns_minimal():
    v = parse_skill_version(Path("/tmp/nonexistent-skill-xyz"))
    assert v.skill_name == "nonexistent-skill-xyz"
    assert v.version is None
    assert v.sha is None


def test_cli_applicability_extracted():
    v = parse_skill_version(Path(__file__).resolve().parents[2] / "qcloud-copilot")
    assert v.cli_applicability is not None


def test_skill_version_sha_is_12_chars():
    v = parse_skill_version(Path(__file__).resolve().parents[2] / "qcloud-copilot")
    assert v.sha is not None
    assert len(v.sha) == 12


def test_skill_version_sha_changes_with_content():
    v1 = parse_skill_version(Path(__file__).resolve().parents[2] / "qcloud-copilot")
    v2 = parse_skill_version(Path(__file__).resolve().parents[2] / "qcloud-monitor-ops")
    # Different skills should have different SHAs (with extremely high probability)
    assert v1.sha != v2.sha


def test_skill_version_is_complete():
    v = parse_skill_version(Path(__file__).resolve().parents[2] / "qcloud-copilot")
    assert v.is_complete() is True


def test_skill_version_incomplete_without_skill_md(tmp_path):
    v = parse_skill_version(tmp_path)
    assert v.is_complete() is False


def test_copilot_version_singleton():
    v = copilot_version()
    assert v.skill_name == "qcloud-copilot"
    assert v.version == "1.1.0"  # matches current SKILL.md version
    assert v.sha is not None
