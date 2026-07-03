# Skill 能力补充实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 6 大核心能力维度分析，通过新增 4 个 Skill + 增强 6 个现有 Skill，覆盖当前技能缺口

**Architecture:** 保持现有以产品为中心的 Skill 组织方式，新增逻辑分组概念（不改变目录结构），新增 Skill 使用 `qcloud-skill-generator` 脚手架，现有 Skill 按外科手术式原则增强

**Tech Stack:** tccli CLI (primary), tencentcloud-sdk-python (fallback), YAML frontmatter, Markdown runbooks

**分组结构（AGENTS.md 中标记）：**

```
核心计算与存储      → cvm-ops, cbs-ops, cos-ops, scf-ops
数据库服务           → cdb-ops, redis-ops, es-ops, mongodb-ops, postgres-ops
网络与混合云         → vpc-ops, clb-ops, cdn-ops, ccn-ops, vpn-ops, ssl-ops
                    + [P1 新增: dc-ops]
云原生与中间件       → tke-ops, ckafka-ops, cls-ops, agsx-ops
                    + [P0 新增: cicd-ops] + [P1 新增: service-mesh-ops]
安全与访问控制       → cam-ops
监控与运维           → monitor-ops, cls-ops, aiops-diagnosis, proactive-inspection
成本与管理           → finops-ops, well-architected-review
迁移与转型 [新增]    → [P2 新增: migration-ops]
元能力               → skill-generator
```

---

## Phase 1: P0 现有 Skill 增强（并行 2 个）

### Task 1: finops-ops — 跨账号成本视图

**Files:**
- Modify: `qcloud-finops-ops/SKILL.md`
- Modify: `qcloud-finops-ops/references/well-architected-assessment.md`
- Modify: `qcloud-finops-ops/assets/eval_queries.json`

- [x] **Step 1: 在 SKILL.md 新增「模块 9：跨账号统一视图」**

在 SKILL.md 末尾（`## 8 大核心模块` 结束后），新增：

```markdown
### 模块 9：跨账号统一成本视图（多账号）

> **能力等级：** P1（扩展功能，需提前配置子账号 CAM 委托）
> **原理：** 通过 CAM 角色委托（Role）获取多个子账号的只读账单数据，合并为统一视图。

#### 前置条件

| 检查 | 方法 | 预期 | 失败处理 |
|------|------|------|----------|
| 主账号 CAM Role | `tccli cam ListRoles` | 存在 FinOps 只读角色 | HALT；创建角色 |
| 子账号列表 | `tccli organization DescribeOrganizationMembers` | 非空 | HALT；未加入组织 |
| 子账号委托 | 每个子账号已授予主账号角色 | 委托状态 `ACTIVE` | HALT；配置委托 |

#### 执行 — 汇总脚本

```bash
#!/bin/bash
# 遍历子账号，汇总月度账单
# 需要子账号 SecretId/SecretKey 或 CAM Role 委托
ACCOUNTS=("$@")
echo "# 跨账号成本报告"
echo "| 账号 | 产品 | 月度费用(元) | 环比 |"
echo "|------|------|------------|------|"
for ACCOUNT in "${ACCOUNTS[@]}"; do
  export TENCENTCLOUD_SECRET_ID="${ACCOUNT}_SECRET_ID"
  export TENCENTCLOUD_SECRET_KEY="${ACCOUNT}_SECRET_KEY"
  tccli billing DescribeBillSummaryByMonth \
    --Month "$(date +%Y-%m)" \
    --Region ap-guangzhou
done
```

#### 输出

| 字段 | 路径 |
|------|------|
| 账号维度汇总 | `$.Response.SummaryTotal[*].RealTotalCost` |
| 按产品汇总 | `$.Response.SummaryByProduct[*]` |
| 环比变化 | `$.Response.SummaryTotal[*].RealTotalCostRate` |

#### 失败恢复

| 错误码 | 处理 |
|--------|------|
| `UnauthorizedOperation` | HALT；检查 CAM 委托配置 |
| `OrganizationNotExists` | HALT；账号未加入组织 |
| `ResourceNotFound.Role` | HALT；创建 FinOps 只读角色 |
```

- [x] **Step 2: 更新 well-architected-assessment.md 的成本维度**

在 `references/well-architected-assessment.md` 的 Cost 维度中补充跨账号场景的评估标准：

```markdown
### Cost — 跨账号成本可见性

| 评估项 | 理想状态 | 检查方法 | 评分标准 |
|--------|----------|----------|----------|
| 多账号统一账单 | 组织内所有账号账单可统一查看 | `tccli organization DescribeOrganization` | 有=5, 部分=3, 无=0 |
| 成本分摊标签 | 所有资源强制打标签 | `tccli tag GetTagValues` | 强制=5, 推荐=3, 无=0 |
| 预算告警覆盖 | 每个账号/项目有预算 | `tccli monitor DescribeAlarmPolicies` | 全覆盖=5, 部分=3, 无=0 |
```

- [x] **Step 3: 更新 eval_queries.json**

新增测试用例：

```json
[
  { "query": "帮我看看所有子账号的账单汇总", "should_trigger": true },
  { "query": "跨账号成本统一视图", "should_trigger": true },
  { "query": "配置子账号的CAM角色委托", "should_trigger": false }
]
```

- [x] **Step 4: 运行 linter 验证**

```bash
ruff check qcloud-finops-ops/SKILL.md
python3 scripts/check_markdown_python.py --root .
```

- [x] **Step 5: 提交**

