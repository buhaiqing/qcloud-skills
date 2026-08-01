# Copyright (c) 2026. All rights reserved.
"""Goal inference — intent-to-goal mapping with multi-plan generation.

Per ADR-0005 §2.2. Converts fuzzy user queries into structured goals
with candidate skill chains. Always presents options to the user;
never auto-executes without confirmation.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SkillChain:
    """A candidate skill execution chain for a goal."""

    skills: list[str]  # ordered list of skill names
    description: str  # human-readable plan summary
    estimated_duration: str  # e.g. "约 2 分钟"
    risk: str  # "low" | "medium" | "high"
    reads_only: bool = True


@dataclass
class InferredGoal:
    """Structured goal inferred from a user query."""

    goal: str  # e.g. "diagnose_performance"
    description: str  # e.g. "诊断 CVM ins-xxx 的性能问题"
    confidence: float  # 0.0 - 1.0
    candidate_chains: list[SkillChain] = field(default_factory=list)
    risk_level: str = "low"  # "low" | "medium" | "high"
    clarifying_questions: list[str] = field(default_factory=list)


__all__ = ["InferredGoal", "SkillChain"]
