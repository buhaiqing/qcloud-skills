# 智能体执行轨迹评测体系

> 文档版本：v2.0.0  
> 更新日期：2026-07-17  
> 维护者：qcloud-skills 团队

---

## 什么是"轨迹评测"，为什么你需要关心它

当你的 AI Agent 执行任务时，它每一步都在留下痕迹：
- 它执行了什么命令（bash / tccli）
- Critic 给了几分（安全分、正确性分）
- 最终是通过了还是失败了
- 失败的话是哪一轮失败的

这些痕迹就是**轨迹（Trajectory）**。

**没有评测体系之前**，你只能靠"感觉"：
- "最近好像总有问题" → 无法量化
- "这个 skill 质量怎么样" → 不知道
- "这次优化到底有没有效果" → 无法对比

**有了评测体系之后**，你能回答：
- "我的 Agent 今天表现怎么样" → 一行命令，量化报告
- "这次改版让收敛更快了吗" → 对比两次轨迹的收敛速度
- "有哪个 skill 总是 early fail" → 早期失败率告警
- "哪些错误是重复出现的" → 失败模式提取

> **一句话：轨迹评测让你对 Agent 的质量从"盲测"变成"仪表盘"**。

---

## 一、我们想要回答的 6 类核心问题

> 以下每类问题对应一个**用户角色**和**业务场景**，从中引出需要的指标。

---

### Q1. 我的 Agent 今天表现怎么样？

**角色**：运维工程师 / SRE

**场景**：每天早上看一眼 Dashboard，确认昨晚的自动化任务没有异常。

**需要的指标**：

| 你想知道 | 对应指标 | 理想值 | 说明 |
|---------|---------|--------|------|
| 今天有多少任务成功 | `pass_rate` | > 80% | 通过率 |
| 有没有人遇到安全问题 | `safety_fail_rate` | = 0% | 安全失败率 |
| 有没有出事故 | `early_failure_rate` | < 5% | 前2轮就失败的比例 |
| 失败的轨迹长什么样 | `trajectory_shape` | fast_pass 多 | 轨迹形状分布 |
| 最近有异常轨迹吗 | `outlier_rate` | < 10% | 异常轨迹比例 |

**👉 一行命令**：`python3 scripts/gcl_trajectory_quality.py --since-hours 24`

---

### Q2. 这次优化到底有没有效果？

**角色**：开发工程师 / Team Lead

**场景**：你刚改了 prompt 模板、优化了 Critic 评分规则，想知道质量有没有提升。

**需要的指标**：

| 你想知道 | 对应指标 | 怎么用 |
|---------|---------|--------|
| 收敛更快了吗 | `avg_convergence_speed` | 优化前 vs 优化后对比 |
| 通过率提升了吗 | `pass_rate` | 同比/环比趋势 |
| 浪费的迭代减少了吗 | `wasted_iter_rate` | 越低越好 |
| 有没有引入新问题 | `oscillation_rate` | 振荡率上升 = 引入不稳定 |

**👉 一行命令**：`python3 scripts/gcl_trajectory_quality.py --since-hours 168`（上周数据）

---

### Q3. 哪个 Skill 质量最差，需要优先修？

**角色**：Tech Lead / 架构师

**场景**：团队有 30+ 个 skill，你知道某个 skill 质量差，但不知道差在哪里。

**需要的指标**：

| 你想知道 | 对应指标 | 怎么用 |
|---------|---------|--------|
| 哪些 skill 通过率低 | `cross_skill_benchmark.by_skill` | 排序找最差的 |
| 哪些 skill 总要多轮收敛 | `avg_iters` | 期望都是 1.0 |
| 哪些 skill 总是 early fail | `early_failure` 按 skill 分组 | 优先修总是第1轮就死的 |
| 哪些 skill 维度评分特别低 | `baselines` | spec_compliance 历史均值 = 0.3 → 阈值不对 |
| 哪些 skill 特别不稳定 | `oscillation_count` 按 skill 聚合 | 振荡率高 = Critic 评分不稳 |

**👉 一行命令**：`python3 scripts/gcl_trace_aggregate.py` → `by_skill` 分组输出

---

