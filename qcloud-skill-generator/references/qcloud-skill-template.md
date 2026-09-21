# YAML anchor for common frontmatter (TE-5: YAML anchors)
# This anchor is used by all 34 skills to eliminate duplicate frontmatter keys
# Each skill frontmatter should use: `<<: *common_frontmatter`
common_frontmatter: &common_frontmatter
  license: MIT
  compatibility: >-
    Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
    Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python),
    valid API credentials, network access to Tencent Cloud endpoints.
  metadata:
    author: qcloud
    version: "1.0.0"
    last_updated: "2026-08-02"
    runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
    python_version_minimum: "3.8"
    api_profile: "[Paste API version or doc link]"
    cli_applicability: "dual-path"  # Choose: cli-first / dual-path / sdk-only / cli-only
    cli_support_evidence: >-
      [If CLI covers this product: cite confirmation via `tccli cvm help`.
      If CLI does NOT cover: note Python SDK fallback required.]
    environment:
      - TENCENTCLOUD_SECRET_ID
      - TENCENTCLOUD_SECRET_KEY
      - TENCENTCLOUD_REGION

---
name: qcloud-[product-name]-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud [Product Name] — [Resource Type] lifecycle, configuration, and
  diagnostics. User mentions [Product Name], [Product Chinese Name],
  [Product Alias], or describes product-specific scenarios (e.g., connection
  issues, performance degradation, resource creation failures) even without
  naming the product directly. Not for billing, CAM, or related products that
  have their own ops skills.
<<: *common_frontmatter
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud [Product Name] Operations Skill

## Overview

[Product Name] on Tencent Cloud provides [brief description]. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **SDK/API** and, when the product is supported by official **`tccli`**, the matching **CLI** flows), response validation, and failure recovery. **Do not use the web console as the primary agent execution path** in `SKILL.md`.

