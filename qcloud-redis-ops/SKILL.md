---
name: qcloud-redis-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or manage TencentDB for Redis
  instances — lifecycle management, backup/restore, specification upgrade, renewal, isolation,
  connectivity diagnostics, and performance monitoring. User mentions Redis, 云缓存,
  TencentDB Redis, cache instance, redis cluster, or describes caching/data store scenarios
  even without naming the product directly. Not for billing, CAM, VPC, or application-level
  Redis client debugging that have their own ops skills.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python-redis),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.1.0"
  last_updated: "2026-06-04"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/239"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli redis help` - CLI exposes CreateInstance, DescribeInstances,
    DescribeProductInfo, DescribeInstanceList, UpgradeInstance, AutoRenewInstance,
    ManualRenewInstance, DescribeInstanceBackupRecords, IsolateInstance,
    CleanInstance, DescribeAutoBackupConfig, ModifyAutoBackupConfig,
    ModifyInstanceParams, DescribeParamTemplateInfo, and 20+ more operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# TencentDB for Redis Operations Skill

## Overview

TencentDB for Redis is Tencent Cloud's managed in-memory database service supporting standalone, master-replica, and cluster architectures. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **`tccli` CLI** and **Python SDK fallback**), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

> **UX Compliance:** This skill follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`**: Official `tccli` fully supports Redis. You **MUST** ship **`references/cli-usage.md`** and, in **each** execution flow below, document **both** the SDK step **and** the `tccli` step. CLI is the **primary** execution path; Python SDK is used for edge-case operations CLI doesn't expose.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers (Redis, 云缓存) and delegation rules (VPC → qcloud-vpc-ops, Monitor → qcloud-monitor-ops) |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented per operation |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps for CLI and SDK paths |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 12 Redis-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (Redis), primary resource model (Instance); cross-product delegation documented |

Refer to the [meta-skill](../qcloud-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions.

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Master-replica/cluster HA, automatic failover, backup/restore, multi-AZ deployment | `references/well-architected-assessment.md` |
| **安全性 (Security)** | CAM permissions, password authentication, VPC isolation, whitelist management | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Instance type/size comparison, prepaid vs pay-as-you-go, idle instance detection | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Batch instance operations, parameter optimization, auto-backup scheduling | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Redis" OR "云缓存" OR "TencentDB Redis" OR "cache instance" OR "redis cluster"
- Task involves CRUD or lifecycle operations on **Redis Instances** (CreateInstance, DescribeInstances, IsolateInstance, CleanInstance)
- Task involves **Backup and Restore** (DescribeInstanceBackupRecords, DescribeAutoBackupConfig, ModifyAutoBackupConfig)
- Task involves **Instance Upgrade** (UpgradeInstance for memory/spec/type changes)
- Task involves **Renewal** (AutoRenewInstance, ManualRenewInstance for prepaid instances)
- Task keywords: create redis, cache instance, redis cluster, backup redis, restore redis, upgrade redis memory, renew redis, isolate instance, redis connection refused, redis slow queries
- User asks to deploy, configure, troubleshoot, or monitor Redis **via API, SDK, CLI, or automation**
- User describes Redis performance issues (high memory, slow queries, connection refused) without naming product

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: `qcloud-billing-ops` (when present)
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops` (when present)
- Task is **VPC network only** → delegate to: `qcloud-vpc-ops`
- Task is **application-level Redis client debugging** (connection strings, serialization) → application debugging, not this skill
- Task is **TencentDB for MySQL/PostgreSQL** → delegate to: `qcloud-cdb-ops` / `qcloud-postgres-ops`
- Task is cloud **Memcached** → delegate to appropriate Memcached skill (when present)
- Task is **architecture design review** / four-pillar Well-Architected assessment → delegate to: `qcloud-well-architected-review`

### Delegation Rules

- Redis depends on VPC: verify VPC/Subnet exist via `qcloud-vpc-ops` before CreateInstance
- Redis uses Monitor for metrics: delegate alerting/dashboard to `qcloud-monitor-ops`
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs
- Proactive inspection (read-only) → invoked by `qcloud-proactive-inspection`; see `references/proactive-inspection.md`
- Well-Architected assessment (read-only) → invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Read-only Well-Architected assessment for **Redis**; return `{{output.product_assessment}}`.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | reliability / security / cost / efficiency (or `all`) |
| `{{user.scope}}` | `single-resource` or `account-wide` |

