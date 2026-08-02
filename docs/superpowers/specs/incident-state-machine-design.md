# P0-3: Incident 生命周期状态机（Incident Lifecycle State Machine）设计

> 状态：Draft · 关联 Plan：`docs/superpowers/plans/2026-07-25-aiops-optimization-todo.md` §P0-3
> 前置：P0-1 `AIOpsEnvelope`（`aiops_envelope.py`）已落地；P0-2 检测质量反馈（`quality/feedback.py`）已落地。本设计定义 incident 的状态机，消费 P0-1 信封的 `incident_id`，复用 P0-2 已确立的 `action_state`/`verification` 语义方向。

## 1. 背景与问题

当前 incident 状态散落在多处且**无统一状态机**：

- `references/mttr-tracking.md` 只有 `status(DETECTED|DIAGNOSED|RESOLVED)` 三态枚举。
- `scripts/incident_timeline_aggregator.py` 定义的是时间线事件**角色**（change/trigger/root_candidate/symptom/correlated），不是 incident 生命周期状态。
- `AIOpsSummary`/信封的 `incident_id`、`action_state` 是快照字段，无状态转移规则。
- 无转移条件、超时、升级、取消、重开、并发冲突处理。
- 无责任人、SLA、升级路径、动作记录、审计字段的统一模型。
- 无 MTTD/MTTA/MTTR + 各状态停留时间统计。

**核心缺口**：没有一个 `IncidentStateMachine` 类能回答「这个 incident 现在在哪个状态、能否转移到哪个状态、如何触发」。

## 2. 目标

- 定义 `detected → correlated → diagnosed → mitigating → verifying → resolved → reviewed` 状态机。
- 明确状态转移条件、超时、升级、取消、重开和并发冲突处理。
- 统一责任人、SLA、升级路径、动作记录和审计字段。
- 在 Blackboard、RCA Bundle 和报告中保持状态一致（幂等、可回放）。
- 接入 MTTD、MTTA、MTTR 和各状态停留时间统计。
- 验收：一个 incident 可完整回放从发现到关闭的生命周期。

## 3. 非目标

- 不重写 `incident_timeline_aggregator.py`（它做时间线聚合，不冲突；状态机独立）。
- 不实现 P0-4 修复后验证闭环（状态机只在 `verifying` 状态停留，验证逻辑归 P0-4）。
- 不实现 P0-5 SLO 排序（状态机不管优先级排序）。

## 4. 架构

```
            ┌─────────────────────────────────────────────┐
            │           IncidentStateMachine (新模块)       │
            │  states: detected→correlated→diagnosed→     │
            │          mitigating→verifying→resolved→     │
            │          reviewed                            │
            │  + cancel(任意态) / reopen(resolved→detected)│
            │  transitions: (from,event,to) + guards       │
            │  + SLA timers / escalation / audit log       │
            └──────────────────┬──────────────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
      Blackboard 事件    RCA Bundle 写入     报告/指标统计
      (信封 incident_id) (state 一致性)     (MTTD/MTTA/MTTR/dwell)
```

**关键决策**：
- **状态机是纯函数/可回放**：`transition(incident, event, meta) -> (new_state, action_log[])`，不直接 mutate；由调用方决定是否持久化。这样 Blackboard/RCA/report 可以各自消费同一转移结果，保持一致性。
- **并发冲突处理**：状态机记录每个状态的 `at` 时间戳 + 乐观锁（`expected_state`），若当前状态 ≠ 期望状态 → 拒绝转移（返回 `StaleStateError`）。
- **事件驱动**：转移由事件（`correlate`/`diagnose`/`mitigate`/`verify`/`resolve`/`review`/`escalate`/`cancel`/`reopen`）触发，而非直接改状态字段。

## 5. 数据模型

### 5.1 `IncidentState`（枚举）

```python
class IncidentState(str, Enum):
    DETECTED = "detected"
    CORRELATED = "correlated"
    DIAGNOSED = "diagnosed"
    MITIGATING = "mitigating"
    VERIFYING = "verifying"
    RESOLVED = "resolved"
    REVIEWED = "reviewed"
    CANCELLED = "cancelled"
```

### 5.2 `IncidentEvent`（枚举）

```python
class IncidentEvent(str, Enum):
    CORRELATE = "correlate"     # detected → correlated
    DIAGNOSE = "diagnose"       # correlated → diagnosed
    MITIGATE = "mitigate"       # diagnosed → mitigating
    VERIFY = "verify"           # mitigating → verifying
    RESOLVE = "resolve"         # verifying → resolved
    REVIEW = "review"           # resolved → reviewed
    ESCALATE = "escalate"       # 任意非终态 → 同状态 + 升级（sla_violated=True）
    CANCEL = "cancel"           # 任意非终态 → cancelled
    REOPEN = "reopen"           # resolved → detected
```

