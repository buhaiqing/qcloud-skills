"""Level 3 Phase 1 E2E: alert analysis → targeted cruise via blackboard (P1-T5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from copilot.blackboard import BlackboardClient
from copilot.integration.alert_intel import AlertIntelRunner
from copilot.integration.cruise import CruiseRunner
from copilot.models import PlanStep


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


def test_alert_to_cruise_blackboard_e2e(monkeypatch, tmp_path, board_dir):
    """V1 + V5: findings flow to cruise; session contributions are recoverable."""
    session_id = "ses-l3-e2e"
    client = BlackboardClient(board_dir=board_dir)
    user_request = "朔州天源最近 P0 告警多，分析并针对性巡检"
    client.create(session_id, user_request)

    resource_id = "rds-mysql-xxx"

    report_path = tmp_path / "cruise-report.json"
    report_path.write_text(
        '{"summary":{"critical":0,"warning":0,"info":0},"all_findings":[]}',
        encoding="utf-8",
    )

    def fake_run(cmd, **kwargs):
        class R:
            returncode = 0
            stdout = f"[已保存] JSON 报告已保存: {report_path}\n"
            stderr = ""

        return R()

    monkeypatch.setattr("copilot.integration.cruise.subprocess.run", fake_run)

    AlertIntelRunner().analyze(
        {
            "alarm_history": [
                {
                    "resourceId": resource_id,
                    "serviceCode": "rds",
                    "metricName": "cpu_util",
                    "status": "ALARM",
                }
            ],
            "time_window": "最近24h",
        },
        client,
        session_id,
    )

    step = PlanStep(
        id="cruise-e2e",
        type="cruise_run",
        params={"customer": "朔州天源", "region": "ap-guangzhou"},
    )
    cruise_result = CruiseRunner().execute(step, {}, blackboard=client, session_id=session_id)

    assert cruise_result.status == "success"
    assert resource_id in cruise_result.output.get("inspected", [])

    # V5: reload session blackboard — full contributions history
    reloaded = client.load(session_id)
    assert reloaded is not None
    assert reloaded["user_request"] == user_request
    assert "qcloud-monitor-ops" in reloaded["shared_context"]["contributions"]
    assert "qcloud-proactive-inspection" in reloaded["shared_context"]["contributions"]

    alert_hints = reloaded["shared_context"]["contributions"]["qcloud-monitor-ops"][
        "topology_hints"
    ]
    cruise_inspected = reloaded["shared_context"]["contributions"]["qcloud-proactive-inspection"][
        "topology_hints"
    ]
    assert resource_id in alert_hints
    assert resource_id in cruise_inspected
