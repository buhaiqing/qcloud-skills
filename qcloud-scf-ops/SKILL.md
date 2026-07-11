---
name: qcloud-scf-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud SCF (Serverless Cloud Function) - function lifecycle management, version
  control, trigger configuration, layer management, and serverless function diagnostics.
  User mentions SCF, 云函数, Serverless Cloud Function, 函数计算, Lambda, or describes
  function deployment, serverless architecture, event-driven computing, function
  triggers (API Gateway, COS, CMQ, Timer), even without naming the product directly.
  Not for billing, CAM, or container-based serverless (use qcloud-tke-ops for EKS).
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python-scf),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.5.0"
  last_updated: "2026-07-09"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/583"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli scf help` - CLI exposes CreateFunction, UpdateFunction,
    DeleteFunction, GetFunction, ListFunctions, UpdateFunctionCode,
    PublishVersion, DeleteTrigger, CreateTrigger, GetFunctionLogs,
    ListAliases, CreateAlias, DeleteAlias, ListLayers, CreateLayer, and 40+ more operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
  related_skills:
    - qcloud-apigw-ops        # 委托：API Gateway 触发器配置
    - qcloud-cos-ops          # 委托：COS 触发器配置
    - qcloud-ckafka-ops       # 委托：CKafka 触发器配置
    - qcloud-vpc-ops          # 委托：VPC 网络配置
    - qcloud-monitor-ops      # 委托：监控告警策略配置
    - qcloud-cls-ops          # 委托：日志分析查询
    - qcloud-cam-ops          # 委托：权限策略配置
    - qcloud-finops-ops       # 反向：成本优化分析
    - qcloud-tcop-ops         # 反向：资源优化与架构评估
    - qcloud-aiops-diagnosis  # 反向：多指标问题诊断
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud SCF Operations Skill

## Overview

SCF (Serverless Cloud Function) is Tencent Cloud's serverless compute service allowing you to run code without provisioning or managing servers. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **`tccli` CLI** and **Python SDK fallback**), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

> **UX Compliance:** This skill follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`**: Official `tccli` fully supports SCF. You **MUST** ship **`references/cli-usage.md`** and, in **each** execution flow below, document **both** the SDK step **and** the `tccli` step. CLI is the **primary** execution path; Python SDK is used for edge-case operations CLI doesn't expose.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers (SCF, 云函数, Serverless) and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented per operation |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps for CLI and SDK paths |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 12 SCF-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (SCF), primary resource model (Function); cross-product delegation documented |

Refer to the [meta-skill](../qcloud-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions.

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-AZ deployment, auto-scaling, dead letter queues, retry policies | `references/well-architected-assessment.md` |
| **安全性 (Security)** | CAM permissions, VPC networking, environment variable encryption, resource-based policies | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Pay-per-use billing, reserved concurrency optimization, memory tuning | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Event-driven architecture, async invocation, batch processing, CI/CD integration | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "SCF" OR "云函数" OR "Serverless Cloud Function" OR "函数计算" OR "Lambda"
- Task involves CRUD or lifecycle operations on **SCF Functions** (CreateFunction, UpdateFunction, DeleteFunction, GetFunction, ListFunctions)
- Task involves **Function Code Management** (UpdateFunctionCode, GetFunction, download function code)
- Task involves **Version and Alias Management** (PublishVersion, ListAliases, CreateAlias, DeleteAlias)
- Task involves **Triggers** (CreateTrigger, DeleteTrigger, ListTriggers) - API Gateway, COS, CMQ/Ckafka, Timer
- Task involves **Layer Management** (CreateLayer, DeleteLayer, ListLayers, PublishLayerVersion)
- Task involves **Function Logs and Monitoring** (GetFunctionLogs, GetRequestStatus)
- Task involves **Async Invoke Config** (PutProvisionedConcurrencyConfig, DeleteProvisionedConcurrencyConfig)
- Task keywords: deploy function, serverless deployment, function trigger, API Gateway trigger, COS trigger, timer trigger, function version, function alias, function layer, serverless architecture
- User asks to deploy, configure, troubleshoot, or monitor SCF **via API, SDK, CLI, or automation**
- User describes serverless issues (cold start, timeout, memory limits, concurrency) without naming product

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: `qcloud-billing-ops` (when present)
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops` (when present)
- Task is **API Gateway** configuration only → delegate to: `qcloud-apigw-ops` (when present)
- Task is **container-based serverless** (EKS/Serverless containers) → delegate to: `qcloud-tke-ops`
- Task is **long-running batch processing** (>15 minutes execution time) → suggest alternative compute solutions
- Task is **architecture design review** / four-pillar Well-Architected assessment → delegate to: `qcloud-well-architected-review`
- Task is **multi-metric RCA, error/timeout/throttle root cause, cold-start correlation, or cross-layer diagnosis** (SCF + downstream CDB/VPC/API GW) → delegate to: `qcloud-aiops-diagnosis` (read-only); execute fixes via this skill per bundle recommendations — see [`references/aiops-diagnosis.md`](references/aiops-diagnosis.md)

