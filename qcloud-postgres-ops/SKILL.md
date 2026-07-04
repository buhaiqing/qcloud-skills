---
name: qcloud-postgres-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud PostgreSQL (TencentDB for PostgreSQL / 云数据库 PostgreSQL) — instance
  lifecycle, backup/restore, account management, parameter tuning, slow log 
  analysis, security groups, read-only instances, data migration, and
  performance diagnostics. User mentions PostgreSQL, Postgres, PG, 云数据库
  PostgreSQL, TencentDB PostgreSQL, or describes database connection issues,
  performance degradation, backup failures, or instance
  creation/modification/deletion scenarios even without naming the product
  directly. Not for basic VPC/CAM/billing operations which have their own ops
  skills.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.1.0"
  last_updated: "2026-06-04"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/409 — 2017-03-12"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli postgres help` — actions covering instance lifecycle,
    backup, account, parameter, and security group operations. Python SDK
    fallback for edge cases.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud PostgreSQL Operations Skill

## Overview

TencentDB for PostgreSQL on Tencent Cloud provides fully managed PostgreSQL database services with single-node and multi-node (HA) architectures. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **`tccli` CLI** primary, **Python SDK** fallback), response validation, and failure recovery.

> **UX Compliance:** This skill follows the User Experience Specification. All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI Applicability

- **`cli_applicability: dual-path`:** Official `tccli` supports PostgreSQL. CLI is the **primary** execution path. Python SDK is the **fallback** for edge cases.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 10 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (PostgreSQL), one primary resource (DBInstance); cross-product delegation to other skills |

### Well-Architected Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-AZ deployment, backup/restore, read replicas, RTO/RPO guidelines, data migration | `references/well-architected-assessment.md` |
| **安全性 (Security)** | CAM permissions, SSL/TLS, VPC isolation, security groups, password policies, audit logging | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Prepaid vs postpaid comparison, right-sizing, reserved instances, backup cost management | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Batch operations, parameter templates, CI/CD automation, connection pooling, slow query optimization | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "TencentDB PostgreSQL", "云数据库 PostgreSQL", "PostgreSQL", "Postgres", "PG"
- Task involves CRUD or lifecycle operations on **DBInstance** (create, describe, modify, delete, list)
- Task keywords: postgresql, postgres, pg, 备份, 恢复, 慢查询, 只读实例, SSL, 迁移, 参数
- User asks to deploy, configure, troubleshoot, or monitor PostgreSQL instances **via API, SDK, CLI, or automation**

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: billing skills
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops`
- Task is about self-hosted PostgreSQL (docker, k8s, manual install) → state limitation
- User asks for PostgreSQL SQL help (SELECT, INSERT, EXPLAIN, VACUUM) → this is for cloud ops only
- Task is about VPC / security group design (without referencing PostgreSQL) → delegate to: `qcloud-vpc-ops`
- Task is **architecture design review** / four-pillar Well-Architected assessment → delegate to: `qcloud-well-architected-review`
- Task is about other database products (MySQL, MariaDB, TDSQL) → delegate to their respective skills

### Delegation Rules

- If creating a PostgreSQL instance in a new VPC/subnet, delegate VPC setup to `qcloud-vpc-ops` first
- If configuring CAM policies for PostgreSQL access, delegate to `qcloud-cam-ops`
- If setting up monitoring alarms, delegate to `qcloud-monitor-ops` for alarm policy creation
- Proactive inspection (read-only) → invoked by `qcloud-proactive-inspection`; see `references/proactive-inspection.md`
- Well-Architected assessment (read-only) → invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Read-only Well-Architected assessment for **PostgreSQL (TDSQL-C)**; return `{{output.product_assessment}}`.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | reliability / security / cost / efficiency (or `all`) |
| `{{user.scope}}` | `single-resource` or `account-wide` |

**Allowed:** `Describe*` and `GetMonitorData` only — **no** TerminateDBInstance/DropDB/DDL mutations.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: postgres`).

## Variable Convention

