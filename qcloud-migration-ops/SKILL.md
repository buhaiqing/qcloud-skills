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
  version: "1.1.0"
  last_updated: "2026-07-09"
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
| ListMigrationProject | List migration projects | Low | None |
| DescribeMigrationTask | Get task details | Low | None |
| ModifyMigrationTaskStatus | Update task status (pause/resume/stop) | Low | Medium |
| Cutover/Switchover | Execute migration cutover (final sync + traffic switch) | High | **High** — production impact |
| Migration Validation | Verify data consistency and application health | Medium | None |
| DeregisterMigrationTask | Remove migration task | Low | **High** — data loss risk |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.1.0 | 2026-07-09 | Scenario enhancement: add ModifyMigrationTaskStatus execution flow (with status transition table), ListMigrationProject flow, Cutover/Switchover Phase 4 flow (pre-cutover checks, final sync, post-cutover monitoring, rollback procedure), Migration Validation Phase 5 flow (data integrity, application smoke tests, validation checklist). Expand Safety Gates and GCL loop coverage. |
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

### Operation: ModifyMigrationTaskStatus

Update migration task status (start, pause, resume, stop, complete). This operation affects
data-in-transit and must be handled with care.

#### Pre-flight (Safety Gate)

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Task exists | `DescribeMigrationTask --TaskId "{{user.task_id}}"` | Task found | `ResourceNotFound` — verify ID |
| Current status | Parse `$.Response.Status` | Known, stable state | Warn if transitioning |
| Target status valid | Validate against allowed transitions | Valid for current state | HALT with transition table |
| User confirmation | Explicit | Task ID + name echoed | HALT without confirmation |

**Valid status transitions:**

| Current Status | Allowed Target | Impact |
|---------------|----------------|--------|
| `READY` | `RUNNING` | Start migration; begins data transfer |
| `RUNNING` | `PAUSED` | Pause transfer; source writes still buffered |
| `RUNNING` | `STOPPED` | **Stop transfer**; abandon in-flight data; target may be inconsistent |
| `RUNNING` | `COMPLETED` | Mark as complete; must verify data integrity first |
| `PAUSED` | `RUNNING` | Resume transfer; continues from checkpoint |
| `PAUSED` | `STOPPED` | **Stop** from paused; no data in-flight (safe) but target may be incomplete |
| — | `DeregisterMigrationTask` | See Deregister operation; only when COMPLETED or STOPPED |

#### Execution — CLI

```bash
tccli msp ModifyMigrationTaskStatus \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TaskId "{{user.task_id}}" \
  --Status "{{user.target_status}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Poll `DescribeMigrationTask` until status transitions; max 30s interval 2s.
2. If transition failed, capture error code and current status.
3. For `STOPPED` → warn: in-flight data abandoned, target may need re-sync.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `OperationDenied.TaskRunning` | Task busy; wait and retry (3x, 30s backoff) |
| `InvalidParameter.StatusTransition` | Invalid transition for current state; HALT and show valid targets |
| `ResourceNotFound.Task` | Verify task ID |
| `RequestLimitExceeded` | Backoff retry (2s,4s,8s) |

### Operation: ListMigrationProject

List all migration projects — the project-level grouping of migration tasks.

#### Execution — CLI

```bash
tccli msp ListMigrationProject \
  --Region "{{env.TENCENTCLOUD_REGION}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Present to User

| Field | Path | Notes |
|-------|------|-------|
| Project ID | `$.Response.ProjectSet[].ProjectId` | Group-level identifier |
| Project name | `$.Response.ProjectSet[].ProjectName` | Display name |
| Task count | `$.Response.ProjectSet[].TaskCount` | Number of tasks in project |
| Status | `$.Response.ProjectSet[].Status` | Project-level status |

### Operation: Cutover/Switchover

Execute migration cutover — the critical Phase 4 step where traffic is switched from
source to target. **This is the highest-risk operation in migration.**