**Allowed:** `Describe*` and `GetMonitorData` only — **no** Create/Destroy/Clear/Modify mutations.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: redis`).

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use default `ap-guangzhou` if unset |
| `{{user.vpc_id}}` | User-supplied VPC ID | Ask once; reuse |
| `{{user.subnet_id}}` | User-supplied subnet ID | Ask once; reuse |
| `{{user.instance_name}}` | User-supplied Redis instance name | Ask once; reuse |
| `{{user.instance_id}}` | User-supplied Redis instance ID (crs-xxx) | Ask once; reuse |
| `{{user.instance_type}}` | User-supplied instance spec/memory type | Ask once; use DescribeProductInfo |
| `{{user.password}}` | User-supplied Redis password | Ask once; mask in output |
| `{{output.instance_id}}` | From CreateInstance response | Parse `$.Response.InstanceId` |
| `{{output.request_id}}` | From any API response | Parse `$.Response.RequestId` for tracking |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose `TENCENTCLOUD_SECRET_KEY` or Redis passwords in any output. Mask all credentials with `***` or `<masked>`.

## API and Response Conventions

- **API spec is canonical** at https://cloud.tencent.com/document/api/239
- **Errors:** Map SDK/HTTP errors to `code` / `message` fields. Tencent Cloud uses `Response.Error` pattern
- **Async behavior:** Instance creation and upgrade are async — poll DescribeInstances until Status = `2` (running)
- **Instance IDs:** Format `crs-xxxxxxxx`

### Response Field Table

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| CreateInstance | `$.Response.InstanceId` | string | New instance ID (crs-xxx) |
| DescribeInstances | `$.Response.InstanceSet[].InstanceId` | array | Instance IDs |
| DescribeInstances | `$.Response.InstanceSet[].Status` | number | 0=待初始化, 1=运行中(旧), 2=运行中, 3=删除中 |
| DescribeInstances | `$.Response.InstanceSet[].Name` | string | Instance name |
| DescribeInstances | `$.Response.InstanceSet[].Size` | number | Memory in MB |
| DescribeInstances | `$.Response.InstanceSet[].NetType` | number | 0=内网, 1=外网 |
| UpgradeInstance | `$.Response.TradeDealDetailId` | string | Trade/transaction ID |
| IsolateInstance | `$.Response.InstanceIds` | array | Isolated instance IDs |

### Expected State Transitions

| Operation | Initial Status | Target Status | Poll Interval | Max Wait |
|-----------|----------------|---------------|---------------|----------|
| CreateInstance | 0 (initializing) | 2 (running) | 10s | 600s |
| UpgradeInstance | 2 (running) | 2 (running, new spec) | 10s | 1200s |
| IsolateInstance | 2 (running) | 3 (isolating) → absent | 10s | 600s |
| CleanInstance | 3 (isolated) | absent | 10s | 300s |

## Quick Start

### What This Skill Does

This skill enables you to deploy, configure, troubleshoot, and manage TencentDB for Redis instances on Tencent Cloud using the `tccli` CLI (primary) or `tencentcloud-sdk-python-redis` SDK (fallback).

### Prerequisites

- [ ] `tccli` CLI installed (or Python 3.8+ runtime for SDK fallback)
- [ ] Credentials configured: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region set: `TENCENTCLOUD_REGION`
- [ ] VPC and subnet created (delegate to `qcloud-vpc-ops` if needed)

### Verify Setup

```bash
# Check CLI and list Redis instances
tccli redis DescribeInstanceList --Region {{env.TENCENTCLOUD_REGION}} --Offset 0 --Limit 1
```

### Your First Command

```bash
# List all Redis instances
tccli redis DescribeInstanceList --Region {{env.TENCENTCLOUD_REGION}} --Offset 0 --Limit 100
```

### Next Steps

- [Core Concepts](references/core-concepts.md) — Understand Redis architecture
- [Execution Flows](#execution-flows-agent-readable) — Create, manage, and delete instances
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreateInstance | Create a Redis instance (standalone/master-replica/cluster) | Medium | Low |
| DescribeInstances | View instance details, status, endpoints | Low | None |
| DescribeProductInfo | Query available instance types and specs | Low | None |
| UpgradeInstance | Upgrade memory size or instance type | Medium | Medium — brief downtime |
| RenewInstance | Renew prepaid instance (auto/manual) | Low | Low |
| DescribeInstanceBackupRecords | List available backups | Low | None |
| IsolateInstance | Isolate (soft delete) a running instance | Low | **High** — instance becomes unavailable |
| CleanInstance | Hard delete an isolated instance | Low | **High** — irreversible |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial release — lifecycle, backup/restore, upgrade, renewal, dual-path |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 Redis-specific safety rules incl. instance-destroy/isolate, FLUSHALL data-plane audit blind spot, spec-change eviction, password no-recovery, backup export security), `references/prompt-templates.md`. `max_iter=2` per AGENTS.md §8 |

---

## Execution Flows (Agent-Readable)

### Operation: CreateInstance

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI installed | `tccli redis help CreateInstance` | Exit code 0 | Document CLI install |
| SDK available | `python3 -c "from tencentcloud.redis import redis_client"` | No ImportError | `pip install tencentcloud-sdk-python-redis` |
| Credentials | Check env vars | Non-empty values | HALT |
| VPC exists | `tccli vpc DescribeVpcs --VpcId {{user.vpc_id}}` | VPC in Available state | Delegate to `qcloud-vpc-ops` |
| Subnet exists | `tccli vpc DescribeSubnets --SubnetIds {{user.subnet_id}}` | Subnet exists | Delegate to `qcloud-vpc-ops` |
| Product info | `tccli redis DescribeProductInfo` | Instance type available | Suggest alternative type |
| Quota | Check DescribeInstances for instance count | Below quota limit | HALT; request quota increase |

#### Execution — CLI (`tccli`) (Primary Path)

```bash
tccli redis CreateInstance \
  --InstanceId "" \
  --Memory 1024 \
  --Period 1 \
  --GoodsNum 1 \
  --Zone "100001" \
  --ProjectId 0 \
  --Password "{{user.password}}" \
  --VpcId "{{user.vpc_id}}" \
  --SubnetId "{{user.subnet_id}}" \
  --InstanceName "{{user.instance_name}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Read `{{output.instance_id}}` from `$.Response.InstanceId`