| Placeholder | Source | Meaning | Agent Action |
|-------------|--------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | Environment | Secret ID | NEVER ask user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | Environment | Secret Key | NEVER ask user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | Environment | Region (e.g. ap-guangzhou) | Use from env; ask if override needed |
| `{{user.instance_id}}` | User | PostgreSQL instance ID (postgres-xxxxx) | Ask once; reuse |
| `{{user.instance_name}}` | User | Display name for instance | Ask once |
| `{{user.zone}}` | User | Availability zone (e.g. ap-guangzhou-3) | Ask once; check via DescribeSpecInfo |
| `{{user.password}}` | User | Account password | Ask interactively (8-32 chars, letters+digits+special) |
| `{{user.db_version}}` | User | PostgreSQL engine version (e.g. 14, 15, 16) | Ask once; list available versions |
| `{{user.backup_id}}` | User | Backup ID for restore | Ask once |
| `{{output.instance_id}}` | API Response | New instance ID | Parse from DescribeDBInstances |
| `{{output.deal_id}}` | API Response | Order/deal ID | Parse from CreateDBInstance response |
| `{{output.vip}}` | API Response | Internal IP address | Parse from instance details |
| `{{output.vport}}` | API Response | Port number (default 5432) | Parse from instance details |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose `TENCENTCLOUD_SECRET_KEY`, `SecretKey`, or any credential field value in console output, debug messages, error messages, or logs. Check existence only: `test -n "$TENCENTCLOUD_SECRET_KEY"` ✅.

## API and Response Conventions

- **API version:** `2017-03-12` (canonical for all operations)
- **API spec:** https://cloud.tencent.com/document/api/409
- **Errors:** PostgreSQL uses `Response.Error` pattern with business error codes
- **Timestamps:** ISO 8601 format (e.g. `2026-04-28T10:00:00+08:00`)
- **Async operations:** Use DescribeDBInstanceAttribute to poll instance status

### Response Fields

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| Create | `$.Response.DealNames[0]` | string | Order/deal ID for async tracking |
| Describe | `$.Response.DBInstance.Status` | string | Instance status (running, creating, etc.) |
| List | `$.Response.DBInstanceSet[].DBInstanceId` | array | Instance IDs |
| Modify/Delete | `$.Response.RequestId` | string | Request tracking ID |

### State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| Create | — | running | 5s | 600s |
| Modify spec | running | running | 5s | 600s |
| Isolate | running | isolated | 5s | 120s |
| Delete | isolated | deleted | 5s | 120s |
| Backup | running | running | 10s | 600s |
| Restore | running | running | 10s | 1800s |

Instance status: creating, running, isolated, deleting, deleted

## Quick Start

### Prerequisites
- [ ] `tccli` CLI installed (or Python 3.8+ runtime for SDK fallback)
- [ ] Tencent Cloud credentials configured: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region set: `TENCENTCLOUD_REGION`

### Verify Setup
```bash
tccli postgres DescribeDBInstances --Limit 5
```

### Your First Command
```bash
# List all PostgreSQL instances
tccli postgres DescribeDBInstances --Limit 20
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — Architecture, states, versions
- [Common Operations](#execution-flows) — Create, manage, backup, restore
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Create Instance | Create a new PostgreSQL instance (monthly/hourly) | High | Low |
| Describe Instance | View instance details | Low | None |
| Modify Spec | Scale memory/disk up or down | Medium | Medium |
| Delete Instance | Isolate + delete | Low | **High** — irreversible |
| Backup Instance | Manual or auto backup | Medium | None |
| Restore Instance | Restore from backup | High | **High** — data overwrite |
| Manage Accounts | Create, list, reset password | Low | Medium |
| Manage Parameters | Describe/modify instance parameters | Low | Medium |
| Slow Log Diagnosis | View slow queries | Low | None |
| SSL/TLS | Enable/disable SSL, update cert | Low | Medium |
| Read-only Replicas | Create/describe/delete read-only replicas | Medium | Medium |
| Security Groups | Describe/modify bound security groups | Low | Medium |
| Data Migration | Create/modify/describe migration jobs | High | **High** — data loss |
| Backup Download | Download backup files | Low | None |

## Execution Flows

Every operation: **Pre-flight → Execute (CLI primary, SDK fallback) → Validate → Recover**. Do not skip phases.

### Operation: Create Instance

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI | `tccli version` | Exit code 0 | Install CLI |
| Credentials | Check env vars | Non-empty | HALT; configure env |
| Region | `tccli postgres DescribeDBInstanceAttribute` | Valid region returned | Suggest valid region |
| Spec availability | Query DescribeDBInstances for version | Requested spec on sale | Show available specs |
| Quota/Price | `InquiryPriceCreateDBInstances` | Price returned | HALT; check limits |

#### Execution — CLI (Primary Path)

**Monthly (prepaid):**
```bash
tccli postgres CreateDBInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Zone "{{user.zone}}" \
  --DBVersion "{{user.db_version}}" \
  --DBNodeSet '[{"Role":"Primary","Zone":"{{user.zone}}"},{"Role":"Standby","Zone":"{{user.zone}}"}]' \
  --Memory 4 \
  --Storage 100 \
  --Period 1 \
  --DBInstanceCount 1 \
  --InstanceChargeType "prepaid"
