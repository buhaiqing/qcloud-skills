# 基于轨迹的无参考评估 — 优化分析报告

> 文档版本：v1.0.0
> 生成日期：2026-07-17
> 维护者：qcloud-skills 团队
> 关联文档：`manual/trajectory-evaluation-metrics.md`（57 指标蓝图）、`docs/gcl-spec.md`

---

## 0. 背景与目标

从**执行轨迹（Trajectory）采集收集**视角，审视 qcloud-copilot / GCL 体系中「基于轨迹的无参考评估」（多轮轨迹质量、安全合规）的现状，找出可优化点，并定位**数据血缘断链**，提出可追溯性（Agent 决策透明、可回溯）修复方案。

**无参考评估（reference-free）**：不依赖人工标注 gold answer，仅从轨迹自身结构 / 语义判质量。

**交付物**：本报告（分析）+ 后续代码实现（按 P1–P6 落地 provenance / 血缘）。

---

## 一、当前两条评估链路的真实结构

### 链路 A — GCL 无参考评估（真正的核心）

```
gcl_runner.py 执行 tccli 命令
   └─ 每轮写入 iterations[].{generator, critic.scores(5维), decision}
   └─ trace.final.{status, failure_pattern}
   └─ persist_trace → audit-results/gcl-trace-*.json
gcl_trajectory_quality.py 事后统计（无 ground truth）：
   convergence_speed / oscillation / early_failure / safety_trajectory
   / outlier / baselines / op_type
```

- 5 维 rubric：`correctness / safety / idempotency / traceability / spec_compliance`（取值 `0/0.5/1`）。
- 证据：`scripts/gcl_trajectory_quality.py:59` `RUBRIC_DIMS`；`scripts/gcl_runner.py:67-69` 默认分；`scripts/gcl_runner.py:321` `decide(critic["scores"])`。

### 链路 B — qcloud-copilot quality/ 四个薄模块

```
dispatcher._execute_step()
   ├─ check_h(step)              → H 幻觉门（白名单拦截未知 skill/operation）
   ├─ audit_trace(...)           → .runtime/gcl/copilot/audit/<sid>/step-<id>-<ts>.json
   ├─ record_health(...)         → .runtime/health/skill-metrics.jsonl
   └─ write_reflexion(...)       → .runtime/reflexion/<date>-scratch.md（仅 failure 时）
```

- 证据：`qcloud-copilot/copilot/dispatcher.py:355-377`（`_emit_trace` / `_emit_health` / `write_reflexion` 调用）；`quality/audit.py:7` `audit_trace`；`quality/hallucination.py:154` `check_h`；`quality/health.py:11` `record_health`；`quality/reflexion.py:11` `write_reflexion`。

**关键事实**：链路 A 与链路 B **物理隔离**。`quality/` 模块不读 GCL trace，GCL 分析脚本不读 copilot 的 `.runtime/` 产物。两条链路的「质量 / 安全」结论互相看不见。

---

## 二、数据血缘断链点（核心问题）

血缘定义：一条评估结论能回溯到「哪条轨迹 → 哪一步 → 哪个评估函数/规则 → 什么输入 → 什么参数」。

| # | 断链位置 | 现状 | 影响 |
|---|---------|------|------|
| **L1** | `audit_trace` 不记 provenance | 只存 `{step_type, status, duration_ms, error, output}`，无 eval_id、无用了哪条规则、无 parent trace 链接 | step 级 trace 无法回答「为什么 status=failure」 |
| **L2** | `check_h` 返回 dict 但无 trace 关联 | `{"passed": bool, "issues": [...]}` 直接丢弃，不落盘、不进 audit_trace | H 门拦截了什么、依据哪条 `KNOWN_OPERATIONS` 完全不可追溯 |
| **L3** | GCL trace 与 copilot 会话无 join key | GCL trace 文件名 timestamp 秒级随机；copilot 用 `session_id`。无共享 `trace_id` | 无法把「某次巡检的某 step」关联到「对应 GCL 安全评分」 |
| **L4** | `record_health` 的 `trace_id` 实为 session_id | `record_health(..., trace_id=session_id)` 字段名 trace_id 但值是 session，且 health.jsonl 与 audit_trace 文件无共同外键 | 健康指标无法 join 到具体 step trace |
| **L5** | `write_reflexion` 与 GCL `failure_pattern` 双写 | copilot 写 `.runtime/reflexion/`，GCL 走 `docs/failure-patterns.md` + `reflexion_store.py`。两套失败模式不互通、不 dedup | 同一失败在两边各记一次，跨体系去重失效 |
| **L6** | 评分维度无可解释锚点 | GCL 5 维分数由 Critic 给 `0/0.5/1`，trace 里不记录每条分数的判定依据（命中哪条 rubric rule） | 「safety=0」无法回答「因为哪条安全规则」 |

