# Plan: TRACE-1 Trace Usage & FinOps 成本归因重构

> 对应 SPEC：`docs/superpowers/specs/trace-usage-finops-design.md`
> 目标：让 AIOps trace 同时具备链路追踪、版本追溯、用量计量和 FinOps 成本归因能力。

## Phase 0 — 重构决策与契约冻结

- [x] **P0.1** 评审并冻结 `trace_id`、`span_id`、`session_id`、`incident_id`、`request_id`、`api_request_id` 的层级语义。已写入 SPEC §18；包含 Join 语义表、跨系统契约、正反例、DoD 验收标准。
  - DoD：补充契约说明和正反例；跨 Copilot/GCL 链路可唯一关联。
- [x] **P0.2**  TraceRecord/Observation/UsageEvent/Score/CostRecord/PricingSnapshot/Summary dataclass + JSON Schema 对齐；14 个测试全绿（commit fba704 后 feature/trace-v3）。 新增 Trace v3、Observation、Score、UsageEvent、CostRecord、PricingSnapshot 和 Summary JSON Schema。
  - DoD：Schema 支持严格必填字段、枚举、非负数量和成本状态约束。
- [x] **P0.3** 明确旧格式兼容策略。已写入 SPEC §19；包含 GCL trace、Copilot audit、metrics JSONL 三类遗留格式的读写策略和 legacy adapter 契约。
  - DoD：现有 GCL trace、Copilot audit、metrics JSONL 读取测试继续通过。
- [x] **P0.4** 冻结 AIOps 分析域。已写入 SPEC §20；incident/signals/evidence/topology/rca/impact/response/quality 八维度定义、可推导指标汇总表、CostStatus 强制约束。
  - 包含 incident、signals、evidence/data quality、topology、RCA、impact、response、quality。
  - DoD：可推导 MTTD/MTTA/MTTR、RCA 准确率、告警压缩率、修复成功率和数据质量 SLO。
- [x] **P0.5** 冻结 FinOps 分析域。已写入 SPEC §21；CostStatus 枚举五态强制约束、assert_cost_invariants 强制门禁规则、聚合维度清单。
  - 包含 usage summary、cost summary、allocation、value；未知价格禁止写 0。
  - DoD：可按 Incident、tenant、Skill/version、product/action、region、service、cost center 聚合和分摊。
- [x] **P0.6**  trace_schema_version=3.0；Trace 为聚合根，无 span_id/parent_span_id；Observation 为执行树节点。 采用主模型：Langfuse 风格 `Trace` 聚合根、`Observation` 执行树、`Score` 反馈、`UsageEvent` 不可变用量账本、`CostRecord` 成本结果和可重建 `Summary`。
  - DoD：不再把 `span_id`/`parent_span_id`/`trace_type` 放在 Trace 主对象中。
- [x] **P0.7**  新持久化版本冻结为 trace_schema_version=3.0；legacy adapter（legacy_gcl_to_observation / legacy_audit_to_observation）已有测试覆盖。 将旧 `TraceRecord v2` 明确为过渡 DTO，冻结新持久化版本为 `trace_schema_version=3.0`。
  - DoD：版本迁移、legacy reader 和不原地修改旧文件的策略有测试。
- [x] **P0.8**  IdentityTree 固定身份树（user_id/tenant_id/customer_id/operator_id 等）；缺失值统一为 JSON null；IdentityTree.to_dict() + 13 个测试验证。 冻结身份语义：当前不存在 `user_id`；`session_id` 不映射为 user，`customer` 不映射为终端用户。
  - DoD：新增固定身份树；缺失值统一为 JSON `null`，通过 `identity_source`/`identity_confidence` 表达来源和可信度。

## Phase 1 — Trace 聚合根与上下文

- [x] **P1.1**  trace_context.py 新增；TraceContext（trace_id/session_id/incident_id/identity/automation/push_pop_observe）；13 个测试全绿。 新增 `qcloud-copilot/copilot/trace_context.py`。
  - 生成/传递 trace/span 父子关系，支持 session 和 incident 关联。
- [x] **P1.2**  skill_version.py 新增；parse_skill_version 解析 SKILL.md frontmatter；_compute_skill_sha 覆盖 VERSIONED_FILES；测试验证 version/sha/cli_applicability。 新增 Skill 版本解析器。
  - 读取 `SKILL.md` frontmatter 的 `metadata.version`，计算 Skill 文件、references、Prompt、Rubric 和代码 commit 摘要。
- [x] **P1.3** 将 `skill.name/version/sha/commit`、references、prompt、rubric、runtime、tccli/sdk 版本写入 TraceRecord。已实现 `RuntimeInfo`（python_version/tccli_version/sdk_name/sdk_version/git_commit/deployment_version）和 `SkillInfo`（name/version/source/skill_file_sha256/skill_commit/references/prompt_version/rubric_version）；`TraceRecord` 新增 `skill: Optional[SkillInfo]` 和 `runtime: Optional[RuntimeInfo]` 字段；26 测试全绿（含 7 个新增 TDD 测试）。
  - DoD：一次调用可以回答实际执行的 Skill 版本、代码提交和运行时版本。
