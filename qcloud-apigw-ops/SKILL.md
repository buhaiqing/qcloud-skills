---
name: qcloud-apigw-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or operate Tencent
  Cloud API Gateway (API 网关) — service lifecycle, API definition, release/environment
  management, usage plans, custom domains, IP strategies, and plugins. Covers create/manage
  services and APIs, publish to test/prepub/release environments, bind usage plans and
  secret keys, bind custom sub-domains, and decommission. Triggers on keywords: API 网关,
  apigateway, API Gateway, 服务, 接口, service, API, 发布, release, 使用计划, usage plan,
  自定义域名, custom domain, 限流, rate limit. Not for SCF function code (use
  `qcloud-scf-ops`) or CLB traffic routing (use `qcloud-clb-ops`).
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "2026-07-09"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/product/628"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli apigateway help` (API version 2018-08-08) — CLI exposes
    CreateService, DeleteService, CreateApi, DeleteApi, ModifyApi, ReleaseService,
    UnReleaseService, CreateUsagePlan, BindSecretIds, BindEnvironment, BindSubDomain,
    and 90+ related operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
  gcl: required
  gcl_max_iter: 2
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud API Gateway Operations Skill

## Overview

Tencent Cloud API Gateway (API 网关) provides managed API hosting: **services** group
**APIs**, which are published to **environments** (test / prepub / release) and fronted by
**usage plans**, **secret keys**, **IP strategies**, and **custom domains**. This skill is an
**operational runbook** for agents: explicit scope, credential rules, pre-flight checks,
**dual-path execution** (`tccli apigateway` primary, `tencentcloud-sdk-python` fallback),
response validation, and failure recovery. **Do not use the web console as the primary agent
execution path** in `SKILL.md`.

> **UX Compliance:** This skill follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** `tccli apigateway` covers API Gateway operations. You
  **MUST** ship `references/cli-usage.md` and document **both** the SDK and `tccli` step for
  every operation the CLI exposes.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT with API Gateway triggers; SCF code → `qcloud-scf-ops`, CLB → `qcloud-clb-ops` |
| 2 | **Structured I/O** | `{{env.*}}` for credentials, `{{user.*}}` for config, `{{output.*}}` from API responses |
| 3 | **Explicit Actionable Steps** | Every op: Pre-flight → Execute (CLI + SDK) → Validate → Recover |
| 4 | **Complete Failure Strategies** | ≥ 10 API Gateway-specific error codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | API Gateway service/API/_release management only; backend compute delegated |

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-environment release (test→prepub→release), canary via API-level release, rollback with UnReleaseService | `references/well-architected-assessment.md` |
| **安全性 (Security)** | AuthType (APP/SecretId/OAuth), IP strategy, CAM scoping, credential masking | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Usage-plan rate limits (MaxRequestNum / MaxRequestNumPreSec), waste detection | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Batch API bind, environment strategy, CI/CD release automation | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "API 网关", "apigateway", "API Gateway", "服务", "接口"
- Task: create/manage a service, define APIs, publish to an environment
- Task: create usage plan, bind secret keys, bind environment, bind custom domain
- Keywords: 发布, release, 使用计划, usage plan, 自定义域名, custom domain, 限流, rate limit, IP 策略

### SHOULD NOT Use This Skill When

- Task is **SCF function code** (business logic) → delegate to `qcloud-scf-ops`
- Task is **CLB layer-4/7 routing** → delegate to `qcloud-clb-ops`
- Task is **CAM policy only** → delegate to `qcloud-cam-ops`
- User insists on **console-only** flows with no API → state limitation

### Delegation Rules

- Backend compute (function/business logic) → `qcloud-scf-ops`, `qcloud-cvm-ops`
- Traffic ingress/LB → `qcloud-clb-ops`
- CAM policy for gateway roles → `qcloud-cam-ops`
- Monitoring/alerts → `qcloud-monitor-ops`

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use documented default only if skill allows |
| `{{user.service_name}}` | Service display name | Ask once; reuse |
| `{{user.service_id}}` | Service ID (`service-xxx`) | Ask once; reuse |
| `{{user.api_id}}` | API ID (`api-xxx`) | Ask once; reuse |
| `{{user.environment}}` | `test` / `prepub` / `release` | Ask once; reuse |
| `{{user.sub_domain}}` | Custom domain name | Ask once; reuse |
| `{{output.service_id}}` | From API response | Parse per API spec |
| `{{output.api_id}}` | From API response | Parse per API spec |
| `{{output.usage_plan_id}}` | From API response | Parse per API spec |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose
> `TENCENTCLOUD_SECRET_KEY`, `SecretKey`, or any credential field value in console output,
> debug messages, error messages, or logs.

