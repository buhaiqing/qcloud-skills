# Copyright (c) 2026. All rights reserved.
"""Tests for adaptive_workflow module."""

from __future__ import annotations

from phase2_ai_models.adaptive_workflow import AdaptiveConfig, Condition


class TestCondition:
    """Condition dataclass validation."""

    def test_condition_required_fields(self) -> None:
        """Verify required fields are set and false_branch defaults to None."""
        c = Condition(expression="{{output.x}} > 0", true_branch="step_a")
        assert c.expression == "{{output.x}} > 0"  # noqa: S101
        assert c.true_branch == "step_a"  # noqa: S101
        assert c.false_branch is None  # noqa: S101

    def test_condition_with_false_branch(self) -> None:
        """Verify false_branch is stored when provided."""
        c = Condition(expression="{{output.x}} > 0", true_branch="step_a", false_branch="step_b")
        assert c.false_branch == "step_b"  # noqa: S101


class TestAdaptiveConfig:
    """AdaptiveConfig defaults and validation."""

    def test_defaults(self) -> None:
        """Verify default values for AdaptiveConfig."""
        cfg = AdaptiveConfig()
        assert cfg.max_revisions == 3  # noqa: S101, PLR2004
        assert cfg.max_branch_depth == 3  # noqa: S101, PLR2004
        assert cfg.discovery_enabled is True  # noqa: S101

    def test_custom_values(self) -> None:
        """Verify custom values override defaults."""
        cfg = AdaptiveConfig(max_revisions=5, max_branch_depth=2, discovery_enabled=False)
        assert cfg.max_revisions == 5  # noqa: S101, PLR2004
        assert cfg.max_branch_depth == 2  # noqa: S101, PLR2004
        assert cfg.discovery_enabled is False  # noqa: S101
