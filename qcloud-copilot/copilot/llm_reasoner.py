"""CI-mode inspection strategy via external LLM (mockable for tests)."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests

from copilot.topology_reasoner import reason_inspection_strategy

_DEFAULT_OPENAI_BASE = "https://api.openai.com/v1"
_CHAT_COMPLETIONS_SUFFIX = "/chat/completions"
_STRATEGY_SYSTEM_PROMPT = (
    "你是腾讯云 AIOps 巡检策略生成器。根据拓扑与用户意图，"
    "仅输出一个 JSON 对象（不要 markdown 代码块），必须包含 "
    "selected_analyzers（字符串数组）和 skipped_analyzers（对象数组，含 service/reason）。"
    '可选字段：agent_rationale、analysis_depth（必须是对象，如 {"vm":"deep","clb":"normal"}）、early_stop。'
)


@dataclass(frozen=True)
class LlmConfig:
    base_url: str
    model: str
    api_key: str

    @property
    def chat_completions_url(self) -> str:
        return resolve_chat_completions_url(self.base_url)


def resolve_chat_completions_url(base_url: str) -> str:
    """Normalize OpenAI-compatible base URL → chat/completions endpoint."""
    raw = (base_url or _DEFAULT_OPENAI_BASE).strip().rstrip("/")
    if not raw:
        raw = _DEFAULT_OPENAI_BASE
    if raw.endswith(_CHAT_COMPLETIONS_SUFFIX):
        return raw
    # Accept host-only mistakes: prepend https if scheme missing
    if not urlparse(raw).scheme:
        raw = f"https://{raw}"
    return f"{raw}{_CHAT_COMPLETIONS_SUFFIX}"


def load_llm_config_from_env() -> LlmConfig | None:
    api_key = (os.environ.get("COPILOT_LLM_API_KEY") or "").strip()
    if not api_key:
        return None
    base_url = (os.environ.get("COPILOT_LLM_BASE_URL") or _DEFAULT_OPENAI_BASE).strip()
    model = (os.environ.get("COPILOT_LLM_MODEL") or "gpt-4o-mini").strip()
    return LlmConfig(base_url=base_url, model=model, api_key=api_key)


def load_llm_timeout_seconds() -> int:
    """HTTP read timeout for CI-mode LLM API calls (seconds)."""
    raw = (os.environ.get("COPILOT_LLM_TIMEOUT") or "300").strip()
    try:
        return max(10, int(raw))
    except ValueError:
        return 300


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("LLM response is not a JSON object")


def _openai_compatible_chat(prompt: str, config: LlmConfig, *, timeout: int | None = None) -> str:
    if timeout is None:
        timeout = load_llm_timeout_seconds()
    url = config.chat_completions_url
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": _STRATEGY_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        msg = "LLM response content is not a string"
        raise TypeError(msg)
    return content


_LayerAnalyzers: dict[str, list[str]] = {
    "公网入口": ["eip", "clb"],
    "数据层": ["redis", "rds_mysql"],
    "应用层": ["vm"],
    "出口层": ["eip"],
    "网络基础": [],
}

_AnalyzerRawKeys: dict[str, str | None] = {
    "vm": "vms",
    "clb": "lbs",
    "eip": "eips",
    "redis": "redis",
    "rds_mysql": "rds",
}


def _topology_count(raw: dict[str, Any], analyzer: str) -> int:
    key = _AnalyzerRawKeys.get(analyzer)
    if key is None:
        return 0
    return len(raw.get(key) or [])


def _select_analyzers_from_chain(
    priority_chain: list[dict[str, Any]], raw: dict[str, Any]
) -> tuple[list[str], list[dict[str, str]]]:
    selected: list[str] = []
    seen: set[str] = set()
    for item in priority_chain:
        if str(item.get("analysis_depth", "")).lower() == "skip":
            continue
        layer = str(item.get("layer", ""))
        for analyzer in _LayerAnalyzers.get(layer, []):
            if analyzer in seen:
                continue
            if _topology_count(raw, analyzer) > 0:
                seen.add(analyzer)
                selected.append(analyzer)

    skipped: list[dict[str, str]] = []
    for analyzer, key in _AnalyzerRawKeys.items():
        if (
            key
            and _topology_count(raw, analyzer) == 0
            and analyzer
            in {
                "redis",
                "rds_mysql",
                "clb",
                "vm",
                "eip",
            }
        ):
            skipped.append({"service": analyzer, "reason": "topology_count=0"})

    return selected, skipped


def _enhance_topology_strategy(
    base: dict[str, Any],
    *,
    decision_maker: str,
    execution_path: str,
    rationale: str,
    sniff_data: dict[str, Any] | None = None,
    mode_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Upgrade topology_reasoner output to schema 1.2 with selective analyzers."""
    priority_chain = base.get("priority_chain") or []
    raw = (sniff_data or {}).get("raw") or {}
    if not raw:
        topo_summary = base.get("topology_summary") or {}
        raw = {
            "vms": [{}] * int(topo_summary.get("vms", 0)),
            "lbs": [{}] * int(topo_summary.get("lbs", 0)),
            "eips": [{}] * int(topo_summary.get("eips", 0)),
            "rds": [{}] * int(topo_summary.get("rds", 0)),
            "redis": [{}] * int(topo_summary.get("redis", 0)),
        }
    selected, skipped = _select_analyzers_from_chain(priority_chain, raw)

    strategy = dict(base)
    strategy.update(
        {
            "strategy_schema": "1.2",
            "decision_maker": decision_maker,
            "execution_path": execution_path,
            "llm_native_target": True,
            "agent_rationale": rationale[:2000],
            "selected_analyzers": selected,
            "skipped_analyzers": skipped,
            "early_stop": False,
        }
    )
    if mode_meta:
        strategy["inspection_mode_meta"] = mode_meta
    return strategy