```

**Hourly (postpaid):**
```bash
tccli postgres CreateDBInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Zone "{{user.zone}}" \
  --DBVersion "{{user.db_version}}" \
  --DBNodeSet '[{"Role":"Primary","Zone":"{{user.zone}}"},{"Role":"Standby","Zone":"{{user.zone}}"}]' \
  --Memory 4 \
  --Storage 100 \
  --DBInstanceCount 1 \
  --InstanceChargeType "postpaid"
```

Parameters:
- `DBVersion`: 14, 15, 16 (verify available versions via `tccli postgres DescribeDBVersions`)
- `Memory`/`Storage`: Memory in GB, Storage in GB
- `DBNodeSet`: Primary + Standby nodes; Zone indicates placement
- `DBInstanceCount`: Number of instances to create (default 1)
- `Period`: months (1-12, 24, 36) — for prepaid only
- `InstanceChargeType`: `prepaid` or `postpaid`
- `AutoVoucher`: 1=use vouchers (optional)

#### Execution — Python SDK (Fallback)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Parse `{{output.deal_names}}` from response (`$.Response.DealNames`)
2. Poll DescribeDBInstances until status=running:
```bash
for i in $(seq 1 120); do
  STATUS=$(tccli postgres DescribeDBInstances --Filters '[{"Name":"db-instance-id","Values":["{{user.instance_id}}"]}]' | jq -r '.Response.DBInstanceSet[0].DBInstanceStatus')
  [ "$STATUS" = "running" ] && break
  sleep 5
done
```
3. Report instance ID, VIP, port, version to user

#### Failure Recovery

| Error Code | Description | Recovery |
|------------|-------------|----------|
| InvalidParameterValue.SpecNotOnSale | 购买规格错误 | Use DescribeDBVersions and DescribeProductConfig to list available specs |
| InvalidParameterValue.ZoneClosed | 可用区已关闭售卖 | Choose a different AZ |
| InvalidParameterValue.PostPaidInstanceBeyondLimit | 后付费实例超限 | Delete unused instances or switch to prepaid |
| InvalidParameterValue.PasswordRuleFailed | 密码不符合规范 | Use 8-32 chars with letters, digits, special chars |
| InternalError.TradeError | 交易系统错误 | Retry 3x with 5s backoff; escalate if persistent |
| LimitExceeded.TooManyRequests | 请求太过频繁 | Retry 3x with exponential backoff |
| AuthFailure | CAM签名/鉴权错误 | HALT; check credentials and permissions |

### Operation: Describe Instance

#### Pre-flight Checks
- Instance ID `{{user.instance_id}}` must be known

#### Execution

```bash
tccli postgres DescribeDBInstances \
  --Filters '[{"Name":"db-instance-id","Values":["{{user.instance_id}}"]}]'
