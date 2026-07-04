---
name: qcloud-cbs-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud CBS (Cloud Block Storage) — cloud disks, snapshots, and disk lifecycle management.
  User mentions CBS, 云硬盘, cloud disk, 快照, snapshot, disk expansion, disk mounting,
  or describes block storage scenarios (e.g., create disk, attach disk, detach disk,
  resize disk, backup disk, restore snapshot) even without naming the product directly.
  Not for billing, CAM, CVM instance management, VPC operations, or related products
  that have their own ops skills.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python-cbs),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.3.0"
  last_updated: "2026-07-04"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/362"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli cbs help` - CLI exposes CreateDisks, AttachDisks, DetachDisks,
    ResizeDisk, DescribeDisks, DeleteDisks, CreateSnapshot, DeleteSnapshots,
    DescribeSnapshots, ApplySnapshot, CreateAutoSnapshotPolicy, BindAutoSnapshotPolicy,
    and 30+ more operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud CBS Operations Skill

## Overview

CBS (Cloud Block Storage) is Tencent Cloud's persistent block storage service for CVM instances, providing high-performance cloud disks and snapshot backup capabilities. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **`tccli` CLI** and **Python SDK fallback**), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

> **UX Compliance:** This skill follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`**: Official `tccli` fully supports CBS. You **MUST** ship **`references/cli-usage.md`** and, in **each** execution flow below, document **both** the SDK step **and** the `tccli` step. CLI is the **primary** execution path for simplicity; Python SDK is used for edge-case operations CLI doesn't expose or for complex parameter handling.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) per operation |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover |
| 4 | **Complete Failure Strategies** | Error taxonomy with ≥ 12 CBS-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (CBS), primary resource model (Disk) |

Refer to the [meta-skill](../qcloud-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions.

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-AZ disk placement, snapshot backup/restore, disk encryption, auto-snapshot policies | `references/well-architected-assessment.md` |
| **安全性 (Security)** | Disk encryption at rest, CAM permissions for disk operations, snapshot access control | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Disk type selection (CLOUD_PREMIUM vs CLOUD_SSD vs CLOUD_HSSD), snapshot lifecycle management, pay-as-you-go optimization | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Batch disk operations, auto-snapshot scheduling, disk sharing across regions | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "CBS" OR "云硬盘" OR "cloud disk" OR "块存储" OR "block storage"
- Task involves CRUD or lifecycle operations on **Cloud Disks** (CreateDisks, AttachDisks, DetachDisks, ResizeDisk, DeleteDisks, DescribeDisks)
- Task involves **Snapshots** for disk backup/restore (CreateSnapshot, DeleteSnapshots, DescribeSnapshots, ApplySnapshot)
- Task involves **Auto Snapshot Policies** (CreateAutoSnapshotPolicy, BindAutoSnapshotPolicy, ModifyAutoSnapshotPolicy)
- Task keywords: create disk, attach disk, detach disk, mount disk, unmount disk, expand disk, resize disk, backup disk, snapshot, restore snapshot, disk quota
- User asks to deploy, configure, troubleshoot, or monitor CBS **via API, SDK, CLI, or automation**
- User describes disk performance issues (IOPS, throughput) or disk space problems without naming product

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: `qcloud-billing-ops` (when present)
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops` (when present)
- Task is **CVM instance** management (VM lifecycle, SSH access) → delegate to: `qcloud-cvm-ops`
- Task is **VPC network** operations (subnet, route table) → delegate to: `qcloud-vpc-ops`
- Task is **COS object storage** (buckets, objects) → delegate to: `qcloud-cos-ops`
- Task is **architecture design review** / four-pillar Well-Architected assessment → delegate to: `qcloud-well-architected-review`

### Delegation Rules

