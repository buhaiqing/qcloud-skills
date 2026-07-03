# 待办事项清单

> 基于规划文件提取的未完成任务，按 **高价值、高ROI、低成本** 原则排序。

## 评估矩阵

| # | 任务 | 价值 | ROI | 成本 | 综合评分 | 状态 |
|---|------|------|-----|------|----------|------|
| 7 | aiops-diagnosis MTTR 自动追踪 | 5 | 5 | 1 | **15** | ✅ 已完成 |
| 11 | SLB 5xx MTTR 优化 | 5 | 5 | 2 | **14** | ✅ 已完成 |
| 12 | RDS MySQL 诊断优化 | 5 | 5 | 2 | **14** | ✅ 已完成 |
| 4 | well-architected 管理层报告 | 4 | 4 | 1 | **13** | ✅ 已完成 |
| 5 | ccn-ops SD-WAN 场景 | 3 | 3 | 1 | **11** | ⏳ 未开始 |
| 6 | vpn-ops 多分支拓扑 | 3 | 3 | 1 | **11** | ⏳ 未开始 |
| 10 | GCL 合规 | 5 | 4 | 5 | **10** | ⏳ 未开始 |
| 1 | cicd-ops 新增 | 4 | 4 | 4 | **10** | ✅ 已完成 |
| 2 | service-mesh-ops 新增 | 4 | 4 | 4 | **10** | ✅ 已完成 |
| 3 | dc-ops 新增 | 3 | 3 | 4 | **8** | ⏳ 未开始 |
| 8 | mongodb-ops 新增 | 4 | 4 | 5 | **9** | ⏳ 未开始 |
| 9 | CBS/CLS/CKafka | 3 | 3 | 5 | **7** | ⏳ 未开始 |

> 综合评分 = 价值 + ROI + (6 - 成本)，越高越优先

---

## 第一批：立即执行（综合评分 ≥ 14）

### ~~7. aiops-diagnosis MTTR 自动追踪~~ ✅ 已完成
**综合评分:** 15 | **状态：** ✅ 已完成

---

### ~~11. SLB 5xx 故障 MTTR 优化~~ ✅ 已完成
**综合评分:** 14 | **预计工作量:** 2 天
**来源：** docs/superpowers/plans/findings/slb-skill-assessment.md
**状态：** ✅ 已完成

**完成情况：**
- [x] 分析 SLB 5xx 故障诊断流程
- [x] 优化诊断决策树
- [x] 添加自动化恢复步骤
- [x] 测试验证 MTTR 改进效果

**提交记录：** `81bded5 feat(clb): optimize SLB 5xx diagnosis for <30min MTTR`

### ~~12. RDS MySQL 诊断时间优化~~ ✅ 已完成
**综合评分:** 14 | **预计工作量:** 2 天
**来源：** docs/superpowers/plans/findings/rds-mysql-skill-assessment.md
**状态：** ✅ 已完成

**完成情况：**
- [x] 分析 RDS MySQL 诊断瓶颈
- [x] 优化慢查询分析流程
- [x] 添加自动化根因定位
- [x] 测试验证诊断时间改进

**提交记录：** `18d3c20 feat(cdb): optimize MySQL slow query diagnosis for <30min MTTR`

**完成时间：** 2026-07-04

---

## 第二批：可并行执行（综合评分 11-13）

### ~~4. well-architected-review — 管理层战略报告~~ ✅ 已完成
**综合评分:** 13 | **预计工作量:** 0.5 天
**来源：** 2026-07-03-skill-gap-filling-plan.md Task 6
**状态：** ✅ 已完成

**完成情况：**
- [x] 创建管理层报告模板（references/executive-report.md）
- [x] 在 SKILL.md 新增管理层报告模式
- [x] 提交

**提交记录：** `f976972 fix(te): fix all Token Efficiency violations (TE-1 to TE-7)`

### ~~5. ccn-ops — SD-WAN 场景补充~~ ✅ 已完成
**综合评分:** 11 | **预计工作量:** 0.5 天
**来源：** 2026-07-03-skill-gap-filling-plan.md Task 7
**状态：** ✅ 已完成

**任务清单：**
- [x] 创建 SD-WAN 场景文档（references/sdwan-scenarios.md）
- [x] 在 SKILL.md 新增 SD-WAN 场景操作
- [x] 提交

**提交记录：** `8ab576a feat(ccn-ops): 补充 SD-WAN 场景文档和操作流程`

### 6. vpn-ops — 多分支 VPN 拓扑模板
**综合评分:** 11 | **预计工作量:** 0.5 天
**来源：** 2026-07-03-skill-gap-filling-plan.md Task 8
**状态：** ⏳ 未开始

