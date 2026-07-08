# AGSX Execution Flows (TE-6)

This file contains detailed per-operation execution flows, moved from SKILL.md (TE-6: Token Efficiency).

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (SDK) → Validate → Recover**. Do not skip phases.

Since `cli_applicability: sdk-only`, only SDK paths are documented. See also `references/api-sdk-usage.md`.

---

## Operation: CreateSandboxTool

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Python SDK | `pip show tencentcloud-sdk-python` | Version ≥ 3.0.1300 | `pip install tencentcloud-sdk-python` |
| Credentials | `test -n "$TENCENTCLOUD_SECRET_ID"` | Non-empty | HALT; user configures env |
| Region | `TENCENTCLOUD_REGION` set or use default | `ap-guangzhou` supported | Suggest valid region |
| Quota | Call DescribeSandboxToolList | Tool count < quota | HALT; user raises quota |

### Execution — Python SDK

See [sdk-code-examples.md](sdk-code-examples.md) for code.

### Post-execution Validation

1. Read `{{output.resource_id}}` from `resp.ToolId`
2. Poll DescribeSandboxToolList until status = `AVAILABLE` (interval: 5s, max: 120s)
3. On success, report `ToolId`, `ToolName`, `Status` to user
4. On terminal failure, go to Failure Recovery

### Failure Recovery

| Error pattern | Max retries | Backoff | Agent Action | UX Feedback |
|---------------|-------------|---------|--------------|-------------|
| `InvalidParameter` | 0 | — | Fix args from API spec | `[ERROR] InvalidParameter: Check parameter values against API docs.` |
| `ResourceAlreadyExists` | 0 | — | Ask reuse vs new name | `[ERROR] ToolName already exists. Use different name or describe existing.` |
| `QuotaExceeded` | 0 | — | HALT | `[ERROR] Quota exceeded. Request increase in console.` |
| `RequestLimitExceeded` | 3 | exponential | Back off; retry | Rate limit. Retrying in {backoff}s... |

---

## Operation: DescribeSandboxToolList

### Execution — Python SDK

See [sdk-code-examples.md](sdk-code-examples.md) for code.

### Present to User

| Field | Path | Notes |
|-------|------|-------|
| ToolId | `$.Response.ToolSet[].ToolId` | stool-xxx format |
| ToolName | `$.Response.ToolSet[].ToolName` | User-friendly name |
| Status | `$.Response.ToolSet[].Status` | AVAILABLE | BUILDING | FAILED |
| ToolType | `$.Response.ToolSet[].ToolType` | CodeSandbox | BrowserSandbox | CustomSandbox |

---

## Operation: UpdateSandboxTool

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Tool exists | DescribeSandboxToolList by `{{user.tool_id}}` | Status = AVAILABLE | HALT; tool not found or not stable |

### Execution — Python SDK

See [sdk-code-examples.md](sdk-code-examples.md) for code.

### Post-execution Validation

1. Poll DescribeSandboxToolList until changes reflected (interval: 5s, max: 60s)
2. Report updated fields to user

### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `ResourceNotFound` | 0 | HALT; verify ToolId |
| `OperationConflict` | 3 (30s backoff) | Wait for tool to stabilize |
| `RequestLimitExceeded` | 3 | Exponential backoff |

---

## Operation: DeleteSandboxTool (SAFETY GATE)

### Pre-flight (Safety Gate)

1. **MUST** obtain explicit confirmation: irreversible delete of `{{user.tool_id}}`
2. **MUST** check for active instances under this tool (call DescribeSandboxInstanceList with ToolId filter)
3. **MUST NOT** proceed without clear user assent

### Execution — Python SDK

See [sdk-code-examples.md](sdk-code-examples.md) for code.

### Post-execution Validation

Poll DescribeSandboxToolList until `ResourceNotFound` or absent (interval: 5s, max: 60s).

### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `ResourceNotFound` | 0 | Already deleted |
| `OperationConflict` | 3 (30s backoff) | Instances still running; stop first |

---

