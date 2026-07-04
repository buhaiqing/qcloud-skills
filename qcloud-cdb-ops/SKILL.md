---
name: qcloud-cdb-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud CDB (TencentDB for MySQL / 云数据库 MySQL) instances, including
  lifecycle management, backup/restore, account management, parameter tuning,
  slow query analysis, and disaster recovery. User mentions CDB, MySQL, 云数据
  库 MySQL, TencentDB, 腾讯云数据库, database instance, or describes
  product-specific scenarios (e.g., connection issues, slow queries, backup
  failure, instance scaling, version upgrade, SSL setup) even without naming the
  product directly. Not for other database types (ES, Redis, PostgreSQL),
  billing, CAM, or related products that have their own ops skills.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python-cdb),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.3.0"
  last_updated: "2026-07-04"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "2017-03-20 - https://cloud.tencent.com/document/api/236"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli cdb help` - CLI exposes CreateDBInstance,
    CreateDBInstanceHour, DescribeDBInstances, UpgradeDBInstance,
    RestartDBInstances, IsolateDBInstance, ReleaseIsolatedDBInstances,
    RenewDBInstance, ModifyDBInstanceName, ModifyDBInstanceProject,
    OpenWanService, CloseWanService, SwitchDBInstanceMasterSlave,
    UpgradeDBInstanceEngineVersion, OpenSSL, CloseSSL, DescribeSSLStatus,
    CreateBackup, DescribeBackups, DeleteBackups, CreateCloneInstance,
    DescribeBackupConfig, ModifyBackupConfig, DescribeErrorLogData,
    DescribeSlowLogData, ModifyInstanceParam, CreateAccounts, DescribeAccounts,
    ModifyAccountPassword, ModifyAccountPrivileges, DeleteAccounts,
    DescribeTasks, DescribeAsyncRequestInfo, and 80+ more operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud CDB (MySQL) Operations Skill

## Overview

TencentDB for MySQL (CDB) on Tencent Cloud provides a stable, reliable, and elastically scalable relational database service with comprehensive features including backup recovery, monitoring, disaster recovery, fast scaling, and data migration. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **`tccli` CLI** and **Python SDK fallback**), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

> **UX Compliance:** This skill follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`**: Official `tccli` fully supports CDB. You **MUST** ship **`references/cli-usage.md`** and, in **each** execution flow below, document **both** the SDK step **and** the `tccli` step. CLI is the **primary** execution path for simplicity; Python SDK is used for edge-case operations CLI doesn't expose or for complex parameter handling.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers (MySQL, CDB, 云数据库) and delegation rules (ES → qcloud-es-ops, Redis → qcloud-redis-ops, PostgreSQL → qcloud-pg-ops) |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented per operation |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps for CLI and SDK paths |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 12 CDB-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (CDB/MySQL), primary resource model (DBInstance); cross-product delegation documented |

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-AZ deployment, automatic backup, clone from backup, cross-region disaster recovery, master-slave switch | `references/well-architected-assessment.md` |
| **安全性 (Security)** | CAM permissions, SSL encryption, data-at-rest encryption, VPC network isolation, account access control | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Instance right-sizing, pay-as-you-go vs prepaid comparison, reserved instances, idle instance detection | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Parameter optimization, slow query analysis, connection pool management, DTS migration, batch operations | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "MySQL" OR "云数据库 MySQL" OR "CDB" OR "TencentDB" OR "腾讯云数据库" OR "数据库实例"
- Task involves CRUD or lifecycle operations on **MySQL DB instances** (CreateDBInstance, DescribeDBInstances, UpgradeDBInstance, RestartDBInstances, IsolateDBInstance, RenewDBInstance)
- Task involves **Backup and restore** (CreateBackup, DescribeBackups, DeleteBackups, CreateCloneInstance)
- Task involves **Account management** (CreateAccounts, DescribeAccounts, ModifyAccountPassword, ModifyAccountPrivileges, DeleteAccounts)
- Task involves **Parameter configuration** (ModifyInstanceParam, DescribeInstanceParams)
- Task involves **Security settings** (OpenSSL, CloseSSL, OpenDBInstanceEncryption)
- Task involves **Log query and analysis** (DescribeErrorLogData, DescribeSlowLogData)
- Task involves **Network configuration** (OpenWanService, CloseWanService, ModifyDBInstanceVipVport)
- Task involves **Version upgrade or engine upgrade** (UpgradeDBInstanceEngineVersion)
- Task keywords: MySQL, database, slow query, backup, restore, connection, password, account, SSL, encryption, migration
- User describes database issues (high CPU, disk full, connection timeout, replication lag)

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: `qcloud-billing-ops` (when present)
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops` (when present)
- Task is **VPC network only** (subnet, route table, NAT gateway) → delegate to: `qcloud-vpc-ops`
- Task is **Elasticsearch Service** → delegate to: `qcloud-es-ops`
- Task is **Redis / memcached** → delegate to: `qcloud-redis-ops` (when present)
- Task is **PostgreSQL** → delegate to: `qcloud-pg-ops` (when present)
- Task is **SQL Server** → delegate to: `qcloud-sqlserver-ops` (when present)
- Task is **MongoDB** → delegate to: `qcloud-mongodb-ops` (when present)
- Task is **architecture design review** / four-pillar Well-Architected assessment → delegate to: `qcloud-well-architected-review`

### Delegation Rules

- CDB instance depends on VPC: verify VPC/Subnet exist via `qcloud-vpc-ops` before CreateDBInstance
- For database migration (DTS), refer to Tencent Cloud DTS documentation (separate skill planned)
- Cloud Monitor integration via `qcloud-monitor-ops` for dashboard and alarm configuration
- Other database types: route to their respective skills (qcloud-es-ops, qcloud-redis-ops, etc.)
- Proactive inspection (read-only) → invoked by `qcloud-proactive-inspection`; see `references/proactive-inspection.md`
- Well-Architected assessment (read-only) → invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Read-only Well-Architected assessment for **CDB**; return `{{output.product_assessment}}`.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | reliability / security / cost / efficiency (or `all`) |
| `{{user.scope}}` | `single-resource` or `account-wide` |

**Allowed:** `Describe*` and `GetMonitorData` only — **no** Isolate/Drop/DDL mutations.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: cdb`).

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use documented default only if skill explicitly allows |
| `{{user.region}}` | User-supplied region | Ask once; reuse |
| `{{user.instance_id}}` | CDB instance ID (cdb-xxxxxx) | Ask once; reuse |
| `{{user.instance_name}}` | User-supplied instance name | Ask once; reuse |
| `{{user.memory}}` | Memory in MB (e.g., 1000, 2000, 4000) | Default: 1000 |
| `{{user.volume}}` | Disk size in GB (e.g., 50, 100, 200) | Default: 50 |
| `{{user.engine_version}}` | MySQL version (5.5, 5.6, 5.7, 8.0) | Default: 8.0 |
| `{{user.db_name}}` | Database name | Ask once |
| `{{user.account_name}}` | MySQL account name | Ask once |
| `{{user.password}}` | Account password | Collect securely; never log |
| `{{user.backup_id}}` | Backup ID | From DescribeBackups |
| `{{output.instance_id}}` | `$.Response.InstanceIds[0]` (or DealId) | Parse from API response |
| `{{output.deal_id}}` | `$.Response.DealIds[0]` | Order ID from purchase |
| `{{output.async_request_id}}` | `$.Response.AsyncRequestId` | Async task tracking ID |
| `{{output.request_id}}` | `$.Response.RequestId` | Request tracking ID |

