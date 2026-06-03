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
  version: "1.1.0"
  last_updated: "2026-06-04"
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
| **成本** | Storage tier optimization, lifecycle rules, idle bucket detection, **full FinOps analysis via CLI + CLS (see FinOpsAnalysis operation)** |
| **效率** | Multipart upload, batch operations, CDN integration |

## Trigger & Scope

### SHOULD Use

- User mentions "COS" OR "对象存储" OR "Object Storage" OR "Bucket"
- CRUD on buckets: create, describe, delete, configure ACL/policy/lifecycle
- Object operations: upload, download, delete, list, multipart upload
- Storage class management: STANDARD, STANDARD_IA, ARCHIVE, DEEP_ARCHIVE
- Keywords: bucket, object, storage class, multipart upload, lifecycle, versioning
- Keywords: cost analysis, FinOps, cost optimization, cost report, 成本, 费用分析, 成本优化, 节省成本, 成本报告, find savings, analyze costs
- User asks to analyze COS storage cost, request cost, traffic cost, or idle resources
- User asks to generate a COS cost report or identify optimization opportunities

### SHOULD NOT Use

- CDN operations → `qcloud-cdn-ops`
- MySQL/PostgreSQL → `qcloud-mysql-ops` / `qcloud-pg-ops`
- Billing/account → `qcloud-billing-ops`
- COS access log analysis (audit, troubleshooting, security) → delegate to `qcloud-cls-ops`
- Console-only → State limitation

### Delegation Rules

- COS access log analysis → delegate to `qcloud-cls-ops` with bucket name, region, and CLS topic
- COS access logging must be enabled before CLS can analyze logs (see [references/cls-analysis-guide.md](references/cls-analysis-guide.md))

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
| `{{user.cost_time_range}}` | Cost analysis time window | Ask once; default "30 days ago" |
| `{{user.cost_budget}}` | Monthly budget threshold (¥) | Optional; for budget alerts |
| `{{user.topic_id}}` | CLS topic ID with COS access logs | Inherit from CLS skill; ask if missing |
| `{{output.finops_report_path}}` | Path to generated FinOps report | Generated automatically |

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
| **FinOpsAnalysis** | **Full COS cost analysis via CLS: storage/request/traffic cost, idle detection, anomaly detection, trend prediction, report** | **None** |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial skill with bucket/object operations, lifecycle/ACL/versioning configuration, FinOpsAnalysis via CLS |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 COS-specific safety rules incl. versioning soft-delete, public ACL, broad-prefix cold transition, batch-delete DryRun), `references/prompt-templates.md` (Generator + Critic + Orchestrator, isolated-context enforcement, secret-content + public-ACL hygiene, FinOpsAnalysis read-only variant). `max_iter=2` per AGENTS.md §8 |

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

---

### FinOpsAnalysis (Full COS Cost Analysis)

Full automated COS FinOps analysis via CLI — collects COS metadata, queries CLS access logs, detects anomalies, identifies idle resources, and generates a structured cost report. **Dual-path**: CLI for metadata collection; CLS queries for cost dimensions.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI install | `tccli cos help` | Exit 0 | Install: `pip install tccli` |
| Credentials | Check `TENCENTCLOUD_SECRET_ID/KEY` env | Non-empty | HALT; configure env |
| Region | `{{env.TENCENTCLOUD_REGION}}` | Valid | Use default ap-guangzhou |
| COS buckets | `tccli cos DescribeBuckets` | ≥ 1 bucket | HALT; no COS resources |
| CLS CLI | `tccli cls help SearchLog` | Exit 0 | Install: `pip install tccli` |
| CLS topic | `tccli cls DescribeTopics --TopicId {{user.topic_id}}` | Topic exists | HALT; need CLS topic with COS logs |

#### Execution — CLI (Primary Path)

**Phase 1: Collect COS Metadata**

```bash
#!/bin/bash
echo "=== Phase 1: COS Metadata Collection ==="

# List all buckets
BUCKETS=$(tccli cos DescribeBuckets --Region {{env.TENCENTCLOUD_REGION}} | jq -r '.Response.Buckets[].Name')
BUCKET_COUNT=$(echo "$BUCKETS" | wc -l | tr -d ' ')
echo "Buckets found: $BUCKET_COUNT"

# For each bucket: check logging, lifecycle, tags
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
```

**Phase 2: Verify CLS COS Log Import**

