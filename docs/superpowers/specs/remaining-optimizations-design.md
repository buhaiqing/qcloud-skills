# 剩余优化任务 — Design & Plan

> 基于 2026-07-19 完整审计。118 个断链，8 个 Region 硬编码，1 个大文件，1 个 GCL 缺项。

---

## 1. 背景与动机

2026-07-04 的 `docs/superpowers/plans/2026-07-04-remaining-optimizations.md` 已严重过时。
本次基于当前磁盘状态重新审计，发现：

| 问题类型 | 真实数量 | 分布 |
|---------|---------|------|
| **断链（broken link）** | **118** | 29 个 skill |
| **Region 硬编码（TE-1）** | 5 处 | 4 个 skill |
| **SKILL.md 过大（TE-4）** | 1 个 | cls-ops 691 行 |
| **GCL 缺项** | 1 个 | cicd-ops rubric 0/8 |

---

## 2. 断链分类与修复策略

### 2.1 断链类别分析

```
类别 A — 引用不存在的 generator 模板文件（14 skills，18 处）
  ../qcloud-skill-generator/references/shared-skills-boilerplate.md
  → 该文件不存在，generator 用的是 SKILL.md 内联模板
  → 修复：替换为 qcloud-skill-generator/SKILL.md 内联锚点或删除引用

类别 B — 引用不存在的 worker schema 文件（17 skills，17 处）
  ../qcloud-well-architected-review/references/worker-output-schema.md
  → 该文件不存在
  → 修复：替换为 well-architected-review/references/worker-output-schema.md

类别 C — execution-flows.md 锚点格式不匹配（3 skills，多处）
  qcloud-ckafka-ops: #1-createinstance, #2-createtopic 等
  qcloud-clb-ops: #1-create-loadbalancer 等
  qcloud-cos-ops: #1-createbucket 等
  → 原因：SKILL.md 中的锚点如 `#1-createbucket` 不等于实际的 `## 1. CreateBucket`
  → 修复：更新锚点格式

类别 D — 引用整个目录而非文件（1 处）
  qcloud-ckafka-ops: ../qcloud-monitor-ops/
  → 修复：替换为 qcloud-monitor-ops/SKILL.md

类别 E — 不存在的其他文件（多处）
  qcloud-cdb-ops: cdb-slow-query-diagnosis-optimized.md（文件不存在）
  qcloud-monitor-ops: ../qcloud-skill-generator/templates/proactive-inspection.md（不存在）
  qcloud-cls-ops: ../examples/（不存在）
  qcloud-postgres-ops, qcloud-ssl-ops: references/sdk-templates.md（不存在）
  qcloud-vpn-ops: #12-multi-branch-hub-spoke-topology-deployment（锚点不存在）
  → 修复：创建缺失文件或删除/修正引用
```

### 2.2 修复规则

```
规则 1 — shared-skills-boilerplate.md 引用
  搜索所有: grep -rn "shared-skills-boilerplate" qcloud-*/SKILL.md
  替换: ../qcloud-skill-generator/SKILL.md#reference-directory
  或: ../qcloud-skill-generator/SKILL.md#five-core-standards

规则 2 — worker-output-schema.md 引用
  搜索所有: grep -rn "worker-output-schema" qcloud-*/SKILL.md
  替换: references/worker-output-schema.md
  （在 well-architected-review 下实际有该文件，但跨 skill 路径错误）

规则 3 — execution-flows.md 锚点
  搜索所有: grep -rn "#1-\|#2-\|#3-\|#4-\|#5-" qcloud-*/SKILL.md
  提取实际标题: grep "^## " qcloud-*/references/execution-flows.md
  映射: #1-createbucket → #1-createbucket 需确认匹配，否则修正

规则 4 — 目录引用
  qcloud-*/SKILL.md 中的 ../qcloud-xxx-ops/ → ../qcloud-xxx-ops/SKILL.md

规则 5 — 不存在文件引用
  cdb-slow-query-diagnosis-optimized.md → 评估：是否创建或删除引用
  sdk-templates.md → 评估：是否创建或删除引用
  templates/proactive-inspection.md → 替换为 qcloud-proactive-inspection/SKILL.md
