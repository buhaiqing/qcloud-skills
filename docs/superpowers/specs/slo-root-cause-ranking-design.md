# P0-5: SLO/业务影响驱动的根因排序（SLO-driven Root Cause Ranking）设计

> 状态：Draft · 关联 Plan：`docs/superpowers/plans/2026-07-25-aiops-optimization-todo.md` §P0-5
> 前置：P0-1 `AIOpsEnvelope`（含 evidence/confidence/decision）、P0-3 `incident_state.py`、P0-4 `verification.py` 已落地。本设计为 incident 的候选根因做 SLO/业务影响驱动的排序。

## 1. 背景与问题

当前根因排序缺乏业务影响维度：

- 无服务、业务链路、客户等级、请求量、错误预算消耗字段。
- 根因排序只按证据强度/拓扑距离，未纳入业务影响。
- 无统一排序公式（证据强度、拓扑距离、时间相关性、业务影响、历史先验）。
- 不支持核心业务时段、发布窗口、维护窗口的优先级调整。
- 同一资源异常在不同业务影响下无法产生不同优先级/响应策略。

**核心缺口**：没有一个 `RootCauseRanker` 能回答「这些候选根因里，哪个最该先处理——考虑它对核心业务的影响」。

## 2. 目标

- 引入服务、业务链路、客户等级、请求量、错误预算消耗字段。
- 将业务影响纳入事件严重度和根因排序。
- 设计并测试统一排序公式：证据强度、拓扑距离、时间相关性、业务影响、历史先验。
- 支持核心业务时段、发布窗口和维护窗口的优先级调整。
- 验收：同一资源异常在不同业务影响下产生不同优先级和响应策略。

## 3. 非目标

- 不重写现有检测器/状态机/验证器（P0-2/3/4）；本模块消费候选根因 + 业务上下文。
- 不实现修复执行（P0-4 已覆盖验证；本模块只管排序）。

## 4. 架构

```
   候选根因列表 + 业务上下文 (envelope/incident)
          │
          ▼
   ┌──────────────────────────────────────┐
   │   RootCauseRanker (新)                │
   │  ┌────────────────────────────────┐  │
   │  │ weighted rank formula          │  │
   │  │  evidence × w1 + topology × w2│  │
   │  │  + time_corr × w3 + impact × w4│ │
   │  │  + prior × w5                 │  │
   │  │  + window_adjust (core/release)│  │
   │  └────────────────────────────────┘  │
   └──────────────┬───────────────────────┘
                  │
                  ▼
          排序后的候选根因 (priority desc)
```

**关键决策**：
- **纯函数可回放**：`rank(candidates, context)` 返回排序后的列表 + 每项得分，不 mutate。
- **权重可配置**：`weights: dict[str, float]`（evidence/topology/time_corr/impact/prior），默认值内置，可 override。
- **业务影响字段**：每个候选根因带 `business_impact` 元数据（service/business_chain/customer_tier/request_rate/error_budget_consumed），驱动影响分。
- **窗口调整**：`window_adjust` 在核心时段/发布窗口给高优先级候选加分（乘性因子）。

## 5. 数据模型

### 5.1 `BusinessContext`

```python
@dataclass
class BusinessContext:
    service: str
    business_chain: str            # 如 "payment" / "search"
    customer_tier: str             # "platinum"|"gold"|"silver"|"internal"
    request_rate: float            # 每秒请求量
    error_budget_consumed: float   # 0~1，错误预算消耗比例
    core_hours: bool = False       # 是否核心业务时段
    release_window: bool = False   # 是否发布窗口
    maintenance_window: bool = False  # 是否维护窗口
```

### 5.2 `CandidateRootCause`

```python
@dataclass
class CandidateRootCause:
    candidate_id: str
    resource: str
    evidence_strength: float       # 0~1
    topology_distance: int         # 距根因节点跳数（越小越近）
    time_correlation: float        # 0~1，与异常时间窗的相关性
    historical_prior: float        # 0~1，历史上该资源是根因的先验概率
    business_impact: float | None = None  # 0~1，业务影响分（None 则从 context 推导）
    priority: float = 0.0          # 排序后回填
```

