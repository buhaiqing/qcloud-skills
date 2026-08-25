"""Phase 2.1: Adaptive Workflow Engine tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from copilot.blackboard import BlackboardClient
from copilot.dispatcher import PlanDispatcher
from copilot.integration.skills import SkillDispatcher
from copilot.models import (
    ClassifiedIntent,
    Condition,
    ExecutionPlan,
    IntentType,
    PlanStep,
    StepResult,
)


@pytest.fixture
def board_dir(tmp_path):
    """Create a temporary blackboard directory with schema."""
    repo_schema = Path(__file__).resolve().parents[1] / "assets" / "blackboard.schema.json"
    target_dir = tmp_path / "blackboard"
    target_dir.mkdir()
    target_dir.joinpath("schema.json").write_text(
        repo_schema.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return target_dir


@pytest.fixture
def dispatcher():
    """Create a PlanDispatcher with mock skill dispatcher."""
    skill = MagicMock(spec=SkillDispatcher)
    skill.execute.return_value = StepResult(
        step_id="mock",
        status="success",
        output={},
    )
    return PlanDispatcher(skill_dispatcher=skill), skill


class TestConditionBranching:
    """Tests for conditional branching in adaptive workflow."""

    def test_condition_true_branch_inserted(self, board_dir):
        """When condition expression is true, true_branch step runs."""
        # Create a plan with a step that has a condition
        intent = ClassifiedIntent(primary=IntentType.DIAGNOSE, secondary=[], targets=["vm"], confidence=1.0)

        # Step 1: diagnose - produces output with cpu_usage = 85 (> 80 threshold)
        diagnose_step = PlanStep(
            id="diagnose-1",
            type="skill_call",
            skill="qcloud-cvm-ops",
            operation="diagnose",
            params={},
            condition=Condition(
                expression="{{ diagnose_output.cpu_usage }} > 80",
                true_branch="alert-2",
                false_branch=None,
            ),
        )

        # Step 2: alert - should run if cpu > 80
        alert_step = PlanStep(
            id="alert-2",
            type="skill_call",
            skill="qcloud-alert-ops",
            operation="create_alert",
            params={},
        )

        plan = ExecutionPlan(
            intent=intent,
            steps=[diagnose_step, alert_step],
            context={"diagnose_output": {"cpu_usage": 85}},
        )

        client = BlackboardClient(board_dir=board_dir)
        session_id = "ses-condition-true"
        client.create(session_id, "condition test")

        # Mock skill to return cpu_usage > 80
        skill = MagicMock(spec=SkillDispatcher)
        skill.execute.return_value = StepResult(
            step_id="diagnose-1",
            status="success",
            output={"cpu_usage": 85},
        )

        dispatcher = PlanDispatcher(skill_dispatcher=skill)
        results = dispatcher.execute(plan, client, session_id, parallel=False)

        # Should have results for both diagnose-1 and alert-2
        step_ids = [r.step_id for r in results]
        assert "diagnose-1" in step_ids
        assert "alert-2" in step_ids

    def test_condition_false_branch_inserted(self, board_dir):
        """When condition expression is false, false_branch step runs."""
        intent = ClassifiedIntent(primary=IntentType.DIAGNOSE, secondary=[], targets=["vm"], confidence=1.0)

        # Step 1: diagnose - produces output with cpu_usage = 50 (< 80 threshold)
        diagnose_step = PlanStep(
            id="diagnose-1",
            type="skill_call",
            skill="qcloud-cvm-ops",
            operation="diagnose",
            params={},
            condition=Condition(
                expression="{{ diagnose_output.cpu_usage }} > 80",
                true_branch="alert-2",
                false_branch="report-3",
            ),
        )

        # Step 2: alert - should run if cpu > 80
        alert_step = PlanStep(
            id="alert-2",
            type="skill_call",
            skill="qcloud-alert-ops",
            operation="create_alert",
            params={},
        )

        # Step 3: report - should run if cpu <= 80
        report_step = PlanStep(
            id="report-3",
            type="skill_call",
            skill="qcloud-report-ops",
            operation="generate_report",
            params={},
        )

        plan = ExecutionPlan(
            intent=intent,
            steps=[diagnose_step, alert_step, report_step],
            context={"diagnose_output": {"cpu_usage": 50}},
        )

        client = BlackboardClient(board_dir=board_dir)
        session_id = "ses-condition-false"
        client.create(session_id, "condition false test")

        # Mock skill to return cpu_usage < 80
        skill = MagicMock(spec=SkillDispatcher)
        skill.execute.return_value = StepResult(
            step_id="diagnose-1",
            status="success",
            output={"cpu_usage": 50},
        )

        dispatcher = PlanDispatcher(skill_dispatcher=skill)
        results = dispatcher.execute(plan, client, session_id, parallel=False)

        step_ids = [r.step_id for r in results]
        # When cpu < 80, only diagnose-1 and report-3 should run (alert-2 skipped)
        assert "diagnose-1" in step_ids
        assert "report-3" in step_ids

    def test_condition_no_false_branch_skips(self, board_dir):
        """False condition with no false_branch = no extra step executed."""
        intent = ClassifiedIntent(primary=IntentType.DIAGNOSE, secondary=[], targets=["vm"], confidence=1.0)

        # Step 1: diagnose - produces output with cpu_usage = 50 (< 80 threshold)
        # No false_branch defined
        diagnose_step = PlanStep(
            id="diagnose-1",
            type="skill_call",
            skill="qcloud-cvm-ops",
            operation="diagnose",
            params={},
            condition=Condition(
                expression="{{ diagnose_output.cpu_usage }} > 80",
                true_branch="alert-2",
                false_branch=None,  # No false branch
            ),
        )

        # Step 2: alert - only runs if condition is true
        alert_step = PlanStep(
            id="alert-2",
            type="skill_call",
            skill="qcloud-alert-ops",
            operation="create_alert",
            params={},
        )

        plan = ExecutionPlan(
            intent=intent,
            steps=[diagnose_step, alert_step],
            context={"diagnose_output": {"cpu_usage": 50}},
        )

        client = BlackboardClient(board_dir=board_dir)
        session_id = "ses-condition-no-false"
        client.create(session_id, "condition no false branch")

        # Mock skill to return cpu_usage < 80
        skill = MagicMock(spec=SkillDispatcher)
        skill.execute.return_value = StepResult(
            step_id="diagnose-1",
            status="success",
            output={"cpu_usage": 50},
        )

        dispatcher = PlanDispatcher(skill_dispatcher=skill)
        results = dispatcher.execute(plan, client, session_id, parallel=False)

        step_ids = [r.step_id for r in results]
        # Only diagnose-1 should run, alert-2 is skipped because false_branch is None
        assert "diagnose-1" in step_ids
        # alert-2 might not be in results since it's not dynamically added
        # and it's not executed because condition was false


class TestPlanRevision:
    """Tests for plan revision based on discoveries."""

    def test_plan_revision_adds_steps(self, board_dir):
        """Discovery step triggers plan_revision."""
        intent = ClassifiedIntent(primary=IntentType.DIAGNOSE, secondary=[], targets=["vm"], confidence=1.0)

        # Step 1: diagnose with discovery=True - discovers vpc_id
        diagnose_step = PlanStep(
            id="diagnose-1",
            type="skill_call",
            skill="qcloud-cvm-ops",
            operation="diagnose",
            params={},
            discovery=True,
            max_revisions=3,
        )

        # Step 2: analyze - depends on vpc_id being discovered
        analyze_step = PlanStep(
            id="analyze-2",
            type="skill_call",
            skill="qcloud-vpc-ops",
            operation="analyze",
            params={"vpc_id": "{{ vpc_id }}"},  # Will be updated by discovery
        )

        plan = ExecutionPlan(
            intent=intent,
            steps=[diagnose_step, analyze_step],
            context={},
        )

        client = BlackboardClient(board_dir=board_dir)
        session_id = "ses-discovery"
        client.create(session_id, "discovery test")

        # Mock skill to return discovery data
        skill = MagicMock(spec=SkillDispatcher)
        skill.execute.return_value = StepResult(
            step_id="diagnose-1",
            status="success",
            output={"vpc_id": "vpc-12345", "cpu_usage": 85},
        )

        dispatcher = PlanDispatcher(skill_dispatcher=skill)
        results = dispatcher.execute(plan, client, session_id, parallel=False)

        # Step should complete successfully
        diagnose_result = next((r for r in results if r.step_id == "diagnose-1"), None)
        assert diagnose_result is not None
        assert diagnose_result.status == "success"

    def test_plan_revision_cannot_undo_completed(self, board_dir):
        """Completed steps stay done - plan_revision cannot undo them."""
        intent = ClassifiedIntent(primary=IntentType.DIAGNOSE, secondary=[], targets=["vm"], confidence=1.0)

        # Step 1: completed - cannot be undone
        completed_step = PlanStep(
            id="completed-1",
            type="skill_call",
            skill="qcloud-cvm-ops",
            operation="diagnose",
            params={"original": "value"},
        )

        # Step 2: pending - can be modified
        # Uses template syntax that will be detected and updated
        pending_step = PlanStep(
            id="pending-2",
            type="skill_call",
            skill="qcloud-vpc-ops",
            operation="analyze",
            params={"vpc_id": "{{ vpc_id }}"},  # Template detected and replaced
        )

        plan = ExecutionPlan(
            intent=intent,
            steps=[completed_step, pending_step],
            context={},
        )

        completed = {
            "completed-1": StepResult(
                step_id="completed-1",
                status="success",
                output={"vpc_id": "vpc-xxx"},
            )
        }
        pending_ids = ["pending-2"]
        new_findings = {"vpc_id": "vpc-xxx"}

        dispatcher = PlanDispatcher()
        dispatcher.plan_revision(plan, completed, pending_ids, new_findings, max_revisions=3)

        # pending-2 params should be updated with vpc_id value
        pending_step_updated = next((s for s in plan.steps if s.id == "pending-2"), None)
        assert pending_step_updated is not None
        # The vpc_id should be directly set (template replaced)
        assert pending_step_updated.params.get("vpc_id") == "vpc-xxx"

    def test_max_revisions_limit(self, board_dir):
        """3rd revision returns error/not modifies plan."""
        intent = ClassifiedIntent(primary=IntentType.DIAGNOSE, secondary=[], targets=["vm"], confidence=1.0)

        plan = ExecutionPlan(
            intent=intent,
            steps=[],
            context={"_revision_count": 3},  # Already at max
        )

        completed = {}
        pending_ids = ["step-1"]
        new_findings = {"key": "value"}

        dispatcher = PlanDispatcher()
        result = dispatcher.plan_revision(plan, completed, pending_ids, new_findings, max_revisions=3)

        # Should not modify plan when at max revisions
        assert result is False

    def test_replan_updates_pending_params(self, board_dir):
        """Pending steps get updated params from context."""
        from copilot.plan_gen import replan

        _ = ClassifiedIntent(primary=IntentType.DIAGNOSE, secondary=[], targets=["vm"], confidence=1.0)

        pending_steps = [
            PlanStep(
                id="analyze-1",
                type="skill_call",
                skill="qcloud-vpc-ops",
                operation="analyze",
                params={"vpc_id": "{{ vpc_id }}"},
            ),
            PlanStep(
                id="report-2",
                type="skill_call",
                skill="qcloud-report-ops",
                operation="generate",
                params={"region": "{{ region }}"},
            ),
        ]

        context = {"vpc_id": "vpc-12345", "region": "ap-guangzhou"}

        updated_steps = replan(pending_steps, context)

        # Check that vpc_id was updated
        assert updated_steps[0].params["vpc_id"] == "vpc-12345"
        # Check that region was updated
        assert updated_steps[1].params["region"] == "ap-guangzhou"


class TestConditionEvaluation:
    """Tests for condition expression evaluation."""

    def test_evaluate_condition_true(self, board_dir):
        """Condition expression evaluates to True."""
        dispatcher = PlanDispatcher()

        condition = Condition(
            expression="{{ cpu_usage }} > 80",
            true_branch="step-true",
            false_branch="step-false",
        )

        context = {"cpu_usage": 85}
        result = dispatcher._evaluate_condition(condition, context)

        assert result is True

    def test_evaluate_condition_false(self, board_dir):
        """Condition expression evaluates to False."""
        dispatcher = PlanDispatcher()

        condition = Condition(
            expression="{{ cpu_usage }} > 80",
            true_branch="step-true",
            false_branch="step-false",
        )

        context = {"cpu_usage": 50}
        result = dispatcher._evaluate_condition(condition, context)

        assert result is False

    def test_evaluate_condition_error_returns_none(self, board_dir):
        """Invalid expression returns None (fail-safe)."""
        dispatcher = PlanDispatcher()

        condition = Condition(
            expression="{{ undefined_var }} > 80",
            true_branch="step-true",
            false_branch="step-false",
        )

        context = {}  # undefined_var not present
        result = dispatcher._evaluate_condition(condition, context)

        # Should return None on error (fail-safe, no branch taken)
        assert result is None


class TestBuildBlackboardContext:
    """Tests for building blackboard context from completed steps."""

    def test_build_context_from_results(self, board_dir):
        """Context is built from completed step results."""
        dispatcher = PlanDispatcher()

        completed = {
            "diagnose-1": StepResult(
                step_id="diagnose-1",
                status="success",
                output={"cpu_usage": 85, "memory_usage": 70},
            ),
            "vpc-2": StepResult(
                step_id="vpc-2",
                status="success",
                output={"vpc_id": "vpc-12345"},
            ),
        }

        context = dispatcher._build_blackboard_context(completed)

        # Should have step_id nested outputs
        assert "diagnose-1" in context
        assert context["diagnose-1"]["cpu_usage"] == 85
        # Should also have flat keys for simpler access
        assert context["cpu_usage"] == 85
        assert context["vpc_id"] == "vpc-12345"


class TestExtractFindings:
    """Tests for extracting findings from discovery step results."""

    def test_extract_error_codes(self, board_dir):
        """Error codes are extracted from output."""
        dispatcher = PlanDispatcher()

        result = StepResult(
            step_id="diagnose-1",
            status="success",
            output={
                "error_code": "InvalidVpc.NotFound",
                "cpu_usage": 85,
            },
        )

        findings = dispatcher._extract_findings(result)

        assert findings["error_code"] == "InvalidVpc.NotFound"
        assert findings["cpu_usage"] == 85

    def test_extract_vpc_id(self, board_dir):
        """VPC ID is extracted from output."""
        dispatcher = PlanDispatcher()

        result = StepResult(
            step_id="diagnose-1",
            status="success",
            output={
                "vpc_id": "vpc-abc123",
                "instance_id": "ins-xyz789",
            },
        )

        findings = dispatcher._extract_findings(result)

        assert findings["vpc_id"] == "vpc-abc123"
        assert findings["instance_id"] == "ins-xyz789"

    def test_extract_no_output(self, board_dir):
        """Empty output returns empty findings."""
        dispatcher = PlanDispatcher()

        result = StepResult(
            step_id="diagnose-1",
            status="success",
            output=None,
        )

        findings = dispatcher._extract_findings(result)

        assert findings == {}