### Q4. 有没有安全风险正在酝酿？

**角色**：安全工程师 / Security Lead

**场景**：不想等事故发生才知道问题，想提前发现隐患。

**需要的指标**：

| 你想知道 | 对应指标 | 触发条件 |
|---------|---------|--------|
| 有没有凭证泄露的轨迹 | `safety = 0`（在 trace 中） | 立即告警 |
| 有没有持续在危险边缘操作 | `safety_persistent_low` | safety 全程 < 1.0 |
| 有没有从安全违规中恢复 | `safety_recovery` | 曾 < 1.0 但最终 = 1.0 |
| 有没有破坏性操作没确认 | `safety` 评分轨迹 | Modify/Delete 操作 safety < 1.0 |
| 有没有新出现的安全问题模式 | `emerging_failure_pattern` | 同一安全错误最近 7 天频率 > 历史均值 2σ |

---

### Q5. 哪些错误是重复的，可以预防？

**角色**：运维工程师 / AI DevOps

**场景**：你发现同一个错误出现第 5 次了，能不能自动记住，下次不再犯。

**需要的指标**：

| 你想知道 | 对应指标 | 怎么用 |
|---------|---------|--------|
| 这个错误之前见过吗 | `failure_pattern` 命中率 | > 0 = 已知模式 |
| 这是新错误还是老错误 | `failure_pattern.count` | 老错误 count 高 |
| 这个错误多久没出现了 | `failure_pattern.last_hit` | 用时间衰减排序 |
| 这次是新出现的模式吗 | `emerging_pattern_detection` | count 从 0 变多 = 新兴 |
| 高频错误有哪些 | `failure_pattern` 按 count 排序 | 优先修 top 5 |

**👉 已有**：`scripts/reflexion_retrieve.py`（已知模式召回）+ `scripts/failure_pattern_extract.py`（提取新模式）

---

### Q6. Agent 自我进化的能力怎么样？

**角色**：AI 工程师 / AI Platform Lead

**场景**：你的 Agent 能不能从历史中学习变得越来越好？还是每次都在重复同样的错误？

**需要的指标**：

| 你想知道 | 对应指标 | 理想趋势 |
|---------|---------|---------|
| 失败模式有没有被记住 | `failure_pattern.hit_rate` | 随时间上升 |
| 成功路径有没有被复用 | `success_pattern.reuse_rate` | 随时间上升 |
| 通过率有没有在改善 | `pass_rate` 30天趋势 | 上升或持平 |
| 收敛速度有没有在改善 | `avg_convergence_speed` 趋势 | 上升或趋近 1.0 |
| 阈值有没有越来越准 | `threshold_deviation` | 趋近 0 |
| 有没有发现新兴失败模式 | `emerging_failure_pattern` 数量 | 应逐渐减少 |

**👉 已有**：`scripts/success_pattern_mine.py`（成功模式挖掘）+ `scripts/rubric_calibrate.py`（自适应阈值校准）

---

## 二、完整指标体系（目标蓝图）

> 以下是我们认为一个完整的轨迹评测体系应该覆盖的指标，按用户问题分类。  
> **✅ = 已实现并测试通过 | ⚠️ = 部分实现或 schema 限制 | ❌ = 未实现**  
> **优先级**：🔴 高（直接影响安全/质量）/ 🟡 中（有价值但非紧急）/ 🔵 低（长期有价值）

---

### 维度 A：今天的 Agent 质量如何？

| 指标 | 状态 | 数据来源 | 实现脚本 |
|------|------|---------|---------|
| **通过率** `pass_rate` | ✅ | `trace.final.status` | `gcl_trace_aggregate` |
| **安全失败率** `safety_fail_rate` | ✅ | `trace.final.status` | `gcl_trace_aggregate` |
| **迭代耗尽率** `max_iter_rate` | ✅ | `trace.final.status` | `gcl_trace_aggregate` |
| **Rubric 五维平均分** `avg_rubric_scores` | ✅ | `trace.iterations[].critic.scores` | `gcl_trace_aggregate` |
| **per-skill 通过率** `by_skill[].pass_rate` | ✅ | `trace.final.status` | `gcl_trace_aggregate` |
| **per-skill 维度平均分** `by_skill[].avg_scores` | ✅ | `trace.iterations[].critic.scores` | `gcl_trace_aggregate` |
| **轨迹形状分布** `trajectory_shape_distribution` | ⚠️ | `trace.iterations[].decision` | `gcl_session_enrich.py`（部分） |
| **异常轨迹比例** `outlier_rate` | ✅ | `trace.final.scores` vs `baselines` | `gcl_trajectory_quality` |
| **异常维度定位** `outlier_dims` | ✅ | `trace.final.scores` vs `baselines` | `gcl_trajectory_quality` |