```

SDK fallback:
→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Present to User

| Field | JSON Path | Description |
|-------|-----------|-------------|
| DBInstanceId | `$.Response.DBInstanceSet[0].DBInstanceId` | Instance ID |
| DBInstanceName | `$.Response.DBInstanceSet[0].DBInstanceName` | Display name |
| DBInstanceStatus | `$.Response.DBInstanceSet[0].DBInstanceStatus` | running/creating/isolated/deleted |
| DBVersion | `$.Response.DBInstanceSet[0].DBVersion` | Engine version (14, 15, 16) |
| Memory | `$.Response.DBInstanceSet[0].Memory` | Memory in GB |
| Storage | `$.Response.DBInstanceSet[0].Storage` | Storage in GB |
| Zone | `$.Response.DBInstanceSet[0].Zone` | Availability zone |
| Vip | `$.Response.DBInstanceSet[0].Vip` | Internal IP |
| Vport | `$.Response.DBInstanceSet[0].Vport` | Port (default 5432) |
| CreateTime | `$.Response.DBInstanceSet[0].CreateTime` | Creation time |
| NetworkAccess | `$.Response.DBInstanceSet[0].NetworkAccess` | Network information |
| DBNodes | `$.Response.DBInstanceSet[0].DBNodes` | Node information |

### Operation: Modify Instance Spec

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | DescribeDBInstances | Status=running | HALT |
| Current spec | DescribeDBInstances.Memory/Storage | Known current | Cannot compare |
| Price | InquiryPriceUpgrade | Price returned | HALT |

#### Execution

```bash
tccli postgres UpgradeDBInstance \
  --DBInstanceId "{{user.instance_id}}" \
  --Memory 8 \
  --Storage 200
```

SDK fallback:
→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Poll DescribeDBInstances until status=running
2. Verify Memory and Storage fields reflect new values
3. Inform user of updated spec

#### Failure Recovery

| Error Code | Recovery |
|------------|----------|
| InvalidParameterValue.IllegalInstanceStatus | Wait for instance to be in running state |
| LimitExceeded.TooManyRequests | Retry 3x with exponential backoff |
| FailedOperation.OperationNotAllowedInInstanceLocking | Wait for lock release; retry 3x with 30s backoff |

### Operation: Delete Instance (Safety Gate — High Risk)

> **Destructive operation — irreversible after deletion.**

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: "Are you sure you want to delete instance `{{user.instance_name}}` (`{{user.instance_id}}`)? This is irreversible."
- **MUST** remind user to take a backup first
- **MUST** check deletion protection status

#### Execution

**Step 1: Isolate (postpaid)**
```bash
tccli postgres IsolateDBInstance \
  --DBInstanceId "{{user.instance_id}}"
```

**Step 2: Offline delete (after isolation)**
```bash
tccli postgres DeleteDBInstance \
  --DBInstanceId "{{user.instance_id}}"
```

#### Post-execution Validation

1. Poll DescribeDBInstances until status=deleted or 404
2. Confirm to user: "Instance `{{user.instance_name}}` has been permanently deleted."

#### Failure Recovery

| Error Code | Recovery |
|------------|----------|
| InvalidParameterValue.NotFoundInstance | Verify instance ID |
| InvalidParameterValue.IllegalInstanceStatus | Wait for instance to reach running or isolated state |
| FailedOperation.DeletionProtectionEnabled | Disable deletion protection first |

### Operation: Backup Instance

#### Execution — Manual Backup

```bash
tccli postgres CreateBackup \
  --DBInstanceId "{{user.instance_id}}" \
  --BackupType "physical" \
  --BackupName "manual-backup-$(date +%Y%m%d)"
```

BackupType: `physical` (recommended) or `logical`.

#### Check Backup Status

```bash
tccli postgres DescribeDBBackups \
  --DBInstanceId "{{user.instance_id}}" \
  --Limit 5 \
  --Offset 0
```

#### Execution — Manual Backup (SDK Fallback)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Capture `{{output.backup_id}}` from response
2. Poll backup status:
```bash
for i in $(seq 1 60); do
  STATUS=$(tccli postgres DescribeDBBackups --DBInstanceId "{{user.instance_id}}" --Limit 1 | jq -r '.Response.BackupList[0].State')
  [ "$STATUS" = "success" ] && break
  [ "$STATUS" = "failed" ] && echo "Backup failed" && exit 1
  sleep 10
done
```

3. Add timeout guard: if loop exhausts 60 iterations, report "[ERROR] Backup timed out after 600s".

### Operation: Restore Instance

> **Reliability Pillar — Emergency Recovery:** Warn user: restore overwrites current data; suggest pre-restore backup.

#### Pre-flight (Safety Gate)

- **MUST** warn user: restore is destructive to current data
- **MUST** confirm: target instance `{{user.instance_id}}`, backup ID `{{user.backup_id}}`

#### Execution

```bash
# List available backups
tccli postgres DescribeDBBackups --DBInstanceId "{{user.instance_id}}"

