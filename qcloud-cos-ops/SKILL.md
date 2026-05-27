---
name: qcloud-cos-ops
description: >-
  Use when the user needs to manage, configure, or operate Tencent Cloud COS
  (Cloud Object Storage) — Bucket lifecycle, object upload/download, storage
  class management, access control, and diagnostics. User mentions COS, 对象存储,
  Object Storage, Bucket, or describes storage-related scenarios (e.g., file
  upload, backup storage, static website hosting) even without naming the
  product directly. Not for billing, CAM, CDN, or related products that have
  their own ops skills.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable) with coscmd
  tool, Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python-cos),
  valid API credentials, network access to Tencent Cloud COS endpoints.
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "2026-05-21"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "2024-01-01 - https://cloud.tencent.com/document/api/436"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    tccli cos help confirms CLI support. coscmd tool provides enhanced object
    operations including multipart upload, sync, and batch delete.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

# Tencent Cloud COS Operations Skill

## Overview

COS (Cloud Object Storage) on Tencent Cloud provides scalable, secure, and highly available object storage for unstructured data. Supports multiple storage classes (STANDARD, STANDARD_IA, ARCHIVE), lifecycle management, versioning, and access control via ACL/Bucket Policy. This skill is an **operational runbook** for agents with **dual-path execution** (tccli/coscmd CLI and Python SDK).

> **UX Compliance:** Follows [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md) with minimal prompts and smart defaults.

### CLI applicability

- **`cli_applicability: dual-path`:** tccli for bucket operations; coscmd for object operations.

## Five Core Standards

| # | Standard | Implementation |
|---|----------|---------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT for bucket/object ops; delegate CDN/MySQL to their skills |
| 2 | **Structured I/O** | `{{env.*}}`/`{{user.*}}`/`{{output.*}}` with COS API fields |
| 3 | **Explicit Steps** | Pre-flight → Execute → Validate → Recover for bucket/object operations |
| 4 | **Failure Strategies** | 15+ COS error codes with HALT/retry logic |
| 5 | **Single Responsibility** | Bucket/Object operations only; delegate database/file system to their skills |

### Well-Architected Framework

| Pillar | Integration |
|--------|-------------|
| **可靠性** | Cross-region replication, versioning, lifecycle backup |
| **安全性** | ACL policies, encryption, bucket policy, access logging |
| **成本** | Storage tier optimization, lifecycle rules, idle bucket detection |
| **效率** | Multipart upload, batch operations, CDN integration |

## Trigger & Scope

### SHOULD Use

- User mentions "COS" OR "对象存储" OR "Object Storage" OR "Bucket"
- CRUD on buckets: create, describe, delete, configure ACL/policy/lifecycle
- Object operations: upload, download, delete, list, multipart upload
- Storage class management: STANDARD, STANDARD_IA, ARCHIVE, DEEP_ARCHIVE
- Keywords: bucket, object, storage class, multipart upload, lifecycle, versioning

### SHOULD NOT Use

- CDN operations → `qcloud-cdn-ops`
- MySQL/PostgreSQL → `qcloud-mysql-ops` / `qcloud-pg-ops`
- Billing/account → `qcloud-billing-ops`
- Console-only → State limitation

## Variables

| Placeholder | Meaning | Action |
|-------------|---------|--------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | Environment | NEVER ask user |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | Environment | NEVER ask user |
| `{{env.TENCENTCLOUD_REGION}}` | Environment | Use default if allowed |
| `{{user.bucket_name}}` | Bucket name (unique) | Ask once; validate naming |
| `{{user.object_key}}` | Object path | Ask once |
| `{{user.storage_class}}` | STANDARD/STANDARD_IA/ARCHIVE | Ask once; default STANDARD |
| `{{output.bucket_id}}` | `$.Response.Location` | Parse from response |
| `{{output.etag}}` | `$.Response.ETag` | Upload completion verification |

## Quick Start

```bash
# Create bucket
tccli cos PutBucket --Bucket "my-bucket-12345" --Region ap-guangzhou

# Upload object (coscmd recommended)
coscmd upload local-file.txt /bucket-name/path/file.txt

# Download object
coscmd download /bucket-name/path/file.txt ./local-file.txt
```

## Capabilities

| Operation | Description | Risk |
|-----------|-------------|------|
| PutBucket | Create bucket | Low |
| GetBucket | List objects | None |
| DeleteBucket | Delete empty bucket | **High** |
| PutObject | Upload object | Low |
| GetObject | Download object | None |
| DeleteObject | Delete object | **High** |
| PutBucketLifecycle | Set lifecycle rules | Medium |

## Execution Flows

### Create Bucket

#### Pre-flight