> **Phase 4 flow:** Pre-cutover checks → Stop source writes → Final incremental sync →
> Verify data consistency → Switch traffic → Monitor for N minutes → Rollback or declare success.

#### Pre-flight (Safety Gate — MANDATORY)

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Task status | `DescribeMigrationTask --TaskId "{{user.task_id}}"` | `RUNNING` or `INCREMENTAL_SYNC` | HALT; task must be in active sync |
| Incremental lag | Parse `$.Response.SyncLagSeconds` | < 60s (gate); wait until < 5s during sync loop | Warn if > 300s; extend monitoring window |
| Source health | Source resource accessible and stable | No recent degradation | Warn; proceed with caution |
| Target health | Target resource accessible and functional | Running/healthy | HALT; fix target first |
| Maintenance window | Current time vs planned window | Within window or user confirmed | Warn; schedule outside window |
| Rollback plan | Documented and verified | Rollback steps confirmed | HALT; must have rollback plan |
| User confirmation | **Explicit** with task ID, source, target, expected downtime | All echoed and confirmed | HALT without confirmation |

#### Execution — Cutover Steps

```bash
# Step 1: Stop source writes (application-level — delegate to application owner)
# Step 2: Perform final incremental sync
tccli msp ModifyMigrationTaskStatus \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TaskId "{{user.task_id}}" \
  --Status "CUTOVER_SYNC"   # triggers final sync pass

# Step 3: Wait for sync to complete (poll until lag=0)
for i in $(seq 1 60); do
  LAG=$(tccli msp DescribeMigrationTask --TaskId "{{user.task_id}}" \
    --Region "{{env.TENCENTCLOUD_REGION}}" \
    | jq -r '.Response.SyncLagSeconds')
  [ "$LAG" -lt 5 ] && break
  sleep 5
done

# Step 4: Verify data consistency (see Migration Validation flow)
# Step 5: Switch traffic (DNS, LB, or proxy — delegate to network/application team)
# Step 6: Mark migration complete
tccli msp ModifyMigrationTaskStatus \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TaskId "{{user.task_id}}" \
  --Status "COMPLETED"
```

#### Post-Cutover Monitoring (first 15 minutes)

| Metric | Check | Threshold | On Breach |
|--------|-------|-----------|-----------|
| Application health | Smoke test endpoints | HTTP 200, latency < 2x baseline | **Trigger rollback** |
| Data integrity | Row counts, checksums (see Validation) | Match source pre-cutover snapshot | Investigate; partial rollback |
| Error rate | Application logs | 0 errors above baseline | **Trigger rollback** |
| Target resource | CPU/Memory/Disk utilization | < 80% | Scale up; warn |

#### Rollback Procedure

If cutover fails:
1. Switch traffic back to source (DNS/proxy revert)
2. Set migration task status to `STOPPED`
3. Document failure: timestamp, error pattern, data gap for retry planning
4. Notify stakeholders with rollback confirmation

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| Sync lag > threshold | Wait; extend monitoring window; warn user |
| Data mismatch detected | HALT cutover; investigate; re-sync affected tables |
| Application smoke test fails | **Immediate rollback**; investigate target config/env |
| Target resource crash | **Immediate rollback**; scale up target before retry |

### Operation: Migration Validation

Post-migration data consistency and application health verification (Phase 5).

> **Run after cutover, before declaring migration complete.**

#### Pre-flight

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Source still accessible | Network test | Reachable for comparison | Proceed with target-only checks |
| Snapshot time recorded | Timestamp from cutover | Valid ISO timestamps | Document approximate time |

#### Execution — Data Validation

