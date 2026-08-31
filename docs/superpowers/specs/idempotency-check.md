# Idempotency Pre-commit Hook — Spec

## Problem Statement

GCL R4 audit (265 runs) found 129 idempotency BLOCKERs:
- `set ClientToken` (108): tccli/sdk call missing `--ClientToken` flag
- `Response missing ClientToken` (21): response object missing `ClientToken` field

Absence of idempotency keys causes Tencent Cloud API to reject duplicate-safe retries.

## Solution

A pre-commit hook (`scripts/check_idempotency.py`) + auto-fix mode in `scripts/auto_fix_gcl_blockers.py`.

## Detection Rules

| Rule | Pattern | Fix |
|------|---------|-----|
| **A: tccli subprocess** | `subprocess.run(["tccli", ...])` or `subprocess.run("tccli ...", shell=True)` without `--ClientToken` | Insert `--ClientToken "$CLIENT_TOKEN"` after tccli arg |
| **B: tencentcloud-sdk** | `from tencentcloud.X import` + nearby `client.Method(...)` without `ClientToken=` field in request | Flag: requires manual injection of `req.ClientToken = str(uuid.uuid4().hex[:32])` |
| **C: requests** | `requests.post(url, ...)` / `requests.get(...)` / `requests.request(...)` without `Idempotency-Key` header | Insert `headers={"Idempotency-Key": str(uuid.uuid4())}` |
| **D: boto3** | `client.method(...)` for write operations without `ClientToken=` kwarg | Add `ClientToken=uuid.uuid4().hex` |
| **E: azure-sdk** | `client.begin_*()` or mutation method without `request_id=` kwarg or `x-ms-client-request-id` header | Add `request_id=` kwarg or header |
| **F: google-cloud** | `bucket.blob().upload_from_filename(...)` / mutation without `request_id=` kwarg | Add `request_id=uuid.uuid4().hex` |
| **G: Go SDK** | `client.<Method>(...)` (tencentcloud-sdk-go / aws-sdk-go-v2 / alibaba-cloud-sdk-go) without `ClientToken` field | Add `ClientToken: aws.String(uuid.New().String())` (inline struct) or `request.ClientToken = ...` before call |

### Skip rules (false-positive suppression)
- `tccli --version` — read-only probe, no write semantics
- `Describe*`, `Query*`, `List*`, `Get*`, `Check*` operations — read-only, no ClientToken needed
- Lines inside triple-quoted docstrings / comments
- Lines already containing `--ClientToken` / `Idempotency-Key`

## ClientToken Recommendation

```python
# Recommended: uuid.uuid4().hex[:32] gives 32-char hex (same format as tccli default)
token = uuid.uuid4().hex[:32]   # e.g. "a1b2c3d4e5f6..."
# Or via env fallback
import os
token = os.environ.get("CLIENT_TOKEN", uuid.uuid4().hex[:32])
```

For tccli injection: `--ClientToken "$CLIENT_TOKEN"` where `$CLIENT_TOKEN` is set via env or inline `$(uuidgen)`.

## tccli Command Mapping

| Operation | Write-safe? | ClientToken required? |
|-----------|-------------|----------------------|
| `Describe*`, `Query*`, `List*`, `Get*` | No | No |
| `Create*`, `Run*`, `Allocate*`, `Start*` | Yes | Yes |
| `Modify*`, `Update*`, `Set*` | Yes | Yes |
| `Delete*`, `Terminate*`, `Stop*`, `Release*` | Yes | Yes |
| `Bind*`, `Attach*`, `Associate*` | Yes | Yes |
| `--version`, `--help` | N/A | No |

## Files

| File | Purpose |
|------|---------|
| `scripts/check_idempotency.py` | Pre-commit hook; exits 1 if issues found (blocks commit) |
| `scripts/auto_fix_gcl_blockers.py` | `--scan-code-idempotency` mode; dry-run default, `--apply` for real fix |
| `.pre-commit-config.yaml` | Hook registration |

## Exit Codes

- `0`: all clear (no idempotency issues, or `--self-test` passed)
- `1`: issues found (commit blocked); or `--self-test` failed

## Self-test Coverage

| Case | Expected |
|------|---------|
| tccli subprocess WITH ClientToken | PASS (no issue) |
| tccli subprocess WITHOUT ClientToken | FAIL (issue detected) |
| requests.post WITH Idempotency-Key | PASS (no issue) |
| requests.post WITHOUT Idempotency-Key | FAIL (issue detected) |
| SDK import + call without ClientToken | FAIL (issue detected) |
| SDK import + call with ClientToken | PASS (no issue) |
| tccli string form (Run*) without ClientToken | FAIL (issue detected) |

## Detection Rules (Extended — R7)

### Rule D: boto3 (AWS SDK for Python)

| Pattern | Fix |
|---------|-----|
| `boto3.client('svc').run_instances(...)` without `ClientToken=` kwarg | Add `ClientToken=uuid.uuid4().hex` |

**Idempotent boto3 methods requiring ClientToken:**
`run_instances`, `create_volume`, `copy_image`, `copy_snapshot`, `create_security_group`, `authorize_security_group_ingress`, `revoke_security_group_ingress`, `delete_security_group`, `create_bucket`, `put_object`, `delete_object`, `delete_bucket`, `create_stack`, `delete_stack`, `update_stack`, `create_change_set`, `delete_change_set`, `start_job`, `create_pipeline`, `send_message`, `receive_message`, `delete_queue`, `create_queue`, `publish`, `subscribe`, `create_topic`, `delete_topic`, `create_table`, `update_table`, `delete_table`, `create_function`, `update_function_code`, `delete_function`, `create_role`, `delete_role`, `attach_role_policy`, `detach_role_policy`, `put_item`, `delete_item`, `update_item`, `send_templated_email`, `send_raw_email`, `send_email`