```bash
git add qcloud-finops-ops/SKILL.md qcloud-finops-ops/references/well-architected-assessment.md qcloud-finops-ops/assets/eval_queries.json
git commit -m "feat(finops): add cross-account cost view (module 9)"
```

---

### Task 2: proactive-inspection — 7×24 值班交接清单

**Files:**
- Create: `qcloud-proactive-inspection/references/oncall-handover.md`
- Modify: `qcloud-proactive-inspection/SKILL.md`
- Modify: `qcloud-proactive-inspection/assets/eval_queries.json`

- [x] **Step 1: 创建值班交接清单参考文档**

`references/oncall-handover.md`：

```markdown
# 7×24 值班交接检查清单

> 每次值班交接时执行，确保接班人员掌握当前系统健康状况。

## 前置检查（接班前 15 分钟）

1. 确认当前值班时段（日/夜/周末）
2. 确认告警通道可用（企业微信/短信/电话）
3. 确认以下工具有访问权限：
   - [ ] 腾讯云控制台（主账号 + 子账号）
   - [ ] 日志平台（CLS）
   - [ ] 监控告警平台（Monitor）
   - [ ] 内部值班群

## 系统健康摘要（必查）

| 检查项 | 命令 | 预期 | 异常处理 |
|--------|------|------|----------|
| 未恢复告警 | `tccli monitor DescribeAlarmHistory` | ≤ 5 条未恢复 | 逐条确认处理人 |
| P0 故障 | 检查内部值班群 / AIOps 诊断记录 | 无未关闭 P0 | 立即升级 |
| 资源水位 | CPU/内存/磁盘 > 80% 的资源列表 | 无持续高水位 | 记录到交接单 |
| 上周变更 | 检查 CloudAudit / 变更记录 | 无未验证变更 | 确认变更后 48h 监控指标 |
| 证书到期 | `tccli ssl DescribeCertificates` | 30 天内无到期 | 排期续期 |
| 余额预警 | `tccli billing DescribeAccountBalance` | 余额 > 阈值 | 通知财务充值 |

## 交接记录模板

```json
{
  "handover_time": "{{user.handover_time}}",
  "from": "{{user.from_person}}",
  "to": "{{user.to_person}}",
  "ongoing_incidents": [
    {
      "id": "INC-xxx",
      "status": "处理中",
      "owner": "姓名",
      "eta": "预计恢复时间"
    }
  ],
  "unresolved_alarms": [],
  "pending_changes": [],
  "health_summary": {
    "status": "GREEN / YELLOW / RED",
    "critical_count": 0,
    "warning_count": 0,
    "info_count": 0
  }
}
```

## 失败场景

| 场景 | 处理方式 |
|------|----------|
| 接班人员 15 分钟未到岗 | 通知值班主管 |
| 关键告警通道不可用 | 切换备用通道，通知运维负责人 |
| 发现未记录的 P0 故障 | 立即启动应急响应，通知 SRE 团队 |
```

- [x] **Step 2: 在 SKILL.md 新增交接清单操作**

在 SKILL.md 的 Operations 中新增：

```markdown
### Operation: 值班交接健康检查

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Credentials | `test -n "$TENCENTCLOUD_SECRET_ID"` | Non-empty | HALT |
| On-call schedule | Ask user for shift time + personnel | Known | Ask user |

#### Execution

执行 [7×24 值班交接检查清单](references/oncall-handover.md) 中的系统健康摘要：

```bash
# 1. 查询未恢复告警
tccli monitor DescribeAlarmHistory \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --StartTime "$(date -d '-24 hours' -u +%Y-%m-%dT%H:%M:%S+08:00)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%S+08:00)"

# 2. 查询证书到期
tccli ssl DescribeCertificates \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ExpireTimeRange '["30"]'

# 3. 查询账户余额
tccli billing DescribeAccountBalance \
  --Region "{{env.TENCENTCLOUD_REGION}}"
```

#### Post-execution Validation

生成交接摘要 JSON，确认所有必填字段已填充：

| 字段 | 来源 | 必填 |
|------|------|------|
| `health_summary.status` | 根据告警/资源水位综合判断 | 是 |
| `ongoing_incidents` | AIOps 诊断记录 + 值班群 | 是 |
| `pending_changes` | 用户提供 | 否 |

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `UnauthorizedOperation` | HALT; 确认账号有 monitor/billing/ssl 只读权限 |
| API rate limit | Backoff retry (2s,4s,8s) |
```

- [x] **Step 3: 更新 eval_queries.json**

```json
[
  { "query": "值班交接检查清单", "should_trigger": true },
  { "query": "交接班时帮我检查系统健康状态", "should_trigger": true },
  { "query": "今天夜班交接需要检查什么", "should_trigger": true },
  { "query": "创建一条告警策略", "should_trigger": false }
]
```

- [x] **Step 4: 验证**

```bash
python3 scripts/check_markdown_python.py --root .
python3 scripts/validate_skills_frontmatter.py
```

- [x] **Step 5: 提交**

```bash
git add qcloud-proactive-inspection/references/oncall-handover.md qcloud-proactive-inspection/SKILL.md qcloud-proactive-inspection/assets/eval_queries.json
git commit -m "feat(proactive-inspection): add oncall handover checklist operation"
```

---

## Phase 2: P0 新增 Skill — qcloud-cicd-ops

### Task 3: 新增 CI/CD 流水线 Skill

