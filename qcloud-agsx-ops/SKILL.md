---
name: qcloud-agsx-ops
description: >-
  Use when the user asks to operate Tencent Cloud Agent Sandbox (AGSX / Agent Runtime), including creating, describing, updating, or deleting sandbox tools and sandbox instances; managing API keys; integrating with e2b-code-interpreter SDK; troubleshooting sandbox startup failures, quota errors, or connection issues; or performing well-architected assessments on agent sandbox deployments. Covers browser sandboxes, code sandboxes, and custom sandboxes. Activates on keywords: AGSX, Agent Runtime, agent sandbox, 代码沙箱, 浏览器沙箱, 沙箱实例, sandbox tool, sandbox instance, e2b sandbox, tencentags. Triggers on API names: CreateSandboxTool, DescribeSandboxToolList, UpdateSandboxTool, DeleteSandboxTool, StartSandboxInstance, DescribeSandboxInstanceList, StopSandboxInstance, CreateAPIKey, DeleteAPIKey, CreatePreCacheImageTask.
license: Apache-2.0
compatibility: >-
  Python 3.8+ runtime (for SDK with tencentcloud-sdk-python >= 3.0.1300),
  valid API credentials, network access to ags.tencentcloudapi.com.
metadata:
  author: qcloud
  version: "1.1.0"
  last_updated: "2026-06-04"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "2025-09-20"
  cli_applicability: "sdk-only"
  cli_support_evidence: >-
    tccli does not ship an `ags` subcommand as of 2026-05-28.
    Verified via `tccli ags help` returning "Invalid product".
    All operations require tencentcloud-sdk-python (ags module).
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
    - E2B_API_KEY
    - E2B_DOMAIN
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud AGSX (Agent Sandbox) Operations Skill

## Overview

Tencent Cloud Agent Runtime (AGSX) is a serverless sandbox service for AI Agent code execution and browser automation. AGSX provides 100ms cold start, 24-hour max lifecycle, and full e2b-protocol compatibility. Sandbox instances are created only via API/SDK/MCP (console is read-only).

This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **SDK-first execution** (tccli does not support this product), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

**Product page**: https://cloud.tencent.com/product/agsx
**API docs**: https://cloud.tencent.com/document/api/1814
**Console**: https://console.cloud.tencent.com/ags/sandbox

### CLI applicability (repository policy)

- **`cli_applicability: sdk-only`:** Official `tccli` does **not** expose this product. **No** `references/cli-usage.md` is required. SDK/API remains mandatory for all operations. Verified via `tccli ags help` returning "Invalid product".

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT with precise AGSX keywords and API names; delegate TKE/CVM/billing to other skills |
| 2 | **Structured I/O** | `{{env.*}}` for credentials (never ask user), `{{user.*}}` for resource params, `{{output.*}}` from API responses |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight -> Execute (SDK) -> Validate -> Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | 10+ product-specific error codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | AGSX/Agent Runtime only; cross-product delegation to `qcloud-tke-ops`, `qcloud-cam-ops`, etc. |

### Well-Architected Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Reliability** | Multi-AZ region, retry on RequestLimitExceeded, instance health probes | `references/well-architected-assessment.md` |
| **Security** | CAM policies, API key rotation, credential masking, VPC isolation | `references/well-architected-assessment.md` |
| **Cost** | Terminate idle instances, monitor sandbox-hours, right-size specs | `references/well-architected-assessment.md` |
| **Efficiency** | Image prewarming, connection pooling, batch instance creation | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "AGSX", "Agent Runtime", "Agent Sandbox", "代码沙箱", "浏览器沙箱", "沙箱实例"
- Task involves CRUD or lifecycle on **SandboxTool**, **SandboxInstance**, **APIKey**, or **Image** resources
- Task keywords: sandbox tool, sandbox instance, e2b sandbox, tencentags, code interpreter sandbox, browser sandbox
- User asks to deploy, configure, troubleshoot, or monitor AGSX **via API, SDK, or automation**

### SHOULD NOT Use This Skill When

- Task is purely billing / account management -> delegate to: `qcloud-billing-ops`
- Task is CAM / permission model only -> delegate to: `qcloud-cam-ops`
- Task is about TKE / CVM / SCF compute -> delegate to: `qcloud-tke-ops`
- User insists on **console-only** flows with no API -> state limitation; do not invent undocumented HTTP steps

