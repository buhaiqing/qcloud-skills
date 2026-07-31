# ADR-0005: Phase 2 — L3→L4 Intent-Aware Systems 跃迁

> **Status**: Proposed
> **Date**: 2026-08-01
> **Deciders**: Architecture review (bohaiqing)
> **Supersedes**: —
> **Related**: ADR-0004 (Phase 1), ADR-0002 (L3→L4 daemon)

## 1. Context

Phase 1 补齐 L3 基础能力（LLM Critic、SkillRegistry、ErrorEscalator、统一观测面）后，系统已具备自适应编排的基础设施。Phase 2 的目标是跃迁到 L4（Intent-Aware Systems），核心特征是：

- 系统能根据运行时中间结果**动态调整**执行计划（而非预生成固定 DAG）
- 系统能**推断用户的高层目标**并主动提出方案（而非仅执行显式指令）
- 系统能**自主选择**跨 skill 编排模式（而非 agent 手动选择）
- 安全门禁从**关键词匹配**升级为**上下文感知**的风险评估

## 2. Decision

### 2.1 四个模块

| # | 模块 | 目标 | 优先级 |
|---|------|------|:------:|
| 2.1 | **自适应工作流引擎** | PlanDispatcher 支持条件分支 + 动态 plan revision | P0 |
| 2.2 | **意图驱动的目标推理** | Copilot Classifier 增加目标推理层 | P0 |
| 2.3 | **跨 Skill 自主编排** | OrchestrationSelector 自动匹配编排模式 | P1 |
| 2.4 | **预测性安全门禁** | 上下文感知的影响面评估 | P1 |

### 2.2 关键架构决策

#### 2.2.1 自适应工作流引擎

**选择**：扩展 `ExecutionPlan` 支持条件分支（`condition` 字段），PlanDispatcher 在每个 step 后评估条件并动态调整。

**实现方式**：
```json
{
  "steps": [
    {"id": "diagnose", "skill": "qcloud-aiops-diagnosis", ...},
    {"id": "fix-vpc", "skill": "qcloud-vpc-ops",
     "condition": "{{output.diagnose.error_code}} == 'InvalidVpc.NotFound'",
     "depends_on": ["diagnose"]},
    {"id": "skip-vpc", "type": "noop",
     "condition": "{{output.diagnose.error_code}} != 'InvalidVpc.NotFound'",
     "depends_on": ["diagnose"]}
  ]
}
```

**弃选方案**：
- ❌ 完全动态生成（无预定义结构） — 不可审计，调试困难
- ❌ 仅 LLM 生成 plan — 幻觉风险，缺少结构化约束

#### 2.2.2 意图驱动的目标推理

**选择**：在 Copilot Classifier 之上增加 `GoalInference` 层，将模糊查询映射为目标 + 候选 skill 链。

**架构**：
```
用户查询: "这台机器最近很慢"
  → GoalInference.infer(query)
  → {goal: "diagnose_performance", candidates: [
       {chain: [CVM_Monitor, TKE_Monitor, CDB_SlowQuery], risk: "low"},
       {chain: [AIOps_Full_Diagnosis], risk: "medium"}
     ]}
  → 生成多方案供用户选择
```

**弃选方案**：
- ❌ 完全自动执行（不询问用户） — 高风险操作不可接受
- ❌ 仅关键词匹配 — 无法处理模糊语义

#### 2.2.3 跨 Skill 自主编排

**选择**：将 `cross-skill-orchestration.md` 中的 F1/F2/P1/A1/A2 模式建模为 `OrchestrationPattern`，`OrchestrationSelector` 根据 Blackboard 状态自动匹配。

**触发条件示例**：
- FinOps 发现成本异常 + CPU 高 → 匹配 F1 → 触发 Proactive Inspection → AIOps RCA
- Inspection 发现 CRITICAL 安全配置 → 匹配 P1 → 触发 AIOps 深度诊断

#### 2.2.4 预测性安全门禁

**选择**：扩展 `harness_safety.py` 增加依赖图分析。删除 CVM 前自动检查关联资源（CLB 监听器、CDB 只读副本、安全组引用），影响面注入到 human confirmation 提示。

**风险分级**：
| 风险等级 | 操作特征 | 确认要求 |
|:--------:|----------|----------|
| LOW | 删除未挂载空磁盘、查询只读操作 | 自动确认 |
| MEDIUM | 停止非生产实例、修改标签 | Critic 评审后自动确认 |
| HIGH | 删除生产实例、修改 VPC 路由 | Human token 确认 |
| CRITICAL | 删除 VPC、销毁数据库、修改 IAM | Human token + 影响面报告确认 |

## 3. Consequences

### Positive
- 系统从"执行命令"升级到"理解目标"，用户体验质变
- 跨 skill 编排自动化，减少 agent 手动选择错误
- 安全门禁上下文感知，减少误报和漏报

### Negative
- 目标推理可能产生不准确方案（LLM 幻觉风险）
- 条件分支增加 plan 执行的不确定性，调试难度增大
- 依赖图分析需要维护资源拓扑（CVM→CLB→VPC→SG 关系）

### Mitigation
- 目标推理结果始终呈现多方案，由用户最终选择
- 条件分支有最大嵌套深度限制（默认 3 层）
- 依赖图分析从 `tccli` API 返回数据中实时构建，不维护静态拓扑

## 4. Status Tracking

| 文档 | 路径 | 状态 |
|------|------|:----:|
| Spec | `docs/superpowers/specs/phase2-intent-aware-systems-design.md` | Draft |
| Plan | `docs/superpowers/plans/phase2-intent-aware-systems-plan.md` | Draft |
| ADR | 本文档 | Proposed |
