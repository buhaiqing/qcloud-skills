from __future__ import annotations

import re
from copilot.models import ParsedRequest
from copilot.context_manager import CUSTOMER_ALIASES

RESOURCE_ID_PATTERNS = re.compile(
    r"(?:ins|cdb|cdbro|redis|mongodb|postgres|"
    r"lb|clb|vpc|subnet|sg|nat|"
    r"disk|cbs|cos|scf|cls|"
    r"ssl|cdn|cam|tke|es|"
    r"apigw|ckafka)-[\w-]+",
    re.IGNORECASE,
)

REGION_PATTERNS = re.compile(
    r"\b(ap-(guangzhou|shanghai|beijing|nanjing|chengdu|chongqing|hongkong)|"
    r"广州|上海|北京|南京|成都)\b"
)

CUSTOMER_PATTERN = re.compile("(" + "|".join(re.escape(k) for k in CUSTOMER_ALIASES) + ")")

VAGUE_PATTERNS: list[re.Pattern] = [
    re.compile(p)
    for p in [
        r"最近.*怎么样",
        r"有没有问题",
        r"正常吗",
        r"怎么回事",
        r"帮我看一下",
        r"健康吗",
        r"汇总",
        r"报告|月度|趋势|报表|统计",
    ]
]


def parse(raw: str) -> ParsedRequest:
    stripped = raw.strip()
    if not stripped:
        return ParsedRequest(raw="", normalized="", confidence=0.0)

    normalized = stripped.lower().strip()

    entities: dict[str, list[str]] = {}
    resource_ids = RESOURCE_ID_PATTERNS.findall(stripped)
    if resource_ids:
        entities["resource_id"] = resource_ids

    regions = REGION_PATTERNS.findall(stripped)
    if regions:
        entities["region"] = [r[0] for r in regions]

    customer_match = CUSTOMER_PATTERN.search(stripped)
    if customer_match:
        entities["customer"] = [customer_match.group(1)]

    confidence = 1.0

    for vp in VAGUE_PATTERNS:
        if vp.search(normalized):
            confidence = min(confidence, 0.55)
            break

    if resource_ids:
        confidence = max(confidence, 0.85)
    if customer_match:
        confidence = max(confidence, 0.75)

    # Very short/noisy input penalty
    if len(stripped.split()) <= 2 and not resource_ids:
        confidence = min(confidence, 0.25)

    return ParsedRequest(
        raw=stripped,
        normalized=normalized,
        entities=entities,
        confidence=round(confidence, 2),
    )