```bash
# Row count comparison (database migration)
echo "Source row count: $(mysql -h $SRC_HOST -e 'SELECT COUNT(*) FROM db.table')"
echo "Target row count: $(mysql -h $DST_HOST -e 'SELECT COUNT(*) FROM db.table')"

# Checksum comparison for critical tables
echo "Source checksum: $(mysql -h $SRC_HOST -e 'CHECKSUM TABLE db.critical_table')"
echo "Target checksum: $(mysql -h $DST_HOST -e 'CHECKSUM TABLE db.critical_table')"

# Object count (storage migration — source may be AWS S3, Alibaba OSS, etc.)
echo "Source objects: $(aws s3 ls s3://source-bucket --recursive | wc -l)    # adapt per source platform"
echo "Target objects: $(coscli ls cos://{{user.target_bucket}} -r | wc -l)"

# File integrity (sample — adapt source-side CLI per platform)
diff <(aws s3 ls s3://source-bucket --recursive | awk '{print $3,$4}') \
     <(coscli ls cos://{{user.target_bucket}} -r | awk '{print $3,$4}')
```

#### Execution — Application Validation

```bash
# Smoke test endpoints
curl -s -o /dev/null -w "%{http_code}" https://{{user.target_endpoint}}/health

# Business verification queries
curl -s https://{{user.target_endpoint}}/api/verify/migration | jq .

# Performance baseline check
ab -n 100 -c 10 https://{{user.target_endpoint}}/api/baseline
```

#### Validation Checklist

| # | Check | Critical? | Status |
|---|-------|-----------|--------|
| 1 | Row counts match (per table) | Yes | PASS/FAIL |
| 2 | Checksums match (critical tables) | Yes | PASS/FAIL |
| 3 | Object counts match (storage) | Yes | PASS/FAIL |
| 4 | Sample file integrity | Yes | PASS/FAIL |
| 5 | Health endpoint 200 | Yes | PASS/FAIL |
| 6 | Business query returns expected data | Yes | PASS/FAIL |
| 7 | Performance within 2x baseline | No | PASS/FAIL/WARN |
| 8 | SSL/TLS certificate valid | No | PASS/FAIL/WARN |
| 9 | DNS resolved to target | Yes | PASS/FAIL |

#### Post-validation

- All **critical** checks PASS → declare migration successful; deregister task.
- Any **critical** check FAIL → investigate; may require re-sync or rollback.
- Non-critical WARN → document; plan follow-up.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| Row count mismatch | Identify missing rows; incremental sync affected tables |
| Checksum mismatch | Re-sync affected table; re-validate |
| Health endpoint unreachable | Check security groups, target networking |
| Performance degradation | Check target specs, auto-scaling config |

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

### DeregisterMigrationTask

1. Explicit user confirmation with task ID
2. Verification that migration is complete or stopped
3. Pre-warning about metadata loss
4. Post-deregister verification (poll until absent)

### ModifyMigrationTaskStatus (STOPPED target)

1. Explicit user confirmation with task ID + current status + target status echoed
2. Warning: `STOPPED` abandons in-flight data; target may be inconsistent
3. Status transition validated against allowed transitions table

### Cutover/Switchover

1. **MANDATORY** user confirmation with task ID, source/target, and expected downtime window
2. **MANDATORY** rollback plan documented before cutover begins
3. Pre-cutover sync lag verified < 60s
4. Post-cutover monitoring for 15 minutes with defined rollback triggers
5. All critical validation checks PASS before declaring migration complete

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
| `Cutover/Switchover` | Yes (blocking) | Production impact; data consistency critical |
| `DeregisterMigrationTask` | Yes (blocking) | Data loss risk, metadata removal |
| `Migration Validation` | Yes (advisory) | Verification gates; must pass before declaring success |
| `ListMigrationTask` | No | Read-only |
| `ListMigrationProject` | No | Read-only |
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
export TENCENTCLOUD_SECRET_ID="{{env.TENCENTCLOUD_SECRET_ID}}"
export TENCENTCLOUD_SECRET_KEY="{{env.TENCENTCLOUD_SECRET_KEY}}"
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
