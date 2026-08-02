# AIOps Optimization TODO

> 目标：将现有的监控、巡检、诊断、Copilot 编排、GCL 和经验沉淀能力，收敛为可运营、可度量、可持续学习的 AIOps 闭环。
>
> 范围：`qcloud-aiops-diagnosis`、`qcloud-proactive-inspection`、`qcloud-copilot`、`qcloud-monitor-ops` 及共享 `scripts/`。
>
> 状态说明：`[ ]` 未开始，`[-]` 进行中，`[x]` 完成，`[!]` 阻塞。

## P0 — 生产闭环

### P0-0 Trace v3 重构基线

- [x] 采用 Langfuse 风格 `Trace` 聚合根、`Observation` 执行树、`UsageEvent` 用量账本、`Score` 反馈和可重建 Summary。— `qcloud-copilot/copilot/trace_records.py`（`TraceRecord:139`、`ObservationRecord:231`、`UsageEvent:292`、`ScoreRecord:337`、`AIOpsSummary:400`）
- [x] 将旧 `TraceRecord v2`、GCL trace、Copilot audit 作为 legacy adapter 输入，不继续扩展为新主模型。— `trace_records.py:468` `legacy_gcl_to_observation()`、`:506` `legacy_audit_to_observation()`
- [x] 保持 AIOps/FinOps 必需字段一等化，禁止依赖自由格式 `output` 或 `metadata` 完成核心分析。— v3 模型一等化 `IdentityTree`/`AutomationTree`/`CostRecord` 等；测试 `tests/test_trace_records.py:256` 断言无 legacy span 字段
- [x] 验收：可从 Observation、Score、UsageEvent 重建 AIOps/FinOps Summary，并导出 Langfuse Trace/Span/Generation/Score。— `qcloud-copilot/copilot/langfuse_exporter.py:91` `export_trace_to_langfuse()` 导出 Trace/Span/Generation/Score
- [x] User ID 定义列为开放议题：本地/自动化运行不强行生成用户身份；固定身份树无值使用 JSON `null`，不阻塞主线。— `IdentityTree:59` / `AutomationTree:78` 支持无值 `null`，本地运行不强制身份

### P0-1 统一 AIOps 事件模型

- [ ] 设计并评审统一 `AIOpsEnvelope`，覆盖租户、地域、trace、incident、资源、时间窗口、证据、数据质量、置信度、决策和动作状态。
- [ ] 定义 Event/RCA/Anomaly/Inspection/Blackboard payload 映射关系。
- [ ] 增加 `schema_version`、兼容策略、迁移策略和 JSON Schema 校验。
- [ ] 为所有跨 Skill handoff 增加 `trace_id`、`incident_id` 和 `causation_id`。
- [ ] 增加 Schema fixture、破坏性变更检测和契约测试。
- [ ] 验收：任一跨产品事件可以通过同一 ID 串联告警、诊断、处置和复盘。

### P0-2 检测质量反馈闭环

- [ ] 为 finding 增加 `review_outcome`：`confirmed`、`false_positive`、`false_negative`、`inconclusive`。
- [ ] 建立规则/模型/产品/租户维度的 Precision、Recall、噪声率、漏报率统计。
- [ ] 统计平均提前发现时间、人工确认耗时和诊断置信度校准误差。
- [ ] 支持人工反馈回写，并防止未经评审的反馈直接修改生产规则。
- [ ] 生成阈值、窗口和规则调优建议，保留审批与版本审计。
- [ ] 验收：每个检测规则都有可追踪的命中、误报和确认结果。

### P0-3 Incident 生命周期状态机

- [ ] 定义 `detected → correlated → diagnosed → mitigating → verifying → resolved → reviewed` 状态机。
- [ ] 明确状态转移条件、超时、升级、取消、重开和并发冲突处理。
- [ ] 统一责任人、SLA、升级路径、动作记录和审计字段。
- [ ] 在 Blackboard、RCA Bundle 和报告中保持状态一致。
- [ ] 接入 MTTD、MTTA、MTTR 和各状态停留时间统计。
- [ ] 验收：一个 incident 可完整回放从发现到关闭的生命周期。

### P0-4 修复后验证闭环

- [ ] 为每类处置动作定义只读验证器和验证指标窗口。
- [ ] 对比事件前、事件中、修复后指标，支持恢复阈值和稳定观察窗口。
- [ ] 输出 `verification_status`、恢复幅度、残余风险和回滚建议。
- [ ] 区分“API 调用成功”和“业务/健康指标恢复”。
- [ ] 验证失败时自动升级、重试或回滚到人工审批队列。
- [ ] 验收：任何 mutation action 都必须有明确的验证结果或显式无法验证原因。

