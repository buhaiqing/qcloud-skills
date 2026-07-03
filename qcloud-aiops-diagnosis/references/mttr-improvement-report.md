# MTTR 改进报告模板

> 用于记录 MTTR 优化前后的对比分析和改进措施。

---

## 报告信息

| 字段 | 值 |
|------|-----|
| 报告 ID | MTTR-RPT-{{YYYYMM}}-{{SEQUENCE}} |
| 生成日期 | {{report.generated_at}} |
| 报告周期 | {{report.start_date}} ~ {{report.end_date}} |
| 对比基准 | {{report.baseline_period}} |

---

## 1. 执行摘要

### 1.1 关键指标对比

| 指标 | 优化前 | 优化后 | 改进幅度 | 目标 | 状态 |
|------|--------|--------|----------|------|------|
| 平均 MTTR | {{metrics.before.avg_mttr}} min | {{metrics.after.avg_mttr}} min | {{metrics.mttr_improvement}}% | < 30 min | {{metrics.mttr_status}} |
| 平均 MTTD | {{metrics.before.avg_mttd}} min | {{metrics.after.avg_mttd}} min | {{metrics.mttd_improvement}}% | < 10 min | {{metrics.mttd_status}} |
| P95 MTTR | {{metrics.before.p95_mttr}} min | {{metrics.after.p95_mttr}} min | {{metrics.p95_improvement}}% | < 60 min | {{metrics.p95_status}} |
| P0 故障数 | {{metrics.before.p0_count}} | {{metrics.after.p0_count}} | {{metrics.p0_change}}% | - | - |
| 总故障数 | {{metrics.before.total_incidents}} | {{metrics.after.total_incidents}} | {{metrics.incident_change}}% | - | - |

### 1.2 结论

{{executive_summary.conclusion}}

---

## 2. 优化项目详情

### 2.1 优化项目列表

| # | 优化项目 | 目标产品 | 预期效果 | 实际效果 | 状态 |
|---|----------|----------|----------|----------|------|
| 1 | {{improvements.1.name}} | {{improvements.1.product}} | MTTR ↓ {{improvements.1.target}}% | MTTR ↓ {{improvements.1.actual}}% | {{improvements.1.status}} |
| 2 | {{improvements.2.name}} | {{improvements.2.product}} | MTTR ↓ {{improvements.2.target}}% | MTTR ↓ {{improvements.2.actual}}% | {{improvements.2.status}} |
| 3 | {{improvements.3.name}} | {{improvements.3.product}} | MTTR ↓ {{improvements.3.target}}% | MTTR ↓ {{improvements.3.actual}}% | {{improvements.3.status}} |

### 2.2 重点项目分析

#### 项目 1: {{improvements.1.name}}

**问题描述:**
{{improvements.1.problem_description}}

**优化措施:**
{{improvements.1.measures}}

**实施前后对比:**

| 场景 | 优化前 MTTR | 优化后 MTTR | 提升 |
|------|-------------|-------------|------|
| {{improvements.1.scenario_1}} | {{improvements.1.before_1}} min | {{improvements.1.after_1}} min | ↓ {{improvements.1.improvement_1}}% |
| {{improvements.1.scenario_2}} | {{improvements.1.before_2}} min | {{improvements.1.after_2}} min | ↓ {{improvements.1.improvement_2}}% |

**关键改进点:**
- {{improvements.1.key_improvement_1}}
- {{improvements.1.key_improvement_2}}
- {{improvements.1.key_improvement_3}}

---

## 3. 分产品 MTTR 分析

### 3.1 各产品 MTTR 对比

| 产品 | 优化前平均 MTTR | 优化后平均 MTTR | 改进幅度 | P95 MTTR | 主要优化点 |
|------|-----------------|-----------------|----------|----------|------------|
| CVM | {{products.cvm.before_mttr}} min | {{products.cvm.after_mttr}} min | {{products.cvm.improvement}}% | {{products.cvm.p95}} min | {{products.cvm.key_point}} |
| CDB/RDS | {{products.cdb.before_mttr}} min | {{products.cdb.after_mttr}} min | {{products.cdb.improvement}}% | {{products.cdb.p95}} min | {{products.cdb.key_point}} |
| TKE | {{products.tke.before_mttr}} min | {{products.tke.after_mttr}} min | {{products.tke.improvement}}% | {{products.tke.p95}} min | {{products.tke.key_point}} |
| CLB | {{products.clb.before_mttr}} min | {{products.clb.after_mttr}} min | {{products.clb.improvement}}% | {{products.clb.p95}} min | {{products.clb.key_point}} |
| Redis | {{products.redis.before_mttr}} min | {{products.redis.after_mttr}} min | {{products.redis.improvement}}% | {{products.redis.p95}} min | {{products.redis.key_point}} |
| ES | {{products.es.before_mttr}} min | {{products.es.after_mttr}} min | {{products.es.improvement}}% | {{products.es.p95}} min | {{products.es.key_point}} |
| COS | {{products.cos.before_mttr}} min | {{products.cos.after_mttr}} min | {{products.cos.improvement}}% | {{products.cos.p95}} min | {{products.cos.key_point}} |

### 3.2 产品详细分析

#### CVM

{{products.cvm.analysis}}

**Top 3 根因及优化:**
1. {{products.cvm.root_cause_1}}: {{products.cvm.rc1_optimization}}
2. {{products.cvm.root_cause_2}}: {{products.cvm.rc2_optimization}}
3. {{products.cvm.root_cause_3}}: {{products.cvm.rc3_optimization}}

#### CLB

{{products.clb.analysis}}

**Top 3 根因及优化:**
1. {{products.clb.root_cause_1}}: {{products.clb.rc1_optimization}}
2. {{products.clb.root_cause_2}}: {{products.clb.rc2_optimization}}
3. {{products.clb.root_cause_3}}: {{products.clb.rc3_optimization}}

