"""P0-1 统一 AIOps 事件信封（AIOpsEnvelope）包装器。

设计见 docs/superpowers/specs/aiops-envelope-design.md。信封是**包装层**：
原始事件被打包为 {"envelope": {...}, "payload": <原始形状>}，不破坏既有结构。

- wrap(): 将原始事件包装为符合 aiops-envelope.schema.json 的字典
- validate(): 校验 envelope 是否合规（返回错误列表，空 = 合法）
- new_causation_id(): 由触发事件生成 caus-<hash> 根因链 ID

Schema version: 0.1（冻结，见 SPEC §5.1）
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

SCHEMA_VERSION = "0.1"

EVENT_TYPES = (
    "alarm",
    "rca",
    "anomaly",
    "inspection",
    "incident",
    "blackboard",
    "action",
    "evidence",
)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _new_event_id() -> str:
    return f"evt-{uuid.uuid4().hex[:12]}"


def new_causation_id(seed: str) -> str:
    """由触发事件（如根因 alarm_id）生成 caus-<sha256[:12]> 根因链 ID。"""
    return f"caus-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:12]}"


def _set_if(dst: dict, key: str, value: Any) -> None:
    """仅在 value 非 None 时写入，避免污染信封（None 字段留空即可，schema 允许）。"""
    if value is not None:
        dst[key] = value


def wrap(
    event_type: str,
    payload: dict,
    *,
    trace_id: str,
    timestamp: str | None = None,
    tenant_id: str | None = None,
    region: str | None = None,
    incident_id: str | None = None,
    causation_id: str | None = None,
    resource: dict | None = None,
    time_window: dict | None = None,
    evidence: list[dict] | None = None,
    data_quality: dict | None = None,
    confidence: float | None = None,
    decision: dict | None = None,
    action_state: str | None = None,
) -> dict:
    """将原始事件包装为 AIOpsEnvelope 字典。

    Args:
        event_type: 事件类型（EVENT_TYPES 之一）。
        payload: 原始事件形状（不改写，原样放入 envelope["payload"]）。
        trace_id: 必填 — 跨产品串联的主键。
        其余为可空身份/上下文字段；None 时以 JSON null 语义留空（对齐 P0-0
        User ID 开放议题：本地/自动化运行无值用 null，不阻塞）。

    Returns:
        符合 aiops-envelope.schema.json 的字典。event_id 自动生成。
    """
    if event_type not in EVENT_TYPES:
        raise ValueError(f"unknown event_type: {event_type!r} (expected one of {EVENT_TYPES})")
    if not trace_id:
        raise ValueError("trace_id is required")

    env: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "event_id": _new_event_id(),
        "event_type": event_type,
        "trace_id": trace_id,
        "timestamp": timestamp or _utc_now(),
    }
    _set_if(env, "tenant_id", tenant_id)
    _set_if(env, "region", region)
    _set_if(env, "incident_id", incident_id)
    _set_if(env, "causation_id", causation_id)
    _set_if(env, "resource", resource)
    _set_if(env, "time_window", time_window)
    _set_if(env, "evidence", evidence)
    _set_if(env, "data_quality", data_quality)
    _set_if(env, "confidence", confidence)
    _set_if(env, "decision", decision)
    _set_if(env, "action_state", action_state)
    env["payload"] = payload
    return env


def validate(envelope: dict, schema: dict | None = None) -> list[str]:
    """校验 envelope 是否符合 aiops-envelope.schema.json。

    Args:
        envelope: wrap() 或外部构造的信封字典。
        schema: 可选 — 注入自定义 schema；None 时加载仓库默认 schema。

    Returns:
        错误列表；空列表 = 合法。
    """
    try:
        import jsonschema  # type: ignore
    except ImportError:
        # 无 jsonschema 依赖时退化为最小结构校验（不阻断 CI 冒烟）。
        return _minimal_validate(envelope)

    if schema is None:
        schema = _load_default_schema()
    validator = jsonschema.Draft7Validator(schema)
    return [e.message for e in validator.iter_errors(envelope)]


def _load_default_schema() -> dict:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]  # qcloud-copilot/
    schema_path = (
        root.parent / "qcloud-aiops-diagnosis" / "assets" / "aiops-envelope.schema.json"
    )
    import json

    with schema_path.open() as f:
        return json.load(f)


def _minimal_validate(envelope: dict) -> list[str]:
    """无 jsonschema 依赖时的最小校验：必填字段 + 类型 + enum 白名单。"""
    errors: list[str] = []
    required = ("schema_version", "event_id", "event_type", "trace_id", "timestamp")
    for k in required:
        if k not in envelope:
            errors.append(f"{k!r} is a required property")
    if envelope.get("event_type") not in EVENT_TYPES:
        errors.append(f"event_type {envelope.get('event_type')!r} not in {EVENT_TYPES}")
    if not envelope.get("trace_id"):
        errors.append("trace_id must be a non-empty string")
    return errors
