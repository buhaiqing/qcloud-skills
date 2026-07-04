---
name: qcloud-es-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud Elasticsearch Service (ES) clusters, indices, snapshots, and Kibana.
  User mentions ES, Elasticsearch, 腾讯云ES, 弹性搜索, cluster health, index
  management, or describes product-specific scenarios (e.g., cluster creation,
  health status red/yellow, index performance, snapshot backup, version upgrade,
  plugin management, Kibana access, node scaling, dictionary update) even
  without naming the product directly. Not for billing, CAM, VPC-only, COS
  standalone, or related products that have their own ops skills.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python-es),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.1.0"
  last_updated: "2026-06-04"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "2018-04-16 - https://cloud.tencent.com/document/api/845"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli es help` - CLI exposes CreateInstance, DescribeInstances,
    DeleteInstance, UpdateInstance, UpgradeInstance, UpgradeLicense, RestartInstance,
    RestartNodes, RestartKibana, DescribeInstanceLogs, DescribeInstanceOperations,
    DescribeViews, CreateIndex, DeleteIndex, DescribeIndexList, DescribeIndexMeta,
    UpdateIndex, UpdatePlugins, UpdateDictionaries, DiagnoseInstance,
    CreateClusterSnapshot, DescribeClusterSnapshot, DeleteClusterSnapshot,
    RestoreClusterSnapshot, and 30+ more operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud Elasticsearch Service Operations Skill

## Overview

Elasticsearch Service (ES) on Tencent Cloud provides a fully managed, elastically scalable cloud-native search and analytics engine built on open-source Elasticsearch, fully compatible with the ELK stack. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **`tccli` CLI** and **Python SDK fallback**), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

> **UX Compliance:** This skill follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`**: Official `tccli` fully supports ES. You **MUST** ship **`references/cli-usage.md`** and, in **each** execution flow below, document **both** the SDK step **and** the `tccli` step. CLI is the **primary** execution path for simplicity; Python SDK is used for edge-case operations CLI doesn't expose or for complex parameter handling.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers (ES, Elasticsearch, 弹性搜索) and delegation rules (VPC → qcloud-vpc-ops, COS → qcloud-cos-ops) |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented per operation |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps for CLI and SDK paths |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 12 ES-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (ES), primary resource model (Instance); cross-product delegation documented |