---

## 4. 根因分析改进

### 4.1 根因分类统计

| 根因类别 | 优化前占比 | 优化后占比 | 变化 | 主要优化措施 |
|----------|------------|------------|------|--------------|
| 配置变更 | {{root_causes.config.before}}% | {{root_causes.config.after}}% | {{root_causes.config.change}}% | {{root_causes.config.measure}} |
| 资源不足 | {{root_causes.resource.before}}% | {{root_causes.resource.after}}% | {{root_causes.resource.change}}% | {{root_causes.resource.measure}} |
| 网络问题 | {{root_causes.network.before}}% | {{root_causes.network.after}}% | {{root_causes.network.change}}% | {{root_causes.network.measure}} |
| 应用故障 | {{root_causes.application.before}}% | {{root_causes.application.after}}% | {{root_causes.application.change}}% | {{root_causes.application.measure}} |
| 依赖故障 | {{root_causes.dependency.before}}% | {{root_causes.dependency.after}}% | {{root_causes.dependency.change}}% | {{root_causes.dependency.measure}} |
| 外部因素 | {{root_causes.external.before}}% | {{root_causes.external.after}}% | {{root_causes.external.change}}% | {{root_causes.external.measure}} |

### 4.2 根因定位效率

| 根因类别 | 优化前定位时间 | 优化后定位时间 | 提升 |
|----------|----------------|----------------|------|
| 配置变更 | {{rc_efficiency.config.before}} min | {{rc_efficiency.config.after}} min | ↓ {{rc_efficiency.config.improvement}}% |
| 资源不足 | {{rc_efficiency.resource.before}} min | {{rc_efficiency.resource.after}} min | ↓ {{rc_efficiency.resource.improvement}}% |
| 网络问题 | {{rc_efficiency.network.before}} min | {{rc_efficiency.network.after}} min | ↓ {{rc_efficiency.network.improvement}}% |

---

## 5. 工具与流程改进

### 5.1 诊断工具增强

| 工具/流程 | 优化内容 | 效果 |
|-----------|----------|------|
| {{tools.1.name}} | {{tools.1.improvement}} | {{tools.1.impact}} |
| {{tools.2.name}} | {{tools.2.improvement}} | {{tools.2.impact}} |
| {{tools.3.name}} | {{tools.3.improvement}} | {{tools.3.impact}} |

### 5.2 自动化程度提升

| 环节 | 优化前人工比例 | 优化后人工比例 | 自动化率提升 |
|------|----------------|----------------|--------------|
| 故障检测 | {{automation.detection.before}}% | {{automation.detection.after}}% | +{{automation.detection.improvement}}% |
| 根因诊断 | {{automation.diagnosis.before}}% | {{automation.diagnosis.after}}% | +{{automation.diagnosis.improvement}}% |
| 恢复执行 | {{automation.recovery.before}}% | {{automation.recovery.after}}% | +{{automation.recovery.improvement}}% |

---

## 6. 问题与挑战

### 6.1 未达标项目

| 项目 | 目标 | 实际 | 差距 | 根因分析 | 后续计划 |
|------|------|------|------|----------|----------|
| {{challenges.1.name}} | {{challenges.1.target}} | {{challenges.1.actual}} | {{challenges.1.gap}} | {{challenges.1.root_cause}} | {{challenges.1.plan}} |

### 6.2 新发现问题

{{challenges.new_findings}}

---

## 7. 最佳实践总结

### 7.1 可复用的优化模式

| 模式名称 | 适用场景 | 实施要点 | 预期效果 |
|----------|----------|----------|----------|
| {{patterns.1.name}} | {{patterns.1.scenario}} | {{patterns.1.key_points}} | {{patterns.1.expected}} |
| {{patterns.2.name}} | {{patterns.2.scenario}} | {{patterns.2.key_points}} | {{patterns.2.expected}} |

### 7.2 经验总结

{{lessons_learned}}

---

## 8. 下一步计划

### 8.1 短期目标 (1-3个月)

| 目标 | 指标 | 负责人 | 截止日期 |
|------|------|--------|----------|
| {{next_steps.short.1.goal}} | {{next_steps.short.1.metric}} | {{next_steps.short.1.owner}} | {{next_steps.short.1.deadline}} |
| {{next_steps.short.2.goal}} | {{next_steps.short.2.metric}} | {{next_steps.short.2.owner}} | {{next_steps.short.2.deadline}} |

### 8.2 中期目标 (3-6个月)

| 目标 | 指标 | 负责人 | 截止日期 |
|------|------|--------|----------|
| {{next_steps.medium.1.goal}} | {{next_steps.medium.1.metric}} | {{next_steps.medium.1.owner}} | {{next_steps.medium.1.deadline}} |

### 8.3 长期目标 (6-12个月)

{{next_steps.long_term}}

---

## 附录

### A. 数据来源

- MTTR 追踪数据库: `incidents.db`
- 监控告警记录: Tencent Cloud Monitor
- 诊断日志: AIOps Diagnosis Logs
- 恢复确认记录: Incident Response System

### B. 统计方法

- MTTR 计算: `resolved_at - detected_at` (分钟)
- MTTD 计算: `diagnosis_at - detected_at` (分钟)
- P95 计算: 百分位数，排除异常值 (> 99th percentile)
- 趋势分析: 周环比，移动平均

### C. 参考文档

- [MTTR 追踪指南](./mttr-tracking.md)
- [诊断框架](./diagnosis-framework.md)
- [故障处理流程](./alarm-handling.md)

---

*报告生成: {{report.generated_by}} | 审核: {{report.reviewed_by}} | 批准: {{report.approved_by}}*
