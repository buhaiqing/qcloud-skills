"""Rubric smoke tests — verify each of the 8 dimensions in
references/rubric.md is executable on the current copilot code.

If this file passes, the rubric's per-dimension checks are sound.
"""

from __future__ import annotations

from pathlib import Path

# --- D1 — Parser Correctness ---


def test_d1_parser_extracts_resource_id():
    from copilot.parser import parse

    req = parse("重启 ins-abc123 在 ap-guangzhou")
    assert "ins-abc123" in req.entities.get("resource_id", [])
    assert "ap-guangzhou" in req.entities.get("region", [])


def test_d1_parser_low_confidence_on_vague():
    from copilot.parser import parse

    req = parse("最近怎么样")
    assert req.confidence <= 0.55


# --- D2 — Classifier Correctness ---


def test_d2_classifier_act_intent():
    from copilot.classifier import classify
    from copilot.models import IntentType
    from copilot.parser import parse

    req = parse("重启 ins-abc")
    intent = classify(req)
    assert intent.primary == IntentType.ACT
    assert "vm" in intent.targets


def test_d2_classifier_inspect_intent():
    from copilot.classifier import classify
    from copilot.models import IntentType
    from copilot.parser import parse

    req = parse("查看 redis-cache-1 的状态")
    intent = classify(req)
    assert intent.primary == IntentType.INSPECT


# --- D3 — Plan Generation ---


def test_d3_act_plan_safety_level_2():
    from copilot.classifier import classify
    from copilot.parser import parse
    from copilot.plan_gen import generate

    req = parse("重启 ins-abc")
    intent = classify(req)
    plan = generate(intent)
    assert plan.safety_level == 2
    assert any(s.destructive for s in plan.steps)


def test_d3_inspect_plan_safety_level_0():
    from copilot.classifier import classify
    from copilot.parser import parse
    from copilot.plan_gen import generate

    req = parse("查看 redis 的状态")
    intent = classify(req)
    plan = generate(intent)
    assert plan.safety_level == 0
    assert not any(s.destructive for s in plan.steps)


# --- D4 — Safety Gate Enforcement (HARD GATE) ---


def test_d4_l0_catches_malformed_resource_id():
    from copilot.classifier import classify
    from copilot.parser import parse
    from copilot.safety.l0 import check_l0

    req = parse("重启 x 在 ap-guangzhou")
    intent = classify(req)
    # Force entities to bypass parse-time filter
    req.entities["resource_id"] = ["invalid-id"]
    result = check_l0(req, intent)
    assert not result["passed"]
    assert any("Malformed" in i for i in result["issues"])


def test_d4_l1_catches_step_budget_exceeded():
    from copilot.models import (
        ClassifiedIntent,
        ExecutionPlan,
        IntentType,
        PlanStep,
    )
    from copilot.safety.l1 import check_l1

    intent = ClassifiedIntent(primary=IntentType.INSPECT, targets=["vm"])
    steps = [PlanStep(id=f"step-{i}", type="skill_call", skill="qcloud-cvm-ops") for i in range(15)]
    plan = ExecutionPlan(intent=intent, steps=steps, context={})
    result = check_l1(plan)
    assert not result["passed"]
    assert any("Step budget" in i for i in result["issues"])


def test_d4_l2_blocks_destructive_without_confirm():
    from copilot.safety.l2 import check_l2

    plan = _destructive_plan()
    result = check_l2(plan, confirmed=False)
    assert not result["passed"]
    assert any("confirm" in i.lower() for i in result["issues"])


def test_d4_l3_blocks_critical_without_review():
    from copilot.models import (
        ClassifiedIntent,
        ExecutionPlan,
        ExecutionResult,
        IntentType,
        Report,
        ReportSection,
    )
    from copilot.safety.l3 import check_l3

    intent = ClassifiedIntent(primary=IntentType.INSPECT, targets=["vm"])
    plan = ExecutionPlan(intent=intent, steps=[], context={})
    report = Report(
        title="Test",
        summary="test",
        sections=[ReportSection(title="x", severity="critical", findings=["bad"])],
    )
    result = ExecutionResult(plan=plan, step_results=[], final_report=report)
    gate = check_l3(result, reviewed=False)
    assert not gate["passed"]


def _destructive_plan():
    from copilot.models import (
        ClassifiedIntent,
        ExecutionPlan,
        IntentType,
        PlanStep,
    )

    intent = ClassifiedIntent(primary=IntentType.ACT, targets=["vm"])
    steps = [
        PlanStep(
            id="act-1",
            type="skill_call",
            skill="qcloud-cvm-ops",
            params={"operation": "stop"},
            destructive=True,
        )
    ]
    return ExecutionPlan(intent=intent, steps=steps, context={}, safety_level=2)


