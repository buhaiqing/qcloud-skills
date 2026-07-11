from __future__ import annotations

import json
from pathlib import Path

import pytest

from copilot.plan_schema import (
    PlanValidationError,
    execution_plan_from_dict,
    load_plan_file,
    validate_execution_plan,
)

FIXTURE = Path(__file__).parent / "fixtures" / "plan-vpc-cruise-alert-report.json"


def test_fixture_loads_as_execution_plan():
    plan = load_plan_file(FIXTURE)
    assert plan.plan_id == "plan-fixture-001"
    assert len(plan.steps) == 4
    assert plan.steps[0].id == "vpc-0"
    assert plan.steps[1].writes_to_blackboard is True
    assert plan.dispatch_config["max_parallel_groups"] == 1


def test_depends_on_references_exist():
    plan = load_plan_file(FIXTURE)
    validate_execution_plan(plan)


def test_missing_dep_raises():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data["steps"].append(
        {
            "id": "orphan",
            "type": "report",
            "depends_on": ["missing-step"],
        }
    )
    plan = execution_plan_from_dict(data)
    with pytest.raises(PlanValidationError, match="missing step"):
        validate_execution_plan(plan)


def test_cycle_raises():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data["steps"].append(
        {
            "id": "cycle-a",
            "type": "report",
            "depends_on": ["cycle-b"],
        }
    )
    data["steps"].append(
        {
            "id": "cycle-b",
            "type": "report",
            "depends_on": ["cycle-a"],
        }
    )
    plan = execution_plan_from_dict(data)
    with pytest.raises(PlanValidationError, match="cycle"):
        validate_execution_plan(plan)
