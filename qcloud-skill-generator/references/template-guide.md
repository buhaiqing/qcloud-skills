# Template Guide — Detailed Conventions & Patterns

> Extracted from `qcloud-skill-template.md`. Referenced by the template for
> detailed guidance on variables, API conventions, CLI behavior, SDK patterns,
> validation, and failure recovery.

---

## Section 1: Variable Convention Details

Structured placeholders reduce injection ambiguity and unsafe prompts. Four placeholder types:

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use documented default only if skill explicitly allows |
| `{{user.region}}` | User-supplied region | Ask once; reuse |
| `{{user.resource_name}}` | User-supplied name | Ask once; reuse |
| `{{output.resource_id}}` | From last API or CLI JSON response | Parse per **API spec** (SDK) or **verified CLI** path for this operation |
| `{{derived.<name>}}` | Computed from API response(s) or local logic | Use as default; user may override via `{{user.*}}` if they specify |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing. **`{{derived.*}}`** is NEVER asked — computed via pre-flight API calls or skill-defined defaults. **`{{output.*}}`** is parsed from the immediate prior response.

### When to use `{{derived.*}}` vs `{{user.*}}`

| Scenario | Use | Reasoning |
|----------|-----|-----------|
| User explicitly wants X | `{{user.X}}` | User intent overrides any default |
| Skill can compute a sane default from API | `{{derived.X}}` | Reduce user prompts; UX-friendly |
| Value is mandatory and only user knows | `{{user.X}}` | `{{derived.*}}` cannot hallucinate |
| Default + override pattern | `{{derived.X}}` with `{{user.X}}` override hint | Best UX: works zero-config but customizable |

### `{{derived.*}}` example patterns

```yaml
# Default zone from DescribeZones (pre-flight)
{{derived.default_zone}}: "$.Response.ZoneSet[0].Zone"

# Default instance type for a zone (matrix lookup)
{{derived.default_instance_type}}: "S5.SMALL1" (or first from DescribeZoneInstanceConfigInfos)

# Default region from env or first valid from DescribeRegions
{{derived.default_region}}: {{env.TENCENTCLOUD_REGION}} or "$.Response.RegionSet[0].Region"

# Default VPC in region
{{derived.default_vpc}}: "$.Response.VpcSet[0].VpcId"
```

**Pattern**: pre-flight API call → store result → reference as `{{derived.*}}` in subsequent operations. NEVER ask user for a `{{derived.*}}` value; if the API call fails, HALT and surface the error.

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
  Before executing, validate params against the skill's references/tool-call-grounding.md
  schema (when that file exists; omit this block otherwise).
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

> **Tool-grounding** (optional): If the skill ships `references/tool-call-grounding.md`,
> integrate it for parameter validation and state-dependency checks. See that file's
> §2 for `register()` / `validate_call()` usage and §3 for `StateTracker` / `can_call()`
> patterns. This reduces hallucinated parameters and prevents invalid state transitions.

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

---

## Section 7: Error Code Reference

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

## Section 8: Safety Gates (Destructive Operations)

Every **Delete**, **Terminate**, or **irreversible** operation MUST have:

1. **Explicit user confirmation** with resource identifier displayed
2. **Pre-backup reminder** (product-specific: snapshot, backup, export)
3. **Dependency check** (warn if resource has active connections/attachments)
4. **Post-delete verification** (poll until 404 or deleted state)

---

## Section 9: Quality Gate (GCL)

> **Required when:** this skill is GCL `required` or `recommended` per AGENTS.md §8. Defaults: any product with destructive operations (Terminate / Delete / Drop / Destroy / Reset) is `required` and `max_iter=2`. Read-only / advisory skills are `optional` and may skip this section.

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. Every mutation executes through `scripts/gcl_runner.py run` with an isolated-context Critic scoring 5 dimensions (correctness / safety / idempotency / traceability / spec_compliance). Safety = 0 ⇒ ABORT.

| Item | Value |
|---|---|
| GCL applicability | `required` / `recommended` / `optional` (per AGENTS.md §8) |
| `max_iterations` | `2` (required) / `3` (recommended) / `5` (optional) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

> **Prompt-context isolation (mandatory):** Generator and Critic run in **isolated** prompt contexts (sub-agent or fresh conversation). Critic MUST NOT see the raw user request — only `{{output.generator_output}}` + `{{output.trace}}`. See `references/prompt-templates.md` §2 for the Critic skeleton.

---

## Section 10: Output Schema

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
