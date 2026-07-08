---
name: qcloud-cos-ops
description: >-
  Use when the user needs to manage, configure, or operate Tencent Cloud COS
  (Cloud Object Storage) — Bucket lifecycle, object upload/download, storage
  class management, access control, and diagnostics. User mentions COS, 对象存储,
  Object Storage, Bucket, or describes storage-related scenarios (e.g., file
  upload, backup storage, static website hosting) even without naming the
  product directly. Not for billing, CAM, CDN, or related products that have
  their own ops skills.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable) with coscmd
  tool, Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python-cos),
  valid API credentials, network access to Tencent Cloud COS endpoints.
metadata:
  author: qcloud
  version: "1.1.0"
  last_updated: "2026-07-08"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/436"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    tccli cos help confirms CLI support. coscmd tool provides enhanced object
    operations including multipart upload, sync, and batch delete.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

# Tencent Cloud COS Operations Skill

## Overview

COS (Cloud Object Storage) on Tencent Cloud provides scalable, secure, and highly available object storage for unstructured data. Supports multiple storage classes (STANDARD, STANDARD_IA, ARCHIVE), lifecycle management, versioning, and access control via ACL/Bucket Policy. This skill is an **operational runbook** for agents with **dual-path execution** (tccli/coscmd CLI and Python SDK).

> **UX Compliance:** Follows [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md) with minimal prompts and smart defaults.

### CLI applicability

- **`cli_applicability: dual-path`:** tccli for bucket operations; coscmd for object operations.

## Five Core Standards

