# 待办事项清单

> 基于磁盘实际状态（2026-07-04 审计），**所有原有 TODO 任务均已完成**。
> 本文档保留作为历史记录。新任务请从扫描发现的实际问题出发。

## 当前全局状态

| 维度 | 状态 |
|------|------|
| 32 个 skill 目录 | ✅ 全部就位（28 product + 3 cross-product + 1 meta） |
| GCL 覆盖率 | ✅ `check_gcl_conformance.py` 已覆盖全部 32 个 skill |
| GCL 通过率 | ✅ 32/32 通过，全部符合 Tier-A conformance |
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
| 1 | **qcloud-dc-ops 场景增强** | DC skill 已存在但场景较基础，可补充专线故障切换、多云接入等 | 0.5-1 天 |
| 2 | **qcloud-migration-ops 场景增强** | 迁移 skill 已存在，可补充更多迁移场景 | ✅ 已完成（`32141e3`）— 新增 ModifyMigrationTaskStatus、ListMigrationProject、Cutover/Switchover、Migration Validation 4 个执行流，rubric 安全规则扩至 5 条，troubleshooting 补充割接失败模式 |
| 3 | **跨 skill 编排测试** | 验证 aiops-diagnosis + monitor-ops + 产品 skill 的跨 skill 调用链路 | ✅ 已完成（`f92111b` + `c079df0`）— 16 个测试覆盖 handoff payload、mode selection、bundle structure |
| 4 | **新技能：消息队列（TDMQ）** | 目前没有 TDMQ（RocketMQ/Pulsar）skill | ✅ 已完成（`e839f05`）— 新增 `qcloud-tdmq-ops` skill，含 10 个执行流（RocketMQ/Pulsar/RabbitMQ/CMQ）、rubric 8 节、prompt 7 节，GCL conform 32/32 | 3 天 |
| 5 | **新技能：API 网关** | 目前没有 API Gateway skill | 2 天 |