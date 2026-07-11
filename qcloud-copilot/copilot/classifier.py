from __future__ import annotations

import re
from copilot.models import ParsedRequest, ClassifiedIntent, IntentType

INTENT_PATTERNS: dict[IntentType, list[re.Pattern]] = {
    IntentType.DIAGNOSE: [
        re.compile(p)
        for p in [
            r"为什么|什么原因|根因|怎么回事|哪里出问题了",
            r"why|root.?cause|what.*happened",
            r"故障|异常|诊断|慢查询",
        ]
    ],
    IntentType.INSPECT: [
        re.compile(p)
        for p in [
            r"查看|检查|看看|显示|列出|有哪些|哪些|多少",
            r"list|show|find|get|describe|check|status",
            r"状态|详情|信息|配置",
        ]
    ],
    IntentType.CRUISE: [
        re.compile(p)
        for p in [
            r"巡检|巡航|全链路|健康.*检查|审计",
            r"cruise|health.?check|full.?link|inspect.*all",
        ]
    ],
    IntentType.ACT: [
        re.compile(p)
        for p in [
            r"重启|停止|启动|创建|删除|修改|调整|扩容|缩容|备份|恢复",
            r"restart|stop|start|create|delete|modify|update|scale|reboot",
        ]
    ],
    IntentType.COMPARE: [
        re.compile(p)
        for p in [
            r"对比|比较|相比|趋势|变化|vs|versus",
            r"compare|vs|versus|trend|change.*(week|month)",
        ]
    ],
    IntentType.REPORT: [
        re.compile(p)
        for p in [
            r"报告|汇总|月度|周报|日报|报表|统计|总结",
            r"report|summary|digest|weekly|monthly",
        ]
    ],
}

RESOURCE_TYPE_ALIASES: dict[str, str] = {
    "vm": "vm",
    "ecs": "vm",
    "instance": "vm",
    "ins": "vm",
    "服务器": "vm",
    "redis": "redis",
    "cache": "redis",
    "mysql": "mysql",
    "rds": "mysql",
    "数据库": "mysql",
    "k8s": "k8s",
    "kubernetes": "k8s",
    "集群": "k8s",
    "disk": "disk",
    "磁盘": "disk",
    "volume": "disk",
    "云盘": "disk",
    "eip": "eip",
    "ip": "eip",
    "clb": "clb",
    "loadbalancer": "clb",
    "oss": "oss",
    "bucket": "oss",
    "对象存储": "oss",
    "iam": "iam",
    "用户": "iam",
    "权限": "iam",
}


def classify(request: ParsedRequest) -> ClassifiedIntent:
    text = request.normalized
    scores: dict[IntentType, int] = {}

    for intent_type, patterns in INTENT_PATTERNS.items():
        score = 0
        for p in patterns:
            matches = p.findall(text)
            score += len(matches)
        if score > 0:
            scores[intent_type] = score

    if not scores:
        return ClassifiedIntent(
            primary=IntentType.UNKNOWN,
            targets=[],
            confidence=0.0,
        )

    primary = max(scores, key=scores.get)
    secondary = [k for k, v in sorted(scores.items(), key=lambda x: -x[1]) if k != primary]

    targets: list[str] = []
    if "resource_id" in request.entities:
        for rid in request.entities["resource_id"]:
            prefix = rid.split("-")[0].lower()
            if prefix in RESOURCE_TYPE_ALIASES:
                targets.append(RESOURCE_TYPE_ALIASES[prefix])

    for alias, canonical in RESOURCE_TYPE_ALIASES.items():
        if alias in text and canonical not in targets:
            targets.append(canonical)

    return ClassifiedIntent(
        primary=primary,
        secondary=secondary[:2],
        targets=sorted(set(targets)),
        confidence=request.confidence,
    )