2. Poll DescribeInstances until Status = `2` (running) or timeout (600s):

```bash
for i in $(seq 1 60); do
  STATUS=$(tccli redis DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} --InstanceId "{{output.instance_id}}" | jq -r '.Response.InstanceSet[0].Status')
  [ "$STATUS" = "2" ] && break
  sleep 10
done
```

3. Report instance ID, endpoint, and port to user
4. On failure, go to **Failure Recovery**

#### Failure Recovery

| Error pattern | Max retries | Backoff | Agent Action | UX Feedback |
|---------------|-------------|---------|--------------|-------------|
| `InvalidParameter` | 0–1 | — | Fix args per API spec; retry once | `[ERROR] InvalidParameter: Check CreateInstance API spec → Retry` |
| `ResourceInsufficient.SpecCode` | 0 | — | HALT | `[ERROR] Instance spec unavailable → Check DescribeProductInfo` |
| `QuotaExceeded.InstanceCount` | 0 | — | HALT | `[ERROR] Instance quota exceeded → Request increase` |
| `ResourceInUse.InstanceName` | 0 | — | HALT | `[ERROR] Instance name already exists → Use unique name` |
| `InvalidSecretKey` / `InvalidSecretId` | 0 | — | HALT | `[ERROR] Credential invalid → Verify env vars` |
| `RequestLimitExceeded` | 3 | exponential | Back off; retry | `⚠️ Rate limit → Retry in {backoff}s` |
| `InternalError` | 3 | 2s, 4s, 8s | Retry; HALT with RequestId | `[ERROR] InternalError → Escalate with RequestId` |
| `VPCNotInZone` | 0 | — | HALT | `[ERROR] VPC not in selected zone → Create VPC in correct zone` |

### Operation: DescribeInstances

#### Execution

```bash
# List all instances
tccli redis DescribeInstanceList --Region {{env.TENCENTCLOUD_REGION}} --Offset 0 --Limit 100

# Filter by instance ID
tccli redis DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} --InstanceId "{{user.instance_id}}"
```

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Present to User

| Field | JSON Path | Notes |
|-------|-----------|-------|
| InstanceId | `$.Response.InstanceSet[0].InstanceId` | Plain text (crs-xxx) |
| Name | `$.Response.InstanceSet[0].Name` | Human-readable |
| Status | `$.Response.InstanceSet[0].Status` | 0=init, 2=running, 3=isolating |
| Size | `$.Response.InstanceSet[0].Size` | Memory in MB |
| VpcId | `$.Response.InstanceSet[0].VpcId` | VPC binding |
| SubnetId | `$.Response.InstanceSet[0].SubnetId` | Subnet binding |
| Ip | `$.Response.InstanceSet[0].Ip` | Internal IP |
| Port | `$.Response.InstanceSet[0].Port` | Redis port (default 6379) |

### Operation: UpgradeInstance

#### Pre-flight

- Instance must be in Status = 2 (running)
- Backup current data before upgrade
- Inform user of brief downtime during upgrade

