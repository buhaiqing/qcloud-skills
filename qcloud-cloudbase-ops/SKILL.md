<!-- TE-1: Query API for dynamic data (regions, envs) — no hardcoded tables -->
<!-- TE-3: Error tables use 3 columns max (Code | Meaning | Action) — see troubleshooting.md -->
<!-- TE-4: JSON paths centralized in API Response table above -->
<!-- TE-6: Pre-flight → Execute → Validate → Recover flows are NOT duplicated in references -->
---
name: qcloud-cloudbase-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud CloudBase (云开发 TCB) — environment lifecycle, cloud database, cloud
  storage, cloud functions, static hosting, auth domains, and API keys. User
  mentions CloudBase, 云开发, TCB, cloudbase, or describes app backend,
  serverless database, static site deployment, or mini-program backend. Not for
  CAM, billing, or compute-only tasks (use qcloud-scf-ops for standalone cloud
  functions).
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "2026-07-20"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/876/36418"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli tcb help` — CLI exposes 80+ operations including
    CreateEnv, DescribeEnvInfo, DeleteEnv, CreateDatabaseACL, DescribeDatabaseACL,
    CreateAuthDomain, DescribeAuthDomains, DeleteAuthDomain, CreateApiKey,
    DescribeApiKeyLists, DeleteApiKey, CreateHostingDomain, DescribeCloudBaseBuildService,
    CreateMySQL, CreateStaticStore, DescribeCurveData, DescribeBillingInfo, and more.
    Python SDK (tencentcloud-sdk-python, module `tencentcloud.tcb.v20180608`) is
    the fallback for edge-case operations not covered by CLI.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
  related_skills:
    - qcloud-scf-ops          # 委托：独立云函数管理（非 CloudBase 托管函数）
    - qcloud-cos-ops          # 委托：COS 对象存储（CloudBase 存储底层依赖）
    - qcloud-cam-ops          # 委托：权限策略配置
    - qcloud-monitor-ops       # 委托：监控告警策略
    - qcloud-cls-ops          # 委托：日志分析
    - qcloud-finops-ops       # 反向：成本优化分析
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud CloudBase (云开发) Operations Skill

## Overview

CloudBase (云开发, TCB) is Tencent Cloud's unified serverless platform providing cloud database (MongoDB-compatible), cloud storage, cloud functions (hosted within CloudBase), static hosting, authentication, and one-click deployment for web and mini-program backends. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **`tccli` CLI** via `tcb` subcommand and **Python SDK fallback**), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

> **UX Compliance:** This skill follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`**: Official `tccli tcb` supports CloudBase. You **MUST** ship **`references/cli-usage.md`** and, in **each** execution flow below, document **both** the SDK step **and** the `tccli` step. CLI is the **primary** execution path; Python SDK is used for edge-case operations CLI doesn't expose.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers (CloudBase, 云开发, TCB) and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented per operation |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps for CLI and SDK paths |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 10 CloudBase-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (CloudBase), primary resource model (Environment); cross-product delegation documented |

Refer to the [meta-skill](../qcloud-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions.

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-environment isolation, database backup, static site CDN, environment disaster recovery | `references/well-architected-assessment.md` |
| **安全性 (Security)** | Auth domains, API keys, database ACL, CAM permissions, network isolation | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Resource point billing, resource package optimization, pay-as-you-go vs plan comparison | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | One-click deployment, CI/CD integration (CloudBase Build Service), static hosting | `references/well-architected-assessment.md` |

See [references/well-architected-assessment.md](references/well-architected-assessment.md) for the complete specification.

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "CloudBase" OR "云开发" OR "TCB" OR "cloudbase"
- Task involves **Environment** lifecycle (CreateEnv, DescribeEnvInfo, ModifyEnv, DeleteEnv)
- Task involves **Database** management (cloud database collections, database ACL rules)
- Task involves **Cloud Storage** (upload, download, delete files in CloudBase storage)
- Task involves **Auth Domains** (whitelist domain for browser access)
- Task involves **API Keys** (manage CloudBase API authentication keys)
- Task involves **Static Hosting** (deploy static sites, manage hosting domains)
- Task involves **CloudBase Build Service** (build and deploy frontend apps)
- Task involves **Billing** info (DescribeBillingInfo, DescribeCurveData for usage metrics)
- Task keywords: mini-program backend, serverless database, static site hosting, cloud storage, one-click deployment, 云端一体化
- User asks to deploy, configure, troubleshoot, or monitor CloudBase **via API, SDK, CLI, or automation**

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: `qcloud-billing-ops` (when present)
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops` (when present)
- Task is **standalone SCF** (not CloudBase-hosted functions) → delegate to: `qcloud-scf-ops`
- Task is **COS** object storage operations outside CloudBase context → delegate to: `qcloud-cos-ops`
- Task is **architecture design review** / four-pillar Well-Architected assessment → delegate to: `qcloud-well-architected-review`
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented HTTP steps