**采集能力评估**：✅ **A1-A9 全部可采集**，数据来源为 `gcl-trace-*.json`，无需 schema 变更。

---

### 维度 B：Agent 收敛快不快？

| 指标 | 状态 | 数据来源 | 实现脚本 |
|------|------|---------|---------|
| **收敛速度** `convergence_speed` | ✅ | `trace.final.iter` / `max_iter` | `gcl_trajectory_quality` |
| **振荡次数** `oscillation_count` | ✅ | 多轮 `critic.scores` 对比 | `gcl_trajectory_quality` |
| **振荡率** `oscillation_rate` | ✅ | 振荡轨迹 / 总轨迹 | `gcl_trajectory_quality` |
| **分数方差** `score_variance` | ✅ | 多轮维度分数方差 | `gcl_trajectory_quality` |
| **迭代利用率** `iter_efficiency` | ✅ | 第一 PASS / 总迭代 | `gcl_trajectory_quality` |
| **浪费迭代数** `wasted_iters` | ✅ | 总迭代 - 首次 PASS | `gcl_trajectory_quality` |
| **收敛趋势** `convergence_trend` | ⚠️ | 需对比两个时间窗口 | 未实现（需增量对比） |

**采集能力评估**：✅ **B1-B6 全部可采集**。B7 需跨时间窗口对比，已知实现路径。

---

### 维度 C：有没有安全风险？

| 指标 | 状态 | 数据来源 | 实现脚本 |
|------|------|---------|---------|
| **凭证泄露检测** | ✅ | `trace.iterations[].generator.result_excerpt` | `gcl_runner` (structural_critic) |
| **安全评分轨迹** `safety_trajectory` | ✅ | 每轮 `critic.scores.safety` | `gcl_trajectory_quality` |
| **持久低安全分** `safety_persistent_low` | ✅ | `all(s < 1.0 for s in safety_trajectory)` | `gcl_trajectory_quality` |
| **安全恢复** `safety_recovery` | ✅ | 曾 < 1.0 且最终 = 1.0 | `gcl_trajectory_quality` |
| **早期失败** `early_failure` | ✅ | 前2轮 SAFETY_FAIL / MAX_ITER | `gcl_trajectory_quality` |
| **早期失败率** `early_failure_rate` | ✅ | early_failure / 总轨迹 | `gcl_trajectory_quality` |
| **破坏性操作确认缺失** | ⚠️ | 需操作类型标注 | 未实现（依赖 rubric.md 安全规则） |
| **安全合规规则覆盖率** `safety_rules_coverage` | ❌ | 需人工维护规则清单 | 未实现 |
| **新兴安全模式检测** `emerging_safety_pattern` | ❌ | 需 pattern_anomaly_detect | P1-C（TODO） |

**采集能力评估**：✅ **C1-C6 可直接采集**。C7 需扩展 rubric schema。C8-C9 需单独模块。

---

### 维度 D：哪些错误在重复出现？

| 指标 | 状态 | 数据来源 | 实现脚本 |
|------|------|---------|---------|
| **失败模式命中率** `failure_pattern_hit_rate` | ✅ | `reflexion_retrieve.py` 召回结果 | `reflexion_retrieve` |
| **失败模式清单** `failure_patterns.md` | ✅ | GCL trace 提取 | `failure_pattern_extract` |
| **分层失败模式** (HOT/WARM/COLD) | ✅ | `failure_pattern_layered` | P0-B 已完成 |
| **严重性 + 时间衰减** `severity_weighted_score` | ✅ | P0-C 完成 | `reflexion_retrieve` |
| **成功模式命中率** `success_pattern_reuse_rate` | ✅ | `success_pattern_mine` + `success_pattern_retrieve` | P0-A 完成 |
| **新兴失败模式发现** `emerging_pattern_detection` | ❌ | P1-C（TODO） | 未实现 |
| **Pattern 升级为 Anti-Pattern** | ❌ | P2-A（TODO） | 未实现 |
| **Pattern 生命周期管理** | ⚠️ | count < 3 修剪 | 部分实现 |

