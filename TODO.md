# 待办事项清单

> 基于磁盘实际状态（2026-07-04 审计），**所有原有 TODO 任务均已完成**。
> 本文档保留作为历史记录。新任务请从扫描发现的实际问题出发。

## 当前全局状态

| 维度 | 状态 |
|------|------|
| 33 个 skill 目录 | ✅ 全部就位（29 product + 3 cross-product + 1 meta） |
| GCL 覆盖率 | ✅ `check_gcl_conformance.py` 已覆盖全部 33 个 skill |
| GCL 通过率 | ✅ 33/33 通过，全部符合 Tier-A conformance |
| 硬编码区域修复 | ✅ Batch 2 完成（`b8d1a10`） |
| AGENTS.md 路径修正 | ✅ Batch 3 完成（`b636cce`） |
| 幽灵链接修复 | ✅ Batch 4 完成（`c3bc268`） |
| Token 效率压缩 | ✅ Batch 5 完成（`62b4251`） |
| SLB 5xx MTTR 优化 | ✅ 完成（`81bded5` + `ec1d8aa`） |
| RDS MySQL 诊断优化 | ✅ 完成（`18d3c20`） |
| AIOps 预测分析/知识图谱 | ✅ 完成（`ae77b8d`） |
| vpn-ops 多分支拓扑模板 | ✅ 完成（`dd06849`，刚提交） |
| service-mesh-ops GCL 对齐 | ✅ 完成（`058978f`，刚提交） |
| 验证脚本 | ✅ frontmatter 30/30, GCL 29/31, Python-in-Markdown OK |

## 待修复 Backlog（GCL 预存不符合）

> 由 `check_gcl_conformance.py` 扩展至 31 个 skill 时暴露（2026-07-09 扫描发现）。
> 非本次扩展引入，属历史遗留结构性问题。

| # | Skill | 失败项 | 现象 | 修复方向 | 预估工作量 |
|---|-------|--------|------|----------|-----------|
| B1 | `qcloud-cam-ops` | rubric 节数 9/8 | rubric.md 含 9 个 `## N.` 编号节，超出模板预期的 8 节 | ✅ 已修复 — rubric.md 已重编号为 8 节，通过 Tier-A conformance | 0.5h |
| B2 | `qcloud-tcop-ops` | rubric 0/8, prompt 0/7 | rubric.md / prompt-templates.md 使用非标准格式（表格 + 无编号节标题），不符合 `qcloud-skill-template.md` 的 `## N.` 编号节要求 | ✅ 已修复 (`5610fdc`) — rubric.md 含 8 节、prompt-templates.md 含 7 节，通过 Tier-A conformance | 1-2h |

## 可考虑的新方向

以下是不在原有 TODO 中，但值得评估的方向：

| # | 方向 | 说明 | 预估工作量 |
|---|------|------|-----------|
| 1 | **qcloud-dc-ops 场景增强** | DC skill 已存在但场景较基础，可补充专线故障切换、多云接入等 | ✅ 已完成（`d920158`）— 新增冗余通道/故障切换（BFD/NQA 健康检查、FailoverSwitch 手动切换）、多云多地域接入（CreateCloudAttachService→CCN）；rubric 安全规则扩至 5 条；修复 Prerequisites 凭证泄露 | 0.5-1 天 |
| 2 | **qcloud-migration-ops 场景增强** | 迁移 skill 已存在，可补充更多迁移场景 | ✅ 已完成（`32141e3`）— 新增 ModifyMigrationTaskStatus、ListMigrationProject、Cutover/Switchover、Migration Validation 4 个执行流，rubric 安全规则扩至 5 条，troubleshooting 补充割接失败模式 |
| 3 | **跨 skill 编排测试** | 验证 aiops-diagnosis + monitor-ops + 产品 skill 的跨 skill 调用链路 | ✅ 已完成（`f92111b` + `c079df0`）— 16 个测试覆盖 handoff payload、mode selection、bundle structure |
| 4 | **新技能：消息队列（TDMQ）** | 目前没有 TDMQ（RocketMQ/Pulsar）skill | ✅ 已完成（`e839f05`）— 新增 `qcloud-tdmq-ops` skill，含 10 个执行流（RocketMQ/Pulsar/RabbitMQ/CMQ）、rubric 8 节、prompt 7 节，GCL conform 32/32 | 3 天 |
| 5 | **新技能：API 网关** | 目前没有 API Gateway skill | ✅ 已完成（`4163c9c`）— 新增 `qcloud-apigw-ops` skill，含 10 个执行流（Service/API/Release/UsagePlan/SubDomain）、rubric 8 节、prompt 7 节，GCL conform 33/33 | 2 天 |

