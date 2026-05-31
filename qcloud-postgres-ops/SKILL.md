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
  version: "1.0.0"
  last_updated: "2026-05-31"
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
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented HTTP steps
- Task is about other database products (MySQL, MariaDB, TDSQL) → delegate to their respective skills

### Delegation Rules

- If creating a PostgreSQL instance in a new VPC/subnet, delegate VPC setup to `qcloud-vpc-ops` first
- If configuring CAM policies for PostgreSQL access, delegate to `qcloud-cam-ops`
- If setting up monitoring alarms, delegate to `qcloud-monitor-ops` for alarm policy creation

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

```python
#!/usr/bin/env python3
import os, json, time
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.postgres.v20170312 import postgres_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = postgres_client.PostgresClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateDBInstancesRequest()
        req.Zone = "ap-guangzhou-3"
        req.DBVersion = "16"
        req.Memory = 4
        req.Storage = 100
        req.DBNodeSet = [{"Role": "Primary", "Zone": "ap-guangzhou-3"}, {"Role": "Standby", "Zone": "ap-guangzhou-3"}]
        req.DBInstanceCount = 1
        req.InstanceChargeType = "postpaid"

        resp = client.CreateDBInstances(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

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
```python
req = models.DescribeDBInstancesRequest()
req.Filters = [{"Name": "db-instance-id", "Values": ["postgres-xxxxx"]}]
resp = client.DescribeDBInstances(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

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
```python
req = models.UpgradeDBInstanceRequest()
req.DBInstanceId = "{{user.instance_id}}"
req.Memory = 8
req.Storage = 200
resp = client.UpgradeDBInstance(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

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

```python
req = models.CreateBackupRequest()
req.DBInstanceId = "{{user.instance_id}}"
req.BackupType = "physical"
req.BackupName = "manual-backup-20260531"
resp = client.CreateBackup(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

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

## Reference Directory

- [Core Concepts](references/core-concepts.md) — Architecture, states, versions, limits
- [API & SDK Usage](references/api-sdk-usage.md) — Operation map, Python SDK examples
- [CLI Usage](references/cli-usage.md) — tccli postgres command reference
- [Troubleshooting Guide](references/troubleshooting.md) — Error codes + diagnostic workflows
- [Monitoring & Alerts](references/monitoring.md) — Metrics, alarms, anomaly patterns
- [Integration](references/integration.md) — SDK setup, env vars, cross-skill delegation
- [Well-Architected Assessment](references/well-architected-assessment.md) — 4-pillar assessment
- [AIOps Integration](#aiops-integration-智能运维) — Proactive monitoring, self-healing, capacity forecasting
- [FinOps Optimization](#finops-optimization-财务优化) — Cost optimization, idle detection, right-sizing

## AIOps Integration (智能运维)

> **AIOps Principle:** Predictive before reactive. Correlate before escalate. Attempt self-heal before alerting human.

### Multi-Metric Anomaly Detection (多指标异常检测)

When a symptom appears, **correlate across metrics** before determining root cause:

| Symptom | Correlate With | Likely Root Cause | Self-Heal Action |
|---------|---------------|-------------------|-------------------|
| CPU ≥ 90% | Slow queries ↑, IOPS ↑ | Missing index, seq scan | Optimize queries or add index |
| CPU ≥ 90% | Connections normal, IOPS normal | Autovacuum running | Wait; tune autovacuum params |
| Memory ≥ 85% | Connections ↑, slow queries | Connection leak, shared_buffers high | Kill idle connections; advise tuning |
| Memory ≥ 85% | Connections stable, QPS normal | Memory leak in application | Restart instance if critical |
| Disk ≥ 85% | WAL size ↑, replication lag | WAL not recycled by standby | Check replication health |
| Disk ≥ 95% | Read-only mode triggered | Storage full | Immediate storage expansion |
| Replication lag ≥ 300s | IOPS ↑ on primary | Heavy write load | Reduce writes or scale up primary |

### Self-Healing Workflows (自愈流程)

**Disk Auto-Diagnose & Recover:**
```bash
#!/bin/bash
# Detected: Disk ≥ 85%. Run this self-healing sequence.
INSTANCE_ID="{{user.instance_id}}"
THRESHOLD=85

DISK_USAGE=$(tccli postgres DescribeDBInstances \
  --Filters "[{\"Name\":\"db-instance-id\",\"Values\":[\"$INSTANCE_ID\"]}]" \
  | jq '.Response.DBInstanceSet[0].Storage')

# Step 1: Clean WAL (if replication is healthy)
REPL_LAG=$(tccli monitor GetMonitorData \
  --Namespace "QCE/POSTGRES" --MetricName "replication_lag" \
  --Period 300 --Instances "[{\"Dimensions\":[{\"Name\":\"DBInstanceId\",\"Value\":\"$INSTANCE_ID\"}]}]" \
  | jq '.Response.DataPoints[0].Values[-1]')

if [ "$REPL_LAG" -lt 300 ]; then
  echo "[HEAL] WAL cleanup: Starting..."
  # Manual vacuum to free space
  tccli postgres ModifyDBInstanceParameters \
    --DBInstanceId "$INSTANCE_ID" \
    --ParamList '[{"Name":"vacuum_cost_delay","Value":"0"}]'
  echo "[HEAL] WAL cleanup: Triggered vacuum_defer_cleanup_age reset"
else
  echo "[WARN] Replication lag > 300s. Cannot clean WAL safely."
fi

# Step 2: If still ≥95%, auto-scale storage
if [ "$DISK_USAGE" -ge 95 ]; then
  CURRENT_STORAGE=$(tccli postgres DescribeDBInstances \
    --Filters "[{\"Name\":\"db-instance-id\",\"Values\":[\"$INSTANCE_ID\"]}]" \
    | jq '.Response.DBInstanceSet[0].Storage')
  NEW_STORAGE=$(( CURRENT_STORAGE * 120 / 100 ))
  echo "[HEAL] Auto-scaling storage from ${CURRENT_STORAGE}GB to ${NEW_STORAGE}GB"
  tccli postgres UpgradeDBInstance \
    --DBInstanceId "$INSTANCE_ID" \
    --Memory $(tccli postgres DescribeDBInstances --Filters "[{\"Name\":\"db-instance-id\",\"Values\":[\"$INSTANCE_ID\"]}]" | jq '.Response.DBInstanceSet[0].Memory') \
    --Storage $NEW_STORAGE
fi
```

**Connection Storm Auto-Recovery:**
```bash
#!/bin/bash
# Detected: Connections ≥ 80%. Kill long-running idle transactions.
INSTANCE_ID="{{user.instance_id}}"

# List idle-in-transaction queries
tccli postgres DescribeSlowQueryList \
  --DBInstanceId "$INSTANCE_ID" \
  --StartTime "$(date -v-1H +'%Y-%m-%d %H:%M:%S')" \
  --EndTime "$(date +'%Y-%m-%d %H:%M:%S')"

# Auto-increase max_connections as temporary relief
echo "[HEAL] Temporarily increasing max_connections..."
tccli postgres ModifyDBInstanceParameters \
  --DBInstanceId "$INSTANCE_ID" \
  --ParamList '[{"Name":"max_connections","Value":"500"}]'
echo "[HEAL] max_connections set to 500. Investigate root cause."
```

### Proactive Health Checks (主动巡检)

Run these checks **before a problem is reported**:

```bash
#!/bin/bash
# pg-health-check.sh — Scheduled (daily/weekly) health check
INSTANCE_ID="{{user.instance_id}}"

echo "=== PostgreSQL Health Check ==="

# 1. Check instance status
STATUS=$(tccli postgres DescribeDBInstances \
  --Filters "[{\"Name\":\"db-instance-id\",\"Values\":[\"$INSTANCE_ID\"]}]" \
  | jq -r '.Response.DBInstanceSet[0].DBInstanceStatus')
echo "[${STATUS}] Instance status: $STATUS"

# 2. Check disk growth rate (7-day trend)
echo "[METRIC] Checking 7-day disk growth..."
tccli monitor GetMonitorData \
  --Namespace "QCE/POSTGRES" --MetricName "disk_usage" \
  --Period 86400 --StartTime "$(date -v-7d +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --Instances "[{\"Dimensions\":[{\"Name\":\"DBInstanceId\",\"Value\":\"$INSTANCE_ID\"}]}]" \
  | jq '.Response.DataPoints[0].Values | {current: .[-1], trend: [.[]]}'

# 3. Check long-running queries
echo "[QUERY] Checking long-running queries..."
tccli postgres DescribeSlowQueryList \
  --DBInstanceId "$INSTANCE_ID" \
  --StartTime "$(date -v-1H +'%Y-%m-%d %H:%M:%S')" \
  --EndTime "$(date +'%Y-%m-%d %H:%M:%S')"

# 4. Check backup freshness
echo "[BACKUP] Last backup check..."
tccli postgres DescribeDBBackups \
  --DBInstanceId "$INSTANCE_ID" --Limit 1 | jq '.Response.BackupList[0] | {State, BackupType, StartTime}'

echo "=== Health Check Complete ==="
```

### Capacity Forecasting (容量预测)

Predict when resources will be exhausted using trend analysis:

```bash
#!/bin/bash
# Capacity forecast: disk, connections, CPU
INSTANCE_ID="{{user.instance_id}}"
# Fetch 14-day metrics to calculate growth rate
METRICS=$(tccli monitor GetMonitorData \
  --Namespace "QCE/POSTGRES" --MetricName "disk_usage" \
  --Period 86400 --StartTime "$(date -v-14d +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --Instances "[{\"Dimensions\":[{\"Name\":\"DBInstanceId\",\"Value\":\"$INSTANCE_ID\"}]}]")

# Calculate daily growth rate (simple linear: last_value - first_value / 14)
FIRST=$(echo "$METRICS" | jq '.Response.DataPoints[0].Values[0]')
LAST=$(echo "$METRICS" | jq '.Response.DataPoints[0].Values[-1]')
CURRENT=$(echo "$METRICS" | jq '.Response.DataPoints[0].Values[-1]')

DAILY_GROWTH=$(echo "scale=2; ($LAST - $FIRST) / 14" | bc)
DAYS_TO_FULL=$(echo "scale=0; (95 - $CURRENT) / $DAILY_GROWTH" | bc 2>/dev/null || echo "N/A")

echo "[CAPACITY] Current disk: ${CURRENT}% | Daily growth: ${DAILY_GROWTH}%/day"
echo "[CAPACITY] Estimated days until 95%: ${DAYS_TO_FULL}"
echo "[ACTION] ${DAYS_TO_FULL} < 30 → Schedule storage expansion within ${DAYS_TO_FULL} days"
```

### Alarm Storm Handling (告警风暴处理)

When multiple instances trigger alerts simultaneously:

1. **Triage by severity:** Instance down → Replication lag → Disk full → High CPU → Memory high
2. **Breadth vs depth:** For 5+ instances with same alarm (e.g., disk full), check if it's a system-wide issue (region/generation) vs independent
3. **Auto-silence known patterns:** If alarm matches a known maintenance window, silence and escalate only after window ends
4. **Correlate before dispatch:** Group alarms from the same application stack before routing to a single on-call engineer

### Observability Pipeline (可观测性管道)

Correlate PostgreSQL **metrics** → **logs** → **traces** for root cause analysis:

```bash
#!/bin/bash
# Ship PostgreSQL slow query logs to CLS (Cloud Log Service)
# Prerequisite: CLS logset and topic created (qcloud-cls-ops)
INSTANCE_ID="{{user.instance_id}}"
CLS_TOPIC_ID="{{user.cls_topic_id}}"

# Export slow queries from PostgreSQL
echo "[OBSERVE] Fetching slow queries for correlation..."
tccli postgres DescribeSlowQueryList \
  --DBInstanceId "$INSTANCE_ID" \
  --StartTime "$(date -v-1H +'%Y-%m-%d %H:%M:%S')" \
  --EndTime "$(date +'%Y-%m-%d %H:%M:%S')" \
  > /tmp/pg_slow_queries.json

# Correlate with Cloud Monitor metrics
METRIC_CPU=$(tccli monitor GetMonitorData \
  --Namespace "QCE/POSTGRES" --MetricName "cpu_usage" \
  --Period 60 --StartTime "$(date -v-1H +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --Instances "[{\"Dimensions\":[{\"Name\":\"DBInstanceId\",\"Value\":\"$INSTANCE_ID\"}]}]")

echo "[OBSERVE] CPU at time of slow queries: $(echo "$METRIC_CPU" | jq '.Response.DataPoints[0].Values[-5:] // []')"
echo "[OBSERVE] Cross-reference: High CPU + slow queries + high IOPS → likely index missing"
echo "[OBSERVE] Action: Add index via CREATE INDEX CONCURRENTLY or enable auto-vacuum tuning"
```

### Error-Proof Script Guards (脚本错误保护)

All self-healing scripts must handle edge cases where API responses are empty:

```bash
# SAFE: Guard against empty API responses
get_metric_safe() {
  local NAMESPACE="$1" METRIC="$2" INSTANCE="$3"
  local RESULT
  RESULT=$(tccli monitor GetMonitorData \
    --Namespace "$NAMESPACE" --MetricName "$METRIC" \
    --Period 300 --StartTime "$(date -v-1d +'%Y-%m-%dT%H:%M:%S+08:00')" \
    --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
    --Instances "[{\"Dimensions\":[{\"Name\":\"DBInstanceId\",\"Value\":\"$INSTANCE\"}]}]" 2>/dev/null)
  
  # Guard: if API returns error or empty, return 0
  echo "$RESULT" | jq '.Response.DataPoints[0].Values[-1] // 0'
}

# Usage: CPU=$(get_metric_safe "QCE/POSTGRES" "cpu_usage" "$INSTANCE_ID")
# Always returns a number (0 if data unavailable)
```

## FinOps Optimization (财务优化)

> **FinOps Principle:** Every resource should justify its cost. Idle resources are waste. Right-sizing is a continuous process.

### Idle Instance Detection (闲置实例检测)

Run this workflow weekly to detect waste:

```bash
#!/bin/bash
# Find idle PostgreSQL instances (CPU < 5% for 7 days)
echo "=== Idle Instance Detection ==="

# List all instances
tccli postgres DescribeDBInstances --Limit 100 \
  | jq -r '.Response.DBInstanceSet[] | select(.DBInstanceStatus == "running") | .DBInstanceId' \
  | while read INSTANCE_ID; do
    AVG_CPU=$(tccli monitor GetMonitorData \
      --Namespace "QCE/POSTGRES" --MetricName "cpu_usage" \
      --Period 86400 --StartTime "$(date -v-7d +'%Y-%m-%dT%H:%M:%S+08:00')" \
      --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
      --Instances "[{\"Dimensions\":[{\"Name\":\"DBInstanceId\",\"Value\":\"$INSTANCE_ID\"}]}]" \
      | jq '.Response.DataPoints[0].Values | add / length')
    
    if [ "${AVG_CPU%.*}" -lt 5 ]; then
      MEM=$(tccli postgres DescribeDBInstances \
        --Filters "[{\"Name\":\"db-instance-id\",\"Values\":[\"$INSTANCE_ID\"]}]" \
        | jq '.Response.DBInstanceSet[0].Memory')
      echo "[IDLE] $INSTANCE_ID (${MEM}GB, avg CPU=${AVG_CPU}%) — consider downsizing or terminating"
    fi
  done
```

**Action Matrix for Idle Instances:**

| Avg CPU | Recommended Action | Monthly Savings (est.) |
|---------|-------------------|----------------------|
| < 5% for 7 days | Downsize to lower spec or terminate | 30-60% |
| < 1% for 30 days | Terminate with final backup | 100% |
| Only accessed during business hours | Switch to postpaid + schedule start/stop | 50-70% |

### Pre-Creation Cost Comparison (创建前成本对比)

Before creating any instance, show user the cost trade-offs:

```bash
#!/bin/bash
# Compare prepaid vs postpaid cost
MEMORY=4
STORAGE=100
PERIOD=12  # months

echo "=== Cost Comparison for ${MEMORY}GB / ${STORAGE}GB PostgreSQL ==="

# Get prepaid price
PREPAID=$(tccli postgres InquiryPriceCreateDBInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --DBVersion "16" --Memory $MEMORY --Storage $STORAGE \
  --DBInstanceCount 1 --Period $PERIOD \
  --InstanceChargeType "prepaid" \
  | jq '.Response.OriginalPrice')

# Get postpaid price per hour
POSTPAID_HOUR=$(tccli postgres InquiryPriceCreateDBInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --DBVersion "16" --Memory $MEMORY --Storage $STORAGE \
  --DBInstanceCount 1 \
  --InstanceChargeType "postpaid" \
  | jq '.Response.OriginalPrice')

MONTHLY_HOURS=$(echo "24 * 30" | bc)
echo "| Model | Cost | Period |"
echo "|-------|------|--------|"
echo "| Prepaid (${PERIOD}mo) | ¥${PREPAID} | ${PERIOD} months |"
echo "| Postpaid (hourly) | ¥${POSTPAID_HOUR}/hour ≈ ¥$(echo "$POSTPAID_HOUR * $MONTHLY_HOURS" | bc)/month | monthly |"
echo ""
echo "→ Recommendation: If workload runs > 60% of time, prepaid is cheaper."
echo "→ If workload is intermittent (< 30%), use postpaid with scheduled stop/start."
```

### Right-Sizing Recommendation (规格优化推荐)

```bash
#!/bin/bash
# Analyze instance utilization and recommend right-sizing
INSTANCE_ID="{{user.instance_id}}"

echo "=== Right-Sizing Analysis ==="

# Get current specs
CURRENT=$(tccli postgres DescribeDBInstances \
  --Filters "[{\"Name\":\"db-instance-id\",\"Values\":[\"$INSTANCE_ID\"]}]" \
  | jq '.Response.DBInstanceSet[0]')
CURRENT_MEM=$(echo "$CURRENT" | jq '.Memory')
CURRENT_STORAGE=$(echo "$CURRENT" | jq '.Storage')

# Get 7-day peak metrics
PEAK_CPU=$(tccli monitor GetMonitorData \
  --Namespace "QCE/POSTGRES" --MetricName "cpu_usage" \
  --Period 3600 --StartTime "$(date -v-7d +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --Instances "[{\"Dimensions\":[{\"Name\":\"DBInstanceId\",\"Value\":\"$INSTANCE_ID\"}]}]" \
  | jq '[.Response.DataPoints[0].Values[] | values] | max')

PEAK_MEM=$(tccli monitor GetMonitorData \
  --Namespace "QCE/POSTGRES" --MetricName "memory_usage" \
  --Period 3600 --Instances "[{\"Dimensions\":[{\"Name\":\"DBInstanceId\",\"Value\":\"$INSTANCE_ID\"}]}]" \
  | jq '[.Response.DataPoints[0].Values[] | values] | max')

echo "| Metric | Current | 7d Peak | Utilization |"
echo "|--------|---------|---------|-------------|"
echo "| Memory | ${CURRENT_MEM}GB | ${PEAK_MEM}% | $(echo "$PEAK_MEM * $CURRENT_MEM / 100" | bc)GB effective |"
echo "| CPU | - | ${PEAK_CPU}% | - |"

if [ "${PEAK_CPU%.*}" -lt 20 ] && [ "${PEAK_MEM%.*}" -lt 30 ]; then
  TARGET_MEM=$(( CURRENT_MEM / 2 ))
  echo "[RIGHT-SIZE] Instance is over-provisioned. Suggest downgrade to ${TARGET_MEM}GB."
  echo "[SAVINGS] Estimated ${CURRENT_MEM}x → ${TARGET_MEM}x cost reduction: ~50%"
elif [ "${PEAK_CPU%.*}" -gt 80 ] || [ "${PEAK_MEM%.*}" -gt 85 ]; then
  TARGET_MEM=$(( CURRENT_MEM * 2 ))
  echo "[RIGHT-SIZE] Instance is under-provisioned. Suggest upgrade to ${TARGET_MEM}GB."
fi
```

### Cost Reporting (成本报告)

```bash
#!/bin/bash
# Generate monthly cost report for all PostgreSQL instances
echo "=== PostgreSQL Monthly Cost Report ==="
tccli postgres DescribeDBInstances --Limit 100 \
  | jq -r '.Response.DBInstanceSet[] | "\(.DBInstanceId) | \(.Memory)GB | \(.Storage)GB | \(.DBInstanceStatus) | \(.CreateTime)"' \
  | while IFS='|' read -r ID MEM STORAGE STATUS CREATE; do
    CHARGE_TYPE="postpaid"  # or check via API
    if [ "$STATUS" = "isolated" ]; then
      echo "| ${ID} | ${MEM}/${STORAGE} | ${STATUS} | ⚠️ Billing stopped | Should delete? |"
    else
      echo "| ${ID} | ${MEM}/${STORAGE} | ${STATUS} | active | Monitor utilization |"
    fi
  done
```

### Cost Anomaly Detection (成本异常检测)

Detect unexpected cost spikes or lingering cost from isolated instances:

```bash
#!/bin/bash
echo "=== Cost Anomaly Detection ==="
tccli postgres DescribeDBInstances --Limit 100 \
  | jq -r '.Response.DBInstanceSet[] | "\(.DBInstanceId)|\(.DBInstanceStatus)|\(.Memory)|\(.Storage)"' \
  | while IFS='|' read -r ID STATUS MEM STORAGE; do
    # Flag: isolated instances still cost for reserved storage
    if [ "$STATUS" = "isolated" ]; then
      echo "[ANOMALY] $ID — ISOLATED but reserved ${MEM}GB/${STORAGE}GB. Monthly cost continues until deleted."
      echo "  Action: tccli postgres DeleteDBInstance --DBInstanceId \"$ID\""
    fi
    
    # Flag: new instances created this month (check CreateTime)
    CREATED=$(tccli postgres DescribeDBInstances \
      --Filters "[{\"Name\":\"db-instance-id\",\"Values\":[\"$ID\"]}]" \
      | jq -r '.Response.DBInstanceSet[0].CreateTime // ""')
    if [ -n "$CREATED" ] && [ "$(echo "$CREATED" | cut -c1-7)" = "$(date +'%Y-%m')" ]; then
      echo "[INFO] $ID — created this month ($CREATED). Track new cost."
    fi
  done
```

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