**采集能力评估**：✅ **D1-D5 核心已实现**。D6-D7 属于 P1-C/P2-A 规划中。

---

### 维度 E：Agent 能不能自我进化？

| 指标 | 状态 | 数据来源 | 实现脚本 |
|------|------|---------|---------|
| **通过率趋势** `pass_rate_trend` | ⚠️ | 需跨时间窗口对比 | 未实现（需趋势计算） |
| **收敛速度趋势** `convergence_trend` | ⚠️ | 需跨时间窗口对比 | 未实现 |
| **自适应阈值偏离度** `threshold_deviation` | ✅ | `rubric_calibrate.py` 输出 | `rubric_calibrate` |
| **历史基线** `baselines` | ✅ | `gcl_trajectory_quality` | `baselines` 字段 |
| **自适应阈值建议** `threshold_suggestions` | ✅ | `rubric_calibrate.py --json` | `rubric_calibrate` |
| **新兴失败模式发现** `emerging_failure_detection` | ❌ | P1-C（TODO） | 未实现 |
| **零样本新 Skill 质量** | ❌ | 需新 skill 首次执行数据 | 未实现（数据积累中） |

**采集能力评估**：⚠️ **E1-E2 趋势分析缺失**，但实现路径清晰（基于已有数据加时间窗口对比）。E6-E7 在 TODO 中。

---

### 维度 F：工具调用效率怎么样？

| 指标 | 状态 | 数据来源 | 实现脚本 |
|------|------|---------|---------|
| **工具调用次数** `tool_call_count` | ⚠️ | 需 pi session log（非 gcl-trace） | `gcl_session_enrich.py` |
| **工具调用分类** `tool_call_by_category` | ⚠️ | read_only / write / bash / subagent | `gcl_session_enrich.py` |
| **每次迭代工具效率** `tool_efficiency_per_iter` | ❌ | 需 session log 关联到 trace | 未实现 |
| **令牌消耗** `token_consumption` | ❌ | 需 LLM API 日志 | 未实现 |
| **执行时长** `execution_duration` | ❌ | 需 session log timing | 未实现 |

**采集能力评估**：⚠️ **F1-F2 通过 `gcl_session_enrich.py` 可采集**（依赖 pi session log）。F3-F5 需 schema 变更或 LLM 日志接入。

---

### 维度 G：多智能体协作质量如何？

| 指标 | 状态 | 数据来源 | 实现脚本 |
|------|------|---------|---------|
| **Subagent 调用深度** `subagent_depth` | ⚠️ | pi session log | `gcl_session_enrich.py` |
| **Subagent 并行度** `subagent_concurrency` | ⚠️ | pi session log | `gcl_session_enrich.py` |
| **冗余调用检测** `redundant_call_detection` | ❌ | 需轨迹相似度分析 | 未实现 |
| **协作效率** `collaboration_efficiency` | ❌ | 需定义"有效协作" | 未实现 |
| **Agent 间上下文传递损失** | ❌ | 需 trace schema 支持 | 未实现 |
| **角色分工清晰度** `role_division_clarity` | ❌ | 需人工标注 | 未实现 |

**采集能力评估**：⚠️ **G1-G2 可采集**（`gcl_session_enrich.py`）。G3-G6 需要更深的 schema 变更或 LLM 分析。

---

### 维度 H：跨 Skill 基准对比