def _default_analysis_depth(
    selected: list[str], priority_chain: list[dict[str, Any]]
) -> dict[str, str]:
    depth_by_analyzer: dict[str, str] = {}
    for item in priority_chain:
        layer = str(item.get("layer", ""))
        depth = str(item.get("analysis_depth", "normal"))
        if depth not in ("deep", "normal", "quick", "skip"):
            depth = "normal"
        for analyzer in _LayerAnalyzers.get(layer, []):
            if analyzer in selected:
                depth_by_analyzer.setdefault(analyzer, depth)
    for analyzer in selected:
        depth_by_analyzer.setdefault(analyzer, "normal")
    return depth_by_analyzer


def _normalize_llm_strategy(
    strategy: dict[str, Any],
    *,
    selected: list[str],
    skipped: list[dict[str, str]],
    priority_chain: list[dict[str, Any]],
) -> dict[str, Any]:
    """Coerce LLM JSON to schema 1.2 (models often return analysis_depth as string)."""
    out = dict(strategy)
    depth = out.get("analysis_depth")
    if isinstance(depth, str) and depth in ("deep", "normal", "quick", "skip"):
        analyzers = list(out.get("selected_analyzers") or selected)
        out["analysis_depth"] = dict.fromkeys(analyzers, depth)
    elif not isinstance(depth, dict):
        out["analysis_depth"] = _default_analysis_depth(
            list(out.get("selected_analyzers") or selected), priority_chain
        )

    if not out.get("selected_analyzers"):
        out["selected_analyzers"] = selected
    if not out.get("skipped_analyzers"):
        out["skipped_analyzers"] = skipped
    out.setdefault("early_stop", False)
    out.setdefault("mode", "topology_first")
    return out


def _default_llm_call(prompt: str) -> str:
    config = load_llm_config_from_env()
    if config is None:
        msg = "COPILOT_LLM_API_KEY not configured"
        raise RuntimeError(msg)
    return _openai_compatible_chat(prompt, config)


