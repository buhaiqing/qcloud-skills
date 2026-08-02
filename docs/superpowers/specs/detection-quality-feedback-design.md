# P0-2: 检测质量反馈闭环（Detection Quality Feedback Loop）设计

> 状态：Draft · 关联 Plan：`docs/superpowers/plans/2026-07-25-aiops-optimization-todo.md` §P0-2
> 前置：P0-1 `AIOpsEnvelope`（`qcloud-copilot/copilot/aiops_envelope.py`）已落地。本设计在 finding/envelope 之上建立检测质量的度量与反馈闭环。

## 1. 背景与问题

当前检测（静态阈值、同比/环比基线、IsolationForest 等）输出 finding，但**没有质量反馈闭环**：

1. 无 `review_outcome` 字段，无法区分 `confirmed` / `false_positive` / `false_negative` / `inconclusive`。
2. 无 Precision / Recall / 噪声率 / 漏报率 的规则/模型/产品/租户维度统计。
3. 无平均提前发现时间、人工确认耗时、诊断置信度校准误差统计。
4. 人工反馈无法写回；即使能写回，也可能被未评审反馈直接改动生产规则。
5. 无阈值/窗口/规则调优建议的生成与审批、版本审计。

## 2. 目标

- 为 finding 增加 `review_outcome`：`confirmed` / `false_positive` / `false_negative` / `inconclusive`。
- 建立规则/模型/产品/租户维度的 Precision、Recall、噪声率、漏报率统计。
- 统计平均提前发现时间（MTTD）、人工确认耗时、诊断置信度校准误差。
- 支持人工反馈写回，并防止未经评审的反馈直接修改生产规则。
- 生成阈值、窗口和规则调优建议，保留审批与版本审计。
- 验收：每个检测规则都有可追踪的命中、误报和确认结果。

## 3. 非目标

- 不重写既有检测器（IsolationForest/Threshold 等）逻辑；只在其输出上增加反馈层。
- 不实现 P0-1 已覆盖的 envelope 包装；本模块消费 envelope/finding。
- 不自动改动生产规则——只生成"建议"，改动必须走审批。
- 不实现 P0-3 状态机 / P0-4 修复验证（`action_state` 归 P0-1 信封，状态转移归 P0-3）。

## 4. 架构

```
        findings / ScoreRecord / 人工确认
                    │
                    ▼
        ┌───────────────────────────────┐
        │   quality_feedback (新模块)     │
        │  ┌───────────────────────────┐ │
        │  │ RecordOutcome → review    │ │  review_outcome 落 finding/envelope
        │  │ MetricsAgg → stats        │ │  precision/recall/noise/late/calib
        │  │ TuningAdvise → 建议       │ │  阈值/窗口/规则 调优建议（只读）
        │  │ ApprovalGate → 审批       │ │  建议→审批→版本审计→落地
        │  └───────────────────────────┘ │
        └───────────────┬───────────────┘
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
    stats.jsonl / audit        生产规则（仅经审批）
```

**关键决策**：
- **度量以 JSONL 追加写**（`audit-results/quality-feedback.jsonl`），对齐仓库既有的 metrics JSONL 风格。
- **反馈写回是幂等的**：`record_outcome(finding_id, outcome)` 以 finding_id 为键，重复提交更新而非重复插入。
- **生产规则只读**：`TuningAdvise` 生成建议，`ApprovalGate` 需显式 token/审批才生成"可落地补丁"；模块默认不落地。
- **防未评审反馈直改规则**：任何 `apply_recommendation()` 必须携带 approval token（复用 `harness_safety` 的 token 语义）。

## 5. 数据模型

### 5.1 `ReviewOutcome`（枚举）

```python
class ReviewOutcome(str, Enum):
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    FALSE_NEGATIVE = "false_negative"
    INCONCLUSIVE = "inconclusive"
```

### 5.2 `OutcomeRecord`（JSONL 行）

```jsonc
{
  "finding_id": "f-xxxx",
  "trace_id": "trace-...",
  "rule": "cvm-cpu-high",
  "model": "threshold_based",
  "product": "cvm",
  "tenant_id": "tenant-01",
  "outcome": "confirmed",            // confirmed|false_positive|false_negative|inconclusive
  "detected_at": "2026-08-02T00:00:00Z",
  "confirmed_at": "2026-08-02T00:30:00Z",   // 人工确认耗时 = confirmed_at - detected_at
  "severity": "P1",
  "confidence": 0.9,                  // 检测器自报置信度（校准误差 = |confidence - correctness|）
  "correctness": 1.0,                 // confirmed/false_positive 时的二值正确性
  "issue_start_at": "2026-08-02T00:00:00Z"  // MTTD 锚点：问题实际发生时间（detected_at - issue_start_at）
}
```

