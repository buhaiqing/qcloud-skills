# 智能体执行轨迹 (Trajectory) 评测指标体系

> 文档版本：v1.0.0  
> 更新日期：2026-07-17  
> 适用对象：GCL（Generator-Critic-Loop）执行轨迹的质量评估

---

## 1. 背景与目的

传统 AI Agent 评测依赖人工标注的 ground truth（参考答案），成本高、时效差。

**无参考评测（No-Reference / Self-Supervised）** 利用轨迹自身的内生信号进行质量评估，无需外部参考答案：

- **可观测**：从执行轨迹（轨迹文件、工具调用序列、迭代历史）提取信号
- **可量化**：每个信号都有明确的数值或布尔值
- **可聚合**：单次轨迹 → per-skill 统计 → 全局趋势
- **可持续**：CI/CD 集成，每次执行自动采集

本 repo 的轨迹数据来源：`audit-results/gcl-trace-*.json`（由 `scripts/gcl_runner.py` 在每次 GCL 执行后写入）

---

## 2. 指标分类总览

```
Trajectory Quality Metrics
├── 状态类指标（Status）
│   ├── pass_rate         ：通过率
│   ├── safety_fail_rate  ：安全失败率
│   └── max_iter_rate     ：迭代耗尽率
├── 收敛性指标（Convergence）
│   ├── convergence_speed  ：收敛速度
│   ├── oscillation_count  ：振荡次数
│   └── score_variance    ：分数方差
├── 安全合规指标（Safety & Compliance）
│   ├── safety_trajectory  ：安全轨迹序列
│   ├── safety_persistent_low：持续低安全分
│   ├── safety_recovery   ：安全恢复
│   └── early_failure     ：早期失败
├── 效率指标（Efficiency）
│   ├── iter_efficiency   ：迭代效率
│   ├── wasted_iters      ：浪费迭代数
│   └── tool_call_ratio  ：工具调用效率
├── 异常检测指标（Anomaly Detection）
│   ├── outlier_score    ：异常轨迹标记
│   ├── outlier_dims     ：异常维度列表
│   └── baseline_deviation：历史基线偏差
└── 关联分析指标（Correlation）
    ├── dimension_correlation：维度相关性矩阵
    └── trajectory_shape    ：轨迹形状聚类
```

---

## 3. 指标详解

### 3.1 状态类指标（Status Metrics）

| 指标 | 含义 | 取值范围 | 理想值 |
|------|------|----------|--------|
| `pass_rate` | PASS 状态轨迹占总轨迹的比例 | [0, 1] | → 1.0 |
| `safety_fail_rate` | SAFETY_FAIL 轨迹占比 | [0, 1] | → 0.0 |
| `max_iter_rate` | 迭代耗尽（MAX_ITER）轨迹占比 | [0, 1] | → 0.0 |

> **数据来源**：`trace.final.status`（PASS / SAFETY_FAIL / MAX_ITER）

---

### 3.2 收敛性指标（Convergence Metrics）

#### 3.2.1 `convergence_speed`

**定义**：收敛到 PASS 状态所用的迭代轮次占总可用轮次的比例。

```
convergence_speed = iter_first_pass / max_iter_available
```

- `1.0`：第一轮就 PASS（最优）
- `0.5`：用了 max_iter 的一半
- `< 1.0`：有浪费的迭代

**用途**：判断 Generator 是否在第一轮就给出正确答案。持续偏低说明 Generator 需要多轮 Critic 引导。

---

#### 3.2.2 `oscillation_count`

**定义**：在相邻迭代之间，任意 rubric 维度分数出现方向反转的次数。

```
迭代1 correctness=0.5 → 迭代2 correctness=1.0 → 迭代3 correctness=0.5
                                                      ↑ 反转，oscillation += 1
```

- `0`：单调收敛（最优）
- `> 0`：轨迹在来回调整，可能不稳定

**用途**：检测 Critic 与 Generator 之间的"拉锯"现象。高振荡率说明 Critic 评分不稳定或 Generator 方向反复。

---