| Check | Expected | On Failure |
|-------|----------|------------|
| CLI (tccli/coscmd) | Installed | Install |
| Bucket name | RFC 952 compliant (unique) | Ask valid name |
| Region | Valid region code | Suggest valid |
| Quota | ≤ 200 buckets | HALT if exceeded |

#### CLI Execution

```bash
tccli cos PutBucket \
  --Bucket "{{user.bucket_name}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}"
```

#### SDK Fallback

```python
from tencentcloud.cos import cos_client, models
client = cos_client.CosClient(cred, region)
req = models.PutBucketRequest()
req.Bucket = "{{user.bucket_name}}"
resp = client.PutBucket(req)
```

#### Validation

Parse `$.Response.Location`, verify bucket exists via GetBucket.

#### Failure Recovery

| Error | Action |
|-------|--------|
| `BucketAlreadyExists` | Ask: reuse or new name |
| `InvalidBucketName` | Fix naming (lowercase, no underscore, globally unique) |
| `QuotaExceeded` | HALT; request quota increase |

### Upload Object

#### Pre-flight

| Check | Expected | On Failure |
|-------|----------|------------|
| Bucket exists | GetBucket succeeds | Create bucket first |
| File exists | Local file readable | HALT; check file path |
| Size ≤ 5GB (simple) | Check file size | Use multipart for >5GB |

#### CLI (coscmd)

```bash
coscmd upload "{{user.local_file}}" "/{{user.bucket_name}}/{{user.object_key}}"
```

#### Large File (>5GB): Multipart Upload

```bash
coscmd upload --multipart "{{user.local_file}}" "/{{user.bucket_name}}/{{user.object_key}}"
```

#### SDK Fallback

```python
#!/usr/bin/env python3
import os
from tencentcloud.common import credential
from tencentcloud.cos import cos_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = cos_client.CosClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.PutObjectRequest()
req.Bucket = "{{user.bucket_name}}"
req.Key = "{{user.object_key}}"
req.Body = file_content
req.StorageClass = "{{user.storage_class}}"
resp = client.PutObject(req)
etag = resp.ETag
print(f"Upload successful. ETag: {etag}")
```

### Get Object (Download)

#### Pre-flight

| Check | Expected | On Failure |
|-------|----------|------------|
| Bucket exists | GetBucket succeeds | HALT |
| Object exists | HeadObject succeeds | HALT |

#### CLI (coscmd)

```bash
coscmd download "/{{user.bucket_name}}/{{user.object_key}}" "{{user.local_file}}"
```

#### SDK Fallback

```python
#!/usr/bin/env python3
import os
from tencentcloud.common import credential
from tencentcloud.cos import cos_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = cos_client.CosClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.GetObjectRequest()
req.Bucket = "{{user.bucket_name}}"
req.Key = "{{user.object_key}}"
resp = client.GetObject(req)

# Save to file
with open("{{user.local_file}}", "wb") as f:
    f.write(resp.Body.read())
print("Download successful")
```

### Delete Object

#### Safety Gate (Mandatory)

1. **MUST** confirm: delete object `{{user.object_key}}` from bucket `{{user.bucket_name}}`
2. **MUST** warn: deletion is irreversible
3. **MUST NOT** proceed without explicit user assent

#### CLI (coscmd)

```bash
coscmd delete "/{{user.bucket_name}}/{{user.object_key}}"
```

#### SDK Fallback

```python
#!/usr/bin/env python3
import os
from tencentcloud.common import credential
from tencentcloud.cos import cos_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = cos_client.CosClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.DeleteObjectRequest()
req.Bucket = "{{user.bucket_name}}"
req.Key = "{{user.object_key}}"
resp = client.DeleteObject(req)
print(f"Deleted: {{user.object_key}}")
```

### List Objects

#### Pre-flight

| Check | Expected | On Failure |
|-------|----------|------------|
| Bucket exists | GetBucket succeeds | Create bucket first |

#### CLI (coscmd)

```bash
coscmd list "{{user.bucket_name}}"
```

#### SDK Fallback

```python
#!/usr/bin/env python3
import os, json
from tencentcloud.common import credential
from tencentcloud.cos import cos_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = cos_client.CosClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.ListObjectsRequest()
req.Bucket = "{{user.bucket_name}}"
req.MaxKeys = 1000
resp = client.ListObjects(req)

for obj in resp.Contents:
    print(f"{obj.Key} - {obj.Size} bytes")
```

#### Present to User

| Field | Path | Notes |
|-------|------|-------|
| Object Key | `$.Response.Contents[].Key` | Full object path |
| Size | `$.Response.Contents[].Size` | Size in bytes |
| Last Modified | `$.Response.Contents[].LastModified` | ISO timestamp |
| ETag | `$.Response.Contents[].ETag` | MD5 hash |
| Storage Class | `$.Response.Contents[].StorageClass` | STANDARD/IA/ARCHIVE |