| 指标 | 状态 | 数据来源 | 实现脚本 |
|------|------|---------|---------|
| **per-family 通过率** `by_family.pass_rate` | ⚠️ | `cross_skill_benchmark` | `gcl_session_enrich.py` |
| **per-family 平均迭代次数** `by_family.avg_iters` | ⚠️ | `cross_skill_benchmark` | `gcl_session_enrich.py` |
| **per-skill 通过率** `by_skill.pass_rate` | ✅ | `gcl_trace_aggregate` | `gcl_trace_aggregate` |
| **维度相关性矩阵** `dimension_correlation` | ✅ | 5 维 Pearson r | `gcl_trajectory_quality` |
| **操作类型成功率** `op_type_success_rate` | ❌ | 需 CLI 命令标注（Describe/Modify/Delete）| 未实现 |
| **Critic 评分一致性** `critic_consistency` | ❌ | 需相似 case 评分对比 | 未实现 |

**采集能力评估**：✅ **H1-H4 可采集**。H5-H6 需扩展 trace schema 标注操作类型。

---

## 三、现状总结：完成了多少？

```
总计 57 个指标

✅ 已实现（可直接使用）:  29 个  ████████████████████░░░░░░░░░  51%
⚠️ 部分实现（可采集但需完善）:  10 个  █████████░░░░░░░░░░░░░░░░░░░  18%
❌ 未实现（需要开发）:       18 个  ███████████████████░░░░░░░░░  32%
```

**优先完成区（🔴 高价值 + 可实现）**：E1-E2（趋势分析）、F3（令牌消耗）、C7-C9（安全增强）  
**值得投资区（🟡 中价值 + 可实现）**：F4-F6（多 Agent 指标）、H5（操作类型成功率）  
**长期目标区（🔵 高价值 + 需 schema 变更）**：G3-G6（多 Agent 协作）、H6（Critic 一致性）

---

## 四、优先级矩阵（RIA 分析）

> RIA = **R**elevance（相关性）+ **I**mpact（影响力）+ **A**chievability（可实现性）

| 指标 | Relevance | Impact | Achievability | ROI 优先级 | 预计工时 |
|------|-----------|--------|--------------|-----------|---------|
| **E1 pass_rate_trend** | 🔴 直接回答"有没有变好" | 🔴 决定优化方向是否正确 | ✅ 已有数据 | 🔴🔴🔴 | 2h |
| **E2 convergence_trend** | 🔴 同上 | 🔴 同上 | ✅ 已有数据 | 🔴🔴🔴 | 2h |
| **C7 破坏性操作确认** | 🔴 安全红线 | 🔴 防止删库跑路 | ⚠️ 需操作类型标注 | 🔴🔴🔴 | 4h |
| **D6 emerging_pattern** | 🔴 发现新兴问题 | 🔴 预防胜于治疗 | ⚠️ 需 pattern_anomaly_detect | 🔴🔴🔴 | 8h |
| **F3 token_consumption** | 🟡 成本控制 | 🟡 优化 token 使用 | ⚠️ 需 LLM 日志 | 🔴🔴 | 4h |
| **H5 op_type_success_rate** | 🟡 精细化分析 | 🟡 知道哪种操作最容易失败 | ⚠️ 需 trace schema 标注 | 🔴🔴 | 4h |
| **G3 redundant_call** | 🟡 效率优化 | 🟡 减少浪费 | ⚠️ 需轨迹相似度 | 🔴🔴 | 8h |
| **C8 emerging_safety** | 🟡 安全增强 | 🟡 预防安全事件 | ⚠️ 需新兴模式检测 | 🔴🔴 | 8h |
| **I1 error_recovery_path** | 🟡 可观测性 | 🟡 知道怎么恢复 | ❌ 需 trace 扩展 | 🟡 | 4h |
| **G6 role_division** | 🔵 理论价值 | 🔵 理解 Agent 行为 | ❌ 需人工标注 | 🟡 | 16h |

---

## 五、TODO 优先级排序

### 🔴 第一梯队（立即安排）

| # | 任务 | 对应指标 | 价值 | 工时 |
|---|------|---------|------|------|
| T1 | 趋势分析模块（pass_rate_trend + convergence_trend） | E1, E2 | 回答"优化有没有效果"，直接驱动开发决策 | 2-4h |
| T2 | 破坏性操作标注 + 告警 | C7 | 安全红线，防止删库跑路 | 4h |
| T3 | 新兴失败模式发现 `pattern_anomaly_detect.py` | D6 | 预防胜于治疗，从被动响应转为主动预警 | 8h |