> **`{{env.*}}` MUST NOT** be collected from the user. Credentials must never be logged or exposed.

## Quick Start

| Step | Action |
|------|--------|
| Env | `export TENCENTCLOUD_SECRET_ID=... TENCENTCLOUD_SECRET_KEY=... TENCENTCLOUD_REGION=...` |
| Setup | `pip install tccli` (CLI) or `pip install tencentcloud-sdk-python-cdb` (SDK fallback) |
| Verify | `tccli cdb DescribeDBInstances --Region {{env.TENCENTCLOUD_REGION}} --Limit 5` |
| First | `tccli cdb DescribeDBInstances --Region {{env.TENCENTCLOUD_REGION}} --Limit 10` |

See [Core Concepts](references/core-concepts.md) → [Execution Flows](#execution-flows) → [Troubleshooting](references/troubleshooting.md).

## Capabilities at a Glance

| Operation | Risk Level |
|-----------|------------|
| CreateDBInstance / CreateDBInstanceHour | Low |
| DescribeDBInstances | None |
| UpgradeDBInstance | Medium |
| RestartDBInstances | Medium |
| IsolateDBInstance | **High** |
| CreateBackup | None |
| CreateCloneInstance | **High** |
| ModifyInstanceParam | Medium |
| CreateAccounts | Low |
| DescribeSlowLogData | None |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial API/SDK-oriented template with tccli CLI support |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 CDB-specific safety rules incl. `ModifyAccountPrivileges` `Host=%` guard), `references/prompt-templates.md` (Generator + Critic + Orchestrator, isolated-context enforcement, password + Host='%' hygiene, SQL data-plane out-of-scope guard). `max_iter=2` per AGENTS.md §8 |
| 1.2.0 | 2026-07-04 | Added slow query quick diagnosis decision tree: `references/cdb-slow-query-diagnosis-optimized.md` with automated recovery strategies, MTTD/MTTR metrics, and 4-type classification. Updated `references/troubleshooting.md` with quick diagnosis path. |
| 1.3.0 | 2026-07-04 | Optimize: compress Quick Start to compact table, add SDK template reference, compress Capabilities table to 2 columns, remove duplicate Prerequisites, replace inline SDK boilerplate with template references. Bump version. |

