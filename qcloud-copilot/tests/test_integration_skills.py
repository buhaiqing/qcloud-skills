from copilot.models import PlanStep
from copilot.integration.skills import SkillDispatcher


def test_unknown_skill_returns_failure():
    dispatcher = SkillDispatcher()
    step = PlanStep(
        id="test-1",
        type="skill_call",
        skill="qcloud-nonexistent",
        params={"operation": "describe"},
        depends_on=[],
    )
    result = dispatcher.execute(step, {})
    assert result.status == "failure"
    assert "unknown" in (result.error or "").lower()
