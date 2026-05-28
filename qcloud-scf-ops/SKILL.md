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
  version: "1.0.0"
  last_updated: "2026-05-28"
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
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented HTTP steps

### Delegation Rules

- SCF integrates with API Gateway: delegate API Gateway configuration to `qcloud-apigw-ops`
- SCF integrates with COS: use `qcloud-cos-ops` for bucket operations when setting up COS triggers
- SCF integrates with CMQ/Ckafka: use relevant skills for message queue trigger configuration
- SCF uses VPC: verify VPC/Subnet via `qcloud-vpc-ops` for VPC-connected functions
- SCF uses Monitor: use `qcloud-monitor-ops` for detailed metrics and alerting setup
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs

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

---

## Execution Flows (Agent-Readable)

### Operation: CreateFunction

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI installed | `tccli scf help CreateFunction` | Exit code 0 | Document CLI install |
| SDK available | `python3 -c "from tencentcloud.scf import scf_client"` | No ImportError | `pip install tencentcloud-sdk-python-scf` |
| Credentials | Check env vars | Non-empty values | HALT; user configures |
| Function name unique | `tccli scf GetFunction --FunctionName {{user.function_name}}` | ResourceNotFound | Suggest alternative name if exists |
| Zip file exists | `test -f {{user.zip_file_path}}` | File exists | HALT; verify path |
| Code size | `stat -f%z {{user.zip_file_path}}` | < 500MB | HALT; reduce package size |

#### Execution — CLI (`tccli`) (Primary Path)

```bash
# Create function with zip package
tccli scf CreateFunction \
  --FunctionName "{{user.function_name}}" \
  --Handler "{{user.handler}}" \
  --Runtime "{{user.runtime}}" \
  --Namespace "{{user.namespace}}" \
  --MemorySize {{user.memory_size}} \
  --Timeout {{user.timeout}} \
  --Code.ZipFile "{{user.zip_file_path}}" \
  --Description "Serverless function deployed via agent" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

#### Execution — Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
"""SDK fallback: SCF CreateFunction"""
import os, json, base64
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.scf import scf_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = scf_client.ScfClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        
        req = models.CreateFunctionRequest()
        req.FunctionName = os.environ.get("FUNCTION_NAME")
        req.Handler = os.environ.get("HANDLER", "index.handler")
        req.Runtime = os.environ.get("RUNTIME", "Python3.8")
        req.MemorySize = int(os.environ.get("MEMORY_SIZE", "512"))
        req.Timeout = int(os.environ.get("TIMEOUT", "30"))
        req.Namespace = os.environ.get("NAMESPACE", "default")
        
        # Read zip file and encode
        with open(os.environ.get("ZIP_FILE_PATH"), "rb") as f:
            zip_content = f.read()
        req.Code = models.Code()
        req.Code.ZipFile = base64.b64encode(zip_content).decode("utf-8")
        
        resp = client.CreateFunction(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

#### Post-execution Validation

1. Read `{{output.function_name}}` from `$.Response.FunctionName`
2. Poll GetFunction until Status = `Active` or timeout (60s):

```bash
for i in $(seq 1 30); do
  STATUS=$(tccli scf GetFunction --Region {{env.TENCENTCLOUD_REGION}} --FunctionName "{{user.function_name}}" | jq -r '.Response.Status')
  [ "$STATUS" = "Active" ] && break
  sleep 2
done

# Check timeout
if [ "$STATUS" != "Active" ]; then
  echo "[ERROR] Timeout waiting for function Active status (current: $STATUS)"
  exit 1
