"""Blackboard read-path perf regression tests.

Covers the correctness contract that must hold after removing per-read
jsonschema validation + deepcopy from the read path (commit fff487c):

  - read_contributions / read_evidence_chain return content equivalent to the
    previous deepcopy behavior
  - mutating the returned reference does NOT pollute the on-disk board or leak
    across calls (each read re-parses the file into a fresh object)
  - validator cache invalidates when the schema file changes with identical
    mtime+size (content-hash key)
  - write-path validation still rejects invalid contributions
"""

from __future__ import annotations

import json
import os

import jsonschema
import pytest
from copilot import blackboard as bb_module
from copilot.blackboard import BlackboardClient, validate_blackboard


@pytest.fixture
def board_dir(tmp_path):
    repo_schema = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "assets"
        / "blackboard.schema.json"
    )
    target_dir = tmp_path / "blackboard"
    target_dir.mkdir()
    target_dir.joinpath("schema.json").write_text(
        repo_schema.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return target_dir


@pytest.fixture
def client(board_dir):
    return BlackboardClient(board_dir=board_dir)


def _seed_contribution(client: BlackboardClient, session_id: str) -> None:
    client.create(session_id, "巡检")
    client.write_contribution(
        session_id,
        "qcloud-monitor-ops",
        {
            "version": "0.4.0",
            "verdict": "PASS",
            "findings": [
                {
                    "id": "f1",
                    "severity": "P0",
                    "summary": "RDS CPU",
                    "resource_id": "rds-mysql-abc",
                }
            ],
            "topology_hints": ["rds-mysql-abc"],
            "metadata": {},
        },
    )


def test_read_contributions_returns_same_content(client: BlackboardClient):
    """Read path returns the same data as before (deepcopy-free but equivalent)."""
    _seed_contribution(client, "ses-content")
    contribs = client.read_contributions("ses-content")
    assert "qcloud-monitor-ops" in contribs
    c = contribs["qcloud-monitor-ops"]
    assert c["verdict"] == "PASS"
    assert c["findings"][0]["severity"] == "P0"


def test_mutating_returned_contributions_does_not_pollute(client: BlackboardClient):
    """Mutating the returned reference must not touch disk or leak across calls."""
    _seed_contribution(client, "ses-mutate")
    contribs = client.read_contributions("ses-mutate")
    contribs["qcloud-monitor-ops"]["verdict"] = "HACKED"

    # Disk must be unchanged (write-path validation would also reject HACKED).
    re_read = client.read_contributions("ses-mutate")
    assert re_read["qcloud-monitor-ops"]["verdict"] == "PASS"


def test_read_evidence_chain_returns_isolated_object(client: BlackboardClient):
    _seed_contribution(client, "ses-chain")
    chain = {
        "schema_version": "1.2",
        "strategy": {"mode": "rollback", "decision_maker": "llm_reasoner_v1"},
        "plan": {},
        "process": [],
        "results": {},
    }
    client.write_evidence_chain("ses-chain", chain)
    got = client.read_evidence_chain("ses-chain")
    assert got == chain
    got["strategy"]["mode"] = "mutated"
    assert client.read_evidence_chain("ses-chain")["strategy"]["mode"] == "rollback"


def test_validator_cache_invalidates_on_content_change_same_size_mtime(tmp_path, monkeypatch):
    """Same path+size+mtime but different content must NOT reuse a stale validator."""
    schema = {
        "type": "object",
        "properties": {"a": {"type": "string"}},
        "required": ["a"],
        "additionalProperties": False,
    }
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")

    # schema_path() prefers the repo asset, so pin it to our temp schema.
    monkeypatch.setattr(bb_module, "schema_path", lambda board_dir=None: schema_path)

    # First validation under the original schema.
    validate_blackboard({"a": "ok"}, tmp_path)

    # Replace schema with DIFFERENT content but IDENTICAL byte length ("string" and
    # "number" are both 8 chars) and preserved mtime, to defeat a (mtime, size) key.
    new_schema = {
        "type": "object",
        "properties": {"a": {"type": "number"}},
        "required": ["a"],
        "additionalProperties": False,
    }
    assert len(json.dumps(new_schema)) == len(json.dumps(schema))  # same length
    schema_path.write_text(json.dumps(new_schema), encoding="utf-8")
    st = os.stat(schema_path)
    os.utime(schema_path, (st.st_atime, st.st_mtime))

    # The new schema must be honored (a is now a number): the old validator would
    # have accepted {"a": "ok"}, so this must raise, proving cache invalidation.
    with pytest.raises(jsonschema.ValidationError):
        validate_blackboard({"a": "ok"}, tmp_path)


def test_write_path_validation_still_rejects_invalid(client: BlackboardClient):
    """Removing read-path validation must not have disabled write-path validation."""
    client.create("ses-write", "巡检")
    with pytest.raises(jsonschema.ValidationError):
        client.write_contribution("ses-write", "qcloud-monitor-ops", {"bad": "shape"})
