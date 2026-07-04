---
name: qcloud-migration-ops
description: >-
  Use when the user needs to plan, execute, or troubleshoot cloud migration
  projects — host migration (CVM online/offline migration), database migration
  (DTS), storage migration (COS Migration Tool), or migration assessment.
  User mentions 迁移上云, 主机迁移, 数据库迁移, DTS, 存储迁移,
  migration to cloud, CVM migration, database transmission. Not for
  application deployment (use `qcloud-cicd-ops`), runtime monitoring
  (use `qcloud-monitor-ops`), or post-migration resource operations
  (use product-specific ops skills).
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
  api_profile: "https://cloud.tencent.com/document/product/659"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli msp help` — CLI exposes RegisterMigrationTask,
    DescribeMigrationTask, ListMigrationTask, ModifyMigrationTaskStatus,
    DeregisterMigrationTask, and related operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
  gcl: required
  gcl_max_iter: 2
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud Migration Operations Skill

## Overview

Tencent Cloud Migration Service Platform (MSP) provides tools and services for migrating workloads to Tencent Cloud, including host migration, database migration, and storage migration.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** `tccli msp` covers migration task operations. You **MUST** ship `references/cli-usage.md` and document **both** the SDK and `tccli` step for every operation.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use with migration triggers; runtime ops → product skills |
| 2 | **Structured I/O** | `{{env.*}}` / `{{user.*}}` / `{{output.*}}` placeholders with MSP API field types |
| 3 | **Explicit Actionable Steps** | Every migration op: Pre-flight → Execute (CLI + SDK) → Validate → Recover |
| 4 | **Complete Failure Strategies** | Error taxonomy with ≥ 10 migration-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | Migration lifecycle only; post-migration → product ops skills |

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Migration validation, rollback planning, data consistency checks | `references/well-architected-assessment.md` |
| **安全性 (Security)** | Data encryption in transit, credential management | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Migration cost estimation, bandwidth optimization | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Parallel migration, incremental sync, scheduling | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "迁移上云" OR "主机迁移" OR "数据库迁移" OR "DTS"
- Task keywords: 存储迁移, migration to cloud, CVM migration, data transmission
- User asks to assess migration readiness or execute migration plan

### SHOULD NOT Use This Skill When

- Task is **application deployment** → delegate to `qcloud-cicd-ops`
- Task is **runtime monitoring** → delegate to `qcloud-monitor-ops`
- Task is **post-migration resource CRUD** → delegate to product ops skills
- Task is **migration target infrastructure setup** → delegate to `qcloud-cvm-ops`, `qcloud-cdb-ops`, etc.

### Delegation Rules

- Pre-migration infrastructure: use `qcloud-cvm-ops`, `qcloud-vpc-ops`, `qcloud-cdb-ops`
- Post-migration validation: use respective product ops skills
- Application deployment: use `qcloud-cicd-ops`
- Monitoring setup: use `qcloud-monitor-ops`

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use documented default only if skill explicitly allows |
| `{{user.task_name}}` | Migration task name | Ask once; reuse |
| `{{user.task_id}}` | Migration task ID | Ask once or derive from `ListMigrationTask` |
| `{{user.source_type}}` | Source platform type | Ask once |
| `{{user.target_type}}` | Target Tencent Cloud product | Ask once |
| `{{output.task_id}}` | From API response | Parse per API spec |
| `{{output.task_status}}` | Migration task status | Parse per API spec |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning:** NEVER expose `TENCENTCLOUD_SECRET_KEY` in output.

## JSON Path Reference

| Path | Maps To |
|------|---------|
| `task.id` | `$.Response.TaskId` |
| `task.name` | `$.Response.TaskName` |
| `task.status` | `$.Response.Status` |
| `task.progress` | `$.Response.Progress` |

## Quick Start

### What This Skill Does
Enables you to plan and execute migration projects — assess readiness, migrate hosts, databases, and storage to Tencent Cloud.

### Prerequisites
- [ ] `tccli` CLI installed
- [ ] Credentials: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region: `TENCENTCLOUD_REGION`
- [ ] Source environment access credentials

### Verify Setup
```bash
tccli msp ListMigrationTask --Region "{{env.TENCENTCLOUD_REGION}}"
```

### Your First Command
```bash
# List migration projects
tccli msp ListMigrationProject --Region "{{env.TENCENTCLOUD_REGION}}"
```

### Next Steps
- [Common Operations](#execution-flows) — Register task, monitor progress
- [Troubleshooting](references/troubleshooting.md) — Fix migration failures

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| RegisterMigrationTask | Register a new migration task | Medium | Low |
| ListMigrationTask | List migration tasks | Low | None |
| DescribeMigrationTask | Get task details | Low | None |
| ModifyMigrationTaskStatus | Update task status | Low | Medium |
| DeregisterMigrationTask | Remove migration task | Low | **High** — data loss risk |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-07-03 | Initial migration skill, dual-path execution. Scope: migration assessment, host migration, database migration, storage migration. Delegates infrastructure setup to product ops skills. |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI and SDK) → Validate → Recover**.

### Operation: Register Migration Task

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Credentials | `test -n "$TENCENTCLOUD_SECRET_ID"` etc. | Non-empty | HALT; user configures env |
| CLI installed | `tccli version` | Exit code 0 | Install tccli |
| Source accessible | Network reachability test | Reachable | HALT; fix network |
| Target ready | Target resource exists | Exists | Create target first |

#### Execution — CLI (`tccli`) (Primary Path)

```bash
tccli msp RegisterMigrationTask \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TaskName "{{user.task_name}}" \
  --TaskType "{{user.task_type}}" \
  --SrcNode "{{user.source_config}}" \
  --DstNode "{{user.target_config}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Capture `{{output.task_id}}` from `$.Response.TaskId`.
