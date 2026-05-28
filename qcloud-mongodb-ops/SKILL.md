---
name: qcloud-mongodb-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud MongoDB (TencentDB for MongoDB / 云数据库 MongoDB) — instance lifecycle,
  backup/restore, account management, parameter tuning, slow log analysis, audit
  configuration, SSL/TLS, security groups, and performance diagnostics. User
  mentions MongoDB, Mongo, 云数据库 MongoDB, TencentDB MongoDB, or describes
  database connection issues, performance degradation, backup failures, or
  instance creation/modification/deletion scenarios even without naming the
  product directly. Not for basic VPC/CAM/billing operations which have their
  own ops skills.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python-mongodb),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "2026-05-29"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/240 — 2019-07-25"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli mongodb help` — 79 available actions for version
    2019-07-25, covering all major instance, backup, account, audit, and
    parameter operations. Python SDK fallback for edge cases.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud MongoDB Operations Skill

## Overview

TencentDB for MongoDB on Tencent Cloud provides fully managed MongoDB database services with replica set and sharded cluster architectures. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **`tccli` CLI** primary, **Python SDK** fallback), response validation, and failure recovery.

> **UX Compliance:** This skill follows the User Experience Specification. All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI Applicability

- **`cli_applicability: dual-path`:** Official `tccli` supports MongoDB with 79 actions for API version 2019-07-25. CLI is the **primary** execution path. Python SDK is the **fallback** for edge cases.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 10 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (MongoDB), one primary resource (DBInstance); cross-product delegation to other skills |