#### Execution — CLI

```bash
tccli redis UpgradeInstance \
  --InstanceId "{{user.instance_id}}" \
  --Memory 2048 \
  --UpgradeType "1" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

#### Post-execution Validation

1. Poll DescribeInstances until Status returns to `2` (max 1200s)
2. Verify new memory size matches requested

### Operation: DescribeInstanceBackupRecords

#### Execution

```bash
tccli redis DescribeInstanceBackupRecords \
  --InstanceId "{{user.instance_id}}" \
  --BeginTime "2026-05-13 00:00:00" \
  --EndTime "2026-05-21 23:59:59" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

### Operation: IsolateInstance (Soft Delete)

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: instance `{{user.instance_name}}` (`{{user.instance_id}}`) will be isolated
- **MUST** warn: instance becomes inaccessible; data preserved for 7 days
- **SHOULD** recommend creating backup before isolation

#### Execution — CLI

```bash
tccli redis IsolateInstance \
  --InstanceId "{{user.instance_id}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

#### Post-execution Validation

1. Verify instance status changes to `3` (isolating)
2. Note: instance appears in list but inaccessible

### Operation: CleanInstance (Hard Delete)

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible deletion of `{{user.instance_id}}`
- **MUST** verify instance is already isolated (Status = 3)
- **MUST** warn: all data permanently destroyed

#### Execution — CLI

```bash
tccli redis CleanInstance \
  --InstanceId "{{user.instance_id}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

---

## Error Code Reference (Redis-Specific)

| Code | Meaning | Retry? | Agent Action |
|------|---------|--------|--------------|
| `InvalidParameter` | Parameter validation failed | No | Fix parameter per API spec |
| `InvalidParameterValue` | Parameter value out of range | No | Adjust value |
| `MissingParameter` | Required parameter missing | No | Add missing parameter |
| `ResourceNotFound` | Instance does not exist | No | Verify InstanceId; list instances |
| `ResourceInsufficient` | Instance type/spec not available | No | Check DescribeProductInfo for alternatives |
| `ResourceInUse` | Instance name already exists | No | Use unique name |
| `InstancePreRunning` | Instance not yet ready | Yes (3x, 30s) | Poll DescribeInstances; retry when running |
| `InstancePreIsolate` | Instance not yet isolatable | Yes (3x, 30s) | Wait; retry |
| `OperationConflict` | Concurrent operation on instance | Yes (3x, 30s) | Wait for completion; retry |
| `InvalidSecretKey` / `InvalidSecretId` | Credential invalid | No | HALT; fix credentials |
| `RequestLimitExceeded` | API rate limit exceeded | Yes (3x) | Exponential backoff |
| `InternalError` | Server-side error | Yes (3x) | Retry; escalate with RequestId |
| `QuotaExceeded` | Instance quota exceeded | No | HALT; request quota increase |
| `VPCNotInZone` | VPC not in selected zone | No | Create VPC in correct zone |

> **After use:** Verify each code in the official Redis API error documentation.

## Safety Gates (Destructive Operations)

Every **IsolateInstance** and **CleanInstance** operation MUST have:

