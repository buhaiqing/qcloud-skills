---
name: qcloud-mongodb-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud MongoDB (TencentDB for MongoDB / 云数据库 MongoDB) — instance lifecycle,
  backup/restore, account management, parameter tuning, slow log analysis, audit
  configuration, SSL/TLS, security groups, and performance diagnostics. User
  mentions MongoDB, Mongo, 云数据库 MongoDB, TencentDB MongoDB, or describes
  database connection issues, performance degradation, backup failures, or
  instance   creation/modification/deletion scenarios even without naming the
  product directly. Not for other database types (MySQL/CDB, Redis, PostgreSQL,
  ES), basic VPC/CAM/billing operations, or self-hosted MongoDB — those have
  their own ops skills or are out of scope.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python-mongodb),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.2.0"
  last_updated: "2026-06-09"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/240"
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

## Five Core Standards

> See [shared-boilerplate.md](../qcloud-skill-generator/SKILL.md#five-core-standards-quality-gates).

### Token Efficiency (TE)

| Rule | Application in This Skill |
|------|---------------------------|
| **TE-1** | Engine versions and on-sale specs via `DescribeSpecInfo` — not hardcoded tables in flows |
| **TE-3** | Error tables ≤3 columns (`Error Code \| Description \| Recovery`) |
| **TE-4** | JSON paths centralized in [API and Response Conventions](#api-and-response-conventions) |
| **TE-5** | `assets/example-config.yaml` uses YAML anchors (`&default-thresholds`) |
| **TE-6** | Pre-flight → Execute → Validate → Recover defined only in this file; references hold depth |
| **TE-7** | Variable table omits redundant Description column where field meaning is obvious |

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
- Task is **architecture design review** / four-pillar Well-Architected assessment → delegate to: `qcloud-well-architected-review`

### Delegation Rules

- If creating a MongoDB instance in a new VPC/subnet, delegate VPC setup to `qcloud-vpc-ops` first
- If configuring CAM policies for MongoDB access, delegate to `qcloud-cam-ops`
- If setting up monitoring alarms, delegate to `qcloud-monitor-ops` for alarm policy creation
- Proactive inspection (read-only) → invoked by `qcloud-proactive-inspection`; see `references/proactive-inspection.md`
- Well-Architected assessment (read-only) → invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Read-only Well-Architected assessment for **MongoDB**; return `{{output.product_assessment}}`.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | reliability / security / cost / efficiency (or `all`) |
| `{{user.scope}}` | `single-resource` or `account-wide` |

**Allowed:** `Describe*` and `GetMonitorData` only — **no** TerminateDBInstance/DropDB/Modify mutations.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: mongodb`).

## Variables

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
| `{{user.backup_id}}` | User | Backup ID for restore | Ask once |
| `{{user.flashback_time}}` | User | Target flashback timestamp (ISO 8601) | Ask once |
| `{{user.target_mongo_version}}` | User | Target engine version (e.g. MONGO_70_WT) | Ask once; verify via DescribeSpecInfo |
| `{{output.instance_id}}` | API Response | New instance ID | Parse from DescribeDBInstances |
| `{{output.deal_id}}` | API Response | Order/deal ID | Parse from CreateDBInstance response |
| `{{output.flow_id}}` | API Response | Async flow ID | Parse from FlashBack/Upgrade responses |

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
| FlashBack | Point-in-time / key-based data rollback | High | **High** — data overwrite |
| Kill Ops | Terminate long-running operations | Low | Medium |
| Version Upgrade | Upgrade MongoDB engine version | High | **High** — restart required |
| TDE | Enable transparent data encryption | Medium | Medium |
| Connection Diagnosis | Connection URI, clients, namespaces | Low | None |
| Security Groups | Describe/modify bound security groups | Low | Medium |

## Execution Flows

Every operation: **Pre-flight → Execute (CLI primary, SDK fallback) → Validate → Recover**. Do not skip phases.

→ 完整操作流程（Create/Describe/Modify/Delete/Backup/Restore/Account/Parameter/SlowLog/SSL/Audit/Connection/KillOps/FlashBack/Upgrade/TDE/SecurityGroup）：见 [`references/execution-flows.md`](references/execution-flows.md)

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

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate
is a **runtime** scoring layer that audits each MongoDB execution against an explicit
rubric, in addition to the build-time **Safety Gates** above and the build-time
**2-round self-review** in [AGENTS.md](../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | [AGENTS.md §8](../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **2** | per-skill override (matches AGENTS.md §8 default for `qcloud-mongodb-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 MongoDB-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive instance: `TerminateDBInstances`, `IsolateDBInstance`, `OfflineIsolatedDBInstance`, `DestroyDBInstance` (and data-plane equivalents `DropDatabase` / `DropCollection`) | **yes** | **MongoDB has no `UNDROP`**; `TerminateDBInstances` (prepaid) is immediate + irreversible; `IsolateDBInstance` → `OfflineIsolatedDBInstance` has only a 7-day recycle-bin window. Termination of the primary strands all secondaries (oplog-replication coupling) |
| Mutating: `CreateDBInstance` / `CreateDBInstanceHour`, `ModifyDBInstanceSpec`, `UpgradeDbInstanceVersion`, `FlashBackDBInstance`, `RestoreDBInstance`, `CreateAccountUser`, `ModifyAccountPassword`, `SetAccountUserPrivilege`, `EnableTransparentDataEncryption`, `ModifyDBInstanceSecurityGroup`, `KillOps`, `ModifyInstanceParams` | **yes** | Restart / data-overwrite / privilege-escalation / lockout risk; needs scoring |
| Read-only: `DescribeDBInstances`, `DescribeSpecInfo`, `DescribeSlowLogs` / `DescribeSlowLogPatterns` / `DescribeDetailedSlowLogs`, `DescribeCurrentOp`, `DescribeClientConnections`, `DescribeDBInstanceURL`, `DescribeDBInstanceNamespace`, `DescribeDBBackups`, `DescribeInstanceParams`, `DescribeTransparentDataEncryptionStatus`, `DescribeAuditConfig`, `DescribeAuditLogs`, `DescribeSecurityGroup`, `DescribeInstanceSSL`, `InquirePriceCreateDBInstances` | optional (max_iter=1, no hard abort) | Polling tails are part of the parent op's trace |

### Decision flow (first match wins)

1. **Safety = 0** OR rule violation in `{1, 2, 3, 4, 5}` ⇒ **ABORT** (no partial result). Any password or `{{user.*}}-secret` field captured un-masked in trace is also an unconditional ABORT.
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

### MongoDB-specific safety rules (rubric §4)

Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | `IsolateDBInstance` / `DestroyDBInstance` (any) | Instance ID + Name + Status echo; warn that isolation moves the instance to recycle bin (7-day re... |
| 2 | `DropDatabase` / `DropCollection` (MongoDB wire protocol / `tccli mongodb` API equivalent) | Database/collection name echoed; warn that ALL documents, indexes, and user-defined roles for tha... |
| 3 | `ModifyDBInstanceSpec` (upgrade/downgrade: `NodeNum`, `Memory`, `Volume`) | Show current spec → target spec; warn that spec changes trigger a restart (30-120s downtime); for... |
| 4 | `ModifyAccountPassword` (any account) | Account name echoed; warn that the password change takes immediate effect; all active connections... |
| 5 | `ModifySecurityGroup` / `ModifyNetworkAccess` (security group or VPC network change) | For security group change: show current security group ID(s) → target; warn that the wrong securi... |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — `TerminateDBInstances` with active oplog replay (prepaid, single primary)

A user runs `tccli mongodb TerminateDBInstances --InstanceId cmgo-abc123` against a
prepaid replica-set primary (`NodeNum=3`) while `DescribeClientConnections` shows
40 active client sessions and the 2 secondaries (`cmgo-def456`, `cmgo-ghi789`) are
still receiving oplog replay.

| Dimension | Score |
|---|---|
| Correctness | 0.5 (instance did terminate — prepaid `TerminateDBInstances` is immediate — but the gate should have caught the situation) |
| **Safety** | **0** (rule 1 violated on two counts: (a) `SetDBInstanceDeletionProtection` status was not checked; protection was enabled and the call should have been blocked; (b) `DescribeDBInstanceNodeProperty` was not called to enumerate the 2 secondaries, so the user was not warned that secondaries `cmgo-def456` and `cmgo-ghi789` would be stranded with no path to elect a new primary) |
| Idempotency | 1 |
| Traceability | 1 |
| Spec Compliance | 1 |

`decision: ABORT`. The instance is already destroyed (prepaid `TerminateDBInstances` is immediate and irreversible — MongoDB has **no UNDROP**, unlike some RDBMS offerings). Recovery suggestion emitted: (1) open a Tencent Cloud support ticket to attempt data recovery from the latest auto-backup via `DescribeDBBackups`; (2) immediately disable `SetDBInstanceDeletionProtection` on the surviving secondaries to prevent the same batch from re-firing on auto-retry; (3) going forward, add a `DescribeDBInstanceNodeProperty` step before any `TerminateDBInstances` / `IsolateDBInstance` to enumerate replica-set peers, and surface the deletion-protection status read before submitting.

See [`references/rubric.md`](references/rubric.md) §6 for two more examples (PASS on `CreateDBInstanceHour` and RETRY on `ModifyDBInstanceSpec` downgrade).

---

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
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 MongoDB-specific safety rules incl. instance-isolate/destroy, database/collection drop, spec-change OOM risk, password change no-recovery, security group lockout), `references/prompt-templates.md`. `max_iter=2` per AGENTS.md §8 |
| 1.2.0 | 2026-06-09 | Added Token Efficiency section (TE-1–TE-7); connection diagnosis, KillOps, FlashBack, version upgrade, TDE flows; `references/idempotency-checklist.md`; expanded eval queries and negative boundaries in description |

## Reference Directory

- [Core Concepts](references/core-concepts.md) — Architecture, states, versions, limits
- [API & SDK Usage](references/api-sdk-usage.md) — Operation map, Python SDK examples
- [CLI Usage](references/cli-usage.md) — tccli mongodb command reference
- [Troubleshooting Guide](references/troubleshooting.md) — Error codes + diagnostic workflows
- [Monitoring & Alerts](references/monitoring.md) — Metrics, alarms, anomaly patterns
- [Integration](references/integration.md) — SDK setup, env vars, cross-skill delegation
- [Well-Architected Assessment](references/well-architected-assessment.md) — 4-pillar assessment
- [SecOps Security Operations](references/secops-security-operations.md) — Credential rotation, high-risk operations, compliance checklist
- [Idempotency Checklist](references/idempotency-checklist.md) — Retry-safe automation patterns

## Operational Best Practices

- **Least privilege:** CAM policies scoped to `mongodb:*` on specific instances only
- **Availability:** Use multi-AZ deployment for replica sets (3 nodes across 3 AZs)
- **Backup:** Enable auto-backup with 7-day retention; test restore quarterly
- **Cost:** Right-size memory/disk via monitoring; prepaid for stable workloads
- **Security:** Enable SSL, VPC isolation, audit logging, and password rotation
