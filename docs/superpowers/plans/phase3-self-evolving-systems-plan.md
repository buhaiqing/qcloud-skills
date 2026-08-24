# Plan: Phase 3 — L4→L5 Self-Evolving Systems 探索

> **Status**: Draft
> **Date**: 2026-08-01
> **Spec**: `docs/superpowers/specs/phase3-self-evolving-systems-design.md`
> **ADR**: `docs/architecture/ADR-0006-phase3-self-evolving-systems.md`

---

## Phase 3.1: 自我修复闭环（P0）

### Step 3.1.1 — SelfHealEngine 实现

- [ ] 新增 `scripts/self_heal_engine.py`
  - `FixProposal` dataclass
  - `SelfHealEngine` 类: analyze_failures / generate_l1_fix / generate_l2_fix / generate_l3_fix / create_pr / verify_fix
  - 触发阈值: 同一 (skill, error) 30 天内出现 5 次
  - L1 修复: 模板化（非 LLM），新增错误码到 SKILL.md error table
  - L2/L3 修复: LLM 生成
  - **DoD**: `ruff check` 零 error；`test_self_heal.py` 通过

### Step 3.1.2 — Reflexion 高频模式提取

- [ ] 修改 `scripts/reflexion_retrieve.py`
  - 新增 `get_high_frequency_patterns(min_occurrences=5, days=30)` 方法
  - 返回满足阈值的 (skill, error_code) 列表
  - **DoD**: 集成测试验证阈值逻辑

### Step 3.1.3 — PR 自动创建与验证

- [ ] SelfHealEngine 集成 GitHub API
  - L1: 自动创建 PR → CI 验证 → 自动合并
  - L2: 自动创建 PR → 标记 `needs-human-review`
  - L3: 自动创建 PR → 标记 `needs-human-approval`
  - **DoD**: L1 修复 PR 自动创建并合并（CI 通过后）

### Step 3.1.4 — 测试

- [ ] 新增 `test_self_heal.py`
  - L1 修复生成正确性
  - L2/L3 修复生成正确性
  - 阈值触发逻辑
  - 修复验证逻辑
  - **DoD**: 4+ 个测试通过

---

## Phase 3.2: 策略自主调优（P1）

### Step 3.2.1 — PolicyTuner 实现

- [ ] 新增 `scripts/policy_tuner.py`
  - `TuningProposal` dataclass
  - `PolicyTuner` 类: analyze / apply
  - Safety 阈值硬编码 1.0（不可调优）
  - 调优范围约束（±20% 最大变化）
  - **DoD**: `ruff check` 零 error

### Step 3.2.2 — Trace 历史统计扩展

- [ ] 修改 `scripts/gcl_trace_aggregate.py`
  - 新增 `--tuning-input` 模式: 输出调优所需的历史统计
  - 包含 per-skill PASS rate / RETRY→PASS rate / 阈值违规频率
  - **DoD**: `gcl_trace_aggregate.py --tuning-input --since-days 30` 输出完整统计

### Step 3.2.3 — 调优应用

- [ ] PolicyTuner.apply() 实现
  - 低风险调优: 自动写入 skill rubric.md
  - 中风险调优: 生成 ADR + Human review
  - 调优变更记录到 rubric.md changelog
  - **DoD**: 低风险调优自动应用并记录

### Step 3.2.4 — 测试

- [ ] 新增 `test_policy_tuner.py`
  - Safety 阈值不可调整
  - 阈值调优范围约束
  - 低风险自动应用 vs 中风险 human review
  - **DoD**: 3+ 个测试通过

---

## Phase 3.3: 工作流自主重构（P1）

### Step 3.3.1 — WorkflowOptimizer 实现

- [ ] 新增 `scripts/workflow_optimizer.py`
  - `WorkflowVariant` dataclass
  - `WorkflowOptimizer` 类: analyze_traces / generate_variant / run_ab_test / promote_variant
  - 5 种优化类型: merge_calls / add_cache / parallelize / early_fail / skip_redundant
  - **DoD**: `ruff check` 零 error

### Step 3.3.2 — A/B 测试框架

- [ ] A/B 测试实现
  - Variant 与原 runbook 并行运行
  - 对比指标: 成功率、P50/P99 耗时、错误率
  - 测试周期: 1 周，至少 50 次执行
  - 自动决策: variant 在所有指标上不差 → 提升；任一指标显著差 → 废弃
  - **DoD**: A/B 测试完整流程可用

### Step 3.3.3 — 测试

- [ ] 新增 `test_workflow_optimizer.py`
  - 连续调用检测
  - Variant 生成正确性
  - A/B 测试决策逻辑
  - **DoD**: 3+ 个测试通过

---

## Phase 3.4: 治理框架下的完全自主（P0）

### Step 3.4.1 — AutonomyPolicy 实现

- [x] 新增 `scripts/autonomy_policy.py`
  - `AutonomyPolicy` + `AutonomyRule` dataclass
  - 4 个策略等级: LEVEL_0 → LEVEL_3
  - 策略评估: `policy.evaluate(operation, risk_level, is_cross_system)`
  - **DoD**: `ruff check` 零 error

### Step 3.4.2 — AuditLogger 实现

- [x] 新增 `scripts/audit_logger.py`
  - `AutonomousDecision` dataclass
  - `AuditLogger` 类: log_decision / generate_report / revoke
  - 持久化: `.runtime/audit/decisions.jsonl` (append-only)
  - 撤回窗口: 5 分钟
  - **DoD**: 自主决策写入审计日志；5 分钟内可撤回

### Step 3.4.3 — harness_safety.py 集成

- [x] 修改 `scripts/harness_safety.py`
  - 集成 `AutonomyPolicy.evaluate()`
  - `evaluate_autonomy()` 导出函数
  - **DoD**: 4 个 autonomy level 行为正确

### Step 3.4.4 — 测试

- [x] 新增 `test_autonomy_policy.py`
  - LEVEL_0: 所有破坏性操作需 human token
  - LEVEL_1: LOW 自动确认，MEDIUM Critic 评审
  - LEVEL_2: LOW/MEDIUM 自动确认，HIGH Critic 评审
  - LEVEL_3: 仅 CRITICAL 需 human approval
  - 跨系统操作在任何 level 下需 human token
  - **DoD**: 5+ 个测试通过

- [x] 新增 `test_audit_logger.py`
  - 决策记录写入
  - 报告生成
  - 撤回机制
  - **DoD**: 3+ 个测试通过

---

## 执行顺序

```
Month 1-2: 3.1 (自我修复) + 3.4 (治理框架) 并行
Month 3-4: 3.2 (策略调优) + 3.3 (工作流重构) 串行
Month 5-6: 集成测试 + A/B 测试验证 + 文档更新 + 验收
```

## 里程碑验收

### M1: 自我修复 + 治理框架就绪（Month 2）

- [ ] 高频失败模式自动生成 L1 修复 PR 并合并
- [ ] `--autonomy-level 0-3` 行为正确
- [ ] 自主决策审计日志完整

### M2: 策略调优 + 工作流重构就绪（Month 4）

- [ ] Safety 阈值保持 1.0 不变
- [ ] 低风险调优自动应用
- [ ] 工作流 variant A/B 测试完成

### M3: Phase 3 整体验收（Month 6）

- [ ] 系统在治理框架约束下运行 30 天无事故
- [ ] L1 自动修复至少 3 次成功合并
- [ ] 至少 1 个 runbook variant 通过 A/B 测试并提升
- [ ] 所有新增测试通过；回归测试零 failure
- [ ] ADR、Spec、Plan 文档状态更新为 Accepted / Complete
