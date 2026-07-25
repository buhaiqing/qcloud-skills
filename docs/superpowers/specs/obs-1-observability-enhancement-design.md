# OBS-1: Copilot 可观测性增强 — 设计文档

## 背景

当前 `qcloud-copilot` 已具备基础埋点能力：
- `copilot/quality/audit.py::audit_trace` — 按 step 写独立 JSON（`step-{id}-{ts}.json`）
- `copilot/quality/health.py::record_health` — append 到 `.runtime/health/skill-metrics.jsonl`
- `copilot/quality/reflexion.py` — 失败 pattern 落 scratch 后聚合进 `docs/failure-patterns.md`
- `integration/gcl.py` — 通过 `trace_id == run_id` 与 GCL 轨迹 join

**诊断结论（代码事实）**：
1. `health.py` 只写不读，全仓库无任何聚合/查询逻辑（O1）。
2. `audit_trace` 同 run 多 step 文件散落，无统一 run 索引，无法串联一次执行（O2）。
3. 仅 jsonl 文本，无 counter/gauge/histogram，无法接入 Prometheus/Grafana（O3）。
4. `record_health` 硬编码 `"error_code": None`，失败路径几乎无信号（O4，见 `health.py:24`）。
5. 仅 blackboard-init 与 L2 有 trace，L0/L1/L3 失败无 trace，安全拒拦不可审计（O5）。

**目标**：把"已落盘但不可消费"的数据升级为"可聚合、可查询、可导出、可审计"的可观测性底座，为后续自我进化回路提供统一信号源。

---

## 架构设计

> **TRACE-1 重构同步说明（2026-07-25）**：本 OBS-1 文档负责埋点基础设施，不再定义业务 Trace 主模型。主模型以 `docs/superpowers/specs/trace-usage-finops-design.md` 第 14 节为准：Langfuse 风格 `Trace` 聚合根、`Observation` 执行树、`UsageEvent` 事实账本、`Score` 和可重建 Summary。`ObservableSink.emit_span` 是底层写入能力，最终应写入 Observation；`audit_trace` 和旧 health JSONL 仅作为兼容入口。

身份同步：当前代码没有 `user_id`；`session_id` 只代表 Copilot 会话，不能当作用户。OBS-1 的埋点接口应透传固定 `identity` 树（`user_id`、`tenant_id`、`customer_id`、`operator_id`、`service_account_id`、`account_id_hash`、`actor_type`、`initiator_type`、`identity_source`、`identity_confidence`）；缺失值统一序列化为 JSON `null`，不得使用 `"unknown"` 或空字符串冒充值。

User ID 是 TRACE-1 的开放/延后决策，不是 OBS-1 或当前 AIOps/FinOps 主线的阻塞项。当前本地 CLI 和定时 Agent 运行只需记录固定身份树与 automation 树；无可靠用户来源时 `user_id=null`，不得用 `session_id`、本地用户名或 Agent 名称替代。

```
执行链路 (engine/dispatcher)
        │ 埋点
        ▼
┌─────────────────────────────────────────┐
│ ObservableSink (新增 copilot/observ.py)  │  ← 统一埋点门面
│  - emit_metric(name, tags, value)        │
│  - emit_observation(trace_id, observation)│
│  - emit_usage(trace_id, usage_event)     │
│  - emit_span(...) [legacy adapter]       │
│  - emit_gate(gate, decision, reason)     │
└─────────────────────────────────────────┘
        │
        ├─► writer: append jsonl (兼容现有 health.py)
        ├─► writer: run-index (audit/{run_id}/_index.json)  ← 解决 O2
        └─► writer: Prometheus text exposition (metrics.prom) ← 解决 O3
        │
        ▼
┌─────────────────────────────────────────┐
│ QueryAPI (新增 copilot/observ_query.py)  │  ← 解决 O1
│  - skill_success_rate(skill, days)       │
│  - p99_latency(op, days)                 │
│  - gate_decision_count(gate, decision)   │
└─────────────────────────────────────────┘
```

---

## 模块设计

### 1. `copilot/observ.py` — 统一埋点门面（解决 O1/O2/O3）

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import time, json
from datetime import datetime, timezone