```bash
echo "=== Phase 2: CLS COS Log Verification ==="

# Check if CLS COS import exists
RECHARGES=$(tccli cls DescribeCosRecharges \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --TopicId "{{user.topic_id}}" 2>/dev/null | jq '.Response.CosRecharges | length // 0')

if [ "$RECHARGES" -eq 0 ]; then
  echo "⚠️  No COS import task found for this topic."
  echo "→ Delegate to qcloud-cls-ops: ImportCOSAccessLogs"
  echo "→ Required: {{user.cos_bucket}}, {{user.cos_region}}, {{user.topic_id}}"
else
  echo "✅ COS import task exists ($RECHARGES task(s))"
fi

# Check if index exists for COS fields
INDEX_STATUS=$(tccli cls DescribeIndex \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --TopicId "{{user.topic_id}}" 2>/dev/null | jq -r '.Response.Status // "not found"')
echo "Index status: $INDEX_STATUS"
echo "Phase 2 complete."
```

**Phase 3: Execute CLS Cost Queries**

```bash
echo "=== Phase 3: CLS Cost Analysis ==="

FROM_TIME=$(date -d '{{user.cost_time_range}}' +%s)000
TO_TIME=$(date +%s)000
TOPIC_ID="{{user.topic_id}}"
REGION="{{env.TENCENTCLOUD_REGION}}"

# 3a. Storage class distribution
echo "--- 3a. Storage Class Distribution ---"
tccli cls SearchLog \
  --Region "$REGION" --TopicId "$TOPIC_ID" \
  --From $FROM_TIME --To $TO_TIME \
  --Query 'eventName:PutObject | select storageClass, count(*) as count, round(sum(objectSize)/1073741824, 2) as totalGB, round(avg(objectSize)/1048576, 2) as avgSizeMB group by storageClass order by totalGB desc' \
  --Limit 100

# 3b. Request cost by operation type
echo "--- 3b. Request Cost by Operation ---"
tccli cls SearchLog \
  --Region "$REGION" --TopicId "$TOPIC_ID" \
  --From $FROM_TIME --To $TO_TIME \
  --Query '| select eventName, count(*) as count, round(sum(reqBytesSent)/1073741824, 2) as uploadGB, round(sum(resBytesSent)/1073741824, 2) as downloadGB group by eventName order by count desc' \
  --Limit 100

# 3c. Traffic TOP consumers
echo "--- 3c. Traffic TOP 10 Consumers ---"
tccli cls SearchLog \
  --Region "$REGION" --TopicId "$TOPIC_ID" \
  --From $FROM_TIME --To $TO_TIME \
  --Query '| select remoteIp, round(sum(resBytesSent)/1073741824, 2) as downloadGB, round(sum(reqBytesSent)/1073741824, 2) as uploadGB, count(*) as count group by remoteIp order by downloadGB desc limit 10'

# 3d. Infrequent storage check
echo "--- 3d. IA Storage Access Check ---"
tccli cls SearchLog \
  --Region "$REGION" --TopicId "$TOPIC_ID" \
  --From $FROM_TIME --To $TO_TIME \
  --Query 'storageClass:STANDARD_IA | select eventName, count(*) as count, round(sum(resBytesSent)/1048576, 2) as totalMB group by eventName order by count desc'

# 3e. Daily storage delta
echo "--- 3e. Daily Storage Delta Trend ---"
tccli cls SearchLog \
  --Region "$REGION" --TopicId "$TOPIC_ID" \
  --From $(date -d '30 days ago' +%s)000 \
  --To $TO_TIME \
  --Query '| select date_trunc('day', eventTime) as day, round(sum(deltaDataSize)/1073741824, 2) as deltaGB, count(*) as count group by day order by day'

echo "Phase 3 complete."
```

**Phase 4: Idle Resource Detection**

```bash
echo "=== Phase 4: Idle Resource Detection ==="

# 4a. Detect empty buckets
echo "--- 4a. Empty Bucket Detection ---"
for bucket in $(tccli cos DescribeBuckets --Region {{env.TENCENTCLOUD_REGION}} | jq -r '.Response.Buckets[].Name'); do
  OBJ_COUNT=$(tccli cos GetBucket --Bucket "$bucket" --Region {{env.TENCENTCLOUD_REGION}} --MaxKeys 1 2>/dev/null | jq '.Response.Contents | length // 0')
  if [ "$OBJ_COUNT" -eq 0 ]; then
    echo "  🔴 Empty bucket: $bucket"
  fi
done

# 4b. Detect buckets with no recent access (via CLS)
echo "--- 4b. Bucket Access Summary (30d) ---"
tccli cls SearchLog \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '30 days ago' +%s)000 \
  --To $(date +%s)000 \
  --Query 'eventName:GetObject | select bucketName, count(*) as accessCount group by bucketName order by accessCount'

# 4c. Detect large unused objects
echo "--- 4c. Large Files (>1GB) with Low Access ---"
tccli cls SearchLog \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '{{user.cost_time_range}}' +%s)000 \
  --To $(date +%s)000 \
  --Query '| select reqPath, round(objectSize/1073741824, 2) as sizeGB, count(*) as accessCount, storageClass, max(eventTime) as lastAccess group by reqPath, sizeGB, storageClass having sizeGB > 1 order by accessCount asc limit 20'

echo "Phase 4 complete."
```

