"""LC-5 integration: CI mode strategy apply via CruiseRunner hook."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from copilot.blackboard import BlackboardClient
from copilot.integration.cruise import CruiseRunner, _apply_ci_mode_strategy
from copilot.models import PlanStep

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = REPO_ROOT / ".runtime" / "blackboard" / "schema.json"


@pytest.fixture
def board_client(tmp_path: Path) -> BlackboardClient:
    board_dir = tmp_path / "blackboard"
    board_dir.mkdir()
    board_dir.joinpath("schema.json").write_text(
        SCHEMA.read_text(encoding="utf-8"), encoding="utf-8"
    )
    return BlackboardClient(board_dir=board_dir)


def test_apply_ci_mode_strategy_writes_llm_reasoner(board_client: BlackboardClient) -> None:
    sniff = {
        "customer": "朔州天源",
        "raw": {
            "vms": [{"instanceId": "i-1"}],
            "lbs": [{"loadBalancerId": "lb-1"}],
            "eips": [],
            "rds": [],
            "redis": [],
        },
    }
    context = {
        "inspection_mode": "ci",
        "inspection_effective": "fallback",
        "inspection_trigger": "keyword",
        "inspection_matched_keyword": "无人值守",
        "inspection_warnings": ["ci_requested_but_llm_disabled"],
        "user_query": "朔州天源 无人值守 定时巡检",
    }

    strategy = _apply_ci_mode_strategy(
        context,
        board_client,
        "ses-lc5",
        sniff,
        "朔州天源",
        "ap-guangzhou",
        None,
    )
    assert strategy["strategy_schema"] == "1.2"
    assert strategy["decision_maker"] == "topology_reasoner_v1"
    assert strategy["selected_analyzers"]

    chain = board_client.read_evidence_chain("ses-lc5")
    assert chain is not None
    assert chain["strategy"]["decision_maker"] == "topology_reasoner_v1"
    assert (board_client.board_dir / "strategy-ses-lc5.json").is_file()


def test_apply_ci_mode_never_overrides_agent(board_client: BlackboardClient) -> None:
    agent = json.loads(
        (REPO_ROOT / ".runtime/blackboard/fixtures/strategy-agent-session.json").read_text(
            encoding="utf-8"
        )
    )
    sniff = {"raw": {"vms": [], "redis": []}}
    context = {"inspection_effective": "ci", "user_query": "CI模式 test"}

    result = _apply_ci_mode_strategy(
        context,
        board_client,
        "ses-agent",
        sniff,
        "朔州天源",
        "ap-guangzhou",
        agent,
    )
    assert result["decision_maker"] == "agent_session_v1"
    assert not (board_client.board_dir / "strategy-ses-agent.json").exists()


def test_cruise_ci_path_invokes_strategy_apply(board_client: BlackboardClient) -> None:
    output_dir = REPO_ROOT / ".runtime" / "proactive-inspection"
    output_dir.mkdir(parents=True, exist_ok=True)
    sniff_path = output_dir / "sniff-朔州天源-lc5test.json"
    sniff_path.write_text(
        json.dumps(
            {
                "customer": "朔州天源",
                "raw": {"vms": [{"instanceId": "i-1"}], "lbs": [], "redis": []},
            }
        ),
        encoding="utf-8",
    )
    cruise_path = output_dir / "cruise-朔州天源-lc5test.json"
    cruise_path.write_text(
        json.dumps({"summary": {"critical": 0, "warning": 0}, "all_findings": []}),
        encoding="utf-8",
    )

    class FakeProc:
        returncode = 0
        stdout = f"Saved JSON report to {cruise_path}\n"
        stderr = ""

    step = PlanStep(
        id="cruise-1", type="cruise_run", skill="qcloud-proactive-inspection", description="cruise"
    )
    runner = CruiseRunner()
    context = {
        "customer": "朔州天源",
        "inspection_effective": "fallback",
        "user_query": "无人值守 朔州天源",
    }

    with (
        patch.object(runner, "_run_script", return_value=FakeProc()),
        patch(
            "copilot.integration.cruise._sniff_script",
            return_value=REPO_ROOT / "qcloud-proactive-inspection/scripts/01-perceive/cruise_sniff.py",
        ),
        patch(
            "copilot.integration.cruise._analyze_script",
            return_value=REPO_ROOT / "qcloud-proactive-inspection/scripts/02-reason/cruise_analyze.py",
        ),
        patch(
            "copilot.integration.cruise._parse_saved_json_path",
            side_effect=[str(sniff_path), str(cruise_path)],
        ),
    ):
        result = runner._execute_full_cruise(
            step,
            "朔州天源",
            "ap-guangzhou",
            session_id="ses-lc5-cruise",
            context=context,
            blackboard=board_client,
        )

    assert result.status == "success"
    chain = board_client.read_evidence_chain("ses-lc5-cruise")
    assert chain is not None
    assert chain["strategy"]["selected_analyzers"]