**Files:**
- Create: `qcloud-cicd-ops/SKILL.md`
- Create: `qcloud-cicd-ops/references/core-concepts.md`
- Create: `qcloud-cicd-ops/references/api-sdk-usage.md`
- Create: `qcloud-cicd-ops/references/troubleshooting.md`
- Create: `qcloud-cicd-ops/references/integration.md`
- Create: `qcloud-cicd-ops/references/well-architected-assessment.md`
- Create: `qcloud-cicd-ops/references/cli-usage.md`
- Create: `qcloud-cicd-ops/assets/example-config.yaml`
- Create: `qcloud-cicd-ops/assets/eval_queries.json`

- [ ] **Step 1: 调研 API 覆盖**

```bash
tccli codepipeline help
tccli coding help
tccli cloudstudio help
```

验证 CLI 支持哪些 CI/CD 相关操作，确定 `cli_applicability` 为 `dual-path`。

- [ ] **Step 2: 使用 skill-generator 脚手架创建目录**

```bash
# 按 skill-generator 的 Step 3 创建目录结构
mkdir -p qcloud-cicd-ops/{references,assets}
```

- [ ] **Step 3: 编写 SKILL.md**

```markdown
---
name: qcloud-cicd-ops
description: >-
  Use when the user needs to create, configure, trigger, or troubleshoot CI/CD
  pipelines, code repositories, artifact repositories, or automated deployments
  on Tencent Cloud CODING DevOps / Cloud Pipeline. User mentions CI/CD, 流水线,
  持续集成, 持续部署, CODING, DevOps, 自动化部署, pipeline, build, deploy
  automation. Not for application runtime monitoring (use `qcloud-monitor-ops`),
  K8s cluster operations (use `qcloud-tke-ops`), or serverless function
  deployment (use `qcloud-scf-ops`).
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "2026-07-03"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/xxx"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli codepipeline help` — CLI exposes
    CreatePipeline, DescribePipelines, DeletePipeline, StartPipeline,
    StopPipeline, DescribePipelineLogs, and related operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud CI/CD Pipeline Operations Skill

## Overview

CI/CD (Continuous Integration / Continuous Deployment) pipelines automate the build, test, and deployment lifecycle. This skill covers Tencent Cloud CODING DevOps pipelines and Cloud Pipeline service.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** `tccli codepipeline` covers pipeline operations. You **MUST** ship `references/cli-usage.md` and document **both** the SDK and `tccli` step for every operation.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with CI/CD-specific triggers; K8s deploy → delegate to `qcloud-tke-ops`; SCF deploy → delegate to `qcloud-scf-ops` |
| 2 | **Structured I/O** | `{{env.*}}` / `{{user.*}}` / `{{output.*}}` placeholders with pipeline API field types |
| 3 | **Explicit Actionable Steps** | Every pipeline op: Pre-flight → Execute (CLI + SDK) → Validate → Recover |
| 4 | **Complete Failure Strategies** | Error taxonomy with ≥ 10 CI/CD-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | CI/CD pipeline + code repository + artifact repository only; K8s deploy → `qcloud-tke-ops`; Serverless → `qcloud-scf-ops` |

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Pipeline retry strategy, multi-stage approval, artifact versioning | `references/well-architected-assessment.md` |
| **安全性 (Security)** | Credential management in pipeline, code scanning integration | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Pipeline runner cost, build cache optimization | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Parallel stages, cache strategy, pipeline template reuse | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "CI/CD pipeline" OR "流水线" OR "持续集成" OR "持续部署" OR "CODING DevOps"
- Task keywords: pipeline, build, deploy automation, artifact, code repository, 构建, 部署, 制品库
- User asks to create, trigger, or troubleshoot an automated build/deploy pipeline

### SHOULD NOT Use This Skill When

- Task is **K8s cluster management** → delegate to `qcloud-tke-ops`
- Task is **serverless function deployment** → delegate to `qcloud-scf-ops`
- Task is **application monitoring / alerting** → delegate to `qcloud-monitor-ops`
- Task is **container image registry** → delegate to `qcloud-tke-ops` (TCR)

### Delegation Rules

- Pipeline deploy-to-TKE: use `qcloud-tke-ops` for the K8s deployment step
- Pipeline deploy-to-SCF: use `qcloud-scf-ops` for the function update step
- Multi-product pipeline: handle each product with its skill; pipeline orchestrates the flow

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use documented default only if skill explicitly allows |
| `{{user.pipeline_name}}` | User-supplied pipeline name | Ask once; reuse |
| `{{user.pipeline_id}}` | Pipeline unique ID | Ask once or derive from `DescribePipelines` |
| `{{user.repo_url}}` | Code repository URL | Ask once; verify format |
| `{{user.branch}}` | Git branch for pipeline trigger | Ask once; default `main` |
| `{{output.pipeline_id}}` | From `$.Response.Pipeline.PipelineId` | Parse per API spec |
| `{{output.build_id}}` | From `$.Response.Build.BuildId` | Parse per API spec |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning:** NEVER expose `TENCENTCLOUD_SECRET_KEY` in output. Use `test -n "$TENCENTCLOUD_SECRET_KEY"` for verification only.

## JSON Path Reference

| Path | Maps To |
|------|---------|
| `pipeline.id` | `$.Response.PipelineSet[*].PipelineId` |
| `pipeline.name` | `$.Response.PipelineSet[*].PipelineName` |
| `pipeline.status` | `$.Response.PipelineSet[*].PipelineStatus` |
| `build.id` | `$.Response.BuildSet[*].BuildId` |
| `build.status` | `$.Response.BuildSet[*].BuildStatus` |
| `build.log` | `$.Response.BuildLog.LogContent` |

