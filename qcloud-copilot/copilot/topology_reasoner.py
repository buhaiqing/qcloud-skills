"""Topology-driven inspection strategy (LLM-native ready).

Current implementation uses deterministic topology heuristics aligned with
qcloud-proactive-inspection SKILL v3 Topology-first rules. The same structure is
designed for LLM replacement: pass topology JSON + user intent → priority chain.

ponytail: heuristic_v1 — upgrade path is swap `decision_maker` to llm_reasoner
without changing Blackboard evidence_chain schema.
"""

from __future__ import annotations

from typing import Any

_LAYER_PRIORITY = [
    ("公网入口", ("eips", "lbs"), "deep", "所有公网流量必经；优先检查带宽与健康"),
    ("数据层", ("rds", "redis", "mongodb", "es"), "deep", "数据一致性/单点风险最高"),
    ("应用层", ("vms",), "normal", "承压上游流量，关注 CPU/磁盘/到期"),
    ("出口层", ("eips",), "normal", "NAT/EIP 出网与绑定关系"),
    ("网络基础", ("vpcs",), "quick", "VPC/子网拓扑上下文"),
]


def _count_by_raw(raw: dict[str, Any]) -> dict[str, int]:
    return {
        key: len(raw.get(key) or [])
        for key in ("vms", "lbs", "redis", "rds", "mongodb", "eips", "es", "vpcs")
    }


def _sample_ids(raw: dict[str, Any], key: str, id_field: str, limit: int = 5) -> list[str]:
    ids: list[str] = []
    for item in raw.get(key) or []:
        rid = item.get(id_field) or item.get("instanceId") or item.get("elasticIpId")
        if rid:
            ids.append(str(rid))
        if len(ids) >= limit:
            break
    return ids


def reason_inspection_strategy(
    *,
    customer: str,
    region: str,
    user_request: str,
    sniff_data: dict[str, Any] | None,
    resource_coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Produce customer-specific inspection strategy from live topology."""
    raw = (sniff_data or {}).get("raw") or {}
    counts = _count_by_raw(raw)
    vpc_n = len((sniff_data or {}).get("topology", {}).get("vpcs") or {}) or counts.get("vpcs", 0)

    priority_chain: list[dict[str, Any]] = []
    for layer, raw_keys, depth, rationale in _LAYER_PRIORITY:
        layer_count = sum(counts.get(k, 0) for k in raw_keys)
        if layer_count <= 0:
            continue
        samples: list[str] = []
        if "eips" in raw_keys:
            samples.extend(_sample_ids(raw, "eips", "elasticIpId"))
        if "lbs" in raw_keys:
            samples.extend(_sample_ids(raw, "lbs", "loadBalancerId"))
        if "vms" in raw_keys:
            samples.extend(_sample_ids(raw, "vms", "instanceId"))
        if "rds" in raw_keys:
            samples.extend(_sample_ids(raw, "rds", "instanceId"))
        if "redis" in raw_keys:
            samples.extend(_sample_ids(raw, "redis", "cacheInstanceId"))
        priority_chain.append(
            {
                "layer": layer,
                "resource_count": layer_count,
                "analysis_depth": depth,
                "rationale": rationale,
                "sample_resource_ids": samples[:6],
            }
        )

    analyzed = (resource_coverage or {}).get("total_analyzed_resources", 0)
    execution_path = "script_analyzer_fallback"
    if sniff_data:
        execution_path = "topology_first_then_analyzer"
    # LLM-native: when COPILOT_LLM_REASONING is wired, decision_maker becomes llm_reasoner_v1
    return {
        "mode": "topology_first",
        "execution_path": execution_path,
        "strategy_schema": "1.1",
        "customer": customer,
        "region": region,
        "user_request": user_request[:500],
        "topology_summary": {**counts, "vpcs": vpc_n},
        "priority_chain": priority_chain,
        "decision_maker": "topology_reasoner_v1",
        "llm_native_target": True,
        "llm_native_note": (
            "当前 analyzer 为脚本 fallback；策略优先级由拓扑推理动态生成。"
            "生产路径应由 LLM 读取本 strategy + 拓扑 JSON 自主决定深挖方向，"
            "而非固定跑完全部 analyzer。"
        ),
        "resources_analyzed": analyzed,
    }
