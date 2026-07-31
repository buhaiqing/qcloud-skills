# Phase 2: L3→L4 Intent-Aware Systems — 设计文档

> **Status**: Draft
> **Date**: 2026-08-01
> **Author**: bohaiqing
> **ADR**: ADR-0005

## 背景

Phase 1 补齐 L3 基础能力后，系统具备：
- 内建 LLM Critic（GCL 闭环）
- 动态 Skill 注册与路由
- 运行时错误升级链
- 统一观测面

Phase 2 在此基础上实现 L4 Intent-Aware Systems，核心能力：
- 工作流从预生成 DAG → 运行时动态调整
- 用户意图从显式指令 → 模糊语义推断
- 跨 skill 编排从手动选择 → 自动匹配
- 安全门禁从关键词 → 上下文感知

---

## 2.1 自适应工作流引擎

### 2.1.1 现状

Phase 1 完成后，PlanDispatcher 执行预生成的 DAG，工作流在生成后固定不变。中间步骤失败 → 后续步骤跳过，不支持动态调整。

### 2.1.2 设计

**ExecutionPlan 扩展**：

```python
@dataclass
class Condition:
    expression: str          # Jinja2 模板: "{{output.diagnose.cpu_usage}} > 80"
    true_branch: str         # 满足条件时执行的 step id
    false_branch: str | None # 不满足条件时执行的 step id (可选)

@dataclass
class PlanStep:
    # ... 现有字段 ...
    condition: Condition | None = None       # NEW: 条件分支
    discovery: bool = False                  # NEW: 探查步骤
    max_revisions: int = 0                   # NEW: 最大 plan revision 次数
```

**条件分支执行**：

```
PlanDispatcher._execute_step(step):
  1. 执行 step
  2. 如果 step.condition:
     a. 评估 condition.expression (Jinja2 渲染，读取 Blackboard 上下文)
     b. 如果 true → 动态插入 true_branch step
     c. 如果 false → 动态插入 false_branch step (如果有)
  3. 如果 step.discovery:
     a. 分析 step 输出中的新发现（错误码、异常指标）
     b. 触发 plan_revision(): 重新规划剩余步骤
```

**Plan Revision 机制**：

```python
def plan_revision(self, plan, completed_steps, new_findings):
    """当中间步骤发现新信息时，重新规划剩余步骤。
    
    限制:
    - 最大 revision 次数: 3
    - 只能修改尚未执行的步骤
    - 已完成的步骤不可撤销
    - 新步骤必须通过 safety gate
    """
    remaining = [s for s in plan.steps if s.status == "pending"]
    revised = self.planner.replan(remaining, context=new_findings)
    plan.steps = completed_steps + revised
```

**集成点**：
- `qcloud-copilot/copilot/dispatcher.py`: `_execute_step()` 增加条件评估 + plan revision
- `qcloud-copilot/copilot/models.py`: PlanStep 扩展
- `qcloud-copilot/copilot/planner.py`: 新增 `replan()` 方法

### 2.1.3 文件变更

| 文件 | 变更 | 行数估计 |
|------|------|:------:|
| `qcloud-copilot/copilot/models.py` | PlanStep 扩展 (condition, discovery, max_revisions) | +20 |
| `qcloud-copilot/copilot/dispatcher.py` | 条件分支 + plan revision 逻辑 | +80 |
| `qcloud-copilot/copilot/planner.py` | 新增 replan() 方法 | +50 |

### 2.1.4 验收标准

- [ ] 条件分支: `diagnose` 发现 VPC 问题 → 自动插入 `fix-vpc` step
- [ ] 条件分支: `diagnose` 未发现问题 → 自动插入 `noop` (skip) step
- [ ] Plan revision: `discovery` step 发现新错误码 → 剩余步骤重新规划
- [ ] 安全约束: plan revision 不能撤销已完成的步骤
- [ ] 最大 revision 次数: 3 次后停止并报告

---

## 2.2 意图驱动的目标推理

### 2.2.1 现状

