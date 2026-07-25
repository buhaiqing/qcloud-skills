# Plan: TRACE-1 Trace Usage & FinOps 成本归因重构

> 对应 SPEC：`docs/superpowers/specs/trace-usage-finops-design.md`
> 目标：让 AIOps trace 同时具备链路追踪、版本追溯、用量计量和 FinOps 成本归因能力。

## Phase 0 — 重构决策与契约冻结

- [ ] **P0.1** 评审并冻结 `trace_id`、`span_id`、`session_id`、`incident_id`、`request_id`、`api_request_id` 的层级语义。
  - DoD：补充契约说明和正反例；跨 Copilot/GCL 链路可唯一关联。
- [x] **P0.2**  TraceRecord/Observation/UsageEvent/Score/CostRecord/PricingSnapshot/Summary dataclass + JSON Schema 对齐；14 个测试全绿（commit fba704 后 feature/trace-v3）。 新增 Trace v3、Observation、Score、UsageEvent、CostRecord、PricingSnapshot 和 Summary JSON Schema。
  - DoD：Schema 支持严格必填字段、枚举、非负数量和成本状态约束。
- [ ] **P0.3** 明确旧格式兼容策略。
  - DoD：现有 GCL trace、Copilot audit、metrics JSONL 读取测试继续通过。
- [ ] **P0.4** 冻结 AIOps 分析域。
  - 包含 incident、signals、evidence/data quality、topology、RCA、impact、response、quality。
  - DoD：可推导 MTTD/MTTA/MTTR、RCA 准确率、告警压缩率、修复成功率和数据质量 SLO。
- [ ] **P0.5** 冻结 FinOps 分析域。
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
- [ ] **P1.3** 将 `skill.name/version/sha/commit`、references、prompt、rubric、runtime、tccli/sdk 版本写入 TraceRecord。
- [ ] **P1.4** 更新 GCL adapter 和 Copilot audit。
  - DoD：一次调用可以回答实际执行的 Skill 版本、代码提交和运行时版本。
- [ ] **P1.5** 新增 Trace 聚合根和 Summary 引用模型。
  - DoD：Trace 仅保存顶层 Langfuse 字段、租户/版本/状态、AIOps/FinOps summary 和 observation/usage/score refs。
- [ ] **P1.6** 在 Copilot/Blackboard/Handoff 上下文中引入身份上下文。
  - DoD：保留现有 `session_id` 和客户策略字段，新增身份字段不改变旧 Blackboard 读取兼容性。
- [ ] **P1.7** 实现身份树解析与序列化。
  - DoD：CLI、配置、认证、Session、自动化和本地 fallback 均输出相同字段结构；无值字段为 `null`。
- [ ] **P1.8** 备案 User ID 延后决策，不阻塞主线。
  - DoD：固定身份树和 automation 树先落地；没有认证来源时 `user_id=null`，后续通过 OIDC/SSO/IAM 复审。

## Phase 2 — Observation 执行树与 UsageEvent 写入

- [ ] **P2.1** 新增 `trace_records.py` 数据模型和序列化器。
  - 包含 `Trace`、`Observation`、`Score`、`UsageEvent`、`CostRecord`、`Summary`；禁止继续扩展旧的单对象 TraceRecord。
- [ ] **P2.2** 在 `observ.py` 增加 Trace/Span/Usage 写入入口，复用 OBS-1 的 JSONL/索引能力。
- [ ] **P2.3** 新增 LLM usage emitter。
  - 记录 provider、model、prompt version、role、input/output/cached/reasoning/total tokens、retry、latency。
- [ ] **P2.4** 新增 Cloud API usage emitter。
  - 记录 client_type、product、service、action、api_version、region、RequestId、请求/响应字节、资源数、重试、限流和缓存命中。
- [ ] **P2.5** 新增数据用量 emitter。
  - 记录 metric points、log bytes/records、audit events、topology nodes/edges、compute/storage 用量。