### P0-5 SLO/业务影响驱动的根因排序

- [ ] 引入服务、业务链路、客户等级、请求量和错误预算消耗字段。
- [ ] 将业务影响纳入事件严重度和根因排序。
- [ ] 设计并测试统一排序公式：证据强度、拓扑距离、时间相关性、业务影响、历史先验。
- [ ] 支持核心业务时段、发布窗口和维护窗口的优先级调整。
- [ ] 验收：同一资源异常在不同业务影响下产生不同优先级和响应策略。

## P1 — 智能增强

### P1-1 运行时拓扑图

- [ ] 定期采集 CVM、TKE、CLB、VPC、数据库、消息队列等依赖关系。
- [ ] 为关系增加 `valid_from`、`valid_to`、来源、置信度和更新时间。
- [ ] 将发布、配置、权限和网络变更作为拓扑事件记录。
- [ ] 支持事故时刻拓扑快照和历史回放。
- [ ] 为拓扑缺失、冲突和过期增加数据质量告警。
- [ ] 验收：RCA 能按事故发生时刻而非当前状态解析依赖关系。

### P1-2 统一告警降噪与事件关联

- [ ] 抽取跨产品通用的去重、抑制、聚类和父子告警识别服务。
- [ ] 使用时间窗口、资源依赖、变更事件、指标共振、错误码和日志模板进行关联。
- [ ] 统一输出 incident，而不是仅输出独立 alarm。
- [ ] 统计告警压缩率、错误合并率、未关联率和错误拆分率。
- [ ] 增加不可逆合并保护、人工拆分和关联解释。
- [ ] 验收：告警数量下降时，真实事件召回率不下降。

### P1-3 增强时序异常检测

- [ ] 在静态阈值和同比/环比基线之外，支持趋势、季节性、分位数和变化点检测。
- [ ] 根据样本量、缺失率和稳定性自动选择检测器。
- [ ] 输出检测方法、训练窗口、基线覆盖率和回退原因。
- [ ] 对发布、节假日、活动和维护窗口提供独立基线或豁免机制。
- [ ] 建立离线回放评测集，比较不同检测器的准确率和成本。
- [ ] 验收：每个异常结论都能解释使用了哪种模型、哪段数据和哪种回退策略。

### P1-4 数据质量 SLO

- [ ] 将采集延迟、缺失率、时间偏移、维度异常、API 限流和权限失败纳入平台指标。
- [ ] 为各数据源定义 freshness、completeness、correctness 和 coverage SLO。
- [ ] 数据质量不足时自动降低置信度或禁止输出 HIGH confidence 根因。
- [ ] 在报告中展示缺失数据、降级路径和对结论的影响。
- [ ] 对长期失效数据源触发责任方通知和修复工单。
- [ ] 验收：任何诊断结论都能回答“用了哪些数据、数据是否新鲜、缺了什么”。

### P1-5 多租户与权限治理

- [ ] 为 Blackboard、审计文件、指标、日志和知识检索增加租户/账号/地域隔离。
- [ ] 校验跨租户事件关联和相似事件检索边界。
- [ ] 使用短期凭证和最小权限，按 Skill/动作拆分权限集合。
- [ ] 对资源 ID、日志、凭证、用户信息和业务数据实行分级脱敏。
- [ ] 审计每次工具调用、数据读取、审批和变更动作。
- [ ] 验收：跨租户读取、跨地域误操作和敏感信息泄漏均有测试覆盖。

## P2 — 平台化与持续优化

### P2-1 AIOps 可观测性面板

- [ ] 统一展示 MTTD、MTTA、MTTR、RCA Top-1/Top-3 准确率。
- [ ] 展示告警压缩率、误报率、自动化成功率、回滚率和人工介入率。
- [ ] 展示数据源新鲜度、覆盖率、API 调用量、LLM token 和单事件成本。
- [ ] 支持按产品、租户、地域、规则、模型和时间窗口钻取。
- [ ] 统一指标命名、标签基数和脱敏规则。
- [ ] 验收：运营人员能从面板定位质量下降的产品、规则或数据源。

### P2-2 可复现事故评测集

- [ ] 沉淀脱敏的指标、日志、拓扑、告警和变更事件 fixture。
- [ ] 建立事件级回放工具，支持固定输入、固定时间窗口和固定版本。
- [ ] 比较 RCA 排名、置信度校准、告警压缩、耗时和成本。
- [ ] 将关键事故加入回归集，规则、Prompt、Schema 变更必须回放。
- [ ] 为每类产品覆盖正常、异常、缺失数据、权限失败和多故障场景。
- [ ] 验收：核心 AIOps 变更可在 CI 中发现准确率、契约或安全回归。