# Restore from backup
tccli postgres RestoreDBInstance \
  --DBInstanceId "{{user.instance_id}}" \
  --BackupId "{{user.backup_id}}"
```

#### Post-execution Validation

1. Poll DescribeDBInstances until status=running
2. Verify data access

### Operation: Account Management

#### Create Account

```bash
tccli postgres CreateAccount \
  --DBInstanceId "{{user.instance_id}}" \
  --UserName "{{user.account_name}}" \
  --Password "{{user.password}}" \
  --Type "Normal" \
  --DBName "postgres"
```

Account types: `Normal` (default), `Admin`, `SuperAdmin`.

#### Reset Password

```bash
tccli postgres ResetAccountPassword \
  --DBInstanceId "{{user.instance_id}}" \
  --UserName "{{user.account_name}}" \
  --Password "{{user.new_password}}"
```

#### List Accounts

```bash
tccli postgres DescribeAccounts \
  --DBInstanceId "{{user.instance_id}}"
```

#### Failure Recovery

| Error Code | Recovery |
|------------|----------|
| InvalidParameterValue.PasswordRuleFailed | Use 8-32 chars with letters, digits, and special characters |
| InvalidParameterValue.NotFoundInstance | Verify instance ID |

### Operation: Parameter Management

#### Describe Parameters

```bash
tccli postgres DescribeInstanceParameters \
  --DBInstanceId "{{user.instance_id}}"
```

#### Modify Parameters

```bash
tccli postgres ModifyDBInstanceParameters \
  --DBInstanceId "{{user.instance_id}}" \
  --ParamList '[{"Name":"max_connections","Value":"200"},{"Name":"work_mem","Value":"4096"}]'
```

Common parameters: `max_connections`, `work_mem` (KB), `shared_buffers` (KB), `maintenance_work_mem` (KB), `effective_cache_size` (KB), `log_min_duration_statement` (ms).

### Operation: Slow Log Diagnosis

```bash
# Get slow log list (7-day max range)
tccli postgres DescribeSlowQueryList \
  --DBInstanceId "{{user.instance_id}}" \
  --StartTime "2026-05-24 00:00:00" \
  --EndTime "2026-05-31 00:00:00"

# Get slow log details
tccli postgres DescribeSlowQueryDetail \
  --DBInstanceId "{{user.instance_id}}" \
  --StartTime "2026-05-24 00:00:00" \
  --EndTime "2026-05-31 00:00:00"
```

### Operation: SSL/TLS Management

```bash
# Check SSL status
tccli postgres DescribeDBInstanceSSL \
  --DBInstanceId "{{user.instance_id}}"

# Enable SSL
tccli postgres ModifyDBInstanceSSL \
  --DBInstanceId "{{user.instance_id}}" \
  --SSLEnabled 1

# Disable SSL
tccli postgres ModifyDBInstanceSSL \
  --DBInstanceId "{{user.instance_id}}" \
  --SSLEnabled 0
```

### Operation: Read-only Replicas

#### Create Read-only Replica

```bash
tccli postgres CreateReadOnlyGroup \
  --MasterDBInstanceId "{{user.instance_id}}" \
  --ReadOnlyGroupName "my-ro-group" \
  --MinDelayEliminate 1 \
  --DelayThreshold 10 \
  --ReplayLatencyEliminate 1 \
  --ReadOnlyMaxDelayTime 10
```

### Operation: Security Group Management

```bash
# Describe security group
tccli postgres DescribeDBInstanceSecurityGroups \
  --DBInstanceId "{{user.instance_id}}"

# Modify security group bindings
tccli postgres ModifyDBInstanceSecurityGroups \
  --DBInstanceId "{{user.instance_id}}" \
  --SecurityGroupIds '["sg-xxxxx"]'