### 🟡 第二梯队（近期安排）

| # | 任务 | 对应指标 | 价值 | 工时 |
|---|------|---------|------|------|
| T4 | 操作类型标注（Describe/Modify/Delete）+ op_type_success_rate | H5 | 知道 Describe 最稳、Delete 最危险，针对性优化 | 4h |
| T5 | LLM Token 日志接入 + token_consumption | F3 | 成本控制，优化 token 使用策略 | 4h |
| T6 | emerging_safety_pattern 检测（基于 T3 扩展） | C8 | 在安全事件发生前预警 | 8h |

### 🔵 第三梯队（中长期目标）

| # | 任务 | 对应指标 | 价值 | 工时 |
|---|------|---------|------|------|
| T7 | 冗余调用检测 `redundant_call_detection` | G3 | 减少无效 Agent 调用，提升效率 | 8h |
| T8 | 错误恢复路径分析 `error_recovery_path` | I1 | 知道 Agent 从失败中如何恢复 | 4h |
| T9 | Critic 评分一致性分析 `critic_consistency` | H6 | 发现 Critic 自身的评分偏差 | 8h |
| T10 | 置信度校准分析 `confidence_calibration` | I5 | 知道 Agent 自评准不准 | 8h |

---

## 六、每项指标完成后的价值

| 完成后的能力 | 驱动的决策 |
|------------|---------|
| 趋势分析（E1-E2） | 知道哪个优化有效、哪个在倒退，停止做无效的改版 |
| 破坏性操作告警（C7） | 防止生产事故，触发人工复核流程 |
| 新兴模式发现（D6/C8） | 从"被动响应告警"升级为"主动预防问题" |
| 操作类型成功率（H5） | 知道 Delete 操作总是失败 → 专门强化删除前的确认逻辑 |
| Token 消耗分析（F3） | 知道哪个 prompt 最费 token → 针对性压缩上下文 |
| 冗余调用检测（G3） | 知道 subagent 调用有没有浪费 → 减少不必要的 Agent 间通信 |

---

## 七、当前可用的命令

```bash
# 1. 轨迹质量分析（9 个无参考信号）
python3 scripts/gcl_trajectory_quality.py --since-hours 720

# 2. 状态聚合（通过率 + per-skill 分解）
python3 scripts/gcl_trace_aggregate.py

# 3. 自适应阈值校准（基于历史数据）
python3 scripts/rubric_calibrate.py --skill qcloud-cos-ops --json

# 4. 轨迹 enrichment（工具效率 + 形状聚类 + 跨 Skill 对比）
python3 scripts/gcl_session_enrich.py --dry-run   # 自验证

# 5. 已知失败模式召回
python3 scripts/reflexion_retrieve.py retrieve --skill qcloud-cvm-ops --command "tccli cvm DescribeInstances"

# 6. 成功路径记录
python3 scripts/success_pattern_mine.py --batch
```

---

## 八、相关文件索引

| 文件 | 作用 |
|------|------|
| `scripts/gcl_runner.py` | 轨迹写入（`audit-results/gcl-trace-*.json`） |
| `scripts/gcl_trace_aggregate.py` | 状态聚合（✅ A1-A6, H3） |
| `scripts/gcl_trajectory_quality.py` | 无参考轨迹质量（✅ B1-B6, C2-C6, E1-E2, G4） |
| `scripts/gcl_session_enrich.py` | Session enrichment（⚠️ F1-F2, H1-H2） |
| `scripts/rubric_calibrate.py` | 自适应阈值校准（✅ E3-E5） |
| `scripts/failure_pattern_extract.py` | 失败模式提取（✅ D1-D4） |
| `scripts/reflexion_retrieve.py` | 已知模式召回（✅ D1） |
| `scripts/success_pattern_mine.py` | 成功路径挖掘（✅ D5） |
| `scripts/reflexion_store.py` | 模式持久化（HOT/WARM/COLD 分层） |
| `docs/superpowers/plans/trajectory-optimization-analysis.md` | 轨迹采集优化分析 |