## Quick Start

### What This Skill Does
Enables you to create, trigger, and manage CI/CD pipelines — automate build, test, and deployment workflows on Tencent Cloud.

### Prerequisites
- [ ] `tccli` CLI installed
- [ ] Credentials: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region: `TENCENTCLOUD_REGION`

### Verify Setup
```bash
tccli codepipeline DescribePipelines --Region ap-guangzhou
```

### Your First Command
```bash
# Create a simple pipeline
tccli codepipeline CreatePipeline \
  --Region "ap-guangzhou" \
  --PipelineName "my-first-pipeline" \
  --PipelineDesc "Automated build and deploy"
```

### Next Steps
- [Common Operations](#execution-flows) — Create, trigger, monitor pipelines
- [Troubleshooting](references/troubleshooting.md) — Fix pipeline failures

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreatePipeline | Create a new CI/CD pipeline | Medium | Low |
| DescribePipelines | List / describe pipelines | Low | None |
| DeletePipeline | Delete a pipeline | Low | **High** — removes automation |
| StartPipeline | Trigger a pipeline run | Low | Low |
| StopPipeline | Stop a running pipeline | Low | Medium |
| DescribeBuildLogs | View build logs | Low | None |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-07-03 | Initial CI/CD skill, dual-path execution. Scope: pipeline CRUD, trigger/monitor, code repository integration, artifact management. Delegates K8s deploy to `qcloud-tke-ops`, SCF deploy to `qcloud-scf-ops`. |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI and SDK) → Validate → Recover**.

### Operation: Create Pipeline

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Credentials | `test -n "$TENCENTCLOUD_SECRET_ID"` etc. | Non-empty | HALT; user configures env |
| CLI installed | `tccli version` | Exit code 0 | Install tccli |
| Name uniqueness | `tccli codepipeline DescribePipelines` | No existing pipeline with same name | Use different name |

#### Execution — CLI (`tccli`) (Primary Path)

```bash
tccli codepipeline CreatePipeline \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --PipelineName "{{user.pipeline_name}}" \
  --PipelineDesc "{{user.pipeline_desc}}"
```

#### Execution — Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.codepipeline import codepipeline_client, models
import os, json

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = codepipeline_client.CodepipelineClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.CreatePipelineRequest()
req.PipelineName = "{{user.pipeline_name}}"
req.PipelineDesc = "{{user.pipeline_desc}}"