### Delegation Rules

- SCF integrates with API Gateway: delegate API Gateway configuration to `qcloud-apigw-ops`
- SCF integrates with COS: use `qcloud-cos-ops` for bucket operations when setting up COS triggers
- SCF integrates with CMQ/Ckafka: use relevant skills for message queue trigger configuration
- SCF uses VPC: verify VPC/Subnet via `qcloud-vpc-ops` for VPC-connected functions
- SCF uses Monitor: use `qcloud-monitor-ops` for alarm **policy** CRUD; **diagnosis bundling** (Error/Duration/Throttle RCA, Rule O) → `qcloud-aiops-diagnosis` with `{{user.function_name}}`, `{{user.scf_namespace}}`, time window
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs
- Proactive inspection (read-only) → invoked by `qcloud-proactive-inspection`; see `references/proactive-inspection.md`
- Well-Architected assessment (read-only) → invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Read-only Well-Architected assessment for **SCF**; return `{{output.product_assessment}}`.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | reliability / security / cost / efficiency (or `all`) |
| `{{user.scope}}` | `single-resource` or `account-wide` |

**Allowed:** `Describe*`, `GetFunction`, `ListFunctions`, `GetFunctionLogs` — **no** Create/Update/Delete mutations.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: scf`).

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use default `ap-guangzhou` if unset |
| `{{user.function_name}}` | User-supplied function name | Ask once; reuse |
| `{{user.function_id}}` | User-supplied function ID (scf-xxx) | Ask once; reuse |
| `{{user.runtime}}` | Function runtime (Python3.8, Nodejs12.18, etc.) | Ask once; suggest Python3.8 |
| `{{user.handler}}` | Function handler (index.handler) | Ask once; default per runtime |
| `{{user.memory_size}}` | Memory in MB (128-3008) | Ask once; suggest 512 |
| `{{user.timeout}}` | Timeout in seconds (1-900) | Ask once; suggest 30 |
| `{{user.zip_file_path}}` | Path to deployment package zip | Ask once; validate exists |
| `{{user.namespace}}` | Function namespace | Ask once; default "default" |
| `{{user.trigger_name}}` | Trigger name | Ask once; reuse |
| `{{user.trigger_type}}` | Trigger type (timer, cos, cmq, ckafka, apigw) | Ask once |
| `{{user.layer_name}}` | Layer name | Ask once; reuse |
| `{{user.version}}` | Function version ($LATEST, 1, 2, etc.) | Ask once; default $LATEST |
| `{{user.alias_name}}` | Alias name (prod, dev, etc.) | Ask once; reuse |
| `{{output.function_name}}` | From CreateFunction response | Parse `$.Response.FunctionName` |
| `{{output.request_id}}` | From any API response | Parse `$.Response.RequestId` for tracking |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose `TENCENTCLOUD_SECRET_KEY` in any output. Mask all credentials with `***` or `<masked>`. Check existence only: `test -n "$TENCENTCLOUD_SECRET_KEY"` ✅ | `echo $TENCENTCLOUD_SECRET_KEY` ❌

## API and Response Conventions

- **API spec is canonical** for path, query, body fields, enums, and response shapes at https://cloud.tencent.com/document/api/583
- **Errors:** Map SDK/HTTP errors to `code` / `message` fields per spec. Tencent Cloud uses `Response.Error` pattern
- **Timestamps:** ISO 8601 format when API returns strings
- **Async behavior:** Function deployment is async — poll GetFunction until Status = `Active`
- **Function States:** `Pending`, `Active`, `Creating`, `CreateFailed`, `Updating`, `UpdateFailed`, `Publishing`, `Deleting`

### Response Field Table

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| CreateFunction | `$.Response.FunctionName` | string | New function name |
| GetFunction | `$.Response.Status` | string | Function lifecycle state |
| GetFunction | `$.Response.Runtime` | string | Function runtime (Python3.8, etc.) |
| GetFunction | `$.Response.Handler` | string | Handler (index.handler) |
| GetFunction | `$.Response.MemorySize` | integer | Memory in MB |
| GetFunction | `$.Response.Timeout` | integer | Timeout in seconds |
| PublishVersion | `$.Response.FunctionVersion` | string | New version (1, 2, 3, etc.) |
| CreateTrigger | `$.Response.TriggerInfo.TriggerName` | string | Trigger name |
| GetFunctionLogs | `$.Response.Data[].RequestId` | array | Execution request IDs |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| CreateFunction | — | `Active` | 2s | 60s |
| UpdateFunctionCode | any | `Active` | 2s | 60s |
| PublishVersion | any | version published | 2s | 30s |
| DeleteFunction | any | absent | 2s | 60s |
| CreateTrigger | — | `Enabled` | 5s | 60s |
| DeleteTrigger | `Enabled` | absent | 5s | 60s |

## Quick Start

### What This Skill Does

This skill enables you to deploy, configure, troubleshoot, and monitor SCF (Serverless Cloud Function) on Tencent Cloud using the `tccli` CLI (primary) or `tencentcloud-sdk-python-scf` SDK (fallback).

### Prerequisites

- [ ] `tccli` CLI installed (or Python 3.8+ runtime for SDK fallback)
- [ ] Credentials configured: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region set: `TENCENTCLOUD_REGION`
- [ ] Function code prepared (zip file or inline code)

### Verify Setup

```bash
# Check CLI and credentials
tccli scf ListFunctions --Region {{env.TENCENTCLOUD_REGION}} --Namespace default --Limit 1
```

### Your First Command

```bash
# List all SCF functions
tccli scf ListFunctions --Region {{env.TENCENTCLOUD_REGION}} --Namespace default
```

### Next Steps

- [Core Concepts](references/core-concepts.md) — Understand SCF architecture
- [Execution Flows](#execution-flows-agent-readable) — Create, manage, and delete functions
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreateFunction | Deploy a new serverless function | Medium | Low |
| UpdateFunctionCode | Update function code | Low | Low |
| DeleteFunction | Remove a function | Low | **Medium** — irreversible |
| PublishVersion | Create a version from $LATEST | Low | Low |
| CreateAlias | Create a named alias for a version | Low | Low |
| CreateTrigger | Set up event triggers | Medium | Low |
| CreateLayer | Deploy a shared layer | Medium | Low |
| GetFunctionLogs | Query execution logs | Low | None |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-28 | Initial release — function lifecycle, triggers, layers, versions, dual-path |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 SCF-specific safety rules incl. function-delete cascade, trigger disruption, namespace/layer cascade, code update env var overwrite, invocation side effects), `references/prompt-templates.md`. `max_iter=2` per AGENTS.md §8 |
| 1.3.0 | 2026-06-13 | Rule O reverse delegation: `references/aiops-diagnosis.md`; Trigger & Scope aiops delegate for error/timeout/throttle/cold-start RCA |
| 1.4.0 | 2026-07-09 | Added `related_skills` to frontmatter (APIGW, COS, CKafka, VPC, Monitor, CLS, CAM, FinOps, TCOP, AIOps) |
| 1.5.0 | 2026-07-09 | Token Efficiency optimization: SKILL.md compressed from 576→305 lines (47% reduction); AIOps diagnosis expanded with diagnostic matrix, fault pattern correlation, workflow examples |

## Execution Flows (Agent-Readable)

> **Detailed CLI/SDK command blocks:** See [`references/execution-flows.md`](references/execution-flows.md) for complete command examples. Quick commands below.

### Operation Index

| Operation | Quick Command | Key Notes |
|-----------|---------------|-----------|
| **CreateFunction** | `tccli scf CreateFunction --FunctionName "..." --Handler "..." --Runtime "..." --MemorySize 512 --Timeout 30 --Code.ZipFile "..." --Region {{env.TENCENTCLOUD_REGION}}` | Pre-flight: check zip size <500MB; poll for Active status |
| **UpdateFunctionCode** | `tccli scf UpdateFunctionCode --FunctionName "..." --Handler "..." --Code.ZipFile "..." --Region {{env.TENCENTCLOUD_REGION}}` | Verify CodeSize changed; test invoke |
| **DeleteFunction** | `tccli scf DeleteFunction --FunctionName "..." --Namespace "..." --Region {{env.TENCENTCLOUD_REGION}}` | **SAFETY GATE**: Confirm; check aliases/triggers |
| **PublishVersion** | `tccli scf PublishVersion --FunctionName "..." --Description "..." --Region {{env.TENCENTCLOUD_REGION}}` | Version auto-increments |
| **CreateAlias** | `tccli scf CreateAlias --FunctionName "..." --Name "..." --FunctionVersion "..." --Region {{env.TENCENTCLOUD_REGION}}` | Alias → version mapping |
| **CreateTrigger** | `tccli scf CreateTrigger --FunctionName "..." --TriggerName "..." --Type timer --TriggerDesc '{"cron":"..."}' --Enable OPEN --Region {{env.TENCENTCLOUD_REGION}}` | Timer/COS triggers |
| **GetFunctionLogs** | `tccli scf GetFunctionLogs --FunctionName "..." --Limit 100 --Order DESC --Region {{env.TENCENTCLOUD_REGION}}` | Filter by request ID |

### Failure Recovery (Key Patterns)

| Error | Retry? | Action |
|-------|--------|--------|
| `InvalidParameter` / `ResourceNotFound` | No | Fix per API spec |
| `ResourceInUse` | No | Use unique name |
| `ResourceLimitExceeded` | No | HALT; request quota |
| `OperationConflict` | Yes (3x) | Wait 10s; retry |
| `RequestLimitExceeded` | Yes (3x) | Exponential backoff |
| `InternalError` | Yes (3x) | Retry; escalate with RequestId |

---

## Error Code Reference

> **Canonical reference:** See [`references/troubleshooting.md`](references/troubleshooting.md) § Error Code Reference for complete error taxonomy with retry policies and agent actions. Key SCF-specific codes:

| Code | Retry? | Quick Action |
|------|--------|--------------|
| `InvalidParameter` / `InvalidParameterValue` | No | Fix per API spec |
| `ResourceNotFound` | No | Verify name; suggest ListFunctions |
| `ResourceInUse` | No | Use unique name |
| `ResourceLimitExceeded` | No | HALT; request quota increase |
| `OperationConflict` | Yes (3x) | Wait; retry |
| `RequestLimitExceeded` | Yes (3x) | Exponential backoff |
| `InternalError` | Yes (3x) | Retry; escalate with RequestId |
| `InvalidCode` / `CodeExceeded` | No | Fix package; reduce size (<500MB) |

## Safety Gates (Destructive Operations)

Every **DeleteFunction** or irreversible operation MUST have:

1. **Explicit user confirmation** with function name displayed
2. **Pre-check** — verify no active aliases or triggers depend on this function
3. **Dependency check** — warn if triggers will be affected
4. **Post-delete verification** — poll until NotFound (max 60s)

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate
is a **runtime** scoring layer that audits each SCF execution against an explicit rubric,
in addition to the build-time **Safety Gates** above and the build-time **2-round
self-review** in [AGENTS.md](../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

| Property | Value | Source |
|---|---|---|
| GCL applicability | **recommended** | [AGENTS.md §8](../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **3** | per-skill override (AGENTS.md §8 default for `qcloud-scf-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 SCF-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive: `DeleteFunction`, `DeleteNamespace`, `DeleteLayerVersion`, `DeleteFunctionTriggers` | **yes** | Cascade to triggers / dependent functions |
| Sensitive mutating: `UpdateFunctionCode`, `UpdateFunctionConfiguration` (env vars), `InvokeFunction` (Event type) | **yes** | Live side effects; env var overwrite |
| Mutating: `CreateFunction`, `CreateNamespace`, `PublishVersion`, `CreateTrigger` | **yes** | Cost / availability risk |
| Read-only: `GetFunction`, `ListFunctions`, `GetFunctionLogs`, `ListTriggers` | optional (max_iter=1, no hard abort) | Pre-flight for parent mutations |

