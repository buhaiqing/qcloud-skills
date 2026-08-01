# Copyright (c) 2026. All rights reserved.
"""Tests for goal_inference module."""

from __future__ import annotations

from phase2_ai_models.goal_inference import InferredGoal, SkillChain


class TestSkillChain:
    """SkillChain dataclass validation."""

    def test_default_reads_only(self) -> None:
        """Verify reads_only defaults to True."""
        chain = SkillChain(
            skills=["qcloud-cvm-ops"],
            description="test",
            estimated_duration="1m",
            risk="low",
        )
        assert chain.reads_only is True  # noqa: S101

    def test_destructive_chain(self) -> None:
        """Verify destructive chain with explicit reads_only=False."""
        chain = SkillChain(
            skills=["qcloud-cvm-ops"],
            description="test",
            estimated_duration="1m",
            risk="high",
            reads_only=False,
        )
        assert chain.risk == "high"  # noqa: S101
        assert chain.reads_only is False  # noqa: S101


class TestInferredGoal:
    """InferredGoal dataclass validation."""

    def test_minimal_goal(self) -> None:
        """Verify minimal InferredGoal with default list fields."""
        goal = InferredGoal(goal="test", description="test goal", confidence=0.5)
        assert goal.goal == "test"  # noqa: S101
        assert goal.confidence == 0.5  # noqa: S101, PLR2004
        assert goal.candidate_chains == []  # noqa: S101
        assert goal.risk_level == "low"  # noqa: S101
        assert goal.clarifying_questions == []  # noqa: S101

    def test_goal_with_chains(self) -> None:
        """Verify InferredGoal with multiple candidate chains."""
        chains = [
            SkillChain(
                skills=["qcloud-cvm-ops"],
                description="fast check",
                estimated_duration="30s",
                risk="low",
            ),
            SkillChain(
                skills=["qcloud-cvm-ops", "qcloud-monitor-ops"],
                description="deep analysis",
                estimated_duration="2m",
                risk="medium",
            ),
        ]
        goal = InferredGoal(
            goal="diagnose_performance",
            description="diagnose slow CVM",
            confidence=0.8,
            candidate_chains=chains,
            risk_level="medium",
            clarifying_questions=["Which instance is slow?"],
        )
        assert len(goal.candidate_chains) == 2  # noqa: S101, PLR2004
        assert goal.clarifying_questions == ["Which instance is slow?"]  # noqa: S101
        assert goal.risk_level == "medium"  # noqa: S101
