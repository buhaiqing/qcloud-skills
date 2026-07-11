"""LC-5 mode resolver tests."""

from __future__ import annotations

import pytest

from copilot.mode_resolver import (
    resolve_inspection_mode,
    strip_ci_trigger_words,
)


def test_default_delivery_mode() -> None:
    result = resolve_inspection_mode("朔州天源 VPC 风险巡检和告警汇总报告")
    assert result.mode == "delivery"
    assert result.effective == "delivery"
    assert result.decision_maker == "agent_session_v1"
    assert result.trigger == "default"
    assert result.matched_keyword is None


def test_keyword_triggers_ci_when_llm_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COPILOT_LLM_REASONING", "1")
    result = resolve_inspection_mode("[CI模式] 丹东鹏飞 无人值守 定时巡检")
    assert result.mode == "ci"
    assert result.effective == "ci"
    assert result.decision_maker == "llm_reasoner_v1"
    assert result.trigger == "keyword"
    assert result.matched_keyword == "ci模式"


def test_keyword_degrades_when_llm_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COPILOT_LLM_REASONING", raising=False)
    result = resolve_inspection_mode("朔州天源 无人值守 定时巡检")
    assert result.mode == "ci"
    assert result.effective == "fallback"
    assert result.decision_maker == "topology_reasoner_v1"
    assert result.warnings


def test_cli_forces_delivery_ignoring_keyword(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COPILOT_LLM_REASONING", "1")
    result = resolve_inspection_mode(
        "[CI模式] 朔州天源 VPC 风险巡检",
        cli_mode="delivery",
    )
    assert result.mode == "delivery"
    assert result.effective == "delivery"
    assert result.trigger == "cli"


def test_cli_forces_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COPILOT_LLM_REASONING", "1")
    result = resolve_inspection_mode("朔州天源 VPC 风险巡检", cli_mode="ci")
    assert result.mode == "ci"
    assert result.effective == "ci"
    assert result.trigger == "cli"


def test_env_delivery_overrides_keyword(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COPILOT_INSPECTION_MODE", "delivery")
    monkeypatch.setenv("COPILOT_LLM_REASONING", "1")
    result = resolve_inspection_mode("无人值守 定时巡检")
    assert result.mode == "delivery"
    assert result.trigger == "env"


def test_strip_ci_trigger_words() -> None:
    cleaned = strip_ci_trigger_words("[CI模式] 朔州天源 VPC 风险巡检", "ci模式")
    assert "ci模式" not in cleaned.lower()
    assert "朔州天源" in cleaned


# ── CI strict gate: COPILOT_CUSTOMER_TAG_KEY unset (P0 follow-up) ────


def test_ci_gate_warns_when_customer_tag_key_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """CI mode + unset COPILOT_CUSTOMER_TAG_KEY → soft warning, no block."""
    monkeypatch.setenv("COPILOT_LLM_REASONING", "1")
    monkeypatch.delenv("COPILOT_CUSTOMER_TAG_KEY", raising=False)
    result = resolve_inspection_mode("[CI模式] 朔州天源 无人值守", cli_mode="ci")
    assert result.effective == "ci"
    assert any("ci_strict_gate" in w for w in result.warnings), (
        f"expected ci_strict_gate warning, got: {result.warnings}"
    )


def test_ci_gate_no_warning_when_customer_tag_key_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CI mode + COPILOT_CUSTOMER_TAG_KEY set → no ci_strict_gate warning."""
    monkeypatch.setenv("COPILOT_LLM_REASONING", "1")
    monkeypatch.setenv("COPILOT_CUSTOMER_TAG_KEY", "customer")
    result = resolve_inspection_mode("[CI模式] 朔州天源 无人值守", cli_mode="ci")
    assert result.effective == "ci"
    assert not any("ci_strict_gate" in w for w in result.warnings)


def test_delivery_mode_no_ci_gate_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    """Delivery mode never emits ci_strict_gate, regardless of env."""
    monkeypatch.delenv("COPILOT_CUSTOMER_TAG_KEY", raising=False)
    result = resolve_inspection_mode("朔州天源 VPC 风险巡检")
    assert result.effective == "delivery"
    assert not any("ci_strict_gate" in w for w in result.warnings)