## JSON Path Reference

| Path | Maps To |
|------|---------|
| `service.id` | `$.Response.ServiceId` |
| `service.name` | `$.Response.ServiceName` |
| `api.id` | `$.Response.ApiId` |
| `api.name` | `$.Response.ApiName` |
| `usage_plan.id` | `$.Response.UsagePlanId` |
| `service.status` | `$.Response.ServiceStatus` (from `DescribeServicesStatus`) |
| `release.version` | `$.Response.Result` / `$.Response.VersionName` |

## Quick Start

### What This Skill Does

Manage Tencent Cloud API Gateway — create services and APIs, publish them to environments,
attach usage plans and secret keys, bind custom domains, and decommission — using
`tccli apigateway` (primary) or `tencentcloud-sdk-python` (fallback).

### Prerequisites

- [ ] `tccli` CLI installed
- [ ] Credentials: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region: `TENCENTCLOUD_REGION`

### Verify Setup

```bash
tccli apigateway DescribeServicesStatus --Region "{{env.TENCENTCLOUD_REGION}}"
```

### Your First Command

```bash
# List existing services
tccli apigateway DescribeServicesStatus --Region "{{env.TENCENTCLOUD_REGION}}"
```

### Next Steps

- [Common Operations](#execution-flows) — Create service, define API, release
- [Troubleshooting](references/troubleshooting.md) — Fix release/API issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreateService | Create an API service | Low | Low |
| CreateApi | Define an API under a service | Medium | Low |
| ReleaseService | Publish service/APIs to an environment | Medium | **High** — affects live traffic |
| CreateUsagePlan | Create a rate-limit/quota plan | Low | Low |
| BindSecretIds | Attach secret keys to a usage plan | Low | Medium |
| BindEnvironment | Bind a usage plan to an environment | Low | Medium |
| BindSubDomain | Bind a custom domain | Medium | Medium |
| ModifyApi | Update an existing API | Medium | Medium |
| DeleteApi | Remove an API | Low | **High** — breaks clients |
| DeleteService | Remove a service and all APIs | Medium | **High** — destroys all APIs |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-07-09 | Initial API Gateway skill: service/API lifecycle, release & environment, usage plan + secret key binding, custom domain, destructive delete guards. Dual-path execution. Delegates SCF/CLB/CAM. |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI and SDK) → Validate → Recover**.

### Operation: Create Service

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Credentials | `test -n "$TENCENTCLOUD_SECRET_ID"` | Non-empty | HALT; user configures env |
| CLI installed | `tccli version` | Exit code 0 | Install tccli |
| Region supported | `tccli apigateway DescribeServicesStatus` | Returns list | Use supported region |
| Service name | User-supplied `{{user.service_name}}` | Non-empty, unique-ish | Ask user |

#### Execution — CLI (`tccli`) (Primary Path)

```bash
tccli apigateway CreateService \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ServiceName "{{user.service_name}}" \
  --Protocol "http&https" \
  --ServiceDesc "{{user.service_desc}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Capture `{{output.service_id}}` from `$.Response.ServiceId`.
2. Poll `DescribeServicesStatus --ServiceIds "[\"{{output.service_id}}\"]"` until the service appears.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `LimitExceeded.ServiceLimitExceeded` | HALT; raise service quota |
| `InvalidParameterValue` | Fix name/protocol per spec |
| `RequestLimitExceeded` | Backoff retry (2s,4s,8s) |

### Operation: Create API

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Service exists | `DescribeServicesStatus --ServiceIds` | Found | Create service first |
| Path unique | `DescribeApisStatus --ServiceId` | No duplicate path+method | Use unique path |

#### Execution — CLI

```bash
tccli apigateway CreateApi \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ServiceId "{{output.service_id}}" \
  --ServiceType "http" \
  --ServiceTimeout 15 \
  --Protocol "HTTP" \
  --ApiName "{{user.api_name}}" \
  --AuthType "NONE" \
  --RequestConfig '{"Path":"/hello","Method":"GET"}' \
  --ServiceConfig '{"Product":"clb","BackendType":"HTTP","Url":"/","Method":"GET"}'
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Capture `{{output.api_id}}` from `$.Response.ApiId`.
2. Poll `DescribeApisStatus --ServiceId "{{output.service_id}}"` until the API appears.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.InvalidService` | Verify `{{user.service_id}}` |
| `LimitExceeded.ApiLimitExceeded` | HALT; raise API quota |
| `InvalidParameterValue` | Fix RequestConfig / ServiceConfig |

### Operation: Release Service (Publish to Environment)

#### Pre-flight (Safety Gate)

- **MUST** confirm target environment (`test` / `prepub` / `release`) with the user.
- **MUST** warn: releasing to `release` routes **live production traffic**.
- **MUST** confirm `ReleaseDesc` (change note) is captured.

#### Execution — CLI

```bash
tccli apigateway ReleaseService \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ServiceId "{{output.service_id}}" \
  --EnvironmentName "{{user.environment}}" \
  --ReleaseDesc "{{user.release_desc}}"
