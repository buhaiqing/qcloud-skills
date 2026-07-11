"""AIOps cruise blackboard read tests (P1-T4)."""

from __future__ import annotations

import json
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


@pytest.fixture
def client(board_dir):
    return BlackboardClient(board_dir=board_dir)


def _fake_analyze_report(tmp_path: Path, customer: str, resource_ids: list[str]) -> Path:
    report_path = tmp_path / f"cruise-{customer}-test.json"
    findings = []
    if resource_ids:
        findings.append(
            {
                "severity": "warning",
                "resource_id": resource_ids[0],
                "resource": resource_ids[0],
                "message": "mock targeted finding",
                "service": "rds_mysql",
            }
        )
    report_path.write_text(
        json.dumps(
            {
                "customer": customer,
                "summary": {
                    "critical": 0,
                    "warning": len(findings),
                    "info": 0,
                    "total_findings": len(findings),
                },
                "all_findings": findings,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return report_path


def test_cruise_reads_topology_hints_and_writes_contribution(
    monkeypatch, tmp_path, client: BlackboardClient
):
    session_id = "ses-cruise"
    client.create(session_id, "定向巡检")

    AlertIntelRunner().analyze(
        {
            "alarm_history": [
                {
                    "resourceId": "rds-mysql-target",
                    "serviceCode": "rds",
                    "metricName": "cpu_util",
                    "status": "ALARM",
                }
            ]
        },
        client,
        session_id,
    )

    report_path = _fake_analyze_report(tmp_path, "朔州天源", ["rds-mysql-target"])

    def fake_run(cmd, **kwargs):
        class R:
            returncode = 0
            stdout = f"[已保存] JSON 报告已保存: {report_path}\n"
            stderr = ""

        return R()

    monkeypatch.setattr("copilot.integration.cruise.subprocess.run", fake_run)

    step = PlanStep(id="cruise-1", type="cruise_run", params={"customer": "朔州天源"})
    result = CruiseRunner().execute(step, {}, blackboard=client, session_id=session_id)

    assert result.status == "success"
    assert result.output["mode"] == "targeted"
    assert "rds-mysql-target" in result.output["inspected"]

    board = client.load(session_id)
    assert "qcloud-proactive-inspection" in board["shared_context"]["contributions"]


def test_cruise_without_hints_uses_selective_mode(monkeypatch, tmp_path, client: BlackboardClient):
    session_id = "ses-full"
    client.create(session_id, "全量巡检")

    sniff_path = tmp_path / "sniff-测试-001.json"
    sniff_path.write_text("{}", encoding="utf-8")
    report_path = _fake_analyze_report(tmp_path, "测试", [])

    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)

        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        if "cruise_sniff.py" in cmd[1]:
            R.stdout = f"[已保存] JSON 已保存: {sniff_path}\n"
        elif "cruise_analyze.py" in cmd[1]:
            R.stdout = f"[已保存] JSON 报告已保存: {report_path}\n"
        return R()

    monkeypatch.setattr("copilot.integration.cruise.subprocess.run", fake_run)

    step = PlanStep(id="cruise-2", type="cruise_run", params={"customer": "测试"})
    result = CruiseRunner().execute(step, {}, blackboard=client, session_id=session_id)
    assert result.status == "success"
    assert result.output["mode"] == "selective"
    assert any("cruise_sniff.py" in part for cmd in calls for part in cmd)
    assert any("cruise_analyze.py" in part for cmd in calls for part in cmd)
