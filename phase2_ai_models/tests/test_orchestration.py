# Copyright (c) 2026. All rights reserved.
"""Tests for orchestration module."""

from __future__ import annotations

from phase2_ai_models.orchestration import PATTERNS, OrchestrationPattern, TriggerCondition


class TestTriggerCondition:
    """TriggerCondition validation."""

    def test_expression(self) -> None:
        """Verify TriggerCondition stores expression string."""
        tc = TriggerCondition(expression="blackboard.finops.anomaly_level == 'HIGH'")
        assert tc.expression == "blackboard.finops.anomaly_level == 'HIGH'"  # noqa: S101


class TestOrchestrationPattern:
    """OrchestrationPattern validation."""

    def test_pattern_defaults(self) -> None:
        """Verify default values for OrchestrationPattern."""
        pattern = OrchestrationPattern(name="TEST", description="test pattern")
        assert pattern.name == "TEST"  # noqa: S101
        assert pattern.trigger_conditions == []  # noqa: S101
        assert pattern.skill_chain == []  # noqa: S101
        assert pattern.handoff_schema is None  # noqa: S101
        assert pattern.fallback_pattern is None  # noqa: S101

    def test_pattern_with_conditions(self) -> None:
        """Verify OrchestrationPattern with triggers, chain, and fallback."""
        pattern = OrchestrationPattern(
            name="TEST",
            description="test",
            trigger_conditions=[TriggerCondition("x > 0"), TriggerCondition("y < 10")],
            skill_chain=["skill-a", "skill-b"],
            handoff_schema="schema.json",
            fallback_pattern="FALLBACK",
        )
        assert len(pattern.trigger_conditions) == 2  # noqa: S101, PLR2004
        assert pattern.skill_chain == ["skill-a", "skill-b"]  # noqa: S101


class TestCanonicalPatterns:
    """Verify all 5 canonical patterns are defined correctly."""

    def test_all_five_patterns_exist(self) -> None:
        """Verify PATTERNS dict contains exactly F1, F2, P1, A1, A2."""
        assert set(PATTERNS.keys()) == {"F1", "F2", "P1", "A1", "A2"}  # noqa: S101

    def test_f1_has_skill_chain(self) -> None:
        """Verify F1 pattern has 2-skill chain starting with proactive-inspection."""
        assert len(PATTERNS["F1"].skill_chain) == 2  # noqa: S101, PLR2004
        assert PATTERNS["F1"].skill_chain[0] == "qcloud-proactive-inspection"  # noqa: S101

    def test_f1_has_fallback(self) -> None:
        """Verify F1 pattern falls back to A1."""
        assert PATTERNS["F1"].fallback_pattern == "A1"  # noqa: S101

    def test_a1_has_no_trigger_conditions(self) -> None:
        """Verify A1 pattern has no trigger conditions."""
        assert PATTERNS["A1"].trigger_conditions == []  # noqa: S101

    def test_a1_has_no_fallback(self) -> None:
        """Verify A1 pattern has no fallback pattern."""
        assert PATTERNS["A1"].fallback_pattern is None  # noqa: S101