**Phase 5: Generate FinOps Report**

```bash
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
- Run `tccli cos PutBucketLifecycle` to set lifecycle rules for unconfigured buckets
- Run `tccli cls SearchLog` with cost analysis queries (see finops-cost-optimization.md)
- Review idle buckets and consider deletion or data migration
REPORT_EOF

echo "✅ Report generated: $REPORT_FILE"
echo "{{output.finops_report_path}} = $REPORT_FILE"
```

#### Execution — Python SDK (Full Automation)

```python
#!/usr/bin/env python3
"""
COS FinOps: Full automated cost analysis
"""
import os, json, subprocess, datetime
from tencentcloud.common import credential
from tencentcloud.cos import cos_client, models
from tencentcloud.cls import cls_client as cls_sdk, models as cls_models

# --- Config ---
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
resp = json.loads(cos_client_inst.DescribeBuckets(req).to_json_string())
buckets = resp.get('Response', {}).get('Buckets', [])
print(f"Buckets: {len(buckets)}")

# Phase 2: Check CLS setup
print("\n=== Phase 2: CLS Verification ===")
cos_req = cls_models.DescribeCosRechargesRequest()
cos_req.TopicId = TOPIC_ID
recharges = json.loads(cls_client_inst.DescribeCosRecharges(cos_req).to_json_string())
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
    resp = json.loads(cls_client_inst.SearchLog(search_req).to_json_string())
    results = resp.get('Response', {}).get('Results', [])
    print(f"Storage class distribution: {len(results)} entries")
except Exception as e:
    print(f"CLS query failed: {e} (index may not be ready)")

print("\n✅ FinOps Analysis Complete")
print("See references/finops-cost-optimization.md for full cost calculations")
```

#### Post-execution Validation

1. Verify report file exists and has content: `test -f /tmp/cos-finops-report-*.md`
2. Verify CLS queries returned data (check result count > 0)
3. If no CLS data, produce **lightweight report** using only COS API metadata
4. Validation checklist:

| Check | Pass Criteria | Fallback |
|-------|-------------|----------|
| COS metadata | Buckets list populated | HALT; no data |
| CLS queries | ≥ 1 query returns data | API-only report (no cost breakdown) |
| Idle detection | Results found or confirmed none | Report with 0 idle resources |
| Report generation | .md file created | Print to stdout |

#### Present to User

Present the report path and key highlights:

```
✅ COS FinOps Analysis Complete

Report: /tmp/cos-finops-report-20260531.md

Highlights:
• Buckets analyzed: 5
• Storage cost: ~¥92.41/month (estimate — see finops-cost-optimization.md)
• Top traffic source: 192.168.1.1 (1250.5GB download)
• Anomalies detected: 1 (2026-05-04 storage spike 5.6x baseline)
• Recommendations: 4 (1 P0, 1 P1, 2 P2)

Next steps: Review references/finops-cost-optimization.md for detailed cost breakdown and optimization commands.
```

#### Failure Recovery

| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| No COS buckets | 0 | HALT; no resources to analyze |
| `NoSuchBucket` | 0 | Skip and continue; bucket may have been deleted |
| CLS `TopicNotExist` | 0 | HALT; instruct user to create topic or import COS logs via `qcloud-cls-ops` |
| `AuthFailure` | 0 | HALT; check TENCENTCLOUD_SECRET_ID/KEY |
| CLS query empty | 1 (expand time range) | Produce API-only report (no cost breakdown) |
| `RequestLimitExceeded` | 3, exp backoff | Add delay between queries |
| `InternalError` | 3 (2s,4s,8s) | Skip failed query; continue with remaining |

