from copilot.models import PlanStep
from copilot.quality.hallucination import check_h


def test_h_pass_for_valid_skill():
    step = PlanStep(
        id="step-1",
        type="skill_call",
        skill="qcloud-cvm-ops",
        params={"operation": "describe"},
        depends_on=[],
    )
    result = check_h(step)
    assert result["passed"] is True


def test_h_fail_for_unknown_skill():
    step = PlanStep(
        id="step-1",
        type="skill_call",
        skill="qcloud-nonexistent",
        params={"operation": "describe"},
        depends_on=[],
    )
    result = check_h(step)
    assert result["passed"] is False
    assert any("skill" in i.lower() for i in result["issues"])


def test_h_fail_for_unknown_operation():
    step = PlanStep(
        id="step-1",
        type="skill_call",
        skill="qcloud-cvm-ops",
        params={"operation": "nonexistent-op"},
        depends_on=[],
    )
    result = check_h(step)
    assert result["passed"] is False
    assert any("operation" in i.lower() for i in result["issues"])