fi
```

3. Report function name and status to user
4. On failure, go to **Failure Recovery**

#### Failure Recovery

| Error pattern | Max retries | Backoff | Agent Action | UX Feedback |
|---------------|-------------|---------|--------------|-------------|
| `InvalidParameter` | 0–1 | — | Fix args per API spec; retry once | `[ERROR] InvalidParameter: Request parameter invalid → Check CreateFunction API spec → Retry` |
| `ResourceInUse` | 0 | — | HALT | `[ERROR] ResourceInUse: Function name already exists → Use unique name → Retry` |
| `ResourceLimitExceeded` | 0 | — | HALT | `[ERROR] ResourceLimitExceeded: Quota exceeded → Request quota increase` |
| `InvalidCode` | 0 | — | HALT | `[ERROR] InvalidCode: Deployment package invalid → Check zip format and handler → Retry` |
| `InvalidSecretKey` / `InvalidSecretId` | 0 | — | HALT | `[ERROR] Credential invalid → Verify env vars → Retry` |
| `OperationConflict` | 3 | 10s | Wait for conflicting op; retry | `⚠️ Another operation in progress → Retrying after completion...` |
| `RequestLimitExceeded` / 429 | 3 | exponential | Back off; respect rate limit | `⚠️ Rate limit reached → Retrying in {backoff}s` |
| `InternalError` / 5xx | 3 | 2s, 4s, 8s | Retry; HALT with RequestId if persists | `[ERROR] InternalError → Retry → Escalate with RequestId: {{output.request_id}}` |

### Operation: UpdateFunctionCode

#### Execution — CLI

```bash
tccli scf UpdateFunctionCode \
  --FunctionName "{{user.function_name}}" \
  --Handler "{{user.handler}}" \
  --Code.ZipFile "{{user.zip_file_path}}" \
  --Namespace "{{user.namespace}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

#### Execution — Python SDK

```python
req = models.UpdateFunctionCodeRequest()
req.FunctionName = os.environ.get("FUNCTION_NAME")
req.Handler = os.environ.get("HANDLER", "index.handler")
with open(os.environ.get("ZIP_FILE_PATH"), "rb") as f:
    req.Code = models.Code()
    req.Code.ZipFile = base64.b64encode(f.read()).decode("utf-8")
resp = client.UpdateFunctionCode(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

1. Poll GetFunction until Status = `Active` (max 60s)
2. Verify `$.Response.CodeSize` changed (indicating new code deployed)
3. Test invoke if possible: `tccli scf Invoke --FunctionName {{user.function_name}}`

#### Failure Recovery

| Error | Max retries | Agent Action | UX Feedback |
|-------|-------------|--------------|-------------|
| `ResourceNotFound` | 0 | HALT | `[ERROR] Function not found → Verify FunctionName` |
| `InvalidCode` | 0 | HALT | `[ERROR] Invalid deployment package → Check zip and handler` |
| `ResourcePreRunning` | 3 | 10s backoff | `⚠️ Function update in progress → Retrying...` |
| `InternalError` | 3 | exponential | `[ERROR] InternalError → Retry → Escalate with RequestId` |

### Operation: DeleteFunction

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible delete of function `{{user.function_name}}`
- **MUST** warn: deletes function and all its triggers
- **MUST** check: no active aliases pointing to this function (or handle alias deletion first)

#### Execution — CLI

```bash
tccli scf DeleteFunction \
  --FunctionName "{{user.function_name}}" \
  --Namespace "{{user.namespace}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

#### Execution — Python SDK

```python
req = models.DeleteFunctionRequest()
req.FunctionName = os.environ.get("FUNCTION_NAME")
req.Namespace = os.environ.get("NAMESPACE", "default")
resp = client.DeleteFunction(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

1. Poll ListFunctions or GetFunction until function returns NotFound (max 60s)
2. Verify associated triggers are cleaned up

#### Failure Recovery

| Error | Max retries | Agent Action | UX Feedback |
|-------|-------------|--------------|-------------|
| `ResourceNotFound` | 0 | HALT | `[ERROR] Function not found → May be already deleted` |
| `ResourceInUse` | 0 | HALT | `[ERROR] Function has active aliases → Delete aliases first` |
| `InternalError` | 3 | exponential | `[ERROR] InternalError → Escalate with RequestId` |

### Operation: PublishVersion

#### Execution — CLI

```bash
# Publish $LATEST as a new version
tccli scf PublishVersion \
  --FunctionName "{{user.function_name}}" \
  --Namespace "{{user.namespace}}" \
  --Description "Version published {{date}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

#### Execution — Python SDK