---

## 三、多轮轨迹质量评估的可优化点

### Q-A：收敛 / 振荡指标只看 final，丢信息
`outlier_score` / `baselines` / `dimension_correlation` **都用 `all_scores[-1]`（最后一轮分数）**。但多轮轨迹的价值在「过程」——前几轮 safety 抖动、correctness 从 0 爬到 1 的过程被丢弃。`convergence_speed` / `oscillation_count` 已用全序列，但 baseline 与 outlier 只用末轮，口径不一致。
- 证据：`scripts/gcl_trajectory_quality.py:211` `final_scores = all_scores[-1]`；`:227-256` `compute_baselines` 取 `all_scores[-1]`；`:259-297` `dimension_correlation` 取 `all_scores[-1]`。

### Q-B：操作类型分类是脆弱的启发式
`classify_op()` 用**命令字符串 CamelCase 词匹配**（`DescribeInstances → read`）。问题：
- copilot 实际 step 的 `operation` 字段是结构化 `describe-instances`（连字符），两套命名不统一（`hallucination.py` 用 `describe-instances`，`gcl_trajectory_quality.py` 用 `DescribeInstances`）。
- 文档维度 H5 `op_type_success_rate` 标 ❌ 未实现，原因「需 trace schema 标注操作类型」——但 GCL trace 的 `generator.command` 里**已有命令**，只是没结构化提取成 `op_type` 字段落库。

### Q-C：copilot 的 quality/ 完全不参与「多轮质量」评估
copilot dispatcher 跑完一个 plan（多 step），只把每个 step 单独 `audit_trace`，**无 plan 级 / session 级轨迹质量聚合**。而 GCL 的 `gcl_trajectory_quality.py` 只读 `audit-results/gcl-trace-*.json`，读不到 copilot 的 `.runtime/`。结果：**copilot 的多轮巡检质量无人评估**。

### Q-D：安全合规覆盖盲点（文档已自认 ❌）
`manual/trajectory-evaluation-metrics.md` 维度 C 自陈：
- `C7 破坏性操作确认缺失` ⚠️、`C8 安全合规规则覆盖率` ❌、`C9 新兴安全模式` ❌
- GCL 的 safety 维度只判 **凭证泄露**（structural_critic 用正则 `SECRET_PATTERNS`）+ Critic 给分。但「破坏性操作（delete/modify）是否经过 L2 确认」在轨迹评估层**完全没有信号**——copilot 的 L2 门在 dispatcher，但 L2 通过/拒绝结果没进任何 trace。

---

## 四、安全合规评估的可优化点

### S-A：凭证泄露检测只在 structural_critic 生效
`has_credential_leak()` 在 `structural_critic_only` 模式（CI/本地 smoke）跑。生产模式 Critic 是**外部注入** JSON（`--critic-json`），**脚本不校验外部 Critic 有没有做过凭证检查**——完全信任外部 Critic 的 `safety` 分（`gcl_runner.py:143` `scores["safety"] = 0.0 if leak else 1.0` 仅在 structural 路径）。若外部 Critic 漏检，凭证泄露轨迹会带 `safety=1.0` 落盘。

### S-B：safety 维度不可逆、无 reason code
`safety_trajectory` 记录每轮 safety 分，但 **`safety=0` 时不记录原因类型**（凭证泄露？破坏性未确认？Critic 判的别的？）。`extract_failure_pattern` 用 `_FAILURE_SIGNATURES` 正则从 corpus 猜 category，是**事后启发式匹配**，非评估时结构化判定。