### Delegation Rules

- If AGSX sandbox requires VPC access, configure VPC via `qcloud-vpc-ops` before sandbox creation.
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs.

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Default `ap-guangzhou` if skill allows |
| `{{env.E2B_API_KEY}}` | Sandbox runtime API key | NEVER ask the user; fail if unset |
| `{{env.E2B_DOMAIN}}` | Sandbox endpoint domain | Default `ap-guangzhou.tencentags.com` |
| `{{user.tool_name}}` | User-supplied tool name | Ask once; reuse |
| `{{user.tool_id}}` | User-supplied tool ID (stool-xxx) | Ask once; reuse |
| `{{user.instance_id}}` | User-supplied instance ID (si-xxx) | Ask once; reuse |
| `{{user.image_id}}` | User-supplied image ID (img-xxx) | Ask once; reuse |
| `{{output.resource_id}}` | From last API JSON response | Parse per API spec response path |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking - MANDATORY):** **NEVER** log, print, or expose `TENCENTCLOUD_SECRET_KEY`, `E2B_API_KEY`, or any credential field value.

| Execution Path | Safe Pattern | Unsafe Pattern |
|----------------|-------------|----------------|
| Console output | `E2B_API_KEY=<masked>` | `E2B_API_KEY=ak-abc123...` |
| Error messages | `Error: API call failed (credential omitted)` | `Error: InvalidSecretKey ... actual key...` |
| Log files | `[INFO] Credentials configured: Key=***` | `[INFO] Secret Key: abc123...` |
| Verification | `test -n "$E2B_API_KEY" && echo "Key is set"` | `echo $E2B_API_KEY` |
| Python SDK | `SecretKey=os.environ.get("...")` (env read safe) | `print(f"Config: {config}")` |

> **If any execution flow violates this rule, the skill SHALL be blocked from merge as a security incident.**

## API and Response Conventions

- **Service**: `ags` | **Version**: `2025-09-20` | **Endpoint**: `ags.tencentcloudapi.com`
- **Errors**: Map SDK errors to `code` / `message` fields per spec. Tencent Cloud uses `Response.Error` pattern.
- **Timestamps**: ISO 8601 format when API returns strings.
- **Idempotency**: CreateSandboxTool with duplicate ToolName returns `ResourceAlreadyExists`.

### Response Field Table

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| CreateSandboxTool | `$.Response.ToolId` | string | New tool ID (stool-xxx) |
| StartSandboxInstance | `$.Response.InstanceId` | string | New instance ID (si-xxx) |
| CreateAPIKey | `$.Response.ApiKey` | string | Runtime API key (shown only once) |
| CreatePreCacheImageTask | `$.Response.RequestId` | string | Request tracking ID |
| Describe* | `$.Response.*Set[]` | array | Resource list |
| Delete/Stop | `$.Response.RequestId` | string | Request tracking ID |

### State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| CreateSandboxTool | -- | `AVAILABLE` | 5s | 120s |
| StartSandboxInstance | -- | `RUNNING` | 2s | 60s |
| StopSandboxInstance | `RUNNING` | absent | 5s | 60s |
| DeleteSandboxTool | `AVAILABLE` | absent | 5s | 60s |

## Quick Start

### Prerequisites
- [ ] Python 3.8+ runtime for SDK fallback
- [ ] Credentials: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region: `TENCENTCLOUD_REGION` (default: ap-guangzhou)

### Verify Setup
```bash
python3 -c "from tencentcloud.ags.v20250920 import ags_client; print('SDK OK')"
test -n "$TENCENTCLOUD_SECRET_ID" && echo "SecretId: set"
test -n "$TENCENTCLOUD_SECRET_KEY" && echo "SecretKey: set"
```

### Your First Command
```python
from tencentcloud.common import credential
from tencentcloud.ags.v20250920 import ags_client, models

cred = credential.Credential(
    os.environ["TENCENTCLOUD_SECRET_ID"],
    os.environ["TENCENTCLOUD_SECRET_KEY"]
)
client = ags_client.AgsClient(cred, "ap-guangzhou")
resp = client.DescribeSandboxToolList(models.DescribeSandboxToolListRequest())
print(resp.to_json_string())
```

## Capabilities at a Glance