class MetricKind(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"

@dataclass
class Metric:
    name: str
    kind: MetricKind
    value: float
    tags: dict[str, str] = field(default_factory=dict)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class Span:
    run_id: str
    step_id: str
    status: str           # started|success|fail|skipped
    duration_ms: int = 0
    error_code: str | None = None

class ObservableSink:
    """Single facade replacing ad-hoc record_health/audit_trace calls."""

    def __init__(self, runtime_root: Path | None = None):
        self._root = runtime_root or (Path.cwd() / ".runtime")
        self._root.mkdir(parents=True, exist_ok=True)

    def emit_metric(self, m: Metric) -> None: ...
    def emit_span(self, s: Span) -> None: ...
    def emit_gate(self, run_id, gate: str, decision: str, reason: str) -> None: ...
    # 内部: 同时写 jsonl + run-index + prom text
```

**run-index（解决 O2）**：每次 `emit_span` 时，向 `.runtime/audit/{run_id}/_index.json` 追加
```json
{"run_id":"...","step_id":"l2-gate","status":"pass","ts":"...","order":3}
```
使一次会话的完整 Observation 树可在 O(1) 读取还原；run-index 不再作为业务 Trace 主模型。

**Prometheus 导出（解决 O3）**：`.runtime/metrics/metrics.prom` 持续追加
```
copilot_step_duration_ms{skill="qcloud-cvm-ops",status="success"} 1234
copilot_gate_decision_total{gate="l2",decision="pass"} 1
copilot_skill_success_total{skill="qcloud-copilot"} 1
```

### 2. `copilot/observ_query.py` — 聚合查询 API（解决 O1）

从 Observation/UsageEvent + 兼容 health JSONL 读取，提供：
- `skill_success_rate(skill, days=7) -> float`
- `p_latency(op, p=99, days=7) -> int`
- `gate_decision_rate(gate) -> dict[str, float]`
- `top_failed_operations(days=7, limit=10) -> list[tuple]`

self-check: 对 `.runtime/health/skill-metrics.jsonl` 已有数据可正确聚合（向后兼容）。

### 3. Gate 可观测性补齐（解决 O5）

在 `engine.py` 中，L0/L1/L3 失败时补 `emit_gate`：
- L0 fail → `emit_gate(run, "l0", "fail", issues)`
- L1 fail → `emit_gate(run, "l1", "fail", issues)`
- L3 fail → `emit_gate(run, "l3", "fail", issues)`

### 4. error_code 填充（解决 O4）

`record_health` / `emit_span` 增加 `error_code` 真实值：
- L0/L1/L2/L3 失败 → 用 gate 名作为 error_code
- step 执行失败 → 用 `step_result.error` 首词或 step 类型

---

## 数据结构 / Schema

### 新增文件
- `.runtime/audit/{run_id}/_index.json` — 执行链路索引（O2）
- `.runtime/metrics/metrics.prom` — Prometheus 文本导出（O3）
- `.runtime/metrics/metrics.jsonl` — 结构化 metric 原始流（O1 查询源）
- `copilot/observ.py` — 埋点门面
- `copilot/observ_query.py` — 查询 API

### 复用/改造
- `copilot/quality/health.py` — 内部改为调用 `ObservableSink`（不破坏现有 jsonl 格式）
- `copilot/quality/audit.py` — 内部改为调用 `ObservableSink.emit_span`
- `copilot/engine.py` — 4 处 gate 补 `emit_gate`
- `copilot/dispatcher.py` — step 执行补 `emit_span` + `error_code`

---

## 文件清单

| 文件 | 动作 |
|------|------|
| `qcloud-copilot/copilot/observ.py` | 新增 |
| `qcloud-copilot/copilot/observ_query.py` | 新增 |
| `qcloud-copilot/copilot/quality/health.py` | 改造（委托 ObservableSink） |
| `qcloud-copilot/copilot/quality/audit.py` | 改造（委托 ObservableSink） |
| `qcloud-copilot/copilot/engine.py` | 改造（4 gate emit_gate） |
| `qcloud-copilot/copilot/dispatcher.py` | 改造（step span + error_code） |
| `qcloud-copilot/tests/test_observ.py` | 新增 |
| `qcloud-copilot/tests/test_observ_query.py` | 新增 |

---

## 自验证（self-check）

```python
# test_observ.py 必须覆盖:
assert ObservableSink.emit_span 写入 {run_id}/_index.json 且可还原顺序
assert Prometheus 文本含 copilot_step_duration_ms 行
assert emit_gate 后 metrics.jsonl 出现对应 counter

# test_observ_query.py 必须覆盖:
# 构造 20 条历史 jsonl, 验证 skill_success_rate 计算正确
# 验证 p99_latency 分位数正确
# 验证 top_failed_operations 返回降序
```

---

## 与自我进化回路的关系

本 spec 是 **EVO-1（自我进化）** 的信号上游：EVO-1 的"进化决策层"将直接消费
`observ_query.skill_success_rate()` / `gate_decision_rate()` 作为反馈信号，
避免重复发明埋点。两者通过 `.runtime/metrics` 单一数据源解耦。