### S-C：copilot 的 H 门与 GCL 安全门语义重叠但不共享
copilot `check_h` 查「未知 skill/未知 operation」（白名单），GCL `decide()` 查「critic safety=0」。都算安全门，但 copilot H 结果不进 GCL trace，GCL safety 结果 copilot 也不知道。一条破坏性命令若在 copilot 被 H 门放过（operation 在白名单内）、实际执行出错，其失败模式在 `.runtime/reflexion/` 与 `docs/failure-patterns.md` 各写一份（L5）。

---

## 五、可追溯性 / 数据血缘修复方案

不改变现有评估逻辑，只在采集层补 **provenance 字段**，打通两条链路。

**P1 — 统一 `trace_id` 与 `eval_id`**
- GCL trace 文件名改用 `gcl-trace-{trace_id}.json`（trace_id = uuid），copilot 的 `audit_trace` / `record_health` 也接收并写入同一 `trace_id`（来自 `session_id` 派生的 run_id）。
- 每条评估结论带 `eval_id`：`<trace_id>:<step_id>:<rule_name>`。

**P2 — `audit_trace` 补 provenance 块**
```json
{
  "eval_id": "ses-001:step-3:check_h",
  "rule": "hallucination.KNOWN_OPERATIONS",
  "input_ref": "step.skill=qcloud-vpc-ops, step.params.operation=release-eip",
  "decision": "pass|fail",
  "reason": "operation in whitelist"
}
```

**P3 — GCL trace 每轮 critic 分数加 `rubric_rule_hits`**
记录每条维度分数为什么得这分（命中哪条 rubric 规则），让 `safety=0` 可回答「哪条规则触发」。

**P4 — 失败模式单一 sink**
`write_reflexion`（copilot）与 `failure_pattern_extract` / `reflexion_store`（GCL）合并到同一去重层，用 `(category, skill, command_normalized, error)` 统一 dedup，避免双写。

**P5 — op_type 结构化落库**
GCL trace 的 `generator` 加 `op_type` 字段（用 `classify_op` 提，但统一成 copilot 连字符命名），让 `op_type_success_rate`（H5）无需 schema 大改即可计算。

**P6 — L2 确认结果进 trace**
copilot dispatcher 在 L2 通过/拒绝时，写一条 `audit_trace` 的 `rule: safety.l2_confirm`，让「破坏性操作是否确认」在轨迹评估层有信号（补 C7）。

---

## 六、优先级与实现顺序

| 优先级 | 优化点 | 对应断链 | 工时 |
|--------|--------|---------|------|
| 🔴 高 | P1 统一 trace_id（打通两条链路） | L3/L4 | 2h |
| 🔴 高 | P6 L2 确认进 trace（补安全盲点 C7） | S-C/L2 | 2h |
| 🔴 高 | P3 critic 分数加 rule_hits（safety 可解释） | L6/S-B | 3h |
| 🟡 中 | P2 audit_trace 补 provenance | L1/L2 | 2h |
| 🟡 中 | P5 op_type 结构化落库（解锁 H5） | Q-B | 2h |
| 🟡 中 | P4 失败模式单一 sink | L5 | 3h |
| 🔵 低 | Q-A baseline/outlier 用全序列而非末轮 | Q-A | 1h |

**实现约束**（来自 `AGENTS.md`）：
- 每个优化点走独立 git worktree：`git worktree add ../qcloud-skills-<feature> -b feature/<feature>`。
- Python 改动后 `ruff check <changed-files>` 零 error。
- Markdown 含 Python 代码块时 `python3 scripts/check_markdown_python.py --root .`。
- GCL 触发检查：本报告改动涉及 `*/references/*.md` 与 `scripts/*.py` 多文件 >5 行 → 实现阶段触发 GCL 多 sub-agent 架构（Generator + ≥2 Critics）。
- 变更后 IMPL **必须**在 commit footer 记 `TE-Audit: ...`（Token Efficiency 审计）。

---

## 七、结论

「基于轨迹的无参考评估」**GCL 链路设计扎实**（5 维 rubric + 收敛/振荡/异常/outlier 全序列统计 + 自适应基线），但存在两个结构性问题：