Refer to the [meta-skill](../qcloud-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions.

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-AZ ES cluster deployment, COS snapshot backup/restore, cross-region disaster recovery, health diagnosis | `references/well-architected-assessment.md` |
| **安全性 (Security)** | CAM permissions, VPC network isolation, HTTPS/TLS encryption, Kibana access control, security groups | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Node type right-sizing, hot/warm/cold/frozen tiering, COS snapshot cost optimization, reserved instances | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | ILM (Index Lifecycle Management), rollover/ shrink/force-merge, batch operations, dictionary/plugin automation | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "ES" OR "Elasticsearch" OR "弹性搜索" OR "腾讯云ES" OR "腾讯云elasticsearch"
- Task involves CRUD or lifecycle operations on **ES cluster instances** (CreateInstance, DescribeInstances, UpdateInstance, DeleteInstance, UpgradeInstance, UpgradeLicense)
- Task involves **Index management** (CreateIndex, DescribeIndexList, DescribeIndexMeta, DeleteIndex, UpdateIndex)
- Task involves **Cluster operations** (RestartInstance, RestartNodes, RestartKibana, DiagnoseInstance)
- Task involves **Snapshots and backups** (CreateClusterSnapshot, DescribeClusterSnapshot, DeleteClusterSnapshot, RestoreClusterSnapshot)
- Task involves **Plugins and dictionaries** (UpdatePlugins, UpdateDictionaries)
- Task keywords: elasticsearch, ES cluster, index, shard, replica, Kibana, logstash, snapshot, health status (green/yellow/red), node scaling, version upgrade, plugin, dictionary
- User asks to deploy, configure, troubleshoot, or monitor ES **via API, SDK, CLI, or automation**
- User describes performance issues (slow search, high indexing latency, JVM memory pressure) without naming the product

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: `qcloud-billing-ops` (when present)
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops` (when present)
- Task is **VPC network only** (subnet, route table, NAT gateway) → delegate to: `qcloud-vpc-ops`
- Task is **COS standalone** (object upload/download without ES context) → delegate to: `qcloud-cos-ops`
- Task is **CVM / compute instance** → delegate to: `qcloud-cvm-ops`
- Task is **MySQL/Redis/PostgreSQL database** → delegate to: `qcloud-cdb-ops` / `qcloud-redis-ops` / `qcloud-postgres-ops`
- Task is **architecture design review** / four-pillar Well-Architected assessment → delegate to: `qcloud-well-architected-review`

### Delegation Rules

- ES cluster depends on VPC: verify VPC/Subnet/SecurityGroup exist via `qcloud-vpc-ops` before CreateInstance
- ES uses COS for snapshot backup: delegate COS storage management to `qcloud-cos-ops` for bucket-level operations
- ES monitoring integration uses `qcloud-monitor-ops` for Cloud Monitor dashboard and alarm configuration
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs into one ambiguous flow
- Proactive inspection (read-only) → invoked by `qcloud-proactive-inspection`; see `references/proactive-inspection.md`
- Well-Architected assessment (read-only) → invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Read-only Well-Architected assessment for **Elasticsearch (ES)**; return `{{output.product_assessment}}`.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | reliability / security / cost / efficiency (or `all`) |
| `{{user.scope}}` | `single-resource` or `account-wide` |

**Allowed:** `Describe*` and read-only snapshot/index queries — **no** DeleteInstance/DeleteIndex/Update/Upgrade/Restart mutations.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: es`).

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use documented default only if skill explicitly allows |
| `{{user.region}}` | User-supplied region | Ask once; reuse |
| `{{user.cluster_name}}` | User-supplied ES cluster name | Ask once; reuse |
| `{{user.instance_id}}` | ES cluster InstanceId (es-xxxxxx) | Ask once; reuse |
| `{{user.index_name}}` | Index name | Ask once |
| `{{user.node_type}}` | Node specification (ES.S1.MEDIUM4, etc.) | Use smart defaults |
| `{{user.node_num}}` | Number of nodes | Default from existing config |
| `{{user.disk_size}}` | Disk size in GB | Default from existing config |
| `{{user.es_version}}` | Elasticsearch version (7.14, 7.10, etc.) | List available versions |
| `{{output.instance_id}}` | `$.Response.InstanceId` | Parse from API response |
| `{{output.deal_name}}` | `$.Response.DealName` | Order number from create response |
| `{{output.index_name}}` | `$.Response.IndexName` | Index creation response |
| `{{output.snapshot_id}}` | `$.Response.SnapshotId` | Snapshot operation response |
| `{{output.request_id}}` | `$.Response.RequestId` | Request tracking ID |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose `TENCENTCLOUD_SECRET_KEY`, `SecretKey`, or any credential field value. Credential verification MUST check existence only.

## Quick Start

### What This Skill Does
This skill enables you to deploy, configure, troubleshoot, and monitor Tencent Cloud Elasticsearch Service resources using the `tccli es` CLI (primary) or `tencentcloud-sdk-python-es` SDK (fallback).

### Prerequisites
- [ ] `tccli` CLI installed (or Python 3.8+ runtime for SDK fallback)
- [ ] Credentials configured: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region set: `TENCENTCLOUD_REGION`

### Verify Setup
```bash
tccli es DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} --Limit 5
```

