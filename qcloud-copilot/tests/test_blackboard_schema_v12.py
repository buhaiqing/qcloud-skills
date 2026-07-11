"""Blackboard schema 1.2 migration tests (BC-T1)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from copilot.blackboard import (
    SCHEMA_VERSION,
    migrate_board,
    migrate_to_1_1,
    migrate_to_1_2,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / ".runtime" / "blackboard" / "schema.json"
FIXTURES_DIR = REPO_ROOT / ".runtime" / "blackboard" / "fixtures"


@pytest.fixture
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def validator(schema: dict) -> jsonschema.Draft7Validator:
    return jsonschema.Draft7Validator(
        schema,
        format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER,
    )


# ---------------------------------------------------------------------------
# Schema 1.2: top-level enum + ask_user_response pending_action
# ---------------------------------------------------------------------------


def test_schema_version_constant_is_1_2() -> None:
    """Head of migration chain must equal SCHEMA_VERSION."""
    assert SCHEMA_VERSION == "1.2"


def test_schema_version_enum_accepts_all_three() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["enum"] == ["1.0", "1.1", "1.2"]


def test_pending_action_accepts_ask_user_response(schema: dict) -> None:
    pa = schema["definitions"]["pending_action"]
    assert "ask_user_response" in pa["properties"]["action"]["enum"]
    assert "invoke_skill" in pa["properties"]["action"]["enum"]


def test_pending_action_ask_user_fields_optional(schema: dict) -> None:
    """All 5 ask_user fields are optional (additionalProperties=false still holds)."""
    pa = schema["definitions"]["pending_action"]
    for field in (
        "question_id",
        "selected_option",
        "selected_label",
        "timeout_seconds",
        "responded_at",
    ):
        assert field in pa["properties"], f"missing {field}"
    required = set(pa["required"])
    for field in (
        "question_id",
        "selected_option",
        "selected_label",
        "timeout_seconds",
        "responded_at",
    ):
        assert field not in required, f"{field} must be optional"
    # additionalProperties=false still enforced
    assert pa["additionalProperties"] is False


# ---------------------------------------------------------------------------
# Backward compatibility: 1.0/1.1 fixtures must still validate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture_name",
    [
        "minimal.json",
        "alert-contribution.json",
        "evidence-chain.json",
        "evidence-chain-agent-session.json",
    ],
)
def test_v10_v11_fixtures_still_validate(
    validator: jsonschema.Draft7Validator, fixture_name: str
) -> None:
    """Schema 1.2 is additive — older fixtures (1.0/1.1) must still pass."""
    instance = json.loads((FIXTURES_DIR / fixture_name).read_text(encoding="utf-8"))
    validator.validate(instance)


# ---------------------------------------------------------------------------
# New 1.2 fixture
# ---------------------------------------------------------------------------


def test_pending_action_ask_user_response_fixture_validates(
    validator: jsonschema.Draft7Validator,
) -> None:
    instance = json.loads(
        (FIXTURES_DIR / "pending-action-ask-user-response.json").read_text(encoding="utf-8")
    )
    validator.validate(instance)
    pa = instance["shared_context"]["pending_actions"][0]
    assert pa["action"] == "ask_user_response"
    assert pa["selected_option"] == "ap-guangzhou"
    assert pa["timeout_seconds"] == 60
    assert pa["responded_at"].startswith("2026-07-11")


def test_pending_action_ask_user_response_required_still_enforced(
    validator: jsonschema.Draft7Validator,
) -> None:
    """Adding ask_user fields must not weaken the 3 required fields."""
    instance = json.loads(
        (FIXTURES_DIR / "pending-action-ask-user-response.json").read_text(encoding="utf-8")
    )
    del instance["shared_context"]["pending_actions"][0]["skill"]
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(instance)


# ---------------------------------------------------------------------------
# Migration chain
# ---------------------------------------------------------------------------


def test_migrate_to_1_2_is_pure_bump() -> None:
    board = {
        "schema_version": "1.1",
        "shared_context": {"contributions": {}, "pending_actions": [], "evidence_chain": None},
    }
    out = migrate_to_1_2(board)
    assert out is board  # in-place


def test_migrate_board_idempotent_at_1_2() -> None:
    board = {"schema_version": "1.2"}
    out = migrate_board(board)
    assert out["schema_version"] == "1.2"


def test_migrate_board_1_0_to_1_2() -> None:
    board = {
        "schema_version": "1.0",
        "shared_context": {"contributions": {}, "pending_actions": []},
    }
    out = migrate_board(board)
    assert out["schema_version"] == "1.2"
    assert "evidence_chain" in out["shared_context"]  # 1.0→1.1 step


def test_migrate_board_1_1_to_1_2() -> None:
    board = {
        "schema_version": "1.1",
        "shared_context": {"evidence_chain": None, "pending_actions": []},
    }
    out = migrate_board(board)
    assert out["schema_version"] == "1.2"


def test_migrate_board_missing_version_defaults_to_1_0_then_bumps() -> None:
    """Pre-schema-version boards (legacy) should land on 1.2."""
    board = {"shared_context": {"contributions": {}, "pending_actions": []}}
    out = migrate_board(board)
    assert out["schema_version"] == "1.2"


def test_migrate_to_1_1_idempotent() -> None:
    """Calling 1.1 migration twice must not double-add evidence_chain."""
    board = {
        "schema_version": "1.0",
        "shared_context": {"contributions": {}, "pending_actions": []},
    }
    migrate_to_1_1(board)
    assert board["shared_context"].get("evidence_chain") is None
    migrate_to_1_1(board)  # again
    assert "evidence_chain" in board["shared_context"]