> See [shared-boilerplate.md](../qcloud-skill-generator/references/shared-skills-boilerplate.md#five-core-standards).

### Well-Architected Framework

| Pillar | Integration |
|--------|-------------|
| **可靠性** | Cross-region replication, versioning, lifecycle backup |
| **安全性** | ACL policies, encryption, bucket policy, access logging |
| **成本** | Storage tier optimization, lifecycle rules, idle bucket detection, **full FinOps analysis via CLI + CLS (see FinOpsAnalysis operation)** |
| **效率** | Multipart upload, batch operations, CDN integration |

## Trigger & Scope

### SHOULD Use

- User mentions "COS" OR "对象存储" OR "Object Storage" OR "Bucket"
- CRUD on buckets: create, describe, delete, configure ACL/policy/lifecycle
- Object operations: upload, download, delete, list, multipart upload
- Storage class management: STANDARD, STANDARD_IA, ARCHIVE, DEEP_ARCHIVE
- Keywords: bucket, object, storage class, multipart upload, lifecycle, versioning
- Keywords: cost analysis, FinOps, cost optimization, cost report, 成本, 费用分析, 成本优化, 节省成本, 成本报告, find savings, analyze costs
- User asks to analyze COS storage cost, request cost, traffic cost, or idle resources
- User asks to generate a COS cost report or identify optimization opportunities

### SHOULD NOT Use

- CDN operations → `qcloud-cdn-ops`
- MySQL/PostgreSQL → `qcloud-cdb-ops` / `qcloud-postgres-ops`
- Billing/account → `qcloud-billing-ops`
- COS access log analysis (audit, troubleshooting, security) → delegate to `qcloud-cls-ops`
- Console-only → State limitation

- Task is **architecture design review** / four-pillar Well-Architected assessment → delegate to: `qcloud-well-architected-review`

### delegate-from: qcloud-proactive-inspection

> **Passively triggered when `{{user.scope}}` includes `cos`.** Read-only COS inspection: ListBuckets → storage analytics → idle detection → cost anomaly flags. See [references/proactive-inspection.md](references/proactive-inspection.md) for delegation contract.

### Delegation Rules

- COS access log analysis → delegate to `qcloud-cls-ops` with bucket name, region, and CLS topic
- COS access logging must be enabled before CLS can analyze logs (see [references/cls-analysis-guide.md](references/cls-analysis-guide.md))
- Proactive inspection (read-only) → invoked by `qcloud-proactive-inspection`; see `references/proactive-inspection.md`
- Well-Architected assessment (read-only) → invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Read-only Well-Architected assessment for **COS**; return `{{output.product_assessment}}`.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | reliability / security / cost / efficiency (or `all`) |
| `{{user.scope}}` | `single-resource` or `account-wide` |

**Allowed:** List/Head/Describe-style read APIs only — **no** Put/Delete bucket or object mutations.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: cos`).

## Variables

| Placeholder | Meaning | Action |
|-------------|---------|--------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | Environment | NEVER ask user |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | Environment | NEVER ask user |
| `{{env.TENCENTCLOUD_REGION}}` | Environment | Use default if allowed |
| `{{user.bucket_name}}` | Bucket name (unique) | Ask once; validate naming |
| `{{user.object_key}}` | Object path | Ask once |
| `{{user.storage_class}}` | STANDARD/STANDARD_IA/ARCHIVE | Ask once; default STANDARD |
| `{{output.bucket_id}}` | `$.Response.Location` | Parse from response |
| `{{output.etag}}` | `$.Response.ETag` | Upload completion verification |
| `{{user.cost_time_range}}` | Cost analysis time window | Ask once; default "30 days ago" |
| `{{user.cost_budget}}` | Monthly budget threshold (¥) | Optional; for budget alerts |
| `{{user.topic_id}}` | CLS topic ID with COS access logs | Inherit from CLS skill; ask if missing |
| `{{output.finops_report_path}}` | Path to generated FinOps report | Generated automatically |

## Quick Start

```bash
# Create bucket
tccli cos PutBucket --Bucket "my-bucket-12345" --Region "{{env.TENCENTCLOUD_REGION}}"

# Upload object (coscmd recommended)
coscmd upload local-file.txt /bucket-name/path/file.txt

# Download object
coscmd download /bucket-name/path/file.txt ./local-file.txt
```

## Capabilities

| Operation | Description | Risk |
|-----------|-------------|------|
| PutBucket | Create bucket | Low |
| GetBucket | List objects | None |
| DeleteBucket | Delete empty bucket | **High** |
| PutObject | Upload object | Low |
| GetObject | Download object | None |
| DeleteObject | Delete object | **High** |
| PutBucketLifecycle | Set lifecycle rules | Medium |
| **FinOpsAnalysis** | **Full COS cost analysis via CLS: storage/request/traffic cost, idle detection, anomaly detection, trend prediction, report** | **None** |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial skill with bucket/object operations, lifecycle/ACL/versioning configuration, FinOpsAnalysis via CLS |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 COS-specific safety rules incl. versioning soft-delete, public ACL, broad-prefix cold transition, batch-delete DryRun), `references/prompt-templates.md` (Generator + Critic + Orchestrator, isolated-context enforcement, secret-content + public-ACL hygiene, FinOpsAnalysis read-only variant). `max_iter=2` per AGENTS.md §8 |

## Execution Flows

### Create Bucket

#### Pre-flight

| Check | Expected | On Failure |
|-------|----------|------------|
| CLI (tccli/coscmd) | Installed | Install |
| Bucket name | RFC 952 compliant (unique) | Ask valid name |
| Region | Valid region code | Suggest valid |
| Quota | ≤ 200 buckets | HALT if exceeded |

#### CLI Execution

**CLI** (`tccli cos PutBucket`): 见 [execution-flows.md §1](references/execution-flows.md#1-createbucket)

**SDK** (Python): 见 [execution-flows.md §1](references/execution-flows.md#1-createbucket)

#### Validation

Parse `$.Response.Location`, verify bucket exists via GetBucket.

#### Failure Recovery

| Error | Action |
|-------|--------|
| `BucketAlreadyExists` | Ask: reuse or new name |
| `InvalidBucketName` | Fix naming (lowercase, no underscore, globally unique) |
| `QuotaExceeded` | HALT; request quota increase |

### Upload Object

#### Pre-flight

| Check | Expected | On Failure |
|-------|----------|------------|
| Bucket exists | GetBucket succeeds | Create bucket first |
| File exists | Local file readable | HALT; check file path |
| Size ≤ 5GB (simple) | Check file size | Use multipart for >5GB |

#### CLI (coscmd)

**CLI** (`coscmd upload`): 见 [execution-flows.md §2](references/execution-flows.md#2-uploadobject)

**SDK** (Python): 见 [execution-flows.md §2](references/execution-flows.md#2-uploadobject)

### Get Object (Download)

#### Pre-flight

| Check | Expected | On Failure |
|-------|----------|------------|
| Bucket exists | GetBucket succeeds | HALT |
| Object exists | HeadObject succeeds | HALT |

#### CLI (coscmd)

**CLI** (`coscmd download`): 见 [execution-flows.md §3](references/execution-flows.md#3-getobject)

**SDK** (Python): 见 [execution-flows.md §3](references/execution-flows.md#3-getobject)

### Delete Object

#### Safety Gate (Mandatory)

1. **MUST** confirm: delete object `{{user.object_key}}` from bucket `{{user.bucket_name}}`
2. **MUST** warn: deletion is irreversible
3. **MUST NOT** proceed without explicit user assent

#### CLI (coscmd)

**CLI** (`coscmd delete`): 见 [execution-flows.md §4](references/execution-flows.md#4-deleteobject)

**SDK** (Python): 见 [execution-flows.md §4](references/execution-flows.md#4-deleteobject)

### List Objects

#### Pre-flight

| Check | Expected | On Failure |
|-------|----------|------------|
| Bucket exists | GetBucket succeeds | Create bucket first |

#### CLI (coscmd)

**CLI** (`coscmd list`): 见 [execution-flows.md §5](references/execution-flows.md#5-listobjects)

**SDK** (Python): 见 [execution-flows.md §5](references/execution-flows.md#5-listobjects)

#### Present to User

| Field | Path | Notes |
|-------|------|-------|
| Object Key | `$.Response.Contents[].Key` | Full object path |
| Size | `$.Response.Contents[].Size` | Size in bytes |
| Last Modified | `$.Response.Contents[].LastModified` | ISO timestamp |
| ETag | `$.Response.Contents[].ETag` | MD5 hash |
| Storage Class | `$.Response.Contents[].StorageClass` | STANDARD/IA/ARCHIVE |

### Delete Bucket

#### Safety Gate (Mandatory)

1. **MUST** check: bucket empty (ListObjects returns empty)
2. **MUST** warn: deletion irreversible
3. **MUST** confirm: user approval with bucket name displayed

#### CLI

**CLI** (`tccli cos DeleteBucket`): 见 [execution-flows.md §6](references/execution-flows.md#6-deletebucket)

**SDK** (Python): 见 [execution-flows.md §6](references/execution-flows.md#6-deletebucket)

### Configure Lifecycle

**CLI** (`tccli cos PutBucketLifecycle`): 见 [execution-flows.md §7](references/execution-flows.md#7-configurelifecycle)

**SDK** (Python): 见 [execution-flows.md §7](references/execution-flows.md#7-configurelifecycle)

---

### FinOpsAnalysis (Full COS Cost Analysis)

Full automated COS FinOps analysis via CLI — collects COS metadata, queries CLS access logs, detects anomalies, identifies idle resources, and generates a structured cost report. **Dual-path**: CLI for metadata collection; CLS queries for cost dimensions.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI install | `tccli cos help` | Exit 0 | Install: `pip install tccli` |
| Credentials | Check `TENCENTCLOUD_SECRET_ID/KEY` env | Non-empty | HALT; configure env |
| Region | `{{env.TENCENTCLOUD_REGION}}` | Valid | Use default ap-guangzhou |
| COS buckets | `tccli cos DescribeBuckets` | ≥ 1 bucket | HALT; no COS resources |
| CLS CLI | `tccli cls help SearchLog` | Exit 0 | Install: `pip install tccli` |
| CLS topic | `tccli cls DescribeTopics --TopicId {{user.topic_id}}` | Topic exists | HALT; need CLS topic with COS logs |

#### Execution — CLI (Primary Path)

**Phase 1: Collect COS Metadata**

**CLI** (5-phase bash): 见 [execution-flows.md §8](references/execution-flows.md#8-finopsanalysis)

**SDK** (Python): 见 [execution-flows.md §8](references/execution-flows.md#8-finopsanalysis)

**Phase 2: Verify CLS COS Log Import**

**CLI** (Phase 2): 见 [execution-flows.md §8](references/execution-flows.md#8-finopsanalysis)

**Phase 3: Execute CLS Cost Queries**

**CLI** (Phase 3 CLS queries): 见 [execution-flows.md §8](references/execution-flows.md#8-finopsanalysis)

**Phase 4: Idle Resource Detection**

**CLI** (Phase 4 idle detection): 见 [execution-flows.md §8](references/execution-flows.md#8-finopsanalysis)

**Phase 5: Generate FinOps Report**

**CLI** (Phase 5 report generation): 见 [execution-flows.md §8](references/execution-flows.md#8-finopsanalysis)

#### Execution — Python SDK (Full Automation)

**SDK** (Python): 见 [execution-flows.md §8](references/execution-flows.md#8-finopsanalysis)

#### Post-execution Validation

1. Verify report file exists and has content: `test -f /tmp/cos-finops-report-*.md`
2. Verify CLS queries returned data (check result count > 0)
3. If no CLS data, produce **lightweight report** using only COS API metadata
4. Validation checklist:

| Check | Pass Criteria | Fallback |
|-------|-------------|----------|
| COS metadata | Buckets list populated | HALT; no data |
| CLS queries | ≥ 1 query returns data | API-only report (no cost breakdown) |
| Idle detection | Results found or confirmed none | Report with 0 idle resources |
| Report generation | .md file created | Print to stdout |

#### Present to User

Present the report path and key highlights:

```
✅ COS FinOps Analysis Complete

Report: /tmp/cos-finops-report-20260531.md

Highlights:
• Buckets analyzed: 5
• Storage cost: ~¥92.41/month (estimate — see finops-cost-optimization.md)
• Top traffic source: 192.168.1.1 (1250.5GB download)
• Anomalies detected: 1 (2026-05-04 storage spike 5.6x baseline)
• Recommendations: 4 (1 P0, 1 P1, 2 P2)

Next steps: Review references/finops-cost-optimization.md for detailed cost breakdown and optimization commands.
```

#### Failure Recovery

| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| No COS buckets | 0 | HALT; no resources to analyze |
| `NoSuchBucket` | 0 | Skip and continue; bucket may have been deleted |
| CLS `TopicNotExist` | 0 | HALT; instruct user to create topic or import COS logs via `qcloud-cls-ops` |
| `AuthFailure` | 0 | HALT; check TENCENTCLOUD_SECRET_ID/KEY |
| CLS query empty | 1 (expand time range) | Produce API-only report (no cost breakdown) |
| `RequestLimitExceeded` | 3, exp backoff | Add delay between queries |
| `InternalError` | 3 (2s,4s,8s) | Skip failed query; continue with remaining |

---

## Error Codes (COS-Specific)

| Code | Meaning | Retry? | Action |
|------|---------|--------|--------|
| `NoSuchBucket` | Bucket not found | No | Verify bucket name |
| `BucketAlreadyExists` | Name taken | No | Ask new name |
| `AccessDenied` | Permission denied | No | Fix ACL/Policy |
| `InvalidBucketName` | Name invalid | No | Use RFC 952 naming |
| `QuotaExceeded` | Bucket quota reached | No | Request increase |
| `EntityTooLarge` | Object >5GB simple upload | No | Use multipart |
| `InvalidDigest` | ETag mismatch | No | Verify content |
| `RequestTimeout` | Upload timeout | Yes (3x) | Retry with smaller chunks |
| `SignatureDoesNotMatch` | Auth invalid | No | Fix credentials |
| `NoSuchKey` | Object not found | No | Verify key path |
| `InvalidStorageClass` | Unknown class | No | Use STANDARD/STANDARD_IA/ARCHIVE |
| `MalformedXML` | Policy malformed | No | Fix JSON/XML format |
| `BucketNotEmpty` | Cannot delete non-empty | No | Delete objects first |
| `InvalidRegion` | Region invalid | No | Use valid region |
| `InternalError` | Server error | Yes (3x) | Retry with RequestId |

## Safety Gates

Every **DeleteBucket/DeleteObject** MUST have:

1. Explicit confirmation with identifier
2. Impact warning (objects will be lost)
3. Empty check for bucket deletion
4. Post-delete verification (poll until 404)

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate
is a **runtime** scoring layer that audits each COS execution against an explicit
rubric, in addition to the build-time **Safety Gates** above and the build-time
**2-round self-review** in [AGENTS.md](../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | [AGENTS.md §8](../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **2** | per-skill override (matches AGENTS.md §8 default for `qcloud-cos-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 COS-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive bucket: `DeleteBucket` (must enumerate live + non-current + DeleteMarkers + incomplete multipart) | **yes** | Irreversible; needs scoring |
| Destructive object: `DeleteObject` (single & batch) on versioning-enabled bucket | **yes** | Soft-delete trap; needs scoring |
| Sensitive mutating: `PutBucketACL` (`public-read` / `public-read-write`), `PutBucketLifecycle` (transition to `ARCHIVE` / `DEEP_ARCHIVE` or `Expiration`) | **yes** | Exfil / cold-transition risk; needs scoring |
| Mutating: `PutBucket`, `PutObject`, multipart `MultiUpload`, `PutBucketPolicy`, `PutBucketCORS`, `PutBucketVersioning`, `PutBucketReplication` | **yes** | Cost / state-change / security risk; needs scoring |
| Read-only: `GetBucket`, `ListObjects`, `HeadObject`, `GetBucketACL`, `GetBucketLifecycle` | optional (max_iter=1, no hard abort) | Polling tails are part of the parent op's trace |
| `FinOpsAnalysis` (read-only, 5 phases) | optional (max_iter=5, no ABORT) | Read-only; lighter scoring per `prompt-templates.md` §4 |

### Decision flow (first match wins)

1. **Safety = 0** OR any rule violation in `{1, 2, 3, 4, 5}` ⇒ **ABORT** (no partial result). Secret-content leak in trace is also an unconditional ABORT.
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

### COS-specific safety rules (rubric §4)

Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | `DeleteObject` (any) on a **versioning-enabled** bucket | Surface versioning status (via `GetBucketVersioning`) before the call; specify `VersionId` to del... |
| 2 | `DeleteBucket` | Bucket must be empty of (a) live objects, (b) non-current versions, (c) DeleteMarkers, (d) incomp... |
| 3 | `PutBucketACL` with `public-read` or `public-read-write` | Surface the full object listing (key paths only, no values) of the bucket to the user before comm... |
| 4 | `PutBucketLifecycle` with `Transition → ARCHIVE` / `DEEP_ARCHIVE` (or `Expiration`) | Show BEFORE/AFTER rule diff; require explicit re-confirmation when (a) the prefix is broad (empty... |
| 5 | Batch delete: `coscmd delete -r`, `coscmd delete -f prefix/`, or any multi-object API call covering >1000 objects | MUST run `coscmd delete --dry-run` (or the SDK equivalent) first and surface the count + a sample... |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — `PutBucketACL public-read` (silent)

| Dimension | Score |
|---|---|
| Correctness | 1 (ACL applied) |
| **Safety** | **0** (rule 3 violated — object enumeration not surfaced; `keys/` and `db-dumps/` likely exposed) |
| Idempotency | 1 |
| Traceability | 1 |
| Spec Compliance | 1 |

`decision: ABORT`. Recovery suggestion emitted: re-read all object keys via `ListObjects`; identify any sensitive prefixes; decide whether to (a) rotate credentials / PII if exposure is suspected, then (b) revert ACL to `private`; (c) use `PutBucketPolicy` for scoped public access to the docs prefix only.

See [`references/rubric.md`](references/rubric.md) §6 for two more examples (PASS on `DeleteObject` and RETRY on `PutBucketLifecycle`).

### Sibling — CVM & CDB Quality Gates

| Skill | Backbone | Distinctive §4 rule |
|---|---|---|
| [`qcloud-cvm-ops`](../qcloud-cvm-ops/SKILL.md#quality-gate-gcl) | 5 dimensions + G/C/O | compute (instances, disks, re-image) |
| [`qcloud-cdb-ops`](../qcloud-cdb-ops/SKILL.md#quality-gate-gcl) | 5 dimensions + G/C/O | database (accounts, privileges, data-plane boundary) |
| `qcloud-cos-ops` (this skill) | 5 dimensions + G/C/O | object storage (versioning, public ACL, cold transition, batch delete) |

---

## Output Schema

```json
{
  "Response": {
    "RequestId": "abc123",
    "Location": "my-bucket-12345.cos.ap-guangzhou.myqcloud.com",
    "Bucket": "my-bucket-12345"
  }
}
```

## Storage Classes

| Class | Name | Use Case | Cost Tier |
|-------|------|----------|-----------|
| STANDARD | 标准存储 | Hot data, frequent access | Highest |
| STANDARD_IA | 低频存储 | Less frequent (>30 days) | Medium |
| ARCHIVE | 影归存储 | Archive (>60 days) | Low |
| DEEP_ARCHIVE | 深度归档 | Long-term archive (>180 days) | Lowest |

## References

- [Core Concepts](references/core-concepts.md)
- [API & SDK](references/api-sdk-usage.md)
- [CLI Usage](references/cli-usage.md)
- [Execution Flows](references/execution-flows.md) — CLI/SDK command blocks (What vs. How separation)
- [Troubleshooting](references/troubleshooting.md)
- [Well-Architected](references/well-architected-assessment.md)
- [Integration](references/integration.md)
- [CLS Analysis Guide](references/cls-analysis-guide.md) — COS access log analysis via CLS
- [FinOps Cost Optimization](references/finops-cost-optimization.md) — CLI-driven cost analysis
- [SecOps Security Operations](references/secops-security-operations.md)
- [AIOps Best Practices](references/aiops-best-practices.md)