Phase 1 完成后，Copilot Classifier 基于正则做意图分类（DIAGNOSE / INSPECT / CRUISE / ACT / COMPARE / REPORT）。用户必须显式说出操作目标，系统不做推断。

### 2.2.2 设计

**GoalInference 层**（在 Classifier 之上）：

```python
@dataclass
class InferredGoal:
    goal: str                          # "diagnose_performance"
    description: str                   # "诊断 CVM ins-xxx 的性能问题"
    confidence: float                  # 0.0-1.0
    candidate_chains: list[SkillChain] # 候选 skill 链
    risk_level: str                    # "low" | "medium" | "high"
    clarifying_questions: list[str]    # 需要用户确认的问题

@dataclass
class SkillChain:
    skills: list[str]                  # ["qcloud-cvm-ops", "qcloud-monitor-ops"]
    description: str                   # "快速诊断 (CVM + Monitor)"
    estimated_duration: str            # "约 2 分钟"
    risk: str                          # "low"
    reads_only: bool                   # 是否只读
```

**推理流程**：

```
用户查询: "这台机器最近很慢"
  → GoalInference.infer(query, context)
    1. LLM 调用: 推断目标 + 生成候选方案
    2. 匹配 SkillRegistry: 将方案中的描述映射到实际 skill
    3. 评估风险: 检查方案中的 skill 是否有破坏性操作
    4. 生成 clarifying_questions: 缺少关键信息时提问
  → 返回 InferredGoal
  → 呈现多方案供用户选择
  → 用户选择后生成 ExecutionPlan
```

**安全约束**：
- 任何包含破坏性操作的方案必须标注 `risk: "high"` 并置顶警告
- 模糊查询必须返回至少 1 个 clarifying_question（如果 confidence < 0.7）
- 目标推理结果不可直接执行，必须经用户确认

### 2.2.3 文件变更

| 文件 | 变更 | 行数估计 |
|------|------|:------:|
| `qcloud-copilot/copilot/goal_inference.py` | 新文件: GoalInference + InferredGoal + SkillChain | +120 |
| `qcloud-copilot/copilot/classifier.py` | 集成 GoalInference 调用 | +30 |
| `qcloud-copilot/copilot/engine.py` | `ask()` 增加目标推理路径 | +40 |

### 2.2.4 验收标准

- [ ] "这台机器最近很慢" → 返回 2+ 个诊断方案
- [ ] "帮我省点钱" → 返回 FinOps 成本优化方案
- [ ] "最近老报警" → 返回告警分析 + 巡检方案
- [ ] 方案中包含破坏性操作时 → 标注 `risk: "high"` + 警告
- [ ] 模糊查询 (confidence < 0.7) → 返回 clarifying_questions
- [ ] 方案中的 skill 链全部在 SkillRegistry 中验证通过

---

## 2.3 跨 Skill 自主编排

### 2.3.1 现状

Phase 1 完成后，`cross-skill-orchestration.md` 定义了 F1/F2/P1/A1/A2 五种模式，但需 agent 手动选择。ErrorEscalator 实现了单步跨 skill 委托，但不支持编排模式级的选择。

### 2.3.2 设计

**OrchestrationPattern 建模**：

```python
@dataclass
class OrchestrationPattern:
    name: str                          # "F1" | "F2" | "P1" | "A1" | "A2"
    description: str
    trigger_conditions: list[Condition] # 触发条件
    skill_chain: list[str]             # 编排的 skill 序列
    handoff_schema: str                # 上下文传递的 JSON Schema 路径
    fallback_pattern: str | None       # 失败时的降级模式

@dataclass
class OrchestrationSelector:
    patterns: list[OrchestrationPattern]
    
    def select(self, blackboard_state: dict) -> OrchestrationPattern | None:
        """根据 Blackboard 当前状态匹配最佳编排模式。
        
        匹配规则:
        1. 所有 trigger_conditions 都满足 → 匹配
        2. 多个匹配 → 选 specificity 最高（条件最多）的
        3. 无匹配 → None (回退到默认执行)
        """
```

**触发条件示例**：