### Delete Bucket

#### Safety Gate (Mandatory)

1. **MUST** check: bucket empty (ListObjects returns empty)
2. **MUST** warn: deletion irreversible
3. **MUST** confirm: user approval with bucket name displayed

```bash
# Pre-check
OBJECT_COUNT=$(coscmd list "{{user.bucket_name}}" | wc -l)
if [ "$OBJECT_COUNT" -gt 0 ]; then
  echo "Bucket not empty. Delete objects first."
  exit 1
fi

# Confirm
echo "Delete bucket: {{user.bucket_name}}? (yes/no)"
read CONFIRM
[ "$CONFIRM" = "yes" ] || exit 0

tccli cos DeleteBucket --Bucket "{{user.bucket_name}}"
```

#### SDK Fallback

```python
#!/usr/bin/env python3
import os
from tencentcloud.common import credential
from tencentcloud.cos import cos_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = cos_client.CosClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

# First check if bucket is empty
list_req = models.ListObjectsRequest()
list_req.Bucket = "{{user.bucket_name}}"
list_req.MaxKeys = 1
list_resp = client.ListObjects(list_req)

if list_resp.Contents:
    print("Bucket not empty. Delete objects first.")
    exit(1)

# Delete bucket
del_req = models.DeleteBucketRequest()
del_req.Bucket = "{{user.bucket_name}}"
resp = client.DeleteBucket(del_req)
print(f"Bucket deleted: {{user.bucket_name}}")
```

### Configure Lifecycle

```bash
tccli cos PutBucketLifecycle \
  --Bucket "{{user.bucket_name}}" \
  --LifecycleConfiguration '{"Rule":[{"ID":"archive-rule","Status":"Enabled","Filter":{"Prefix":""},"Transition":{"Days":30,"StorageClass":"ARCHIVE"}}]}'
```

## Error Codes (COS-Specific)

| Code | Meaning | Retry? | Action |
|------|---------|--------|--------|
| `NoSuchBucket` | Bucket not found | No | Verify bucket name |
| `BucketAlreadyExists` | Name taken | No | Ask new name |
| `AccessDenied` | Permission denied | No | Fix ACL/Policy |
| `InvalidBucketName` | Name invalid | No | Use RFC 952 naming |
| `QuotaExceeded` | Bucket quota reached | No | Request increase |
| `EntityTooLarge` | Object >5GB simple upload | No | Use multipart |
| `InvalidDigest` | ETag mismatch | No | Verify content |
| `RequestTimeout` | Upload timeout | Yes (3x) | Retry with smaller chunks |
| `SignatureDoesNotMatch` | Auth invalid | No | Fix credentials |
| `NoSuchKey` | Object not found | No | Verify key path |
| `InvalidStorageClass` | Unknown class | No | Use STANDARD/STANDARD_IA/ARCHIVE |
| `MalformedXML` | Policy malformed | No | Fix JSON/XML format |
| `BucketNotEmpty` | Cannot delete non-empty | No | Delete objects first |
| `InvalidRegion` | Region invalid | No | Use valid region |
| `InternalError` | Server error | Yes (3x) | Retry with RequestId |

## Safety Gates

Every **DeleteBucket/DeleteObject** MUST have:

1. Explicit confirmation with identifier
2. Impact warning (objects will be lost)
3. Empty check for bucket deletion
4. Post-delete verification (poll until 404)

## Output Schema

```json
{
  "Response": {
    "RequestId": "abc123",
    "Location": "my-bucket-12345.cos.ap-guangzhou.myqcloud.com",
    "Bucket": "my-bucket-12345"
  }
}
```

## Storage Classes

| Class | Name | Use Case | Cost Tier |
|-------|------|----------|-----------|
| STANDARD | 标准存储 | Hot data, frequent access | Highest |
| STANDARD_IA | 低频存储 | Less frequent (>30 days) | Medium |
| ARCHIVE | 影归存储 | Archive (>60 days) | Low |
| DEEP_ARCHIVE | 深度归档 | Long-term archive (>180 days) | Lowest |

## References

- [Core Concepts](references/core-concepts.md)
- [API & SDK](references/api-sdk-usage.md)
- [CLI Usage](references/cli-usage.md)
- [Troubleshooting](references/troubleshooting.md)
- [Well-Architected](references/well-architected-assessment.md)
- [Integration](references/integration.md)
- [FinOps Cost Optimization](references/finops-cost-optimization.md)
- [SecOps Security Operations](references/secops-security-operations.md)
- [AIOps Best Practices](references/aiops-best-practices.md)