### Your First Command
```bash
# List ES clusters in current region
tccli es DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} --Limit 10
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — Understand ES architecture
- [Common Operations](#execution-flows) — Create, manage, and monitor ES clusters
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreateInstance | Create ES cluster | High | Low |
| DescribeInstances | List ES clusters | Low | None |
| UpdateInstance | Scale/modify ES cluster | Medium | Medium |
| DeleteInstance | Terminate ES cluster | Medium | **High** — irreversible |
| UpgradeInstance | Upgrade ES version | High | Medium |
| RestartInstance | Restart ES cluster | Medium | Medium |
| DiagnoseInstance | Health diagnosis | Low | None |
| CreateIndex | Create index | Low | Low |
| DeleteIndex | Delete index | Low | **High** — data loss |
| CreateClusterSnapshot | Create snapshot backup | Medium | None |
| RestoreClusterSnapshot | Restore from snapshot | High | **High** — overwrite data |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial API/SDK-oriented template with tccli CLI support |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 ES-specific safety rules incl. cluster-delete irreversible, index-delete ILM awareness, config-change stability risk, password no-recovery, version-upgrade plugin compat), `references/prompt-templates.md`. `max_iter=2` per AGENTS.md §8 |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (SDK/API and tccli) → Validate → Recover**. Do not skip phases.

### Operation: CreateInstance (Create ES Cluster)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Python SDK | `pip show tencentcloud-sdk-python-es` | Version ≥ minimum | Document install |
| CLI / deps | `tccli version` | Exit code 0 | Document CLI install |
| Credentials | Check env vars | Non-empty values | HALT; user configures env |
| Region | Call DescribeInstances with limit 1 | Region valid | Suggest valid region |
| VPC/Subnet | Verify via qcloud-vpc-ops | VPC and subnet exist | HALT; create VPC first |
| Quota | Check `ResourceInsufficient` patterns | Sufficient quota | HALT; raise quota |

#### Execution

See [execution-flows.md](references/execution-flows.md) §1 for CLI and SDK command blocks.

#### Post-execution Validation

1. Capture `{{output.instance_id}}` from response: `$.Response.InstanceId`
2. Poll `DescribeInstances` until `HealthStatus` is stable (0=green, 1=yellow) or timeout — see [execution-flows.md](references/execution-flows.md) §1 polling examples
3. On success, report `{{output.instance_id}}` and cluster endpoint details to the user
4. On terminal failure, go to **Failure Recovery**

#### Failure Recovery

| Error pattern | Max retries | Backoff | Agent Action | UX Feedback |
|--------------|-------------|---------|--------------|-------------|
| `InvalidParameterValue` / invalid node type | 0–1 | — | Fix node type from spec; retry once | `[ERROR] InvalidParameterValue: Node type invalid. Check available node types via DescribeInstance` |
| `ResourceInsufficient` / quota exceeded | 0 | — | HALT | `[ERROR] ResourceInsufficient: Quota limit reached. Delete unused resources or request quota increase.` |
| `FailedOperation.NoEnoughNodes` | 0 | — | HALT | `[ERROR] NoEnoughNodes: Insufficient resources in this AZ. Try a different zone.` |
| `FailedOperation.PayFailed` | 0 | — | HALT | `[ERROR] PayFailed: Payment failed. Check account balance.` |
| `InvalidSecretKey` / `InvalidSecretId` | 0 | — | HALT | `[ERROR] Credential invalid. Verify TENCENTCLOUD_SECRET_ID and TENCENTCLOUD_SECRET_KEY.` |
| `RequestLimitExceeded` / 429 | 3 | exponential | Back off; respect rate limit | `⚠️ Rate limit reached. Retrying in {backoff}s...` |
| `InternalError` / 5xx | 3 | 2s, 4s, 8s | Retry; then HALT with RequestId | `[ERROR] InternalError. Retry or escalate with RequestId.` |

### Operation: DescribeInstances (List ES Clusters)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Credentials | Check env vars | Non-empty | HALT |

#### Execution

See [execution-flows.md](references/execution-flows.md) §2 for CLI and SDK command blocks.

### Operation: DeleteInstance (Terminate ES Cluster) — DESTRUCTIVE

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible delete of ES cluster `{{user.cluster_name}}` (`{{user.instance_id}}`)
- **MUST** suggest creating a final snapshot backup before deletion
- **MUST** warn: all indices, data, and Kibana configurations will be permanently lost
- **MUST NOT** proceed without clear user assent (type "CONFIRM" to proceed)

#### Execution

See [execution-flows.md](references/execution-flows.md) §3 for CLI and SDK command blocks.

### Operation: UpdateInstance (Scale Cluster)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Resource exists | DescribeInstances | Status=1 (normal) | HALT |
| Cluster healthy | HealthStatus | 0 or 1 (green/yellow) | Warn user; proceed with caution |

#### Execution

See [execution-flows.md](references/execution-flows.md) §4 for CLI and SDK command blocks.

### Operation: RestartInstance (Restart ES Cluster)

#### Pre-flight

- Warn user: cluster will be unavailable during restart (typically 30s–5min)

#### Execution

See [execution-flows.md](references/execution-flows.md) §5 and §6 for CLI and SDK command blocks for RestartInstance and RestartNodes.

### Operation: CreateClusterSnapshot (Backup)

> **Reliability Pillar:** Following Tencent Cloud Well-Architected Framework, snapshot backup is the primary data protection mechanism for ES.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Cluster exists | DescribeInstances | Instance exists | HALT |
| COS backup configured | DescribeClusterSnapshot | Backup repository accessible | Configure COS backup first |

#### Execution

See [execution-flows.md](references/execution-flows.md) §7 for CLI and SDK command blocks.

### Operation: RestoreClusterSnapshot (Restore)

#### Pre-flight (Safety Gate)

- **MUST** warn: restore overwrites current data
- **MUST** confirm target cluster and snapshot source

#### Execution

See [execution-flows.md](references/execution-flows.md) §8 for CLI and SDK command blocks.

### Operation: DiagnoseInstance (Health Diagnosis)

#### Execution

See [execution-flows.md](references/execution-flows.md) §9 for CLI and SDK command blocks.

---

## Prerequisites

1. **Install `tccli` CLI** (primary execution path):
   ```bash
   pip install tccli
   ```

2. **Bootstrap Python runtime** (for SDK fallback — Python 3.8+):
   ```bash
   pip install tencentcloud-sdk-python-es
   ```

3. **Configure Credentials** — Environment variables:
   ```bash
   export TENCENTCLOUD_SECRET_ID="{{env.TENCENTCLOUD_SECRET_ID}}"
   export TENCENTCLOUD_SECRET_KEY="{{env.TENCENTCLOUD_SECRET_KEY}}"
   export TENCENTCLOUD_REGION="{{env.TENCENTCLOUD_REGION}}"
   ```

4. **Verify Configuration**:
   ```bash
   tccli es DescribeInstances --Region "{{env.TENCENTCLOUD_REGION}}" --Limit 5
   ```

---

## Error Code Reference (≥ 12 Product-Specific Codes)

| Code | Meaning | Retry? | Agent Action |
|------|---------|--------|--------------|
| `InvalidParameterValue` | Parameter value invalid | No | Fix parameter per API spec |
| `InvalidParameter.InvalidNodeType` | Node type not supported | No | Check available node types |
| `InvalidParameter.InvalidAppId` | AppId mismatch | No | Check account configuration |
| `MissingParameter` | Required parameter missing | No | Add missing parameter |
| `ResourceNotFound` | ES instance not found | No | Verify InstanceId with DescribeInstances |
| `ResourceInsufficient` | Resource quota exceeded | No | HALT; request quota increase or delete resources |
| `AuthFailure.UnAuthDescribeInstances` | No CAM permission for describe | No | HALT; add CAM policy |
| `FailedOperation.ClusterStateError` | Cluster in wrong state for operation | Yes (3x, 30s) | Wait for cluster stable state; retry |
| `FailedOperation.NoEnoughNodes` | Insufficient node resources | No | Choose different AZ or node type |
| `FailedOperation.PayFailed` | Payment failure | No | HALT; check account balance |
| `FailedOperation.GetTagInfoError` | Tag query error | Yes (2x) | Retry; if persists, skip tag filter |
| `OperationDenied` | Operation not allowed | No | Check instance status and permissions |
| `RequestLimitExceeded` | API rate limit exceeded | Yes (3x) | Exponential backoff |
| `InternalError` | Internal server error | Yes (3x) | Retry; escalate with RequestId |

---

## Safety Gates (Destructive Operations)

Every **DeleteInstance**, **DeleteIndex**, **DeleteClusterSnapshot**, or **irreversible** operation MUST have:

1. **Explicit user confirmation** with resource identifier displayed
2. **Pre-backup reminder** (snapshot before destroy)
3. **Dependency check** (warn if cluster has active indices)
4. **Post-delete verification** (poll until ResourceNotFound)

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate
is a **runtime** scoring layer that audits each ES execution against an explicit
rubric, in addition to the build-time **Safety Gates** above and the build-time
**2-round self-review** in [AGENTS.md](../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | [AGENTS.md §8](../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **2** | per-skill override (matches AGENTS.md §8 default for `qcloud-es-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 ES-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive: `DeleteInstance`, `DeleteIndex`, `DeleteDataStream`, `DeleteClusterSnapshot` (without prior verify), `RestoreClusterSnapshot` (without target verify) | **yes** | Irreversible; ES has no Tencent Cloud recycle bin; data loss is immediate |
| Mutating: `CreateInstance`, `UpdateInstance` (vertical scale / disk expansion), `UpgradeInstance` (ES version), `RestartInstance`, `RestartNodes`, `UpdatePlugins`, `UpdateDictionaries`, `UpdateIndex` (settings / mapping), `UpdateInstanceSettings` (cluster dynamic settings), `ResetPassword` / `ModifyAccountPassword` | **yes** | Triggers rolling restart, password rotation, or cluster config change; needs scoring |
| Read-only: `DescribeInstances`, `DescribeIndexList`, `DescribeIndexMeta`, `DescribeClusterSnapshot`, `DescribeViews`, `DescribeInstanceOperations`, `DescribeDiagnose`, `DescribePlugins`, `DiagnoseInstance` | optional (max_iter=1, no hard abort) | Polling tails are part of the parent op's trace |