### 5.3 `QualityMetrics`（聚合输出）

```python
@dataclass
class QualityMetrics:
    precision: float    # TP / (TP + FP)
    recall: float       # TP / (TP + FN)
    noise_rate: float   # FP / total
    late_rate: float    # FN / total
    avg_mttd_hours: float          # 平均提前发现时间
    avg_confirm_mins: float        # 平均人工确认耗时
    calibration_error: float       # mean |confidence - correctness|
    n: int
```

维度键：`rule` / `model` / `product` / `tenant_id`（组合维度可选）。

### 5.4 `TuningRecommendation`

```python
@dataclass
class TuningRecommendation:
    rule: str
    dimension: str        # threshold|window|rule
    current: str
    suggested: str
    rationale: str
    impact: str           # 预期 precision/recall 变化
    approval_required: bool = True
    version: str = ""     # 落地后递增
```

## 6. 文件清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `docs/superpowers/specs/detection-quality-feedback-design.md` | 设计文档 | 本文档 |
| `qcloud-copilot/copilot/quality/feedback.py` | 实现 | `ReviewOutcome`/`OutcomeRecord`/`MetricsAgg`/`TuningAdvise`/`ApprovalGate` |
| `scripts/quality_feedback_aggregate.py` | 聚合 | 读 JSONL → QualityMetrics 表（按维度钻取） |
| `scripts/test_quality_feedback.py` | 测试 | TDD：outcome 记录、metrics 计算、校准误差、审批门禁、幂等 |

## 7. 函数签名

```python
# qcloud-copilot/copilot/quality/feedback.py
def record_outcome(record: dict, *, store_path: str | None = None) -> str:
    """记录一条 ReviewOutcome，以 finding_id 幂等追加/更新到 JSONL。返回 finding_id。"""

def compute_metrics(records: list[dict], *, by: str = "rule") -> dict[str, QualityMetrics]:
    """按 rule/model/product/tenant 维度聚合 precision/recall/noise/late/mttd/confirm/calib。"""

def tune_recommendation(metrics: QualityMetrics, *, rule: str, threshold_ctx: dict) -> TuningRecommendation:
    """基于 metrics 生成阈值/窗口/规则调优建议（只读，不落地）。"""

def apply_recommendation(rec: TuningRecommendation, *, approval_token: str) -> bool:
    """需审批 token 才能落地建议（复用 harness_safety 语义）。无 token 直接拒绝。"""
```

## 8. Self-check / 自验

- **TDD 红→绿**：先写 `test_quality_feedback.py`（失败），再实现 `feedback.py` / 聚合脚本（变绿）。
- Precision/Recall 用确定样本人工核对（如 4 命中 1 误报 1 漏报 → precision=4/5, recall=4/5）。
- 校准误差 = `mean(|confidence - correctness|)`，含边缘（confidence 缺失 → 跳过）。
- 幂等：同一 `finding_id` 二次 `record_outcome` 更新不重复。
- 审批门禁：无 approval_token 调 `apply_recommendation` → 拒绝（返回 False），不落地。
- 脱敏：JSONL 不含 SecretId/SecretKey/原始凭证。
- 门禁：`ruff check` 零 error；`pytest scripts/test_quality_feedback.py` 全绿；`validate_local.py` 不回归。

## 9. Phase 清单（PLAN）

- [ ] **Phase 0**: 写本文档（SPEC）。
- [ ] **Phase 1 (TDD 红)**: 写 `scripts/test_quality_feedback.py` 全部用例（含确定样本的 precision/recall 断言）。
- [ ] **Phase 2 (TDD 绿)**: 实现 `qcloud-copilot/copilot/quality/feedback.py` + `scripts/quality_feedback_aggregate.py`，跑测试转绿。
- [ ] **Phase 3**: ruff + 全量测试 + `validate_local.py` + SPEC 逐条对照。

## 10. DoD / 验收标准

- [ ] `ReviewOutcome` 四值可用，`record_outcome` 幂等。
- [ ] `compute_metrics` 按维度正确输出 precision/recall/noise/late/mttd/confirm/calibration_error。
- [ ] `tune_recommendation` 生成只读建议；`apply_recommendation` 无 token 拒绝。
- [ ] 确定样本测试断言数值精确（非仅键存在）。
- [ ] 无凭证/敏感信息写入 JSONL。
- [ ] `ruff check` 零 error、`pytest test_quality_feedback.py` 全绿、`validate_local.py` 不回归。
