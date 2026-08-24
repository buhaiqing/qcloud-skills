"""Tests for Phase 2.3 Cross-Skill Autonomous Orchestration."""
from __future__ import annotations

import pytest
from copilot.models import ClassifiedIntent, IntentType
from copilot.orchestration import (
    _PREDEFINED_PATTERNS,
    OrchestrationSelector,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def selector() -> OrchestrationSelector:
    return OrchestrationSelector(patterns=list(_PREDEFINED_PATTERNS))


def _diagnose_intent() -> ClassifiedIntent:
    return ClassifiedIntent(
        primary=IntentType.DIAGNOSE,
        secondary=[],
        targets=["cvm"],
        confidence=0.9,
    )


def _inspect_intent() -> ClassifiedIntent:
    return ClassifiedIntent(
        primary=IntentType.INSPECT,
        secondary=[],
        targets=["cvm"],
        confidence=0.9,
    )


def _unknown_intent() -> ClassifiedIntent:
    return ClassifiedIntent(
        primary=IntentType.UNKNOWN,
        secondary=[],
        targets=[],
        confidence=0.3,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_f1_triggered_by_finops_high_cpu(selector: OrchestrationSelector) -> None:
    """F1 fires when blackboard.finops.anomaly_level == 'HIGH' AND resource_cpu > 80."""
    blackboard_state = {
        "finops": {
            "anomaly_level": "HIGH",
            "resource_cpu": 85,
        },
        "inspection": {},
    }
    intent = _diagnose_intent()

    result = selector.select(blackboard_state, intent)

    assert result is not None
    assert result.name == "F1"
    assert result.skill_chain == ["qcloud-proactive-inspection", "qcloud-aiops-diagnosis"]
    assert result.fallback_pattern == "A1"


def test_p1_triggered_by_critical_security(selector: OrchestrationSelector) -> None:
    """P1 fires when inspection.severity == 'CRITICAL' AND category == 'security'."""
    blackboard_state = {
        "finops": {},
        "inspection": {
            "severity": "CRITICAL",
            "category": "security",
        },
    }
    intent = _inspect_intent()

    result = selector.select(blackboard_state, intent)

    assert result is not None
    assert result.name == "P1"
    assert result.skill_chain == ["qcloud-aiops-diagnosis"]
    assert result.fallback_pattern == "A2"


def test_no_match_returns_none(selector: OrchestrationSelector) -> None:
    """No pattern matches → select returns None (caller falls back to default)."""
    # finops anomaly_level is MEDIUM, not HIGH
    blackboard_state = {
        "finops": {
            "anomaly_level": "MEDIUM",
            "resource_cpu": 50,
        },
        "inspection": {
            "severity": "LOW",
            "category": "performance",
        },
    }
    intent = _unknown_intent()

    result = selector.select(blackboard_state, intent)

    assert result is None


def test_highest_specificity_wins(selector: OrchestrationSelector) -> None:
    """F1 (2 conditions) beats A1 (1 condition) when both match."""
    blackboard_state = {
        "finops": {
            "anomaly_level": "HIGH",
            "resource_cpu": 90,
        },
        "inspection": {},
    }
    # Intent is DIAGNOSE, so both F1 and A1 would match
    intent = _diagnose_intent()

    result = selector.select(blackboard_state, intent)

    assert result is not None
    # F1 has specificity=2, A1 has specificity=1 → F1 wins
    assert result.name == "F1"


def test_a1_triggered_by_diagnose_intent(selector: OrchestrationSelector) -> None:
    """A1 fires when intent.category == 'DIAGNOSE' with no blackboard state."""
    blackboard_state = {
        "finops": {},
        "inspection": {},
    }
    intent = _diagnose_intent()

    result = selector.select(blackboard_state, intent)

    assert result is not None
    assert result.name == "A1"
    assert result.skill_chain == ["qcloud-aiops-diagnosis"]


def test_fallback_on_pattern_failure(selector: OrchestrationSelector) -> None:
    """Pattern records its fallback_pattern for the caller to use on failure."""
    blackboard_state = {
        "finops": {
            "anomaly_level": "HIGH",
            "resource_cpu": 85,
        },
        "inspection": {},
    }
    intent = _diagnose_intent()

    result = selector.select(blackboard_state, intent)

    assert result is not None
    assert result.fallback_pattern == "A1"
    # P1 fallback is A2
    p1 = next(p for p in _PREDEFINED_PATTERNS if p.name == "P1")
    assert p1.fallback_pattern == "A2"
    # A1 has no fallback
    a1 = next(p for p in _PREDEFINED_PATTERNS if p.name == "A1")
    assert a1.fallback_pattern is None