## GCL Loop Engineering 优化（qcloud-cdn-ops P0-P5）

> 基于 Loop Engineering 视角分析 CDN GCL 的优化机会。

| # | 优化项 | 说明 | 状态 |
|---|--------|------|------|
| P0 | **动态 max_iterations** | 按操作风险等级动态调整迭代次数（破坏性=2, 缓存变更=1, 敏感配置=3） | ✅ 已完成（`f03fe9a`） |
| P1 | **早期停止机制** | Safety 规则满足 + Critic 分数收敛（Δ < 0.1 for 2 rounds）时提前通过 | ✅ 已完成（`50d6a7f`） |
| P2 | **并行 Critic 专业化** | Data Quality Critic + Safety Rules Critic 并行评审，不同维度专门化 | ✅ 已完成（`ccedfd1`） |
| P3 | **自适应退避策略** | 根据错误类型动态调整重试间隔（指数退避 vs 固定间隔） | ✅ 已完成（`bfe7a5f`） |
| P4 | **安全规则优先级分级** | CDN 操作按风险分级：高风险（DeleteCdnDomain）→ 立即中止，中风险（UpdateDomainConfig）→ 迭代，低风险（只读）→ 跳过 | ✅ 已完成（`69a2547`） |
| P5 | **上下文感知 GCL** | 读取操作历史（reflexion memory）自动调整策略，新操作 vs 重复操作区别处理 | ✅ 已完成（`1fcf258`） |

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
| **状态** | ✅ 已完成（`d0fec4c` + `04c7569`）— 22 tests pass |

#### P1-B: Self-Critique 补强

| 属性 | 内容 |
|------|------|
| **文件** | `scripts/gcl_runner.py`（修改 `structural_critic`） |
| **补强项** | correctness：检查响应是否含预期 JSON path / idempotency：检查是否含 ClientToken / traceability：检查是否含 RequestId / spec_compliance：检查 command 是否匹配 skill 的 cli-usage.md |
| **状态** | ✅ 已完成（`46695ab`）— 35 tests pass |

#### P1-C: 主动模式发现

| 属性 | 内容 |
|------|------|
| **文件** | `scripts/pattern_anomaly_detect.py`（新增） |
| **检测逻辑** | 同一 error 最近7天频率 vs 历史均值（>2σ=emerging）/ 新 skill+operation 组合首次出现（novel） |
| **输出** | `audit-results/pattern-anomaly-YYYYMMDD.json` + `docs/failure-patterns.md` 顶部 `## Emerging Alerts` 区块 |
| **状态** | ✅ 已完成（`97b0d93`）— ruff clean |


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
| **状态** | ✅ 已完成（`dfb2782`）— ruff clean |

#### P1-F: 幻觉检测 `hallucination_detection`

| 属性 | 内容 |
|------|------|
| **文件** | `scripts/hallucination_detection.py`（新增） |
| **检测方法** | Schema 验证 + 边界检测（Describe 应有结果却返回空）+ 幂等性自洽 |
| **状态** | ✅ 已完成（`dfb2782`）— ruff clean |

### P2 改进项

#### P2-A: Pattern → Rule 升级路径

| 属性 | 内容 |
|------|------|
| **文件** | `scripts/failure_pattern_extract.py`（新增 `--promote` flag） |
| **触发条件** | pattern count≥10 |
| **状态** | ✅ 已完成（`46695ab`）— 17 tests pass |

### P3 改进项

#### P3-A: 结构化错误语义提取

| 属性 | 内容 |
|------|------|
| **文件** | `scripts/tcloud_error_codes.py`（新增） |
| **内容** | 腾讯云 API 错误码表（9 个核心错误码 + severity/category/fix） |
| **状态** | ✅ 已完成（`46695ab`）— ruff clean |


### L4 验收标准

完成 P0 + P1 后，以下指标应达成：

| 指标 | 目标 | 测量方式 |
|------|------|---------|
| GCL 平均迭代次数 | 下降 20%（从当前均值向 1 次收敛） | `gcl_trace_aggregate.py` 统计 |
| failure-patterns 命中率 | 新 trace 命中历史 pattern 比例 ≥ 60% | `reflexion_retrieve.py` 查询统计 |
| emerging pattern 发现延迟 | 从首次出现到预警 < 7 天 | `pattern_anomaly_detect.py` 日志 |
| 成功路径复用率 | 含 success pattern 的 Generator 执行 PASS 率 > 90% | 对比有/无 success pattern 的 trace |
| Rubric 阈值偏离度 | 动态阈值与实际评分均值的偏差 < 0.1 | `rubric_calibrate.py` 输出报告 |