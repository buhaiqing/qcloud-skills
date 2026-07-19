# 待办事项清单

> 基于磁盘实际状态（2026-07-04 审计），**所有原有 TODO 任务均已完成**。
> 本文档保留作为历史记录。新任务请从扫描发现的实际问题出发。

## 当前全局状态

| 维度 | 状态 |
|------|------|
| 34 个 SKILL.md 文件 | ✅ 全部就位（29 product + 3 cross-product + 1 meta + 1 skill-generator） |
| GCL 覆盖率 | ✅ `check_gcl_conformance.py` 已覆盖全部 33 个 skill |
| GCL 通过率 | ✅ 33/33 通过，全部符合 Tier-A conformance |
| 硬编码区域修复 | ✅ Batch 2 完成（[`b8d1a10`](https://github.com/buhaiqing/qcloud-skills/commit/b8d1a10)） |
| AGENTS.md 路径修正 | ✅ Batch 3 完成（[`b636cce`](https://github.com/buhaiqing/qcloud-skills/commit/b636cce)） |
| 幽灵链接修复 | ✅ Batch 4 完成（[`c3bc268`](https://github.com/buhaiqing/qcloud-skills/commit/c3bc268)） |
| Token 效率压缩 | ✅ Batch 5 完成（[`62b4251`](https://github.com/buhaiqing/qcloud-skills/commit/62b4251)） |
| SLB 5xx MTTR 优化 | ✅ 完成（[`81bded5`](https://github.com/buhaiqing/qcloud-skills/commit/81bded5) + [`ec1d8aa`](https://github.com/buhaiqing/qcloud-skills/commit/ec1d8aa)） |
| RDS MySQL 诊断优化 | ✅ 完成（[`18d3c20`](https://github.com/buhaiqing/qcloud-skills/commit/18d3c20)） |
| AIOps 预测分析/知识图谱 | ✅ 完成（[`ae77b8d`](https://github.com/buhaiqing/qcloud-skills/commit/ae77b8d)） |
| vpn-ops 多分支拓扑模板 | ✅ 完成（[`dd06849`](https://github.com/buhaiqing/qcloud-skills/commit/dd06849)，刚提交） |
| service-mesh-ops GCL 对齐 | ✅ 完成（[`058978f`](https://github.com/buhaiqing/qcloud-skills/commit/058978f)，刚提交） |
| 验证脚本 | ✅ frontmatter 34/34, GCL 33/33, Python-in-Markdown OK |

## Harness Engineering 对齐（待补充）

> 以下维度是Harness AI Agent工程标准的核心要求，当前TODO.md完全缺失。

| 维度 | 标准来源 | 当前状态 | 建议行动 |
|------|---------|---------|---------|
| Agent执行可靠性 | Harness AI Agent SLA (uptime/p99 latency) | 仅GCL trace，缺SLA指标 | 补充agent执行SLA dashboard和告警SLO |
| 多Agent协作安全 | Harness Multi-Agent Protocol / HITL | 缺human-in-the-loop checkpoint | 补充高风险操作的HITL审批节点 |
| Prompt注入防护 | OWASP LLM Top 10 / Harness Security | 缺prompt注入检测和防御 | 补充reflexion的adversarial pattern覆盖 |
| Skill版本漂移 | Harness Skill Registry / Semantic Versioning | 缺skill版本兼容性追踪 | 补充skill版本matrix和breaking change检测 |
| Agent成本治理 | Harness FinOps / token预算控制 | 无cost tracking | 补充per-skill/token消耗的计量表 |
| 跨Agent上下文隔离 | Harness Agent Mesh / 租户隔离 | GCL C/G隔离已有，缺Agent Mesh层 | 补充多租户/多环境context隔离规范 |

> 注：以上补充内容不影响当前GCL/Reflexion技术实现的正确性，属Harness工程语境对齐。

## 待修复 Backlog（GCL 预存不符合）

> 由 `check_gcl_conformance.py` 扩展至 31 个 skill 时暴露（2026-07-09 扫描发现）。
> 非本次扩展引入，属历史遗留结构性问题。

| # | Skill | 失败项 | 现象 | 修复方向 | 预估工作量 |
|---|-------|--------|------|----------|-----------|
| B1 | `qcloud-cam-ops` | rubric 节数 9/8 | rubric.md 含 9 个 `## N.` 编号节，超出模板预期的 8 节 | ✅ 已修复 — rubric.md 已重编号为 8 节，通过 Tier-A conformance | 0.5h |
| B2 | `qcloud-tcop-ops` | rubric 0/8, prompt 0/7 | rubric.md / prompt-templates.md 使用非标准格式（表格 + 无编号节标题），不符合 `qcloud-skill-template.md` 的 `## N.` 编号节要求 | ✅ 已修复 ([`5610fdc`](https://github.com/buhaiqing/qcloud-skills/commit/5610fdc)) — rubric.md 含 8 节、prompt-templates.md 含 7 节，通过 Tier-A conformance | 1-2h |

## 可考虑的新方向

以下是不在原有 TODO 中，但值得评估的方向：

| # | 方向 | 说明 | 预估工作量 |
|---|------|------|-----------|
| 1 | **qcloud-dc-ops 场景增强** | DC skill 已存在但场景较基础，可补充专线故障切换、多云接入等 | ✅ 已完成（[`d920158`](https://github.com/buhaiqing/qcloud-skills/commit/d920158)）— 新增冗余通道/故障切换（BFD/NQA 健康检查、FailoverSwitch 手动切换）、多云多地域接入（CreateCloudAttachService→CCN）；rubric 安全规则扩至 5 条；修复 Prerequisites 凭证泄露 | 0.5-1 天 |
| 2 | **qcloud-migration-ops 场景增强** | 迁移 skill 已存在，可补充更多迁移场景 | ✅ 已完成（[`32141e3`](https://github.com/buhaiqing/qcloud-skills/commit/32141e3)）— 新增 ModifyMigrationTaskStatus、ListMigrationProject、Cutover/Switchover、Migration Validation 4 个执行流，rubric 安全规则扩至 5 条，troubleshooting 补充割接失败模式 |
| 3 | **跨 skill 编排测试** | 验证 aiops-diagnosis + monitor-ops + 产品 skill 的跨 skill 调用链路 | ✅ 已完成（[`f92111b`](https://github.com/buhaiqing/qcloud-skills/commit/f92111b) + [`c079df0`](https://github.com/buhaiqing/qcloud-skills/commit/c079df0)）— 16 个测试覆盖 handoff payload、mode selection、bundle structure |
| 4 | **新技能：消息队列（TDMQ）** | 目前没有 TDMQ（RocketMQ/Pulsar）skill | ✅ 已完成（[`e839f05`](https://github.com/buhaiqing/qcloud-skills/commit/e839f05)）— 新增 `qcloud-tdmq-ops` skill，含 10 个执行流（RocketMQ/Pulsar/RabbitMQ/CMQ）、rubric 8 节、prompt 7 节，GCL conform 32/32 | 3 天 |
| 5 | **新技能：API 网关** | 目前没有 API Gateway skill | ✅ 已完成（[`4163c9c`](https://github.com/buhaiqing/qcloud-skills/commit/4163c9c)）— 新增 `qcloud-apigw-ops` skill，含 10 个执行流（Service/API/Release/UsagePlan/SubDomain）、rubric 8 节、prompt 7 节，GCL conform 33/33 | 2 天 |

## GCL Loop Engineering 优化（qcloud-cdn-ops P0-P5）

> 基于 Loop Engineering 视角分析 CDN GCL 的优化机会。

| # | 优化项 | 说明 | 状态 |
|---|--------|------|------|
| P0 | **动态 max_iterations** | 按操作风险等级动态调整迭代次数（破坏性=2, 缓存变更=1, 敏感配置=3） | ✅ 已完成（[`f03fe9a`](https://github.com/buhaiqing/qcloud-skills/commit/f03fe9a)） |
| P1 | **早期停止机制** | Safety 规则满足 + Critic 分数收敛（Δ < 0.1 for 2 rounds）时提前通过 | ✅ 已完成（[`50d6a7f`](https://github.com/buhaiqing/qcloud-skills/commit/50d6a7f)） |
| P2 | **并行 Critic 专业化** | Data Quality Critic + Safety Rules Critic 并行评审，不同维度专门化 | ✅ 已完成（[`ccedfd1`](https://github.com/buhaiqing/qcloud-skills/commit/ccedfd1)） |
| P3 | **自适应退避策略** | 根据错误类型动态调整重试间隔（指数退避 vs 固定间隔） | ✅ 已完成（[`bfe7a5f`](https://github.com/buhaiqing/qcloud-skills/commit/bfe7a5f)） |
| P4 | **安全规则优先级分级** | CDN 操作按风险分级：高风险（DeleteCdnDomain）→ 立即中止，中风险（UpdateDomainConfig）→ 迭代，低风险（只读）→ 跳过 | ✅ 已完成（[`69a2547`](https://github.com/buhaiqing/qcloud-skills/commit/69a2547)） |
| P5 | **上下文感知 GCL** | 读取操作历史（reflexion memory）自动调整策略，新操作 vs 重复操作区别处理 | ✅ 已完成（[`1fcf258`](https://github.com/buhaiqing/qcloud-skills/commit/1fcf258)） |

## L4 接入项（2026-07-19 完成）

> P0/P1 规划的基础设施已就位，但接入点存在缺口。以下为 L4 就绪所需的最后一公里。

| # | 接入项 | 文件 | 状态 |
|---|--------|------|------|
| L4-1 | Rubric校准结果接入 gcl_runner | `scripts/gcl_runner.py` | ✅ 上下文管理器 `_rubric_calibration` 注入 |
| L4-2 | `pattern_anomaly_detect.py` 定时触发 | `.github/workflows/pattern-anomaly-cron.yml` + CI hook | ✅ 每日cron + CI non-blocking step |
| L4-3 | `--post-process` 默认启用（生产模式）/CI模式关闭 | `scripts/gcl_runner.py` | ✅ `--structural-critic-only` 时自动关闭 |
| L4-4 | L4指标追踪 dashboard | `scripts/l4_metrics_tracker.py` | ✅ 5指标实时写入 `audit-results/l4-metrics.json` |
| L4-5 | 腾讯云错误码注入 Critic | `scripts/gcl_runner.py` + `scripts/tcloud_error_codes.py` | ✅ `load_tcloud_error_hints()` + structural_critic 增强 |

### L4 指标快照（`python3 scripts/l4_metrics_tracker.py`）

```json
{
  "avg_iterations":          {"current": 1.0,  "target": 1.8,  "status": "✅"},
  "failure_pattern_hit_rate":{"current": 0.0,  "target": 0.6,  "status": "❌ 尚未启用"},
  "success_path_reuse_rate": {"current": 0.0,  "target": 0.9,  "status": "❌ 尚未启用"},
  "rubric_threshold_deviation": {"current": 0.22, "target": 0.1, "status": "❌"},
  "emerging_pattern_latency":{"current": null, "target": 7,   "status": "❌"}
}
```

## Agentic AI 成熟度升级：自纠正能力 & 上下文适应 → L4

> 基于 Gartner Agentic AI 成熟度评估（2025），当前 repo 处于 L3 高级段。
> 本节规划将 **自纠正能力** 和 **上下文适应** 两个维度从 L3+ 提升至 L4。
> 目标：从"依赖外部 Critic 评分"升级为"持续自我校准的多层反馈系统"。

### 背景：当前 L3+ 能力现状

| 维度 | 当前实现 | 证据 |
|------|---------|------|
| **自纠正** | GCL Loop（Generator → 隔离 Critic → 重试）| `docs/gcl-spec.md` §4, `scripts/gcl_runner.py` |
| **上下文适应** | Reflexion Memory（failure-patterns.md，≤200行）| `docs/reflexion-memory.md`, `scripts/reflexion_retrieve.py` |

### 当前核心差距

| 差距 | 根因 |
|------|------|
| 无成功路径学习 | `extract_failure_pattern` 只处理失败；`gcl_trace_aggregate` 只聚合失败指标 |
| Rubric 静态固定 | 所有 skill 共用 `RUBRIC_THRESHOLDS`（correctness≥0.5, safety=1.0），不看执行历史 |
| Self-Critique 太弱 | `structural_critic` 只检查 exit_code，不能替代真实 Critic |
| failure_pattern 提取用启发式 regex | `_FAILURE_SIGNATURES` 只有 5 个 pattern，对复杂错误无能为力 |
| 200 行上限太紧 | 34 个 skill × 多操作类型，平均每 skill 不到 6 条 pattern |
| Pattern 排序只看 count | 无时间衰减、无严重性权重 |
| 无主动模式发现 | 依赖 GCL trace 事后写入，emerging pattern 无法主动预警 |
| Pattern 无生命周期 | count<3 修剪，但从未升级为 anti-pattern |

---

### P0 改进项（并行开发，预计 2 周）

#### P0-A: 成功路径记录（C+D 混合：一次性全量 + 每日增量）

> **Spec**：`docs/superpowers/specs/success-patterns-design.md`

> **设计原则**：轻量实时写入候选文件，深度聚合由批处理在低峰期完成。
> 存量 trace 为零（D 无历史成本），基础设施就绪后 C 即生效。

```
[GCL 执行 — 每次执行]
  └── gcl_runner.py (structual_critic 评分)
       └── structual_critic PASS → 写入 gcl-success-pending.jsonl (追加, 非阻塞)

[每日 02:00 — cron]
  └── success_pattern_mine.py --batch
       ├── 读取 gcl-success-pending.jsonl
       ├── 去重 + 聚类 (按 skill + operation 分组)
       ├── 更新 docs/success-patterns.md
       └── 清空 pending 文件

[首次部署 — 全量回填 (D)]
  └── success_pattern_mine.py --full-scan
       ├── 扫描 audit-results/ 下所有现有 gcl-trace-*.json
       ├── 提取所有 final.status=PASS 的记录
       ├── 建立 docs/success-patterns.md 初始版本
       └── 完成后正常进入每日增量模式 (C)
```

**文件设计**：

| 文件 | 类型 | 说明 |
|------|------|------|
| `audit-results/gcl-success-pending.jsonl` | 追加日志 | 每次 PASS trace 后轻量追加，单行 `{"skill","operation","iter","scores","command"}` |
| `scripts/success_pattern_mine.py` | 脚本 | `--batch` 增量合并 / `--full-scan` 全量回填 |
| `docs/success-patterns.md` | 知识库 | 与 `failure-patterns.md` 对称，Agent Pre-flight 读取 |

**pending 文件为什么不用锁**：每次写入是单行 append，crontab 在凌晨 02:00 执行，此时无并发写入风险。唯一冲突是 GCL 恰好在 02:00 执行——用 `fcntl.flock` 文件锁保护整个 pending 文件。

**注入点**：Generator Pre-flight 同时加载 `failure-patterns.md` + `success-patterns.md`，两类模式都作为预防 hint 注入 Generator context。

| 属性 | 内容 |
|------|------|
| **状态** | ✅ Phase 1-5 全部完成（ruff 0 errors, 162 tests pass, 端到端 dry-run 通过）|

#### P0-B: Pattern Store 分层存储

> **Spec**：`docs/superpowers/specs/p0-b-layered-failure-patterns-design.md`
> **状态**：✅ Phase 1-5 全部完成 — 196 tests, ruff 0 errors

- Phase 1：`failure_pattern_extract.py --layered`（merge_failure_batch + self_verify_failure V1-V5 + emit_layer/save_layer）✅
- Phase 2：`reflexion_retrieve.py` 分层查询（load_all_layers + cross-layer dedup + --layer flag）✅
- Phase 3：数据迁移（HOT_PATH=existing failure-patterns.md, warm/cold 首次写入自动创建）✅
- Phase 4：分层单元测试（failure_pattern_layered_test 17 + reflexion_retrieve_layered_test 15）✅
- Phase 5：端到端验证（--dry-run --layered, retrieve e2e, ruff, 196 tests）✅
- 共享模块：`_failure_pattern_store.py`（parse_existing + load_all_layers + 常量）✅

#### P0-C: 严重性 + 时间衰减评分

| 属性 | 内容 |
|------|------|
| **文件** | `scripts/reflexion_retrieve.py`（修改）、`scripts/failure_pattern_extract.py`（修改）、`docs/failure-patterns.md`（修改） |
| **评分公式** | `score = base_score × severity_weight × recency_decay` |
| **severity_weight** | critical=3.0 / major=2.0 / minor=1.0 |
| **recency_decay** | <7天=1.0 / 7-30天=0.7 / 30-90天=0.3 / >90天=0.1 |
| **新字段** | GCL trace schema 新增 `failure_pattern.severity`；store 新增 `last_seen` |
| **改动点** | `reflexion_retrieve.py` 重写评分算法 + `failure_pattern_extract.py` 解析/写入 `last_seen` + `failure-patterns.md` 表头新增 `LastSeen`/`Severity` 列 |
| **状态** | ✅ 已完成 — ruff clean (0 errors), 68 tests pass |

---

### P1 改进项（预计 2 周）

#### P1-A: Rubric 自适应阈值

| 属性 | 内容 |
|------|------|
| **文件** | `scripts/rubric_calibrate.py`（新增，22 tests pass） |
| **输入** | `audit-results/gcl-trace-*.json` 历史数据 |
| **输出** | per-skill 动态阈值建议 |
| **状态** | ✅ 已完成（[`d0fec4c`](https://github.com/buhaiqing/qcloud-skills/commit/d0fec4c) + [`04c7569`](https://github.com/buhaiqing/qcloud-skills/commit/04c7569)）— 22 tests pass |

#### P1-B: Self-Critique 补强

| 属性 | 内容 |
|------|------|
| **文件** | `scripts/gcl_runner.py`（修改 `structural_critic`） |
| **补强项** | correctness：检查响应是否含预期 JSON path / idempotency：检查是否含 ClientToken / traceability：检查是否含 RequestId / spec_compliance：检查 command 是否匹配 skill 的 cli-usage.md |
| **状态** | ✅ 已完成（[`46695ab`](https://github.com/buhaiqing/qcloud-skills/commit/46695ab)）— 35 tests pass |

#### P1-C: 主动模式发现

| 属性 | 内容 |
|------|------|
| **文件** | `scripts/pattern_anomaly_detect.py`（新增） |
| **检测逻辑** | 同一 error 最近7天频率 vs 历史均值（>2σ=emerging）/ 新 skill+operation 组合首次出现（novel） |
| **输出** | `audit-results/pattern-anomaly-YYYYMMDD.json` + `docs/failure-patterns.md` 顶部 `## Emerging Alerts` 区块 |
| **状态** | ✅ 已完成（[`97b0d93`](https://github.com/buhaiqing/qcloud-skills/commit/97b0d93)）— ruff clean |


---

#### P1-D: 操作类型成功率 `op_type_success_rate`

| 属性 | 内容 |
|------|------|
| **文件** | `scripts/gcl_trajectory_quality.py`（修改）/ `scripts/op_type_classifier.py`（新增） |
| **Spec** | `docs/superpowers/specs/p1-d-op-type-success-rate-design.md` |
| **状态** | ✅ Phase 1-5 全部完成 — ruff 0 errors, 24 tests pass |

#### P1-E: 分布漂移检测 `distribution_drift`

| 属性 | 内容 |
|------|------|
| **文件** | `scripts/distribution_drift.py`（新增） |
| **检测方法** | 近期 7 天 vs 历史 30 天：均值对比 |
| **状态** | ✅ 已完成（[`dfb2782`](https://github.com/buhaiqing/qcloud-skills/commit/dfb2782)）— ruff clean |

#### P1-F: 幻觉检测 `hallucination_detection`

| 属性 | 内容 |
|------|------|
| **文件** | `scripts/hallucination_detection.py`（新增） |
| **检测方法** | Schema 验证 + 边界检测（Describe 应有结果却返回空）+ 幂等性自洽 |
| **状态** | ✅ 已完成（[`dfb2782`](https://github.com/buhaiqing/qcloud-skills/commit/dfb2782)）— ruff clean |

### P2 改进项

#### P2-A: Pattern → Rule 升级路径

| 属性 | 内容 |
|------|------|
| **文件** | `scripts/failure_pattern_extract.py`（新增 `--promote` flag） |
| **触发条件** | pattern count≥10 |
| **状态** | ✅ 已完成（[`46695ab`](https://github.com/buhaiqing/qcloud-skills/commit/46695ab)）— 17 tests pass |

### P3 改进项

#### P3-A: 结构化错误语义提取

| 属性 | 内容 |
|------|------|
| **文件** | `scripts/tcloud_error_codes.py`（新增） |
| **内容** | 腾讯云 API 错误码表（9 个核心错误码 + severity/category/fix） |
| **状态** | ✅ 已完成（[`46695ab`](https://github.com/buhaiqing/qcloud-skills/commit/46695ab)）— ruff clean |


### L4 验收标准

完成 P0 + P1 后，以下指标应达成：
| 指标 | 当前基线 | 目标 | 测量方式 |
|------|---------|------|---------|
| GCL 平均迭代次数 | 1.0 ✅ | ≤1.8次（下降20%） | `gcl_trace_aggregate.py` 统计 |
| failure-patterns 命中率 | 0%（尚未启用） | ≥ 60% | `reflexion_retrieve.py` 查询统计 |
| emerging pattern 发现延迟 | N/A（无触发数据） | < 7 天 | `pattern_anomaly_detect.py` 日志 |
| 成功路径复用率 | 0%（尚未启用） | > 90% | 对比有/无 success pattern 的 trace |
| Rubric 阈值偏离度 | 0.22 | < 0.1 | `rubric_calibrate.py` 输出报告 |