| Operation | API | Complexity | Risk Level |
|-----------|-----|------------|------------|
| List sandbox tools | DescribeSandboxToolList | Low | None |
| Create sandbox tool | CreateSandboxTool | Medium | Low |
| Update sandbox tool | UpdateSandboxTool | Medium | Medium |
| Delete sandbox tool | DeleteSandboxTool | Low | **High** - irreversible |
| Start sandbox instance | StartSandboxInstance | Medium | Low |
| List sandbox instances | DescribeSandboxInstanceList | Low | None |
| Stop sandbox instance | StopSandboxInstance | Low | **High** - irreversible |
| Pause sandbox instance | PauseSandboxInstance | Low | None |
| Resume sandbox instance | ResumeSandboxInstance | Low | None |
| Create API key | CreateAPIKey | Medium | Low |
| Delete API key | DeleteAPIKey | Low | **High** - irreversible |
| Pre-cache image | CreatePreCacheImageTask | Low | None |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight -> Execute (SDK) -> Validate -> Recover**. Do not skip phases.

Since `cli_applicability: sdk-only`, only SDK paths are documented. See `references/api-sdk-usage.md` for complete code examples.

### Operation: CreateSandboxTool

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Python SDK | `pip show tencentcloud-sdk-python` | Version >= 3.0.1300 | `pip install tencentcloud-sdk-python` |
| Credentials | `test -n "$TENCENTCLOUD_SECRET_ID"` | Non-empty | HALT; user configures env |
| Region | `TENCENTCLOUD_REGION` set or use default | `ap-guangzhou` supported | Suggest valid region |
| Quota | Call DescribeSandboxToolList | Tool count < quota | HALT; user raises quota |

#### Execution - Python SDK

```python
from tencentcloud.ags.v20250920 import ags_client, models

req = models.CreateSandboxToolRequest()
req.from_json_string(json.dumps({
    "ToolName": "{{user.tool_name}}",
    "ToolType": "CodeSandbox",       # CodeSandbox | BrowserSandbox | CustomSandbox
    "DefaultTimeout": 3600,
    "Description": "Created by AGSX skill"
}))
resp = client.CreateSandboxTool(req)
# resp.ToolId -> stool-xxxxxxxx (capture as {{output.resource_id}})
```

#### Post-execution Validation

1. Read `{{output.resource_id}}` from `resp.ToolId`.
2. Poll DescribeSandboxToolList until status = `AVAILABLE` (interval: 5s, max: 120s).
3. On success, report `ToolId`, `ToolName`, `Status` to user.
4. On terminal failure, go to Failure Recovery.

#### Failure Recovery

| Error pattern | Max retries | Backoff | Agent Action | UX Feedback |
|---------------|-------------|---------|--------------|-------------|
| `InvalidParameter` | 0 | -- | Fix args from API spec | `[ERROR] InvalidParameter: Check parameter values against API docs.` |
| `ResourceAlreadyExists` | 0 | -- | Ask reuse vs new name | `[ERROR] ToolName already exists. Use different name or describe existing.` |
| `QuotaExceeded` | 0 | -- | HALT | `[ERROR] Quota exceeded. Request increase in console.` |
| `RequestLimitExceeded` | 3 | exponential | Back off; retry | `Rate limit. Retrying in {backoff}s...` |

---

### Operation: DescribeSandboxToolList

#### Execution - Python SDK

```python
req = models.DescribeSandboxToolListRequest()
req.from_json_string('{"Limit": 20, "Offset": 0}')
resp = client.DescribeSandboxToolList(req)
for tool in resp.ToolSet:
    print(tool.ToolId, tool.ToolName, tool.Status)
```

#### Present to User

| Field | Path | Notes |
|-------|------|-------|
| ToolId | `$.Response.ToolSet[].ToolId` | stool-xxx format |
| ToolName | `$.Response.ToolSet[].ToolName` | User-friendly name |
| Status | `$.Response.ToolSet[].Status` | AVAILABLE | BUILDING | FAILED |
| ToolType | `$.Response.ToolSet[].ToolType` | CodeSandbox | BrowserSandbox | CustomSandbox |

---

### Operation: UpdateSandboxTool

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Tool exists | DescribeSandboxToolList by `{{user.tool_id}}` | Status = AVAILABLE | HALT; tool not found or not stable |

