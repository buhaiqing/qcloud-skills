"""Inspection strategy schema 1.2 tests (LC-1-T1 / LC-1-T4)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / ".runtime" / "blackboard" / "schema.json"
FIXTURES_DIR = REPO_ROOT / ".runtime" / "blackboard" / "fixtures"


@pytest.fixture
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def board_validator(schema: dict) -> jsonschema.Draft7Validator:
    return jsonschema.Draft7Validator(
        schema,
        format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER,
    )


@pytest.fixture
def strategy_validator(schema: dict) -> jsonschema.Draft7Validator:
    subschema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        **schema["definitions"]["inspection_strategy"],
        "definitions": {
            "skipped_analyzer": schema["definitions"]["skipped_analyzer"],
            "priority_chain_item": schema["definitions"]["priority_chain_item"],
        },
    }
    return jsonschema.Draft7Validator(
        subschema,
        format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER,
    )


def test_strategy_dandong_fixture(strategy_validator: jsonschema.Draft7Validator) -> None:
    strategy = json.loads(
        (FIXTURES_DIR / "strategy-agent-session-dandong.json").read_text(encoding="utf-8")
    )
    strategy_validator.validate(strategy)
    assert "redis" in strategy["selected_analyzers"]


def test_strategy_agent_session_fixture(strategy_validator: jsonschema.Draft7Validator) -> None:
    strategy = json.loads(
        (FIXTURES_DIR / "strategy-agent-session.json").read_text(encoding="utf-8")
    )
    strategy_validator.validate(strategy)
    assert strategy["strategy_schema"] == "1.2"
    assert strategy["decision_maker"] == "agent_session_v1"
    assert "redis" in {s["service"] for s in strategy["skipped_analyzers"]}


def test_evidence_chain_agent_session_board(board_validator: jsonschema.Draft7Validator) -> None:
    board = json.loads(
        (FIXTURES_DIR / "evidence-chain-agent-session.json").read_text(encoding="utf-8")
    )
    board_validator.validate(board)


@pytest.mark.parametrize(
    "fixture_name",
    ["minimal.json", "alert-contribution.json", "evidence-chain.json"],
)
def test_legacy_board_fixtures_still_valid(
    board_validator: jsonschema.Draft7Validator, fixture_name: str
) -> None:
    board = json.loads((FIXTURES_DIR / fixture_name).read_text(encoding="utf-8"))
    board_validator.validate(board)


def test_invalid_decision_maker_rejected(strategy_validator: jsonschema.Draft7Validator) -> None:
    bad = json.loads((FIXTURES_DIR / "strategy-agent-session.json").read_text(encoding="utf-8"))
    bad["decision_maker"] = "cursor_only_v99"
    with pytest.raises(jsonschema.ValidationError):
        strategy_validator.validate(bad)


def test_invalid_skipped_analyzer_missing_reason(
    strategy_validator: jsonschema.Draft7Validator,
) -> None:
    bad = json.loads((FIXTURES_DIR / "strategy-agent-session.json").read_text(encoding="utf-8"))
    bad["skipped_analyzers"] = [{"service": "redis"}]
    with pytest.raises(jsonschema.ValidationError):
        strategy_validator.validate(bad)


def test_invalid_analysis_depth_enum(strategy_validator: jsonschema.Draft7Validator) -> None:
    bad = json.loads((FIXTURES_DIR / "strategy-agent-session.json").read_text(encoding="utf-8"))
    bad["analysis_depth"] = {"vm": "ultra_deep"}
    with pytest.raises(jsonschema.ValidationError):
        strategy_validator.validate(bad)
