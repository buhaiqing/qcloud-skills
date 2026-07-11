"""LC-3 strategy apply CLI and Blackboard write-back tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from copilot.blackboard import BlackboardClient
from copilot.cli import app
from copilot.evidence import build_evidence_chain
from copilot.strategy import apply_strategy, load_strategy_file

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / ".runtime/blackboard/fixtures/strategy-agent-session.json"
runner = CliRunner()


@pytest.fixture
def board_dir(tmp_path):
    repo_schema = REPO_ROOT / ".runtime" / "blackboard" / "schema.json"
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


def test_apply_strategy_writes_file_and_evidence_chain(client: BlackboardClient) -> None:
    strategy = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result = apply_strategy("ses-lc3", strategy, blackboard=client)

    assert result["decision_maker"] == "agent_session_v1"
    assert "redis" in {s["service"] for s in result["skipped_analyzers"]}

    strategy_path = client.board_dir / "strategy-ses-lc3.json"
    assert strategy_path.is_file()

    chain = client.read_evidence_chain("ses-lc3")
    assert chain is not None
    assert chain["strategy"]["decision_maker"] == "agent_session_v1"
    assert chain["strategy"]["agent_rationale"]
    assert "rds_mysql" in chain["strategy"]["selected_analyzers"]


def test_build_evidence_chain_prefers_agent_strategy() -> None:
    agent = json.loads(FIXTURE.read_text(encoding="utf-8"))
    chain = build_evidence_chain(
        user_request=agent["user_request"],
        plan=None,
        step_results=None,
        contributions={},
        agent_strategy=agent,
    )
    assert chain["strategy"]["decision_maker"] == "agent_session_v1"
    assert chain["strategy"]["strategy_schema"] == "1.2"
    assert chain["strategy"]["agent_rationale"] == agent["agent_rationale"]


def test_strategy_apply_cli(board_dir, monkeypatch) -> None:
    monkeypatch.setattr("copilot.blackboard.default_board_dir", lambda: board_dir)
    monkeypatch.setattr("copilot.strategy.default_board_dir", lambda: board_dir)
    result = runner.invoke(
        app,
        [
            "strategy",
            "apply",
            "--session",
            "ses-cli-strategy",
            "--file",
            str(FIXTURE),
            "--decision-maker",
            "agent_session_v1",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "Strategy applied" in result.stdout
    assert "agent_session_v1" in result.stdout

    client = BlackboardClient(board_dir=board_dir)
    chain = client.read_evidence_chain("ses-cli-strategy")
    assert chain["strategy"]["selected_analyzers"]


def test_load_strategy_file_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_strategy_file(tmp_path / "missing.json")
