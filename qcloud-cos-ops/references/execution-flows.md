# COS Execution Flows — CLI/SDK Reference

> **Purpose:** This file contains the detailed **how-to** commands (CLI and SDK) for each COS operation. The parent `SKILL.md` describes **what-to-do** and references this file for implementation details.
>
> **Index:** Each section corresponds to a `## Execution Flows` subsection in `SKILL.md`. Cross-link anchors use the format `#N-operation-name`.

## Index

| § | Operation | CLI Command | SDK Command |
|---|-----------|-------------|-------------|
| 1 | [CreateBucket](#1-createbucket) | `tccli cos PutBucket` | `cos_client.CosClient.PutBucket` |
| 2 | [UploadObject](#2-uploadobject) | `coscmd upload` / `coscmd upload --multipart` | `cos_client.CosClient.PutObject` |
| 3 | [GetObject](#3-getobject) | `coscmd download` | `cos_client.CosClient.GetObject` |
| 4 | [DeleteObject](#4-deleteobject) | `coscmd delete` | `cos_client.CosClient.DeleteObject` |
| 5 | [ListObjects](#5-listobjects) | `coscmd list` | `cos_client.CosClient.ListObjects` |
| 6 | [DeleteBucket](#6-deletebucket) | `tccli cos DeleteBucket` | `cos_client.CosClient.DeleteBucket` |
| 7 | [ConfigureLifecycle](#7-configurelifecycle) | `tccli cos PutBucketLifecycle` | `cos_client.CosClient.PutBucketLifecycle` |
| 8 | [FinOpsAnalysis](#8-finopsanalysis) | CLI (multi-phase bash + CLS queries) | Python SDK (full automation) |

---

## 1. CreateBucket

### CLI

```bash
tccli cos PutBucket \
  --Bucket "{{user.bucket_name}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}"
```

### SDK (Python)

```python
from tencentcloud.common import credential
from qcloud_cos import CosClient
from qcloud_cos import CosConfig, CosRequestError
from qcloud_cos.utils import UtilAuto

cred = credential.Credential(
    "{{env.TENCENTCLOUD_SECRET_ID}}",
    "{{env.TENCENTCLOUD_SECRET_KEY}}"
)
client = cos_client.CosClient(cred, "{{env.TENCENTCLOUD_REGION}}")

req = models.PutBucketRequest()
req.Bucket = "{{user.bucket_name}}"
resp = client.PutBucket(req)
resp.to_json_string()  # → "{\"Response\": {\"RequestId\": \"...\"}}"
```

---

## 2. UploadObject

### CLI

```bash
# Simple upload (≤ 5GB)
coscmd upload "{{user.local_file}}" "/{{user.bucket_name}}/{{user.object_key}}"

# Large file (> 5GB): multipart upload
coscmd upload --multipart "{{user.local_file}}" "/{{user.bucket_name}}/{{user.object_key}}"
```

### SDK (Python)

```python
from tencentcloud.common import credential
from qcloud_cos import CosClient
from qcloud_cos import CosConfig, CosRequestError
from qcloud_cos.utils import UtilAuto

cred = credential.Credential(
    "{{env.TENCENTCLOUD_SECRET_ID}}",
    "{{env.TENCENTCLOUD_SECRET_KEY}}"
)
client = cos_client.CosClient(cred, "{{env.TENCENTCLOUD_REGION}}")

req = models.PutObjectRequest()
req.Bucket = "{{user.bucket_name}}"
req.Key = "{{user.object_key}}"
req.Body = open("{{user.local_file}}", "rb")
req.StorageClass = "{{user.storage_class}}"
resp = client.PutObject(req)
resp.to_json_string()  # → "{\"Response\": {\"ETag\": \"...\"}}"
```

---

## 3. GetObject

### CLI

```bash
coscmd download "/{{user.bucket_name}}/{{user.object_key}}" "{{user.local_file}}"
```

### SDK (Python)

```python
from tencentcloud.common import credential
from qcloud_cos import CosClient
from qcloud_cos import CosConfig, CosRequestError
from qcloud_cos.utils import UtilAuto

cred = credential.Credential(
    "{{env.TENCENTCLOUD_SECRET_ID}}",
    "{{env.TENCENTCLOUD_SECRET_KEY}}"
)
client = cos_client.CosClient(cred, "{{env.TENCENTCLOUD_REGION}}")

req = models.GetObjectRequest()
req.Bucket = "{{user.bucket_name}}"
req.Key = "{{user.object_key}}"
resp = client.GetObject(req)

# Save response body to file
with open("{{user.local_file}}", "wb") as f:
    f.write(resp.Body.read())
resp.to_json_string()  # → "{\"Response\": {\"ObjectURL\": \"...\"}}"
```

---

## 4. DeleteObject

### CLI

```bash
coscmd delete "/{{user.bucket_name}}/{{user.object_key}}"
```

### SDK (Python)

```python
from tencentcloud.common import credential
from qcloud_cos import CosClient
from qcloud_cos import CosConfig, CosRequestError
from qcloud_cos.utils import UtilAuto

cred = credential.Credential(
    "{{env.TENCENTCLOUD_SECRET_ID}}",
    "{{env.TENCENTCLOUD_SECRET_KEY}}"
)
client = cos_client.CosClient(cred, "{{env.TENCENTCLOUD_REGION}}")

req = models.DeleteObjectRequest()
req.Bucket = "{{user.bucket_name}}"
req.Key = "{{user.object_key}}"
resp = client.DeleteObject(req)
resp.to_json_string()  # → "{\"Response\": {\"RequestId\": \"...\"}}"
```

---

## 5. ListObjects

### CLI

```bash
coscmd list "{{user.bucket_name}}"
```

### SDK (Python)

```python
from tencentcloud.common import credential
from qcloud_cos import CosClient
from qcloud_cos import CosConfig, CosRequestError
from qcloud_cos.utils import UtilAuto

cred = credential.Credential(
    "{{env.TENCENTCLOUD_SECRET_ID}}",
    "{{env.TENCENTCLOUD_SECRET_KEY}}"
)
client = cos_client.CosClient(cred, "{{env.TENCENTCLOUD_REGION}}")

req = models.ListObjectsRequest()
req.Bucket = "{{user.bucket_name}}"
req.MaxKeys = 1000
resp = client.ListObjects(req)
resp.to_json_string()  # → "{\"Response\": {\"Contents\": [...]}}"
```

---

## 6. DeleteBucket

### CLI

```bash
# Pre-check: verify bucket is empty
OBJECT_COUNT=$(coscmd list "{{user.bucket_name}}" | wc -l)
if [ "$OBJECT_COUNT" -gt 0 ]; then
  echo "Bucket not empty. Delete objects first."
  exit 1
fi

# Confirm with user
echo "Delete bucket: {{user.bucket_name}}? (yes/no)"
read CONFIRM
[ "$CONFIRM" = "yes" ] || exit 0

# Delete bucket
tccli cos DeleteBucket \
  --Bucket "{{user.bucket_name}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}"
```

### SDK (Python)

```python
from tencentcloud.common import credential
from qcloud_cos import CosClient
from qcloud_cos import CosConfig, CosRequestError
from qcloud_cos.utils import UtilAuto

cred = credential.Credential(
    "{{env.TENCENTCLOUD_SECRET_ID}}",
    "{{env.TENCENTCLOUD_SECRET_KEY}}"
)
client = cos_client.CosClient(cred, "{{env.TENCENTCLOUD_REGION}}")

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
resp.to_json_string()  # → "{\"Response\": {\"RequestId\": \"...\"}}"
```

---

## 7. ConfigureLifecycle

### CLI

```bash
tccli cos PutBucketLifecycle \
  --Bucket "{{user.bucket_name}}" \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --LifecycleConfiguration '{"Rule":[{"ID":"archive-rule","Status":"Enabled","Filter":{"Prefix":""},"Transition":{"Days":30,"StorageClass":"ARCHIVE"}}]}'
```

### SDK (Python)

```python
from tencentcloud.common import credential
from qcloud_cos import CosClient
from qcloud_cos import CosConfig, CosRequestError
from qcloud_cos.utils import UtilAuto

cred = credential.Credential(
    "{{env.TENCENTCLOUD_SECRET_ID}}",
    "{{env.TENCENTCLOUD_SECRET_KEY}}"
)
client = cos_client.CosClient(cred, "{{env.TENCENTCLOUD_REGION}}")

req = models.PutBucketLifecycleRequest()
req.Bucket = "{{user.bucket_name}}"
req.LifecycleConfiguration = {
    "Rule": [{
        "ID": "archive-rule",
        "Status": "Enabled",
        "Filter": {"Prefix": ""},
        "Transition": {"Days": 30, "StorageClass": "ARCHIVE"}
    }]
}
resp = client.PutBucketLifecycle(req)
resp.to_json_string()  # → "{\"Response\": {\"RequestId\": \"...\"}}"
```

---

## 8. FinOpsAnalysis

### CLI (5-Phase)

```bash
#!/bin/bash
# Phase 1: Collect COS Metadata
echo "=== Phase 1: COS Metadata Collection ==="
BUCKETS=$(tccli cos DescribeBuckets --Region {{env.TENCENTCLOUD_REGION}} | jq -r '.Response.Buckets[].Name')
BUCKET_COUNT=$(echo "$BUCKETS" | wc -l | tr -d ' ')
echo "Buckets found: $BUCKET_COUNT"

HAS_LOGGING=0
HAS_LIFECYCLE=0
for bucket in $BUCKETS; do
  LOGGING=$(tccli cos GetBucketLogging --Bucket "$bucket" --Region {{env.TENCENTCLOUD_REGION}} 2>/dev/null)
  if echo "$LOGGING" | jq -e '.Response.BucketLoggingStatus.TargetBucket' > /dev/null 2>&1; then
    HAS_LOGGING=$((HAS_LOGGING + 1))
  fi
  LIFECYCLE=$(tccli cos GetBucketLifecycle --Bucket "$bucket" --Region {{env.TENCENTCLOUD_REGION}} 2>/dev/null)
  RULES=$(echo "$LIFECYCLE" | jq '.Response.Rules | length // 0')
  if [ "$RULES" -gt 0 ]; then
    HAS_LIFECYCLE=$((HAS_LIFECYCLE + 1))
  fi
done
echo "Buckets with logging enabled: $HAS_LOGGING / $BUCKET_COUNT"
echo "Buckets with lifecycle rules: $HAS_LIFECYCLE / $BUCKET_COUNT"
echo "Phase 1 complete."

# Phase 2: Verify CLS COS Log Import
echo "=== Phase 2: CLS COS Log Verification ==="
RECHARGES=$(tccli cls DescribeCosRecharges \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --TopicId "{{user.topic_id}}" 2>/dev/null | jq '.Response.CosRecharges | length // 0')
if [ "$RECHARGES" -eq 0 ]; then
  echo "⚠️  No COS import task found. Delegate to qcloud-cls-ops."
else
  echo "✅ COS import task exists ($RECHARGES task(s))"
fi
INDEX_STATUS=$(tccli cls DescribeIndex \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --TopicId "{{user.topic_id}}" 2>/dev/null | jq -r '.Response.Status // "not found"')
echo "Index status: $INDEX_STATUS"
echo "Phase 2 complete."

# Phase 3: Execute CLS Cost Queries
echo "=== Phase 3: CLS Cost Analysis ==="
FROM_TIME=$(date -d '{{user.cost_time_range}}' +%s)000
TO_TIME=$(date +%s)000
TOPIC_ID="{{user.topic_id}}"
REGION="{{env.TENCENTCLOUD_REGION}}"

echo "--- 3a. Storage Class Distribution ---"
tccli cls SearchLog \
  --Region "$REGION" --TopicId "$TOPIC_ID" \
  --From $FROM_TIME --To $TO_TIME \
  --Query 'eventName:PutObject | select storageClass, count(*) as count, round(sum(objectSize)/1073741824, 2) as totalGB, round(avg(objectSize)/1048576, 2) as avgSizeMB group by storageClass order by totalGB desc' \
  --Limit 100

echo "--- 3b. Request Cost by Operation ---"
tccli cls SearchLog \
  --Region "$REGION" --TopicId "$TOPIC_ID" \
  --From $FROM_TIME --To $TO_TIME \
  --Query '| select eventName, count(*) as count, round(sum(reqBytesSent)/1073741824, 2) as uploadGB, round(sum(resBytesSent)/1073741824, 2) as downloadGB group by eventName order by count desc' \
  --Limit 100

echo "--- 3c. Traffic TOP 10 Consumers ---"
tccli cls SearchLog \
  --Region "$REGION" --TopicId "$TOPIC_ID" \
  --From $FROM_TIME --To $TO_TIME \
  --Query '| select remoteIp, round(sum(resBytesSent)/1073741824, 2) as downloadGB, round(sum(reqBytesSent)/1073741824, 2) as uploadGB, count(*) as count group by remoteIp order by downloadGB desc limit 10'

echo "--- 3d. IA Storage Access Check ---"
tccli cls SearchLog \
  --Region "$REGION" --TopicId "$TOPIC_ID" \
  --From $FROM_TIME --To $TO_TIME \
  --Query 'storageClass:STANDARD_IA | select eventName, count(*) as count, round(sum(resBytesSent)/1048576, 2) as totalMB group by eventName order by count desc'

echo "--- 3e. Daily Storage Delta Trend ---"
tccli cls SearchLog \
  --Region "$REGION" --TopicId "$TOPIC_ID" \
  --From $(date -d '30 days ago' +%s)000 \
  --To $TO_TIME \
  --Query '| select date_trunc('\''day'\'', eventTime) as day, round(sum(deltaDataSize)/1073741824, 2) as deltaGB, count(*) as count group by day order by day'

echo "Phase 3 complete."

# Phase 4: Idle Resource Detection
echo "=== Phase 4: Idle Resource Detection ==="
echo "--- 4a. Empty Bucket Detection ---"
for bucket in $(tccli cos DescribeBuckets --Region {{env.TENCENTCLOUD_REGION}} | jq -r '.Response.Buckets[].Name'); do
  OBJ_COUNT=$(tccli cos ListObjects --Bucket "$bucket" --Region {{env.TENCENTCLOUD_REGION}} --MaxKeys 1 2>/dev/null | jq '.Response.Contents | length // 0')
  if [ "$OBJ_COUNT" -eq 0 ]; then
    echo "  🔴 Empty bucket: $bucket"
  fi
done

echo "--- 4b. Bucket Access Summary (30d) ---"
tccli cls SearchLog \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '30 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query 'eventName:GetObject | select bucketName, count(*) as accessCount group by bucketName order by accessCount'

echo "--- 4c. Large Files (>1GB) with Low Access ---"
tccli cls SearchLog \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '{{user.cost_time_range}}' +%s)000 \
  --To $(date +%s)000 \
  --Query '| select reqPath, round(objectSize/1073741824, 2) as sizeGB, count(*) as accessCount, storageClass, max(eventTime) as lastAccess group by reqPath, sizeGB, storageClass having sizeGB > 1 order by accessCount asc limit 20'

echo "Phase 4 complete."

# Phase 5: Generate FinOps Report
echo "=== Phase 5: Generating FinOps Report ==="
REPORT_FILE="/tmp/cos-finops-report-$(date +%Y%m%d).md"
cat > "$REPORT_FILE" << REPORT_EOF
# COS FinOps Analysis Report
**Generated**: $(date '+%Y-%m-%d %H:%M:%S')
**Region**: {{env.TENCENTCLOUD_REGION}}
**Analysis Window**: {{user.cost_time_range}}

## Quick Summary
- **Buckets**: $BUCKET_COUNT | **Logging**: $HAS_LOGGING/$BUCKET_COUNT | **Lifecycle**: $HAS_LIFECYCLE/$BUCKET_COUNT
- **Storage Cost**: Refer to finops-cost-optimization.md Section 2 for calculation
- **Request Cost**: Refer to finops-cost-optimization.md Section 3 for calculation
- **Traffic Cost**: Refer to finops-cost-optimization.md Section 4 for calculation

## Key Findings
1. **Idle Resources**: Check Phase 4 output for empty buckets and unused objects
2. **Storage Optimization**: Check Phase 3d for IA storage access frequency
3. **Cost Anomalies**: Check Phase 3e for daily storage delta spikes
4. **Traffic Consumers**: Check Phase 3c for top bandwidth users

## Recommendations
- Run \`tccli cos PutBucketLifecycle\` to set lifecycle rules for unconfigured buckets
- Run \`tccli cls SearchLog\` with cost analysis queries (see finops-cost-optimization.md)
- Review idle buckets and consider deletion or data migration
REPORT_EOF

echo "✅ Report generated: $REPORT_FILE"
echo "{{output.finops_report_path}} = $REPORT_FILE"
```

### SDK (Python)

```python
#!/usr/bin/env python3
"""
COS FinOps: Full automated cost analysis
"""
import os, json, subprocess, datetime
from tencentcloud.common import credential
from qcloud_cos import CosClient
from qcloud_cos import CosConfig, CosRequestError
from qcloud_cos.utils import UtilAuto
from tencentcloud.cls import cls_client as cls_sdk, models as cls_models

REGION = os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou")
TOPIC_ID = os.environ.get("TOPIC_ID")
COST_DAYS = int(os.environ.get("COST_DAYS", "30"))

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
cos_client_inst = cos_client.CosClient(cred, REGION)
cls_client_inst = cls_sdk.ClsClient(cred, REGION)

# Phase 1: Collect COS metadata
print("=== Phase 1: COS Metadata ===")
req = models.DescribeBucketsRequest()
resp = json.loads(cos_client_inst.DescribeBuckets(req))
buckets = resp.get('Response', {}).get('Buckets', [])
print(f"Buckets: {len(buckets)}")

# Phase 2: Check CLS setup
print("\n=== Phase 2: CLS Verification ===")
cos_req = cls_models.DescribeCosRechargesRequest()
cos_req.TopicId = TOPIC_ID
recharges = json.loads(cls_client_inst.DescribeCosRecharges(cos_req))
recharge_count = len(recharges.get('Response', {}).get('CosRecharges', []))
print(f"COS import tasks: {recharge_count}")

# Phase 3: CLS Cost Queries
print("\n=== Phase 3: CLS Cost Analysis ===")
search_req = cls_models.SearchLogRequest()
search_req.TopicId = TOPIC_ID
search_req.From = int(datetime.datetime.now().timestamp()) - (COST_DAYS * 86400)
search_req.To = int(datetime.datetime.now().timestamp())

try:
    search_req.Query = 'eventName:PutObject | select storageClass, count(*) as c, round(sum(objectSize)/1073741824, 2) as tGB group by storageClass'
    search_req.Limit = 100
    resp = json.loads(cls_client_inst.SearchLog(search_req))
    results = resp.get('Response', {}).get('Results', [])
    print(f"Storage class distribution: {len(results)} entries")
except Exception as e:
    print(f"CLS query failed: {e} (index may not be ready)")

print("\n✅ FinOps Analysis Complete")
print("See references/finops-cost-optimization.md for full cost calculations")
```
