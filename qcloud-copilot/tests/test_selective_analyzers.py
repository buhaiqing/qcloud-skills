"""LC-2 CruiseRunner selective analyzer integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from copilot.blackboard import BlackboardClient
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


def _fake_report(tmp_path: Path, customer: str) -> Path:
    report_path = tmp_path / f"cruise-{customer}-sel.json"
    report_path.write_text(
        json.dumps(
            {
                "customer": customer,
                "summary": {"critical": 0, "warning": 0, "info": 0, "total_findings": 0},
                "analyzer_selection": {
                    "mode": "strategy_selected",
                    "requested": ["eip", "clb", "vm", "rds_mysql"],
                    "executed": ["eip", "clb", "vm", "rds_mysql"],
                    "skipped": [{"service": "redis", "reason": "topology_count=0"}],
                },
                "service_reports": [],
                "all_findings": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return report_path


def test_cruise_passes_strategy_file_from_blackboard(
    monkeypatch, tmp_path, client: BlackboardClient
):
    session_id = "ses-strategy"
    client.create(session_id, "选择性巡检")
    strategy = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / ".runtime/blackboard/fixtures/strategy-agent-session.json"
        ).read_text(encoding="utf-8")
    )
    client.write_evidence_chain(
        session_id,
        {"schema_version": "1.1", "strategy": strategy, "plan": {}, "process": [], "results": {}},
    )

    sniff_path = tmp_path / "sniff-朔州天源.json"
    sniff_path.write_text(
        json.dumps({"customer": "朔州天源", "raw": {"redis": []}}), encoding="utf-8"
    )
    report_path = _fake_report(tmp_path, "朔州天源")
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

    step = PlanStep(id="cruise-1", type="cruise_run", params={"customer": "朔州天源"})
    result = CruiseRunner().execute(step, {}, blackboard=client, session_id=session_id)

    assert result.status == "success"
    assert result.output["mode"] == "selective"
    analyze_cmds = [c for c in calls if any("cruise_analyze.py" in part for part in c)]
    assert len(analyze_cmds) == 1
    assert "--strategy-file" in analyze_cmds[0]