### Decision flow (first match wins)

1. **Safety = 0** OR rule violation in `{1, 2, 3, 4, 5}` ⇒ **ABORT** (no partial result)
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

### ES-specific safety rules (rubric §4)

Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | `DeleteInstance` / `DeleteCluster` (any) | Cluster ID + Name + version + index count echo; warn that ALL indices, data, snapshots, and Kiban... |
| 2 | `DeleteIndex` / `DeleteDataStream` (data-plane or API) | Index name + shard count + document count + index health status echoed; warn that index deletion ... |
| 3 | `UpdateInstanceSettings` / `ModifyClusterConfig` (cluster settings: `YML`, `ESConfig`, or dynamic settings) | Echo the config change diff (BEFORE vs AFTER); for settings that affect stability (`indices.field... |
| 4 | `ResetPassword` / `ModifyAccountPassword` (Kibana / ES built-in user) | Account name echoed; warn that the password change takes immediate effect; for the `elastic` / Ki... |
| 5 | `UpgradeElasticsearchVersion` (ES version upgrade) | Show current version → target version; warn that ES upgrades are one-directional (downgrade requi... |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — `DeleteIndex` without ILM / data-stream check

A user asked the agent to "delete the old logs". The agent called `DeleteIndex` for `log-2024.01` without first running `DescribeIndexList` to inspect whether the index was a rollover alias target for an ILM policy.

| Dimension | Score |
|---|---|
| Correctness | 0.5 (index did delete, but gate should have caught the role) |
| **Safety** | **0** (rule 2 violated) |
| Idempotency | 1 (`ResourceNotFound` recognized on follow-up) |
| Traceability | 1 |
| Spec Compliance | 1 |

`decision: ABORT`. Recovery suggestion emitted: recreate the index with the original mapping/settings, re-attach it as the ILM rollover alias target, then advance the ILM policy phase. Going forward, add a "check ILM / data-stream membership before delete" guard to the skill's pre-flight.

See [`references/rubric.md`](references/rubric.md) §6 for two more examples.

---

## Output Schema

All responses follow Tencent Cloud API structure:

```json
{
  "Response": {
    "RequestId": "abc123",
    "InstanceId": "es-xxxxxx"
  }
}
```

Error responses:

```json
{
  "Response": {
    "RequestId": "abc123",
    "Error": {
      "Code": "InvalidParameterValue",
      "Message": "Parameter node type is invalid"
    }
  }
}
```

## Reference Directory

- [Core Concepts](references/core-concepts.md) — ES architecture, node types, storage hierarchy
- [API & SDK Usage](references/api-sdk-usage.md) — Operation map with request/response examples
- [CLI Usage](references/cli-usage.md) — tccli es command map and invocation patterns
- [Troubleshooting Guide](references/troubleshooting.md) — Error code diagnostics (≥ 12 codes)
- [Monitoring & Alerts](references/monitoring.md) — Metrics, dashboards, Cloud Monitor integration
- [Integration](references/integration.md) — SDK setup, env config, cross-skill delegation
- [Well-Architected Assessment](references/well-architected-assessment.md) — Four-pillar assessment (Tencent Cloud framework)

## Operational Best Practices

- **Least privilege:** CAM policies scoped to required ES APIs only
- **Availability:** Multi-AZ deployment for production clusters; dedicated master nodes for stability
- **Cost:** Right-size node specifications based on workload; use warm/cold tiering for old indices
- **Performance:** Monitor JVM heap usage; set ILM policies for index rollover; force-merge read-only indices