#### Execution - Python SDK

```python
req = models.UpdateSandboxToolRequest()
req.from_json_string(json.dumps({
    "ToolId": "{{user.tool_id}}",
    "Description": "Updated description"
}))
resp = client.UpdateSandboxTool(req)
```

#### Post-execution Validation

1. Poll DescribeSandboxToolList until changes reflected (interval: 5s, max: 60s).
2. Report updated fields to user.

#### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `ResourceNotFound` | 0 | HALT; verify ToolId |
| `OperationConflict` | 3 (30s backoff) | Wait for tool to stabilize |
| `RequestLimitExceeded` | 3 | Exponential backoff |

---

### Operation: DeleteSandboxTool (SAFETY GATE)

#### Pre-flight (Safety Gate)

1. **MUST** obtain explicit confirmation: irreversible delete of `{{user.tool_id}}`.
2. **MUST** check for active instances under this tool (call DescribeSandboxInstanceList with ToolId filter).
3. **MUST NOT** proceed without clear user assent.

#### Execution - Python SDK

```python
# Pre-check: confirm no active instances
desc_req = models.DescribeSandboxInstanceListRequest()
desc_req.from_json_string(json.dumps({"ToolId": "{{user.tool_id}}"}))
desc_resp = client.DescribeSandboxInstanceList(desc_req)
if len(desc_resp.InstanceSet) > 0:
    print(f"[WARN] {len(desc_resp.InstanceSet)} active instances. Stop first.")
    # HALT until instances cleared

# User confirmed; proceed
req = models.DeleteSandboxToolRequest()
req.from_json_string(json.dumps({"ToolId": "{{user.tool_id}}"}))
resp = client.DeleteSandboxTool(req)
```

#### Post-execution Validation

Poll DescribeSandboxToolList until `ResourceNotFound` or absent (interval: 5s, max: 60s).

#### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `ResourceNotFound` | 0 | Already deleted |
| `OperationConflict` | 3 (30s backoff) | Instances still running; stop first |

---

### Operation: StartSandboxInstance

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Tool exists | DescribeSandboxToolList | Status = AVAILABLE | HALT; create tool first |
| API key | `test -n "$E2B_API_KEY"` | Non-empty | CreateAPIKey first |

#### Execution - Python SDK

```python
req = models.StartSandboxInstanceRequest()
req.from_json_string(json.dumps({
    "ToolId": "{{user.tool_id}}",
    "ToolName": "{{user.tool_name}}",
    "Timeout": 3600,
    "Metadata": [{"Key": "agent_id", "Value": "agent-001"}]
}))
resp = client.StartSandboxInstance(req)
# resp.InstanceId -> si-xxxxxxxx
# resp.Endpoint -> wss://si-xxx.ap-guangzhou.tencentags.com
```

#### Post-execution Validation

1. Poll DescribeSandboxInstanceList until Status = `RUNNING` (interval: 2s, max: 60s).
2. Verify connectivity via e2b SDK: `Sandbox.connect(instance_id)`.

#### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `ResourceNotFound` | 0 | HALT; verify ToolId |
| `ResourceInsufficient` | 0 | HALT; quota or capacity |
| `RequestLimitExceeded` | 3 | Exponential backoff |

---

### Operation: DescribeSandboxInstanceList

#### Execution - Python SDK

```python
req = models.DescribeSandboxInstanceListRequest()
req.from_json_string(json.dumps({"InstanceIds": ["{{user.instance_id}}"]}))
resp = client.DescribeSandboxInstanceList(req)
for inst in resp.InstanceSet:
    print(inst.InstanceId, inst.Status, inst.CreatedAt, inst.ExpireAt)
```

#### Present to User

| Field | Path | Notes |
|-------|------|-------|
| InstanceId | `$.Response.InstanceSet[].InstanceId` | si-xxx format |
| Status | `$.Response.InstanceSet[].Status` | RUNNING | PENDING | STOPPED |
| CreatedAt | `$.Response.InstanceSet[].CreatedAt` | ISO 8601 |
| ExpireAt | `$.Response.InstanceSet[].ExpireAt` | 24h max from creation |

---

### Operation: StopSandboxInstance (SAFETY GATE)

#### Pre-flight (Safety Gate)