```

## Error Code Reference

| Code | Meaning | Recovery |
|------|---------|----------|
| InvalidParameterValue.NotFoundInstance | 未找到实例 | Verify instance ID; suggest DescribeDBInstances |
| InvalidParameterValue.IllegalInstanceStatus | 实例状态不允许操作 | Check status; wait for running state |
| InvalidParameterValue.SpecNotOnSale | 购买规格错误 | Use DescribeProductConfig for available specs |
| InvalidParameterValue.ZoneClosed | 可用区已关闭售卖 | Choose different AZ |
| InvalidParameterValue.PostPaidInstanceBeyondLimit | 后付费实例超限 | Delete unused or switch to prepaid |
| InvalidParameterValue.PasswordRuleFailed | 密码不符合规范 | 8-32 chars, letters + digits + special chars |
| FailedOperation.DeletionProtectionEnabled | 实例开启了销毁保护 | Disable deletion protection first |
| FailedOperation.OperationNotAllowedInInstanceLocking | 实例锁定中 | Retry 3x with 30s backoff |
| InternalError.TradeError | 交易系统错误 | Retry 3x with 5s backoff; escalate with RequestId |
| LimitExceeded.TooManyRequests | 请求太过频繁 | Retry 3x with exponential backoff |
| AuthFailure | CAM鉴权错误 | HALT; check credentials |
| InternalError | 内部错误 | Retry 3x (2s, 4s, 8s); escalate with RequestId |

## Safety Gates (Destructive Operations)

Every **Delete**, **Isolate**, or **irreversible** operation MUST have:

1. **Explicit user confirmation** with resource identifier (`{{user.instance_name}}` / `{{user.instance_id}}`)
2. **Pre-backup reminder** — suggest `CreateBackup` before destructive ops
3. **Deletion protection check** — verify status before delete
4. **Post-delete verification** — poll describe until status=deleted or 404

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate
is a **runtime** scoring layer that audits each PostgreSQL execution against an explicit
rubric, in addition to the build-time **Safety Gates** above and the build-time
**2-round self-review** in [AGENTS.md](../../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

> **Standard PostgreSQL has no UNDROP.** Unlike Oracle Flashback, a `DropDatabase` or
> `REVOKE ALL` is immediately effective — running applications fail on the next query with
> lazy privilege errors that look like transient auth failures.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **2** | per-skill override (matches AGENTS.md §8 default for `qcloud-postgres-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 PostgreSQL-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive: `IsolateDBInstance`, `DeleteDBInstance`, `RestoreDBInstance` (overwrite target), `DropDatabase` (data-plane boundary — HALT if via raw `psql`) | **yes** | Irreversible or recycle-bin window only; needs scoring |
| Sensitive mutating: `ModifyDBInstanceSpec` (storage/memory change), `ResetAccountPassword` / `ModifyAccountPassword`, `ModifyAccountPrivileges` (`REVOKE ALL`) | **yes** | Restart / immediate connection drop / silent privilege loss; needs scoring |
| Mutating: `CreateDBInstances`, `CreateAccount`, `UpgradeDBInstance`, `ModifyDBInstanceName`, `OpenWanService` / `CloseWanService` | **yes** | Cost / security / connectivity risk; needs scoring |
| Read-only: `DescribeDBInstances`, `DescribeAccounts`, `DescribeDBBackups`, `DescribeSlowLogData`, `DescribeErrorLogData` | optional (max_iter=1, no hard abort) | Polling tails are part of the parent op's trace |

### Decision flow (first match wins)

1. **Safety = 0** OR rule violation in `{1, 2, 3, 4, 5}` ⇒ **ABORT** (no partial result)
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