```python
req = models.PublishVersionRequest()
req.FunctionName = os.environ.get("FUNCTION_NAME")
req.Namespace = os.environ.get("NAMESPACE", "default")
req.Description = f"Published {datetime.now().isoformat()}"
resp = client.PublishVersion(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

1. Read new version number from `$.Response.FunctionVersion`
2. Verify version exists via ListAliases or GetFunction

#### Failure Recovery

| Error | Max retries | Agent Action | UX Feedback |
|-------|-------------|--------------|-------------|
| `ResourceNotFound` | 0 | HALT | `[ERROR] Function not found` |
| `FailedOperation` | 0 | HALT | `[ERROR] Publish failed → Check function is Active` |
| `InternalError` | 3 | exponential | `[ERROR] InternalError → Retry → Escalate` |

### Operation: CreateAlias

#### Execution — CLI

```bash
tccli scf CreateAlias \
  --FunctionName "{{user.function_name}}" \
  --Name "{{user.alias_name}}" \
  --FunctionVersion "{{user.version}}" \
  --Namespace "{{user.namespace}}" \
  --Description "Alias for {{user.alias_name}} environment" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

#### Execution — Python SDK

```python
req = models.CreateAliasRequest()
req.FunctionName = os.environ.get("FUNCTION_NAME")
req.Name = os.environ.get("ALIAS_NAME")
req.FunctionVersion = os.environ.get("FUNCTION_VERSION", "$LATEST")
req.Namespace = os.environ.get("NAMESPACE", "default")
resp = client.CreateAlias(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

1. Read alias info from response
2. Verify alias points to correct version

#### Failure Recovery

| Error | Max retries | Agent Action | UX Feedback |
|-------|-------------|--------------|-------------|
| `ResourceNotFound` | 0 | HALT | `[ERROR] Function not found` |
| `ResourceInUse` | 0 | HALT | `[ERROR] Alias name already exists` |
| `InternalError` | 3 | exponential | `[ERROR] InternalError → Retry → Escalate` |

### Operation: CreateTrigger

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Function exists | `tccli scf GetFunction --FunctionName {{user.function_name}}` | Status = Active | HALT |
| Trigger config valid | Validate per trigger type | Valid config | Fix config |

#### Execution — CLI (Timer Trigger)

```bash
# Create timer trigger (cron expression)
tccli scf CreateTrigger \
  --FunctionName "{{user.function_name}}" \
  --TriggerName "{{user.trigger_name}}" \
  --Type "timer" \
  --TriggerDesc '{"cron": "0 */2 * * * *"}' \
  --Enable "OPEN" \
  --Namespace "{{user.namespace}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

#### Execution — CLI (COS Trigger)

```bash
# Create COS bucket trigger
tccli scf CreateTrigger \
  --FunctionName "{{user.function_name}}" \
  --TriggerName "{{user.trigger_name}}" \
  --Type "cos" \
  --TriggerDesc '{"bucketUrl": "mybucket-{{appid}}.cos.{{region}}.myqcloud.com", "event": "cos:ObjectCreated:*", "filter": {"Prefix": "uploads/", "Suffix": ".jpg"}}' \
  --Enable "OPEN" \
  --Namespace "{{user.namespace}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

#### Execution — Python SDK

```python
req = models.CreateTriggerRequest()
req.FunctionName = os.environ.get("FUNCTION_NAME")
req.TriggerName = os.environ.get("TRIGGER_NAME")
req.Type = os.environ.get("TRIGGER_TYPE")
req.Namespace = os.environ.get("NAMESPACE", "default")
req.Enable = "OPEN"

# TriggerDesc varies by type
trigger_type = os.environ.get("TRIGGER_TYPE")
if trigger_type == "timer":
    req.TriggerDesc = '{"cron": "0 */2 * * * *"}'
elif trigger_type == "cos":
    req.TriggerDesc = '{"bucketUrl": "...", "event": "cos:ObjectCreated:*"}'