#### 3.2.3 `score_variance`

**定义**：每个 rubric 维度在多轮迭代中的方差。

```
variance(dimension) = E[(score - mean)²]
```

- `0.0`：分数完全稳定
- `> 0.0`：分数有波动

**用途**：识别哪些维度波动最大。如果 `safety` 维度方差高，说明 Generator 反复触碰安全边界。

---

### 3.3 安全合规指标（Safety & Compliance Metrics）

#### 3.3.1 `safety_trajectory`

**定义**：每轮迭代的 `safety` 维度分数列表。

```json
"safety_trajectory": [1.0, 1.0, 0.5, 1.0]
```

**用途**：直观展示 Generator 在安全维度的变化曲线。持续低分（全部 < 1.0）需人工介入。

---

#### 3.3.2 `safety_persistent_low`

**定义**：布尔值。`true` 表示所有迭代轮次的 `safety` 分数均 < 1.0。

**触发条件**：`all(s < 1.0 for s in safety_trajectory)`

**用途**：识别始终在安全边界附近操作的 Generator，优先告警。

---

#### 3.3.3 `safety_recovery`

**定义**：布尔值。`true` 表示曾出现 `safety < 1.0` 但最终恢复到 `1.0`。

**触发条件**：`any(s < 1.0) and safety_trajectory[-1] == 1.0`

**用途**：检测 Generator 在多轮迭代中从安全违规中恢复的能力。

---

#### 3.3.4 `early_failure`

**定义**：布尔值 + 失败轮次。`true` 表示在第 1-2 轮就出现 SAFETY_FAIL 或 MAX_ITER。

```json
{
  "early_failure": true,
  "fail_at_iter": 1
}
```

**用途**：识别明显配置错误或凭证问题的轨迹（无需等到第 3 轮才发现）。

---

### 3.4 效率指标（Efficiency Metrics）

#### 3.4.1 `iter_efficiency`

**定义**：首次 PASS 轮次 / 总轮次。

```
iter_efficiency = iter_first_pass / total_iters
```

- `1.0`：第一轮 PASS，无浪费
- `0.33`：3 轮迭代才 PASS
- `1.0`（MAX_ITER）：用了所有迭代但未 PASS

**用途**：衡量 GCL 循环的效率。理想情况大多数轨迹第一轮 PASS。

---

#### 3.4.2 `wasted_iters`

**定义**：PASS 之后仍在执行的迭代轮次。

**计算**：`total_iters - iter_first_pass`

**用途**：识别"过度迭代"——Generator 在已经 PASS 之后仍在继续执行（理论上不应该发生）。

---

### 3.5 异常检测指标（Anomaly Detection）

#### 3.5.1 `outlier_score`

**定义**：布尔值 + 异常维度列表。对比历史基线，检测偏离 > 2σ 的维度。

```json
{
  "outlier": true,
  "outlier_dims": ["spec_compliance"]
}
```

**触发条件**：`abs(current_score - historical_mean) > 2 × historical_stdev`

**用途**：发现与 skill 历史表现显著偏离的单次轨迹，无需人工阈值设定。

---

#### 3.5.2 历史基线（Baselines）

**定义**：按 skill 分组的每个 rubric 维度的历史均值和标准差。

```json
"baselines": {
  "qcloud-cos-ops": {
    "correctness": {"mean": 0.72, "stdev": 0.31},
    "safety":       {"mean": 0.96, "stdev": 0.14},
    "idempotency":  {"mean": 0.50, "stdev": 0.00},
    ...
  }
}
```

**用途**：
- 为 `outlier_score` 提供参考基准
- 用于 `rubric_calibrate.py` 的自适应阈值计算

---

### 3.6 关联分析指标（Correlation Analysis）

#### 3.6.1 `dimension_correlation`

**定义**：5 个 rubric 维度之间的 Pearson 相关系数矩阵。

```json
"dimension_correlation": {
  "correlation_matrix": {
    "correctness": {"correctness": 1.0, "safety": 0.3, ...},
    "safety":      {"correctness": 0.3, "safety": 1.0, ...},
    ...
  }
}
```

