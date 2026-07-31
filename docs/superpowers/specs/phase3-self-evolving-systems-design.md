# Phase 3: L4→L5 Self-Evolving Systems — 设计文档

> **Status**: Draft
> **Date**: 2026-08-01
> **Author**: bohaiqing
> **ADR**: ADR-0006

## 背景

Phase 2 完成后，系统已具备 L4 意图感知能力（自适应工作流、目标推理、自主编排、预测性安全）。Phase 3 探索 L5 Self-Evolving Systems，核心能力：

- 系统能自我修复——根据失败模式自动修改配置
- 系统能策略调优——基于历史数据调整门禁阈值
- 系统能工作流重构——从执行历史中优化 runbook
- 所有自主行为在治理框架约束下运行

**L5 的核心约束是 governance，不是无限制自主。**

---

## 3.1 自我修复闭环

### 3.1.1 现状

Phase 2 完成后，Reflexion Memory 记录了失败模式，CADL 沉淀了经验到文档。但修复仍然需要人工执行——系统只会"记录问题"，不会"修复问题"。

### 3.1.2 设计

**修复触发条件**：

同一 `(skill, error_code)` 在 30 天内出现 N 次（N 可配置，默认 5）。

**修复分级**：

| 级别 | 范围 | 示例 | 生成方式 | 审批 |
|:----:|------|------|----------|:----:|
| L1 | error table | 新增错误码、修正 recovery hint | 模板化（非 LLM） | 自动合并 |
| L2 | 默认参数 | 增加 `--ClientToken`、调整超时 | LLM 生成 | GCL Critic + Human review |
| L3 | 命令模板 | 调整 API 调用顺序、增加 pre-check | LLM 生成 | GCL Critic + Human approval |

**SelfHealEngine**：

```python
@dataclass
class FixProposal:
    level: str                         # "L1" | "L2" | "L3"
    skill: str
    error_code: str
    occurrence_count: int
    target_file: str                   # 要修改的文件路径
    old_content: str                   # 原始内容
    new_content: str                   # 修改后内容
    rationale: str                     # 修复理由
    risk_assessment: str               # 风险评估
    auto_merge: bool                   # 是否可自动合并

class SelfHealEngine:
    def analyze_failures(self) -> list[FixProposal]:
        """分析 failure-patterns.md + trace 历史，生成修复提案"""
    
    def generate_l1_fix(self, pattern) -> FixProposal:
        """模板化生成 L1 修复（新增错误码到 SKILL.md error table）"""
    
    def generate_l2_fix(self, pattern) -> FixProposal:
        """LLM 生成 L2 修复（修改默认参数）"""
    
    def generate_l3_fix(self, pattern) -> FixProposal:
        """LLM 生成 L3 修复（修改命令模板）"""
    
    def create_pr(self, proposal: FixProposal) -> str:
        """创建修复 PR，L1 自动合并，L2/L3 标记 needs-human-review"""
    
    def verify_fix(self, proposal: FixProposal) -> bool:
        """CI 验证: linter + 测试 + GCL dry-run"""
```

**修复验证**：
- L1: CI 自动验证（linter + 测试）
- L2: CI + GCL dry-run + Human review
- L3: CI + GCL dry-run + Human approval

### 3.1.3 文件变更

| 文件 | 变更 | 行数估计 |
|------|------|:------:|
| `scripts/self_heal_engine.py` | 新文件 | +200 |
| `scripts/reflexion_retrieve.py` | 新增 `get_high_frequency_patterns()` | +30 |

### 3.1.4 验收标准

- [ ] 同一 (skill, error) 出现 5 次 → 自动生成 L1 修复 PR
- [ ] L1 修复 PR 自动合并（CI 通过后）
- [ ] L2 修复 PR 创建后标记 `needs-human-review`
- [ ] L3 修复 PR 创建后标记 `needs-human-approval`
- [ ] 修复生效后 Reflexion 记忆自动去重

---

## 3.2 策略自主调优

### 3.2.1 现状