1. **MUST** obtain explicit confirmation: stop `{{user.instance_id}}`.
2. Display remaining TTL and any active connections.
3. **MUST NOT** proceed without clear user assent.

#### Execution - Python SDK

```python
req = models.StopSandboxInstanceRequest()
req.from_json_string(json.dumps({"InstanceId": "{{user.instance_id}}"}))
resp = client.StopSandboxInstance(req)
```

#### Post-execution Validation

Poll DescribeSandboxInstanceList until Status = `STOPPED` or absent (interval: 5s, max: 60s).

#### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `ResourceNotFound` | 0 | HALT; instance not found |
| `OperationConflict` | 3 (30s backoff) | Instance in transition state |

---

### Operation: CreateAPIKey

#### Execution - Python SDK

```python
req = models.CreateAPIKeyRequest()
req.from_json_string(json.dumps({"Name": "prod-key-01"}))
resp = client.CreateAPIKey(req)
# resp.ApiKey -> store securely, shown only once
# MASK in logs: ak-****resp.ApiKey[-4:]
```

> **Security:** The API key value is returned ONLY on creation. Store immediately. Mask in all subsequent logs.

#### Post-execution Validation

1. Capture `resp.ApiKey` immediately (shown only once).
2. Verify key appears in DescribeAPIKeyList.
3. Test connectivity: set `E2B_API_KEY` and run e2b-code-interpreter.

#### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `InvalidParameter` | 0 | Fix name parameter |
| `QuotaExceeded` | 0 | HALT; delete unused keys first |

---

### Operation: DeleteAPIKey (SAFETY GATE)

#### Pre-flight (Safety Gate)

1. **MUST** warn: all sandbox instances using this key will lose connectivity.
2. **MUST** obtain explicit confirmation for `{{user.key_id}}`.
3. Suggest creating replacement key first if still in use.

#### Execution - Python SDK

```python
req = models.DeleteAPIKeyRequest()
req.from_json_string(json.dumps({"KeyId": "{{user.key_id}}"}))
resp = client.DeleteAPIKey(req)
```

#### Post-execution Validation

1. Verify key no longer appears in DescribeAPIKeyList.
2. Note: existing connections using this key will break.

#### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `ResourceNotFound` | 0 | HALT; KeyId already deleted |
| `OperationConflict` | 3 (30s backoff) | Key in use; wait |

---

### Operation: CreatePreCacheImageTask

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Image exists | DescribePreCacheImageTask | Valid image | HALT; verify Image name |
| Region support | Check region | ap-guangzhou | Switch to supported region |

#### Execution - Python SDK

```python
req = models.CreatePreCacheImageTaskRequest()
req.from_json_string(json.dumps({
    "Image": "{{user.image_id}}",
    "ImageRegistryType": "DockerHub"
}))
resp = client.CreatePreCacheImageTask(req)
# Reduces cold-start from ~500ms to ~100ms
```

#### Post-execution Validation

1. Poll DescribePreCacheImageTask until Status = `COMPLETED`.
2. Test StartSandboxInstance latency < 200ms.

#### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `InvalidParameter` | 0 | Check Image name format |
| `UnsupportedOperation` | 0 | Switch to supported region |

---

## Prerequisites

1. **Install Python SDK** (required - tccli does not support this product):

   ```bash
   pip install tencentcloud-sdk-python
   # Or product-specific: pip install tencentcloud-sdk-python-ags
   python3 --version  # Must be >= 3.8
   ```

2. **Install client-side SDK** (for runtime sandbox connections):

   ```bash
   pip install e2b-code-interpreter
   ```

3. **Configure Credentials** -- Environment variables (recommended for Agent execution):

   ```bash
   export TENCENTCLOUD_SECRET_ID="{{env.TENCENTCLOUD_SECRET_ID}}"
   export TENCENTCLOUD_SECRET_KEY="{{env.TENCENTCLOUD_SECRET_KEY}}"
   export TENCENTCLOUD_REGION="{{env.TENCENTCLOUD_REGION}}"
   export E2B_API_KEY="{{env.E2B_API_KEY}}"
   export E2B_DOMAIN="ap-guangzhou.tencentags.com"
   ```

4. **Verify Configuration**:

   ```bash
   python3 -c "
   from tencentcloud.ags.v20250920 import ags_client
   print('AGSX SDK: OK')
   "
   test -n "$TENCENTCLOUD_SECRET_ID" && echo "SecretId: set"
   ```

