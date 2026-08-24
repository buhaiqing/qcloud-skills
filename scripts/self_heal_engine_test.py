#!/usr/bin/env python3
"""Tests for self_heal_engine.py."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

from self_heal_engine import (
    FixProposal,
    SelfHealEngine,
    _load_failure_patterns,
    _skill_to_skill_path,
)


class TestFixProposal:
    def test_to_dict(self):
        p = FixProposal(
            level="L1",
            skill="qcloud-cvm-ops",
            error_code="InvalidInstanceId",
            occurrence_count=7,
            target_file="qcloud-cvm-ops/SKILL.md",
            old_content="",
            new_content="# patched",
            rationale="test",
            risk_assessment="LOW",
            auto_merge=True,
        )
        d = p.to_dict()
        assert d["level"] == "L1"
        assert d["skill"] == "qcloud-cvm-ops"
        assert d["error_code"] == "InvalidInstanceId"
        assert d["occurrence_count"] == 7
        assert d["auto_merge"] is True


class TestSkillToSkillPath:
    def test_maps_skill_to_path(self):
        path = _skill_to_skill_path("qcloud-cvm-ops")
        assert path.name == "SKILL.md"
        assert "qcloud-cvm-ops" in str(path)


class TestLoadFailurePatterns:
    def test_empty_file_returns_empty_list(self, tmp_path):
        fp = tmp_path / "failure-patterns.md"
        fp.write_text("# Failure Patterns\n")
        patterns = _load_failure_patterns(fp)
        assert patterns == []

    def test_parses_section_header(self, tmp_path):
        fp = tmp_path / "failure-patterns.md"
        fp.write_text(
            "## [qcloud-cvm-ops] / [InvalidInstanceId]\n"
            "- count: 7\n"
            "- fix: Check instance state\n"
            "- first_seen: 2026-08-01\n"
            "- last_seen: 2026-08-20\n"
        )
        patterns = _load_failure_patterns(fp)
        assert len(patterns) == 1
        assert patterns[0]["skill"] == "qcloud-cvm-ops"
        assert patterns[0]["error"] == "InvalidInstanceId"
        assert patterns[0]["count"] == 7

    def test_parses_multiple_sections(self, tmp_path):
        fp = tmp_path / "failure-patterns.md"
        fp.write_text(
            "## [qcloud-cvm-ops] / [InvalidInstanceId]\n"
            "- count: 5\n"
            "## [qcloud-redis-ops] / [RedisConnectionError]\n"
            "- count: 3\n"
        )
        patterns = _load_failure_patterns(fp)
        assert len(patterns) == 2
        skills = [p["skill"] for p in patterns]
        assert "qcloud-cvm-ops" in skills
        assert "qcloud-redis-ops" in skills


class TestSelfHealEngine:
    def test_analyze_failures_no_patterns(self, tmp_path):
        engine = SelfHealEngine(
            failure_patterns_path=tmp_path / "nonexistent.md",
            min_occurrences=5,
        )
        proposals = engine.analyze_failures()
        assert proposals == []

    def test_analyze_failures_below_threshold(self, tmp_path):
        fp = tmp_path / "failure-patterns.md"
        fp.write_text(
            "## [qcloud-cvm-ops] / [SomeError]\n"
            "- count: 3\n"
        )
        engine = SelfHealEngine(
            failure_patterns_path=fp,
            min_occurrences=5,
        )
        proposals = engine.analyze_failures()
        assert proposals == []

    def test_analyze_failures_above_threshold_l1(self, tmp_path):
        fp = tmp_path / "failure-patterns.md"
        fp.write_text(
            "## [qcloud-cvm-ops] / [InvalidInstanceId]\n"
            "- count: 7\n"
            "- fix: Check instance state before terminating\n"
        )
        engine = SelfHealEngine(failure_patterns_path=fp, min_occurrences=5)
        proposals = engine.analyze_failures()
        assert len(proposals) == 1
        p = proposals[0]
        assert p.level == "L1"
        assert p.skill == "qcloud-cvm-ops"
        assert p.error_code == "InvalidInstanceId"
        assert p.occurrence_count == 7
        assert p.auto_merge is True
        assert p.risk_assessment == "LOW: only appends to error table"

    def test_analyze_failures_l2_fix_type(self, tmp_path):
        fp = tmp_path / "failure-patterns.md"
        fp.write_text(
            "## [qcloud-cvm-ops] / [TimeoutError]\n"
            "- count: 8\n"
            "- fix_type: L2\n"
        )
        engine = SelfHealEngine(failure_patterns_path=fp, min_occurrences=5)
        proposals = engine.analyze_failures()
        assert len(proposals) == 1
        p = proposals[0]
        assert p.level == "L2"
        assert p.auto_merge is False
        assert p.risk_assessment == "MEDIUM: modifies default parameters"

    def test_analyze_failures_l3_fix_type(self, tmp_path):
        fp = tmp_path / "failure-patterns.md"
        fp.write_text(
            "## [qcloud-cvm-ops] / [OrderError]\n"
            "- count: 6\n"
            "- fix_type: L3\n"
        )
        engine = SelfHealEngine(failure_patterns_path=fp, min_occurrences=5)
        proposals = engine.analyze_failures()
        assert len(proposals) == 1
        p = proposals[0]
        assert p.level == "L3"
        assert p.auto_merge is False
        assert p.risk_assessment == "HIGH: modifies command execution flow"

    def test_generate_l1_fix_creates_error_section_when_no_table(self, tmp_path):
        # Create isolated env so we don't read real SKILL.md
        import self_heal_engine as she

        orig_root = she.ROOT
        she.ROOT = tmp_path
        try:
            fp = tmp_path / "fp.md"
            fp.write_text("## [qcloud-cvm-ops] / [NewError]\n- count: 7\n")
            engine = SelfHealEngine(failure_patterns_path=fp)
            pattern = ("qcloud-cvm-ops", "NewError", {"count": 7, "fix": "Restart the instance"})
            proposal = engine.generate_l1_fix(pattern)
        finally:
            she.ROOT = orig_root

        assert proposal.level == "L1"
        assert "NewError" in proposal.new_content
        assert "Error Reference" in proposal.new_content

    def test_generate_l1_fix_appends_to_existing_table(self, tmp_path):
        import self_heal_engine as she

        orig_root = she.ROOT
        she.ROOT = tmp_path
        try:
            fp = tmp_path / "fp.md"
            fp.write_text("## [qcloud-cvm-ops] / [NewError]\n- count: 7\n")
            # Create a fake SKILL.md with a table
            skill_dir = tmp_path / "qcloud-cvm-ops"
            skill_dir.mkdir()
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text(
                "## Error\n\n"
                "| Error Code | Occurrences | Recovery |\n"
                "| --- | --- | --- |\n"
                "| `ExistingError` | 3 | Restart |\n"
            )
            engine = SelfHealEngine(failure_patterns_path=fp)
            pattern = ("qcloud-cvm-ops", "NewError", {"count": 7, "fix": "Restart the instance"})
            proposal = engine.generate_l1_fix(pattern)
        finally:
            she.ROOT = orig_root

        assert "NewError" in proposal.new_content
        assert "ExistingError" in proposal.new_content

    def test_generate_l2_fix_returns_placeholder(self):
        engine = SelfHealEngine(min_occurrences=5)
        pattern = ("qcloud-cvm-ops", "TimeoutError", {"count": 8})
        proposal = engine.generate_l2_fix(pattern)
        assert proposal.level == "L2"
        assert proposal.auto_merge is False
        assert "LLM" in proposal.rationale

    def test_generate_l3_fix_returns_placeholder(self):
        engine = SelfHealEngine(min_occurrences=5)
        pattern = ("qcloud-cvm-ops", "OrderError", {"count": 6})
        proposal = engine.generate_l3_fix(pattern)
        assert proposal.level == "L3"
        assert proposal.auto_merge is False
        assert "LLM" in proposal.rationale

    def test_apply_fix_writes_file(self, tmp_path):
        engine = SelfHealEngine(failure_patterns_path=tmp_path / "fp.md")
        proposal = FixProposal(
            level="L1",
            skill="qcloud-cvm-ops",
            error_code="TestError",
            occurrence_count=5,
            target_file=str(tmp_path / "test.md"),
            old_content="",
            new_content="# New content",
            rationale="test",
            risk_assessment="LOW",
            auto_merge=True,
        )
        ok = engine.apply_fix(proposal)
        assert ok is True
        assert (tmp_path / "test.md").read_text() == "# New content"

    def test_apply_fix_returns_false_on_oserror(self):
        engine = SelfHealEngine(failure_patterns_path="/nonexistent/fp.md")
        proposal = FixProposal(
            level="L1",
            skill="qcloud-cvm-ops",
            error_code="TestError",
            occurrence_count=5,
            target_file="/proc/0/test.md",
            old_content="",
            new_content="# New content",
            rationale="test",
            risk_assessment="LOW",
            auto_merge=True,
        )
        ok = engine.apply_fix(proposal)
        assert ok is False

    def test_verify_fix_returns_false_if_file_missing(self):
        engine = SelfHealEngine()
        proposal = FixProposal(
            level="L1",
            skill="qcloud-cvm-ops",
            error_code="TestError",
            occurrence_count=5,
            target_file="nonexistent/file.md",
            old_content="",
            new_content="# New",
            rationale="test",
            risk_assessment="LOW",
            auto_merge=True,
        )
        ok = engine.verify_fix(proposal)
        assert ok is False

    def test_create_pr_returns_empty_without_token(self, tmp_path):
        old_token = os.environ.pop("GITHUB_TOKEN", None)
        try:
            engine = SelfHealEngine(
                failure_patterns_path=tmp_path / "fp.md",
                github_token=None,
            )
            proposal = FixProposal(
                level="L1",
                skill="qcloud-cvm-ops",
                error_code="TestError",
                occurrence_count=5,
                target_file="test.md",
                old_content="",
                new_content="# New",
                rationale="test",
                risk_assessment="LOW",
                auto_merge=True,
            )
            url = engine.create_pr(proposal)
            assert url == ""
        finally:
            if old_token is not None:
                os.environ["GITHUB_TOKEN"] = old_token


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