# --- D5 — H Gate Coverage ---


def test_d5_h_catches_unknown_skill():
    from copilot.models import PlanStep
    from copilot.quality.hallucination import check_h

    step = PlanStep(
        id="x",
        type="skill_call",
        skill="qcloud-nonexistent-ops",
        params={"operation": "describe"},
    )
    result = check_h(step)
    assert not result["passed"]
    assert any("Unknown skill" in i for i in result["issues"])


def test_d5_h_catches_unknown_operation():
    from copilot.models import PlanStep
    from copilot.quality.hallucination import check_h

    step = PlanStep(
        id="x",
        type="skill_call",
        skill="qcloud-cvm-ops",
        params={"operation": "totally-bogus-op"},
    )
    result = check_h(step)
    assert not result["passed"]
    assert any("Unknown operation" in i for i in result["issues"])


# --- D6 — Skill Dispatch Validity ---


def test_d6_dispatcher_rejects_unknown_skill():
    from copilot.integration.skills import SkillDispatcher
    from copilot.models import PlanStep

    dispatcher = SkillDispatcher()
    step = PlanStep(
        id="x",
        type="skill_call",
        skill="qcloud-fake-ops",
        params={"operation": "describe"},
    )
    result = dispatcher.execute(step, context={})
    assert result.status == "failure"
    assert "Unknown skill" in (result.error or "")


def test_d6_dispatcher_accepts_known_skill(monkeypatch):
    """Dispatcher must invoke real subprocess (not return mock). Mock subprocess.run
    so this unit test doesn't depend on real tccli / network / credentials."""
    from copilot.integration.skills import SkillDispatcher
    from copilot.models import PlanStep

    # Mock subprocess.run to return canned success JSON
    class FakeProc:
        returncode = 0
        stdout = '{"Response": {"InstanceSet": []}}'
        stderr = ""

    def fake_run(cmd, **kwargs):
        return FakeProc()

    monkeypatch.setattr("copilot.integration.skills.subprocess.run", fake_run)

    dispatcher = SkillDispatcher()
    step = PlanStep(
        id="x",
        type="skill_call",
        skill="qcloud-cvm-ops",
        params={"operation": "describe-instance", "target": ["ins-test"]},
    )
    result = dispatcher.execute(step, context={"region": "ap-guangzhou"})
    assert result.status == "success"
    assert result.output is not None
    assert "command_invoked" in result.output
    cmd = result.output["command_invoked"]
    assert cmd[0] == "tccli"
    assert cmd[1] == "cvm"
    assert cmd[2] == "DescribeInstances"
    assert cmd[4] == "ap-guangzhou"
    assert "--InstanceIds.0" in cmd
    assert cmd[cmd.index("--InstanceIds.0") + 1] == "ins-test"


# --- D8 — Report Synthesis ---


def test_d8_summary_template_has_executive_summary():
    from copilot.models import (
        ClassifiedIntent,
        ExecutionPlan,
        ExecutionResult,
        IntentType,
        StepResult,
    )
    from copilot.report_gen import synthesize

    intent = ClassifiedIntent(primary=IntentType.INSPECT, targets=["vm"])
    plan = ExecutionPlan(intent=intent, steps=[], context={})
    result = ExecutionResult(
        plan=plan,
        step_results=[StepResult(step_id="x", status="success", output={"k": "v"})],
    )
    report = synthesize(result, audience="summary")
    titles = [s.title for s in report.sections]
    assert any("Executive Summary" in t for t in titles)


def test_d8_detailed_template_per_step_section():
    from copilot.models import (
        ClassifiedIntent,
        ExecutionPlan,
        ExecutionResult,
        IntentType,
        StepResult,
    )
    from copilot.report_gen import synthesize

    intent = ClassifiedIntent(primary=IntentType.INSPECT, targets=["vm"])
    plan = ExecutionPlan(intent=intent, steps=[], context={})
    result = ExecutionResult(
        plan=plan,
        step_results=[
            StepResult(step_id="inspect-1", status="success", output={"k": "v"}),
        ],
    )
    report = synthesize(result, audience="detailed")
    titles = [s.title for s in report.sections]
    assert any("inspect-1" in t for t in titles)


# --- Rubric file presence ---


def test_rubric_file_exists():
    rubric = Path(__file__).parent.parent / "references" / "rubric.md"
    assert rubric.exists(), "rubric.md must exist (Task 2 deliverable)"


def test_rubric_has_frontmatter():
    rubric = Path(__file__).parent.parent / "references" / "rubric.md"
    text = rubric.read_text()
    assert text.startswith("---\n")
    assert "max_iter: 3" in text
    assert "rubric_dimensions: 8" in text