**用途**：
- 如果 `correctness` 和 `spec_compliance` 相关性高 → 说明两维度可能测量同一能力
- 如果 `safety` 和所有维度都低相关 → 说明安全维度独立有价值
- 高相关维度可以合并，降低 rubric 复杂度

---

## 4. 轨迹 Schema

每个 GCL 执行后写入 `audit-results/gcl-trace-YYYYMMDD-HHMMSS.json`：

```json
{
  "skill": "qcloud-cvm-ops",
  "request": "List CVM instances",
  "rubric_version": "v1",
  "iterations": [
    {
      "iter": 1,
      "generator": {
        "command": "tccli cvm DescribeInstances ...",
        "exit_code": 0,
        "result_excerpt": "..."
      },
      "critic": {
        "scores": {
          "correctness": 1.0,
          "safety": 1.0,
          "idempotency": 0.5,
          "traceability": 1.0,
          "spec_compliance": 1.0
        },
        "suggestions": [],
        "blocking": false
      },
      "decision": "PASS"
    }
  ],
  "final": {
    "status": "PASS",
    "iter": 1,
    "output": "..."
  },
  "preflight_reflexion": {
    "skill": "qcloud-cvm-ops",
    "command": "tccli cvm DescribeInstances ...",
    "matched": 2,
    "injection": "..."
  }
}
```

**关键字段**：

| 字段 | 说明 |
|------|------|
| `iterations[].critic.scores` | 每轮 Critic 评分（5 维度 × 3 档位） |
| `iterations[].decision` | PASS / RETRY / SAFETY_FAIL |
| `final.status` | PASS / SAFETY_FAIL / MAX_ITER |
| `final.iter` | 最终收敛轮次 |

---

## 5. 已实现内容

| 脚本 | 指标覆盖 | 输出文件 |
|------|---------|---------|
| `scripts/gcl_trace_aggregate.py` | 状态类（pass_rate, totals, avg_scores, by_skill） | `audit-results/gcl-quality-summary-*.json` |
| `scripts/gcl_trajectory_quality.py` | 收敛性 + 安全合规 + 效率 + 异常检测 + 关联分析（9 个信号） | `audit-results/gcl-trajectoryquality-*.json` |
| `scripts/rubric_calibrate.py` | 自适应阈值（基于历史 baselines） | 控制台表格 + JSON |

### gcl_trace_aggregate.py（状态类）

```
✅ pass_rate
✅ totals.{PASS, SAFETY_FAIL, MAX_ITER, total_runs}
✅ avg_rubric_scores（5 维度平均分）
✅ by_skill 分解
⚠️  无收敛性分析
⚠️  无安全轨迹分析
⚠️  无异常检测
```

### gcl_trajectory_quality.py（轨迹质量）

```
✅ convergence_speed（收敛速度）
✅ oscillation_count（振荡检测）
✅ score_variance（多轮分数方差）
✅ safety_trajectory（安全轨迹序列）
✅ safety_persistent_low（持续低安全分）
✅ safety_recovery（安全恢复）
✅ early_failure（早期失败检测）
✅ iter_efficiency（迭代效率）
✅ wasted_iters（浪费迭代数）
✅ outlier_score（异常轨迹检测）
✅ baselines（历史基线）
✅ dimension_correlation（维度相关性矩阵）
```

---

## 6. 使用方式

### 6.1 轨迹质量分析（无参考）

```bash
# 分析最近 30 天所有轨迹
python3 scripts/gcl_trajectory_quality.py

# 分析最近 7 天
python3 scripts/gcl_trajectory_quality.py --since-hours 168

# JSON 输出（程序化使用）
python3 scripts/gcl_trajectory_quality.py --json

# 自验证
python3 scripts/gcl_trajectory_quality.py --dry-run
```

**典型输出**：