### PostgreSQL-specific safety rules (rubric §4)

Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | `IsolateDBInstance` / `DeleteDBInstance` (any, batch or single) | ID + Name + Status echo + explicit confirmation + retention-window warning + dependency check (re... |
| 2 | `RestoreDBInstance` / restore-from-backup (data plane boundary) | Source `BackupId` named + `DescribeDBBackups` re-confirms; explicit confirmation that the action ... |
| 3 | `UpgradeDBInstance` (downgrade: `Storage`; also any `Memory` change) | Show current spec → target spec; warn that spec changes trigger a restart (30-60s downtime, brief... |
| 4 | `ResetAccountPassword` / `ModifyAccountPassword` (any account, **especially** `postgres` / superuser) | Account name echoed; warn that the password change takes immediate effect; all active connections... |
| 5 | `CreateAccount` (especially with wildcard `Host`) and `ModifyAccountPrivileges` with `REVOKE ALL` | For `CreateAccount`: surface the account name, host pattern (PG API does not always expose `Host`... |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — `ModifyAccountPrivileges` (`REVOKE ALL`) on running connections

| Dimension | Score |
|---|---|
| Correctness | 1 (`ModifyAccountPrivileges` succeeded) |
| **Safety** | **0** (rule 5 violated — no BEFORE/AFTER privilege diff, no running-connection warning) |
| Idempotency | 1 |
| Traceability | 0.5 (API call logged but no `DescribeAccounts` follow-up) |
| Spec Compliance | 0.5 |

`decision: ABORT`. Recovery suggestion: "Re-run with `DescribeAccounts` BEFORE/AFTER; warn that running apps connecting as `app_user` will fail on next query; require explicit confirmation with account name."

See [`references/rubric.md`](references/rubric.md) §6 for two more examples (PASS on `CreateDBInstances` and SAFETY_FAIL on `DeleteDBInstance` reflecting no-UNDROP).

---

## Output Schema

All responses follow Tencent Cloud API structure:

```json
{
  "Response": {
    "RequestId": "abc123",
    "DealNames": ["2026053112345678"],
    "DBInstanceSet": [
      {
        "DBInstanceId": "postgres-6ielucen",
        "DBInstanceName": "my-pg",
        "DBInstanceStatus": "running",
        "DBVersion": "16",
        "Memory": 4,
        "Storage": 100,
        "Zone": "ap-guangzhou-3",
        "Vip": "10.0.0.10",
        "Vport": 5432
      }
    ]
  }
}
```

Error responses:
```json
{
  "Response": {
    "RequestId": "abc123",
    "Error": {
      "Code": "InvalidParameterValue.NotFoundInstance",
      "Message": "未找到实例"
    }
  }
}
```

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-31 | Initial release — PostgreSQL instance lifecycle, backup/restore, accounts, parameters, slow logs, SSL, read-only replicas, security groups |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 PG-specific safety rules incl. instance-isolate/terminate, data-plane drop guard, spec-change restart, root password no-recovery, wildcard host account), `references/prompt-templates.md`. `max_iter=2` per AGENTS.md §8 |

## Reference Directory

- [Core Concepts](references/core-concepts.md) — Architecture, states, versions, limits
- [API & SDK Usage](references/api-sdk-usage.md) — Operation map, Python SDK examples
- [CLI Usage](references/cli-usage.md) — tccli postgres command reference
- [Troubleshooting Guide](references/troubleshooting.md) — Error codes + diagnostic workflows
- [Monitoring & Alerts](references/monitoring.md) — Metrics, alarms, anomaly patterns
- [Integration](references/integration.md) — SDK setup, env vars, cross-skill delegation
- [Well-Architected Assessment](references/well-architected-assessment.md) — 4-pillar assessment
- [AIOps Integration](references/aiops-self-healing.md) — Proactive monitoring, self-healing, capacity forecasting
- [FinOps Optimization](references/finops-cost-optimization.md) — Cost optimization, idle detection, right-sizing

## AIOps Integration (智能运维)

> **AIOps Principle:** Predictive before reactive. Correlate before escalate. Attempt self-heal before alerting human.

→ 完整自愈流程、主动巡检、容量预测、告警风暴处理、可观测性管道：见 [`references/aiops-self-healing.md`](references/aiops-self-healing.md)

## FinOps Optimization (财务优化)

> **FinOps Principle:** Every resource should justify its cost. Idle resources are waste. Right-sizing is a continuous process.

→ 完整闲置检测、成本对比、规格优化、成本报告、异常检测：见 [`references/finops-cost-optimization.md`](references/finops-cost-optimization.md)

### Operational Best Practices (Enhanced)

- **Least privilege:** CAM policies scoped to `postgres:*` on specific instances only
- **Availability:** Use multi-AZ deployment; deploy across 2+ AZs for production
- **Backup:** Enable auto-backup; test restore quarterly; use physical backup
- **AIOps:** Set up proactive health checks (daily); configure self-healing for disk/connections
- **FinOps:** Run idle detection weekly; right-size quarterly; compare costs before every create
- **Capacity:** Forecast disk/connections monthly; expand before hitting 80% threshold
- **Security:** Enable SSL, VPC isolation, strong passwords, and regular patching
- **Maintenance:** Set maintenance window during off-peak hours
- **Cost-aware creation:** Default to `postpaid` for dev/test; `prepaid` for prod with 12+ month commitment