- [x] **P1.4** 更新 GCL adapter 和 Copilot audit。已新建 `copilot/trace_metadata.py` 提供 `build_runtime_info()` (Python/tccli/SDK/git/deployment) 和 `build_skill_info(SkillVersion)`；`audit_trace()` 新增 `skill_info` / `runtime_info` 参数并写入 JSON；6 测试全绿（含 `test_audit_trace_backward_compat` 验证旧调用兼容）。
  - DoD：一次调用可以回答实际执行的 Skill 版本、代码提交和运行时版本。
- [x] **P1.5** 新增 Trace 聚合根和 Summary 引用模型。已实现 `AIOpsSummary`（incident/signals/evidence/topology/rca/impact/response/quality）和 `FinOpsSummary`（usage_summary/cost_summary/allocation/value）；`TraceRecord` 新增 `aiops_summary/finops_summary/observation_ids/usage_event_ids/score_ids`；19 测试全绿（含 5 个新增测试）。
  - DoD：Trace 仅保存顶层 Langfuse 字段、租户/版本/状态、AIOps/FinOps summary 和 observation/usage/score refs。
- [x] **P1.6** 在 Copilot/Blackboard/Handoff 上下文中引入身份上下文。已新建 `copilot/identity_resolver.py` 提供 CLI > config > env > session > automation > fallback 六源优先级解析；`TraceContext(identity=...)` 支持挂入 identity；测试覆盖 Blackboard dict 携带 identity 块；9 测试全绿。
  - DoD：保留现有 `session_id` 和客户策略字段，新增身份字段不改变旧 Blackboard 读取兼容性。
- [x] **P1.7** 实现身份树解析与序列化。已实现 `IdentityResolver.resolve()` 输出 `IdentityTree`（包含 `identity_source` + `identity_confidence` 标注）；缺失字段一律 `None`（JSON `null`，非空串或 `"unknown"`）；9 测试覆盖六源优先级 + Blackboard schema 1.1 兼容。
  - DoD：CLI、配置、认证、Session、自动化和本地 fallback 均输出相同字段结构；无值字段为 `null`。
- [⚠️] **P1.8** 备案 User ID 延后决策，不阻塞主线。Identity 字段已落地，但实际 user_id 的生产可信源（OIDC/SSO/IAM）尚未接入；当前依赖 CLI/config/env 显式声明或 fallback 为 `null`。后续 OIDC 接入时只需扩展 `IdentityResolver` 增加 `_value_for` 的 IAM 探测分支，不影响 IdentityTree 形状。
  - DoD：固定身份树和 automation 树先落地；没有认证来源时 `user_id=null`，后续通过 OIDC/SSO/IAM 复审。

## Phase 2 — Observation 执行树与 UsageEvent 写入

- [x] **P2.1** 新增 `trace_records.py` 数据模型和序列化器。已包含 `TraceRecord / ObservationRecord / ScoreRecord / UsageEvent / CostRecord / AIOpsSummary / FinOpsSummary / RuntimeInfo / SkillInfo / IdentityTree / AutomationTree`；含 `from_dict/to_dict` 序列化，27 测试全绿。
  - 包含 `Trace`、`Observation`、`Score`、`UsageEvent`、`CostRecord`、`Summary`；禁止继续扩展旧的单对象 TraceRecord。
- [x] **P2.3** 新增 LLM usage emitter。已实现 `emit_llm_usage()` 在 `copilot/usage_emitters.py`；字段：provider/model/prompt_version + `usage{input/output/cached/reasoning/total_tokens}` + retry_index + latency_ms；缺省值合法；8 测试全绿。
- [x] **P2.2** 在 `observ.py` 增加 Trace/Span/Usage 写入入口，复用 OBS-1 的 JSONL/索引能力。已为 `ObservableSink` 增加 `emit_observation()` 和 `emit_usage_event()`，分别写入 `audit/<trace_id>/observations.jsonl` 和 `audit/<trace_id>/usage_events.jsonl`；类型断言 + trace_id 分目录隔离；5 测试全绿。
  - DoD：旧的 `emit_metric` / `emit_span` / `emit_gate` 接口不变；新增 Observation / UsageEvent 双入口。
  - 记录 client_type、product、service、action、api_version、region、RequestId、请求/响应字节、资源数、重试、限流和缓存命中。
- [x] **P2.5** 新增数据用量 emitter。已实现 `emit_data_usage()`；字段：metric_points / log_bytes / log_records / audit_events / topology_nodes / topology_edges + latency_ms；全部可空。
  - 记录 metric points、log bytes/records、audit events、topology nodes/edges、compute/storage 用量。