Phase 2 完成后，GCL rubric 阈值（Correctness ≥ 0.5, Safety = 1）和重试策略（2s/4s/8s）是静态配置。不同 skill 可能有不同的最优阈值。

### 3.2.2 设计

**调优范围**：

| 参数 | 当前值 | 调优方式 | 安全约束 |
|------|--------|----------|:--------:|
| Correctness 阈值 | 0.5 | 基于 skill 历史 PASS rate 动态 ±0.1 | 范围: [0.3, 0.8] |
| Idempotency 阈值 | 0.5 | 基于 destructive 操作历史调整 | 范围: [0.3, 0.8] |
| Traceability 阈值 | 0.5 | 基于 RequestId 缺失率调整 | 范围: [0.3, 0.8] |
| Spec Compliance 阈值 | 0.5 | 基于 spec violation 率调整 | 范围: [0.3, 0.8] |
| Safety 阈值 | 1.0 | **不可调整** | 固定 |
| Max Iterations | 2-5 | 基于 RETRY→PASS 概率调整 | 范围: [1, 10] |
| 重试退避 | 2s/4s/8s | 基于 API P50/P99 恢复时间 | 范围: [1s, 60s] |

**PolicyTuner**：

```python
@dataclass
class TuningProposal:
    parameter: str                     # "correctness_threshold"
    skill: str                         # "qcloud-cvm-ops"
    current_value: float
    proposed_value: float
    evidence: dict                     # 调优依据（PASS rate、错误分布等）
    risk: str                          # "low" | "medium"
    auto_apply: bool                   # 是否自动应用

class PolicyTuner:
    def analyze(self, traces: list[dict]) -> list[TuningProposal]:
        """分析 trace 历史，生成调优提案"""
    
    def apply(self, proposal: TuningProposal) -> None:
        """应用调优（写入 skill 的 rubric.md 或 gcl_runner 配置）"""
```

**调优流程**：
1. `gcl_trace_aggregate.py` 输出 30 天汇总数据
2. `PolicyTuner.analyze()` 检测可调优参数
3. 低风险调优（PASS rate 稳定 → 阈值小幅调整）→ 自动应用
4. 中风险调优（PASS rate 波动 → 阈值显著调整）→ 创建 ADR + Human review

### 3.2.3 文件变更

| 文件 | 变更 | 行数估计 |
|------|------|:------:|
| `scripts/policy_tuner.py` | 新文件 | +150 |
| `scripts/gcl_trace_aggregate.py` | 扩展: 输出调优所需的历史统计 | +30 |

### 3.2.4 验收标准

- [ ] 30 天内 CVM skill PASS rate 稳定在 95% → 自动降低 Correctness 阈值
- [ ] 30 天内 CVM skill RETRY→PASS 率低 → 自动增加 Max Iterations
- [ ] Safety 阈值保持 1.0 不变
- [ ] 中风险调优生成 ADR + Human review
- [ ] 调优变更记录在 skill 的 rubric.md changelog 中

---

## 3.3 工作流自主重构

### 3.3.1 现状

Phase 2 完成后，SKILL.md 中的 runbook（Pre-check → Execute → Verify → Recover）是人工编写的固定模板。同一操作在不同场景下可能需要不同的执行路径。

### 3.3.2 设计

**优化类型**：

| 类型 | 触发条件 | 实现 |
|------|----------|------|
| 合并 API 调用 | 同一 resource 的连续 Describe 调用 | 合并为批量查询 |
| 增加缓存 | 同一查询在 5 分钟内重复 3+ 次 | 缓存结果（TTL 5min） |
| 并行化 | 无依赖的 API 调用串行执行 | 改为 ThreadPoolExecutor 并行 |
| 提前失败 | 预检查失败概率 > 80% | 增加强制性 pre-check |
| 跳过冗余步骤 | 已验证的前置条件 | 跳过重复验证 |

**WorkflowOptimizer**：

