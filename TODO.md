# 待办事项清单

> 基于磁盘实际状态（2026-07-04 审计），**所有原有 TODO 任务均已完成**。
> 本文档保留作为历史记录。新任务请从扫描发现的实际问题出发。

## 当前全局状态

| 维度 | 状态 |
|------|------|
| 26 个 skill 目录 | ✅ 全部就位（含 dc-ops, cicd-ops, service-mesh-ops, migration-ops, mongodb-ops, ccn-ops, vpn-ops） |
| GCL 组件（Quality Gate + rubric + prompt-templates） | ✅ 全部就位（26/26 skill，含 service-mesh-ops 刚修复） |
| 硬编码区域修复 | ✅ Batch 2 完成（`b8d1a10`） |
| AGENTS.md 路径修正 | ✅ Batch 3 完成（`b636cce`） |
| 幽灵链接修复 | ✅ Batch 4 完成（`c3bc268`） |
| Token 效率压缩 | ✅ Batch 5 完成（`62b4251`） |
| SLB 5xx MTTR 优化 | ✅ 完成（`81bded5` + `ec1d8aa`） |
| RDS MySQL 诊断优化 | ✅ 完成（`18d3c20`） |
| AIOps 预测分析/知识图谱 | ✅ 完成（`ae77b8d`） |
| vpn-ops 多分支拓扑模板 | ✅ 完成（`dd06849`，刚提交） |
| service-mesh-ops GCL 对齐 | ✅ 完成（`058978f`，刚提交） |
| 验证脚本 | ✅ frontmatter 30/30, GCL 24/24, Python-in-Markdown OK |

## 可考虑的新方向

以下是不在原有 TODO 中，但值得评估的方向：

| # | 方向 | 说明 | 预估工作量 |
|---|------|------|-----------|
| 1 | **qcloud-dc-ops 场景增强** | DC skill 已存在但场景较基础，可补充专线故障切换、多云接入等 | 0.5-1 天 |
| 2 | **qcloud-migration-ops 场景增强** | 迁移 skill 已存在，可补充更多迁移场景 | 0.5-1 天 |
| 3 | **跨 skill 编排测试** | 验证 aiops-diagnosis + monitor-ops + 产品 skill 的跨 skill 调用链路 | 1 天 |
| 4 | **check_gcl_conformance.py 扩展** | 当前仅检查 24 个 skill，需扩展至 30 个 | 0.5 天 |
| 5 | **新技能：消息队列（TDMQ）** | 目前没有 TDMQ（RocketMQ/Pulsar）skill | 3 天 |
| 6 | **新技能：API 网关** | 目前没有 API Gateway skill | 2 天 |