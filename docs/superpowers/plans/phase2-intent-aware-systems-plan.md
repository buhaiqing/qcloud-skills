# Phase 2: L3→L4 Intent-Aware Systems — 开发计划

> **Status**: Draft
> **Date**: 2026-08-01
> **Spec**: `docs/superpowers/specs/phase2-intent-aware-systems-design.md`
> **ADR**: `docs/architecture/ADR-0005-phase2-intent-aware-systems.md`

---

## Phase 2.1: 自适应工作流引擎（P0）

### Step 2.1.1 — ExecutionPlan 扩展

- [ ] 修改 `qcloud-copilot/copilot/models.py`
  - PlanStep 新增 `condition: Condition | None`, `discovery: bool`, `max_revisions: int`
  - 新增 `Condition` dataclass（expression, true_branch, false_branch）
  - **DoD**: `ruff check` 零 error；`test_models.py` 通过

### Step 2.1.2 — 条件分支执行

- [ ] 修改 `qcloud-copilot/copilot/dispatcher.py`
  - `_execute_step()` 增加条件评估
  - Jinja2 模板渲染（读取 Blackboard 上下文）
  - 动态插入 true_branch / false_branch step
  - 最大嵌套深度限制: 3 层
  - **DoD**: 集成测试验证条件分支逻辑

### Step 2.1.3 — Plan Revision

- [ ] 修改 `qcloud-copilot/copilot/dispatcher.py` 和 `planner.py`
  - `discovery` step 执行后触发 `plan_revision()`
  - `planner.replan()` 基于新发现重新规划剩余步骤
  - 安全约束: 不可撤销已完成的步骤
  - 最大 revision 次数: 3
  - **DoD**: discovery step 发现新错误码 → 剩余步骤重新规划

### Step 2.1.4 — 测试

- [ ] 新增 `test_adaptive_workflow.py`
  - 条件分支 true 路径
  - 条件分支 false 路径
  - Plan revision 正确性
  - 最大 revision 次数限制
  - 安全约束: 已完成步骤不可撤销
  - **DoD**: 5+ 个测试通过

---

## Phase 2.2: 意图驱动的目标推理（P0）

### Step 2.2.1 — GoalInference 实现

- [ ] 新增 `qcloud-copilot/copilot/goal_inference.py`
  - `InferredGoal` + `SkillChain` dataclass
  - `GoalInference` 类: infer() 方法
  - LLM 调用 + SkillRegistry 匹配 + 风险评估
  - 安全约束: 破坏性方案标注 risk + 警告
  - **DoD**: `ruff check` 零 error

### Step 2.2.2 — Classifier 集成

- [ ] 修改 `qcloud-copilot/copilot/classifier.py`
  - 模糊查询（confidence < 阈值）→ 触发 GoalInference
  - 明确指令（confidence > 阈值）→ 走现有分类逻辑
  - **DoD**: 模糊查询走目标推理，明确指令走现有逻辑

### Step 2.2.3 — Engine 集成

- [ ] 修改 `qcloud-copilot/copilot/engine.py`
  - `ask()` 增加目标推理路径
  - 多方案呈现 → 用户选择 → 生成 ExecutionPlan
  - **DoD**: "这台机器最近很慢" → 多方案 → 用户选择 → 执行

### Step 2.2.4 — 测试

- [ ] 新增 `test_goal_inference.py`
  - 模糊查询返回多方案
  - 破坏性方案标注风险
  - 低置信度返回 clarifying_questions
  - Skill 链验证
  - **DoD**: 4+ 个测试通过

---

## Phase 2.3: 跨 Skill 自主编排（P1）

### Step 2.3.1 — OrchestrationSelector 实现

- [ ] 新增 `qcloud-copilot/copilot/orchestration.py`
  - `OrchestrationPattern` dataclass
  - `OrchestrationSelector` 类: select() 方法
  - 5 种模式定义（F1, F2, P1, A1, A2）
  - Specificity 排序: 条件最多的模式优先
  - **DoD**: `ruff check` 零 error

### Step 2.3.2 — Engine 集成

- [ ] 修改 `qcloud-copilot/copilot/engine.py`
  - Plan generation 前调用 `OrchestrationSelector.select()`
  - 匹配到模式 → 使用模式 skill_chain
  - 无匹配 → 回退到默认 plan generation
  - 模式执行失败 → fallback_pattern
  - **DoD**: FinOps HIGH → 自动 F1

### Step 2.3.3 — 测试

- [ ] 新增 `test_orchestration.py`
  - F1 触发条件匹配
  - P1 触发条件匹配
  - 多模式冲突 → specificity 选择
  - 无匹配 → None
  - **DoD**: 4+ 个测试通过

---

## Phase 2.4: 预测性安全门禁（P1）

### Step 2.4.1 — ImpactAnalyzer 实现

- [ ] 新增 `scripts/impact_analyzer.py`
  - `ImpactAssessment` + `AffectedResource` dataclass
  - `ImpactAnalyzer.assess()` 方法
  - 依赖图分析: CVM → CLB / CDB / SG / Disk / EIP
  - 风险分级: LOW / MEDIUM / HIGH / CRITICAL
  - **DoD**: `ruff check` 零 error

### Step 2.4.2 — harness_safety.py 集成

- [ ] 修改 `scripts/harness_safety.py`
  - `is_destructive()` 后调用 `ImpactAnalyzer.assess()`
  - 返回风险等级 + 影响面
  - LOW → 自动确认
  - MEDIUM → Critic 评审后自动确认
  - HIGH → Human token
  - CRITICAL → Human token + 影响面报告
  - **DoD**: 风险分级确认逻辑正确

### Step 2.4.3 — evidence_kernel.py 增强

- [ ] 修改 `scripts/evidence_kernel.py`
  - human confirmation 提示增加影响面报告
  - 包含关联资源列表 + 建议预操作步骤
  - **DoD**: human confirmation 提示包含完整影响面

### Step 2.4.4 — 测试

- [ ] 新增 `test_impact_analyzer.py`
  - 无关联资源 → LOW
  - 2 个关联资源 → MEDIUM
  - 5+ 个关联资源 → HIGH/CRITICAL
  - 影响面报告完整性
  - **DoD**: 4+ 个测试通过

---

## 执行顺序

```
Month 1: 2.1 (自适应工作流) + 2.2 (目标推理) 并行
Month 2: 2.3 (自主编排) + 2.4 (预测性安全) 串行（均依赖 Phase 1）
Month 3: 集成测试 + 文档更新 + 验收
```

## 里程碑验收

### M1: 自适应工作流 + 目标推理就绪（Month 1）

- [ ] 条件分支: diagnose → fix-vpc (条件满足时)
- [ ] Plan revision: discovery step → 重新规划
- [ ] "这台机器最近很慢" → 多方案 → 用户选择 → 执行
- [ ] 破坏性方案标注 risk + 警告

### M2: 自主编排 + 预测性安全就绪（Month 2）

- [ ] FinOps HIGH → F1 自动编排
- [ ] 巡检 CRITICAL → P1 自动编排
- [ ] 删除未挂载空磁盘 → 自动确认
- [ ] 删除生产实例 → Human token + 影响面报告

### M3: Phase 2 整体验收（Month 3）

- [ ] 一次模糊查询 → 目标推理 → 多方案选择 → 自适应执行 → 安全确认 完整闭环
- [ ] 所有新增测试通过；回归测试零 failure
- [ ] ADR、Spec、Plan 文档状态更新为 Accepted / Complete
