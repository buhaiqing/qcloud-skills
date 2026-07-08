# COS Execution Flows — CLI/SDK Reference

> **Purpose:** This file contains the detailed **how-to** commands (CLI and SDK) for each COS operation. The parent `SKILL.md` describes **what-to-do** and references this file for implementation details.
>
> **Index:** Each section corresponds to a `## Execution Flows` subsection in `SKILL.md`. Cross-link anchors use the format `#N-operation-name`.
>
> **Path policy (verified):** COS has **no** `tccli cos` service. Object operations use the **coscmd** CLI; bucket/lifecycle/ACL/versioning operations use the **Python SDK** (`tencentcloud-sdk-python-cos`). Do not emit `tccli cos ...` commands — they do not exist.

## Index

| § | Operation | CLI Command | SDK Command |
|---|-----------|-------------|-------------|
| 1 | [CreateBucket](#1-createbucket) | — (SDK only) | `cos_client.CosClient.PutBucket` |
| 2 | [UploadObject](#2-uploadobject) | `coscmd upload` / `coscmd upload --multipart` | `cos_client.CosClient.PutObject` |
| 3 | [GetObject](#3-getobject) | `coscmd download` | `cos_client.CosClient.GetObject` |
| 4 | [DeleteObject](#4-deleteobject) | `coscmd delete` | `cos_client.CosClient.DeleteObject` |
| 5 | [ListObjects](#5-listobjects) | `coscmd list` | `cos_client.CosClient.ListObjects` |
| 6 | [DeleteBucket](#6-deletebucket) | — (SDK only) | `cos_client.CosClient.DeleteBucket` |
| 7 | [ConfigureLifecycle](#7-configurelifecycle) | — (SDK only) | `cos_client.CosClient.PutBucketLifecycle` |
| 8 | [FinOpsAnalysis](#8-finopsanalysis) | CLI (multi-phase bash + CLS queries) | Python SDK (full automation) |

---

## 1. CreateBucket

### CLI

> coscmd does **not** provide bucket creation. Use the Python SDK (below) or the COS Console.

### SDK (Python)

```python
from qcloud_cos import CosConfig, CosS3Client
import os

config = CosConfig(
    Region=os.environ.get("TENCENTCLOUD_REGION"),
    SecretId=os.environ.get("TENCENTCLOUD_SECRET_ID"),
    SecretKey=os.environ.get("TENCENTCLOUD_SECRET_KEY"),
)
client = CosS3Client(config)

resp = client.create_bucket(Bucket="{{user.bucket_name}}")
# resp -> bucket location
```

---

## 2. UploadObject

### CLI (coscmd)

```bash
# Simple upload (≤ 5GB)
coscmd upload "{{user.local_file}}" "/{{user.bucket_name}}/{{user.object_key}}"

# Large file (> 5GB): multipart upload
coscmd upload --multipart "{{user.local_file}}" "/{{user.bucket_name}}/{{user.object_key}}"
```

### SDK (Python)

```python
from qcloud_cos import CosConfig, CosS3Client
import os

config = CosConfig(
    Region=os.environ.get("TENCENTCLOUD_REGION"),
    SecretId=os.environ.get("TENCENTCLOUD_SECRET_ID"),
    SecretKey=os.environ.get("TENCENTCLOUD_SECRET_KEY"),
)
client = CosS3Client(config)

with open("{{user.local_file}}", "rb") as f:
    resp = client.put_object(
        Bucket="{{user.bucket_name}}",
        Key="{{user.object_key}}",
        Body=f.read(),
        StorageClass="{{user.storage_class}}",
    )
# resp['ETag'] -> MD5 hash for integrity verification
```

---

## 3. GetObject

### CLI (coscmd)

```bash
coscmd download "/{{user.bucket_name}}/{{user.object_key}}" "{{user.local_file}}"
```

### SDK (Python)

```python
from qcloud_cos import CosConfig, CosS3Client
import os

config = CosConfig(
    Region=os.environ.get("TENCENTCLOUD_REGION"),
    SecretId=os.environ.get("TENCENTCLOUD_SECRET_ID"),
    SecretKey=os.environ.get("TENCENTCLOUD_SECRET_KEY"),
)
client = CosS3Client(config)

resp = client.get_object(
    Bucket="{{user.bucket_name}}",
    Key="{{user.object_key}}",
)

with open("{{user.local_file}}", "wb") as f:
    f.write(resp['Body'].get_raw_stream().read())
```

---

## 4. DeleteObject

### CLI (coscmd)

```bash
coscmd delete "/{{user.bucket_name}}/{{user.object_key}}"
```

### SDK (Python)

```python
from qcloud_cos import CosConfig, CosS3Client
import os

config = CosConfig(
    Region=os.environ.get("TENCENTCLOUD_REGION"),
    SecretId=os.environ.get("TENCENTCLOUD_SECRET_ID"),
    SecretKey=os.environ.get("TENCENTCLOUD_SECRET_KEY"),
)
client = CosS3Client(config)

resp = client.delete_object(
    Bucket="{{user.bucket_name}}",
    Key="{{user.object_key}}",
)
```

---

## 5. ListObjects

### CLI (coscmd)

```bash
coscmd list "{{user.bucket_name}}"

# With prefix
coscmd list "{{user.bucket_name}}" -p logs/
```

### SDK (Python)

```python
from qcloud_cos import CosConfig, CosS3Client
import os

config = CosConfig(
    Region=os.environ.get("TENCENTCLOUD_REGION"),
    SecretId=os.environ.get("TENCENTCLOUD_SECRET_ID"),
    SecretKey=os.environ.get("TENCENTCLOUD_SECRET_KEY"),
)
client = CosS3Client(config)

marker = None
all_objects = []
while True:
    resp = client.list_objects(
        Bucket="{{user.bucket_name}}",
        MaxKeys=1000,
        Marker=marker,
    )
    all_objects.extend(resp.get("Contents", []))
    if not resp.get("IsTruncated"):
        break
    marker = resp.get("NextMarker")
```

---

## 6. DeleteBucket

### CLI

> coscmd does **not** provide bucket deletion. Use the Python SDK (below).

### SDK (Python)

```python
from qcloud_cos import CosConfig, CosS3Client
import os

config = CosConfig(
    Region=os.environ.get("TENCENTCLOUD_REGION"),
    SecretId=os.environ.get("TENCENTCLOUD_SECRET_ID"),
    SecretKey=os.environ.get("TENCENTCLOUD_SECRET_KEY"),
)
client = CosS3Client(config)

# First verify the bucket is empty (live + non-current versions + DeleteMarkers)
resp = client.list_objects(
    Bucket="{{user.bucket_name}}",
    MaxKeys=1,
)
if resp.get("Contents"):
    print("Bucket not empty. Delete objects first.")
    raise SystemExit(1)

# Soft-delete guard: abort if versioning is enabled (non-current versions remain)
ver_resp = client.get_bucket_versioning(Bucket="{{user.bucket_name}}")
if ver_resp.get("Status") == "Enabled":
    print("Versioning enabled: list and delete all versions + DeleteMarkers first.")
    raise SystemExit(1)

client.delete_bucket(Bucket="{{user.bucket_name}}")
```

> **Note:** The safety gate in `SKILL.md` (empty check + versioning guard) must run before this call.

---

## 7. ConfigureLifecycle

### CLI

> coscmd does **not** provide lifecycle configuration. Use the Python SDK (below).

### SDK (Python)

```python
from qcloud_cos import CosConfig, CosS3Client
import os

config = CosConfig(
    Region=os.environ.get("TENCENTCLOUD_REGION"),
    SecretId=os.environ.get("TENCENTCLOUD_SECRET_ID"),
    SecretKey=os.environ.get("TENCENTCLOUD_SECRET_KEY"),
)
client = CosS3Client(config)

client.put_bucket_lifecycle(
    Bucket="{{user.bucket_name}}",
    LifecycleConfiguration={
        "Rule": [{
            "ID": "archive-rule",
            "Status": "Enabled",
            "Filter": {"Prefix": ""},
            "Transition": {"Days": 30, "StorageClass": "ARCHIVE"},
        }]
    }
)
```

> **Safety:** Before applying a broad/empty-prefix `Transition → ARCHIVE`/`DEEP_ARCHIVE` or `Expiration` rule, surface the BEFORE/AFTER diff and require explicit re-confirmation (see `SKILL.md` Quality Gate rule 4).

---

## 8. FinOpsAnalysis

### CLI (5-Phase)

> **Path policy (verified):** COS has **no** `tccli cos` service. Bucket/metadata enumeration uses the **Python SDK** (`qcloud_cos`). Only the CLS query phases use `tccli cls`, which **is** a valid service.

```bash
#!/bin/bash
# Phase 1: Collect COS Metadata
echo "=== Phase 1: COS Metadata Collection ==="
BUCKETS=$(python3 - <<'PY'
from qcloud_cos import CosConfig, CosS3Client
import os
config = CosConfig(
    Region=os.environ["TENCENTCLOUD_REGION"],
    SecretId=os.environ["TENCENTCLOUD_SECRET_ID"],
    SecretKey=os.environ["TENCENTCLOUD_SECRET_KEY"],
)
client = CosS3Client(config)
buckets = client.list_buckets().get("Buckets", {}).get("Bucket", [])
print("\n".join(b.get("Name", "") for b in buckets))
PY
)
BUCKET_COUNT=$(echo "$BUCKETS" | grep -c .)
echo "Buckets found: $BUCKET_COUNT"
```

### SDK (Python)

```python
#!/usr/bin/env python3
"""
COS FinOps: Full automated cost analysis.
"""
import os
from qcloud_cos import CosConfig, CosS3Client
from tencentcloud.common import credential
from tencentcloud.cls import cls_client, models as cls_models

REGION = os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou")
TOPIC_ID = os.environ.get("TOPIC_ID")
COST_DAYS = int(os.environ.get("COST_DAYS", "30"))

# COS SDK setup
cos_config = CosConfig(
    Region=REGION,
    SecretId=os.environ.get("TENCENTCLOUD_SECRET_ID"),
    SecretKey=os.environ.get("TENCENTCLOUD_SECRET_KEY"),
)
cos_client_inst = CosS3Client(cos_config)

# CLS SDK setup
cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY"),
)
cls_client_inst = cls_client.ClsClient(cred, REGION)

# Phase 1: Collect COS metadata
print("=== Phase 1: COS Metadata ===")
buckets = cos_client_inst.list_buckets().get("Buckets", {}).get("Bucket", [])
print(f"Buckets: {len(buckets)}")

# Phase 2: Check CLS setup
print("\n=== Phase 2: CLS Verification ===")
cos_req = cls_models.DescribeCosRechargesRequest()
cos_req.TopicId = TOPIC_ID
recharge_count = len(cls_client_inst.DescribeCosRecharges(cos_req).CosRecharges)
print(f"COS import tasks: {recharge_count}")

# Phase 3: CLS Cost Queries
print("\n=== Phase 3: CLS Cost Analysis ===")
import datetime
search_req = cls_models.SearchLogRequest()
search_req.TopicId = TOPIC_ID
search_req.From = int(datetime.datetime.now().timestamp()) - (COST_DAYS * 86400)
search_req.To = int(datetime.datetime.now().timestamp())

try:
    search_req.Query = (
        "eventName:PutObject | select storageClass, count(*) as c, "
        "round(sum(objectSize)/1073741824, 2) as tGB group by storageClass"
    )
    search_req.Limit = 100
    results = cls_client_inst.SearchLog(search_req).Results
    print(f"Storage class distribution: {len(results)} entries")
except Exception as e:
    print(f"CLS query failed: {e} (index may not be ready)")

print("\n✅ FinOps Analysis Complete")
print("See references/finops-cost-optimization.md for full cost calculations")
```