1. **Explicit user confirmation** with instance ID and name displayed
2. **Pre-operation backup reminder** — CreateInstance backup or manual export
3. **Status verification** — confirm instance is in correct state before operation
4. **Post-operation validation** — poll until target state achieved

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate
is a **runtime** scoring layer that audits each Redis execution against an explicit
rubric, in addition to the build-time **Safety Gates** above and the build-time
**2-round self-review** in [AGENTS.md](../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | [AGENTS.md §8](../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **2** | per-skill override (matches AGENTS.md §8 default for `qcloud-redis-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 Redis-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive: `IsolateInstance` (soft delete), `CleanInstance` (hard delete), `ClearInstance` (FLUSHALL/FLUSHDB data-plane flush), `ResetPassword` on `default` account | **yes** | Irreversible or near-irreversible; needs scoring |
| Sensitive mutating: `UpgradeInstance` (memory/shard/replica change — triggers primary-replica failover), `ModifyInstanceParams` (`NeedRestart=1`), `ResetPassword` (immediate effect, drops live connections), `BackupDownload` (export — in-memory exposure) | **yes** | Failover / immediate-effect / data-plane audit-blind risk; needs scoring |
| Mutating: `CreateInstance`, `AutoRenewInstance` / `ManualRenewInstance`, `ModifyAutoBackupConfig`, `ModifyNetworkConfig`, `ModifyInstanceAccount` | **yes** | Cost / state-change / security risk; needs scoring |
| Read-only: `DescribeInstances`, `DescribeInstanceList`, `DescribeProductInfo`, `DescribeAutoBackupConfig`, `DescribeInstanceBackups`, `DescribeInstanceMonitorBigKey`, `DescribeParamTemplateInfo` | optional (max_iter=1, no hard abort) | Polling tails are part of the parent op's trace |
| **Out of scope**: raw Redis wire-protocol data-plane commands outside the skill's `ClearInstance` surface (`KEYS`, `SCAN` mass reads, `DEBUG` family, raw `CONFIG SET` via app side-channel) | **HALT** | This skill does not own the application-side data plane. GCL pilot covers Tencent Cloud Redis API ops plus the documented `ClearInstance` flush |

### Decision flow (first match wins)

1. **Safety = 0** OR any rule violation in `{1, 2, 3, 4, 5}` ⇒ **ABORT** (no partial result). Password or `TENCENTCLOUD_SECRET_KEY` leak in trace is also an unconditional ABORT.
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

### Redis-specific safety rules (rubric §4)

Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | `DestroyInstances` / `IsolateInstance` (any) | Instance ID + Name + Status echo; warn that isolation moves instance to recycle bin (short retent... |
| 2 | `ClearInstance` (`FlushInstance` — FLUSHALL / FLUSHDB) | Instance ID + Name + database index (0-255) echoed; warn that FLUSHALL removes ALL keys in ALL da... |
| 3 | `ModifyInstanceSpec` / `UpgradeInstance` (spec change, `MemSize`, `ReplicasNum`, `NodeNum`, `ShardNum`) | Show current spec → target spec; warn that spec changes trigger a failover (5-30s downtime); for ... |
| 4 | `ResetPassword` (any, especially `default` account) | Account name echoed; warn that the password change takes immediate effect and all existing connec... |
| 5 | `BackupDownload` / export (sensitive data) | Backup file size + time range echoed; warn that the backup contains all cached data including any... |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — `ClearInstance` (FLUSHALL) without literal confirmation

| Dimension | Score |
|---|---|
| Correctness | 0.5 (FLUSHALL issued, protocol returned `+OK`, but gate should have caught it) |
| **Safety** | **0** (rule 2 violated) |
| Idempotency | 1 |
| Traceability | 0 (no `RequestId` — call is invisible to API audit; `DBSIZE` post-check missing) |
| Spec Compliance | 1 |

`decision: ABORT`. Recovery suggestion emitted: "Confirm with user that the dev cache is the intended target; add a 'literal `CONFIRM FLUSH <instance_id>`' gate to pre-flight for all `ClearInstance` calls; capture `DBSIZE` pre + post as the only audit trail — `ClearInstance` is invisible to CloudAudit."

See [`references/rubric.md`](references/rubric.md) §6 for two more examples (PASS on `DescribeInstances` and RETRY on `ResetPassword`).

---

## Output Schema

All responses follow Tencent Cloud API structure:

```json
{
  "Response": {
    "RequestId": "abc123",
    "InstanceId": "crs-xxxxx"
  }
}
```

Error responses:

```json
{
  "Response": {
    "RequestId": "abc123",
    "Error": {
      "Code": "InvalidParameter",
      "Message": "Parameter validation failed"
    }
  }
}
```

---

## Reference Directory

- [Core Concepts](references/core-concepts.md) — Redis architecture, instance types, modes
- [API & SDK Usage](references/api-sdk-usage.md) — Redis API operation map and SDK patterns
- [CLI Usage](references/cli-usage.md) — `tccli redis` command map and coverage gaps
- [Troubleshooting Guide](references/troubleshooting.md) — Error codes, diagnostics, scenarios
- [Monitoring & Alerts](references/monitoring.md) — Redis metrics, alert patterns
- [Integration](references/integration.md) — SDK setup, cross-skill delegation, CI/CD
- [Well-Architected Assessment](references/well-architected-assessment.md) — Four-pillar assessment
- [Enhanced Self-Healing Framework](references/enhanced-self-healing-framework.md) — Installation recovery
- [Execution Environment Setup](../qcloud-skill-generator/references/execution-environment.md)

## Operational Best Practices

- **Architecture choice:** Use master-replica for production HA; standalone for development
- **Memory sizing:** Monitor memory usage; upgrade before > 80% sustained utilization
- **Backup policy:** Enable automatic daily backup; retain ≥ 7 days
- **Security:** Always use VPC (private IP); set strong password; configure whitelist
- **Version:** Use latest Redis version available in TencentDB (currently Redis 6.0/7.0)
- **Multi-AZ:** Deploy master-replica in different availability zones for fault tolerance