> **Security:** Never commit `.env` to version control. All credentials use `{{env.*}}` placeholders -- never real values.

## Reference Directory

- [Core Concepts](references/core-concepts.md) -- AGSX domain model and sandbox types
- [API & SDK Usage](references/api-sdk-usage.md) -- Full SDK examples for all 10 APIs
- [Troubleshooting Guide](references/troubleshooting.md) -- Error remediation playbook
- [Monitoring & Alerts](references/monitoring.md) -- CLS + CloudMonitor integration
- [Integration](references/integration.md) -- e2b SDK + MCP client patterns
- [Well-Architected Assessment](references/well-architected-assessment.md) -- 5-pillar audit checklist
- [Example Config](assets/example-config.yaml) -- Reference configuration
- [Eval Queries](assets/eval_queries.json) -- Test prompts for skill validation

## Operational Best Practices

- **Least privilege:** CAM policies scoped to `ags:*` actions only.
- **Availability:** Use ap-guangzhou as primary; ap-shanghai as failover.
- **Cost:** Terminate idle instances within 5min; right-size specs via monitoring.
- **Security:** Rotate API keys quarterly; enable CLS logging on all tools.

---

## Error Code Reference (10 Product-Specific Codes)

| Code | Meaning | Retry? | Agent Action |
|------|---------|--------|--------------|
| `InvalidParameter` | Parameter validation failed | No | Fix parameter; retry with correct value |
| `ResourceNotFound` | Target resource not found | No | Verify resource ID; suggest Describe |
| `ResourceInsufficient` | Quota or capacity exhausted | No | HALT; request quota increase |
| `InvalidSecretKey` | Credential invalid | No | HALT; fix credentials via CAM |
| `RequestLimitExceeded` | API rate limit | Yes (3x) | Exponential backoff |
| `InternalError` | Server-side error | Yes (3x) | Retry 2s/4s/8s; escalate with RequestId |
| `OperationConflict` | Concurrent operation conflict | Yes (3x, 30s) | Wait; retry after stable state |
| `UnauthorizedOperation` | CAM policy denies action | No | HALT; grant `ags:*` permission |
| `UnsupportedOperation` | API not supported in region | No | Switch to supported region |
| `QuotaExceeded` | Account quota reached | No | HALT; apply for quota increase |

---

## Safety Gates (Destructive Operations)

Every **Delete**, **Terminate**, or **irreversible** operation MUST have:

1. **Explicit user confirmation** with resource identifier displayed
2. **Dependency check** (active instances under tool, keys in use)
3. **Impact display** (what resources will be affected)
4. **Post-delete verification** (poll until 404 or deleted state)

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **recommended** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **3** | per-skill override (AGENTS.md §8 default for `qcloud-agsx-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 AGSX-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### AGSX-specific safety rules (rubric §4)

1. `DeleteAgentPool` / `TerminateAgentPool` — pool ID + Name + agent count echo; cascade warning; confirm
2. `DeleteAgent` (active) — agent ID + status echo; check pending executions; confirm
3. `TerminateAgentExecution` — execution ID + agent ID echo; warn no-rollback; confirm
4. `UpdateAgentPoolConfig` — BEFORE/AFTER diff; warn capacity/timeout kills in-flight agents; confirm per field
5. `CreateAgentPool` / `CreateAgent` — surface cost + quota; warn compute-heavy billing; confirm

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

---

## Output Schema

All responses follow Tencent Cloud API structure:

```json
{
  "Response": {
    "RequestId": "req-abc123",
    "ToolId": "stool-xxxxxxxx",
    "InstanceId": "si-xxxxxxxx",
    "Status": "RUNNING",
    "ApiKey": "<masked>"
  }
}
```

Error responses:

```json
{
  "Response": {
    "RequestId": "req-abc123",
    "Error": {
      "Code": "InvalidParameter",
      "Message": "Parameter validation failed"
    }
  }
}
```

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-28 | Initial skill generated from qcloud-skill-generator template |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 AGSX-specific safety rules incl. agent-pool cascade, active-agent deletion, force-termination no-rollback, pool config disruption, provisioning cost), `references/prompt-templates.md`. `max_iter=3` per AGENTS.md §8 |