---

## Slow Query Quick Diagnosis (快速诊断)

> **推荐**: 对于慢查询问题，使用 [CDB 慢查询快速诊断决策树](references/cdb-slow-query-diagnosis-optimized.md) 进行结构化诊断。

### 快速诊断场景

| 场景 | 特征 | 诊断时间 | 恢复时间 | 参考文档 |
|------|------|----------|----------|----------|
| **超长查询** | QueryTime > 10s | ≤ 2 分钟 | ≤ 5 分钟 | [决策树 §4.1](references/cdb-slow-query-diagnosis-optimized.md#41-type-a-超长查询诊断) |
| **资源瓶颈** | CPU > 80% | ≤ 3 分钟 | ≤ 15 分钟 | [决策树 §4.2](references/cdb-slow-query-diagnosis-optimized.md#42-type-b-资源瓶颈诊断) |
| **锁等待** | LockTime/QueryTime > 50% | ≤ 2 分钟 | ≤ 5 分钟 | [决策树 §4.3](references/cdb-slow-query-diagnosis-optimized.md#43-type-c-锁等待诊断) |
| **查询优化** | QueryTime 1-10s | ≤ 3 分钟 | ≤ 10 分钟 | [决策树 §4.4](references/cdb-slow-query-diagnosis-optimized.md#44-type-d-查询优化诊断) |

### 自动化恢复策略优先级

| 优先级 | 策略 | 适用场景 | MTTR |
|--------|------|----------|------|
| P0 | 终止超长查询 | Type A, 紧急情况 | ≤ 5 分钟 |
| P1 | 参数调优 | Type B, Type C | ≤ 15 分钟 |
| P2 | SQL 重写 | Type D | ≤ 10 分钟 |
| P3 | 规格升级 | Type B, 长期方案 | ≤ 30 分钟 |

### 快速检查命令

```bash
# 确认慢查询是否存在 (最近 1 小时)
tccli cdb DescribeSlowLogData \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "$(date -v-1H +'%Y-%m-%d %H:%M:%S')" \
  --EndTime "$(date +'%Y-%m-%d %H:%M:%S')" \
  --Limit 5 \
  --OrderBy "QueryTime" \
  --Order "DESC"

# 检查慢查询日志是否开启
tccli cdb DescribeInstanceParams \
  --InstanceId "{{user.instance_id}}" \
  --ParamNames '["slow_query_log","long_query_time"]'
```

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (SDK/API and tccli) → Validate → Recover**. Do not skip phases.

### Operation: CreateDBInstance (Create MySQL Instance — Prepaid)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Python SDK | `pip show tencentcloud-sdk-python-cdb` | Version installed | Document install |
| CLI / deps | `tccli version` | Exit code 0 | Document CLI install |
| Credentials | Check env vars | Non-empty | HALT |
| VPC/Subnet | Verify via qcloud-vpc-ops | VPC and subnet exist | HALT |
| Price | `tccli cdb DescribeDBPrice` | Price available | Check spec validity |

#### Execution — CLI

```bash
# Create prepaid MySQL 8.0 instance
tccli cdb CreateDBInstance \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Memory 1000 \
  --Volume 50 \
  --Period 1 \
  --GoodsNum 1 \
  --Zone "{{user.zone}}" \
  --UniqVpcId "{{user.vpc_id}}" \
  --UniqSubnetId "{{user.subnet_id}}" \
  --EngineVersion "8.0" \
  --InstanceRole "master" \
  --ProjectId 0
```

#### Execution — SDK

```python
# See references/sdk-templates.md for common init/poll/error boilerplate.

req = models.CreateDBInstanceRequest()
req.Memory = 1000
req.Volume = 50
req.Period = 1
req.GoodsNum = 1
req.Zone = "ap-guangzhou-3"
req.EngineVersion = "8.0"
resp = client.CreateDBInstance(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

1. Capture `{{output.deal_id}}` from CreateDBInstance response
2. Poll `DescribeTasks` or use `DescribeAsyncRequestInfo` until instance status is 1 (running)
3. On success, report instance ID and connection info

#### Failure Recovery

| Error pattern | Max retries | Agent Action |
|--------------|-------------|--------------|
| `InvalidParameterValue` | 0–1 | Fix parameter; retry |
| `FailedOperation.CreateOrderFailed` | 0 | HALT; check account/payment |
| `OperationDenied.InstanceStatusError` | 0 | HALT; check existing instance status |
| `InternalError.DBError` | 3 | Retry; escalate if persists |
| `LimitExceeded.ExceedMaxInstanceCount` | 0 | HALT; raise quota |

### Operation: DescribeDBInstances (List Instances)

#### Execution — CLI

```bash
# List all instances
tccli cdb DescribeDBInstances --Region {{env.TENCENTCLOUD_REGION}} --Offset 0 --Limit 20

# Filter by instance ID
tccli cdb DescribeDBInstances --InstanceIds '["cdb-xxxxxx"]'

# Filter by status (1=running)
tccli cdb DescribeDBInstances --Status "[1]"

# Filter by project
tccli cdb DescribeDBInstances --ProjectId 0
```

#### Execution — SDK

```python
# See references/sdk-templates.md for common init/poll/error boilerplate.

req = models.DescribeDBInstancesRequest()
req.Offset = 0
req.Limit = 20
# Optional filters
# req.InstanceIds = ["cdb-xxxxxx"]
# req.Status = [1]  # 1=running

resp = client.DescribeDBInstances(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Key Response Fields

| Field | JSON Path | Notes |
|-------|-----------|-------|
| InstanceId | `$.Response.Items[].InstanceId` | Instance unique ID |
| InstanceName | `$.Response.Items[].InstanceName` | — |
| Status | `$.Response.Items[].Status` | 0=creating, 1=running, 4=isolating, 5=isolated |
| Memory | `$.Response.Items[].Memory` | Memory in MB |
| Volume | `$.Response.Items[].Volume` | Disk in GB |
| EngineVersion | `$.Response.Items[].EngineVersion` | — |
| Vip | `$.Response.Items[].Vip` | — |
| Vport | `$.Response.Items[].Vport` | Port (default 3306) |
| Zone | `$.Response.Items[].Zone` | — |
| InstanceType | `$.Response.Items[].InstanceType` | 1=master, 2=DR, 3=read-only |
| AutoRenew | `$.Response.Items[].AutoRenew` | Auto-renewal flag |

### Operation: UpgradeDBInstance (Scale Instance)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | DescribeDBInstances | Status=1 (running) | HALT |
| New spec valid | DescribeDBPrice | Price available | Recommend valid specs |

#### Execution — CLI

```bash
# Upgrade instance configuration
tccli cdb UpgradeDBInstance \
  --InstanceId "{{user.instance_id}}" \
  --Memory 4000 \
  --Volume 200 \
  --WaitSwitch 1
```

#### Execution — SDK

```python
# See references/sdk-templates.md for common init/poll/error boilerplate.

req = models.UpgradeDBInstanceRequest()
req.InstanceId = "{{user.instance_id}}"
req.Memory = 4000
req.Volume = 200
req.WaitSwitch = 1  # 0=immediate, 1=maintain window

resp = client.UpgradeDBInstance(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

### Operation: RestartDBInstances

#### Pre-flight

- Warn user: instance will be unavailable during restart (typically 30–120s)

#### Execution — CLI

```bash
tccli cdb RestartDBInstances --InstanceIds '["{{user.instance_id}}"]'
```

#### Execution — SDK

```python
# See references/sdk-templates.md for common init/poll/error boilerplate.

req = models.RestartDBInstancesRequest()
req.InstanceIds = ["{{user.instance_id}}"]

resp = client.RestartDBInstances(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

### Operation: IsolateDBInstance — DESTRUCTIVE

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: isolating `{{user.instance_id}}` will make it inaccessible
- **MUST** suggest creating a final backup before isolation
- **MUST** warn: isolated instances can be de-isolated via `ReleaseIsolatedDBInstances` if within retention period
- **MUST NOT** proceed without clear user assent

#### Execution — CLI

```bash
tccli cdb IsolateDBInstance --InstanceId "{{user.instance_id}}"
```

### Operation: CreateBackup (Backup)

> **Reliability Pillar:** Following Tencent Cloud Well-Architected Framework, every writable skill MUST document backup operations.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | DescribeDBInstances | Status=1 | HALT |
| Backup config | DescribeBackupConfig | Config valid | Configure backup first |

#### Execution — CLI

```bash
# Create manual backup
tccli cdb CreateBackup \
  --InstanceId "{{user.instance_id}}" \
  --BackupMethod "logical" \
  --BackupDBTableList '[{"Db":"mysql","Table":"user"}]'
```

#### Execution — SDK

```python
# See references/sdk-templates.md for common init/poll/error boilerplate.

req = models.CreateBackupRequest()
req.InstanceId = "{{user.instance_id}}"
req.BackupMethod = "physical"  # or "logical"

# Optional: backup specific tables
# table_item = models.BackupItem()
# table_item.Db = "mysql"
# table_item.Table = "user"
# req.BackupDBTableList = [table_item]

resp = client.CreateBackup(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

Poll `DescribeBackups` until `Status` is `SUCCESS`:

```bash
tccli cdb DescribeBackups --InstanceId "{{user.instance_id}}" --Offset 0 --Limit 1
```

### Operation: ModifyInstanceParam (Parameter Change)

#### Execution — CLI

```bash
# Modify parameters
tccli cdb ModifyInstanceParam \
  --InstanceIds '["{{user.instance_id}}"]' \
  --ParamList '[{"Name":"auto_increment_increment","CurrentValue":"2"},{"Name":"max_connections","CurrentValue":"1000"}]'
```

#### Execution — SDK

```python
# See references/sdk-templates.md for common init/poll/error boilerplate.

req = models.ModifyInstanceParamRequest()
req.InstanceIds = ["{{user.instance_id}}"]

param1 = models.Parameter()
param1.Name = "auto_increment_increment"
param1.CurrentValue = "2"

param2 = models.Parameter()
param2.Name = "max_connections"
param2.CurrentValue = "1000"

req.ParamList = [param1, param2]

resp = client.ModifyInstanceParam(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

1. Verify via `DescribeInstanceParams` that values were applied
2. If `WaitSwitch=0` (immediate), some params may require restart

### Operation: Account Management

#### Create Account — CLI

```bash
tccli cdb CreateAccounts \
  --InstanceId "{{user.instance_id}}" \
  --Accounts '[{"User":"dbuser","Host":"%"}]' \
  --Password "{{user.password}}" \
  --Description "Application account"
```

#### Create Account — SDK

```python
# See references/sdk-templates.md for common init/poll/error boilerplate.

req = models.CreateAccountsRequest()
req.InstanceId = "{{user.instance_id}}"

account = models.Account()
account.User = "dbuser"
account.Host = "%"

req.Accounts = [account]
req.Password = "{{user.password}}"
req.Description = "Application account"

resp = client.CreateAccounts(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Describe Accounts — CLI

```bash
tccli cdb DescribeAccounts --InstanceId "{{user.instance_id}}" --Limit 20
```

#### Describe Accounts — SDK

```python
# See references/sdk-templates.md for common init/poll/error boilerplate.

req = models.DescribeAccountsRequest()
req.InstanceId = "{{user.instance_id}}"
req.Limit = 20

resp = client.DescribeAccounts(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Modify Password — CLI

```bash
tccli cdb ModifyAccountPassword \
  --InstanceId "{{user.instance_id}}" \
  --Accounts '[{"User":"dbuser","Host":"%"}]' \
  --NewPassword "{{user.new_password}}"
```

#### Modify Password — SDK

```python
# See references/sdk-templates.md for common init/poll/error boilerplate.

req = models.ModifyAccountPasswordRequest()
req.InstanceId = "{{user.instance_id}}"

account = models.Account()
account.User = "dbuser"
account.Host = "%"

req.Accounts = [account]
req.NewPassword = "{{user.new_password}}"

resp = client.ModifyAccountPassword(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

### Operation: Slow Query Log

#### Execution — CLI

```bash
tccli cdb DescribeSlowLogData \
  --InstanceId "{{user.instance_id}}" \
  --StartTime "2026-05-20 00:00:00" \
  --EndTime "2026-05-21 00:00:00" \
  --Limit 20
```


## Error Code Reference (≥ 12 Product-Specific Codes)

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter` | Parameter validation failed | Fix parameter per API spec |
| `InvalidParameterValue` | Parameter value out of range | Adjust value per spec |
| `MissingParameter` | Required parameter missing | Add missing parameter |
| `ResourceNotFound` | Resource not found | Verify instance ID via DescribeDBInstances |
| `ResourceNotFound.NoDBInstanceFound` | DB instance not found | Verify InstanceId |
| `ResourceInsufficient` | Resource quota insufficient | HALT; raise quota or delete resources |
| `InvalidSecretKey` | Credential invalid | HALT; fix credentials |
| `OperationDenied.InstanceLocked` | Instance locked by operation | Retry (3x, 30s); wait for completion |
| `OperationDenied.InstanceStatusError` | Wrong instance status | Check status via DescribeDBInstances |
| `FailedOperation.AsyncTaskError` | Async task execution failure | Retry (3x); check async task or escalate |
| `FailedOperation.CreateOrderFailed` | Order creation failed | HALT; check account balance/spec validity |
| `FailedOperation.StatusConflict` | Status conflict | Retry (2x, 10s); wait and retry |
| `LimitExceeded.ExceedMaxInstanceCount` | Max instance count exceeded | HALT; raise instance quota |
| `RequestLimitExceeded` | API rate limit | Retry (3x); exponential backoff |
| `InternalError` | Internal server error | Retry (3x); escalate with RequestId |
| `InternalError.DBError` | Database internal error | Retry (3x); escalate with RequestId |
| `InternalError.TaskError` | Task internal error | Retry (3x); check task details |
| `UnauthorizedOperation` | Unauthorized operation | HALT; check CAM permissions |

---

## Safety Gates (Destructive Operations)

Every **IsolateDBInstance**, **DeleteBackups**, **DeleteAccounts**, or **irreversible** operation MUST have:

1. **Explicit user confirmation** with resource identifier displayed
2. **Pre-backup reminder** (backup before isolate/delete)
3. **Dependency check** (warn if instance has active connections or dependent read replicas)
4. **Post-delete verification** (poll until status confirms operation)

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate
is a **runtime** scoring layer that audits each CDB execution against an explicit
rubric, in addition to the build-time **Safety Gates** above and the build-time
**2-round self-review** in [AGENTS.md](../../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **2** | per-skill override (matches AGENTS.md §8 default for `qcloud-cdb-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 CDB-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive: `IsolateDBInstance`, `ReleaseIsolatedDBInstances`, `DeleteBackups`, `DeleteAccounts`, `CreateCloneInstance` (over-spec restore) | **yes** | Irreversible or near-irreversible; needs scoring |
| Sensitive mutating: `ModifyAccountPrivileges` (esp. `GRANT ALL`), `UpgradeDBInstanceEngineVersion`, `ModifyInstanceParam` (params requiring restart), `SwitchDBInstanceMasterSlave` | **yes** | Privilege / version / failover risk; needs scoring |
| Mutating: `CreateDBInstance`, `CreateDBInstanceHour`, `UpgradeDBInstance`, `RestartDBInstances`, `CreateBackup`, `CreateAccounts`, `ModifyAccountPassword`, `OpenWanService` / `CloseWanService`, `OpenSSL` / `CloseSSL` | **yes** | Cost / state-change / security risk; needs scoring |
| Read-only: `DescribeDBInstances`, `DescribeBackups`, `DescribeAccounts`, `DescribeInstanceParams`, `DescribeSlowLogData` | optional (max_iter=1, no hard abort) | Polling tails are part of the parent op's trace |
| **Out of scope**: SQL execution against a CDB instance via MySQL wire protocol (`DROP DATABASE`, `TRUNCATE`, raw `UPDATE`) | **HALT** | This skill does not own the data plane. GCL pilot covers Tencent Cloud CDB API ops only |

### Decision flow (first match wins)

1. **Safety = 0** OR any rule violation in `{1, 2, 3, 4, 5}` ⇒ **ABORT** (no partial result). Password leak in trace is also an unconditional ABORT.
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

### CDB-specific safety rules (rubric §4)

Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | `IsolateDBInstance` (any, batch or single) | ID + Name echo + explicit confirmation + retention-window warning + dependency check (read-only r... |
| 2 | `CreateCloneInstance` / `Restore from backup` | Source backup must be named + `DescribeBackups` re-confirms; explicit confirmation that the actio... |
| 3 | `DeleteBackups` | Backup IDs + names + retention-day math surfaced ("deleting this backup means you cannot restore ... |
| 4 | `DeleteAccounts` | Account `User`+`Host` echoed; dependency check on active connections (`SHOW PROCESSLIST` or Tence... |
| 5 | `ModifyAccountPrivileges` (especially `GRANT ALL` / `REVOKE` of root-level privileges) | Show BEFORE / AFTER privilege diff; require explicit re-confirmation when the change is `GRANT AL... |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — `DeleteBackups` (last backup while isolate in flight)

| Dimension | Score |
|---|---|
| Correctness | 0.5 (backups were deleted, but gate should have caught the situation) |
| **Safety** | **0** (rule 3 violated) |
| Idempotency | 1 |
| Traceability | 1 |
| Spec Compliance | 1 |

`decision: ABORT`. Recovery suggestion emitted: check TencentDB recycle bin; if within window, file a Tencent Cloud support ticket; add a "do not delete last backup while isolate in flight" guard to the skill's pre-flight.

See [`references/rubric.md`](references/rubric.md) §6 for two more examples (PASS on `IsolateDBInstance` and RETRY on `ModifyAccountPrivileges`).

### Sibling — CVM Quality Gate

The CVM Quality Gate uses the same 5-dimension backbone and the same G/C/O prompt
architecture, with a different §4 rule set (CVM: `TerminateInstances` / HARD-stop /
`ResizeInstanceDisks` / `RunInstances` / `ResetInstances`). See
[`qcloud-cvm-ops/SKILL.md` §Quality Gate](../cvm-ops/SKILL.md#quality-gate-gcl) for
contrast.

---

## Reference Directory

- [Core Concepts](references/core-concepts.md) — CDB architecture, instance types, storage engines
- [API & SDK Usage](references/api-sdk-usage.md) — Operation map with request/response examples
- [CLI Usage](references/cli-usage.md) — tccli cdb command map and invocation patterns
- [Troubleshooting Guide](references/troubleshooting.md) — Error code diagnostics (≥ 12 codes)
- [Monitoring & Alerts](references/monitoring.md) — Metrics, dashboards, Cloud Monitor integration
- [Integration](references/integration.md) — SDK setup, env config, cross-skill delegation
- [Well-Architected Assessment](references/well-architected-assessment.md) — Four-pillar assessment

## Operational Best Practices

- **Least privilege:** CAM policies scoped to required CDB APIs only
- **Availability:** Multi-AZ deployment for production; automatic backup enabled with appropriate retention
- **Cost:** Right-size specifications; use prepaid for stable workloads, postpaid for variable loads
- **Performance:** Regular slow query analysis; optimize indexes; maintain appropriate connection pools