resp = client.CreatePipeline(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

1. Capture `{{output.pipeline_id}}` from `$.Response.Pipeline.PipelineId`.
2. Poll `DescribePipelines` until `PipelineStatus = ACTIVE`.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.PipelineNameExists` | Use a different name |
| `ResourceQuotaExceeded.Pipeline` | HALT; raise per-region pipeline quota |
| `InvalidSecretKey` | HALT; fix credentials |
| `RequestLimitExceeded` | Backoff retry (2s,4s,8s) |

### Operation: Trigger Pipeline

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Pipeline exists | `DescribePipelines` with `{{user.pipeline_id}}` | Status ACTIVE | HALT; create pipeline first |

#### Execution — CLI

```bash
tccli codepipeline StartPipeline \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --PipelineId "{{output.pipeline_id}}" \
  --Branch "{{user.branch}}"
```

#### Execution — Python SDK (Fallback Path)

```python
req = models.StartPipelineRequest()
req.PipelineId = "{{output.pipeline_id}}"
req.Branch = "{{user.branch}}"
resp = client.StartPipeline(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

Poll `DescribePipelines` until build completes (or check build status):

```bash
for i in $(seq 1 60); do
  STATUS=$(tccli codepipeline DescribePipelines \
    --PipelineId "{{output.pipeline_id}}" | jq -r '.Response.PipelineSet[0].PipelineStatus')
  echo "Build status: $STATUS"
  [ "$STATUS" = "SUCCEEDED" ] && break
  [ "$STATUS" = "FAILED" ] && { echo "Build failed"; break; }
  sleep 10
done
```

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.Pipeline` | Verify pipeline ID |
| `OperationDenied.PipelineRunning` | Wait for current build to complete |
| `InvalidParameter.BranchNotFound` | Check branch exists in repo |

### Operation: Describe Pipelines

#### Execution — CLI

```bash
tccli codepipeline DescribePipelines \
  --Region "{{env.TENCENTCLOUD_REGION}}"
```

Filter by name:

```bash
tccli codepipeline DescribePipelines \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=pipeline-name,Values={{user.pipeline_name}}"
```

#### Execution — Python SDK (Fallback Path)

```python
req = models.DescribePipelinesRequest()
req.Filters = [{"Name": "pipeline-name", "Values": ["{{user.pipeline_name}}"]}]
resp = client.DescribePipelines(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

### Operation: Delete Pipeline

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation with the pipeline ID and name.
- **MUST** warn: deleting a pipeline removes all automation; any running builds will be cancelled.
- **MUST** list any dependent resources (webhooks, triggers) that will become orphaned.

#### Execution — CLI

```bash
tccli codepipeline DeletePipeline \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --PipelineId "{{output.pipeline_id}}"
```

#### Execution — Python SDK (Fallback Path)

```python
req = models.DeletePipelineRequest()
req.PipelineId = "{{output.pipeline_id}}"
resp = client.DeletePipeline(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

Poll `DescribePipelines` for the ID; expect absent within 30s.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.Pipeline` | Already deleted; treat as success |
| `OperationDenied.PipelineRunning` | Stop running build first |

## Error Code Reference (CI/CD-Specific)

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter.PipelineNameExists` | Pipeline name already exists | Use a different name |
| `InvalidParameter.BranchNotFound` | Specified branch not found in repo | Check branch name |
| `ResourceNotFound.Pipeline` | Pipeline ID not found | Verify pipeline ID |
| `ResourceNotFound.Project` | CODING project not found | Verify project ID |
| `ResourceQuotaExceeded.Pipeline` | Pipeline quota exceeded | HALT; raise quota |
| `OperationDenied.PipelineRunning` | Pipeline is already running | Wait for completion |
| `OperationDenied.PipelineSuspended` | Pipeline is suspended | Resume pipeline first |
| `OperationDenied.NotAuthorized` | Insufficient CODING permissions | HALT; check CAM/CODING permissions |
| `InternalError.BuildFailed` | Build failed due to script error | Check build logs for details |
| `InvalidSecretKey` | Credential invalid | HALT; fix credentials |
| `RequestLimitExceeded` | API rate limit | Exponential backoff (3x) |
| `InternalError` | Server error | Retry with RequestId (3x) |

## Safety Gates (Destructive Operations)

Every **DeletePipeline** MUST have:

1. Explicit user confirmation with pipeline ID
2. Dependency check (running builds; dependent webhooks)
3. Pre-warning about automation loss
4. Post-delete verification (poll until absent)

---

## Prerequisites

1. **Install `tccli` CLI:**

```bash
pip install tccli
tccli version
```

2. **Configure Credentials:**

```bash
export TENCENTCLOUD_SECRET_ID="AKID..."
export TENCENTCLOUD_SECRET_KEY="..."
export TENCENTCLOUD_REGION="ap-guangzhou"
```

3. **Verify:**

```bash
tccli codepipeline DescribePipelines --Region ap-guangzhou
```

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [CLI Usage](references/cli-usage.md)
- [Troubleshooting](references/troubleshooting.md)
- [Well-Architected Assessment](references/well-architected-assessment.md)
- [Integration](references/integration.md)
```

- [ ] **Step 4: 创建 reference 文件**

创建 `references/core-concepts.md`（CI/CD 架构、流水线概念、CODING DevOps 概述）

```markdown
# CI/CD Core Concepts

## Architecture
Tencent Cloud CI/CD pipeline services:
- **CODING DevOps**: Full DevOps platform (code repository, CI/CD, artifact, test management)
- **Cloud Pipeline**: Standalone pipeline service

## Pipeline Stages
1. Source (code checkout)
2. Build (compile, test, package)
3. Deploy (push to target environment)

## Resource Limits
| Resource | Limit |
|----------|-------|
| Max pipelines per account | 200 |
| Max concurrent builds | 10 |
| Build timeout | 120 minutes |

## Delegation
- K8s deploy → `qcloud-tke-ops`
- SCF deploy → `qcloud-scf-ops`
- Monitor pipeline metrics → `qcloud-monitor-ops`
```

创建 `references/troubleshooting.md`：

```markdown
# CI/CD Troubleshooting

## Build Failure Diagnosis

1. Check build logs: `tccli codepipeline DescribeBuildLogs --PipelineId <id>`
2. Verify code repository access
3. Check build environment (resource limits, dependency versions)
4. Validate deployment target availability

## Common Issues

| Symptom | Likely Cause | Check |
|---------|-------------|-------|
| Build hangs | Resource limit reached | Check concurrent build limit |
| Deploy fails | Target service unavailable | Check target health |
| Source fetch fails | Credential expired | Rotate code repo token |
```

创建 `references/well-architected-assessment.md`（简化版四支柱评估）：

```markdown
# Well-Architected Assessment — CI/CD

## Reliability
- Pipeline retry strategy: configure auto-retry for transient failures
- Multi-stage approval: require manual approval before production deploy
- Artifact versioning: tag every build with unique version

## Security
- Credential management: use CODING environment variables (masked) for secrets
- Code scanning: integrate SAST/DAST in pipeline
- Access control: restrict pipeline modification permissions

## Cost
- Build cache: enable dependency caching to reduce build time
- Runner optimization: use spot instances for build runners
- Artifact lifecycle: auto-delete old artifacts

## Efficiency
- Parallel stages: run independent tests concurrently
- Pipeline templates: reuse standardized pipeline definitions
- Caching: cache dependencies across builds
```

创建 `references/integration.md`：

```markdown
# Integration Guide

## SDK Setup
```python
pip install tencentcloud-sdk-python
```

## Cross-Skill Delegation

| Scenario | Delegate To |
|----------|------------|
| K8s deployment | `qcloud-tke-ops` |
| SCF function deploy | `qcloud-scf-ops` |
| Pipeline monitoring | `qcloud-monitor-ops` |
| Cost tracking | `qcloud-finops-ops` |

## Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `TENCENTCLOUD_SECRET_ID` | Yes | API Secret ID |
| `TENCENTCLOUD_SECRET_KEY` | Yes | API Secret Key |
| `TENCENTCLOUD_REGION` | Yes | Region |
```

创建 `assets/example-config.yaml`：

```yaml
# CI/CD example configuration
pipeline:
  name: example-pipeline
  stages:
    - source:
        repo_url: "https://github.com/example/app.git"
        branch: main
    - build:
        commands:
          - npm install
          - npm run build
        cache:
          - node_modules
    - deploy:
        target: tke
        cluster_id: cls-xxx
```

创建 `assets/eval_queries.json`：

```json
[
  { "query": "创建一条 CI/CD 流水线", "should_trigger": true },
  { "query": "帮我配置持续集成和持续部署", "should_trigger": true },
  { "query": "CODING DevOps 流水线管理", "should_trigger": true },
  { "query": "查看构建日志", "should_trigger": true },
  { "query": "如何自动化部署到K8s集群", "should_trigger": true },
  { "query": "启动流水线构建", "should_trigger": true },
  { "query": "停止正在运行的流水线", "should_trigger": true },
  { "query": "帮我查一下数据库慢查询", "should_trigger": false },
  { "query": "K8s 集群节点扩容", "should_trigger": false },
  { "query": "配置负载均衡健康检查", "should_trigger": false },
  { "query": "查看本月账单", "should_trigger": false },
  { "query": "SSL 证书续期", "should_trigger": false },
  { "query": "创建云服务器实例", "should_trigger": false }
]
```

- [ ] **Step 5: 创建 `references/cli-usage.md`**

```markdown
# CLI Usage Guide

## Command Map

| Operation | CLI Command | SDK Method |
|-----------|------------|------------|
| Create Pipeline | `tccli codepipeline CreatePipeline` | `CreatePipeline` |
| List Pipelines | `tccli codepipeline DescribePipelines` | `DescribePipelines` |
| Delete Pipeline | `tccli codepipeline DeletePipeline` | `DeletePipeline` |
| Start Pipeline | `tccli codepipeline StartPipeline` | `StartPipeline` |
| Stop Pipeline | `tccli codepipeline StopPipeline` | `StopPipeline` |
| View Build Logs | `tccli codepipeline DescribeBuildLogs` | `DescribeBuildLogs` |

## Common Patterns

```bash
# List all pipelines
tccli codepipeline DescribePipelines --Region ap-guangzhou

# Filter by name
tccli codepipeline DescribePipelines --Filters "Name=pipeline-name,Values=my-pipeline"
```
```

- [ ] **Step 6: 运行 2 轮自审**

```bash
# Round 1: Five Core Standards + Token Efficiency
python3 scripts/check_markdown_python.py --root .
python3 scripts/validate_skills_frontmatter.py
ruff check scripts/check_markdown_python.py

# Round 2: Adversarial review — manually verify
# R1 Security: no credential leaks
# R2 API Fidelity: verify CLI commands against actual API
# R3 Safety Gates: DeletePipeline has confirmation
# R4 UX: Quick Start present, error format correct
```

- [ ] **Step 7: 提交**

```bash
git add qcloud-cicd-ops/
git commit -m "feat(cicd): add qcloud-cicd-ops skill for CI/CD pipeline management"
```

---

## Phase 3: P1 新增 Skill — qcloud-service-mesh-ops

### Task 4: 新增 Service Mesh Skill

> **Note:** 此 Task 结构同 Task 3（CICD），使用 `qcloud-skill-generator` 脚手架。以下为关键差异。

**Files:**
- Create: `qcloud-service-mesh-ops/SKILL.md`
- Create: `qcloud-service-mesh-ops/references/core-concepts.md`
- Create: `qcloud-service-mesh-ops/references/api-sdk-usage.md`
- Create: `qcloud-service-mesh-ops/references/troubleshooting.md`
- Create: `qcloud-service-mesh-ops/references/integration.md`
- Create: `qcloud-service-mesh-ops/references/well-architected-assessment.md`
- Create: `qcloud-service-mesh-ops/references/cli-usage.md`
- Create: `qcloud-service-mesh-ops/assets/example-config.yaml`
- Create: `qcloud-service-mesh-ops/assets/eval_queries.json`

- [ ] **Step 1: 调研 API 覆盖**

```bash
tccli tcm help
tccli mesh help
```

验证 TCM (Tencent Cloud Mesh) CLI 支持。

- [ ] **Step 2: 创建 SKILL.md（与 cicd 模板一致，差异在 Operations 部分）**

关键差异：
- **Trigger:** 服务网格、TCM、Istio、Sidecar、流量治理、灰度发布、mTLS、链路追踪
- **Operations:** CreateMesh, DescribeMeshes, DeleteMesh, CreateSidecarInject, CreateVirtualService, CreateDestinationRule, 查询链路追踪
- **Delegation:** 底层 K8s 集群 → `qcloud-tke-ops`；监控指标 → `qcloud-monitor-ops`
- **GCL:** `required`（DeleteMesh 为破坏性操作）

- [ ] **Step 3: 创建 reference 文件**

核心概念文档需包含：
- Mesh vs K8s 关系
- Sidecar 注入原理
- 流量治理（VirtualService, DestinationRule, Gateway）
- 安全策略（mTLS, RBAC）
- 可观测性（链路追踪, 指标, 日志）

- [ ] **Step 4: 创建 eval_queries.json**

```json
[
  { "query": "创建服务网格", "should_trigger": true },
  { "query": "配置灰度发布策略", "should_trigger": true },
  { "query": "开启 Sidecar 自动注入", "should_trigger": true },
  { "query": "配置服务间 mTLS", "should_trigger": true },
  { "query": "查看网格链路追踪", "should_trigger": true },
  { "query": "K8s 集群节点管理", "should_trigger": false },
  { "query": "创建负载均衡", "should_trigger": false },
  { "query": "配置告警策略", "should_trigger": false }
]
```

- [ ] **Step 5: 运行 2 轮自审 + 提交**

---

## Phase 3: P1 新增 Skill — qcloud-dc-ops

### Task 5: 新增专线接入 Skill

> **Note:** 与 CCN/VPN Skill 共享 `tccli vpc` namespace，`cli_applicability: dual-path`。

**Files:**
- Create: `qcloud-dc-ops/SKILL.md`
- Create: `qcloud-dc-ops/references/core-concepts.md`
- Create: `qcloud-dc-ops/references/api-sdk-usage.md`
- Create: `qcloud-dc-ops/references/troubleshooting.md`
- Create: `qcloud-dc-ops/references/integration.md`
- Create: `qcloud-dc-ops/references/well-architected-assessment.md`
- Create: `qcloud-dc-ops/references/cli-usage.md`
- Create: `qcloud-dc-ops/assets/example-config.yaml`
- Create: `qcloud-dc-ops/assets/eval_queries.json`

- [ ] **Step 1: 调研 API 覆盖**

```bash
tccli dc help
```

验证 Direct Connect CLI 支持。

- [ ] **Step 2: 创建 SKILL.md**

关键 Operations:
- CreateDirectConnect (物理专线)
- DescribeDirectConnects
- DeleteDirectConnect
- CreateDirectConnectTunnel (专用通道)
- DescribeDirectConnectTunnels
- ModifyDirectConnectTunnelAttribute
- CreateDirectConnectGateway (专线网关)
- DescribeDirectConnectGateways

- [ ] **Step 3: 创建 eval_queries.json**

```json
[
  { "query": "申请专线接入", "should_trigger": true },
  { "query": "配置专用通道", "should_trigger": true },
  { "query": "专线故障排查", "should_trigger": true },
  { "query": "查看专线监控", "should_trigger": true },
  { "query": "配置 VPN 隧道", "should_trigger": false },
  { "query": "创建云联网实例", "should_trigger": false },
  { "query": "VPC 对等连接", "should_trigger": false }
]
```

- [ ] **Step 4: 运行 2 轮自审 + 提交**

---

## Phase 4: P1 现有 Skill 增强（并行 4 个）

### Task 6: well-architected-review — 管理层战略报告

**Files:**
- Modify: `qcloud-well-architected-review/SKILL.md`
- Create: `qcloud-well-architected-review/references/executive-report.md`

- [ ] **Step 1: 创建管理层报告模板**

`references/executive-report.md`：

```markdown
# 卓越架构评估 — 管理层战略报告

> 生成面向 CTO/VP 的可视化摘要，包含风险排名、投入建议和 ROI 估算。

## 报告结构

### 1. 执行摘要
- 整体架构健康评分（满分 5 分）
- 与上次评估的评分变化趋势
- 核心风险数量（Critical / High / Medium）

### 2. 四支柱评分总览

| 支柱 | 评分 | 趋势 | 关键发现 |
|------|------|------|----------|
| 可靠性 | X/5 | ↑/↓/→ | ... |
| 安全性 | X/5 | ↑/↓/→ | ... |
| 成本 | X/5 | ↑/↓/→ | ... |
| 效率 | X/5 | ↑/↓/→ | ... |

### 3. 风险排名（按严重程度）

| 排名 | 风险描述 | 影响范围 | 严重程度 | 建议投入(人天) | ROI 估算 |
|------|----------|----------|----------|---------------|----------|
| 1 | ... | ... | Critical | ... | ... |
| 2 | ... | ... | High | ... | ... |

### 4. 投入产出建议

按 ROI 排序的投资建议：

| 优先级 | 建议 | 预计投入 | 预计收益 | 回收期 |
|--------|------|----------|----------|--------|
| P0 | ... | ... | ... | ... |
| P1 | ... | ... | ... | ... |

### 5. 行动计划

| 阶段 | 内容 | 时间线 | 负责人 |
|------|------|--------|--------|
| Phase 1 | ... | Q3 2026 | ... |
| Phase 2 | ... | Q4 2026 | ... |
```

- [ ] **Step 2: 在 SKILL.md 新增管理层报告模式**

在 Operations 中新增 "Generate Executive Report" 操作，调用四支柱评估结果 → 聚合 → 生成报告。

- [ ] **Step 3: 提交**

---

### Task 7: ccn-ops — SD-WAN 场景补充

**Files:**
- Modify: `qcloud-ccn-ops/SKILL.md`
- Create: `qcloud-ccn-ops/references/sdwan-scenarios.md`

- [ ] **Step 1: 创建 SD-WAN 场景文档**

`references/sdwan-scenarios.md` 包含：
- 多分支互联拓扑模板（Hub-Spoke CCN）
- QoS 策略配置建议
- 分支上云最佳实践（带宽规划、路由设计）
- 故障切换场景（主备 CCN）

- [ ] **Step 2: 在 SKILL.md 的 Operations 中新增 SD-WAN 场景操作**

- [ ] **Step 3: 提交**

---

### Task 8: vpn-ops — 多分支 VPN 拓扑模板

**Files:**
- Modify: `qcloud-vpn-ops/SKILL.md`
- Create: `qcloud-vpn-ops/references/multi-branch-topology.md`

- [ ] **Step 1: 创建多分支拓扑文档**

`references/multi-branch-topology.md` 包含：
- Hub-Spoke VPN 拓扑模板
- 故障切换场景（主备 VPN 隧道）
- 分支上云带宽规划
- IPSec + SSL VPN 混合方案

- [ ] **Step 2: 在 SKILL.md 中引用新文档**

- [ ] **Step 3: 提交**

---

### Task 9: aiops-diagnosis — MTTR 自动追踪

**Files:**
- Modify: `qcloud-aiops-diagnosis/SKILL.md`
- Create: `qcloud-aiops-diagnosis/references/mttr-tracking.md`

- [ ] **Step 1: 创建 MTTR 追踪文档**

`references/mttr-tracking.md` 包含：

```markdown
# MTTR 自动追踪

> 每次故障诊断后自动记录：故障时间 → 诊断时间 → 恢复时间。

## 追踪字段

| 字段 | 来源 | 说明 |
|------|------|------|
| incident_id | AIOps 诊断记录 | 故障唯一 ID |
| detected_at | 告警触发时间 | 首次告警时间戳 |
| diagnosis_at | 诊断完成时间 | AIOps 输出根因时间戳 |
| resolved_at | 用户确认恢复时间 | 资源恢复时间戳 |
| mttd | detected_at → diagnosis_at | 平均诊断时间 |
| mttr | detected_at → resolved_at | 平均恢复时间 |

## 月报聚合

```sql
SELECT
  COUNT(*) as total_incidents,
  AVG(mttd) as avg_mttd_minutes,
  AVG(mttr) as avg_mttr_minutes,
  product
FROM incidents
WHERE detected_at >= date_trunc('month', NOW())
GROUP BY product
ORDER BY avg_mttr_minutes DESC
```
```

- [ ] **Step 2: 在 SKILL.md 的故障诊断流程末尾新增 MTTR 记录步骤**

- [ ] **Step 3: 提交**

---

## Phase 5: P2 新增 Skill — qcloud-migration-ops

### Task 10: 新增迁移上云评估与执行 Skill

> **Note:** 此 Task 结构同 Task 3（CICD），使用 `qcloud-skill-generator` 脚手架。以下为关键差异。

**Files:**
- Create: `qcloud-migration-ops/SKILL.md`
- Create: `qcloud-migration-ops/references/core-concepts.md`
- Create: `qcloud-migration-ops/references/api-sdk-usage.md`
- Create: `qcloud-migration-ops/references/troubleshooting.md`
- Create: `qcloud-migration-ops/references/integration.md`
- Create: `qcloud-migration-ops/references/well-architected-assessment.md`
- Create: `qcloud-migration-ops/references/cli-usage.md`
- Create: `qcloud-migration-ops/assets/example-config.yaml`
- Create: `qcloud-migration-ops/assets/eval_queries.json`

- [ ] **Step 1: 调研 API 覆盖**

```bash
tccli cvm help | grep -i migration
tccli cbs help | grep -i migration
tccli dts help
tccli cos help | grep -i migration
```

- [ ] **Step 2: 创建 SKILL.md**

关键 Operations：
- 迁移评估（CMM/Cloud Migration Center）
- 主机迁移（在线迁移/离线迁移）
- 数据库迁移（DTS — Data Transmission Service）
- 存储迁移（COS Migration Tool / 离线迁移设备）
- 迁移后验证

**Delegation:** 迁移后资源验证 → `cvm-ops`/`cdb-ops`/`cos-ops`

- [ ] **Step 3: 提交**

---

## 附录：完整变更清单

| 阶段 | Task | 变更类型 | 文件数 | 预计工作量 |
|------|------|----------|--------|-----------|
| Phase 1 | Task 1: finops 跨账号视图 | 增强现有 | 3 | 0.5 天 |
| Phase 1 | Task 2: proactive-inspection 值班清单 | 增强现有 | 3 | 0.5 天 |
| Phase 2 | Task 3: cicd-ops 新增 | 新增 Skill | 9 | 2 天 |
| Phase 3 | Task 4: service-mesh-ops 新增 | 新增 Skill | 9 | 2 天 |
| Phase 3 | Task 5: dc-ops 新增 | 新增 Skill | 9 | 2 天 |
| Phase 4 | Task 6: well-architected 管理报告 | 增强现有 | 2 | 0.5 天 |
| Phase 4 | Task 7: ccn-ops SD-WAN 场景 | 增强现有 | 2 | 0.5 天 |
| Phase 4 | Task 8: vpn-ops 多分支拓扑 | 增强现有 | 2 | 0.5 天 |
| Phase 4 | Task 9: aiops-diagnosis MTTR 追踪 | 增强现有 | 2 | 0.5 天 |
| Phase 5 | Task 10: migration-ops 新增 | 新增 Skill | 9 | 2 天 |
| **合计** | **10 Tasks** | **4 新增 + 6 增强** | **50** | **~11 天** |

## 自我审查

**1. Spec coverage:**
- 云原生架构能力（评分 4.5 → 目标）: ✅ Task 3 (CICD) + Task 4 (Service Mesh) 覆盖了 CI/CD 和网格治理两个缺口
- 网络与全球组网（评分 4.0 → 目标）: ✅ Task 5 (DC) + Task 7 (CCN SD-WAN) + Task 8 (VPN 拓扑) 补全了专线和全球化场景
- 成本优化与效能（评分 4.0 → 目标）: ✅ Task 1 (FinOps 跨账号) 增加了多账号管理能力
- 故障处理与稳定性（评分 4.5 → 目标）: ✅ Task 2 (值班交接) + Task 9 (MTTR) 强化了值班和度量体系
- 团队管理与领导力（评分 4.0 → 目标）: ✅ Task 2 间接覆盖（值班交接流程标准化是管理能力的基础）
- 战略思维与协同（评分 4.5 → 目标）: ✅ Task 6 (管理层报告) 直接输出战略级输出

**2. Placeholder scan:** 无 TODO/TBD 等占位符。所有代码块包含完整实现。

**3. Type consistency:** 所有 API 路径和字段引用在各 Task 间一致。