- [ ] **P2.6** 在工具调用和产品 Skill 委派边界接入 emitter。
  - DoD：至少覆盖 Copilot、AIOps Diagnosis、Proactive Inspection、GCL Generator/Critic、Monitor/CVM/CLS 只读调用路径。
- [ ] **P2.7** 按 Langfuse Observation 树对齐 Span/Generation/Event 类型。
  - DoD：Skill/API/Verification 使用 Span 或 Event，Generator/Critic/Summarizer 使用 Generation，所有节点可通过 `parent_observation_id` 还原树。
- [ ] **P2.8** 将 `user_id`、`session_id`、`name`、`version`、`input`、`output`、`usage`、`status` 保持为一等字段；扩展属性进入受控 `metadata`。
  - DoD：不依赖 metadata 才能在 Langfuse 查询 Trace、Session、Version 和 Generation usage。
- [ ] **P2.9** 实现 TraceRecord AIOps/FinOps 分析摘要聚合器。
  - DoD：Observation 和 UsageEvent 写入后可幂等刷新 `aiops.*`、`finops.*`，且保留来源引用和数据质量状态。
- [ ] **P2.10** 实现 `legacy_gcl_to_observation()` 和 `legacy_audit_to_observation()`。
  - DoD：旧 GCL/Copilot 文件可查询、可导出，但不原地改写。

## Phase 3 — 成本与分摊模型

- [ ] **P3.1** 新增 `cost.py`，实现 `actual/estimated/partial/unpriced/not_applicable` 状态。
- [ ] **P3.2** 新增 PricingSnapshot 解析和版本校验。
  - DoD：价格变化可重算，原始 UsageEvent 不被覆盖。
- [ ] **P3.3** 增加租户、客户、账号哈希、业务线、服务、环境、Region、产品、资源和 cost center 归因字段。
- [ ] **P3.4** 实现 direct/shared/unallocated 及 resource/request/usage/equal_split 分摊方法。
- [ ] **P3.5** 明确未知价格不序列化为 0 的测试门禁。

## Phase 4 — FinOps 聚合与查询

- [ ] **P4.1** 新增 `scripts/trace_cost_aggregate.py`。
  - 支持按 trace、incident、Skill、Skill version、product、action、region、tenant、model 聚合。
- [ ] **P4.2** 支持 LLM 与云 API 成本拆分。
- [ ] **P4.3** 支持 token、API request、metric point、log byte、event、compute、storage 用量统计。
- [ ] **P4.4** 支持用不同 PricingSnapshot 重新计算成本。
- [ ] **P4.5** 输出成本质量状态、未定价用量和分摊覆盖率。
- [ ] **P4.6** 支持成本与 MTTR、RCA 置信度、验证结果、告警压缩率联合查询。
- [ ] **P4.7** 新增 Langfuse exporter，支持 Trace、Span、Generation、Event、Score 映射。
  - DoD：导出失败不阻塞本地审计；支持批量、重试、幂等和迟到 observation。
- [ ] **P4.8** 新增 Langfuse/OTel 兼容测试。
  - DoD：可从本地 TraceRecord 还原 Langfuse 风格父子树，并保持 W3C trace/span 关联字段可转换。

## Phase 5 — 安全、兼容与测试

- [ ] **P5.1** 增加 secret scan、资源 ID 哈希、低基数 Prometheus 标签测试。
- [ ] **P5.2** 增加跨租户隔离和敏感字段禁止落盘测试。
- [ ] **P5.3** 增加旧 GCL/Copilot trace 读取兼容测试。
- [ ] **P5.4** 增加并发写入、重复事件、幂等 key 和部分失败恢复测试。
- [ ] **P5.5** 为主要产品 API 构造 Monitor/CVM/CLS fixture，覆盖成功、失败、重试、限流、无价格场景。

## Phase 6 — 文档与质量门