### Well-Architected Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-AZ deployment, backup/restore, DR instances, RTO/RPO guidelines | `references/well-architected-assessment.md` |
| **安全性 (Security)** | CAM permissions, SSL/TLS, transparent data encryption, audit logging, security groups, VPC isolation, password policies | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Prepaid vs postpaid comparison, right-sizing, reserved instances, backup cost management | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Batch operations, parameter templates, CI/CD automation, connection pooling, slow query optimization | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "TencentDB MongoDB", "云数据库 MongoDB", "MongoDB", "Mongo"
- Task involves CRUD or lifecycle operations on **DBInstance** (create, describe, modify, delete, list)
- Task keywords: mongodb, mongo, 副本集, 分片集群, 备份, 慢查询, 审计, SSL
- User asks to deploy, configure, troubleshoot, or monitor MongoDB instances **via API, SDK, CLI, or automation**

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: billing skills
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops`
- Task is about self-hosted MongoDB (docker, k8s, manual install) → state limitation
- User asks for MongoDB CRUD query help (insert, find, update, aggregate) → this is for cloud ops only
- Task is about VPC / security group design (without referencing MongoDB) → delegate to: `qcloud-vpc-ops`
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented HTTP steps

### Delegation Rules

- If creating a MongoDB instance in a new VPC/subnet, delegate VPC setup to `qcloud-vpc-ops` first
- If configuring CAM policies for MongoDB access, delegate to `qcloud-cam-ops`
- If setting up monitoring alarms, delegate to `qcloud-monitor-ops` for alarm policy creation

## Variable Convention

| Placeholder | Source | Meaning | Agent Action |
|-------------|--------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | Environment | Secret ID | NEVER ask user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | Environment | Secret Key | NEVER ask user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | Environment | Region (e.g. ap-guangzhou) | Use from env; ask if override needed |
| `{{user.instance_id}}` | User | MongoDB instance ID (cmgo-xxxxx) | Ask once; reuse |
| `{{user.instance_name}}` | User | Display name for instance | Ask once |
| `{{user.zone}}` | User | Availability zone (e.g. ap-guangzhou-3) | Ask once; check via DescribeSpecInfo |
| `{{user.password}}` | User | Account password | Ask interactively (8-32 chars, letters+digits+special) |
| `{{user.account_name}}` | User | MongoDB account username | Ask once |
| `{{output.instance_id}}` | API Response | New instance ID | Parse from DescribeDBInstances |
| `{{output.deal_id}}` | API Response | Order/deal ID | Parse from CreateDBInstance response |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose `TENCENTCLOUD_SECRET_KEY`, `SecretKey`, or any credential field value in console output, debug messages, error messages, or logs. Check existence only: `test -n "$TENCENTCLOUD_SECRET_KEY"` ✅.

## API and Response Conventions

- **API version:** `2019-07-25` (canonical for all operations)
- **API spec:** https://cloud.tencent.com/document/api/240
- **Errors:** MongoDB uses `Response.Error` pattern with business error codes
- **Timestamps:** ISO 8601 format (e.g. `2026-04-28T10:00:00+08:00`)
- **Async operations:** Use `DescribeAsyncRequestInfo` with DealId, polling every 5s

### Response Fields

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| Create | `$.Response.DealId` | string | Order/deal ID for async tracking |
| Describe | `$.Response.InstanceDetails[0].Status` | integer | Instance status code |
| List | `$.Response.InstanceDetails[].InstanceId` | array | Instance IDs |
| Modify/Delete | `$.Response.RequestId` | string | Request tracking ID |

### State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| Create | — | 2 (running) | 5s | 600s |
| Modify spec | 2 (running) | 2 (running) | 5s | 600s |
| Isolate | 2 (running) | 3 (isolated) | 5s | 120s |
| Offline delete | 3 (isolated) | -2 (deleted) | 5s | 120s |
| Backup | 2 (running) | 2 (running) | 10s | 600s |

Instance status codes: 0=creating, 1=in progress, 2=running, 3=isolated, -2=deleted

## Quick Start

### Prerequisites
- [ ] `tccli` CLI installed (or Python 3.8+ runtime for SDK fallback)
- [ ] Tencent Cloud credentials configured: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region set: `TENCENTCLOUD_REGION`

### Verify Setup
```bash
tccli mongodb DescribeSpecInfo --version 2019-07-25
```

### Your First Command
```bash
# List all MongoDB instances
tccli mongodb DescribeDBInstances --Limit 20
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — Architecture, states, versions
- [Common Operations](#execution-flows) — Create, manage, backup, restore
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Create Instance | Create a new MongoDB instance (monthly/hourly) | High | Low |
| Describe Instance | View instance details | Low | None |
| Modify Spec | Scale memory/disk up or down | Medium | Medium |
| Delete Instance | Isolate + offline delete | Low | **High** — irreversible |
| Backup Instance | Manual or auto backup | Medium | None |
| Restore Instance | Restore from backup | High | **High** — data overwrite |
| Manage Accounts | Create, list, set privileges, reset password | Low | Medium |
| Manage Parameters | Describe/modify instance parameters | Low | Medium |
| Slow Log Diagnosis | View slow queries and patterns | Low | None |
| SSL/TLS | Enable/disable SSL, check status | Low | Medium |
| Audit Service | Open/close audit, query audit logs | Medium | Low |
| Security Groups | Describe/modify bound security groups | Low | Medium |

## Execution Flows

Every operation: **Pre-flight → Execute (CLI primary, SDK fallback) → Validate → Recover**. Do not skip phases.

### Operation: Create Instance

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI | `tccli version` | Exit code 0 | Install CLI |
| Credentials | Check env vars | Non-empty | HALT; configure env |
| Region | `tccli mongodb DescribeSpecInfo` | Valid region returned | Suggest valid region |
| Spec availability | Query DescribeSpecInfo for zone | Requested spec on sale | Show available specs |
| Quota/Price | `InquirePriceCreateDBInstances` | Price returned | HALT; check limits |

#### Execution — CLI (Primary Path)

**Monthly (prepaid):**
```bash
tccli mongodb CreateDBInstance \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Zone "{{user.zone}}" \
  --NodeNum 3 \
  --Memory 4 \
  --Volume 10 \
  --MongoVersion "MONGO_60_WT" \
  --MachineCode "HCD" \
  --GoodsNum 1 \
  --ClusterType 0 \
  --Period 1
```

**Hourly (postpaid):**
```bash
tccli mongodb CreateDBInstanceHour \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Zone "{{user.zone}}" \
  --NodeNum 3 \
  --Memory 4 \
  --Volume 10 \
  --MongoVersion "MONGO_60_WT" \
  --MachineCode "HCD" \
  --GoodsNum 1 \
  --ClusterType 0
```

Parameters:
- `NodeNum`: 3 for replica set (primary+secondary+secondary), 3+ per shard for sharded
- `Memory`/`Volume`: Memory in GB, Volume in GB. Disk must be ≥ 1.2× used disk on modify.
- `MongoVersion`: MONGO_42_WT, MONGO_50_WT, MONGO_60_WT, MONGO_70_WT, MONGO_80_WT
- `MachineCode`: HIO10G (High IO), HCD (Cloud Disk)
- `ClusterType`: 0=replica set, 1=sharded cluster
- `Period`: months (1-12, 24, 36) — for prepaid only

#### Execution — Python SDK (Fallback)

```python
#!/usr/bin/env python3
import os, json, time
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.mongodb.v20190725 import mongodb_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = mongodb_client.MongodbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateDBInstanceHourRequest()
        req.Zone = "ap-guangzhou-3"
        req.NodeNum = 3
        req.Memory = 4
        req.Volume = 10
        req.MongoVersion = "MONGO_60_WT"
        req.MachineCode = "HCD"
        req.GoodsNum = 1
        req.ClusterType = 0

        resp = client.CreateDBInstanceHour(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

#### Post-execution Validation

1. Parse `{{output.deal_id}}` from response (when present)
2. Track async operation:
```bash
for i in $(seq 1 120); do
  STATUS=$(tccli mongodb DescribeAsyncRequestInfo --DealId "{{output.deal_id}}" | jq -r '.Response.Status')
  [ "$STATUS" = "success" ] && break
  [ "$STATUS" = "error" ] && echo "Async task failed" && exit 1
  sleep 5
done
```
3. Call `DescribeDBInstances` to get `{{output.instance_id}}` and verify status=2 (running)
4. Report instance ID, name, VIP, port to user

#### Failure Recovery

| Error Code | Description | Recovery |
|------------|-------------|----------|
| InvalidParameterValue.SpecNotOnSale | 购买规格错误 | Use DescribeSpecInfo to list available specs |
| InvalidParameterValue.ZoneClosed | 可用区已关闭售卖 | Choose a different AZ |
| InvalidParameterValue.PostPaidInstanceBeyondLimit | 后付费实例超限 | Delete unused instances or switch to prepaid |
| InvalidParameterValue.PasswordRuleFailed | 密码不符合规范 | Use 8-32 chars with letters, digits, special chars |
| InternalError.TradeError | 交易系统错误 | Retry 3x with 5s backoff; escalate if persistent |
| LimitExceeded.TooManyRequests | 请求太过频繁 | Retry 3x with exponential backoff |
| AuthFailure | CAM签名/鉴权错误 | HALT; check credentials and permissions |

### Operation: Describe Instance

#### Execution

```bash
tccli mongodb DescribeDBInstances \
  --InstanceIds '["{{user.instance_id}}"]'
```

SDK fallback:
```python
req = models.DescribeDBInstancesRequest()
req.InstanceIds = ["cmgo-xxxxx"]
resp = client.DescribeDBInstances(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Present to User

| Field | JSON Path | Description |
|-------|-----------|-------------|
| InstanceId | `$.Response.InstanceDetails[0].InstanceId` | Instance ID |
| InstanceName | `$.Response.InstanceDetails[0].InstanceName` | Display name |
| Status | `$.Response.InstanceDetails[0].Status` | 0=creating, 1=in progress, 2=running, 3=isolated, -2=deleted |
| MongoVersion | `$.Response.InstanceDetails[0].MongoVersion` | Engine version |
| Memory | `$.Response.InstanceDetails[0].Memory` | Memory in MB |
| Volume | `$.Response.InstanceDetails[0].Volume` | Disk in MB |
| Zone | `$.Response.InstanceDetails[0].Zone` | Availability zone |
| Vip | `$.Response.InstanceDetails[0].Vip` | Internal IP |
| Vport | `$.Response.InstanceDetails[0].Vport` | Port |
| ClusterType | `$.Response.InstanceDetails[0].ClusterType` | 0=replica set, 1=sharded |
| CreateTime | `$.Response.InstanceDetails[0].CreateTime` | Creation time |

### Operation: Modify Instance Spec

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | DescribeDBInstances | Status=2 (running) | HALT |
| Current spec | DescribeDBInstances.Memory/Volume | Known current | Cannot compare |
| New spec > current | Compare values | Memory and Volume both change | ModifyModeError |
| Price | InquirePriceModifyDBInstanceSpec | Price returned | HALT |

#### Execution

```bash
tccli mongodb ModifyDBInstanceSpec \
  --InstanceId "{{user.instance_id}}" \
  --Memory 8 \
  --Volume 20
```

> Note: Memory and Volume must both increase or both decrease (ModifyModeError otherwise).

#### Execution — Python SDK (Fallback)

```python
req = models.ModifyDBInstanceSpecRequest()
req.InstanceId = "{{user.instance_id}}"
req.Memory = 8
req.Volume = 20
resp = client.ModifyDBInstanceSpec(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

1. Poll DescribeDBInstances until status=2 (running) — may take several minutes
2. Verify Memory and Volume fields reflect new values
3. Inform user of new connection info (VIP/port unchanged)

#### Failure Recovery

| Error Code | Recovery |
|------------|----------|
| InvalidParameterValue.ModifyModeError | Memory and disk must scale together |
| InvalidParameterValue.SetDiskLessThanUsed | Set disk ≥ 1.2× current used disk |
| InvalidParameterValue.IllegalInstanceStatus | Wait for instance to be in running state |
| FailedOperation.OperationNotAllowedInInstanceLocking | Wait for lock release; retry 3x with 30s backoff |

### Operation: Delete Instance (Safety Gate — High Risk)

> **Destructive operation — irreversible after offline step.**

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: "Are you sure you want to delete instance `{{user.instance_name}}` (`{{user.instance_id}}`)? This is irreversible."
- **MUST** remind user to take a backup first: `tccli mongodb CreateBackupDBInstance --InstanceId "{{user.instance_id}}"`
- **MUST** check deletion protection: `tccli mongodb DescribeDBInstances --InstanceIds '["{{user.instance_id}}"]' | jq '.Response.InstanceDetails[0].AutoRenewFlag'`
- If `FailedOperation.DeletionProtectionEnabled`, disable first via `SetDBInstanceDeletionProtection`
- Prepaid instances use `TerminateDBInstances` instead of Isolate

#### Execution

**Step 1: Isolate (postpaid)**
```bash
tccli mongodb IsolateDBInstance --InstanceId "{{user.instance_id}}"
```

**Step 1 (alternative): Terminate (prepaid)**
```bash
tccli mongodb TerminateDBInstances --InstanceId "{{user.instance_id}}"
```

**Step 2: Offline (after isolation, within recovery window)**
```bash
tccli mongodb OfflineIsolatedDBInstance --InstanceId "{{user.instance_id}}"
```

#### Post-execution Validation

1. Poll DescribeDBInstances until status=-2 (deleted) or 404
2. Confirm to user: "Instance `{{user.instance_name}}` has been permanently deleted."

#### Failure Recovery

| Error Code | Recovery |
|------------|----------|
| FailedOperation.DeletionProtectionEnabled | Disable deletion protection via SetDBInstanceDeletionProtection first |
| InvalidParameterValue.PrePaidInstanceUnableToIsolate | Use TerminateDBInstances instead |
| InvalidParameterValue.IllegalInstanceStatus | Wait for instance to reach running or isolated state |

### Operation: Backup Instance

#### Execution — Manual Backup

```bash
# Create backup
tccli mongodb CreateBackupDBInstance --InstanceId "{{user.instance_id}}"

# Check backup status
tccli mongodb DescribeDBBackups --InstanceId "{{user.instance_id}}" --Limit 5
```

#### Execution — Manual Backup (SDK Fallback)

```python
req = models.CreateBackupDBInstanceRequest()
req.InstanceId = "{{user.instance_id}}"
resp = client.CreateBackupDBInstance(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Execution — Set Auto Backup Rules

```bash
tccli mongodb SetBackupRules \
  --InstanceId "{{user.instance_id}}" \
  --BackupType 0 \
  --BackupTime "01:00-02:00" \
  --BackupRetentionPeriod 7
```

Parameters: `BackupType` 0=auto, 1=manual; `BackupTime` in 1-hour window; `BackupRetentionPeriod` in days.

#### Post-execution Validation

1. Capture `{{output.backup_id}}` from `CreateBackupDBInstance` response (when returned)
2. Poll backup status using the specific backup ID (or most recent backup):

```bash
for i in $(seq 1 60); do
  STATUS=$(tccli mongodb DescribeDBBackups --InstanceId "{{user.instance_id}}" --Limit 1 | jq -r '.Response.BackupList[0].Status')
  [ "$STATUS" = "2" ] && break
  [ "$STATUS" = "1" ] || { echo "Backup failed (status=$STATUS)"; exit 1; }
  sleep 10
done
```

Backup status: 1=in progress, 2=success. `--Limit 1` returns the most recent backup.

3. Add timeout guard: if loop exhausts 60 iterations, report "[ERROR] Backup timed out after 600s".

#### Failure Recovery

| Error Code | Recovery |
|------------|----------|
| FailedOperation.TransparentDataEncryptionAlreadyOpen | TDE instances only support logical backup |
| InvalidParameterValue.IllegalInstanceStatus | Wait for instance to be running |

### Operation: Restore Instance

> **Reliability Pillar — Emergency Recovery:** Warn user: restore overwrites current data; suggest pre-restore backup.

#### Pre-flight (Safety Gate)

- **MUST** warn user: restore is destructive to current data
- **MUST** confirm: target instance `{{user.instance_id}}`, backup ID `{{user.backup_id}}`

#### Execution

```bash
# List available backups
tccli mongodb DescribeDBBackups --InstanceId "{{user.instance_id}}"

# Restore from backup
tccli mongodb RestoreDBInstance \
  --InstanceId "{{user.instance_id}}" \
  --BackupId 12345
```

#### Post-execution Validation

1. Poll DescribeDBInstances until status=2 (running)
2. Verify data access: connect and check key collections

### Operation: Account Management

#### Create Account

```bash
tccli mongodb CreateAccountUser \
  --InstanceId "{{user.instance_id}}" \
  --UserName "{{user.account_name}}" \
  --Password "{{user.password}}" \
  --AuthRole '[{"Mask":1,"NameSpace":"admin"}]'
```

Permission mask: 0=none, 1=read-only, 3=read-write.

#### List Accounts

```bash
tccli mongodb DescribeAccountUsers --InstanceId "{{user.instance_id}}"
```

#### Set Account Privilege

```bash
tccli mongodb SetAccountUserPrivilege \
  --InstanceId "{{user.instance_id}}" \
  --UserName "{{user.account_name}}" \
  --AuthRole '[{"Mask":3,"NameSpace":"testdb"}]'
```

#### Reset Password

```bash
tccli mongodb ResetDBInstancePassword \
  --InstanceId "{{user.instance_id}}" \
  --UserName "{{user.account_name}}" \
  --Password "{{user.new_password}}"
```

#### Failure Recovery

| Error Code | Recovery |
|------------|----------|
| InvalidParameterValue.PasswordRuleFailed | Use 8-32 chars with letters, digits, and special characters |
| InvalidParameterValue.NotFoundInstance | Verify instance ID |

### Operation: Parameter Management

#### Describe Parameters

```bash
tccli mongodb DescribeInstanceParams --InstanceId "{{user.instance_id}}"
```

#### Modify Parameters

```bash
tccli mongodb ModifyInstanceParams \
  --InstanceId "{{user.instance_id}}" \
  --InstanceParams '[{"Key":"net.messageMaxBytes","Value":"16777216"}]'
```

Common parameters: `net.messageMaxBytes`, `operationProfiling.slowOpThresholdMs` (slowMS), `net.maxIncomingConnections` (maxConns).

### Operation: Slow Log Diagnosis

```bash
# Get slow log count/statistics (7-day max range)
tccli mongodb DescribeSlowLogs \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "2026-05-22 00:00:00" \
  --EndTime "2026-05-29 00:00:00" \
  --SlowMS 100

# Get slow log patterns (aggregated by query hash)
tccli mongodb DescribeSlowLogPatterns \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "2026-05-22 00:00:00" \
  --EndTime "2026-05-29 00:00:00" \
  --SlowMS 100

# Get detailed slow logs (individual query details)
tccli mongodb DescribeDetailedSlowLogs \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "2026-05-22 00:00:00" \
  --EndTime "2026-05-29 00:00:00" \
  --SlowMS 100
```

### Operation: SSL/TLS Management

```bash
# Check SSL status
tccli mongodb DescribeInstanceSSL --InstanceId "{{user.instance_id}}"

# Enable/disable SSL
tccli mongodb InstanceEnableSSL \
  --InstanceId "{{user.instance_id}}" \
  --SslSwitch "on"  # or "off"
```

### Operation: Audit Service Management

```bash
# Check audit config
tccli mongodb DescribeAuditConfig --InstanceId "{{user.instance_id}}"

# Open audit service (30-day retention)
tccli mongodb OpenAuditService \
  --InstanceId "{{user.instance_id}}" \
  --LogExpireDay 30

# Modify audit retention
tccli mongodb ModifyAuditService \
  --InstanceId "{{user.instance_id}}" \
  --LogExpireDay 60

# Query audit logs
tccli mongodb DescribeAuditLogs \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "2026-05-22 00:00:00" \
  --EndTime "2026-05-29 00:00:00"

# Close audit service
tccli mongodb CloseAuditService --InstanceId "{{user.instance_id}}"
```

### Operation: Security Group Management

```bash
# Describe security group
tccli mongodb DescribeSecurityGroup --InstanceId "{{user.instance_id}}"

# Modify security group bindings
tccli mongodb ModifyDBInstanceSecurityGroup \
  --InstanceId "{{user.instance_id}}" \
  --SecurityGroupIds '["sg-xxxxx"]'
```

## Error Code Reference

| Code | Meaning | Recovery |
|------|---------|----------|
| InvalidParameterValue.NotFoundInstance | 未找到实例 | Verify instance ID; suggest DescribeDBInstances |
| InvalidParameterValue.IllegalInstanceStatus | 实例状态不允许操作 | Check status; wait for running state |
| InvalidParameterValue.ModifyModeError | 内存和磁盘必须同时升配或降配 | Adjust both Memory and Volume |
| InvalidParameterValue.PasswordRuleFailed | 密码不符合规范 | 8-32 chars, letters + digits + special chars |
| InvalidParameterValue.SpecNotOnSale | 购买规格错误 | Use DescribeSpecInfo for available specs |
| InvalidParameterValue.ZoneClosed | 可用区已关闭售卖 | Choose different AZ |
| InvalidParameterValue.PostPaidInstanceBeyondLimit | 后付费实例超限 | Delete unused or switch to prepaid |
| InvalidParameterValue.SetDiskLessThanUsed | 磁盘不得低于已用1.2倍 | Increase disk size |
| FailedOperation.DeletionProtectionEnabled | 实例开启了销毁保护 | Disable via SetDBInstanceDeletionProtection |
| FailedOperation.OperationNotAllowedInInstanceLocking | 实例锁定中 | Retry 3x with 30s backoff |
| InternalError.TradeError | 交易系统错误 | Retry 3x with 5s backoff; escalate with RequestId |
| LimitExceeded.TooManyRequests | 请求太过频繁 | Retry 3x with exponential backoff |
| UnsupportedOperation.VersionNotSupport | 版本不支持该操作 | Upgrade instance version |
| InternalError | 内部错误 | Retry 3x (2s, 4s, 8s); escalate with RequestId |
| AuthFailure | CAM鉴权错误 | HALT; check credentials |

## Safety Gates (Destructive Operations)

Every **Delete**, **Terminate**, **Isolate**, **Offline**, or **irreversible** operation MUST have:

1. **Explicit user confirmation** with resource identifier (`{{user.instance_name}}` / `{{user.instance_id}}`)
2. **Pre-backup reminder** — suggest `CreateBackupDBInstance` before destructive ops
3. **Dependency check** — warn if instance has active connections (via `DescribeClientConnections`)
4. **Deletion protection check** — verify via `SetDBInstanceDeletionProtection` status
5. **Post-delete verification** — poll describe until status=-2 or 404

## Output Schema

All responses follow Tencent Cloud API structure:

```json
{
  "Response": {
    "RequestId": "abc123",
    "DealId": "12345678",
    "InstanceDetails": [
      {
        "InstanceId": "cmgo-6ielucen",
        "InstanceName": "my-mongo",
        "Status": 2,
        "MongoVersion": "MONGO_60_WT",
        "Memory": 4096,
        "Volume": 10240,
        "Zone": "ap-guangzhou-3",
        "Vip": "10.0.0.10",
        "Vport": 27017,
        "ClusterType": 0
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
| 1.0.0 | 2026-05-29 | Initial release — MongoDB instance lifecycle, backup/restore, accounts, parameters, slow logs, SSL, audit, security groups |

## Reference Directory

- [Core Concepts](references/core-concepts.md) — Architecture, states, versions, limits
- [API & SDK Usage](references/api-sdk-usage.md) — Operation map, Python SDK examples
- [CLI Usage](references/cli-usage.md) — tccli mongodb command reference
- [Troubleshooting Guide](references/troubleshooting.md) — Error codes + diagnostic workflows
- [Monitoring & Alerts](references/monitoring.md) — Metrics, alarms, anomaly patterns
- [Integration](references/integration.md) — SDK setup, env vars, cross-skill delegation
- [Well-Architected Assessment](references/well-architected-assessment.md) — 4-pillar assessment

## Operational Best Practices

- **Least privilege:** CAM policies scoped to `mongodb:*` on specific instances only
- **Availability:** Use multi-AZ deployment for replica sets (3 nodes across 3 AZs)
- **Backup:** Enable auto-backup with 7-day retention; test restore quarterly
- **Cost:** Right-size memory/disk via monitoring; prepaid for stable workloads
- **Security:** Enable SSL, VPC isolation, audit logging, and password rotation