### 5.3 `IncidentRecord`

```python
@dataclass
class IncidentRecord:
    incident_id: str
    state: IncidentState
    severity: str          # P0..P3
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
    escalation_path: list[str] = field(default_factory=list)
    action_log: list[dict] = field(default_factory=list)  # {event,state,at,actor,note}
```

### 5.4 状态转移表

| from | event | to | 说明 |
|---|---|---|---|
| detected | correlate | correlated | 关联到同类事件 |
| correlated | diagnose | diagnosed | 根因诊断完成 |
| diagnosed | mitigate | mitigating | 开始处置 |
| mitigating | verify | verifying | 处置完成，进入验证 |
| verifying | resolve | resolved | 验证通过 |
| resolved | review | reviewed | 复盘完成（终态） |
| 任意非终态 | cancel | cancelled | 取消（终态） |
| resolved | reopen | detected | 重开 |

**非法转移**：不在表内的 `(from,event)` → `InvalidTransitionError`。

### 5.5 SLA 升级

- 每个非终态可有 `sla_deadline`（如 diagnosed 后 30min 未 mitigate → escalate）。
- `escalate` 事件：`sla_escalated=True`，追加到 `escalation_path`，状态不变。

## 6. 文件清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `docs/superpowers/specs/incident-state-machine-design.md` | 设计文档 | 本文档 |
| `qcloud-copilot/copilot/incident_state.py` | 实现 | `IncidentState`/`IncidentEvent`/`IncidentRecord`/`IncidentStateMachine`/`transition` |
| `scripts/incident_state_aggregate.py` | 聚合 | 读 JSONL → 每 incident 状态回放 + MTTD/MTTA/MTTR/dwell 表 |
| `scripts/test_incident_state.py` | 测试 | 状态机转移/非法转移/SLA/并发/回放/dwell |

## 7. 函数签名

```python
# qcloud-copilot/copilot/incident_state.py
class IncidentStateMachine:
    def __init__(self, *, sla_minutes: dict | None = None) -> None: ...
    def valid_transitions(self, state: IncidentState) -> list[tuple[IncidentEvent, IncidentState]]: ...
    def transition(self, incident: IncidentRecord, event: IncidentEvent, *,
                   actor: str = "", note: str = "",
                   expected_state: IncidentState | None = None) -> IncidentRecord:
        """返回转移后的新 IncidentRecord（不 mutate 原对象）。非法转移抛
        InvalidTransitionError；并发冲突（expected_state 不符）抛 StaleStateError。"""

def replay(records: list[dict]) -> IncidentRecord:
    """从 JSONL 动作日志回放出 incident 当前状态（可回放性验收）。"""

def dwell_stats(record: IncidentRecord, now: str | None = None) -> dict[str, float]:
    """各状态停留时间（分钟）+ MTTD/MTTA/MTTR 摘要。"""
```

## 8. Self-check / 自验

- **转移表完备**：遍历所有 `(state,event)` 组合，合法转移返回新状态，非法抛 `InvalidTransitionError`。
- **可回放**：对同一 incident 的动作日志 replay 两次 → 结果一致（幂等）。
- **并发**：`transition` 带 `expected_state`，旧状态转移 → `StaleStateError`。
- **SLA**：超过 `sla_deadline` 的 escalate → `sla_escalated=True` + escalation_path 追加。
- **dwell 统计**：已知时间戳样本 → 断言停留时间精确（非仅键存在）。
- **脱敏**：JSONL 不含 SecretId/SecretKey。
- 门禁：ruff 零 error；pytest 全绿；`validate_local.py` 不回归。

## 9. Phase 清单（PLAN）

- [ ] **Phase 0**: 写本文档（SPEC）。
- [ ] **Phase 1 (TDD 红)**: 写 `scripts/test_incident_state.py`（转移表/非法转移/SLA/并发/回放/dwell）。
- [ ] **Phase 2 (TDD 绿)**: 实现 `qcloud-copilot/copilot/incident_state.py` + `scripts/incident_state_aggregate.py`，转绿。
- [ ] **Phase 3**: ruff + 全量测试 + SPEC 逐条对照。

## 10. DoD / 验收标准

- [ ] 7 态 + cancel/reopen 状态机可回放，非法转移显式报错。
- [ ] SLA 升级、责任人、escalation_path、action_log 完整。
- [ ] dwell_stats 输出 MTTD/MTTA/MTTR + 各状态停留时间（精确断言）。
- [ ] 无凭证/敏感信息写入 JSONL。
- [ ] ruff 零 error、pytest 全绿、`validate_local.py` 不回归。
