"""Tests for copilot.quality.reflexion (P4: unified 4-tuple dedup key)."""

from __future__ import annotations

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