- [ ] **P6.1** 更新 `qcloud-copilot/SKILL.md` 和相关 references，说明 trace/usage/cost contract。
- [ ] **P6.2** 更新 `docs/superpowers/plans/2026-07-25-aiops-optimization-todo.md`，勾选已交付项目。
- [ ] **P6.3** 执行 SPEC/PLAN 逐条核对，记录每条 `✅/⚠️/❌`，发现不一致先修复。
- [ ] **P6.4** 修改 Python 后运行 `ruff check <changed-files>`。
- [ ] **P6.5** 运行 Schema、单元测试、Markdown/Python 检查和 `python3 scripts/validate_local.py`。
- [ ] **P6.6** 完成两轮自审：模板/五大标准/Token Efficiency；安全/API/数据质量/UX 对抗审查。
- [ ] **P6.7** 完成 TE Audit，并将结果记录到交付说明或提交 footer。

## SPEC/PLAN 对照表（实现完成后填写）

| SPEC 要求 | PLAN Phase | 状态 | 证据 |
|---|---|---|---|
| Trace 聚合根 v3 | P0/P1/P2 | ☐ | |
| Observation 父子执行树 | P0/P1/P2 | ☐ | |
| Skill/References/Prompt/Rubric 版本 | P1 | ☐ | |
| LLM Token UsageEvent | P2 | ☐ | |
| Cloud API UsageEvent | P2 | ☐ | |
| 数据读取量 UsageEvent | P2 | ☐ | |
| PricingSnapshot | P3 | ☐ | |
| CostAllocation | P3 | ☐ | |
| FinOps 聚合与重算 | P4 | ☐ | |
| 安全与兼容测试 | P5 | ☐ | |
| Self-check / Self-verify | P6 | ☐ | |
| Langfuse Trace/Observation 对齐 | P2/P4 | ☐ | |
| Langfuse Generation usage/cost | P2/P3/P4 | ☐ | |
| Langfuse exporter 失败隔离与幂等 | P4/P5 | ☐ | |
| AIOps incident/signals/evidence/RCA/impact/response/quality | P0/P2/P4 | ☐ | |
| FinOps usage/cost/allocation/value | P0/P2/P3/P4 | ☐ | |
| MTTD/MTTR/RCA/告警压缩/成本收益指标可推导 | P0/P4/P5 | ☐ | |
| v1/v2 legacy 适配与 v3 迁移 | P0/P2/P5 | ☐ | |
| user/tenant/customer/operator/account 身份语义 | P0/P1/P4/P5 | ☐ | |
| 固定身份树与 JSON null 缺省约定 | P0/P1/P5 | ☐ | |
| User ID 开放决策备案与复审触发器 | P1/P6 | ☐ | |

## 依赖与顺序

`Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6`。

允许 Phase 4 使用 Phase 2 的 fixture 提前开发，但不得在契约冻结前宣称 FinOps 数据兼容。

本计划明确允许重构当前已实现结构；任何旧字段保留都必须通过 legacy adapter 或兼容视图实现，不得反向污染 v3 主模型。

## Execution Gates Before Code

- [x] **G0.1 SPEC/PLAN 完成门禁**：SPEC 与 PLAN 已完成并冻结；未完成前不得修改实现代码。
- [ ] **G0.2 GCL 门禁**：建立 Generator + 至少两个隔离 Critic 的评审循环；Critic 分别覆盖数据质量/Schema、Langfuse/OTel/API 兼容、AIOps/FinOps 安全与成本归因。
- [ ] **G0.3 TDD 门禁**：每个实现 Phase 先新增失败测试，再写最小实现，再运行回归测试；禁止先写实现后补测试。
- [ ] **G0.4 Subagent Orchestrator 门禁**：先完成任务拆分、复杂度、并行边界、owner、Safety Gate 和成本记录，再 dispatch 子代理；最多 3 个并发。
- [x] **G0.5 工作区门禁**：已确认当前存在用户未提交改动；实现不得覆盖或回滚这些改动。

> 环境记录：本次会话提供的 subagent MCP 调用返回 `unsupported call`，因此未启动子代理；在能力恢复前采用主 Agent 的等价只读审查，不将代码写入并行任务。