```python
# F1: FinOps 发现成本异常 + 资源 CPU 高 → 巡检 → AIOps RCA
F1 = OrchestrationPattern(
    name="F1",
    trigger_conditions=[
        Condition("blackboard.finops.anomaly_level == 'HIGH'"),
        Condition("blackboard.finops.resource_cpu > 80"),
    ],
    skill_chain=["qcloud-proactive-inspection", "qcloud-aiops-diagnosis"],
    handoff_schema="qcloud-aiops-diagnosis/assets/finops-handoff.schema.json",
    fallback_pattern="A1"
)

# P1: 巡检发现 CRITICAL 安全配置 → AIOps 深度诊断
P1 = OrchestrationPattern(
    name="P1",
    trigger_conditions=[
        Condition("blackboard.inspection.severity == 'CRITICAL'"),
        Condition("blackboard.inspection.category == 'security'"),
    ],
    skill_chain=["qcloud-aiops-diagnosis"],
    handoff_schema="qcloud-aiops-diagnosis/assets/inspection-handoff.schema.json",
    fallback_pattern="A2"
)
```

**集成点**：
- `qcloud-copilot/copilot/engine.py`: 在 plan generation 前调用 `OrchestrationSelector.select()`
- 匹配到模式 → 使用模式定义的 skill_chain 替代默认 plan
- 模式执行失败 → 触发 fallback_pattern

### 2.3.3 文件变更

| 文件 | 变更 | 行数估计 |
|------|------|:------:|
| `qcloud-copilot/copilot/orchestration.py` | 新文件: OrchestrationPattern + OrchestrationSelector | +100 |
| `qcloud-copilot/copilot/engine.py` | 集成 OrchestrationSelector | +30 |
| `qcloud-aiops-diagnosis/references/cross-skill-orchestration.md` | 模式定义迁移到代码 (或保持文档同步) | ±0 |

### 2.3.4 验收标准

- [ ] FinOps HIGH 异常 + CPU > 80% → 自动选择 F1 → 巡检 → AIOps
- [ ] 巡检 CRITICAL 安全发现 → 自动选择 P1 → AIOps 深度诊断
- [ ] 无模式匹配 → 回退到默认 plan generation
- [ ] F1 执行失败 → fallback 到 A1

---

## 2.4 预测性安全门禁

### 2.4.1 现状

Phase 1 完成后，`harness_safety.py` 基于动词词干匹配检测破坏性操作（delete、terminate、destroy 等）。所有破坏性操作统一要求 human token。

### 2.4.2 设计

**影响面评估**：

```python
@dataclass
class ImpactAssessment:
    operation: str                     # "TerminateInstances"
    resource_ids: list[str]            # ["ins-xxx"]
    affected_resources: list[AffectedResource]  # 受影响的关联资源
    risk_level: str                    # "low" | "medium" | "high" | "critical"
    blast_radius: int                  # 受影响的资源数量
    recommendation: str                # 建议

@dataclass
class AffectedResource:
    resource_type: str                 # "CLB" | "CDB" | "SecurityGroup"
    resource_id: str
    relationship: str                  # "listener" | "readonly_replica" | "member"
    impact: str                        # "监听器将失去后端" | "只读副本将断开"
```

**依赖图分析**：

```
删除 CVM ins-xxx:
  1. 查询 CLB 监听器 → 发现 ins-xxx 是 2 个监听器的后端
  2. 查询 CDB 只读副本 → 无关联
  3. 查询安全组 → ins-xxx 在 sg-abc 中
  4. 查询 CVM 磁盘 → 2 块数据盘 (disk-1, disk-2) 已挂载
  5. 查询弹性公网 IP → 1 个 EIP 已绑定
  
  影响面: 2 CLB 监听器 + 1 安全组 + 2 数据盘 + 1 EIP
  风险等级: HIGH
  建议: 先解绑 CLB 后端 + EIP，再卸载磁盘，最后删除 CVM
```

**风险分级确认**：