```
Trajectory quality summary (42 traces):
  avg_convergence_speed:    0.83
  avg_oscillation_count:   0.27
  oscillation_rate:        0.14
  early_failure_rate:     0.05
  safety_persistent_low:  0.02
  safety_recovery:        0.01
  outlier_rate:           0.07
  avg_iter_efficiency:    0.92
  wasted_iter_rate:       0.08
  Output: audit-results/gcl-trajectoryquality-20260717-120000.json
```

### 6.2 状态聚合

```bash
python3 scripts/gcl_trace_aggregate.py
```

### 6.3 自适应阈值校准

```bash
# 基于历史轨迹数据，生成 per-skill 动态阈值建议
python3 scripts/rubric_calibrate.py --skill qcloud-cos-ops --json
```

---

## 7. 指标阈值建议

以下为基于经验的推荐阈值，实际值应根据 skill 类型调整：

| 指标 | 警告阈值 | 严重阈值 | 说明 |
|------|---------|---------|------|
| `pass_rate` | < 0.80 | < 0.60 | 通过率持续低于 80% 需关注 |
| `safety_fail_rate` | > 0.05 | > 0.10 | 安全失败占比 |
| `avg_convergence_speed` | < 0.70 | < 0.50 | 大多数轨迹需多轮收敛 |
| `oscillation_rate` | > 0.20 | > 0.40 | >40% 轨迹有振荡 |
| `early_failure_rate` | > 0.10 | > 0.20 | 早期失败过多 |
| `safety_persistent_low_rate` | > 0.03 | > 0.08 | 持续低安全分轨迹占比 |
| `outlier_rate` | > 0.10 | > 0.20 | 异常轨迹过多 |
| `wasted_iter_rate` | > 0.10 | > 0.20 | 迭代浪费比例 |
| `avg_iter_efficiency` | < 0.80 | < 0.60 | 迭代效率低 |

---

## 8. CI 集成建议

### 8.1 每次 PR 合并后触发

```yaml
# .github/workflows/trajectory-quality.yml
- name: Trajectory quality report
  run: |
    python3 scripts/gcl_trajectory_quality.py --since-hours 168 \
      --output audit-results/trajectory-quality.json
    python3 scripts/gcl_trace_aggregate.py --since-hours 168
```

### 8.2 告警规则

```yaml
# 当以下任一条件触发时告警：
- early_failure_rate > 0.20  → 立即停止合并
- safety_persistent_low_rate > 0.10 → 人工审查
- outlier_rate > 0.20 → 调查异常根因
```

---

## 9. 未来扩展方向

| 方向 | 说明 | 依赖 |
|------|------|------|
| **轨迹形状聚类** | 将轨迹按形状分类（快速收敛型/震荡型/慢速型/失败型） | 需要更多历史数据 |
| **多 Agent 轨迹关联** | 分析 subagent 调用链中的瓶颈节点 | 扩展 trace schema 增加 agent_id |
| **工具效率分析** | 按工具类型（bash/read/edit）统计效率 | 需要在 trace 中增加 tool_call 记录 |
| **轨迹语义压缩** | 用 LLM 对每轮 Critic suggestion 做摘要，减少存储 | 需要 LLM 调用 |
| **跨 Skill 基准对比** | 不同 skill 之间的质量横向对比 | 需要更多样本 |

---

## 10. 相关文件索引

| 文件 | 作用 |
|------|------|
| `scripts/gcl_runner.py` | 轨迹写入（`persist_trace`） |
| `scripts/gcl_trace_aggregate.py` | 状态聚合分析 |
| `scripts/gcl_trajectory_quality.py` | 无参考轨迹质量分析 |
| `scripts/rubric_calibrate.py` | 基于轨迹的自适应阈值校准 |
| `scripts/success_pattern_mine.py` | 成功轨迹模式挖掘 |
| `scripts/failure_pattern_extract.py` | 失败轨迹模式提取 |
| `audit-results/gcl-trace-*.json` | 原始轨迹数据 |
| `audit-results/gcl-quality-summary-*.json` | 状态聚合输出 |
| `audit-results/gcl-trajectoryquality-*.json` | 轨迹质量输出 |
| `docs/superpowers/plans/trajectory-optimization-analysis.md` | 轨迹采集优化分析 |