```python
@dataclass
class WorkflowVariant:
    skill: str
    operation: str
    variant_id: str
    steps: list[RunbookStep]
    optimizations: list[str]           # 应用的优化类型
    baseline_metrics: dict             # 原 runbook 的指标
    variant_metrics: dict | None       # 变体的指标（A/B 测试后填充）

class WorkflowOptimizer:
    def analyze_traces(self, skill: str, operation: str) -> list[Optimization]:
        """分析 trace 历史，发现优化机会"""
    
    def generate_variant(self, skill: str, operation: str,
                         optimizations: list[Optimization]) -> WorkflowVariant:
        """生成优化 variant（LLM 辅助）"""
    
    def run_ab_test(self, variant: WorkflowVariant) -> dict:
        """A/B 测试: 原 runbook vs variant，对比成功率/耗时/错误率"""
    
    def promote_variant(self, variant: WorkflowVariant) -> None:
        """Variant 胜出 → 更新 SKILL.md runbook"""
```

**A/B 测试流程**：
1. 生成 variant，标记为 `experimental`
2. 并行运行原 runbook + variant（1 周，至少 50 次执行）
3. 对比指标：成功率、P50/P99 耗时、错误率
4. Variant 在所有指标上不差于原版 → 提升为正式 runbook
5. Variant 在任一指标上显著差于原版 → 废弃

### 3.3.3 文件变更

| 文件 | 变更 | 行数估计 |
|------|------|:------:|
| `scripts/workflow_optimizer.py` | 新文件 | +200 |
| `scripts/gcl_trace_aggregate.py` | 扩展: 输出 per-operation 统计 | +30 |

### 3.3.4 验收标准

- [ ] 检测到连续 Describe 调用 → 建议合并为批量查询
- [ ] 生成 variant → A/B 测试 1 周
- [ ] Variant 在成功率 + 耗时上不差于原版 → 提升为正式 runbook
- [ ] Variant 在任一指标上显著差 → 自动废弃
- [ ] Runbook 变更有完整的 trace 历史作为依据

---

## 3.4 治理框架下的完全自主

### 3.4.1 现状

Phase 2 完成后，安全门禁实现了风险分级（LOW/MEDIUM/HIGH/CRITICAL），但分级是硬编码的规则，不是可配置的策略框架。

### 3.4.2 设计

**AutonomyPolicy 分层**：

```python
@dataclass
class AutonomyPolicy:
    level: int                         # 0-3
    description: str
    rules: list[AutonomyRule]

@dataclass
class AutonomyRule:
    condition: str                     # "risk_level == 'LOW'"
    action: str                        # "auto_confirm" | "critic_review" | "human_token" | "human_approval"
    scope: list[str]                   # ["qcloud-cvm-ops", "qcloud-cdb-ops"]
    max_decisions_per_hour: int        # 速率限制
    require_audit: bool                # 是否写入审计日志

# Level 0 (Phase 1): 所有破坏性操作需 human token
LEVEL_0 = AutonomyPolicy(level=0, rules=[
    AutonomyRule(condition="is_destructive", action="human_token", scope=["*"])
])

# Level 1 (Phase 2): 低风险自动确认
LEVEL_1 = AutonomyPolicy(level=1, rules=[
    AutonomyRule(condition="risk_level == 'LOW'", action="auto_confirm", scope=["*"]),
    AutonomyRule(condition="risk_level == 'MEDIUM'", action="critic_review", scope=["*"]),
    AutonomyRule(condition="risk_level in ('HIGH', 'CRITICAL')", action="human_token", scope=["*"])
])

# Level 2 (Phase 3 早期): 中风险自动执行
LEVEL_2 = AutonomyPolicy(level=2, rules=[
    AutonomyRule(condition="risk_level in ('LOW', 'MEDIUM')", action="auto_confirm", scope=["*"]),
    AutonomyRule(condition="risk_level == 'HIGH'", action="critic_review", scope=["*"]),
    AutonomyRule(condition="risk_level == 'CRITICAL'", action="human_approval", scope=["*"])
])

# Level 3 (Phase 3 晚期): 仅最高风险需人工
LEVEL_3 = AutonomyPolicy(level=3, rules=[
    AutonomyRule(condition="risk_level in ('LOW', 'MEDIUM', 'HIGH')", action="auto_confirm", scope=["*"]),
    AutonomyRule(condition="risk_level == 'CRITICAL'", action="human_approval", scope=["*"]),
    AutonomyRule(condition="is_cross_system", action="human_token", scope=["*"])
])
```