| 风险等级 | 条件 | 确认方式 |
|:--------:|------|----------|
| LOW | 影响面 = 0，非生产环境 | 自动确认（无需 human token） |
| MEDIUM | 影响面 ≤ 2，非生产环境 | GCL Critic 评审后自动确认 |
| HIGH | 影响面 > 2，或生产环境 | Human token |
| CRITICAL | 影响面 > 5，或删除 VPC/IAM/DB | Human token + 影响面报告 |

**Human Confirmation 提示增强**：

```
当前提示: "This operation is destructive. Confirm token to proceed."
增强提示:
  "⚠️ DESTRUCTIVE OPERATION: TerminateInstances ins-xxx
   Risk Level: HIGH
   Affected Resources:
     - 2 CLB Listeners (lb-abc, lb-def) will lose backend
     - 2 Data Disks (disk-1, disk-2) will be released
     - 1 EIP (eip-xxx) will be disassociated
     - 1 Security Group membership will be removed
   Recommended Pre-steps:
     1. Deregister from CLB listeners
     2. Unbind EIP
     3. Detach data disks
   Confirm token to proceed."
```

### 2.4.3 文件变更

| 文件 | 变更 | 行数估计 |
|------|------|:------:|
| `scripts/impact_analyzer.py` | 新文件: ImpactAssessment + 依赖图分析 | +150 |
| `scripts/harness_safety.py` | 集成 ImpactAnalyzer，风险分级 | +60 |
| `scripts/evidence_kernel.py` | human confirmation 提示增强 | +30 |

### 2.4.4 验收标准

- [ ] 删除未挂载空磁盘 (LOW) → 自动确认
- [ ] 停止非生产实例 (MEDIUM) → Critic 评审后自动确认
- [ ] 删除生产实例 (HIGH) → Human token 确认
- [ ] 删除 VPC (CRITICAL) → Human token + 影响面报告确认
- [ ] 影响面报告包含完整的关联资源列表和建议的预操作步骤
- [ ] 回归: 现有 `harness_safety.py` 行为不变

---

## 自验证

```python
# 2.1: 条件分支
plan = ExecutionPlan(steps=[
    PlanStep(id="diag", ...),
    PlanStep(id="fix", condition=Condition("{{output.diag.error}} == 'VpcNotFound'", ...), ...)
])
# 验证: diag 失败 + error=VpcNotFound → fix 被插入执行

# 2.2: 目标推理
goal = GoalInference().infer("这台机器最近很慢")
assert len(goal.candidate_chains) >= 2
assert all(c.risk for c in goal.candidate_chains)

# 2.3: 自主编排
selector = OrchestrationSelector([F1, F2, P1, A1, A2])
state = {"finops": {"anomaly_level": "HIGH", "resource_cpu": 85}}
assert selector.select(state).name == "F1"

# 2.4: 安全分级
impact = ImpactAnalyzer().assess("TerminateInstances", ["ins-xxx"])
assert impact.risk_level in {"low", "medium", "high", "critical"}
assert len(impact.affected_resources) == impact.blast_radius
```

## 文件清单

| 文件 | 操作 | 说明 |
|------|:----:|------|
| `qcloud-copilot/copilot/models.py` | 修改 | PlanStep 扩展 |
| `qcloud-copilot/copilot/dispatcher.py` | 修改 | 条件分支 + plan revision |
| `qcloud-copilot/copilot/planner.py` | 修改 | replan() 方法 |
| `qcloud-copilot/copilot/goal_inference.py` | 新增 | GoalInference |
| `qcloud-copilot/copilot/classifier.py` | 修改 | 集成 GoalInference |
| `qcloud-copilot/copilot/engine.py` | 修改 | 目标推理路径 + OrchestrationSelector |
| `qcloud-copilot/copilot/orchestration.py` | 新增 | OrchestrationPattern + OrchestrationSelector |
| `scripts/impact_analyzer.py` | 新增 | ImpactAssessment |
| `scripts/harness_safety.py` | 修改 | 风险分级 |
| `scripts/evidence_kernel.py` | 修改 | 增强 human confirmation |
