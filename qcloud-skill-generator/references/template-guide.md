# Template Guide — Detailed Conventions & Patterns

> Extracted from `qcloud-skill-template.md`. Referenced by the template for
> detailed guidance on variables, API conventions, CLI behavior, SDK patterns,
> validation, and failure recovery.

---

## Section 1: Variable Convention Details

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

---

## Section 2: API and Response Conventions

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

---

## Section 3: CLI Execution Notes

> **Critical CLI Notes** (verified through official documentation):
> - Output is **JSON by default** — standard JSON structure with `Response` wrapper
> - CLI uses `--region` for region specification (not `--RegionId`)
> - Credentials from env vars: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
> - CLI format: `tccli <product> <ActionName> --Param1 value1 --Param2 value2`

---

## Section 4: SDK Fallback Script Template

When `tccli` CLI does not support a specific operation, use `tencentcloud-sdk-python`:

```python
#!/usr/bin/env python3
"""
SDK fallback script for [Product] Create[Resource]

Tool-grounding integration (P1-3):
  Before executing, validate params against the skill's tool-call-grounding.md
  schema reference (see references/tool-call-grounding.md §2 for registration pattern).
  Use GroundingDetector to catch tool_not_found, param_out_of_range, and
  state_not_satisfied errors before they reach the cloud.
"""
import os
import json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
# Import product-specific module
from tencentcloud.[product] import [product_client, models]

def main():
    try:
        # Credential from environment
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        
        # Client with region
        client = [product_client].[Product]Client(cred, os.environ.get("TENCENTCLOUD_REGION"))
        
        # Request per API spec
        req = models.Create[Resource]Request()
        req.[Param1] = "<value1>"
        req.[Param2] = "<value2>"
        
        # Execute and print
        resp = client.Create[Resource](req)
        print(json.dumps(resp.to_json_string(), indent=2))
        
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

> **Tool-grounding**: Every SDK fallback script should integrate the skill's
> `references/tool-call-grounding.md` for parameter validation and state-dependency
> checks. See `references/tool-call-grounding.md` §2 for `register()` / `validate_call()`
> usage and §3 for `StateTracker` / `can_call()` patterns. This reduces
> hallucinated parameters and prevents invalid state transitions.

---

## Section 5: Post-Execution Validation Pattern

1. Read `{{output.resource_id}}` from the **documented** response path (`$.Response.InstanceId` for most products).
2. Poll **Describe** until terminal success state or timeout:

```bash
# CLI polling (manual loop)
for i in $(seq 1 60); do
  STATUS=$(tccli [product] Describe[Resource] --[IdName] "{{output.resource_id}}" | jq -r '.Response.Status')
  [ "$STATUS" = "RUNNING" ] && break
  sleep 5
done
```

```python
# SDK polling
import time
for i in range(60):
    resp = client.Describe[Resource](describe_req)
    if resp.Status == "RUNNING":
        break
    time.sleep(5)
```

3. On success, report `{{output.resource_id}}` and key fields to the user.
4. On terminal failure, go to **Failure Recovery**.

---

## Section 6: Failure Recovery Table Template

| Error pattern (from API/SDK or parsed CLI JSON) | Max retries | Backoff | Agent Action | UX Feedback |
|------------------------------|-------------|---------|--------------|-------------|
| `InvalidParameter` / 400 invalid input | 0–1 | — | Fix args from API spec; retry once if safe | `[ERROR] InvalidParameter: The request parameter is invalid. What happened: One or more parameters do not meet the API specification. How to fix: Check the parameter against API docs and retry. Next step: Review the parameter table above.` |
| `ResourceInsufficient` / `资源不足` | 0 | — | HALT | `[ERROR] ResourceInsufficient: Resource quota limit reached. What happened: Your account has reached the maximum allowed number of this resource type. How to fix: Delete unused resources or request a quota increase. Next step: Contact support or delete unused resources.` |
| `InvalidSecretKey` / `InvalidSecretId` | 0 | — | HALT | `[ERROR] InvalidSecretKey/InvalidSecretId: Credential invalid. What happened: Your API credentials are incorrect or expired. How to fix: Verify TENCENTCLOUD_SECRET_ID and TENCENTCLOUD_SECRET_KEY. Next step: Check environment variables.` |
| `ResourceAlreadyExists` | 0 | — | Ask reuse vs new name | `[ERROR] ResourceAlreadyExists: A resource with this name already exists. What happened: The specified resource name is already in use. How to fix: Use a different name or reuse the existing resource. Next step: Choose a unique name or describe the existing resource.` |
| RequestLimitExceeded / 429 | 3 | exponential | Back off; respect rate limit | `⚠️ Rate limit reached. Retrying in {backoff}s... (Attempt {current}/{max})` |
| `InternalError` / 5xx | 3 | 2s, 4s, 8s | Retry; then HALT with RequestId if any | `[ERROR] InternalError: Server-side error occurred. What happened: Tencent Cloud encountered an internal error processing your request. How to fix: Retry the operation. If it persists, escalate with RequestId. Next step: Retry now or escalate with RequestId: {RequestId}.` |
