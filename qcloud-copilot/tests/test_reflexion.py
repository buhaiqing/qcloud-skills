"""Tests for copilot.quality.reflexion (P4: unified 4-tuple dedup key)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from copilot.quality import reflexion


def test_normalize_reflexion_key_shape() -> None:
    key = reflexion.normalize_reflexion_key(
        "Runtime", "Qcloud-CVM-Ops", "TerminateInstances i-abc", "MissingParameter X"
    )
    assert key == ("runtime", "qcloud-cvm-ops", "terminateinstances", "missingparameter x")


def test_normalize_reflexion_key_matches_gcl_sink() -> None:
    cat, skill, cmd, err = "runtime", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter"
    # copilot and GCL reflexion_store use identical normalize_reflexion_key shape
    assert ":".join(reflexion.normalize_reflexion_key(cat, skill, cmd, err)) == (
        "runtime:qcloud-cvm-ops:terminateinstances:missingparameter"
    )


def test_write_reflexion_emits_dedup_key_column() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        reflexion.SCRATCH_DIR = Path(tmp)
        reflexion.write_reflexion("runtime", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter", "Fix it")
        files = list(Path(tmp).glob("*-scratch.md"))
        assert files, "scratch file not written"
        content = files[0].read_text()
        assert "runtime:qcloud-cvm-ops:terminateinstances:missingparameter" in content


def test_aggregate_scratch_dedups_same_normalized_command() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        reflexion.SCRATCH_DIR = Path(tmp)
        reflexion.DOCS_FAILURE_PATTERNS = Path(tmp) / "failure-patterns.md"
        reflexion.DOCS_FAILURE_PATTERNS.write_text(
            "# Reflexion Store\n\n## 4. Runtime\n\n"
            "| Category | Skill | Command | Error | Fix | Count | Reusable |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
        )
        # Two rows differ only by command casing → must collapse to one key
        reflexion.write_reflexion("runtime", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter", "Fix A")
        reflexion.write_reflexion("runtime", "qcloud-cvm-ops", "terminateinstances", "MissingParameter", "Fix B")

        merged = reflexion.aggregate_scratch()
        # Only one new row appended (the 2nd is a 4-tuple duplicate)
        assert merged == 1


def test_aggregate_scratch_keeps_distinct_commands() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        reflexion.SCRATCH_DIR = Path(tmp)
        reflexion.DOCS_FAILURE_PATTERNS = Path(tmp) / "failure-patterns.md"
        reflexion.DOCS_FAILURE_PATTERNS.write_text(
            "# Reflexion Store\n\n## 4. Runtime\n\n"
            "| Category | Skill | Command | Error | Fix | Count | Reusable |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
        )
        reflexion.write_reflexion("runtime", "qcloud-cvm-ops", "TerminateInstances", "MissingParameter", "Fix A")
        reflexion.write_reflexion("runtime", "qcloud-cvm-ops", "RunInstances", "MissingParameter", "Fix B")

        merged = reflexion.aggregate_scratch()
        assert merged == 2