```

#### Post-execution Validation

1. Confirm via `DescribeServiceReleaseVersion --ServiceId "{{output.service_id}}"`.
2. For `release` env, verify health endpoint if available.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.InvalidService` | Verify service ID |
| `FailedOperation.ServiceInUse` | Another release in progress; retry after wait |
| `UnsupportedOperation.ReleasedEnvironment` | Check env state |

### Operation: Create Usage Plan + Bind

#### Execution — CLI

```bash
# Create usage plan (rate limit / quota)
tccli apigateway CreateUsagePlan \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --UsagePlanName "{{user.usage_plan_name}}" \
  --MaxRequestNum 1000000 \
  --MaxRequestNumPreSec 100

# Bind secret keys (AccessKeyIds from CreateApiKey / DescribeApiKeysStatus)
tccli apigateway BindSecretIds \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --UsagePlanId "{{output.usage_plan_id}}" \
  --AccessKeyIds '["{{user.access_key_id}}"]'

# Bind the plan to an environment of the service
tccli apigateway BindEnvironment \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --UsagePlanIds '["{{output.usage_plan_id}}"]' \
  --BindType "SERVICE" \
  --Environment "{{user.environment}}" \
  --ServiceId "{{output.service_id}}"
```

### Operation: Bind Custom Domain

#### Execution — CLI

```bash
tccli apigateway BindSubDomain \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ServiceId "{{output.service_id}}" \
  --SubDomain "{{user.sub_domain}}" \
  --Protocol "https" \
  --NetType "OUTER" \
  --IsDefaultMapping true \
  --NetSubDomain "{{user.sub_domain}}" \
  --CertificateId "{{user.certificate_id}}"
```

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameterValue.CertificateId` | Verify certificate in SSL console → `qcloud-ssl-ops` |
| `ResourceNotFound.InvalidService` | Verify service ID |

### Operation: Modify API

#### Execution — CLI

```bash
tccli apigateway ModifyApi \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ServiceId "{{output.service_id}}" \
  --ApiId "{{output.api_id}}" \
  --ServiceType "http" \
  --RequestConfig '{"Path":"/hello","Method":"POST"}'
```

### Operation: Delete API

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation with `{{user.api_id}}` + service.
- **MUST** warn: deleting an API breaks all clients calling it (returns 404/5xx).

#### Execution — CLI

```bash
tccli apigateway DeleteApi \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ServiceId "{{output.service_id}}" \
  --ApiId "{{output.api_id}}"
```

#### Post-execution Validation

Poll `DescribeApisStatus --ServiceId "{{output.service_id}}"`; expect API absent.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.InvalidApi` | Already removed; treat as success |
| `UnsupportedOperation.ApiInUse` | Unbind usage plans / un-release first |

### Operation: Delete Service

#### Pre-flight (Safety Gate — MANDATORY)

- **MUST** obtain explicit user confirmation with `{{user.service_id}}` + name.
- **MUST** warn: deleting a service destroys **ALL** its APIs and release history.
- **MUST** verify no live `release` bindings / custom domains before delete.
- By default pass `--SkipVerification 0` (keep safety verification ON); only set `1` when the user explicitly accepts skipping.

#### Execution — CLI

```bash
tccli apigateway DeleteService \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ServiceId "{{output.service_id}}" \
  --SkipVerification 0
```

#### Post-execution Validation