- CBS disks attach to CVM: verify CVM instance exists via `qcloud-cvm-ops` before AttachDisks
- CBS snapshots can be used for CVM image creation: delegate image operations to `qcloud-cvm-ops`
- CBS disk operations require VPC/Subnet for network-attached storage: verify via `qcloud-vpc-ops`
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs
- Proactive inspection (read-only) → invoked by `qcloud-proactive-inspection`; see `references/proactive-inspection.md`
- Well-Architected assessment (read-only) → invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below
- Disks attached to CVM during architecture review → orchestrator may also dispatch `qcloud-cvm-ops`; this skill covers **standalone CBS** (unattached disks, snapshot policies)

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Read-only Well-Architected assessment for **CBS**; return `{{output.product_assessment}}`.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | reliability / security / cost / efficiency (or `all`) |
| `{{user.scope}}` | `single-resource` or `account-wide` |

**Allowed:** `Describe*` only — **no** Create/Attach/Detach/Delete/Resize mutations.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: cbs`).

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use default `ap-guangzhou` if unset |
| `{{user.zone}}` | User-supplied availability zone | Ask once; reuse (e.g., `ap-guangzhou-3`) |
| `{{user.disk_name}}` | User-supplied disk name | Ask once; reuse |
| `{{user.disk_id}}` | User-supplied disk ID (disk-xxx) | Ask once; reuse for subsequent ops |
| `{{user.disk_size}}` | User-supplied disk size in GB | Ask once; default 50GB for data disk |
| `{{user.disk_type}}` | User-supplied disk type | Ask once; suggest `CLOUD_PREMIUM` |
| `{{user.instance_id}}` | User-supplied CVM instance ID | Ask once; for attach/detach operations |
| `{{user.snapshot_name}}` | User-supplied snapshot name | Ask once; reuse |
| `{{user.snapshot_id}}` | User-supplied snapshot ID (snap-xxx) | Ask once; reuse for restore/delete |
| `{{output.disk_id}}` | From CreateDisks response | Parse `$.Response.DiskIdSet[0]` |
| `{{output.snapshot_id}}` | From CreateSnapshot response | Parse `$.Response.SnapshotId` |
| `{{output.request_id}}` | From any API response | Parse `$.Response.RequestId` for tracking |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose `TENCENTCLOUD_SECRET_KEY` in any output. Mask all credentials with `***` or `<masked>`. Check existence only: `test -n "$TENCENTCLOUD_SECRET_KEY"` ✅ | `echo $TENCENTCLOUD_SECRET_KEY` ❌

## API and Response Conventions (Agent-Readable)

- **API spec is canonical**: https://cloud.tencent.com/document/api/362
- **Errors**: Tencent Cloud uses `Response.Error.Code` / `Response.Error.Message` pattern
- **Timestamps**: ISO 8601 format (e.g., `2026-05-28T10:00:00+08:00`)
- **Idempotency**: Use `ClientToken` for CreateDisks to avoid duplicate creation on retry

### Disk State Definitions

| State | Description | Allowed Operations |
|-------|-------------|-------------------|
| `UNATTACHED` | Disk not attached to any instance | Attach, Delete, Create Snapshot |
| `ATTACHING` | Disk is being attached | Poll only |
| `ATTACHED` | Disk attached to instance | Detach, Resize, Create Snapshot |
| `DETACHING` | Disk is being detached | Poll only |
| `EXPANDING` | Disk is being expanded | Poll only |
| `ROLLBACKING` | Disk is being rolled back | Poll only |
| `TORECYCLE` | Disk pending recycling | Recover or Delete |
| `DUMPING` | Disk data is being exported | Poll only |

### Response Field Summary

| Operation | Key Field | Description |
|-----------|-----------|-------------|
| CreateDisks | `$.Response.DiskIdSet[0]` | New disk ID |
| DescribeDisks | `$.Response.DiskSet[].DiskId/State/Size/Type` | Disk list |
| Attach/Detach/Resize | `$.Response.RequestId` | Tracking ID |
| CreateSnapshot | `$.Response.SnapshotId` | Snapshot ID |
| DescribeSnapshots | `$.Response.SnapshotSet[].SnapshotId/State` | Snapshot list |

### State Transitions

| Operation | Initial → Target | Poll/Max |
|-----------|------------------|----------|
| CreateDisks | — → `UNATTACHED` | 5s/120s |
| Attach/Detach | `UNATTACHED` ↔ `ATTACHED` | 5s/120s |
| ResizeDisk | Same state | 5s/300s |
| CreateSnapshot | — → `NORMAL` | 5s/600s |
| DeleteSnapshots | any → absent | 5s/120s |

## Quick Start

| Env | Setup |
|-----|-------|
| **Cloud Shell** | [Console](https://console.cloud.tencent.com) → Cloud Shell icon. Pre-installed `tccli`/SDK, pre-authenticated, 10GB `/data/`. Limit: 30min idle, 10 sessions, no CI/CD. |
| **Local CLI** | `pip install tccli` + `TENCENTCLOUD_SECRET_ID`/`_KEY`/`_REGION` |
| **Local SDK** | `pip install tencentcloud-sdk-python-cbs` + same credentials |

```bash
# Verify
tccli cbs DescribeDisks --Region {{env.TENCENTCLOUD_REGION}} --Limit 1
```

**Next:** [Core Concepts](references/core-concepts.md) → [Operations](#execution-flows) → [Troubleshooting](references/troubleshooting.md)

## Capabilities at a Glance

| Operation | Risk Level | Notes |
|-----------|------------|-------|
| CreateDisks | Low | — |
| AttachDisks | Low | — |
| DetachDisks | Medium | Data access interruption |
| ResizeDisk | Medium | Requires unmount/remount |
| CreateSnapshot | Low | — |
| DeleteSnapshots | **High** | Irreversible |
| ApplySnapshot | **High** | Data overwrite |
| DescribeDisks | None | Read-only |
| DescribeSnapshots | None | Read-only |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-28 | Initial skill with CreateDisks, AttachDisks, DetachDisks, ResizeDisk, CreateSnapshot, DeleteSnapshots, dual-path execution |
| 1.3.0 | 2026-07-04 | Optimize: compress Quick Start, add SDK templates, compress Capabilities table, remove duplicate Prerequisites, replace inline SDK blocks with template references. Bump version. |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 CBS-specific safety rules incl. disk-destroy irreversibility, detach-without-unmount guard, resize-shrink rejection, snapshot-chain warning, DeleteWithInstance toggle guard), `references/prompt-templates.md` (Generator + Critic + Orchestrator). `max_iter=2` per AGENTS.md §8 |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI and SDK) → Validate → Recover**. Do not skip phases.

### Operation: CreateDisks (Create Cloud Disk)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI install | `tccli version` | Exit 0 | Install: `pip install tccli` |
| Credentials | Check `TENCENTCLOUD_SECRET_ID/KEY` env | Non-empty | HALT; configure env |
| Region | `tccli cbs DescribeDisks --Region {{env.TENCENTCLOUD_REGION}} --Limit 1` | Valid response | HALT; set valid region |
| Zone valid | `tccli cbs DescribeDisks --Filters '[{"Name":"zone","Values":["{{user.zone}}"]}]'` | Zone in region | HALT; use valid zone |
| Disk quota | `tccli cbs DescribeDiskConfigQuota --InquiryType INQUIRY_CBS_CONFIG` | Quota available | HALT; raise quota |

#### Execution — CLI (`tccli`) (Primary Path)

See [execution-flows.md](references/execution-flows.md) §1 CLI.

#### Execution — Python SDK (Fallback Path)

See [execution-flows.md](references/execution-flows.md) §1 SDK.

#### Post-execution Validation

1. Capture `{{output.disk_id}}` from `$.Response.DiskIdSet[0]`
2. Poll DescribeDisks until `UNATTACHED`: see [execution-flows.md](references/execution-flows.md) §1 Validation Poll
3. Report disk ID, size, and type to user

#### Failure Recovery

| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| `InvalidParameter.DiskTypeNotSupported` | 0 | Fix disk type to valid value (CLOUD_PREMIUM, CLOUD_SSD, CLOUD_HSSD) |
| `InvalidParameterValue.DiskSizeNotSupported` | 0 | Check disk size limits (min 20GB, max 32000GB) |
| `ResourceInsufficient.ZoneResourceInsufficient` | 3, 30s | Retry with exponential backoff; HALT if persists |
| `QuotaExceeded.DiskQuota` | 0 | HALT. Request quota increase or delete unused disks |
| `InvalidZone.NotFound` | 0 | HALT. Use valid availability zone |
| `RequestLimitExceeded` | 3, exp backoff | Back off and retry |
| `InternalError` | 3 (2s,4s,8s) | Retry; HALT with RequestId if persists |

---

### Operation: AttachDisks (Attach Disk to CVM)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Disk exists | `tccli cbs DescribeDisks --DiskIds '["{{user.disk_id}}"]'` | Disk found | HALT |
| Disk state | `tccli cbs DescribeDisks --DiskIds '["{{user.disk_id}}"]'` | `UNATTACHED` | HALT; disk already attached |
| CVM exists | Delegate to `qcloud-cvm-ops` DescribeInstances | Instance found | HALT; create CVM first |
| CVM state | Delegate to `qcloud-cvm-ops` | `RUNNING` or `STOPPED` | HALT; wait for stable state |
| Same zone | Compare disk zone and CVM zone | Zones match | HALT; disk and CVM must be in same zone |

#### Execution — CLI (`tccli`) (Primary Path)

See [execution-flows.md](references/execution-flows.md) §2 CLI.

#### Execution — Python SDK (Fallback Path)

See [execution-flows.md](references/execution-flows.md) §2 SDK.

#### Post-execution Validation

1. Poll DescribeDisks until `ATTACHED`: see [execution-flows.md](references/execution-flows.md) §2 Validation Poll

#### Failure Recovery

| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| `InvalidDisk.Attached` | 0 | HALT. Disk already attached to another instance |
| `InvalidDisk.NotFound` | 0 | HALT. Verify disk ID via DescribeDisks |
| `InvalidInstance.NotFound` | 0 | HALT. Verify instance ID via DescribeInstances |
| `InvalidDisk.ZoneMismatch` | 0 | HALT. Disk and instance must be in same zone |
| `LimitExceeded.AttachedDiskQuota` | 0 | HALT. Instance disk quota exceeded |
| `OperationConflict.DiskOperationConflict` | 3, 30s | Retry; another operation in progress |
| `InternalError` | 3 (2s,4s,8s) | Retry; HALT with RequestId if persists |

---

### Operation: DetachDisks (Detach Disk from CVM)

#### Pre-flight (Safety Gate)

- **MUST** warn: detaching disk interrupts data access
- **MUST** confirm: `{{user.disk_id}}`, `{{user.instance_id}}`
- **MUST** suggest: ensure disk is unmounted in OS before detaching to avoid data corruption

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Disk exists | `tccli cbs DescribeDisks --DiskIds '["{{user.disk_id}}"]'` | Disk found | HALT |
| Disk state | `tccli cbs DescribeDisks --DiskIds '["{{user.disk_id}}"]'` | `ATTACHED` | HALT; disk not attached |
| Attached to correct instance | Check InstanceId field | Matches `{{user.instance_id}}` | HALT; disk attached to different instance |

#### Execution — CLI (`tccli`) (Primary Path)

See [execution-flows.md](references/execution-flows.md) §3 CLI.

#### Execution — Python SDK (Fallback Path)

See [execution-flows.md](references/execution-flows.md) §3 SDK.

#### Post-execution Validation

1. Poll DescribeDisks until `UNATTACHED`: see [execution-flows.md](references/execution-flows.md) §3 Validation Poll

#### Failure Recovery

| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| `InvalidDisk.NotAttached` | 0 | HALT. Disk is not attached to any instance |
| `InvalidDisk.NotFound` | 0 | HALT. Verify disk ID |
| `OperationConflict.DiskOperationConflict` | 3, 30s | Retry; another operation in progress |
| `InternalError` | 3 (2s,4s,8s) | Retry; HALT with RequestId if persists |

---

### Operation: ResizeDisk (Expand Disk Capacity)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Disk exists | `tccli cbs DescribeDisks --DiskIds '["{{user.disk_id}}"]'` | Disk found | HALT |
| Current size | Parse from DescribeDisks | Baseline known | — |
| Target size > current | User input validation | Target > Current | HALT; can only expand |
| Disk type supports resize | Check DiskType | Not `LOCAL_BASIC` or `LOCAL_SSD` | HALT; local disks cannot be resized |
| Disk quota | `tccli cbs DescribeDiskConfigQuota` | Capacity available | HALT; request quota increase |

#### Execution — CLI (`tccli`) (Primary Path)

See [execution-flows.md](references/execution-flows.md) §4 CLI.

#### Execution — Python SDK (Fallback Path)

See [execution-flows.md](references/execution-flows.md) §4 SDK.

#### Post-execution Validation

1. Poll DescribeDisks until size matches target: see [execution-flows.md](references/execution-flows.md) §4 Validation Poll
2. **Inform user**: After cloud-side resize, must extend filesystem inside OS using appropriate tools (e.g., `resize2fs` for ext4, `xfs_growfs` for XFS)

#### Failure Recovery

| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| `InvalidParameter.DiskSizeNotSupported` | 0 | HALT. Verify disk size limits |
| `InvalidDisk.NotFound` | 0 | HALT. Verify disk ID |
| `InvalidDisk.ResizeNotSupported` | 0 | HALT. Disk type does not support resizing |
| `InvalidParameterValue.DiskSizeTooSmall` | 0 | HALT. New size must be larger than current |
| `OperationConflict.DiskOperationConflict` | 3, 30s | Retry; another operation in progress |
| `InternalError` | 3 (2s,4s,8s) | Retry; HALT with RequestId if persists |

---

### Operation: CreateSnapshot (Create Disk Backup)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Disk exists | `tccli cbs DescribeDisks --DiskIds '["{{user.disk_id}}"]'` | Disk found | HALT |
| Disk state | `tccli cbs DescribeDisks --DiskIds '["{{user.disk_id}}"]'` | `ATTACHED` or `UNATTACHED` | HALT; disk in transition state |
| Snapshot quota | `tccli cbs DescribeSnapshotQuota` | Quota available | HALT; delete old snapshots |

#### Execution — CLI (`tccli`) (Primary Path)

See [execution-flows.md](references/execution-flows.md) §5 CLI.

#### Execution — Python SDK (Fallback Path)

See [execution-flows.md](references/execution-flows.md) §5 SDK.

#### Post-execution Validation

1. Capture `{{output.snapshot_id}}` from `$.Response.SnapshotId`
2. Poll DescribeSnapshots until `NORMAL`: see [execution-flows.md](references/execution-flows.md) §5 Validation Poll

#### Failure Recovery

| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| `InvalidDisk.NotFound` | 0 | HALT. Verify disk ID |
| `QuotaExceeded.SnapshotQuota` | 0 | HALT. Delete old snapshots or request quota increase |
| `OperationConflict.DiskOperationConflict` | 3, 30s | Retry; disk operation in progress |
| `InternalError` | 3 (2s,4s,8s) | Retry; HALT with RequestId if persists |

---

### Operation: DeleteSnapshots (Delete Disk Snapshots)

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible deletion of `{{user.snapshot_id}}`
- **MUST** warn: snapshot deletion is permanent and cannot be undone
- **MUST NOT** proceed without clear user assent
- **MUST** check: snapshot is not being used for any image creation

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Snapshot exists | `tccli cbs DescribeSnapshots --SnapshotIds '["{{user.snapshot_id}}"]'` | Snapshot found | HALT |
| Not in use | Check SnapshotState and related image info | Not `CREATING` | HALT; wait for completion |

#### Execution — CLI (`tccli`) (Primary Path)

See [execution-flows.md](references/execution-flows.md) §6 CLI.

#### Execution — Python SDK (Fallback Path)

See [execution-flows.md](references/execution-flows.md) §6 SDK.

#### Post-execution Validation

1. Poll DescribeSnapshots until 404 or empty response: see [execution-flows.md](references/execution-flows.md) §6 Validation Poll

#### Failure Recovery

| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| `InvalidSnapshot.NotFound` | 0 | HALT. Snapshot already deleted or invalid ID |
| `InvalidSnapshot.InUse` | 0 | HALT. Snapshot is being used for image creation or other operations |
| `OperationConflict.SnapshotOperationConflict` | 3, 30s | Retry; another operation in progress |
| `InternalError` | 3 (2s,4s,8s) | Retry; HALT with RequestId if persists |



## Reference Directory

### Core References

- [Core Concepts](references/core-concepts.md) — CBS architecture, disk types, performance characteristics
- [API & SDK Usage](references/api-sdk-usage.md) — Operation map, pagination, response schemas
- [CLI Usage Guide](references/cli-usage.md) — `tccli cbs` command reference
- [Troubleshooting Guide](references/troubleshooting.md) — CBS-specific error codes and fixes
- [Monitoring & Alerts](references/monitoring.md) — CBS metrics and alarm configuration
- [Integration](references/integration.md) — Cloud Shell, SDK setup, environment variables

### Well-Architected Framework

- [Well-Architected Assessment](references/well-architected-assessment.md) — Four-pillar assessment (Reliability, Security, Cost, Efficiency)

### FinOps Cost Optimization

- [FinOps Analysis](references/finops-analysis.md) — Cost anomaly detection, disk type optimization, snapshot lifecycle, idle disk analysis

### SecOps Security Operations

- [Audit Rules](references/audit-rules.md) — Audit rules for disk encryption, snapshot access, backup compliance
- [SecOps Checklist](references/secops-checklist.md) — Security audit logs, encryption verification, compliance checklist

### AIOps Intelligent Operations

- [Proactive Inspection](references/proactive-inspection.md) — Five-step closed-loop inspection workflow for CBS
- [AIOps Diagnosis](references/aiops-diagnosis.md) — Delegate to `qcloud-aiops-diagnosis` for disk I/O correlation and cross-layer RCA

## Operational Best Practices

- **Least privilege**: CAM policies scoped to `cbs:*` APIs only
- **Availability**: Use multi-AZ disk placement for high availability
- **Backup**: Regular snapshots with auto-snapshot policies
- **Cost**: Choose appropriate disk type (PREMIUM for standard, SSD/HSSD for high performance)
- **Security**: Enable disk encryption for sensitive data

---

## Error Code Reference (CBS-Specific)

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter` | Generic parameter error | Fix per API spec |
| `InvalidDisk.NotFound` | Disk ID invalid | Verify via DescribeDisks |
| `InvalidDisk.Attached` | Disk already attached | Detach first or use another disk |
| `InvalidDisk.NotAttached` | Disk not attached | Attach before operation |
| `InvalidDisk.ZoneMismatch` | Disk and instance in different zones | Use resources in same zone |
| `InvalidDisk.ResizeNotSupported` | Disk type cannot be resized | Use CLOUD_PREMIUM/SSD/HSSD |
| `InvalidSnapshot.NotFound` | Snapshot ID invalid | Verify via DescribeSnapshots |
| `InvalidSnapshot.InUse` | Snapshot being used for image creation | Wait for completion |
| `InvalidInstance.NotFound` | Instance ID invalid | Verify via DescribeInstances |
| `QuotaExceeded.DiskQuota` | Disk quota exceeded | Request quota increase |
| `QuotaExceeded.SnapshotQuota` | Snapshot quota exceeded | Delete old snapshots |
| `LimitExceeded.AttachedDiskQuota` | Instance disk quota exceeded | Detach unused disks |
| `ResourceInsufficient.ZoneResourceInsufficient` | Zone resource insufficient | Retry or use different zone |
| `OperationConflict.DiskOperationConflict` | Another disk operation in progress | Retry (3x, 30s) |
| `OperationConflict.SnapshotOperationConflict` | Another snapshot operation in progress | Retry (3x, 30s) |
| `RequestLimitExceeded` | API rate limit | Retry (3x, exp backoff) |
| `InternalError` | Server error | Retry (3x); escalate |