## Operation: StartSandboxInstance

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Tool exists | DescribeSandboxToolList | Status = AVAILABLE | HALT; create tool first |
| API key | `test -n "$E2B_API_KEY"` | Non-empty | CreateAPIKey first |

### Execution — Python SDK

See [sdk-code-examples.md](sdk-code-examples.md) for code.

### Post-execution Validation

1. Poll DescribeSandboxInstanceList until Status = `RUNNING` (interval: 2s, max: 60s)
2. Verify connectivity via e2b SDK: `Sandbox.connect(instance_id)`

### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `ResourceNotFound` | 0 | HALT; verify ToolId |
| `ResourceInsufficient` | 0 | HALT; quota or capacity |
| `RequestLimitExceeded` | 3 | Exponential backoff |

---

## Operation: DescribeSandboxInstanceList

### Execution — Python SDK

See [sdk-code-examples.md](sdk-code-examples.md) for code.

### Present to User

| Field | Path | Notes |
|-------|------|-------|
| InstanceId | `$.Response.InstanceSet[].InstanceId` | si-xxx format |
| Status | `$.Response.InstanceSet[].Status` | RUNNING | PENDING | STOPPED |
| CreatedAt | `$.Response.InstanceSet[].CreatedAt` | ISO 8601 |
| ExpireAt | `$.Response.InstanceSet[].ExpireAt` | 24h max from creation |

---

## Operation: StopSandboxInstance (SAFETY GATE)

### Pre-flight (Safety Gate)

1. **MUST** obtain explicit confirmation: stop `{{user.instance_id}}`
2. Display remaining TTL and any active connections
3. **MUST NOT** proceed without clear user assent

### Execution — Python SDK

See [sdk-code-examples.md](sdk-code-examples.md) for code.

### Post-execution Validation

Poll DescribeSandboxInstanceList until Status = `STOPPED` or absent (interval: 5s, max: 60s).

### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `ResourceNotFound` | 0 | HALT; instance not found |
| `OperationConflict` | 3 (30s backoff) | Instance in transition state |

---

## Operation: CreateAPIKey

### Execution — Python SDK

See [sdk-code-examples.md](sdk-code-examples.md) for code.

> **Security:** The API key value is returned ONLY on creation. Store immediately. Mask in all subsequent logs.

### Post-execution Validation

1. Capture `resp.ApiKey` immediately (shown only once)
2. Verify key appears in DescribeAPIKeyList
3. Test connectivity: set `E2B_API_KEY` and run e2b-code-interpreter

### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `InvalidParameter` | 0 | Fix name parameter |
| `QuotaExceeded` | 0 | HALT; delete unused keys first |

---

## Operation: DeleteAPIKey (SAFETY GATE)

### Pre-flight (Safety Gate)

1. **MUST** warn: all sandbox instances using this key will lose connectivity
2. **MUST** obtain explicit confirmation for `{{user.key_id}}`
3. Suggest creating replacement key first if still in use

### Execution — Python SDK

See [sdk-code-examples.md](sdk-code-examples.md) for code.

### Post-execution Validation

1. Verify key no longer appears in DescribeAPIKeyList
2. Note: existing connections using this key will break

### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `ResourceNotFound` | 0 | HALT; KeyId already deleted |
| `OperationConflict` | 3 (30s backoff) | Key in use; wait |

---

## Operation: CreatePreCacheImageTask

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Image exists | DescribePreCacheImageTask | Valid image | HALT; verify Image name |
| Region support | Check region | ap-guangzhou | Switch to supported region |

### Execution — Python SDK

See [sdk-code-examples.md](sdk-code-examples.md) for code.

### Post-execution Validation

1. Poll DescribePreCacheImageTask until Status = `COMPLETED`
2. Test StartSandboxInstance latency < 200ms

### Failure Recovery

| Error pattern | Max retries | Agent Action |
|---------------|-------------|--------------|
| `InvalidParameter` | 0 | Check Image name format |
| `UnsupportedOperation` | 0 | Switch to supported region |

---

## Index

### Per-Operation Failure Recovery Quick Reference

See [error-reference.md](error-reference.md) for full error taxonomy.