1. **copilot 的 `quality/` 子系统与 GCL 评估体系完全隔离**——copilot 的多轮巡检质量实际处于「无人评估」状态，且两者失败模式、安全信号双写不互通。
2. **provenance 几乎为零**——任何一条质量/安全结论都无法回答「依据什么规则、来自哪一步、输入是什么」，无法满足「Agent 决策透明和可追溯」。

最该先做的是 **P1（统一 trace_id）**——它是所有血缘打通的前提，改动最小、风险最低。

---

## 八、相关文件索引

| 文件 | 角色 |
|------|------|
| `scripts/gcl_runner.py` | GCL 轨迹写入（`audit-results/gcl-trace-*.json`）、structural_critic、凭证检测 |
| `scripts/gcl_trajectory_quality.py` | 无参考轨迹质量（收敛/振荡/异常/outlier/baseline） |
| `scripts/gcl_trace_aggregate.py` | 状态聚合（pass_rate / per-skill） |
| `qcloud-copilot/copilot/quality/audit.py` | step 级 trace 落盘 |
| `qcloud-copilot/copilot/quality/hallucination.py` | H 幻觉门（skill/operation 白名单） |
| `qcloud-copilot/copilot/quality/health.py` | 技能健康指标 JSONL |
| `qcloud-copilot/copilot/quality/reflexion.py` | 失败模式写 scratch |
| `qcloud-copilot/copilot/dispatcher.py` | 调用上述四模块的编排器 |
| `manual/trajectory-evaluation-metrics.md` | 57 指标蓝图（现状自检） |
| `docs/gcl-spec.md` | GCL 运行时规范 |

---

## 九、落地状态（Status）

| 优化点 | 状态 | 合并 commit | 说明 |
|--------|------|------------|------|
| **P1** 统一 trace_id | ✅ 已完成 | `3afada6` | `run_gcl` 透传 `session_id` 为 `--trace-id`；dispatcher `_emit_trace` 非 L2 步默认 `exec.step` provenance（`eval_id=<session_id>:<step_id>:exec.step`）；`record_health(trace_id=self._session_id)` 已正确；补 `test_p1_trace_id.py`（4 测试全过） |
| **P2** audit_trace 补 provenance | ✅ 已随 P6 落地 | `06bf695` | `safety.l2_confirm` provenance 块已写入 |
| **P3** critic 分数加 rule_hits | ✅ 已完成 | `7284685` | `gcl_runner.py:385` critic 块含 `rubric_rule_hits: derive_rule_hits(...)`；`derive_rule_hits`(L194) 实现 `safety=0 → credential_leak_detected/critic_safety_zero` |
| **P4** 失败模式单一 sink | ✅ 已完成 | `bc77e0f` | `reflexion_store.py` 与 `quality/reflexion.py` 共用 `normalize_reflexion_key` 4-tuple；copilot 写 scratch→`aggregate_scratch` 合并到 `docs/failure-patterns.md`（同 GCL sink），双写已解 |
| **P5** op_type 结构化落库 | ✅ 已完成 | `b4799fc` | `gcl_runner.run_command` 返回 dict 加 `op_type`（复用 `classify_op`，read/write/delete 三态）；`gcl_trajectory_quality.operation_type_analysis` 优先读落库字段、回退 `classify_op` 兼容老 trace；H5 `op_type_success_rate` 现消费 first-class 字段 |
| **P6** L2 确认进 trace | ✅ 已完成 | `06bf695` | engine plan 级（check_l2 pass/fail 都写）+ dispatcher step 级（destructive `skill_call` step 写 `rule: safety.l2_confirm` provenance）；`run_plan`/`execute` 新增 `l2_confirmed` kwarg 透传；补 C7 安全盲点；新增 `test_p6_l2_trace.py`（5 测试全过） |

**决策记录**：
- P5 命名沿用 `classify_op` 的 read/write/delete 三态（非 copilot 连字符命名），符合"复用现有分类逻辑、不引入新命名体系"的用户决策。
- P6 采用"两层都写"策略（engine plan 级 + dispatcher step 级），满足轨迹评估层对破坏性操作确认信号的细粒度需求。

