# P0-4: 修复后验证闭环（Post-Fix Verification Loop）设计

> 状态：Draft · 关联 Plan：`docs/superpowers/plans/2026-07-25-aiops-optimization-todo.md` §P0-4
> 前置：P0-3 `incident_state.py`（IncidentStateMachine/action_state）已落地；P0-2 `quality/feedback.py` 已落地。本设计定义 mutation action 的修复后验证，消费 incident 的 `action_state` 与指标窗口。

## 1. 背景与问题

当前 mutation action（修复/处置）**无修复后验证闭环**：

- 无法确认"修复动作是否真的让业务/健康指标恢复"。
- 只有 API 调用成功（`returncode==0`）的隐式信号，无业务指标对比。
- 无 `verification_status`、恢复幅度、残余风险、回滚建议的输出。
- 无法区分"API 调用成功"和"业务/健康指标恢复"（两回事）。
- 验证失败时无自动升级/重试/回滚到人工审批队列的机制。

**核心缺口**：没有一个 `VerificationEvaluator` 能回答「修复动作做了，但指标到底恢复没有、恢复到什么程度、要不要回滚」。

## 2. 目标

- 为每类处置动作定义只读验证器和验证指标窗口。
- 对比事件前、事件中、修复后指标，支持恢复阈值和稳定观察窗口。
- 输出 `verification_status`、恢复幅度、残余风险和回滚建议。
- 区分"API 调用成功"和"业务/健康指标恢复"。
- 验证失败时自动升级、重试或回滚到人工审批队列。
- 验收：任何 mutation action 都必须有明确的验证结果或显式无法验证原因。

## 3. 非目标

- 不执行实际的修复/处置动作（本模块是验证层，不是执行层）。
- 不实现 P0-3 状态机转移（本模块消费 `action_state`，只输出 `verification_status`）。
- 不实现 P0-5 SLO 排序。

## 4. 架构

```
   mutation action (修复/处置)
          │
          ▼
   ┌──────────────────────────────┐
   │   VerificationEvaluator (新)  │
   │  ┌────────────────────────┐  │
   │  │ pre/fix/post 指标对比   │  │  事件前(pre) / 事件中(impact) / 修复后(post)
   │  │ recovery_threshold     │  │  恢复阈值 + 稳定观察窗口
   │  │ verification_status    │  │  verified / recovered / partial / failed / unverifiable
   │  │ rollback_suggested     │  │  残余风险 + 回滚建议
   │  │ api_success vs health  │  │  区分 API 成功 与 指标恢复
   │  │ escalation policy      │  │  验证失败 → retry/escalate/rollback
   │  └────────────────────────┘  │
   └──────────────┬───────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
   verification_status   人工审批队列(rollback)
   (JSONL/报告)
```

**关键决策**：
- **纯函数可回放**：`evaluate(pre, impact, post, threshold)` 返回 `VerificationResult`（dataclass），不 mutate。
- **区分两件事**：`api_success`（动作调用返回 0）与 `health_recovered`（指标恢复到阈值内）是两个独立布尔；`verification_status` 综合二者。
- **验证窗口**：`stable_window_min` — 指标需在恢复后持续稳定 N 分钟才算 `recovered`，防瞬时抖动。

## 5. 数据模型

### 5.1 `VerificationStatus`（枚举）

```python
class VerificationStatus(str, Enum):
    VERIFIED = "verified"          # api_success 且 health_recovered
    RECOVERED = "recovered"        # health_recovered（不管 api_success，如手动修复）
    PARTIAL = "partial"            # 部分指标恢复
    FAILED = "failed"              # 未恢复，需重试/回滚
    UNVERIFIABLE = "unverifiable"  # 缺指标数据，无法验证（显式原因）
```

### 5.2 `VerificationResult`

```python
@dataclass
class VerificationResult:
    verification_status: VerificationStatus
    api_success: bool
    health_recovered: bool
    recovery_magnitude: float       # 修复后 vs 事件中 的恢复幅度 (0~1+)
    residual_risk: str              # 残余风险描述
    rollback_suggested: bool
    action: str                     # 原处置动作
    reason: str                     # 状态判定理由 / 显式无法验证原因
```