### 5.3 `RankResult`

```python
@dataclass
class RankResult:
    candidate_id: str
    score: float
    priority: float
    components: dict[str, float]   # 各维度原始分
    resource: str = ""             # 附加字段：来自 CandidateRootCause.resource，供聚合表展示
```

## 6. 文件清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `docs/superpowers/specs/slo-root-cause-ranking-design.md` | 设计文档 | 本文档 |
| `qcloud-copilot/copilot/root_cause_rank.py` | 实现 | `BusinessContext`/`CandidateRootCause`/`RankResult`/`RootCauseRanker`/`rank`/`impact_score`/`window_adjust` |
| `scripts/root_cause_rank_aggregate.py` | 聚合 | 读 JSONL → 排序表 + top 候选 |
| `scripts/test_root_cause_rank.py` | 测试 | 公式/权重/窗口调整/业务影响验收/幂等 |

## 7. 函数签名

```python
# qcloud-copilot/copilot/root_cause_rank.py
class RootCauseRanker:
    def __init__(self, *, weights: dict[str, float] | None = None,
                 window_boost: float = 1.2) -> None: ...
    def impact_score(self, candidate: CandidateRootCause, ctx: BusinessContext) -> float:
        """由 ctx 推导业务影响分（0~1）：客户等级 + 请求量 + 错误预算消耗加权。"""

    def rank(self, candidates: list[CandidateRootCause], ctx: BusinessContext) -> list[RankResult]:
        """按统一公式排序候选根因（降序）。不 mutate。window_adjust 叠加核心时段/发布窗口。"""

    def adjust_priority(self, score: float, ctx: BusinessContext) -> float:
        """核心时段/发布窗口乘 window_boost；维护窗口乘 1/window_boost。"""

def default_weights() -> dict[str, float]:
    """evidence=0.35, topology=0.2, time_corr=0.15, impact=0.2, prior=0.1。"""
```

## 8. Self-check / 自验

- **公式单调**：单维度升 → score 单调升；权重和为 1。
- **业务影响验收**：同一 resource 在 platinum 核心时段 vs internal 维护窗口 → 不同 priority。
- **窗口调整**：core_hours=True → 分乘 window_boost；maintenance_window=True → 分乘 1/boost。
- **幂等/纯函数**：rank 不 mutate candidates；两次 rank 结果一致。
- **权重 sum=1**：默认权重和为 1。partial override 时未指定维度归 0（非默认权重），有效权重归一化后和恒为 1（相对重要性语义）；全 0 → ValueError。
- **NaN/Inf 守卫**：evidence_strength/time_correlation/historical_prior/business_impact 为 NaN/Inf → ValueError，避免静默 nan 排序。
- **脱敏**：JSONL 不含 SecretId/SecretKey。
- 门禁：ruff 零 error；pytest 全绿；`validate_local.py` 不回归。

## 9. Phase 清单（PLAN）

- [x] **Phase 0**: 写本文档（SPEC）。
- [x] **Phase 1 (TDD 红)**: 写 `scripts/test_root_cause_rank.py`。
- [x] **Phase 2 (TDD 绿)**: 实现 `qcloud-copilot/copilot/root_cause_rank.py` + `scripts/root_cause_rank_aggregate.py`，转绿。
- [x] **Phase 3**: ruff + 全量测试 + SPEC 逐条对照。

## 10. DoD / 验收标准

- [x] 统一排序公式实现，权重可配置（partial override 未指定维度归 0，有效权重归一化）。
- [x] 业务影响（服务/链路/客户等级/请求量/错误预算）纳入排序。
- [x] 核心时段/发布/维护窗口优先级调整可测。
- [x] 同一资源异常在不同业务影响下 → 不同 priority（验收）。
- [x] 无凭证/敏感信息写入 JSONL。
- [x] ruff 零 error、pytest 全绿、`validate_local.py` 不回归。
