"""BlackboardClient tests (P1-T2)."""

from __future__ import annotations

import json

import jsonschema
import pytest

from copilot.blackboard import BlackboardClient, validate_blackboard


@pytest.fixture
def board_dir(tmp_path):
    repo_schema = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / ".runtime"
        / "blackboard"
        / "schema.json"
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


def test_create_and_load(client: BlackboardClient):
    board = client.create("ses-test", "巡检济南银座")
    assert board["session_id"] == "ses-test"
    assert board["user_request"] == "巡检济南银座"
    assert board["status"] == "active"

    loaded = client.load("ses-test")
    assert loaded is not None
    assert loaded["session_id"] == "ses-test"


def test_write_contribution_and_topology_hints(client: BlackboardClient):
    client.create("ses-c1", "告警分析")
    client.write_contribution(
        "ses-c1",
        "qcloud-monitor-ops",
        {
            "version": "0.4.0",
            "verdict": "CRITICAL",
            "findings": [
                {
                    "id": "f1",
                    "severity": "P0",
                    "summary": "RDS CPU",
                    "resource_id": "rds-mysql-abc",
                }
            ],
            "topology_hints": ["rds-mysql-abc"],
            "metadata": {"alarm_count": 1},
        },
    )
    hints = client.read_topology_hints("ses-c1")
    assert hints == ["rds-mysql-abc"]

    contribs = client.read_contributions("ses-c1")
    assert "qcloud-monitor-ops" in contribs


def test_idempotent_create_load(client: BlackboardClient):
    first = client.create("ses-idem", "req")
    second = client.load("ses-idem")
    assert first["session_id"] == second["session_id"]
    assert first["created_at"] == second["created_at"]


def test_invalid_contribution_rejected(client: BlackboardClient):
    client.create("ses-bad", "x")
    with pytest.raises(jsonschema.ValidationError):
        client.write_contribution(
            "ses-bad",
            "qcloud-monitor-ops",
            {"version": "0.4.0", "verdict": "PASS"},
        )


def test_pending_action(client: BlackboardClient):
    client.create("ses-pa", "x")
    client.add_pending_action(
        "ses-pa",
        {
            "action": "invoke_skill",
            "skill": "qcloud-proactive-inspection",
            "reason": "P0 requires cruise",
        },
    )
    board = client.load("ses-pa")
    assert len(board["shared_context"]["pending_actions"]) == 1


def test_set_status(client: BlackboardClient):
    client.create("ses-st", "x")
    client.set_status("ses-st", "completed")
    board = client.load("ses-st")
    assert board["status"] == "completed"


def test_validate_blackboard_roundtrip(client: BlackboardClient):
    client.create("ses-val", "validate me")
    path = client.board_dir / "ses-val.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_blackboard(data, client.board_dir)
