"""P0-3 Incident 生命周期状态机（IncidentStateMachine）。

设计见 docs/superpowers/specs/incident-state-machine-design.md。

- ``IncidentState`` / ``IncidentEvent``：状态与事件枚举。
- ``IncidentRecord``：incident 快照（时间戳 / SLA / 升级路径 / 动作日志）。
- ``IncidentStateMachine``：纯函数式状态转移（不 mutate 输入），支持乐观锁
  （``expected_state``）与 SLA 升级。
- ``replay``：从动作日志回放 incident 当前状态（可回放性验收）。
- ``dwell_stats``：各状态停留时间 + MTTD/MTTA/MTTR 摘要。

状态机是纯函数/可回放：``transition`` 返回新 ``IncidentRecord``，由调用方决定
是否持久化，保证 Blackboard / RCA / report 消费同一转移结果。
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import Enum


class IncidentState(str, Enum):
    DETECTED = "detected"
    CORRELATED = "correlated"
    DIAGNOSED = "diagnosed"
    MITIGATING = "mitigating"
    VERIFYING = "verifying"
    RESOLVED = "resolved"
    REVIEWED = "reviewed"
    CANCELLED = "cancelled"


class IncidentEvent(str, Enum):
    CORRELATE = "correlate"  # detected → correlated
    DIAGNOSE = "diagnose"  # correlated → diagnosed
    MITIGATE = "mitigate"  # diagnosed → mitigating
    VERIFY = "verify"  # mitigating → verifying
    RESOLVE = "resolve"  # verifying → resolved
    REVIEW = "review"  # resolved → reviewed
    ESCALATE = "escalate"  # 任意非终态 → 同状态 + 升级
    CANCEL = "cancel"  # 任意非终态 → cancelled
    REOPEN = "reopen"  # resolved → detected


# 非终态（可 escalate / cancel）
_NONTERMINAL = frozenset(
    {
        IncidentState.DETECTED,
        IncidentState.CORRELATED,
        IncidentState.DIAGNOSED,
        IncidentState.MITIGATING,
        IncidentState.VERIFYING,
    }
)

# 时间戳字段名 → 对应状态
_TIMESTAMP_FIELDS = {
    IncidentState.DETECTED: "detected_at",
    IncidentState.CORRELATED: "correlated_at",
    IncidentState.DIAGNOSED: "diagnosed_at",
    IncidentState.MITIGATING: "mitigating_at",
    IncidentState.VERIFYING: "verifying_at",
    IncidentState.RESOLVED: "resolved_at",
    IncidentState.REVIEWED: "reviewed_at",
    IncidentState.CANCELLED: "cancelled_at",
}

# 状态顺序（主链）
_CHAIN = (
    IncidentState.DETECTED,
    IncidentState.CORRELATED,
    IncidentState.DIAGNOSED,
    IncidentState.MITIGATING,
    IncidentState.VERIFYING,
    IncidentState.RESOLVED,
    IncidentState.REVIEWED,
)


class InvalidTransitionError(Exception):
    """非法转移：(from_state, event) 不在转移表内。"""

    def __init__(self, from_state: IncidentState, event: IncidentEvent) -> None:
        self.from_state = from_state
        self.event = event
        super().__init__(f"invalid transition: {from_state.value} + {event.value}")


class StaleStateError(Exception):
    """并发冲突：expected_state 与当前状态不符（乐观锁拒绝）。"""

    def __init__(self, expected: IncidentState, actual: IncidentState) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(f"stale state: expected {expected.value}, actual {actual.value}")


@dataclass
class IncidentRecord:
    incident_id: str
    state: IncidentState
    severity: str  # P0..P3
    tenant_id: str | None = None
    region: str | None = None
    product: str | None = None
    detected_at: str | None = None
    correlated_at: str | None = None
    diagnosed_at: str | None = None
    mitigating_at: str | None = None
    verifying_at: str | None = None
    resolved_at: str | None = None
    reviewed_at: str | None = None
    cancelled_at: str | None = None
    sla_escalated: bool = False
    sla_deadline: str | None = None
    owner: str | None = None
    escalation_path: list[dict] = field(default_factory=list)
    action_log: list[dict] = field(default_factory=list)  # {event,state,at,actor,note}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


class IncidentStateMachine:
    """Incident 状态机。

    Args:
        sla_minutes: 可选 — 状态名 → 分钟数，如 {"diagnosed": 30}。状态在对应
            状态停留超过该时长时，可触发 escalate（由调用方判断；本类在 escalate
            事件上只标记升级，不自动计时）。
    """

    def __init__(self, *, sla_minutes: dict | None = None) -> None:
        self.sla_minutes = sla_minutes or {}

    def valid_transitions(self, state: IncidentState) -> list[tuple[IncidentEvent, IncidentState]]:
        """返回某状态合法的 (event, to) 对列表。"""
        pairs: list[tuple[IncidentEvent, IncidentState]] = []
        if state == IncidentState.DETECTED:
            pairs.append((IncidentEvent.CORRELATE, IncidentState.CORRELATED))
        elif state == IncidentState.CORRELATED:
            pairs.append((IncidentEvent.DIAGNOSE, IncidentState.DIAGNOSED))
        elif state == IncidentState.DIAGNOSED:
            pairs.append((IncidentEvent.MITIGATE, IncidentState.MITIGATING))
        elif state == IncidentState.MITIGATING:
            pairs.append((IncidentEvent.VERIFY, IncidentState.VERIFYING))
        elif state == IncidentState.VERIFYING:
            pairs.append((IncidentEvent.RESOLVE, IncidentState.RESOLVED))
        elif state == IncidentState.RESOLVED:
            pairs.append((IncidentEvent.REVIEW, IncidentState.REVIEWED))
            pairs.append((IncidentEvent.REOPEN, IncidentState.DETECTED))

        if state in _NONTERMINAL:
            pairs.append((IncidentEvent.ESCALATE, state))
            pairs.append((IncidentEvent.CANCEL, IncidentState.CANCELLED))
        return pairs

    def transition(
        self,
        incident: IncidentRecord,
        event: IncidentEvent,
        *,
        actor: str = "",
        note: str = "",
        expected_state: IncidentState | None = None,
    ) -> IncidentRecord:
        """应用一次事件转移，返回新的 ``IncidentRecord``（不 mutate 输入）。

        - ``expected_state`` 不为 None 且与当前状态不符 → 抛 ``StaleStateError``。
        - 不在转移表内的 (state, event) → 抛 ``InvalidTransitionError``。
        - 前向转移设置对应 ``*_at`` 为当前 UTC 时间；escalate 设置
          ``sla_escalated=True`` 并把 actor 追加到 ``escalation_path``。
        - 每次转移都追加一条 ``action_log``。
        """
        if expected_state is not None and incident.state != expected_state:
            raise StaleStateError(expected=expected_state, actual=incident.state)

        to_state: IncidentState | None = None
        for ev, to in self.valid_transitions(incident.state):
            if ev == event:
                to_state = to
                break
        if to_state is None:
            raise InvalidTransitionError(incident.state, event)

        now = _utc_now()
        new = replace(incident, state=to_state)
        new.action_log = list(incident.action_log)

        if event == IncidentEvent.ESCALATE:
            new.sla_escalated = True
            new.escalation_path = list(incident.escalation_path)
            if actor:
                new.escalation_path.append({"actor": actor})
        else:
            ts_field = _TIMESTAMP_FIELDS.get(to_state)
            if ts_field is not None and getattr(new, ts_field) is None:
                setattr(new, ts_field, now)
            if event == IncidentEvent.CANCEL:
                new.escalation_path = list(incident.escalation_path)

        new.action_log.append(
            {
                "event": event.value,
                "state": to_state.value,
                "at": now,
                "actor": actor,
                "note": note,
            }
        )
        return new

    def sla_breached(self, incident: IncidentRecord, now: str | None = None) -> bool:
        """当前状态是否已超过 sla_minutes 设定的停留时长（SLA 触发检查）。

        sla_minutes 是事件驱动 escalate 的计时依据：调用方在 escalate 前用本方法
        判断是否应升级。无 sla_minutes 配置或当前状态无起始时间戳 → False。
        """
        limit = self.sla_minutes.get(incident.state.value)
        if not limit:
            return False
        state_at = _TIMESTAMP_FIELDS.get(incident.state)
        start = getattr(incident, state_at, None) if state_at else None
        if not start:
            return False
        return _minutes_between(start, now or _utc_now()) > limit


def replay(
    records: list[dict],
    *,
    incident_id: str | None = None,
    severity: str = "P1",
    detected_at: str | None = None,
) -> IncidentRecord:
    """从动作日志回放 incident 当前状态。

    Args:
        records: action-log 字典列表，每个形如 {event, state, at, actor, note}。
            以 DETECTED 为起点，顺序应用事件。
        incident_id: 可选 — 回放记录的 incident_id（缺省取第一条日志或 "replayed"）。
        severity: 可选 — 回放记录的严重级别（默认 "P1"）。
        detected_at: 可选 — 检测时刻。动作日志无 DETECT 事件，若提供则种子化
            ``detected_at``，使 dwell/mttd 统计可精确还原。

    Returns:
        回放结束后的 ``IncidentRecord``。
    """
    sm = IncidentStateMachine()
    rec = IncidentRecord(
        incident_id=incident_id or (records[0].get("incident_id") if records else None) or "replayed",
        state=IncidentState.DETECTED,
        severity=severity,
        detected_at=detected_at,
    )
    for entry in records:
        if "event" not in entry:
            raise ValueError(f"replay entry missing required 'event' key: {entry!r}")
        event = IncidentEvent(entry["event"])
        rec = sm.transition(
            rec,
            event,
            actor=entry.get("actor", ""),
            note=entry.get("note", ""),
        )
        # 回放时用日志里记录的时间戳恢复确定性
        at = entry.get("at")
        if at:
            ts_field = _TIMESTAMP_FIELDS.get(rec.state)
            if ts_field is not None and rec.state != IncidentState.CANCELLED:
                setattr(rec, ts_field, at)
        if rec.state == IncidentState.CANCELLED and entry.get("at"):
            rec.cancelled_at = entry["at"]
    return rec


def _parse_ts(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _minutes_between(a: str | None, b: str | None) -> float:
    """返回 b - a 的分钟数；任一未设置 → 0.0；结果为负（如 reopen 后旧状态
    时间戳晚于新 detected_at）→ 截断为 0.0，避免聚合表出现负 dwell/MTTR。"""
    if not a or not b:
        return 0.0
    mins = (_parse_ts(b) - _parse_ts(a)).total_seconds() / 60.0
    return max(0.0, mins)


def dwell_stats(record: IncidentRecord, now: str | None = None) -> dict[str, float]:
    """各状态停留时间（分钟）+ MTTD/MTTA/MTTR 摘要。

    - 仅统计已发生（对应 ``*_at`` 已设置）的状态。
    - 状态 X 的 dwell = 下一个状态 ``*_at`` - X 的 ``*_at``；若 X 是当前/终态且无
      下一个状态，则用 ``now``（未给则 0.0）。
    - mttd_min = correlated_at - detected_at（发现→关联）。
    - mtta_min = diagnosed_at - detected_at（发现→确认/诊断）。
    - mttr_min = resolved_at - detected_at（发现→解决）。
    """
    at_of = {st: getattr(record, _TIMESTAMP_FIELDS[st]) for st in _CHAIN}

    def dwell_for(idx: int) -> float:
        st = _CHAIN[idx]
        cur_at = at_of[st]
        if cur_at is None:
            return 0.0
        nxt = _CHAIN[idx + 1] if idx + 1 < len(_CHAIN) else None
        nxt_at = at_of[nxt] if nxt else None
        if nxt_at is not None:
            return _minutes_between(cur_at, nxt_at)
        # 无下一个状态：若是 cancelled，用 cancelled_at；否则用 now
        if record.state == IncidentState.CANCELLED and record.cancelled_at:
            return _minutes_between(cur_at, record.cancelled_at)
        return _minutes_between(cur_at, now)

    stats: dict[str, float] = {}
    for idx, st in enumerate(_CHAIN):
        if at_of[st] is not None:
            stats[st.value] = round(dwell_for(idx), 6)

    stats["mttd_min"] = round(_minutes_between(record.detected_at, record.correlated_at), 6)
    stats["mtta_min"] = round(_minutes_between(record.detected_at, record.diagnosed_at), 6)
    stats["mttr_min"] = round(_minutes_between(record.detected_at, record.resolved_at), 6)
    return stats
