"""Blackboard schema validation tests (P1-T1)."""

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
def validator(schema: dict) -> jsonschema.Draft7Validator:
    return jsonschema.Draft7Validator(
        schema,
        format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER,
    )


@pytest.mark.parametrize(
    "fixture_name",
    [
        "minimal.json",
        "alert-contribution.json",
        "evidence-chain.json",
        "evidence-chain-agent-session.json",
    ],
)
def test_fixture_validates(validator: jsonschema.Draft7Validator, fixture_name: str) -> None:
    instance = json.loads((FIXTURES_DIR / fixture_name).read_text(encoding="utf-8"))
    validator.validate(instance)


def test_invalid_missing_contribution_fields(validator: jsonschema.Draft7Validator) -> None:
    bad = json.loads((FIXTURES_DIR / "minimal.json").read_text(encoding="utf-8"))
    bad["shared_context"]["contributions"] = {
        "qcloud-monitor-ops": {
            "version": "0.4.0",
            "verdict": "PASS",
        }
    }
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(bad)


def test_invalid_verdict_enum(validator: jsonschema.Draft7Validator) -> None:
    bad = json.loads((FIXTURES_DIR / "minimal.json").read_text(encoding="utf-8"))
    bad["status"] = "running"
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(bad)