2. Poll `DescribeMigrationTask` until task is ready to start.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.TaskNameExists` | Use a different name |
| `InvalidParameterValue.SrcNode` | Check source configuration |
| `ResourceNotFound.TargetResource` | Create target resource first |
| `RequestLimitExceeded` | Backoff retry (2s,4s,8s) |

### Operation: Monitor Migration Progress

#### Execution — CLI

```bash
tccli msp DescribeMigrationTask \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TaskId "{{output.task_id}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

### Operation: List Migration Tasks

#### Execution — CLI

```bash
tccli msp ListMigrationTask \
  --Region "{{env.TENCENTCLOUD_REGION}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

### Operation: Deregister Migration Task

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation with the task ID.
- **MUST** warn: removing task removes migration metadata.
- **MUST** verify migration is complete or stopped.

#### Execution — CLI

```bash
tccli msp DeregisterMigrationTask \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TaskId "{{output.task_id}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

Poll `ListMigrationTask`; expect task absent.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.Task` | Already removed; treat as success |
| `OperationDenied.TaskRunning` | Stop task first |

## Error Code Reference (Migration-Specific)

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter.TaskNameExists` | Task name already exists | Use a different name |
| `InvalidParameterValue.SrcNode` | Source config invalid | Check source configuration |
| `InvalidParameterValue.DstNode` | Target config invalid | Check target configuration |
| `ResourceNotFound.Task` | Task ID not found | Verify task ID |
| `ResourceNotFound.TargetResource` | Target resource not found | Create target first |
| `ResourceQuotaExceeded.Task` | Task quota exceeded | HALT; request quota increase |
| `OperationDenied.TaskRunning` | Task is running | Stop before deregister |
| `OperationDenied.InsufficientPermissions` | Insufficient permissions | HALT; check CAM |
| `InvalidSecretKey` | Credential invalid | HALT; fix credentials |
| `RequestLimitExceeded` | API rate limit | Exponential backoff (3x) |
| `InternalError` | Server error | Retry with RequestId (3x) |

## Safety Gates (Destructive Operations)

Every **DeregisterMigrationTask** MUST have:

1. Explicit user confirmation with task ID
2. Verification that migration is complete or stopped
3. Pre-warning about metadata loss
4. Post-deregister verification (poll until absent)

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** quality gate for all mutation operations.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | frontmatter `gcl: required` |
| max_iterations | **2** | frontmatter `gcl_max_iter: 2` |
| Rubric instance | `references/rubric.md` | 5 dimensions, Migration-specific safety rules |
| Prompt templates | `references/prompt-templates.md` | Generator + Critic + Orchestrator |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | per AGENTS.md §7 |

### When the loop runs

| Operation | Loop required? | Reason |
|---|---|---|
| `RegisterMigrationTask` | Yes | Creates new migration |
| `ModifyMigrationTaskStatus` | Yes (blocking) | Status change may affect data transfer |
| `DeregisterMigrationTask` | Yes (blocking) | Data loss risk, metadata removal |
| `ListMigrationTask` | No | Read-only |
| `DescribeMigrationTask` | No | Read-only |

### Decision flow (first match wins)

1. **Safety=0** → `ABORT` — immediate halt, no output
2. **current_iter >= max_iterations** → `MAX_ITER` — return best result, blocking=true
3. **All thresholds met** → `PASS` — output accepted
4. **Otherwise** → `RETRY` — inject suggestions, increment iter

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
tccli msp ListMigrationTask --Region "{{env.TENCENTCLOUD_REGION}}"
```

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [CLI Usage](references/cli-usage.md)
- [Troubleshooting](references/troubleshooting.md)
- [Well-Architected Assessment](references/well-architected-assessment.md)
- [Integration](references/integration.md)