def reason_inspection_strategy_llm(
    *,
    customer: str,
    region: str,
    user_request: str,
    sniff_data: dict[str, Any] | None,
    mode_meta: dict[str, Any] | None = None,
    llm_call: Callable[[str], str] | None = None,
    force_topology_fallback: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    """Produce schema 1.2 strategy for CI path. Returns (strategy, warnings)."""
    warnings: list[str] = []
    base = reason_inspection_strategy(
        customer=customer,
        region=region,
        user_request=user_request,
        sniff_data=sniff_data,
    )
    raw = (sniff_data or {}).get("raw") or {}
    priority_chain = base.get("priority_chain") or []
    selected, skipped = _select_analyzers_from_chain(priority_chain, raw)

    if force_topology_fallback:
        strategy = _enhance_topology_strategy(
            base,
            decision_maker="topology_reasoner_v1",
            execution_path="topology_first_then_analyzer",
            rationale="CI 模式降级：LLM 门禁未开启或调用失败，使用拓扑启发式选择性 analyzer。",
            sniff_data=sniff_data,
            mode_meta=mode_meta,
        )
        return strategy, warnings

    prompt = json.dumps(
        {
            "task": "inspection_strategy",
            "customer": customer,
            "region": region,
            "user_request": user_request[:500],
            "topology_summary": base.get("topology_summary"),
            "priority_chain": priority_chain,
            "hint_selected_analyzers": selected,
            "hint_skipped_analyzers": skipped,
        },
        ensure_ascii=False,
    )

    caller = llm_call
    if caller is None and load_llm_config_from_env() is not None:
        caller = _default_llm_call

    if caller is None:
        warnings.append("llm_reasoner_no_api: using topology-enhanced fallback")
        strategy = _enhance_topology_strategy(
            base,
            decision_maker="topology_reasoner_v1",
            execution_path="topology_first_then_analyzer",
            rationale="CI 路径无 LLM 凭据；拓扑启发式生成 selective analyzers。",
            sniff_data=sniff_data,
            mode_meta=mode_meta,
        )
        return strategy, warnings

    try:
        raw_response = caller(prompt)
        parsed = _extract_json_object(raw_response)
        if parsed.get("selected_analyzers"):
            strategy = _normalize_llm_strategy(
                parsed,
                selected=selected,
                skipped=skipped,
                priority_chain=priority_chain,
            )
        else:
            raise ValueError("LLM response missing selected_analyzers")
        strategy.setdefault("strategy_schema", "1.2")
        strategy.setdefault("decision_maker", "llm_reasoner_v1")
        strategy.setdefault("execution_path", "llm_api_selective")
        strategy.setdefault("llm_native_target", True)
        llm_cfg = load_llm_config_from_env()
        if llm_cfg:
            strategy.setdefault("llm_model", llm_cfg.model)
            strategy.setdefault("llm_base_url", llm_cfg.base_url)
        strategy.setdefault("customer", customer)
        strategy.setdefault("region", region)
        strategy.setdefault("user_request", user_request[:500])
        strategy.setdefault("topology_summary", base.get("topology_summary"))
        strategy.setdefault("priority_chain", priority_chain)
        strategy.setdefault(
            "agent_rationale",
            strategy.get("agent_rationale")
            or "CI 模式：外部 LLM 根据拓扑与用户意图生成 selective analyzer 策略。",
        )
        if mode_meta:
            strategy["inspection_mode_meta"] = mode_meta
        from copilot.strategy import validate_strategy

        validate_strategy(strategy)
        return strategy, warnings
    except Exception as exc:
        warnings.append(f"llm_reasoner_failed: {exc}")
        strategy = _enhance_topology_strategy(
            base,
            decision_maker="topology_reasoner_v1",
            execution_path="topology_first_then_analyzer",
            rationale=f"CI LLM 调用失败，降级拓扑启发式：{exc}",
            sniff_data=sniff_data,
            mode_meta=mode_meta,
        )
        return strategy, warnings
