# ADR-0006: Phase 3 — L4→L5 Self-Evolving Systems 探索

> **Status**: Proposed
> **Date**: 2026-08-01
> **Deciders**: Architecture review (bohaiqing)
> **Supersedes**: —
> **Related**: ADR-0004 (Phase 1), ADR-0005 (Phase 2)

## 1. Context

Phase 2 完成后，系统已具备 L4 意图感知能力（自适应工作流、目标推理、自主编排、预测性安全）。Phase 3 的目标是探索 L5（Self-Evolving Systems），核心特征是：

- 系统能**自我修复**——根据失败模式自动修改 skill 配置和参数
- 系统能**策略自主调优**——基于历史数据调整质量门禁阈值
- 系统能**工作流自主重构**——从执行历史中优化 runbook 步骤
- 所有自主行为在**治理框架**约束下运行

L5 的定义是"在治理策略范围内完全自主运营"，关键约束是 governance，不是无限制的自主。

## 2. Decision

### 2.1 四个模块

| # | 模块 | 目标 | 优先级 |
|---|------|------|:------:|
| 3.1 | **自我修复闭环** | 高频失败模式自动生成修复 PR | P0 |
| 3.2 | **策略自主调优** | Rubric 阈值 + 重试策略基于历史数据自动调整 | P1 |
| 3.3 | **工作流自主重构** | Runbook 从执行历史中持续优化 | P1 |
| 3.4 | **治理框架下的完全自主** | AutonomyPolicy 分层治理 | P0 |

### 2.2 关键架构决策

#### 2.2.1 自我修复闭环

**选择**：失败模式达到阈值（同一 skill + error 出现 N 次）→ 自动生成修复 PR。修复分三级：

| 级别 | 范围 | 示例 | 审批要求 |
|:----:|------|------|:--------:|
| L1 | 更新 error table | 新增错误码、修正 recovery hint | 自动合并 |
| L2 | 修改默认参数 | 增加 `--ClientToken`、调整超时 | GCL Critic + Human review |
| L3 | 修改命令模板 | 调整 API 调用顺序、增加 pre-check | GCL Critic + Human approval |

**实现方式**：
- 修复内容由 LLM 生成（读取 SKILL.md + failure-patterns.md + trace 历史）
- L1 修复自动创建 PR 并合并（经 CI 验证）
- L2/L3 修复创建 PR 后标记 `needs-human-review`
- 修复生效后自动更新 Reflexion 记忆（去重）

**弃选方案**：
- ❌ 全自动修复 — L2/L3 级别修改有回归风险，不可无人审查
- ❌ 全人工修复 — L1 级别修改量大（预计每月 10+ 次），人工不可持续

#### 2.2.2 策略自主调优

**选择**：从 `gcl_trace_aggregate.py` 历史数据中学习最优阈值和重试策略。

**调优范围**：
| 参数 | 当前值 | 调优方式 |
|------|--------|----------|
| Correctness 阈值 | 0.5 | 基于 skill 历史 PASS rate 动态 ±0.1 |
| Max Iterations | 2 (destructive) / 3-5 (advisory) | 基于 RETRY→PASS 概率调整 |
| 重试退避 | 2s, 4s, 8s | 基于 API 实际恢复时间调整 |
| Structural Critic fallback 触发条件 | LLM 超时 | 基于 LLM API P99 延迟调整 |

**安全约束**：
- Safety 阈值永远 = 1.0（不可调整）
- 阈值调优有最大变化范围（±20%）
- 每次调整记录 ADR
- 调整需 human review 后生效

#### 2.2.3 工作流自主重构

**选择**：分析 trace 历史，识别 runbook 瓶颈，自动生成优化 variant。

**优化类型**：
| 类型 | 触发条件 | 示例 |
|------|----------|------|
| 合并 API 调用 | 同一 resource 的连续 Describe 调用 | 一次 DescribeInstances 替代多次单实例查询 |
| 增加缓存 | 同一查询在 5 分钟内重复 3+ 次 | 缓存 DescribeImages 结果 5 分钟 |
| 并行化 | 无依赖的 API 调用串行执行 | VPC + SG + Image 预检查并行 |
| 提前失败 | 预检查失败概率 > 80% | 在 RunInstances 前强制 VPC/Quota 预检查 |

**A/B 测试机制**：
- 优化 variant 与原 runbook 并行运行 1 周
- 对比成功率、耗时、错误率
- 优化 variant 胜出 → 替换原 runbook

#### 2.2.4 治理框架下的完全自主

**选择**：定义 `AutonomyPolicy` 分层治理。

**策略分层**：
```
Level 0 (Phase 1): 所有破坏性操作需 human token
Level 1 (Phase 2): 低风险破坏性操作自动确认
Level 2 (Phase 3 早期): 中等风险操作经 Critic 评审后自动执行
Level 3 (Phase 3 晚期): 仅高风险/跨系统/不可逆操作需 human approval
```

**不可篡改审计日志**：
- 每次自主决策记录到 append-only audit log
- 包含: timestamp, decision_id, autonomy_level, operation, risk_assessment, rationale
- 定期生成自主决策报告，供 human 审计

**自主决策撤回机制**：
- 任何自主决策可在 5 分钟内通过 `--revoke <decision_id>` 撤回
- 撤回后自动执行回滚操作（如果已执行）

## 3. Consequences

### Positive
- 运维人力从重复性修复中解放（L1 自动修复）
- 质量门禁从静态变为数据驱动（策略调优）
- Runbook 持续进化，不再依赖人工优化（工作流重构）
- 自主能力在治理框架约束下渐进开放，风险可控

### Negative
- 自动修复可能引入回归（L2/L3 级别）
- 策略调优可能过拟合历史数据
- 工作流自主重构的 A/B 测试需要额外资源
- 治理框架本身可能成为瓶颈

### Mitigation
- L2/L3 修复必须 human review
- 策略调优有安全约束和变化范围限制
- A/B 测试在隔离环境运行，不影响生产
- 治理框架分层，Level 0-1 默认安全，Level 2-3 逐步开放

## 4. Status Tracking

| 文档 | 路径 | 状态 |
|------|------|:----:|
| Spec | `docs/superpowers/specs/phase3-self-evolving-systems-design.md` | Draft |
| Plan | `docs/superpowers/plans/phase3-self-evolving-systems-plan.md` | Draft |
| ADR | 本文档 | Proposed |