### Decision flow (first match wins)

1. **Safety = 0** OR rule violation in `{1, 2, 3, 4, 5}` ⇒ **ABORT** (no partial result)
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

### SCF-specific safety rules (rubric §4)

Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | `DeleteFunction` (any version/alias) | Function name + namespace + version count + active trigger count echo; warn that deletion removes... |
| 2 | `DeleteFunctionTriggers` (any) | Trigger type + trigger name + trigger-escaped source ARN echo; warn that removing a trigger stops... |
| 3 | `DeleteNamespace` / `DeleteLayerVersion` | Namespace name / layer name + version echo; for `DeleteNamespace`: warn that ALL functions, layer... |
| 4 | `UpdateFunctionCode` / `UpdateFunctionConfiguration` (code or config change) | Show BEFORE/AFTER diff (for code: `CosBucketName`, `CosObjectName`, `ZipFile`; for config: `Memor... |
| 5 | `InvokeFunction` (with `InvocationType=RequestResponse` or `Event`) | For `InvocationType=Event` (async): warn that the function may not execute immediately and errors... |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — `DeleteFunction` with active API Gateway trigger

| Dimension | Score |
|---|---|
| Correctness | 0.5 (function deleted, but trigger orphan not surfaced) |
| **Safety** | **0** (rule 1 violated — no trigger count echo) |
| Idempotency | 1 |
| Traceability | 0.5 |
| Spec Compliance | 1 |

`decision: ABORT`. Recovery suggestion: "Recreate function + rebind API Gateway trigger; check APIG for 502 errors."

See [`references/rubric.md`](references/rubric.md) §6 for two more examples (PASS on `GetFunction` and RETRY on `UpdateFunctionConfiguration` env var overwrite).

---

## Output Schema

All responses follow Tencent Cloud API structure:

```json
{
  "Response": {
    "RequestId": "abc123",
    "FunctionName": "my-function",
    "FunctionVersion": "1"
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

- [Core Concepts](references/core-concepts.md) — SCF architecture, runtimes, triggers, layers
- [CLI Usage](references/cli-usage.md) — `tccli scf` command map and coverage gaps
- [Troubleshooting Guide](references/troubleshooting.md) — Error codes, diagnostics, common issues
- [Integration](references/integration.md) — CI/CD, API Gateway, COS integration patterns
- [Well-Architected Assessment](references/well-architected-assessment.md) — Serverless best practices
- [Execution Environment Setup](../qcloud-skill-generator/references/execution-environment.md)

## Operational Best Practices

- **Function design:** Keep functions small and focused; single responsibility
- **Cold start:** Minimize initialization code; use provisioned concurrency for latency-sensitive apps
- **Error handling:** Always handle exceptions in function code; use DLQ for failed async invocations
- **Monitoring:** Set up Cloud Monitor alarms for errors, duration, throttles
- **Security:** Store secrets in environment variables (encrypted); use VPC for private resource access
- **Versioning:** Use aliases for deployment stages (dev/test/prod); never invoke $LATEST in production
- **Concurrency:** Configure reserved concurrency for critical functions; understand account concurrency limits