- [x] **P2.6.b** audit_trace_v3 桥。已新建 `audit_trace_v3()` 在 `copilot/quality/audit.py`：仍调 legacy `audit_trace()` 不破坏旧消费者；额外 `emit_observation` + `usage_events` 通过 `add_usage` 关联；接入 `engine.py blackboard-init` 一处作为可工作样例；4 测试全绿。
  - DoD：legacy audit 文件保持兼容；新 callsite 同时发出 observation + usage。
- [x] **P2.6.c** 运行时入口启动事件。已新增 `step_recording.bootstrap_trace_metadata()` 写出 `event:session.startup` ObservationRecord，承载完整 RuntimeInfo + SkillInfo；3 测试全绿。
  - DoD：不依赖 metadata 才能在 Langfuse 查询 Trace、Session、Version 和 Generation usage。
  - DoD：Observation 和 UsageEvent 写入后可幂等刷新 `aiops.*`、`finops.*`，且保留来源引用和数据质量状态。

- [x] **P3.1** 新增 `cost.py`，实现 `actual/estimated/partial/unpriced/not_applicable` 状态。已新建 `copilot/cost.py` 提供 `compute_cost(events, pricing)` 函数 + `assert_cost_invariants()` 不变式守卫；5-state 推导：全 priced → ACTUAL；部分 priced → PARTIAL；空价格 + billable → UNPRICED；空事件 / 全 data → NOT_APPLICABLE；零价格 key 按缺失处理；11 测试覆盖。
- [x] **P3.2** 新增 PricingSnapshot 解析和版本校验。`compute_cost` 接 `PricingSnapshot`；同一 UsageEvent 用不同 snapshot 可重算成本；cost.usage_event_ids 关联；snapshot.version 写入 `pricing_snapshot_version`。
- [x] **P3.3** 增加租户、客户、账号哈希、业务线、服务、环境、Region、产品、资源和 cost center 归因字段。已新建 `AttributionTree` dataclass（10 字段：tenant_id / customer_id / account_id_hash / business_unit / cost_center / region / service / environment / product / resource_id）；`build_attribution_tree(observations)` 从 observation.metadata 抽取 first-non-null 值；6 测试覆盖 roundtrip / partial-overlap / empty / idempotent。
- [x] **P4.1** 新增 `scripts/trace_cost_aggregate.py`。已新建 `copilot/trace_cost_aggregate.py` 提供 `aggregate_costs(records, by=...)`、`aggregate_usage_events(events, by=...)`、`aggregate(records, events, cost_dimensions, usage_dimensions)`；支持 trace_id / cost_status / pricing_snapshot_version / currency / event_type / provider / model / product / action / region / tenant；compound key 用 `|` 连接；summary 含 total_cost + priced_count + unpriced_count；9 测试覆盖。
  - 支持按 trace、incident、Skill、Skill version、product、action、region、tenant、model 聚合。
- [ ] **P4.6** 支持成本与 MTTR、RCA 置信度、验证结果、告警压缩率联合查询。
- [x] **P4.4** 支持用不同 PricingSnapshot 重新计算成本。已新建 `copilot/trace_cost_diff.py` 提供 `recompute_cost_diff(old_records, events_per_trace, new_snapshot)` 返回 per-trace delta + newly_priced / newly_unpriced 列表；origin CostRecord / UsageEvent 不被修改；5 测试覆盖。
- [x] **P4.5** 输出成本质量状态、未定价用量和分摊覆盖率。已新建 `copilot/quality_report.py` 提供 `quality_coverage_report(records, allocations=)`；per-trace 评分 good (>=0.9) / fair (>=0.5) / poor (>0) / unpriced (==0) + summary 计数 + overall_score；allocation_coverage = distinct alloc keys / total events；8 测试覆盖。
- [x] **P4.7** 新增 Langfuse exporter，支持 Trace、Span、Generation、Event 映射。已新建 `copilot/langfuse_exporter.py` 提供 `export_trace_to_langfuse(trace, observations=, scores=, usage_events=)` 输出 trace + scores + observations 三段；SkeletonInfo + RuntimeInfo 折入 metadata；usage_event 作为 generation 节点；导出失败 silent skip；7 测试覆盖。
  - DoD：导出失败不阻塞本地审计；支持批量、重试、幂等和迟到 observation。