### Delegation Rules

- CloudBase storage is backed by COS: delegate standalone COS operations to `qcloud-cos-ops`
- CloudBase-hosted cloud functions: managed via CloudBase APIs (not standalone SCF APIs)
- Monitoring metrics: use `qcloud-monitor-ops` for alarm policy CRUD; CloudBase provides usage metrics via `DescribeCurveData`
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs into one ambiguous flow

## Variables (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use default `ap-guangzhou` if unset |
| `{{user.env_id}}` | CloudBase environment ID (env-xxxxx) | Ask once; reuse |
| `{{user.env_name}}` | CloudBase environment name | Ask once; reuse |
| `{{user.collection_name}}` | Database collection name | Ask once; reuse |
| `{{user.file_path}}` | Cloud storage file path | Ask once; reuse |
| `{{user.domain}}` | Auth domain / hosting domain | Ask once; reuse |
| `{{user.api_key_id}}` | CloudBase API key ID | Ask once; reuse |
| `{{user.service_id}}` | CloudBase Build Service ID | Ask once; reuse |
| `{{output.request_id}}` | From any API response | Parse `$.Response.RequestId` for tracking |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose `TENCENTCLOUD_SECRET_KEY` in any output. Mask all credentials with `***` or `<masked>`. Check existence only: `test -n "$TENCENTCLOUD_SECRET_KEY"` ✅ | `echo $TENCENTCLOUD_SECRET_KEY` ❌

## API and Response Conventions (Agent-Readable)

- **API spec is canonical** at https://cloud.tencent.com/document/api/876/36418
- **Errors:** Map SDK/HTTP errors to `code` / `message` fields per spec. Tencent Cloud uses `Response.Error` pattern
- **Timestamps:** ISO 8601 format when API returns strings
- **Environment ID format:** `env-` prefix (e.g., `env-5triui5j0c4e`)
- **Async behavior:** Environment creation and some resource provisioning are async — poll DescribeEnvInfo until stable state

### Response Field Table

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| CreateEnv | `$.Response.EnvId` | string | New environment ID (env-xxxxx) |
| DescribeEnvInfo | `$.Response.EnvId` | string | Environment ID |
| DescribeEnvInfo | `$.Response.Status` | string | Environment status (0=正常, -1=未初始化, etc.) |
| DescribeEnvInfo | `$.Response.DatabaseACL` | object | Database access control list |
| DescribeDatabaseACL | `$.Response.ACL` | array | Collection ACL rules |
| DescribeApiKeyLists | `$.Response.ApiKeyList[].SecretKey` | string | API key (masked) |
| DescribeBillingInfo | `$.Response.BillingInfo` | object | Billing details |
| DescribeCurveData | `$.Response.CurveData` | array | Usage metrics over time |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| CreateEnv | — | `0` (正常/RUNNING) | 5s | 300s |
| DeleteEnv | `0` | absent or `Status=-2` | 5s | 300s |

## Quick Start

### What This Skill Does

This skill enables you to deploy, configure, troubleshoot, and monitor CloudBase (云开发) on Tencent Cloud using the `tccli tcb` CLI (primary) or `tencentcloud-sdk-python` SDK (fallback).