> **UX Compliance:** This skill follows the [User Experience Specification](../references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: cli-first`:** Official `tccli` fully supports this product. CLI is the **primary** execution path. Python SDK is the **fallback** only for edge-case operations CLI doesn't expose. Omit `references/cli-usage.md` content gaps unless partial coverage exists.
- **`cli_applicability: dual-path`:** Official `tccli` supports this product. You **MUST** ship **`references/cli-usage.md`** and, in **each** execution flow below, document **both** the SDK step **and** the `tccli` step for every operation the CLI exposes. If the CLI covers **only part** of the API, add a **coverage gap** table (SDK-only operations) in `references/cli-usage.md`.
- **`cli_applicability: sdk-only`:** Official `tccli` does **not** expose this product. **Omit** `references/cli-usage.md`. Keep **`cli_support_evidence`** pointing at official proof. SDK/API remains mandatory for all operations.
- **`cli_applicability: cli-only`:** Read-only/discovery skills that ONLY query cloud resources (e.g., `qcloud-topo-discovery`). No write operations, no SDK fallback needed. No `references/cli-usage.md` required beyond basic usage examples.

## Five Core Standards (Quality Gates)

Every generated skill MUST satisfy these five standards. Use them as a design checklist during population:

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 10 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product, one primary resource model; cross-product delegation to other skills |

Refer to the [meta-skill](../SKILL.md#five-core-standards-quality-gates) for detailed descriptions of each standard.

### Well-Architected Framework Integration (卓越架构)

In addition to the Five Core Standards, every generated skill MUST map its operations to Tencent Cloud's Well-Architected Framework four pillars:

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-AZ/region deployment, backup/restore, DR runbook, failure-oriented design | `references/well-architected-assessment.md` |
| **安全性 (Security)** | CAM permissions, credential masking, network isolation, encryption | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Billing model comparison, waste detection, right-sizing, reserved instances | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Batch operations, CI/CD integration, automation patterns, resource scheduling | `references/well-architected-assessment.md` |

See [references/well-architected-assessment.md](references/well-architected-assessment.md) for the complete specification.

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Tencent Cloud [Product Name]" OR "[Product Chinese Name]" OR "[Product Alias]"
- Task involves CRUD or lifecycle operations on **[Resource Type]** (create, describe, modify, delete, list, and product-specific actions)
- Task keywords: [keyword1], [keyword2], [keyword3], …
- User asks to deploy, configure, troubleshoot, or monitor [Product Name] **via API, SDK, CLI, or automation**

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: `qcloud-finops-ops` (when present)
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops` (when present)
- Task is about **[related product]** → delegate to: `qcloud-[other]-ops`
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented HTTP steps

### Delegation Rules

- If resource B depends on resource A, complete or verify A (via the A skill) before B's SDK or CLI steps.
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs into one ambiguous flow.

## Variable Convention (Agent-Readable)

Structured placeholders reduce injection ambiguity and unsafe prompts:

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use documented default only if skill explicitly allows |
| `{{user.region}}` | User-supplied region | Ask once; reuse |
| `{{user.resource_name}}` | User-supplied name | Ask once; reuse |
| `{{output.resource_id}}` | From last API or CLI JSON response | Parse per **API spec** (SDK) or **verified CLI** path for this operation |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> For detailed variable conventions, API response patterns, CLI notes, SDK templates, and execution flow guidance, see [template-guide.md](template-guide.md).

> **Credential Masking**: See [credential-masking.md](credential-masking.md) for full masking rules. Summary: NEVER log/expose credentials; check existence only. Violations block merge.

## API and Response Conventions (Agent-Readable)

- **API spec is canonical** for path, query, body fields, enums, and response shapes. Replace generic JSON paths below with **real** schema field names.
- **Errors:** Map SDK/HTTP errors to `code` / `message` fields per spec. Tencent Cloud uses `Response.Error` pattern.
- **Timestamps:** ISO 8601 format when API returns strings (e.g. `2026-04-28T10:00:00+08:00`).
- **Idempotency:** Document client request tokens, duplicate names, and `ResourceAlreadyExists` behavior per API.

### Example Response Field Table (Replace with API-Accurate Paths)

| Operation | JSON Path (example) | Type | Description |
|-----------|---------------------|------|-------------|
| Create | `$.Response.InstanceId` | string | New resource ID (verify name in spec) |
| Describe | `$.Response.Status` | string | Lifecycle state |
| List | `$.Response.InstanceSet[].InstanceId` | array | IDs (verify array structure) |
| Modify / Delete | `$.Response.RequestId` | string | Request tracking ID |

### Expected State Transitions (Adjust to Product)

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| Create | — | `RUNNING` or product equivalent | 5s | 300s |
| Start | `STOPPED` | `RUNNING` | 5s | 120s |
| Stop | `RUNNING` | `STOPPED` | 5s | 120s |
| Delete | any stable state | absent or `DELETED` per describe | 5s | 300s |

## Quick Start

### What This Skill Does
This skill enables you to deploy, configure, troubleshoot, and monitor [Product Name] resources on Tencent Cloud using the `tccli` CLI (primary) or `tencentcloud-sdk-python` SDK (fallback).

### Prerequisites
- [ ] `tccli` CLI installed (or Python 3.8+ runtime for SDK fallback)
- [ ] Credentials configured: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region set: `TENCENTCLOUD_REGION`

### Verify Setup
```bash
# Check CLI and credentials
tccli cvm DescribeRegions
```

### Your First Command
```bash
# Example: List resources
tccli [product] Describe[Resources] --Region {{env.TENCENTCLOUD_REGION}}
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — Understand [Product Name] architecture
- [Common Operations](#execution-flows) — Create, manage, and delete resources
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Create | Create a new [Resource] | Medium | Low |
| Describe | View [Resource] details | Low | None |
| Modify | Change [Resource] configuration | Medium | Medium |
| Delete | Remove a [Resource] | Low | **High** — irreversible |
| List | View all [Resources] | Low | None |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial API/SDK-oriented template with tccli CLI support |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (SDK/API and, when applicable, `tccli`) → Validate → Recover**. Do not skip phases.

**Preference hint:** When CLI does not support a specific operation, use Python SDK (`tencentcloud-sdk-python`) as fallback. CLI is preferred for coverage and simplicity; Python SDK is used for operations CLI does not expose.

### Operation: Create [Resource]

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Python SDK | `pip show tencentcloud-sdk-python` | Version ≥ minimum | Document install |
| CLI / deps | `tccli version` (**required** when `cli_applicability: cli-first` / `dual-path` / `cli-only`) | Exit code 0 | Document CLI install |
| Credentials | Check env vars: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY` | Non-empty values | HALT; user configures env |
| Region | Call **DescribeRegions** (or equivalent) if applicable | `{{user.region}}` supported | Suggest valid region |
| Quota | Call quota/describe API per API spec | Sufficient quota | HALT; user raises quota |

#### Execution — CLI (`tccli`) (Primary Path)

Use the [Tencent Cloud CLI (tccli)](https://cloud.tencent.com/document/product/440) as the **primary execution path**.

> CLI behavioral notes: see [template-guide.md](template-guide.md#section-3-cli-execution-notes).

```bash
# CLI call (JSON output by default)
tccli [product] Create[Resource] \
  --Region "<region-from-env-or-user>" \
  --[Param1] "<value1>" \
  --[Param2] "<value2>"
  # add parameters per official `tccli [product] help Create[Resource]`
```

#### Execution — Python SDK (Fallback Path)

When `tccli` CLI does not support a specific operation, use `tencentcloud-sdk-python`. See [template-guide.md](template-guide.md#section-4-sdk-fallback-script-template) for the complete SDK fallback script template.

Execute:
```bash
# Install SDK if needed
pip install tencentcloud-sdk-python

# Run script
python3 /tmp/qcloud-sdk-script/create_resource.py
```

#### Post-execution Validation

See [template-guide.md](template-guide.md#section-5-post-execution-validation-pattern) for the full polling pattern (CLI + SDK). Summary: read `{{output.resource_id}}` from documented response path; poll **Describe** until terminal state.
4. On terminal failure, go to **Failure Recovery**.

#### Failure Recovery

| Error pattern (from API/SDK or parsed CLI JSON) | Max retries | Backoff | Agent Action | UX Feedback |
|------------------------------|-------------|---------|--------------|-------------|
| `InvalidParameter` / 400 invalid input | 0–1 | — | Fix args from API spec; retry once if safe | `[ERROR] InvalidParameter: The request parameter is invalid. What happened: One or more parameters do not meet the API specification. How to fix: Check the parameter against API docs and retry. Next step: Review the parameter table above.` |
| `ResourceInsufficient` / `资源不足` | 0 | — | HALT | `[ERROR] ResourceInsufficient: Resource quota limit reached. What happened: Your account has reached the maximum allowed number of this resource type. How to fix: Delete unused resources or request a quota increase. Next step: Contact support or delete unused resources.` |
| `InvalidSecretKey` / `InvalidSecretId` | 0 | — | HALT | `[ERROR] InvalidSecretKey/InvalidSecretId: Credential invalid. What happened: Your API credentials are incorrect or expired. How to fix: Verify TENCENTCLOUD_SECRET_ID and TENCENTCLOUD_SECRET_KEY. Next step: Check environment variables.` |
| `ResourceAlreadyExists` | 0 | — | Ask reuse vs new name | `[ERROR] ResourceAlreadyExists: A resource with this name already exists. What happened: The specified resource name is already in use. How to fix: Use a different name or reuse the existing resource. Next step: Choose a unique name or describe the existing resource.` |
| RequestLimitExceeded / 429 | 3 | exponential | Back off; respect rate limit | `⚠️ Rate limit reached. Retrying in {backoff}s... (Attempt {current}/{max})` |
| `InternalError` / 5xx | 3 | 2s, 4s, 8s | Retry; then HALT with RequestId if any | `[ERROR] InternalError: Server-side error occurred. What happened: Tencent Cloud encountered an internal error processing your request. How to fix: Retry the operation. If it persists, escalate with RequestId. Next step: Retry now or escalate with RequestId: {RequestId}.` |

### Operation: Describe [Resource]

#### Execution

Use the SDK **describe** or **get** API matching API spec. When **`cli_applicability`** is `cli-first` / `dual-path` / `cli-only`, also document the equivalent `tccli [product] Describe[Resource]`, passing `{{user.resource_id}}` and region.

```bash
# CLI — JSON output (default)
tccli [product] Describe[Resource] --Region {{env.TENCENTCLOUD_REGION}} --[IdName] "{{user.resource_id}}"
```

#### Present to User

| Field | Path (example) | Notes |
|-------|----------------|-------|
| ID | `$.Response.InstanceId` | Plain text |
| Name | `$.Response.InstanceName` | Plain text |
| Status | `$.Response.Status` | Human-readable state |
| Created time | `$.Response.CreatedTime` | Format ISO per API |

### Operation: Delete [Resource]

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible delete of `{{user.resource_name}}` (`{{user.resource_id}}`).
- **MUST NOT** proceed without clear user assent.

#### Execution

Call delete API per API spec (skip for `cli-only`). When **`cli_applicability`** is `cli-first` / `dual-path`, also document the `tccli` delete action; capture `RequestId`, success flag, or error per **verified** output shape for **each** path.

#### Post-execution Validation

Poll describe (or head/get) until **404**, **NotFound**, or status indicates deleted—per API semantics—within **max wait**.

### Operation: Backup [Resource]

> **Reliability Pillar:** Following Tencent Cloud Well-Architected Framework, every writable skill MUST document backup and recovery operations.

#### When to Use
- Before any destructive operation (delete, resize, upgrade)
- Scheduled per organizational RPO requirements
- Migration or region transfer prerequisites

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Resource exists | Describe[Resource] with ID | Resource in stable state (RUNNING/AVAILABLE) | HALT — cannot backup non-existent or transitioning resource |
| Backup window | Check current time vs maintenance window | Within allowed backup window | Warn user; proceed with confirmation |
| Storage quota | Describe quota for snapshots/backups | Sufficient backup storage | HALT — user must free space or raise quota |

#### Execution — CLI (`tccli`) (Primary Path)

```bash
# Create backup/snapshot (adjust per product API)
tccli [product] Create[Backup/Snapshot] \
  --[ResourceIdName] "{{user.resource_id}}" \
  --[SnapshotName] "auto-backup-$(date +%Y%m%d-%H%M%S)"
```

#### Execution — Python SDK (Fallback Path)

```python
req = models.Create[Snapshot]Request()
req.[InstanceId] = os.environ.get("INSTANCE_ID")
req.[SnapshotName] = "auto-backup-" + datetime.now().strftime("%Y%m%d-%H%M%S")
resp = client.Create[Snapshot](req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

1. Capture `{{output.backup_id}}` from response (`$.Response.SnapshotId`)
2. Poll backup status until terminal state (`SUCCESS`/`COMPLETED`):

```bash
# Poll snapshot status
for i in $(seq 1 60); do
  STATUS=$(tccli [product] Describe[Snapshots] --SnapshotIds "[{{output.backup_id}}]" | jq -r '.Response.SnapshotSet[0].Status')
  [ "$STATUS" = "SUCCESS" ] && break
  sleep 10
done
```

#### Failure Recovery

| Error pattern | Max retries | Agent Action | UX Feedback |
|--------------|-------------|--------------|-------------|
| `OperationConflict` | 3, 30s backoff | Wait for conflicting operation; retry | `⚠️ Another operation is in progress. Retrying after completion...` |
| `QuotaExceeded.Snapshot` | 0 | HALT | `[ERROR] Backup quota exceeded. How to fix: Delete old backups or raise quota.` |
| `InvalidResourceStatus` | 0 | HALT | `[ERROR] Resource not in a backup-ready state. How to fix: Wait for resource to reach stable state.` |

---

### Operation: Restore from Backup

> **Reliability Pillar — Emergency Recovery:** Follow the Phase 1 → Phase 2 → Phase 3 runbook structure per `well-architected-assessment.md`.

#### Pre-flight (Safety Gate)

- **MUST** warn user: restore overwrites current data; suggest pre-restore backup
- **MUST** confirm: target resource `{{user.resource_id}}`, backup source `{{user.backup_id}}`, expected data loss window

#### Execution — CLI (`tccli`) (Primary Path)

```bash
# Restore from backup (adjust per product API)
tccli [product] Restore[Resource] \
  --[ResourceIdName] "{{user.resource_id}}" \
  --[BackupIdName] "{{user.backup_id}}"
```

#### Post-execution Validation

1. Poll restore operation until terminal state
2. **Recovery verification:** run connectivity check against restored resource
3. Verify data integrity: compare row counts, checksums, or product-specific validation
4. Document actual recovery time vs RTO target

---

## Prerequisites

For complete Prerequisites: `tccli` install, Python runtime setup, credential configuration, and verification — see [execution-environment.md](execution-environment.md). All credentials use `{{env.*}}` placeholders; never commit `.env` to version control.

**One-line verify**: `tccli cvm DescribeZones --Region ap-guangzhou` returns JSON ⇒ environment ready.

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [CLI Usage](references/cli-usage.md) (**required** when `cli_applicability: cli-first` or `dual-path`; omit for `sdk-only`; basic examples for `cli-only`)
- [Troubleshooting Guide](references/troubleshooting.md)
- [Monitoring & Alerts](references/monitoring.md)
- [Integration](references/integration.md)
- [Knowledge Base](references/knowledge-base.md) — fault pattern library (AIOps diagnostic skills)
- [Observability Integration](references/observability.md) — Metrics/Logs/Traces linkage (AIOps diagnostic skills)
- [User Experience Specification](references/user-experience-spec.md) — mandatory UX compliance reference
- [AIOps Best Practices](references/aiops-best-practices.md) — mandatory AIOps patterns for monitoring/diagnosis skills
- [Optimization Analysis](references/optimization-analysis.md) — three-dimensional optimization framework
- [Execution Environment Setup](references/execution-environment.md) — CLI install, Python SDK setup, credential config, verification
- [CLI Behavioral Reference](references/cli-behavior.md) — verified `tccli` CLI conventions (JSON output, env vars, invocation patterns)
- [Enhanced Self-Healing Framework](references/enhanced-self-healing-framework.md) — **MANDATORY** self-healing patterns for all installation flows
- [Well-Architected Assessment](references/well-architected-assessment.md) — **MANDATORY** Tencent Cloud Well-Architected Framework four-pillar integration

## Operational Best Practices

- **Least privilege:** CAM policies scoped to required APIs only.
- **Availability:** Multi-AZ or product-specific HA patterns per docs.
- **Cost:** Right-size resources; use product cost controls where applicable.

---

## Error Code Reference (Minimum 10 Product-Specific Codes)

> **MANDATORY:** Fill this table with **actual** error codes from the product's API documentation.

| Code | Meaning | Retry? | Agent Action |
|------|---------|--------|--------------|
| `InvalidParameter` | Parameter validation failed | No | Fix parameter; retry with correct value |
| `InvalidParameterValue` | Parameter value out of range | No | Adjust value per spec |
| `MissingParameter` | Required parameter missing | No | Add missing parameter |
| `ResourceNotFound` | Target resource not found | No | Verify resource ID; suggest Describe |
| `ResourceInsufficient` | Quota exceeded | No | HALT; suggest quota increase |
| `InvalidSecretKey` | Credential invalid | No | HALT; fix credentials |
| `InvalidSecretId` | Credential ID invalid | No | HALT; fix credentials |
| `RequestLimitExceeded` | API rate limit | Yes (3x) | Exponential backoff |
| `InternalError` | Server error | Yes (3x) | Retry; escalate with RequestId |
| `OperationConflict` | Concurrent operation conflict | Yes (3x, 30s) | Wait; retry |

> **After population:** Verify each code exists in the official API error documentation for this product.

---

## Safety Gates (Destructive Operations)

Every **Delete**, **Terminate**, or **irreversible** operation MUST have:

1. **Explicit user confirmation** with resource identifier displayed
2. **Pre-backup reminder** (product-specific: snapshot, backup, export)
3. **Dependency check** (warn if resource has active connections/attachments)
4. **Post-delete verification** (poll until 404 or deleted state)

---

## Quality Gate (GCL)

> **Required when:** this skill is GCL `required` or `recommended` per [AGENTS.md §10.8](../../AGENTS.md#8-per-skill-defaults-qcloud). Defaults: any product with destructive operations (Terminate / Delete / Drop / Destroy / Reset) is `required` and `max_iter=2`. Read-only / advisory skills are `optional` and may skip this section.

This skill participates in the **Generator-Critic-Loop (GCL)** pilot ([AGENTS.md §10](../../AGENTS.md#10-generator-critic-loop-gcl--adversarial-quality-gate)). Every mutation executes through `scripts/gcl_runner.py run` with an isolated-context Critic scoring 5 dimensions (correctness / safety / idempotency / traceability / spec_compliance). Safety = 0 ⇒ ABORT.

| Item | Value |
|---|---|
| GCL applicability | `required` / `recommended` / `optional` (per AGENTS.md §8) |
| `max_iterations` | `2` (required) / `3` (recommended) / `5` (optional) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

> **Prompt-context isolation (mandatory):** Generator and Critic run in **isolated** prompt contexts (sub-agent or fresh conversation). Critic MUST NOT see the raw user request — only `{{output.generator_output}}` + `{{output.trace}}`. See `references/prompt-templates.md` §2 for the Critic skeleton.

---

## Output Schema

All responses follow Tencent Cloud API structure:

```json
{
  "Response": {
    "RequestId": "abc123",
    "[ResourceId]": "ins-xxx",
    // Product-specific fields
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

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。