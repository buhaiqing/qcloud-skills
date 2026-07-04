# 剩余优化任务计划

> 生成时间: 2026-07-04
> 基于全面扫描结果，按优先级排列。

---

## Batch 1: GCL 组件补齐（P0 — 阻塞质量门禁）

### 任务 1.1 cicd-ops GCL 补齐
- 文件: `qcloud-cicd-ops/`
- 缺失: Quality Gate 章节、rubric.md、prompt-templates.md
- 说明: CI/CD 管道管理 skill，需 pipeline-specific safety rules

### 任务 1.2 dc-ops GCL 补齐
- 文件: `qcloud-dc-ops/`
- 缺失: Quality Gate 章节、rubric.md、prompt-templates.md
- 说明: 物理专线管理 skill，需 Direct Connect-specific safety rules

### 任务 1.3 migration-ops GCL 补齐
- 文件: `qcloud-migration-ops/`
- 缺失: Quality Gate 章节、rubric.md、prompt-templates.md
- 说明: 数据迁移 skill，需 migration-specific safety rules

### 任务 1.4 service-mesh-ops Quality Gate 补齐
- 文件: `qcloud-service-mesh-ops/`
- 缺失: Quality Gate 章节
- 说明: 已有 rubric.md 和 prompt-templates.md，仅缺 Quality Gate 章节

---

## Batch 2: 硬编码区域修复（P1 — Token 效率 TE-1）

### 任务 2.1 ccn-ops 硬编码区域
- 文件: `qcloud-ccn-ops/SKILL.md`
- 行号: 162, 169, 230
- 内容: `tccli vpc DescribeCCNs --Region ap-guangzhou`

### 任务 2.2 clb-ops 硬编码区域
- 文件: `qcloud-clb-ops/SKILL.md`
- 行号: 191
- 内容: `tccli clb DescribeLoadBalancers --Region ap-guangzhou`

### 任务 2.3 cos-ops 硬编码区域
- 文件: `qcloud-cos-ops/SKILL.md`
- 行号: 129
- 内容: `tccli cos PutBucket --Bucket "my-bucket-12345" --Region ap-guangzhou`

### 任务 2.4 cvm-ops 硬编码区域
- 文件: `qcloud-cvm-ops/SKILL.md`
- 行号: 106
- 内容: `tccli cvm DescribeZones --Region ap-guangzhou`

### 任务 2.5 dc-ops 硬编码区域
- 文件: `qcloud-dc-ops/SKILL.md`
- 行号: 132, 138, 359
- 内容: `tccli dc DescribeDirectConnects --Region ap-guangzhou`

### 任务 2.6 migration-ops 硬编码区域
- 文件: `qcloud-migration-ops/SKILL.md`
- 行号: 309
- 内容: `tccli msp ListMigrationTask --Region ap-guangzhou`

### 任务 2.7 service-mesh-ops 硬编码区域
- 文件: `qcloud-service-mesh-ops/SKILL.md`
- 行号: 130, 137, 368
- 内容: `tccli tcm DescribeMeshList --Region ap-guangzhou`

### 任务 2.8 vpc-ops 硬编码区域
- 文件: `qcloud-vpc-ops/SKILL.md`
- 行号: 184, 190, 697
- 内容: `tccli vpc DescribeVpcs --Region ap-guangzhou`

---

## Batch 3: AGENTS.md 路径修复（P1 — 幽灵链接）

### 任务 3.1 修正 ../../AGENTS.md → ../AGENTS.md
- 影响: 20 个 SKILL.md 文件
- 文件列表:
  agsx, cam, cbs, cdb, cdn, ckafka, clb, cls, cos, cvm,
  es, finops, mongodb, monitor, postgres, redis, scf, ssl, tke, vpc
- 说明: 所有 SKILL.md 中 `../../AGENTS.md` 应为 `../AGENTS.md`

---

## Batch 4: 幽灵链接修复（P1 — 断链引用）

### 任务 4.1 cbs-ops 幽灵链接
- 缺失文件: api-sdk-usage.md, monitoring.md, integration.md, finops-analysis.md, audit-rules.md, secops-checklist.md
- 方案: 创建缺失文件或移除引用

### 任务 4.2 ckafka-ops 幽灵链接
- 缺失文件: api-instance.md, api-topic.md, api-consumer.md, api-acl.md
- 方案: 创建缺失文件或移除引用

### 任务 4.3 cls-ops 幽灵链接
- 缺失文件: integration.md, query-language.md
- 方案: 创建缺失文件或移除引用

### 任务 4.4 scf-ops 幽灵链接
- 缺失文件: integration.md
- 方案: 创建缺失文件或移除引用

### 任务 4.5 vpn-ops 幽灵链接
- 缺失文件: api-sdk-usage.md, integration.md, finops-cost-optimization.md, secops-security-operations.md, aiops-best-practices.md
- 方案: 创建缺失文件或移除引用

### 任务 4.6 vpn-ops 跨 skill 引用路径
- 文件: `qcloud-vpn-ops/SKILL.md`
- 问题: `../references/user-experience-spec.md` 应为 `../qcloud-skill-generator/references/user-experience-spec.md`

---

## Batch 5: Token 效率压缩（P2 — 行数优化）

### 任务 5.1 cls-ops 压缩（863 行）
- 当前: 863 行，最大 skill
- 方案: 进一步提取内联 bash 块到 references/

### 任务 5.2 ssl-ops 压缩（827 行）
- 当前: 827 行
- 方案: 评估是否有可提取的执行流程

### 任务 5.3 vpc-ops 压缩（822 行）
- 当前: 822 行
- 方案: 评估是否有可提取的执行流程

### 任务 5.4 cvm-ops 压缩（760 行）
- 当前: 760 行
- 方案: 评估是否有可提取的执行流程

### 任务 5.5 postgres-ops 压缩（751 行）
- 当前: 751 行
- 方案: 评估是否有可提取的执行流程

### 任务 5.6 cbs-ops 压缩（635 行）
- 当前: 635 行
- 方案: 评估是否有可提取的执行流程

### 任务 5.7 ckafka-ops 压缩（624 行）
- 当前: 624 行
- 方案: 评估是否有可提取的执行流程

### 任务 5.8 agsx-ops 压缩（624 行）
- 当前: 624 行
- 方案: 评估是否有可提取的执行流程

---

## 优先级矩阵

| Batch | 优先级 | 任务数 | 影响范围 | 预估工作量 |
|-------|--------|--------|----------|-----------|
| Batch 1 | P0 | 4 | 4 个 skill | 3 agent runs |
| Batch 2 | P1 | 8 | 8 个 skill | 1 agent run |
| Batch 3 | P1 | 1 | 20 个 SKILL.md | 1 agent run |
| Batch 4 | P1 | 6 | 5 个 skill | 3 agent runs |
| Batch 5 | P2 | 8 | 8 个 skill | 3 agent runs |

---

## 执行顺序

Batch 1 → Batch 2 + Batch 3 (并行) → Batch 4 → Batch 5
每个 Batch 内并发 ≤3 个 subagent。