resp = client.CreateTrigger(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

1. Read `{{output.trigger_name}}` from `$.Response.TriggerInfo.TriggerName`
2. Poll ListTriggers until trigger appears and is `Enabled`
3. Verify trigger configuration matches expected

#### Failure Recovery

| Error | Max retries | Agent Action | UX Feedback |
|-------|-------------|--------------|-------------|
| `ResourceNotFound` | 0 | HALT | `[ERROR] Function not found` |
| `ResourceInUse` | 0 | HALT | `[ERROR] Trigger name already exists` |
| `InvalidParameterValue` | 0 | HALT | `[ERROR] Invalid trigger configuration → Check TriggerDesc format` |
| `InternalError` | 3 | exponential | `[ERROR] InternalError → Retry → Escalate` |

### Operation: GetFunctionLogs

#### Execution — CLI

```bash
# Get recent function logs
tccli scf GetFunctionLogs \
  --FunctionName "{{user.function_name}}" \
  --Namespace "{{user.namespace}}" \
  --Limit 100 \
  --Order "DESC" \
  --Region {{env.TENCENTCLOUD_REGION}}

# Filter by request ID
tccli scf GetFunctionLogs \
  --FunctionName "{{user.function_name}}" \
  --Namespace "{{user.namespace}}" \
  --FunctionRequestId "{{user.request_id}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

#### Execution — Python SDK

```python
req = models.GetFunctionLogsRequest()
req.FunctionName = os.environ.get("FUNCTION_NAME")
req.Namespace = os.environ.get("NAMESPACE", "default")
req.Limit = int(os.environ.get("LIMIT", "100"))
req.Order = os.environ.get("ORDER", "DESC")

request_id = os.environ.get("REQUEST_ID")
if request_id:
    req.FunctionRequestId = request_id

resp = client.GetFunctionLogs(req)
for log in resp.Data:
    print(f"{log.StartTime} - {log.FunctionName} - {log.Log}")
```

#### Present to User

| Field | JSON Path | Notes |
|-------|-----------|-------|
| RequestId | `$.Response.Data[0].RequestId` | Execution request ID |
| StartTime | `$.Response.Data[0].StartTime` | ISO 8601 timestamp |
| Duration | `$.Response.Data[0].Duration` | Execution time in ms |
| MemoryUsed | `$.Response.Data[0].MemUsage` | Memory consumed |
| Log | `$.Response.Data[0].Log` | Function log output |
| RetCode | `$.Response.Data[0].RetCode` | Return code (0 = success) |

---

## Error Code Reference (SCF-Specific)

| Code | Meaning | Retry? | Agent Action |
|------|---------|--------|--------------|
| `InvalidParameter` | Parameter validation failed | No | Fix parameter; retry with correct value |
| `InvalidParameterValue` | Parameter value out of range | No | Adjust value per API spec |
| `MissingParameter` | Required parameter missing | No | Add missing parameter |
| `ResourceNotFound` | Target function/resource not found | No | Verify name; suggest ListFunctions |
| `ResourceNotFound.Function` | Function does not exist | No | Verify FunctionName; list functions |
| `ResourceInUse` | Function name/trigger already used | No | Use unique name |
| `ResourceLimitExceeded` | Quota exceeded (functions, triggers) | No | HALT; request quota increase |
| `ResourceUnavailable` | Function in operation or unavailable | Yes (3x) | Wait; poll status; retry |
| `FailedOperation` | General operation failure | No | Check function state; verify config |
| `FailedOperation.FunctionStatusError` | Function not in correct state | Yes (3x) | Wait for Active state; retry |
| `FailedOperation.InvokeFunctionFailed` | Function invocation failed | Yes (3x) | Check code; retry invoke |
| `OperationConflict` | Concurrent operation conflict | Yes (3x) | Wait; retry after completion |
| `InvalidSecretKey` / `InvalidSecretId` | Credential invalid | No | HALT; fix credentials |
| `RequestLimitExceeded` | API rate limit exceeded | Yes (3x) | Exponential backoff |
| `InternalError` | Server-side error | Yes (3x) | Retry; escalate with RequestId |
| `InvalidCode` | Deployment package invalid | No | Fix zip file; verify handler |
| `CodeExceeded` | Code package size exceeded | No | Reduce package size (<500MB) |

> **After use:** Verify each code exists in the official SCF API error documentation.

## Safety Gates (Destructive Operations)

Every **DeleteFunction** or irreversible operation MUST have:

1. **Explicit user confirmation** with function name displayed
2. **Pre-check** — verify no active aliases or triggers depend on this function
3. **Dependency check** — warn if triggers will be affected
4. **Post-delete verification** — poll until NotFound (max 60s)

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