### P2-3 成本治理

- [ ] 记录每次事件的 API 调用数、日志扫描量、LLM token、运行时长和存储量。
- [ ] 根据事件严重度、证据增益和预算动态决定继续采集还是提前停止。
- [ ] 对重复查询、重复诊断和相同时间窗口启用缓存。
- [ ] 设置租户、产品和事件级预算及超限降级策略。
- [ ] 将成本与诊断质量联合评估，避免单纯追求低成本。
- [ ] 验收：每个事件都能解释成本来源，并能在预算受限时安全降级。

### P2-4 事后复盘与预防任务自动化

- [ ] Incident 关闭后自动生成时间线、根因、促成因素、检测缺口和恢复动作。
- [ ] 将有效方案写入成功模式，将误判和失败方案写入失败模式。
- [ ] 将预防项转化为巡检规则、监控策略或产品 Skill 验证步骤。
- [ ] 为预防任务分配责任人、截止时间、优先级和验收指标。
- [ ] 追踪预防项是否落地，以及落地后是否减少同类事件。
- [ ] 验收：复盘结果能产生可执行资产，而不是只生成静态报告。

## Cross-cutting Delivery Gates

- [ ] 每项涉及新数据结构、脚本或算法的工作先补充 `docs/superpowers/specs/` 设计文档。
- [ ] 每项功能实现后完成 SPEC/PLAN 逐条对照，并记录 `✅/⚠️/❌`。
- [ ] 修改 `SKILL.md`、`references/` 或 `assets/` 后执行两轮自审和 Token Efficiency Audit。
- [ ] 修改 Python 后运行 `ruff check <changed-files>`。
- [ ] 修改 Markdown 中 Python SDK 代码块后运行 `python3 scripts/check_markdown_python.py --root .`。
- [ ] 运行相关单元测试、Schema 校验、链接校验和 `python3 scripts/validate_local.py`。
- [ ] 所有运行时 trace、审计记录和反馈数据必须脱敏，禁止打印凭证或敏感资源信息。
- [ ] 所有 mutation action 保持 GCL、安全门、人工审批和修复后验证。

## Suggested Execution Order

- [ ] Wave 1：P0-0 Trace v3 重构基线 + P0-1 统一事件模型 + P0-3 Incident 状态机 + P1-4 数据质量 SLO。
- [ ] Wave 2：P0-4 修复后验证 + P0-2 检测质量反馈 + P2-2 事故评测集。
- [ ] Wave 3：P0-5 SLO 排序 + P1-2 告警关联 + P1-3 时序检测。
- [ ] Wave 4：P1-1 运行时拓扑 + P1-5 权限治理 + P2-3 成本治理。
- [ ] Wave 5：P2-1 可观测性面板 + P2-4 复盘与预防自动化。

---

## 更新记录（2026-07-25）

| 任务 | 状态 | 说明 |
|---|---|---|
| OBS-1 可观测性增强 | **✅ 全部完成** | P0（基础设施）P1（health/audit改造）P2（gate可观测）P3（step埋点）P4（查询API）全部在 commit 25c480b 完成；P5 核心测试全绿、ruff零error、TE-Audit已记录；P5.4 已完成 SKILL.md 新增 `## Observability` 节 + v1.1.0 changelog；P5.5 完成 18 条 SPEC/PLAN 逐条对照（17✅+1⚠️ P4A移TRACE-1）；P4A（emit_observation/emit_usage/Summary聚合）由TRACE-1承接 |
| EVO-1 自我进化闭环 | **✅ 全部完成** | E0记忆层/E1决策层/E2护栏层/E3 hook接入/E4反馈采集/E5闭环集成全部在 commit 357ee48 完成；test_evo_generator.py 15个测试全绿 |
| TRACE-1 Trace v3 重构基线（P0-0） | **✅ 完成**（2026-08-02 核实） | `trace_records.py` 实现 Trace/Observation/UsageEvent/ScoreRecord/AIOpsSummary + `langfuse_exporter.py` 导出 + legacy adapter（`legacy_gcl_to_observation`/`legacy_audit_to_observation`）；tests `test_trace_records.py` 通过 |
| P0-1 统一AIOps事件模型 | `[ ]` 未开始 | |
| P0-2 检测质量反馈闭环 | `[ ]` 未开始 | |
| P0-3 Incident生命周期状态机 | `[ ]` 未开始 | |
| P0-4 修复后验证闭环 | `[ ]` 未开始 | |
| P0-5 SLO/业务影响驱动根因排序 | `[ ]` 未开始 | |
| P1-1 ~ P1-5 | `[ ]` 未开始 | |
| P2-1 ~ P2-4 | `[ ]` 未开始 | |