### Rule E: azure-sdk (azure-mgmt-* / azure-identity)

| Pattern | Fix |
|---------|-----|
| `client.begin_create_or_update(...)` / `begin_delete(...)` / mutation method without `request_id=` kwarg or `x-ms-client-request-id` header | Add `request_id=uuid.uuid4().hex` or `x-ms-client-request-id` header |
| `requests.post(..., "https://*.azure.com/...")` without `x-ms-client-request-id` header | Add header |

**azure-sdk idempotency mechanisms:**
- Async LRO methods (`begin_*`) use `Operation-Location` polling; `request_id` decorates the initial request
- REST API calls should include `x-ms-client-request-id: <uuid>` header
- Auto-fix: `scripts/auto_fix_gcl_blockers.py` covers boto3; azure/gcp require manual injection

### Rule F: google-cloud-python (storage, bigquery, pubsub, datastore, kms, secretmanager)

| Pattern | Fix |
|---------|-----|
| `bucket.blob().upload_from_filename(...)` / `client.insert_rows(...)` / mutation without `request_id=` kwarg | Add `request_id=uuid.uuid4().hex` |

**google-cloud idempotent methods requiring request_id:**
`upload_from_string`, `upload_from_filename`, `delete`, `copy_blob`, `rename`, `compose`, `insert`, `insert_rows`, `insert_rows_json`, `delete_table`, `update_table`, `patch_table`, `copy_table`, `publish`, `publish_message`, `delete_topic`, `delete_subscription`, `create_snapshot`, `seek`, `put`, `allocate_ids`, `encrypt`, `decrypt`, `destroy_crypto_key`, `disable_crypto_key`, `add_version`, `destroy_secret_version`, `create_endpoint`, `deploy_model`, `undeploy_model`

### Rule G: Go SDK (tencentcloud-sdk-go / aws-sdk-go-v2 / alibaba-cloud-sdk-go)

Go is not Python AST — detection is **regex heuristic** (no Go toolchain dependency):

| Pattern | Fix |
|---------|-----|
| `client.RunInstances(request)` — request built via `cvm.NewRunInstancesRequest()` without `request.ClientToken = ...` | Add `request.ClientToken = aws.String(uuid.New().String())` before the call |
| `client.RunInstances(ctx, &ec2.RunInstancesInput{...})` without `ClientToken:` field | Add `ClientToken: aws.String(uuid.New().String())` to the Input struct literal |
| `client.CreateInstance(request)` (aliyun) without `request.ClientToken = ...` | Add `request.ClientToken = uuid.New().String()` |

**How it works:** regex matches `client.<Method>(` / `svc.<Method>(` / `xxxClient.<Method>(` call sites,
skips read-only ops (`Describe*`, `Query*`, `List*`, `Get*`, `Check*`, `Head*`, `Inspect*`),
then checks the window bounded by the previous/next SDK call for `ClientToken` / `Idempotency*`
(a GOOD call's token never masks a neighboring BAD call).

**Go idempotent method prefixes:** `Create`, `Run`, `Modify`, `Update`, `Set`, `Put`, `Delete`,
`Terminate`, `Stop`, `Release`, `Reset`, `Reboot`, `Restart`, `Bind`, `Attach`, `Associate`,
`Allocate`, `Start`, `Clone`, `Copy`.

### SDK Field Mapping

| SDK | Idempotency Field | Example |
|-----|-------------------|---------|
| tccli / tencentcloud-sdk | `ClientToken` | `--ClientToken "$TOKEN"` / `req.ClientToken = uuid` |
| boto3 (AWS) | `ClientToken` | `ClientToken=uuid.uuid4().hex` |
| Go SDK (tencent/aws/aliyun) | `ClientToken` | `ClientToken: aws.String(uuid.New().String())` / `request.ClientToken = ...` |
| azure-sdk | `request_id` or `x-ms-client-request-id` header | `request_id=uuid.hex` / `headers={"x-ms-client-request-id": uuid}` |
| google-cloud-python | `request_id` | `request_id=uuid.uuid4().hex` |
| requests (raw HTTP) | `Idempotency-Key` header | `headers={"Idempotency-Key": uuid}` |


| boto3 run_instances WITHOUT ClientToken | FAIL (issue detected) |
| boto3 run_instances WITH ClientToken | PASS (no issue) |
| boto3 create_bucket WITHOUT ClientToken | FAIL (issue detected) |
| azure-mgmt begin_create_or_update without request-id | FAIL (issue detected) |
| azure-mgmt begin_create_or_update with request_id kwarg | PASS (no issue) |
| google-cloud storage upload without request_id | FAIL (issue detected) |
| clean file (no API calls) | PASS (no issue) |
| go tencentcloud v3 RunInstances WITHOUT ClientToken | FAIL (issue detected) |
| go tencentcloud v3 RunInstances WITH ClientToken | PASS (no issue) |
| go aws-sdk-go-v2 RunInstances WITHOUT ClientToken | FAIL (issue detected) |
| go aws-sdk-go-v2 RunInstances WITH inline ClientToken | PASS (no issue) |
| go ModifyInstance WITHOUT ClientToken (method variant) | FAIL (issue detected) |
| go DescribeInstances (read-only) | PASS (no issue) |
| go aliyun CreateInstance WITHOUT ClientToken | FAIL (issue detected) |