Poll `DescribeServicesStatus --ServiceIds "[\"{{output.service_id}}\"]"`; expect service absent.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.InvalidService` | Already removed |
| `UnsupportedOperation.ServiceInUse` | Delete all child APIs / unbind domains first |
| `FailedOperation.ServiceInUse` | Wait for in-flight traffic; retry |

## Error Code Reference (Minimum 10 API Gateway-Specific Codes)

| Code | Meaning | Retry? | Agent Action |
|------|---------|--------|--------------|
| `InvalidParameterValue` | Parameter value invalid | No | Adjust per spec |
| `InvalidParameter` | Parameter validation failed | No | Fix parameter |
| `MissingParameter` | Required parameter missing | No | Add missing parameter |
| `ResourceNotFound.InvalidService` | Service not found | No | Verify service ID |
| `ResourceNotFound.InvalidApi` | API not found | No | Verify API ID |
| `LimitExceeded.ServiceLimitExceeded` | Service quota exceeded | No | HALT; raise quota |
| `LimitExceeded.ApiLimitExceeded` | API quota exceeded | No | HALT; raise quota |
| `UnsupportedOperation.ServiceInUse` | Service has active resources | No | Delete children / unbind first |
| `FailedOperation.ServiceInUse` | Service busy with in-flight op | Yes (3x, 30s) | Wait; retry |
| `InvalidSecretKey` | Credential invalid | No | HALT; fix credentials |
| `RequestLimitExceeded` | API rate limit | Yes (3x) | Exponential backoff |
| `InternalError` | Server error | Yes (3x) | Retry; escalate with RequestId |

## Safety Gates (Destructive Operations)

Every **DeleteApi** / **DeleteService** MUST have:

1. Explicit user confirmation with resource ID + name
2. Verification that the resource is not actively serving live traffic (un-release / unbind first)
3. Pre-warning about client breakage / data loss
4. Post-delete verification (poll until absent)

**ReleaseService** to `release` is semi-destructive (routes production traffic) — always confirm
environment + change note. **DeleteService** keeps `SkipVerification=0` by default.

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | frontmatter `gcl: required` |
| max_iterations | **2** | frontmatter `gcl_max_iter: 2` |
| Rubric instance | `references/rubric.md` | 5 dimensions, API Gateway-specific safety rules |
| Prompt templates | `references/prompt-templates.md` | Generator + Critic + Orchestrator |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | per AGENTS.md §7 |

### When the loop runs

| Operation | Loop required? | Reason |
|---|---|---|
| `CreateService` | Yes | Creates service |
| `CreateApi` | Yes | Creates API |
| `DeleteApi` | Yes (blocking) | Breaks clients |
| `DeleteService` | Yes (blocking) | Destroys all child APIs |
| `ReleaseService` (to `release`) | Yes (blocking) | Routes live traffic |
| `ModifyApi` | Yes | Alters API behavior |
| `Describe*` / `Bind*` | No | Read-only / advisory |

### Decision flow (first match wins)

1. **Safety=0** → `ABORT` — immediate halt, no output
2. **current_iter >= max_iterations** → `MAX_ITER` — return best result, blocking=true
3. **All thresholds met** → `PASS` — output accepted
4. **Otherwise** → `RETRY` — inject suggestions, increment iter

---

## Prerequisites

1. **Install `tccli` CLI:**
```bash
pip install tccli
tccli version
```

2. **Configure Credentials:**
```bash
export TENCENTCLOUD_SECRET_ID="{{env.TENCENTCLOUD_SECRET_ID}}"
export TENCENTCLOUD_SECRET_KEY="{{env.TENCENTCLOUD_SECRET_KEY}}"
export TENCENTCLOUD_REGION="{{env.TENCENTCLOUD_REGION}}"
```

3. **Verify:**
```bash
tccli apigateway DescribeServicesStatus --Region "{{env.TENCENTCLOUD_REGION}}"
```

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [CLI Usage](references/cli-usage.md)
- [Troubleshooting](references/troubleshooting.md)
- [Well-Architected Assessment](references/well-architected-assessment.md)
- [Integration](references/integration.md)
- [SDK Code Examples](references/sdk-code-examples.md)
- [GCL Rubric](references/rubric.md)
- [GCL Prompt Templates](references/prompt-templates.md)
- [Eval Queries](assets/eval_queries.json)
- [Example Configuration](assets/example-config.yaml)