### Prerequisites

- [ ] `tccli` CLI installed (or Python 3.8+ runtime for SDK fallback)
- [ ] Credentials configured: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region set: `TENCENTCLOUD_REGION`
- [ ] CloudBase service enabled (use `tccli tcb CheckTcbService` to verify)

### Verify Setup

```bash
# Check CloudBase service status
tccli tcb CheckTcbService --Region {{env.TENCENTCLOUD_REGION}}

# List environments
tccli tcb DescribeEnvInfo --Region {{env.TENCENTCLOUD_REGION}}
```

### Your First Command

```bash
# List all CloudBase environments
tccli tcb DescribeEnvInfo --Region {{env.TENCENTCLOUD_REGION}}
```

### Next Steps

- [Core Concepts](references/core-concepts.md) — Understand CloudBase architecture
- [Common Operations](#execution-flows) — Create, manage, and delete resources
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreateEnv | Create a new CloudBase environment | Medium | Low |
| DescribeEnvInfo | View environment details and status | Low | None |
| ModifyEnv | Update environment configuration | Medium | Medium |
| DeleteEnv | Remove an environment and all resources | Low | **High** — irreversible |
| DescribeDatabaseACL | View database access control rules | Low | None |
| CreateDatabaseACL | Set database collection permissions | Medium | Medium |
| DescribeAuthDomains | List allowed browser domains | Low | None |
| CreateAuthDomain | Add an allowed auth domain | Low | Low |
| DeleteAuthDomain | Remove an auth domain | Low | Medium |
| DescribeApiKeyLists | List API keys | Low | None |
| CreateApiKey | Generate a new API key | Low | Low |
| DeleteApiKey | Revoke an API key | Low | **Medium** — revocation is immediate |
| DescribeBillingInfo | View billing details and resource usage | Low | None |
| DescribeCurveData | Query usage metrics over time | Low | None |
| CreateHostingDomain | Add a custom domain for static hosting | Low | Low |
| DescribeCloudBaseBuildService | Check build service status | Low | None |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-07-20 | Initial release — environment lifecycle, database ACL, auth domains, API keys, billing, static hosting, dual-path (tccli tcb + SDK) |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (SDK/API and `tccli`) → Validate → Recover**. Do not skip phases.

> **Preference hint:** When CLI does not support a specific operation, use Python SDK (`tencentcloud-sdk-python`, module `tencentcloud.tcb.v20180608`) as fallback. CLI is preferred for coverage and simplicity; Python SDK is used for operations CLI does not expose.

### Operation Index

| Operation | Quick Command | Key Notes |
|-----------|---------------|-----------|
| **CreateEnv** | `tccli tcb CreateEnv --Region {{env.TENCENTCLOUD_REGION}} --EnvName "{{user.env_name}}"` | Poll DescribeEnvInfo until Status=0 |
| **DescribeEnvInfo** | `tccli tcb DescribeEnvInfo --Region {{env.TENCENTCLOUD_REGION}}` | Get env list; capture EnvId |
| **ModifyEnv** | `tccli tcb ModifyEnv --Region {{env.TENCENTCLOUD_REGION}} --EnvId "{{user.env_id}}"` | Update env config |
| **DeleteEnv** | `tccli tcb DeleteEnv --Region {{env.TENCENTCLOUD_REGION}} --EnvId "{{user.env_id}}"` | **SAFETY GATE**: Confirm; deletes ALL resources |
| **DescribeDatabaseACL** | `tccli tcb DescribeDatabaseACL --Region {{env.TENCENTCLOUD_REGION}} --EnvId "{{user.env_id}}"` | List ACL rules |
| **CreateDatabaseACL** | `tccli tcb CreateDatabaseACL --Region {{env.TENCENTCLOUD_REGION}} --EnvId "{{user.env_id}}"` | Set collection permissions |
| **DescribeAuthDomains** | `tccli tcb DescribeAuthDomains --Region {{env.TENCENTCLOUD_REGION}} --EnvId "{{user.env_id}}"` | List auth domains |
| **CreateAuthDomain** | `tccli tcb CreateAuthDomain --Region {{env.TENCENTCLOUD_REGION}} --EnvId "{{user.env_id}}"` | Add domain to whitelist |
| **DeleteAuthDomain** | `tccli tcb DeleteAuthDomain --Region {{env.TENCENTCLOUD_REGION}} --EnvId "{{user.env_id}}"` | Remove domain |
| **DescribeApiKeyLists** | `tccli tcb DescribeApiKeyLists --Region {{env.TENCENTCLOUD_REGION}}` | List keys (SecretKey masked) |
| **CreateApiKey** | `tccli tcb CreateApiKey --Region {{env.TENCENTCLOUD_REGION}}` | Returns SecretKey ONCE |
| **DeleteApiKey** | `tccli tcb DeleteApiKey --Region {{env.TENCENTCLOUD_REGION}} --ApiKeyId "{{user.api_key_id}}"` | Revoke key immediately |
| **DescribeBillingInfo** | `tccli tcb DescribeBillingInfo --Region {{env.TENCENTCLOUD_REGION}} --EnvId "{{user.env_id}}"` | View bill + resource usage |
| **DescribeCurveData** | `tccli tcb DescribeCurveData --Region {{env.TENCENTCLOUD_REGION}} --EnvId "{{user.env_id}}"` | Time-series usage metrics |
| **CreateHostingDomain** | `tccli tcb CreateHostingDomain --Region {{env.TENCENTCLOUD_REGION}} --EnvId "{{user.env_id}}"` | Bind custom domain |

### Operation: Create Environment

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Python SDK | `pip show tencentcloud-sdk-python` | Version ≥ minimum | Document install |
| CLI / deps | `tccli version` | Exit code 0 | Document CLI install |
| Credentials | Check env vars: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY` | Non-empty values | HALT; user configures env |
| Region | Call `DescribeEnvInfo` if applicable | `{{user.region}}` supported | Suggest valid region |
| Service enabled | `tccli tcb CheckTcbService --Region {{env.TENCENTCLOUD_REGION}}` | ServiceAvailable | HALT; user enables CloudBase |
| Quota | Query current env count via DescribeEnvInfo | < env quota limit | HALT; user deletes unused envs |

#### Execution — CLI (`tccli tcb`) (Primary Path)

```bash
# Create a CloudBase environment
tccli tcb CreateEnv \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --EnvName "{{user.env_name}}" \
  --Channel "cloudbase" \
  # Optional: --IsVip, --BillingType, --VpcInfo, --PackageType
```

#### Execution — Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
# SDK fallback script for CloudBase CreateEnv
import os
import json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tcb.v20180608 import tcb_client, models

def main():
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = tcb_client.TcbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

    req = models.CreateEnvRequest()
    req.EnvName = os.environ.get("ENV_NAME", "my-env")
    req.Channel = "cloudbase"

    resp = client.CreateEnv(req)
    print(json.dumps(resp.to_json_string(), indent=2))

if __name__ == "__main__":
    main()
```

#### Post-execution Validation

1. Read `{{output.env_id}}` from `$.Response.EnvId`
2. Poll `DescribeEnvInfo` until `Status == 0` (正常):

```bash
for i in $(seq 1 60); do
  STATUS=$(tccli tcb DescribeEnvInfo \
    --Region "{{env.TENCENTCLOUD_REGION}}" \
    --EnvId "{{output.env_id}}" \
    | jq -r '.Response.Status')
  [ "$STATUS" = "0" ] && break
  sleep 5
done
```

3. On success, report `{{output.env_id}}` and env name to the user
4. On terminal failure, go to **Failure Recovery**

#### Failure Recovery

See [`references/troubleshooting.md`](references/troubleshooting.md) § Error Code Reference for complete error taxonomy with retry policies and agent actions. Key patterns:

| Error | Retry? | Action |
|-------|--------|--------|
| `InvalidParameter` / `ResourceNotFound` | No | Fix per API spec |
| `ResourceInsufficient` | No | HALT; request quota |
| `OperationConflict` | Yes (3x) | Wait; retry |
| `RequestLimitExceeded` | Yes (3x) | Exponential backoff |
| `InternalError` | Yes (3x) | Retry; escalate with RequestId |

### Operation: Describe Environment

#### Execution — CLI (`tccli tcb`) (Primary Path)

```bash
# Describe all environments
tccli tcb DescribeEnvInfo --Region "{{env.TENCENTCLOUD_REGION}}"

# Describe a specific environment
tccli tcb DescribeEnvInfo \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --EnvIds '["{{user.env_id}}"]'
```

#### Execution — Python SDK (Fallback Path)

```python
req = models.DescribeEnvInfoRequest()
req.EnvIds = [os.environ.get("ENV_ID")]
resp = client.DescribeEnvInfo(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Present to User

| Field | Path | Notes |
|-------|------|-------|
| EnvId | `$.Response.EnvList[].EnvId` | env-xxxxx format |
| EnvName | `$.Response.EnvList[].EnvName` | Plain text |
| Status | `$.Response.EnvList[].Status` | 0=正常, -1=未初始化, -2=删除中 |
| DatabaseVersion | `$.Response.EnvList[].DatabaseVersion` | MONGO/etc. |
| CreatedTime | `$.Response.EnvList[].CreateTime` | Format ISO per API |

### Operation: Delete Environment

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible delete of `{{user.env_name}}` (`{{user.env_id}}`) — deletes ALL cloud database, storage, functions, and static hosting content
- **MUST NOT** proceed without clear user assent
- **MUST** warn: data loss is permanent

#### Execution — CLI (`tccli tcb`) (Primary Path)

```bash
# Delete environment (all resources deleted)
tccli tcb DeleteEnv \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --EnvId "{{user.env_id}}"
```

#### Post-execution Validation

Poll `DescribeEnvInfo` until env is absent or Status = -2 (删除中→已删除):

```bash
for i in $(seq 1 60); do
  RESULT=$(tccli tcb DescribeEnvInfo \
    --Region "{{env.TENCENTCLOUD_REGION}}" \
    --EnvIds '["{{user.env_id}}"]' \
    | jq -r '.Response.EnvList | length')
  [ "$RESULT" = "0" ] && break
  sleep 5
done
```

### Operation: Manage Database ACL

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Env exists | DescribeEnvInfo with `{{user.env_id}}` | Status = 0 | HALT; create or fix env first |
| Collection name | Ask `{{user.collection_name}}` | Non-empty | Ask user |

#### Execution — CLI (`tccli tcb`) (Primary Path)

```bash
# Describe current ACL for a collection
tccli tcb DescribeDatabaseACL \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --EnvId "{{user.env_id}}"

# Create / update ACL for a collection
tccli tcb CreateDatabaseACL \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --EnvId "{{user.env_id}}" \
  --CollectionName "{{user.collection_name}}" \
  --Acl '{"readOnly": false, "insertOnly": false}'
```

#### ACL Permission Modes

| Mode | Read | Write | Use Case |
|------|------|-------|----------|
| `admin` | All users | All users (admin only) | Internal tools |
| `readOnly` | All users | Admin only | Public data |
| `writeOnly` | Admin only | All users | User-generated content |
| `none` | Admin only | Admin only | Private data |

### Operation: Manage Auth Domains

#### Execution — CLI (`tccli tcb`) (Primary Path)

```bash
# List auth domains
tccli tcb DescribeAuthDomains \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --EnvId "{{user.env_id}}"

# Add an auth domain (whitelist browser access)
tccli tcb CreateAuthDomain \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --EnvId "{{user.env_id}}" \
  --Domain "{{user.domain}}" \
  --Type "web"

# Remove an auth domain
tccli tcb DeleteAuthDomain \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --EnvId "{{user.env_id}}" \
  --Domain "{{user.domain}}"
```

### Operation: Manage API Keys

#### Execution — CLI (`tccli tcb`) (Primary Path)

```bash
# List API keys (SecretKey is masked)
tccli tcb DescribeApiKeyLists --Region "{{env.TENCENTCLOUD_REGION}}"

# Create a new API key (SecretKey returned ONCE — must be saved immediately)
tccli tcb CreateApiKey --Region "{{env.TENCENTCLOUD_REGION}}"

# Delete / revoke an API key
tccli tcb DeleteApiKey \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ApiKeyId "{{user.api_key_id}}"
```

#### Safety Warning

> **SecretKey is shown only once at creation time.** The agent MUST inform the user to save it immediately. The SDK/CLI will never reveal the full SecretKey again.

### Operation: Describe Billing Info

#### Execution — CLI (`tccli tcb`) (Primary Path)

```bash
# View billing details and resource usage for an environment
tccli tcb DescribeBillingInfo \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --EnvId "{{user.env_id}}"

# Query time-series usage metrics (cloud database reads/writes, storage, CDN, etc.)
tccli tcb DescribeCurveData \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --EnvId "{{user.env_id}}" \
  --MetricName "FunctionCallCount" \
  --StartTime "2026-07-01" \
  --EndTime "2026-07-20"
```

### Operation: Static Hosting

#### Execution — CLI (`tccli tcb`) (Primary Path)

```bash
# Create a static hosting domain binding
tccli tcb CreateHostingDomain \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --EnvId "{{user.env_id}}" \
  --Domain "{{user.domain}}"

# Check CloudBase Build Service status
tccli tcb DescribeCloudBaseBuildService \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --EnvId "{{user.env_id}}" \
  --ServiceId "{{user.service_id}}"
```

---

## Error Code Reference

| Code | Meaning | Retry? | Agent Action |
|------|---------|--------|--------------|
| `InvalidParameter` | Parameter validation failed | No | Fix parameter per API spec |
| `InvalidParameterValue` | Parameter value out of range | No | Adjust value per spec |
| `MissingParameter` | Required parameter missing | No | Add missing parameter |
| `ResourceNotFound` | Environment or resource not found | No | Verify EnvId; list resources |
| `ResourceInsufficient` | Quota exceeded | No | HALT; delete unused resources |
| `InvalidSecretKey` | Credential invalid | No | HALT; fix credentials |
| `InvalidSecretId` | Credential ID invalid | No | HALT; fix credentials |
| `RequestLimitExceeded` | API rate limit | Yes (3x) | Exponential backoff |
| `InternalError` | Server error | Yes (3x) | Retry; escalate with RequestId |
| `OperationDenied` | Operation not allowed (e.g., delete in bad state) | No | Wait or check env status |

---

## Safety Gates (Destructive Operations)

Every **DeleteEnv** or irreversible operation MUST have:

1. **Explicit user confirmation** with environment name and ID displayed
2. **Pre-warning** — all data (database, storage, functions, hosting) will be permanently deleted
3. **Dependency check** — warn if environment has active resources
4. **Post-delete verification** — poll until env is absent

---

## Reference Directory

- [Core Concepts](references/core-concepts.md) — Understand CloudBase architecture, billing model, and resource model
- [API & SDK Usage](references/api-sdk-usage.md) — Operation map, required fields, pagination, request/response snippets
- [CLI Usage](references/cli-usage.md) — `tccli tcb` command map, coverage gap table, invocation patterns
- [Troubleshooting Guide](references/troubleshooting.md) — Fix common issues
- [Well-Architected Assessment](references/well-architected-assessment.md) — Four-pillar assessment
- [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md) — Mandatory UX compliance reference
- [Optimization Analysis](../qcloud-skill-generator/references/optimization-analysis.md) — Three-dimensional optimization framework
- [Execution Environment Setup](../qcloud-skill-generator/references/execution-environment.md) — CLI install, Python SDK setup, credential config
- [CLI Behavioral Reference](../qcloud-skill-generator/references/cli-behavior.md) — Verified `tccli` CLI conventions

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。