---

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

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate
is a **runtime** scoring layer that audits each COS execution against an explicit
rubric, in addition to the build-time **Safety Gates** above and the build-time
**2-round self-review** in [AGENTS.md](../../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **2** | per-skill override (matches AGENTS.md §8 default for `qcloud-cos-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 COS-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive bucket: `DeleteBucket` (must enumerate live + non-current + DeleteMarkers + incomplete multipart) | **yes** | Irreversible; needs scoring |
| Destructive object: `DeleteObject` (single & batch) on versioning-enabled bucket | **yes** | Soft-delete trap; needs scoring |
| Sensitive mutating: `PutBucketACL` (`public-read` / `public-read-write`), `PutBucketLifecycle` (transition to `ARCHIVE` / `DEEP_ARCHIVE` or `Expiration`) | **yes** | Exfil / cold-transition risk; needs scoring |
| Mutating: `PutBucket`, `PutObject`, multipart `MultiUpload`, `PutBucketPolicy`, `PutBucketCORS`, `PutBucketVersioning`, `PutBucketReplication` | **yes** | Cost / state-change / security risk; needs scoring |
| Read-only: `GetBucket`, `ListObjects`, `HeadObject`, `GetBucketACL`, `GetBucketLifecycle` | optional (max_iter=1, no hard abort) | Polling tails are part of the parent op's trace |
| `FinOpsAnalysis` (read-only, 5 phases) | optional (max_iter=5, no ABORT) | Read-only; lighter scoring per `prompt-templates.md` §4 |

### Decision flow (first match wins)

1. **Safety = 0** OR any rule violation in `{1, 2, 3, 4, 5}` ⇒ **ABORT** (no partial result). Secret-content leak in trace is also an unconditional ABORT.
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

### COS-specific safety rules (rubric §4)

The Critic checks 5 COS-specific rules independently of which operation ran:

1. `DeleteObject` on a **versioning-enabled** bucket — surface versioning status via `GetBucketVersioning`; require `VersionId` for hard delete OR explicit acknowledgement of `DeleteMarker` semantics; warn on `Status=Suspended`
2. `DeleteBucket` — enumerate live objects + non-current versions + DeleteMarkers + incomplete multipart uploads; surface ACL/bucket-policy/CORS/replication dependencies; explicit confirmation with all four counts
3. `PutBucketACL` with `public-read` / `public-read-write` — surface full object key listing; require user to confirm no key contains credentials / PII / private keys; warn ACL applies to ALL objects including pre-existing ones
4. `PutBucketLifecycle` with `Transition → ARCHIVE` / `DEEP_ARCHIVE` (or `Expiration`) — show BEFORE/AFTER rule diff; require re-confirmation when prefix is broad AND target is cold; require non-zero `Expiration.Days`
5. Batch delete: `coscmd delete -r`, `coscmd delete -f prefix/`, multi-object API with count > 1000 — MUST run `--dry-run` first and surface count + sample keys; require literal "yes, delete <count> objects" recurse-confirm; block if count > 10000 unless explicit `--force-bulk` rationale

Missing any of these ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — `PutBucketACL public-read` (silent)

| Dimension | Score |
|---|---|
| Correctness | 1 (ACL applied) |
| **Safety** | **0** (rule 3 violated — object enumeration not surfaced; `keys/` and `db-dumps/` likely exposed) |
| Idempotency | 1 |
| Traceability | 1 |
| Spec Compliance | 1 |

`decision: ABORT`. Recovery suggestion emitted: re-read all object keys via `ListObjects`; identify any sensitive prefixes; decide whether to (a) rotate credentials / PII if exposure is suspected, then (b) revert ACL to `private`; (c) use `PutBucketPolicy` for scoped public access to the docs prefix only.

See [`references/rubric.md`](references/rubric.md) §6 for two more examples (PASS on `DeleteObject` and RETRY on `PutBucketLifecycle`).

### Sibling — CVM & CDB Quality Gates

| Skill | Backbone | Distinctive §4 rule |
|---|---|---|
| [`qcloud-cvm-ops`](../cvm-ops/SKILL.md#quality-gate-gcl) | 5 dimensions + G/C/O | compute (instances, disks, re-image) |
| [`qcloud-cdb-ops`](../cdb-ops/SKILL.md#quality-gate-gcl) | 5 dimensions + G/C/O | database (accounts, privileges, data-plane boundary) |
| `qcloud-cos-ops` (this skill) | 5 dimensions + G/C/O | object storage (versioning, public ACL, cold transition, batch delete) |

---

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
- [CLS Analysis Guide](references/cls-analysis-guide.md) — COS access log analysis via CLS
- [FinOps Cost Optimization](references/finops-cost-optimization.md) — CLI-driven cost analysis
- [SecOps Security Operations](references/secops-security-operations.md)
- [AIOps Best Practices](references/aiops-best-practices.md)