---

## Safety Gates (Destructive Operations)

Every **DeleteSnapshots**, **DetachDisks**, **ResizeDisk**, or **irreversible** operation MUST have:

1. **Explicit user confirmation** with disk ID and name displayed
2. **Pre-backup reminder** (snapshot suggestion before destructive operations)
3. **Dependency check** (verify disk not in use, not being backed up)
4. **Post-operation verification** (poll until target state reached)

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate
is a **runtime** scoring layer that audits each CBS execution against an explicit
rubric, in addition to the build-time **Safety Gates** above and the build-time
**2-round self-review** in [AGENTS.md](../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | [AGENTS.md §8](../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **2** | per-skill override (matches AGENTS.md §8 default for `qcloud-cbs-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 CBS-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive: `TerminateDisks`, `DeleteSnapshots`, `ApplySnapshot`, `DetachDisks` (force on running CVM), `ModifyDiskAttributes` (`DeleteWithInstance` toggle) | **yes** | Mostly irreversible or near-irreversible; data-loss or data-corruption risk; needs scoring |
| Mutating: `CreateDisks`, `AttachDisks`, `DetachDisks` (clean), `ResizeDisk` (grow only — shrink blocked by rule 3), `CreateSnapshot`, `ModifyDiskAttributes` (other attrs) | **yes** | Cost / state-change risk; needs scoring |
| Read-only: `DescribeDisks`, `DescribeSnapshots`, `DescribeDiskConfigQuota`, `DescribeSnapshotQuota` | optional (max_iter=1, no hard abort) | Polling tails are part of the parent op's trace |

### Decision flow (first match wins)

1. **Safety = 0** OR rule violation in `{1, 2, 3, 4, 5}` ⇒ **ABORT** (no partial result). Secret-content leak in trace is also an unconditional ABORT.
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

### CBS-specific safety rules (rubric §4)

Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | `TerminateDisks` (destroy) | Disk ID + Name + Size + Status echo; warn that disk destroy is irreversible (snapshot recovery is... |
| 2 | `DetachDisks` (force detach) | Disk ID + attached CVM ID + status echo; warn that detaching a disk attached to a running CVM wit... |
| 3 | `ResizeDisk` (any) | Show current size → target size; warn that CBS resize is EXPAND ONLY (cannot shrink except by cre... |
| 4 | `DeleteSnapshots` (any) | Snapshot ID + Name + Size + CreatedTime + any dependent `ApplySnapshot` references echoed; warn t... |
| 5 | `ModifyDiskAttributes` (changing `DiskName`, `ProjectId`, or `DeleteWithInstance`) | Echo new attributes BEFORE the call; for `DeleteWithInstance` toggle from `FALSE` → `TRUE`: warn ... |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — `ResizeDisk` shrink attempt (ExpandOnly violation)

| Dimension | Score |
|---|---|
| Correctness | 0 (API rejected with `InvalidParameterValue.DiskSizeTooSmall`; agent should have caught this in Pre-flight and never submitted the call) |
| **Safety** | **0** (rule 3 violated — Pre-flight did not enforce the ExpandOnly invariant) |
| Idempotency | 1 |
| Traceability | 1 |
| Spec Compliance | 0 (`core-concepts.md` § "ExpandOnly invariant" was not consulted) |

`decision: ABORT`. Recovery suggestion emitted: reject the shrink request with a clear "CBS does not support shrink — alternative: create a new 50GB disk, copy data with `rsync`, decommission the old one" message; do not submit the `ResizeDisk` call.

See [`references/rubric.md`](references/rubric.md) §6 for two more examples (PASS on `CreateSnapshot` with retention check and SAFETY_FAIL on `TerminateDisks` without snapshot).

---

## Output Schema

Standard Tencent Cloud API response:

```json
{
  "Response": {
    "RequestId": "abc123",
    "DiskIdSet": ["disk-xxx"],
    "SnapshotId": "snap-xxx",
    ...
  }
}
```

Error response:

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
