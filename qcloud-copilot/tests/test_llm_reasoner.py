"""LC-5 llm_reasoner tests (mock LLM, no API key)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from copilot.llm_reasoner import (
    _extract_json_object,
    _openai_compatible_chat,
    load_llm_config_from_env,
    load_llm_timeout_seconds,
    reason_inspection_strategy_llm,
    resolve_chat_completions_url,
)
from copilot.strategy import validate_strategy


@pytest.fixture
def sniff_shuozhou() -> dict:
    return {
        "customer": "朔州天源",
        "raw": {
            "vms": [{"instanceId": "i-1"}, {"instanceId": "i-2"}],
            "lbs": [{"loadBalancerId": "lb-1"}],
            "eips": [{"elasticIpId": "eip-1"}],
            "rds": [{"instanceId": "rds-1"}],
            "redis": [],
        },
        "topology": {"vpcs": [{"vpcId": "vpc-1"}]},
    }


def test_topology_fallback_without_api(sniff_shuozhou: dict) -> None:
    strategy, warnings = reason_inspection_strategy_llm(
        customer="朔州天源",
        region="ap-guangzhou",
        user_request="[CI模式] 朔州天源 VPC 风险巡检",
        sniff_data=sniff_shuozhou,
        force_topology_fallback=True,
    )
    assert strategy["decision_maker"] == "topology_reasoner_v1"
    assert strategy["strategy_schema"] == "1.2"
    assert "redis" in {s["service"] for s in strategy["skipped_analyzers"]}
    assert "rds_mysql" in strategy["selected_analyzers"]
    assert strategy["skipped_analyzers"]


def test_mock_llm_returns_selective_strategy(sniff_shuozhou: dict) -> None:
    def mock_llm(_prompt: str) -> str:
        return json.dumps(
            {
                "strategy_schema": "1.2",
                "decision_maker": "llm_reasoner_v1",
                "execution_path": "llm_api_selective",
                "selected_analyzers": ["eip", "clb", "vm"],
                "skipped_analyzers": [{"service": "redis", "reason": "topology_count=0"}],
                "agent_rationale": "mock LLM: 公网入口优先",
            }
        )

    strategy, warnings = reason_inspection_strategy_llm(
        customer="朔州天源",
        region="ap-guangzhou",
        user_request="CI模式 朔州天源",
        sniff_data=sniff_shuozhou,
        llm_call=mock_llm,
    )
    assert not warnings
    assert strategy["decision_maker"] == "llm_reasoner_v1"
    assert strategy["selected_analyzers"] == ["eip", "clb", "vm"]
    validate_strategy(strategy)


def test_normalize_string_analysis_depth() -> None:
    from copilot.llm_reasoner import _normalize_llm_strategy

    normalized = _normalize_llm_strategy(
        {"selected_analyzers": ["vm", "clb"], "analysis_depth": "deep"},
        selected=["vm", "clb"],
        skipped=[],
        priority_chain=[],
    )
    assert normalized["analysis_depth"] == {"vm": "deep", "clb": "deep"}
    validate_strategy(
        {
            **normalized,
            "strategy_schema": "1.2",
            "decision_maker": "llm_reasoner_v1",
            "execution_path": "llm_api_selective",
            "customer": "x",
            "region": "ap-guangzhou",
            "user_request": "test",
            "topology_summary": {"vms": 1},
            "priority_chain": [
                {
                    "layer": "应用层",
                    "resource_count": 1,
                    "analysis_depth": "deep",
                    "rationale": "r",
                }
            ],
            "agent_rationale": "ok",
            "llm_native_target": True,
            "early_stop": False,
            "skipped_analyzers": [],
        }
    )


def test_mock_llm_failure_degrades(sniff_shuozhou: dict) -> None:
    def bad_llm(_prompt: str) -> str:
        raise RuntimeError("api down")

    strategy, warnings = reason_inspection_strategy_llm(
        customer="朔州天源",
        region="ap-guangzhou",
        user_request="无人值守",
        sniff_data=sniff_shuozhou,
        llm_call=bad_llm,
    )
    assert strategy["decision_maker"] == "topology_reasoner_v1"
    assert any("llm_reasoner_failed" in w for w in warnings)


@pytest.mark.parametrize(
    "base,expected",
    [
        ("https://api.openai.com/v1", "https://api.openai.com/v1/chat/completions"),
        (
            "https://dashscope.aliyuncs.com/compatible-mode/v1/",
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        ),
        (
            "https://api.deepseek.com/v1/chat/completions",
            "https://api.deepseek.com/v1/chat/completions",
        ),
    ],
)
def test_resolve_chat_completions_url(base: str, expected: str) -> None:
    assert resolve_chat_completions_url(base) == expected


def test_load_llm_timeout_seconds_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COPILOT_LLM_TIMEOUT", raising=False)
    assert load_llm_timeout_seconds() == 300


def test_load_llm_timeout_seconds_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COPILOT_LLM_TIMEOUT", "180")
    assert load_llm_timeout_seconds() == 180


def test_load_llm_timeout_seconds_invalid_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COPILOT_LLM_TIMEOUT", "not-a-number")
    assert load_llm_timeout_seconds() == 300


def test_load_llm_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COPILOT_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("COPILOT_LLM_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("COPILOT_LLM_MODEL", "deepseek-chat")
    cfg = load_llm_config_from_env()
    assert cfg is not None
    assert cfg.base_url == "https://api.deepseek.com/v1"
    assert cfg.model == "deepseek-chat"
    assert cfg.chat_completions_url.endswith("/chat/completions")


def test_extract_json_object_strips_markdown_fence() -> None:
    raw = '```json\n{"selected_analyzers": ["vm"]}\n```'
    parsed = _extract_json_object(raw)
    assert parsed["selected_analyzers"] == ["vm"]


@patch("copilot.llm_reasoner.requests.post")
def test_openai_compatible_chat_uses_base_url(mock_post: MagicMock) -> None:
    from copilot.llm_reasoner import LlmConfig

    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"choices": [{"message": {"content": '{"selected_analyzers":["vm"]}'}}]},
    )
    mock_post.return_value.raise_for_status = MagicMock()

    cfg = LlmConfig(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen-plus",
        api_key="sk-x",
    )
    content = _openai_compatible_chat('{"task":"x"}', cfg, timeout=30)
    assert "vm" in content
    called_url = mock_post.call_args[0][0]
    assert called_url == "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    assert mock_post.call_args[1]["json"]["model"] == "qwen-plus"
    assert mock_post.call_args[1]["timeout"] == 30