**任务清单：**
- [ ] 创建多分支拓扑文档（references/multi-branch-topology.md）
- [ ] 在 SKILL.md 中引用新文档
- [ ] 提交

---

## 第三批：较高成本任务（综合评分 8-10）

### ~~1. qcloud-cicd-ops 新增（CI/CD 流水线 Skill）~~ ✅ 已完成
**综合评分:** 10 | **预计工作量:** 2 天
**来源：** 2026-07-03-skill-gap-filling-plan.md Task 3
**状态：** ✅ 已完成

### ~~2. qcloud-service-mesh-ops 新增（Service Mesh Skill）~~ ✅ 已完成
**综合评分:** 10 | **预计工作量:** 2 天
**来源：** 2026-07-03-skill-gap-filling-plan.md Task 4
**状态：** ✅ 已完成

### 3. qcloud-dc-ops 新增（专线接入 Skill）
**综合评分:** 8 | **预计工作量:** 2 天
**来源：** 2026-07-03-skill-gap-filling-plan.md Task 5
**状态：** ⏳ 未开始

**任务清单：**
- [ ] 调研 Direct Connect API（tccli dc help）
- [ ] 创建 SKILL.md
- [ ] 创建 reference 文件
- [ ] 创建 eval_queries.json
- [ ] 运行 2 轮自审 + 提交

---

## 第四批：高成本任务（综合评分 ≤ 9）

### 8. qcloud-mongodb-ops 新增（MongoDB Skill）
**综合评分:** 9 | **预计工作量:** 3 天
**来源：** 2026-05-29-qcloud-mongodb-ops.md
**状态：** ⏳ 未开始

**任务清单：**
- [ ] 创建 skill 目录结构
- [ ] 创建 SKILL.md（主 skill 文件）
- [ ] 创建 references/core-concepts.md
- [ ] 创建 references/api-sdk-usage.md
- [ ] 创建 references/cli-usage.md
- [ ] 创建 references/troubleshooting.md
- [ ] 创建 references/monitoring.md
- [ ] 创建 references/integration.md
- [ ] 创建 references/well-architected-assessment.md
- [ ] 创建 assets/example-config.yaml
- [ ] 创建 assets/eval_queries.json
- [ ] 最终验证和 charter 合规检查

### 9. CBS/CLS/CKafka skill 开发
**综合评分:** 7 | **预计工作量:** 4 天
**来源：** 2025-05-28-cbs-cls-ckafka-skills.md
**状态：** ⏳ 未开始

**任务清单：**
- [ ] CBS skill 开发（Task 1.1-1.5）
- [ ] CLS skill 开发（Task 2.1-2.3）
- [ ] CKafka skill 开发（Task 3.1-3.3）

## GCL 合规计划

### 10. GCL Tier B/C/D 合规性提升
**综合评分:** 10 | **预计工作量:** 5 天
**来源：** 2026-06-18-gcl-tier-b-c-d-conformance.md
**状态：** ⏳ 未开始

**阶段清单：**
- [ ] Phase 1: CI Enforcement Gate
- [ ] Phase 2: Tier B Rubric Flesh-Out (8 skills)
- [ ] Phase 3: Tier B Recommended-Skill Rubric Flesh-Out (6 skills)
- [ ] Phase 4: Tier B Optional-Skill Rubric (1 skill)
- [ ] Phase 5: Tier B Prompt-Templates Flesh-Out (15 skills)
- [ ] Phase 6: Tier B SKILL.md Quality Gate Expansion (15 skills)
- [ ] Phase 7: Tier C Special-Case Skills (3 skills)
- [ ] Phase 8: Tier D Skill (qcloud-skill-generator)
- [ ] Phase 9: End-to-End GCL Loop Test per Skill
- [ ] Phase 10: AGENTS.md Phase 4.1 Update

---

## 执行建议

### 优先级排序
1. **P0 任务**（Task 1-3）：新增 3 个核心 Skills，填补关键能力缺口
2. **P1 任务**（Task 4-7）：增强现有 Skills，提升运维能力
3. **P2 任务**（Task 8-9）：新增数据库和存储相关 Skills
4. **GCL 合规**（Task 10）：提升整体代码质量门禁

### 执行策略
- **并行执行**：P1 任务（Task 4-7）可以并行执行
- **依赖关系**：GCL 合规计划（Task 10）需要在其他任务完成后执行
- **验证点**：每个任务完成后运行对应的验证命令

### 验证命令
```bash
# 验证 skill 结构
python3 scripts/validate_skills_frontmatter.py

# 验证 markdown 内容
python3 scripts/check_markdown_python.py --root .

# 验证 GCL 合规性
python3 scripts/check_gcl_conformance.py
```