**不可篡改审计日志**：

```python
@dataclass
class AutonomousDecision:
    decision_id: str
    timestamp: str
    autonomy_level: int
    operation: str
    resource_ids: list[str]
    risk_level: str
    action_taken: str                 # "auto_confirm" | "human_token" | ...
    rationale: str
    result: str                       # "success" | "failure" | "rolled_back"
    revocable_until: str              # ISO 8601, 5 分钟内可撤回

class AuditLogger:
    def log_decision(self, decision: AutonomousDecision) -> None:
        """写入 append-only audit log (.runtime/audit/decisions.jsonl)"""
    
    def generate_report(self, since: str) -> str:
        """生成自主决策报告"""
    
    def revoke(self, decision_id: str) -> bool:
        """撤回自主决策（5 分钟内有效）"""
```

### 3.4.3 文件变更

| 文件 | 变更 | 行数估计 |
|------|------|:------:|
| `scripts/autonomy_policy.py` | 新文件: AutonomyPolicy + AutonomyRule | +100 |
| `scripts/audit_logger.py` | 新文件: AutonomousDecision + AuditLogger | +120 |
| `scripts/harness_safety.py` | 修改: 集成 AutonomyPolicy | +30 |
| `scripts/evidence_kernel.py` | 修改: 集成 AuditLogger | +20 |

### 3.4.4 验收标准

- [ ] `--autonomy-level 0` → 所有破坏性操作需 human token
- [ ] `--autonomy-level 1` → LOW 自动确认，MEDIUM Critic 评审
- [ ] `--autonomy-level 2` → LOW/MEDIUM 自动确认，HIGH Critic 评审
- [ ] `--autonomy-level 3` → 仅 CRITICAL 需 human approval
- [ ] 每次自主决策写入 audit log
- [ ] 5 分钟内可撤回自主决策
- [ ] 跨系统操作在任何 level 下都需 human token

---

## 自验证

```python
# 3.1: 自我修复
engine = SelfHealEngine()
proposals = engine.analyze_failures()
assert all(p.level in ("L1", "L2", "L3") for p in proposals)
assert all(p.auto_merge == (p.level == "L1") for p in proposals)

# 3.2: 策略调优
tuner = PolicyTuner()
proposals = tuner.analyze(traces)
for p in proposals:
    if p.parameter == "safety":
        assert p.proposed_value == 1.0  # Safety 永远不变

# 3.3: 工作流优化
optimizer = WorkflowOptimizer()
opts = optimizer.analyze_traces("qcloud-cvm-ops", "DescribeInstances")
assert any(o.type == "merge_calls" for o in opts)  # 连续调用可合并

# 3.4: 治理框架
policy = LEVEL_0
assert policy.evaluate("TerminateInstances", risk="LOW").action == "human_token"
policy = LEVEL_2
assert policy.evaluate("TerminateInstances", risk="MEDIUM").action == "auto_confirm"
assert policy.evaluate("DeleteVpc", risk="CRITICAL").action == "human_approval"
```

## 文件清单

| 文件 | 操作 | 说明 |
|------|:----:|------|
| `scripts/self_heal_engine.py` | 新增 | SelfHealEngine |
| `scripts/policy_tuner.py` | 新增 | PolicyTuner |
| `scripts/workflow_optimizer.py` | 新增 | WorkflowOptimizer |
| `scripts/autonomy_policy.py` | 新增 | AutonomyPolicy |
| `scripts/audit_logger.py` | 新增 | AuditLogger |
| `scripts/reflexion_retrieve.py` | 修改 | get_high_frequency_patterns() |
| `scripts/gcl_trace_aggregate.py` | 修改 | 扩展历史统计 |
| `scripts/harness_safety.py` | 修改 | 集成 AutonomyPolicy |
| `scripts/evidence_kernel.py` | 修改 | 集成 AuditLogger |
