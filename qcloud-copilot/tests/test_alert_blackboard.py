"""Alert intelligence blackboard write tests (P1-T3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from copilot.blackboard import BlackboardClient
from copilot.integration.alert_intel import AlertIntelRunner, SKILL_NAME


@pytest.fixture
def board_dir(tmp_path):
    repo_schema = Path(__file__).resolve().parents[2] / ".runtime" / "blackboard" / "schema.json"
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


def test_alert_writes_contribution_with_topology_hints(client: BlackboardClient):
    client.create("ses-alert", "朔州天源 P0 告警")
    runner = AlertIntelRunner()
    alarms = [
        {
            "resourceId": "rds-mysql-xxx",
            "serviceCode": "rds",
            "metricName": "cpu_util",
            "status": "ALARM",
        }
    ]
    contribution = runner.analyze(
        {"alarm_history": alarms, "time_window": "最近24h"},
        client,
        "ses-alert",
    )

    assert contribution["verdict"] == "CRITICAL"
    assert "rds-mysql-xxx" in contribution["topology_hints"]

    board = client.load("ses-alert")
    assert SKILL_NAME in board["shared_context"]["contributions"]
    assert board["shared_context"]["pending_actions"]


def test_alert_pass_when_no_alarms(client: BlackboardClient):
    client.create("ses-empty", "无告警")
    runner = AlertIntelRunner()
    contribution = runner.analyze({"alarm_history": []}, client, "ses-empty")
    assert contribution["verdict"] == "PASS"
    assert contribution["topology_hints"] == []