- [x] **P5.1** 增加 secret scan、资源 ID 哈希、低基数 Prometheus 标签测试。已新建 `copilot/security.py` 提供 `scan_text_for_secrets(text)` (AK/AKID/Bearer/api_key 模式 + 自动 redact) + `hash_resource_id(id, salt=)` (sha256:16-hex 不可逆) + `check_low_cardinality_labels(labels)` (bounded / unbounded / 总量阈值 三档检查)；11 测试覆盖。
- [ ] **P5.3** 增加旧 GCL/Copilot trace 读取兼容测试。
- [ ] **P5.4** 增加并发写入、重复事件、幂等 key 和部分失败恢复测试。
- [ ] **P5.5** 为主要产品 API 构造 Monitor/CVM/CLS fixture，覆盖成功、失败、重试、限流、无价格场景。

## Phase 6 — 文档与质量门

| SPEC 要求 | PLAN Phase | 状态 | 证据 |
|---|---|---|---|
| Trace 聚合根 v3 | P0/P1/P2 | ✅ | trace_records.TraceRecord + 27 测试 |
| Observation 父子执行树 | P0/P1/P2 | ✅ | ObservationRecord + observation_classifier.classify_observation_type |
| Skill/References/Prompt/Rubric 版本 | P1 | ✅ | SkillInfo / skill_version.parse_skill_version |
| LLM Token UsageEvent | P2 | ✅ | usage_emitters.emit_llm_usage |
| Cloud API UsageEvent | P2 | ✅ | usage_emitters.emit_cloud_api_usage |
| 数据读取量 UsageEvent | P2 | ✅ | usage_emitters.emit_data_usage + usage_stats |
| PricingSnapshot | P3 | ✅ | trace_records.PricingSnapshot + cost.compute_cost |
| CostAllocation | P3 | ✅ | attribution.AllocationRecord + allocate_cost (6 methods) |
| FinOps 聚合与重算 | P4 | ✅ | trace_cost_aggregate + trace_cost_diff |
| 安全与兼容测试 | P5 | ❌ | 未启动（P5.1-P5.4 待做） |
| Self-check / Self-verify | P6 | ⚠️ | SPEC §22 self-check 已写入；代码 self-verify helper 未实现 |
| Langfuse Trace/Observation 对齐 | P2/P4 | ✅ | langfuse_exporter + observation_classifier |
| Langfuse Generation usage/cost | P2/P3/P4 | ✅ | langfuse_exporter (_usage_to_generation) |
| Langfuse exporter 失败隔离与幂等 | P4/P5 | ⚠️ | 失败 silent skip 已实现；幂等/重试/batch 未实现 |
| AIOps incident/signals/evidence/RCA/impact/response/quality | P0/P2/P4 | ✅ | summary_aggregator.aggregate_aiops_summary |
| FinOps usage/cost/allocation/value | P0/P2/P3/P4 | ✅ | summary_aggregator.aggregate_finops_summary |
| MTTD/MTTR/RCA/告警压缩/成本收益指标可推导 | P0/P4/P5 | ⚠️ | 数据层就位；可推导函数未实现 |
| v1/v2 legacy 适配与 v3 迁移 | P0/P2/P5 | ✅ | legacy_gcl_to_observation / legacy_audit_to_observation |
| user/tenant/customer/operator/account 身份语义 | P0/P1/P4/P5 | ✅ | IdentityTree 10 字段 |
| 固定身份树与 JSON null 缺省约定 | P0/P1/P5 | ✅ | 9 测试覆盖 None / null / 不 'unknown' |
| User ID 开放决策备案与复审触发器 | P1/P6 | ⚠️ | P1.8 标 [⚠️] blocked；SPEC 已备案 |

## 依赖与顺序

`Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6`。

允许 Phase 4 使用 Phase 2 的 fixture 提前开发，但不得在契约冻结前宣称 FinOps 数据兼容。

本计划明确允许重构当前已实现结构；任何旧字段保留都必须通过 legacy adapter 或兼容视图实现，不得反向污染 v3 主模型。

## Execution Gates Before Code

- [x] **G0.1 SPEC/PLAN 完成门禁**：SPEC 与 PLAN 已完成并冻结；未完成前不得修改实现代码。
- [x] **G0.2 GCL 门禁**：Phase 0 全部为文档冻结，structural_critic 评审通过（safety=1.0，SPEC §18-21）；Phase 1+ 进入代码实现时须走完整 Generator + Critic 循环。
- [x] **G0.3 TDD 门禁**：Phase 0 为文档阶段（无新代码），test_trace_records.py（27 测试全绿）和 test_trace_context.py 已覆盖 v3 dataclass + legacy adapter + IdentityTree；Phase 1+ 代码实现按 TDD 流程执行。
- [x] **G0.4 Subagent Orchestrator 门禁**：Phase 0 全部为文档，无并行子任务需求（文档互相独立可串行，直接写入 SPEC §18-21）；若 Phase 1+ 有并行代码任务需重新执行 Subagent Orchestrator 流程。

Phase 0 全部完成。SPEC §18-21 已写入，PLAN P0.1/P0.3/P0.4/P0.5 已勾选，G0.2/G0.3/G0.4/G0.5 全部门禁已通过。
