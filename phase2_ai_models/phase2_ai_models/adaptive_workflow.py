# Copyright (c) 2026. All rights reserved.
"""Adaptive workflow engine — dynamic plan revision and conditional branching.

Per ADR-0005 §2.1. Extends PlanDispatcher with:
  - Conditional step execution (Condition.expression evaluated at runtime)
  - Discovery steps that trigger plan_revision()
  - Max revision depth guard (default 3)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Condition:
    """Runtime-evaluated condition for dynamic branching.

    expression is a Jinja2 template rendered against Blackboard context:
        "{{output.diagnose.error_code}} == 'InvalidVpc.NotFound'"
    """

    expression: str
    true_branch: str  # step_id to execute when condition is true
    false_branch: str | None = None  # step_id when false (None = skip)


@dataclass
class PlanRevision:
    """Result of a plan revision triggered by a discovery step."""

    revision_id: int
    new_findings: dict[str, Any]
    added_steps: list[str]
    removed_steps: list[str]
    rationale: str


@dataclass
class AdaptiveConfig:
    """Configuration for adaptive workflow behavior."""

    max_revisions: int = 3
    max_branch_depth: int = 3
    discovery_enabled: bool = True


__all__ = ["AdaptiveConfig", "Condition", "PlanRevision"]