```

---

## 3. Region 硬编码（TE-1）

### 现状

| Skill | 位置 | 内容 | 类型 |
|-------|------|------|------|
| ccn-ops | L224 | `export TENCENTCLOUD_REGION="ap-guangzhou"` | ✅ 环境变量默认值（合理）|
| clb-ops | L104 | `| Region | {{env.TENCENTCLOUD_REGION}} | Default ap-guangzhou` | ✅ 文档说明（合理）|
| cos-ops | L297 | `| Region | {{env.TENCENTCLOUD_REGION}} | Valid | Use default ap-guangzhou` | ✅ 文档说明（合理）|
| cos-ops | L485 | `"Location": "my-bucket-12345.cos.ap-guangzhou.myqcloud.com"` | ⚠️ 示例域名含 Region（TE-1，替换为 `{{env.TENCENTCLOUD_REGION}}`）|
| cvm-ops | L68-69 | `Default ap-guangzhou` in param table | ✅ 文档说明（合理）|
| migration-ops | L583 | `export TENCENTCLOUD_REGION="ap-guangzhou"` | ✅ 环境变量默认值（合理）|
| service-mesh-ops | L381 | `export TENCENTCLOUD_REGION="ap-guangzhou"` | ✅ 环境变量默认值（合理）|

**真实 TE-1 问题**：cos-ops L485 的示例域名含 `ap-guangzhou`，应在代码示例块中替换为 `{{env.TENCENTCLOUD_REGION}}` 或通用 placeholder。

---

## 4. Token 效率（TE-4）

### cls-ops SKILL.md（691 行）

文件大小：691 行，是所有 product skill 中最大。
建议：检查是否有重复的内联 bash 块可提取到 references/ 下的专门文件中。

---

## 5. GCL 缺项

### cicd-ops rubric 状态

当前 `qcloud-cicd-ops/references/rubric.md` 存在（从 ls 可见），需验证是否符合 Tier-A（8 节）。
用 `check_gcl_conformance.py` 验证。

---

## 6. 实施清单

### Phase A: 断链修复（最高优先级，118 处）

- [ ] **A1**: 替换所有 `shared-skills-boilerplate.md` 引用 → `qcloud-skill-generator/SKILL.md` 锚点（14 skills，18 处）
- [ ] **A2**: 替换所有 `worker-output-schema.md` 跨 skill 引用路径（17 skills，17 处）
- [ ] **A3**: 修复 execution-flows.md 锚点格式（ckafka, clb, cos — 多处）
- [ ] **A4**: 修复目录引用为文件引用（ckafka L581-583）
- [ ] **A5**: 处理不存在文件的引用（cdb slow-query, sdk-templates, templates, vpn multi-branch 锚点）
- [ ] **A6**: 运行 `check_markdown_links.py` 验证所有断链已修复

### Phase B: Region 硬编码（TE-1）

- [ ] **B1**: 修复 cos-ops L485 示例域名（1 处）

### Phase C: Token 效率（TE-4）

- [ ] **C1**: cls-ops SKILL.md 行数分析，提取可外置的内联 bash 块

### Phase D: GCL 验证

- [ ] **D1**: `python3 scripts/check_gcl_conformance.py` 验证 cicd-ops 等 skill GCL 状态

### Phase E: 收尾

- [ ] **E1**: `python3 scripts/validate_local.py` 全量验证通过
- [ ] **E2**: 更新 TODO.md，标记所有项完成
- [ ] **E3**: commit + merge + worktree 清理

---

## 7. Self-verify（自验证逻辑）

```python
def self_verify():
    # A6: check_markdown_links.py 应报告 0 broken links
    # B1: cos-ops L485 不含 "ap-guangzhou"
    # C1: cls-ops SKILL.md ≤ 600 行（或确认无需压缩）
    # D1: check_gcl_conformance.py 通过
    # E1: validate_local.py 全量通过
    pass
```

---

## 8. 文件清单

| 文件 | 操作 |
|------|------|
| 所有含断链的 `qcloud-*/SKILL.md` | 修改（替换引用） |
| `qcloud-cos-ops/SKILL.md` | 修改（TE-1 域名硬编码） |
| `qcloud-cls-ops/SKILL.md` | 修改（如有可提取内容） |
| `scripts/validate_local.py` | 验证通过 |
| `TODO.md` | 更新状态 |