### 5.3 `VerificationSample`

```python
@dataclass
class VerificationSample:
    pre_value: float       # 事件前基线
    impact_value: float    # 事件中/峰值
    post_value: float      # 修复后
    threshold: float       # 恢复阈值（健康上限/下限）
    direction: str         # "upper"（高于此算恢复，如可用性）| "lower"（低于此算恢复，如延迟/错误率）
    stable_window_min: int = 15   # 稳定观察窗口（分钟）
    unit: str = ""         # 可选单位
```

## 6. 文件清单

| 文件 | 类型 | 说明 |
|---|---|---|
| `docs/superpowers/specs/post-fix-verification-design.md` | 设计文档 | 本文档 |
| `qcloud-copilot/copilot/verification.py` | 实现 | `VerificationStatus`/`VerificationResult`/`VerificationSample`/`VerificationEvaluator`/`evaluate`/`escalation_decision` |
| `scripts/verification_aggregate.py` | 聚合 | 读 JSONL → verification_status 分布表 + failed 清单 |
| `scripts/test_verification.py` | 测试 | 状态判定/阈值/窗口/api_vs_health/残余风险/回滚/升级 |

## 7. 函数签名

```python
# qcloud-copilot/copilot/verification.py
class VerificationEvaluator:
    def evaluate(self, sample: VerificationSample, *, api_success: bool) -> VerificationResult:
        """综合 api_success + health 指标对比 → VerificationResult。不 mutate。"""

    def is_recovered(self, sample: VerificationSample) -> bool:
        """按 direction + threshold 判断 post 是否恢复到健康区。"""

def escalation_decision(result: VerificationResult, *, max_retries: int = 2) -> str:
    """验证失败时的升级策略：retry / escalate / rollback / ok。"""

def recovery_magnitude(sample: VerificationSample) -> float:
    """恢复幅度 = (post - impact)/(pre - impact) 或按方向归一，clamp 到 [0, 2]。
    无法计算（分母 0 或缺数据）→ 0.0。"""
```

## 8. Self-check / 自验

- **状态判定完备**：穷举 `api_success × health_recovered × direction × threshold` 组合 → 正确的 `VerificationStatus`。
- **api vs health 分离**：api_success=False 但 health_recovered=True（手动修复）→ `recovered`；api_success=True 但 health_recovered=False → `failed`/`partial`。
- **恢复幅度**：已知样本断言精确值（如 pre=100, impact=50, post=90 → magnitude=0.8）。
- **稳定窗口**：仅 post 在窗口内持续达标才算 recovered（测试用 stable_window_min=0 简化，或 mock 时间）。
- **升级策略**：failed + 重试耗尽 → rollback；partial → escalate；verified/recovered → ok。
- **脱敏**：JSONL 不含 SecretId/SecretKey。
- 门禁：ruff 零 error；pytest 全绿；`validate_local.py` 不回归。

## 9. Phase 清单（PLAN）

- [ ] **Phase 0**: 写本文档（SPEC）。
- [ ] **Phase 1 (TDD 红)**: 写 `scripts/test_verification.py`。
- [ ] **Phase 2 (TDD 绿)**: 实现 `qcloud-copilot/copilot/verification.py` + `scripts/verification_aggregate.py`，转绿。
- [ ] **Phase 3**: ruff + 全量测试 + SPEC 逐条对照。

## 10. DoD / 验收标准

- [ ] 只读验证器 + 指标窗口可判定 verified/recovered/partial/failed/unverifiable。
- [ ] 输出 `verification_status`、恢复幅度、残余风险、回滚建议。
- [ ] 明确区分 API 成功 vs 健康恢复。
- [ ] 验证失败自动升级/重试/回滚策略可测。
- [ ] 无凭证/敏感信息写入 JSONL。
- [ ] ruff 零 error、pytest 全绿、`validate_local.py` 不回归。
