---
name: qcloud-cls-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud CLS (Cloud Log Service) — log collection, storage, indexing, querying,
  and analysis. User mentions CLS, 日志服务, Cloud Log Service, log collection,
  log search, or describes log management scenarios (e.g., application logs,
  system logs, audit logs, log shipping, log analysis) even without naming the
  product directly. Not for metrics monitoring (use qcloud-monitor-ops),
  standalone COS operations (use qcloud-cos-ops), or database operations.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python-cls),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "2026-05-28"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/614"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli cls help` - CLI exposes CreateLogset, DeleteLogset,
    CreateTopic, DeleteTopic, CreateIndex, DeleteIndex, SearchLog,
    CreateMachineGroup, DeleteMachineGroup, CreateConfig, DeleteConfig,
    CreateShipper, DeleteShipper, CreateAlarm, DeleteAlarm, and 50+ more operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud CLS Operations Skill

## Overview

CLS (Cloud Log Service) is Tencent Cloud's fully managed log service providing log collection, storage, indexing, querying, and analysis. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **`tccli` CLI** and **Python SDK fallback**), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

> **UX Compliance:** This skill follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`**: Official `tccli` fully supports CLS. You **MUST** ship **`references/cli-usage.md`** and, in **each** execution flow below, document **both** the SDK step **and** the `tccli` step. CLI is the **primary** execution path for simplicity; Python SDK is used for edge-case operations CLI doesn't expose or for complex parameter handling.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) per operation |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover |
| 4 | **Complete Failure Strategies** | Error taxonomy with ≥ 12 CLS-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (CLS), primary resource model (Logset + Topic + Index) |

Refer to the [meta-skill](../qcloud-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions.

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-AZ log storage, log shipping to COS/CKafka for DR, index auto-rebuild, data lifecycle management | `references/well-architected-assessment.md` |
| **安全性 (Security)** | CAM permissions, log encryption at rest, log encryption in transit (TLS), access control for log search | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Log retention policies, log shipping to COS for cold storage, log sampling configuration, index optimization | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | High-performance log search (SQL-like syntax), real-time alerting, automated log collection, machine group auto-scaling | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "CLS" OR "日志服务" OR "Cloud Log Service" OR "log service"
- Task involves CRUD or lifecycle operations on **Logsets** (CreateLogset, DeleteLogset, ModifyLogset)
- Task involves **Topics** (CreateTopic, DeleteTopic, ModifyTopic) — the log storage unit
- Task involves **Index configuration** (CreateIndex, DeleteIndex, ModifyIndex) — for log search and analysis
- Task involves **Log search/query** (SearchLog) — SQL-like syntax for log analysis
- Task involves **Machine Groups** (CreateMachineGroup, DeleteMachineGroup, DescribeMachineGroups) — log collection agents
- Task involves **Collection Configs** (CreateConfig, DeleteConfig, ModifyConfig) — log source configuration
- Task involves **Log shipping** (CreateShipper, DeleteShipper) — to COS, CKafka, SCF, DLC
- Task involves **Alarm rules** (CreateAlarm, DeleteAlarm, ModifyAlarm) — for log-based alerting
- Task keywords: create logset, create topic, search logs, query logs, log collection, log agent, ship logs, log analysis, log retention, index fields
- User asks to deploy, configure, troubleshoot, or monitor CLS **via API, SDK, CLI, or automation**
- User describes log aggregation, centralized logging, or log analysis scenarios without naming the product
- User asks to **analyze COS access logs** — troubleshoot object access failures, audit operations, identify security threats, analyze request performance, or review cost/storage distribution
- Task involves **importing COS data into CLS** for further analysis
- Keywords: COS log analysis, cos access log, COS 访问日志分析, audit COS operations, analyze COS requests, COS 审计
- User asks to **analyze COS access logs** — audit trail, troubleshooting (e.g., why an object is inaccessible), security analysis (anomalous IPs), or performance analysis (slow requests)
- User describes importing COS data into CLS for log analysis
- Keywords: COS access log, COS 访问日志, COS审计, COS分析, cos log analysis, import COS data, monitoring COS access

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: `qcloud-billing-ops` (when present)
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops` (when present)
- Task is **metrics monitoring** (Cloud Monitor metrics) → delegate to: `qcloud-monitor-ops`
- Task is **COS object storage** operations (buckets, objects) → delegate to: `qcloud-cos-ops`
- Task is **CKafka message queue** operations → delegate to: `qcloud-ckafka-ops`
- Task is **SCF serverless function** deployment → delegate to: `qcloud-scf-ops` (when present)
- Task is **TKE Kubernetes** log collection → use `qcloud-tke-ops` for TKE-specific log collection; use this skill for CLS backend operations
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented HTTP steps

### Delegation Rules

- CLS collection depends on CVM: verify CVM instances exist via `qcloud-cvm-ops` before creating machine groups
- CLS shipping to COS requires COS bucket: verify bucket exists via `qcloud-cos-ops` before CreateShipper
- CLS shipping to CKafka requires CKafka topic: verify topic exists via `qcloud-ckafka-ops` before CreateShipper
- **COS access log import requires COS bucket**: verify bucket exists and access logging is enabled via `qcloud-cos-ops` before CreateCosRecharge
- **COS access log analysis**: delegate COS bucket operations to `qcloud-cos-ops`; this skill handles CLS-side import and analysis
- TKE container logs can be collected to CLS: TKE skill creates collection config, this skill manages CLS backend
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs
- COS access log analysis requires enabling COS logging first: delegate to `qcloud-cos-ops` to verify/enable bucket logging before importing
- COS import task (`CreateCosRecharge`) depends on COS bucket: verify bucket exists via `qcloud-cos-ops` before creating import task

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use default `ap-guangzhou` if unset |
| `{{user.logset_name}}` | User-supplied logset name | Ask once; reuse |
| `{{user.logset_id}}` | User-supplied logset ID (e.g., `0f77c853-5c08-44f2-a3c3-5c0e8d3a9b12`) | Ask once; reuse |
| `{{user.topic_name}}` | User-supplied topic name | Ask once; reuse |
| `{{user.topic_id}}` | User-supplied topic ID (e.g., `e621fbc8-46d4-4b7a-bf12-6c6e7e8f9a0b`) | Ask once; reuse |
| `{{user.machine_group_name}}` | User-supplied machine group name | Ask once; reuse |
| `{{user.machine_group_id}}` | User-supplied machine group ID | Ask once; reuse |
| `{{user.config_name}}` | User-supplied collection config name | Ask once; reuse |
| `{{user.config_id}}` | User-supplied collection config ID | Ask once; reuse |
| `{{user.search_query}}` | User-supplied log search query (SQL syntax) | Ask once; reuse |
| `{{user.time_range}}` | User-supplied time range for log search | Ask once; default to last 1 hour |
| `{{user.cos_bucket}}` | COS bucket name with access logs | Ask once; validate naming |
| `{{user.cos_region}}` | COS bucket region (e.g., ap-guangzhou) | Ask once; default to env region |
| `{{user.cos_prefix}}` | COS log file prefix (e.g., `my-log/`) | Ask once; use root if empty |
| `{{user.cos_recharge_name}}` | COS import task name | Auto-generate if not provided |
| `{{output.cos_recharge_id}}` | From CreateCosRecharge response | Parse `$.Response.TaskId` or recharge ID |
| `{{output.logset_id}}` | From CreateLogset response | Parse `$.Response.LogsetId` |
| `{{output.topic_id}}` | From CreateTopic response | Parse `$.Response.TopicId` |
| `{{output.request_id}}` | From any API response | Parse `$.Response.RequestId` for tracking |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose `TENCENTCLOUD_SECRET_KEY` in any output. Mask all credentials with `***` or `<masked>`. Check existence only: `test -n "$TENCENTCLOUD_SECRET_KEY"` ✅ | `echo $TENCENTCLOUD_SECRET_KEY` ❌

## API and Response Conventions (Agent-Readable)

- **API spec is canonical**: https://cloud.tencent.com/document/api/614
- **Errors**: Tencent Cloud uses `Response.Error.Code` / `Response.Error.Message` pattern
- **Timestamps**: Unix timestamp (seconds) or ISO 8601 format depending on API
- **Idempotency**: Use `ClientToken` for Create operations to avoid duplicates on retry

### Example Response Field Table

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| CreateLogset | `$.Response.LogsetId` | string | New logset ID (UUID format) |
| DescribeLogsets | `$.Response.Logsets[0].LogsetId` | string | Logset ID |
| DescribeLogsets | `$.Response.Logsets[0].LogsetName` | string | Logset name |
| CreateTopic | `$.Response.TopicId` | string | New topic ID (UUID format) |
| DescribeTopics | `$.Response.Topics[0].TopicId` | string | Topic ID |
| DescribeTopics | `$.Response.Topics[0].TopicName` | string | Topic name |
| DescribeTopics | `$.Response.Topics[0].PartitionCount` | int | Number of partitions |
| SearchLog | `$.Response.Results[0].Timestamp` | int | Log timestamp (Unix) |
| SearchLog | `$.Response.Results[0].Content` | string | Log content |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| CreateLogset | — | `ACTIVE` | 2s | 30s |
| CreateTopic | — | `ACTIVE` | 2s | 30s |
| CreateIndex | — | `ACTIVE` | 5s | 60s |
| DeleteLogset | `ACTIVE` | absent (404) | 5s | 60s |
| DeleteTopic | `ACTIVE` | absent (404) | 5s | 60s |

## Quick Start

### What This Skill Does

This skill enables you to deploy, configure, troubleshoot, and monitor CLS (Cloud Log Service) log infrastructure using `tccli` CLI (primary) or `tencentcloud-sdk-python-cls` SDK (fallback).

### Execution Environments

| Environment | Setup Required | Use Case |
|-------------|---------------|----------|
| **Cloud Shell** | Zero setup | Quick operations, troubleshooting |
| **Local CLI** | Install tccli + credentials | Development, automation |
| **Local SDK** | Python 3.8+ + SDK package | Complex operations, batch processing |

### Option 1: Cloud Shell (Recommended for Quick Start)

**Zero-setup execution environment**:

1. Login to [Tencent Cloud Console](https://console.cloud.tencent.com)
2. Click **Cloud Shell** icon (top right toolbar)
3. Terminal opens with pre-installed `tccli` and SDK

```bash
# Cloud Shell is pre-authenticated - no credential setup needed
tccli cls DescribeLogsets --Region ap-guangzhou

# Save scripts to persistent storage
mkdir -p /data/scripts
# Files in /data/ persist across sessions
```

**Cloud Shell Features**:
- Pre-installed: `tccli`, `tencentcloud-sdk-python`, common tools
- Pre-authenticated: Uses console login credentials
- Persistent: 10GB storage in `/data/`
- Free: No additional cost

### Option 2: Local CLI Setup

**Prerequisites**:
- [ ] `tccli` CLI installed (`pip install tccli`)
- [ ] Credentials configured: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region set: `TENCENTCLOUD_REGION`

### Option 3: Python SDK Setup

**Prerequisites**:
- [ ] Python 3.8+ runtime
- [ ] SDK installed: `pip install tencentcloud-sdk-python-cls`
- [ ] Credentials configured

### Verify Setup (All Environments)

```bash
# Check CLI version
tccli version

# Test API access
tccli cls DescribeLogsets --Region ap-guangzhou

# Expected output (JSON)
# {"Response": {"Logsets": [...], "RequestId": "..."}}
```

### Your First Command

```bash
# List all logsets in current region
tccli cls DescribeLogsets --Region {{env.TENCENTCLOUD_REGION}}

# Cloud Shell: Use explicit region
tccli cls DescribeLogsets --Region ap-guangzhou
```

### Next Steps

- [Core Concepts](references/core-concepts.md) — Understand CLS architecture: Logset → Topic → Index → MachineGroup → Config
- [Common Operations](#execution-flows) — Create logset, create topic, search logs, configure collection
- [CLI Usage Guide](references/cli-usage.md) — Detailed CLI command reference
- [Integration Guide](references/integration.md) — Cloud Shell, SDK setup, automation
- [Troubleshooting](references/troubleshooting.md) — Fix common CLS issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreateLogset | Create new logset (log project container) | Low | Low |
| DescribeLogsets | View logset details | Low | None |
| DeleteLogset | Delete logset and all topics | Low | **High** — irreversible |
| CreateTopic | Create log topic (storage/shard unit) | Low | Low |
| DescribeTopics | View topic details and status | Low | None |
| DeleteTopic | Delete topic and all logs | Low | **High** — irreversible |
| CreateIndex | Configure index for log search | Medium | Low |
| DeleteIndex | Remove index (search disabled) | Low | Medium |
| SearchLog | Query logs with SQL syntax | Low | None |
| CreateMachineGroup | Create log collection agent group | Medium | Low |
| CreateConfig | Create log collection configuration | Medium | Low |
| CreateShipper | Ship logs to COS/CKafka | Medium | Low |
| CreateAlarm | Create log-based alarm rule | Medium | Low |
| ImportCOSAccessLogs | Import COS access logs to CLS for analysis | Medium | Low |
| COSAccessLogAnalysis | Analyze COS access logs — audit, troubleshooting, performance | Medium | None |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-28 | Initial skill with CreateLogset, CreateTopic, CreateIndex, SearchLog, CreateMachineGroup, CreateConfig, Delete operations |
| 1.1.0 | 2026-05-31 | Add ImportCOSAccessLogs and COSAccessLogAnalysis operations; add cos-log-analysis.md reference |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI and SDK) → Validate → Recover**. Do not skip phases.

### Operation: CreateLogset (Create Log Project)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI install | `tccli cls help CreateLogset` | Exit 0 | Install: `pip install tccli` |
| Credentials | Check `TENCENTCLOUD_SECRET_ID/KEY` env | Non-empty | HALT; configure env |
| Region | `tccli cls DescribeLogsets --Region {{env.TENCENTCLOUD_REGION}}` | Valid response | HALT; set valid region |
| Quota | `tccli cls DescribeLogsets` | Check quota usage | HALT; raise quota if full |

#### Execution — CLI (`tccli`) (Primary Path)

```bash
# Create logset
tccli cls CreateLogset \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --LogsetName "{{user.logset_name}}" \
  --ClientToken "$(date +%s%N)" > /tmp/response.json

# Capture logset ID from response
LOGSET_ID=$(jq -r '.Response.LogsetId' /tmp/response.json)
echo "Created Logset ID: $LOGSET_ID"
```

#### Execution — Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
"""
SDK fallback for CreateLogset when CLI is unavailable
"""
import os, json, time
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cls import cls_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = cls_client.ClsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateLogsetRequest()
        req.LogsetName = os.environ.get("LOGSET_NAME", "default-logset")
        req.ClientToken = str(int(time.time() * 1000000))

        resp = client.CreateLogset(req)
        result = json.loads(resp.to_json_string())
        print(json.dumps(result, indent=2))
        print(f"\nLogsetId: {result['Response']['LogsetId']}")
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

#### Post-execution Validation

1. Capture `{{output.logset_id}}` from `$.Response.LogsetId`
2. Verify logset exists:

```bash
# Verify logset exists
tccli cls DescribeLogsets \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --LogsetId "{{output.logset_id}}"
```

3. Report logset ID to user

#### Failure Recovery

| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| `InvalidParameter.LogsetName` | 0 | Fix logset name format; retry |
| `ResourceInUse.LogsetName` | 0 | Logset name already exists; use unique name |
| `QuotaExceeded.Logset` | 0 | HALT; Request quota increase |
| `RequestLimitExceeded` | 3, exp backoff | Back off and retry |
| `InternalError` | 3 (2s,4s,8s) | Retry; HALT with RequestId if persists |

---

### Operation: CreateTopic (Create Log Topic)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Logset exists | `tccli cls DescribeLogsets --LogsetId {{user.logset_id}}` | Logset found | HALT; create logset first |
| Quota | Check existing topics | Topic quota not exceeded | HALT; raise quota |

#### Execution — CLI

```bash
# Create topic
tccli cls CreateTopic \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --LogsetId "{{user.logset_id}}" \
  --TopicName "{{user.topic_name}}" \
  --PartitionCount 1 \
  --AutoSplit true \
  --MaxSplitPartitions 50 \
  --ClientToken "$(date +%s%N)" > /tmp/response.json

# Capture topic ID
TOPIC_ID=$(jq -r '.Response.TopicId' /tmp/response.json)
echo "Created Topic ID: $TOPIC_ID"
```

#### Execution — Python SDK

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.cls import cls_client, models
import os, json

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = cls_client.ClsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateTopicRequest()
        req.LogsetId = os.environ.get("LOGSET_ID")
        req.TopicName = os.environ.get("TOPIC_NAME", "default-topic")
        req.PartitionCount = int(os.environ.get("PARTITION_COUNT", "1"))
        req.AutoSplit = True
        req.MaxSplitPartitions = 50

        resp = client.CreateTopic(req)
        result = json.loads(resp.to_json_string())
        print(json.dumps(result, indent=2))
        print(f"\nTopicId: {result['Response']['TopicId']}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
```

#### Post-execution Validation

1. Capture `{{output.topic_id}}` from `$.Response.TopicId`
2. Verify topic exists:

```bash
tccli cls DescribeTopics \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --LogsetId "{{user.logset_id}}"
```

3. Report topic ID and partition count to user

#### Failure Recovery

| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| `ResourceNotFound.LogsetNotExist` | 0 | HALT; create logset first |
| `InvalidParameter.TopicName` | 0 | Fix topic name format; retry |
| `ResourceInUse.TopicName` | 0 | Topic name exists in logset; use unique name |
| `QuotaExceeded.Topic` | 0 | HALT; request quota increase |

---

### Operation: CreateIndex (Configure Log Index)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Topic exists | `tccli cls DescribeTopics --TopicId {{user.topic_id}}` | Topic found | HALT |
| No existing index | Check DescribeIndex response | Index not exists | Warn; confirm overwrite |

#### Execution — CLI

```bash
# Create index with field configuration
tccli cls CreateIndex \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --Rule '{"FullText":{"CaseSensitive":false,"Tokenizer":"@&()='\''%$"}}' \
  --Status true > /tmp/response.json

# Alternative: Create with key-value index fields
tccli cls CreateIndex \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --Rule '{
    "FullText": {"CaseSensitive": false, "Tokenizer": "@&()='\''%$"},
    "KeyValue": {
      "CaseSensitive": false,
      "KeyValues": [
        {"Key": "level", "Value": {"Type": "text", "Tokenizer": " "}},
        {"Key": "timestamp", "Value": {"Type": "long"}},
        {"Key": "message", "Value": {"Type": "text", "Tokenizer": "@&()='\''%$"}}
      ]
    }
  }' \
  --Status true
```

#### Execution — Python SDK

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.cls import cls_client, models
import os, json

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = cls_client.ClsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateIndexRequest()
        req.TopicId = os.environ.get("TOPIC_ID")
        
        # Configure index rule
        rule = {
            "FullText": {
                "CaseSensitive": False,
                "Tokenizer": "@&()='%$"
            },
            "KeyValue": {
                "CaseSensitive": False,
                "KeyValues": [
                    {"Key": "level", "Value": {"Type": "text", "Tokenizer": " "}},
                    {"Key": "timestamp", "Value": {"Type": "long"}},
                    {"Key": "message", "Value": {"Type": "text", "Tokenizer": "@&()='%$"}}
                ]
            }
        }
        req.Rule = json.dumps(rule)
        req.Status = True

        resp = client.CreateIndex(req)
        print(json.dumps(json.loads(resp.to_json_string()), indent=2))
        print("\n✅ Index created successfully")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
```

#### Post-execution Validation

1. Verify index is active:

```bash
tccli cls DescribeIndex \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --TopicId "{{user.topic_id}}"
```

2. Expected: `Status = true`, `Rule` contains configured fields

#### Failure Recovery

| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| `ResourceNotFound.TopicNotExist` | 0 | HALT; verify topic ID |
| `ResourceInUse.IndexAlreadyExist` | 0 | Index exists; use ModifyIndex or DeleteIndex first |
| `InvalidParameter.IndexRule` | 0 | Fix index rule format; refer to API spec |

---

### Operation: SearchLog (Query Logs)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Topic exists | `tccli cls DescribeTopics --TopicId {{user.topic_id}}` | Topic found | HALT |
| Index exists | `tccli cls DescribeIndex --TopicId {{user.topic_id}}` | Index configured | HALT; create index first |
| Time range | Parse `{{user.time_range}}` | Valid timestamps | Use default (last 1 hour) |

#### Execution — CLI

```bash
# Search logs with SQL-like query
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '1 hour ago' +%s) \
  --To $(date +%s) \
  --Query '{{user.search_query}}' \
  --Limit 100

# Example: Search error logs
# Query: 'level:ERROR AND message:*exception*'
```

#### Execution — Python SDK

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.cls import cls_client, models
import os, json, time

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = cls_client.ClsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.SearchLogRequest()
        req.TopicId = os.environ.get("TOPIC_ID")
        req.From = int(time.time()) - 3600  # 1 hour ago
        req.To = int(time.time())
        req.Query = os.environ.get("SEARCH_QUERY", "*")
        req.Limit = int(os.environ.get("LIMIT", "100"))

        resp = client.SearchLog(req)
        result = json.loads(resp.to_json_string())
        
        print(f"Total: {result['Response'].get('Count', 0)} logs")
        print("\nResults:")
        for log in result['Response'].get('Results', []):
            print(f"  [{log.get('Timestamp')}] {log.get('Content', '')[:200]}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
```

#### Present to User

| Field | Path | Notes |
|-------|------|-------|
| Count | `$.Response.Count` | Total matching logs |
| Timestamp | `$.Response.Results[].Timestamp` | Unix timestamp |
| Content | `$.Response.Results[].Content` | Log content (JSON or text) |
| Source | `$.Response.Results[].Source` | Log source file |
| Hostname | `$.Response.Results[].Hostname` | Source host |

#### Failure Recovery

| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| `ResourceNotFound.TopicNotExist` | 0 | HALT; verify topic ID |
| `InvalidParameter.QuerySyntax` | 0 | Fix query syntax; refer to query language doc |
| `LimitExceeded.SearchTimeRange` | 0 | Reduce time range; max 31 days per query |
| `RequestLimitExceeded` | 3, exp backoff | Back off and retry |

---

### Operation: CreateMachineGroup (Create Log Collection Agent Group)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CVM exists | Delegate to `qcloud-cvm-ops` DescribeInstances | CVM instances available | HALT; create CVM first |
| Machine group name | Validate format | Valid string | Fix name format |

#### Execution — CLI

```bash
# Create machine group with CVM IPs
tccli cls CreateMachineGroup \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --GroupName "{{user.machine_group_name}}" \
  --MachineGroupType '{"Type": "ip", "Values": ["10.0.1.10", "10.0.1.11"]}' \
  --ClientToken "$(date +%s%N)"

# Alternative: Use CVM instance IDs
tccli cls CreateMachineGroup \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --GroupName "{{user.machine_group_name}}" \
  --MachineGroupType '{"Type": "label", "Values": ["app:nginx", "env:prod"]}'
```

#### Execution — Python SDK

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.cls import cls_client, models
import os, json

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = cls_client.ClsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateMachineGroupRequest()
        req.GroupName = os.environ.get("GROUP_NAME", "default-group")
        
        # Machine group type: IP-based
        machine_group_type = {
            "Type": "ip",
            "Values": os.environ.get("CVM_IPS", "10.0.1.10").split(",")
        }
        req.MachineGroupType = json.dumps(machine_group_type)

        resp = client.CreateMachineGroup(req)
        result = json.loads(resp.to_json_string())
        print(json.dumps(result, indent=2))
        print(f"\nGroupId: {result['Response'].get('GroupId', 'N/A')}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
```

#### Post-execution Validation

1. Capture group ID from response
2. Verify machine group status:

```bash
tccli cls DescribeMachineGroups \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --GroupId "{{output.group_id}}"
```

#### Failure Recovery

| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| `InvalidParameter.GroupName` | 0 | Fix group name format |
| `ResourceInUse.GroupName` | 0 | Group name exists; use unique name |
| `InvalidParameterValue` | 0 | Check MachineGroupType format |

---

### Operation: CreateConfig (Create Collection Configuration)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Topic exists | `tccli cls DescribeTopics --TopicId {{user.topic_id}}` | Topic found | HALT |
| Machine group exists | `tccli cls DescribeMachineGroups` | Group found | HALT; create machine group |
| Log path | Validate format | Valid file path | Fix path format |

#### Execution — CLI

```bash
# Create collection config for application logs
tccli cls CreateConfig \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Name "{{user.config_name}}" \
  --TopicId "{{user.topic_id}}" \
  --Output '{"TopicId": "{{user.topic_id}}"}' \
  --Input '{
    "Content": {
      "Type": "container_stdout",
      "ContainerStdout": {
        "Namespace": "default",
        "IncludeLabels": {"app": "myapp"}
      }
    }
  }' \
  --MachineGroupIds '["{{user.machine_group_id}}"]'

# Alternative: Collect file logs
# Type can be: container_stdout, container_file, host_file
```

#### Execution — Python SDK

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.cls import cls_client, models
import os, json

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = cls_client.ClsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateConfigRequest()
        req.Name = os.environ.get("CONFIG_NAME", "default-config")
        req.TopicId = os.environ.get("TOPIC_ID")
        
        # Output configuration
        output = {"TopicId": os.environ.get("TOPIC_ID")}
        req.Output = json.dumps(output)
        
        # Input configuration - container stdout
        input_config = {
            "Content": {
                "Type": "container_stdout",
                "ContainerStdout": {
                    "Namespace": "default",
                    "IncludeLabels": {"app": "myapp"}
                }
            }
        }
        req.Input = json.dumps(input_config)
        
        # Associate with machine group
        req.MachineGroupIds = [os.environ.get("MACHINE_GROUP_ID", "")]

        resp = client.CreateConfig(req)
        print(json.dumps(json.loads(resp.to_json_string()), indent=2))
        print("\n✅ Config created successfully")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
```

#### Post-execution Validation

1. Verify config exists:

```bash
tccli cls DescribeConfigs \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --Filters '[{"Key": "topicId", "Values": ["{{user.topic_id}}"]}]'
```

2. Check collection status via console or wait 1-2 minutes for logs to appear

#### Failure Recovery

| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| `ResourceNotFound.TopicNotExist` | 0 | HALT; verify topic ID |
| `ResourceNotFound.MachineGroupNotExist` | 0 | HALT; verify machine group ID |
| `InvalidParameter.ConfigName` | 0 | Fix config name format |
| `InvalidParameter.InputConfig` | 0 | Check input configuration format |

---

### Operation: ImportCOSAccessLogs (Import COS Access Logs to CLS)

Import COS access logs into CLS for search and analysis. COS must have access logging enabled on the source bucket — logs are stored in a target bucket, then imported into CLS via `CreateCosRecharge`.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI install | `tccli cls help CreateCosRecharge` | Exit 0 | Install: `pip install tccli` |
| Credentials | Check `TENCENTCLOUD_SECRET_ID/KEY` env | Non-empty | HALT; configure env |
| COS bucket exists | Delegate to `qcloud-cos-ops` DescribeBuckets | Bucket exists | HALT; verify bucket |
| COS logging enabled | Check via COS console or `tccli cos GetBucketLogging` | Logging enabled | Guide user to enable COS access logging |
| CLS topic exists | `tccli cls DescribeTopics --TopicId {{user.topic_id}}` | Topic found | HALT; create topic first |
| No duplicate recharge | `tccli cls DescribeCosRecharges --TopicId {{user.topic_id}}` | No existing task | Warn; confirm overwrite |

#### Execution — CLI (`tccli`) (Primary Path)

```bash
# Preview COS import information before creating the task
tccli cls SearchCosRechargeInfo \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --Bucket "{{user.cos_bucket}}" \
  --BucketRegion "{{user.cos_region}}" \
  --LogType "minimalist_log" \
  --Prefix "{{user.cos_prefix}}"

# Create COS import task
tccli cls CreateCosRecharge \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --Bucket "{{user.cos_bucket}}" \
  --BucketRegion "{{user.cos_region}}" \
  --LogType "minimalist_log" \
  --Prefix "{{user.cos_prefix}}" \
  --TaskName "{{user.cos_recharge_name}}" \
  --Enable 1 > /tmp/response.json

# Capture recharge ID
RECHARGE_ID=$(jq -r '.Response.TaskId // .Response.RechargeId' /tmp/response.json)
echo "Created COS import task: $RECHARGE_ID"
```

#### Execution — Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
"""
SDK fallback for CreateCosRecharge when CLI is unavailable
"""
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cls import cls_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = cls_client.ClsClient(cred, os.environ.get("TENCENTCLOUD_REGION", "ap-guangzhou"))

        req = models.CreateCosRechargeRequest()
        req.TopicId = os.environ.get("TOPIC_ID")
        req.Bucket = os.environ.get("COS_BUCKET")
        req.BucketRegion = os.environ.get("COS_REGION", os.environ.get("TENCENTCLOUD_REGION"))
        req.LogType = os.environ.get("LOG_TYPE", "minimalist_log")
        req.Prefix = os.environ.get("COS_PREFIX", "")
        req.TaskName = os.environ.get("TASK_NAME", "cos-log-import")
        req.Enable = 1

        resp = client.CreateCosRecharge(req)
        result = json.loads(resp.to_json_string())
        print(json.dumps(result, indent=2))
        recharge_id = result.get('Response', {}).get('TaskId') or result.get('Response', {}).get('RechargeId')
        print(f"\n✅ COS import task created: {recharge_id}")
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

#### Post-execution Validation

1. Capture `{{output.cos_recharge_id}}` from response
2. Verify import task is active:

```bash
tccli cls DescribeCosRecharges \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --TopicId "{{user.topic_id}}"
```

3. Wait 1-2 minutes for initial log ingestion
4. Verify logs are available:

```bash
tccli cls SearchLog \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '10 minutes ago' +%s) \
  --To $(date +%s) \
  --Query '*' \
  --Limit 5
```

#### Failure Recovery

| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| `InvalidParameter.Bucket` | 0 | Verify COS bucket name and region |
| `InvalidParameter.TopicId` | 0 | HALT; verify CLS topic ID |
| `ResourceNotFound.BucketNotExist` | 0 | HALT; COS bucket does not exist |
| `ResourceNotFound.TopicNotExist` | 0 | HALT; CLS topic not found |
| `ResourceInUse.CosRechargeAlreadyExist` | 0 | Import task exists; use ModifyCosRecharge or delete first |
| `QuotaExceeded.CosRecharge` | 0 | HALT; too many import tasks per topic |
| `RequestLimitExceeded` | 3, exp backoff | Back off and retry |
| `InternalError` | 3 (2s,4s,8s) | Retry; HALT with RequestId if persists |

---

### Operation: COSAccessLogAnalysis (Analyze COS Access Logs)

Multi-step analysis of COS access logs imported into CLS. Covers troubleshooting, audit, security, and performance scenarios.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| COS logs imported | `tccli cls DescribeCosRecharges --TopicId {{user.topic_id}}` | Import task exists | Run ImportCOSAccessLogs first |
| Index configured | `tccli cls DescribeIndex --TopicId {{user.topic_id}}` | Index exists | Create COS log index (see cos-log-analysis.md) |
| Recent data | `SearchLog` with 5-min window | Results found | Wait for log ingestion (may take 2-5 min) |
| Time range | Parse user intent | Valid time range | Default to last 24h |

#### Execution Flow

**Step 1: Determine analysis scenario from user intent**

Classify the user's request into one of these scenarios:

| Scenario | User Keywords | Primary Fields |
|----------|--------------|----------------|
| Troubleshooting | "can't access", "object not found", "404 error" | `reqPath`, `resHttpCode`, `resErrorCode` |
| Audit | "who deleted", "who modified", "audit trail" | `eventName`, `requester`, `eventTime` |
| Security | "anomalous IP", "brute force", "suspicious" | `remoteIp`, `resHttpCode`, `requester` |
| Performance | "slow requests", "high latency", "timeout" | `resTotalTime`, `eventName` |
| Cost | "infrequent access", "cost optimization" | `reqPath`, `storageClass`, access count |
| General | No specific intent | Show overview dashboard |

**Step 2: Execute scenario-specific analysis**

> Full query templates and field definitions are in [references/cos-log-analysis.md](references/cos-log-analysis.md).

##### Scenario A: Troubleshooting

```bash
# Search by object path
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '{{user.time_range}}' +%s) \
  --To $(date +%s) \
  --Query 'reqPath:"{{user.req_path}}"' \
  --Limit 100

# Aggregate by HTTP status code
# resHttpCode aggregation requires SQL analysis in console
# CLI alternative: SearchLog with query='reqPath:"/path" AND resHttpCode:*'
```

##### Scenario B: Audit Trail

```bash
# Search for delete events on a specific path
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '{{user.time_range}}' +%s) \
  --To $(date +%s) \
  --Query 'eventName:DeleteObject AND reqPath:"{{user.req_path}}"' \
  --Limit 50

# Search all delete events in a bucket
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '{{user.time_range}}' +%s) \
  --To $(date +%s) \
  --Query 'eventName:DeleteObject AND bucketName:{{user.cos_bucket}}' \
  --Limit 200
```

##### Scenario C: Security Analysis

```bash
# Top requesting IPs
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '{{user.time_range}}' +%s) \
  --To $(date +%s) \
  --Query 'resHttpCode:403 OR resHttpCode:404' \
  --Limit 200

# Anonymous access attempts
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '{{user.time_range}}' +%s) \
  --To $(date +%s) \
  --Query 'requester:- AND resHttpCode:403' \
  --Limit 100
```

##### Scenario D: Performance Analysis

```bash
# Slow requests (resTotalTime > 1000ms)
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '{{user.time_range}}' +%s) \
  --To $(date +%s) \
  --Query 'resTotalTime:>1000' \
  --Limit 100 \
  --Sort desc
```

**Step 3: Present results to user**

| Scenario | Key Insights to Present |
|----------|------------------------|
| Troubleshooting | Show matching log count by resHttpCode; highlight 4xx/5xx; show latest error events |
| Audit | Show who (requester), when (eventTime), what eventName, source IP |
| Security | Show top IPs by error count; flag IPs with >100 errors; identify scan patterns |
| Performance | Show top 10 slowest requests; average latency by eventName |
| Cost | Show least-accessed objects; recommend storage class transitions |

Format results as structured Markdown tables:

```
### COS Access Log Analysis Results

**Scenario**: Troubleshooting — Object `/folder/text.txt` access failure

**Time Range**: Last 7 days
**Total Requests**: 142 | **Errors**: 8 (5.6%)

| resHttpCode | Count | Interpretation |
|-------------|-------|----------------|
| 200 | 134 | Success |
| 403 | 5 | Access Denied — check bucket policy |
| 404 | 3 | NoSuchKey — object may have been deleted |

**Latest Errors**:
| Time | Event | IP | Error Code | Requester |
|------|-------|----|------------|-----------|
| 2026-05-30T10:00Z | GetObject | 192.168.1.1 | AccessDenied | 100012345678:subuser |
```

#### Failure Recovery

| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| No data in time range | 0 | Expand time range or wait for COS import to complete |
| Index not found | 0 | HALT; create COS log index first (see cos-log-analysis.md) |
| Import task not found | 0 | HALT; run ImportCOSAccessLogs first |
| `InvalidParameter.QuerySyntax` | 0 | Fix query syntax; test with simple `*` first |
| `LimitExceeded.SearchTimeRange` | 0 | Reduce time range (max 31 days) |

#### Present to User

**Always** include:
1. Analysis scenario name
2. Time range examined
3. Summary statistics (total requests, error count, error rate)
4. Categorized findings with actionable insights
5. Reference to [cos-log-analysis.md](references/cos-log-analysis.md) for detailed queries

---

## Error Code Reference


| Error Code | Description | Retry | Agent Action | User Message |
|------------|-------------|-------|--------------|--------------|
| `InvalidParameter` | Parameter format invalid | 0 | Fix per API spec; retry | `[ERROR] Parameter invalid → Check format → Retry` |
| `InvalidParameterValue` | Parameter value invalid | 0 | Fix value; retry | `[ERROR] Invalid value → Correct input → Retry` |
| `ResourceNotFound.LogsetNotExist` | Logset does not exist | 0 | HALT; verify logset ID | `[ERROR] Logset not found → Verify LogsetId` |
| `ResourceNotFound.TopicNotExist` | Topic does not exist | 0 | HALT; verify topic ID | `[ERROR] Topic not found → Verify TopicId` |
| `ResourceNotFound.IndexNotExist` | Index does not exist | 0 | HALT; create index first | `[ERROR] Index not found → Create index first` |
| `ResourceNotFound.MachineGroupNotExist` | Machine group not found | 0 | HALT; verify group ID | `[ERROR] Machine group not found → Verify GroupId` |
| `ResourceInUse.LogsetName` | Logset name already exists | 0 | Use unique name | `[ERROR] Logset name in use → Choose unique name` |
| `ResourceInUse.TopicName` | Topic name already exists | 0 | Use unique name | `[ERROR] Topic name in use → Choose unique name` |
| `ResourceInUse.IndexAlreadyExist` | Index already exists | 0 | Use ModifyIndex or delete first | `[ERROR] Index exists → Modify or delete first` |
| `QuotaExceeded.Logset` | Logset quota exceeded | 0 | HALT; request quota increase | `[ERROR] Logset quota exceeded → Request increase` |
| `QuotaExceeded.Topic` | Topic quota exceeded | 0 | HALT; request quota increase | `[ERROR] Topic quota exceeded → Request increase` |
| `LimitExceeded.SearchTimeRange` | Search time range too large | 0 | Reduce to max 31 days | `[ERROR] Time range too large → Max 31 days` |
| `InvalidParameter.QuerySyntax` | Log query syntax error | 0 | Fix query syntax | `[ERROR] Query syntax error → Check syntax` |
| `RequestLimitExceeded` | API rate limit exceeded | 3 | Exponential backoff | `⚠️ Rate limit → Retrying...` |
| `OperationConflict` | Concurrent operation conflict | 3 | Wait; retry | `⚠️ Operation in progress → Waiting...` |
| `InternalError` | Internal server error | 3 | Retry; HALT if persists | `[ERROR] Internal error → Retry → Escalate` |
| `UnauthorizedOperation` | Permission denied | 0 | HALT; check CAM permissions | `[ERROR] Permission denied → Check CAM` |
| `InvalidParameter.Bucket` | COS bucket parameter invalid | 0 | Verify bucket name and region | `[ERROR] Invalid COS bucket → Verify name/region` |
| `ResourceNotFound.BucketNotExist` | COS bucket not found | 0 | HALT; verify bucket exists | `[ERROR] COS bucket not found → Verify bucket` |
| `ResourceInUse.CosRechargeAlreadyExist` | COS import task exists | 0 | Use ModifyCosRecharge or delete first | `[ERROR] Import task exists → Modify or delete first` |
| `QuotaExceeded.CosRecharge` | COS import task quota reached | 0 | HALT; delete unused import tasks | `[ERROR] Import task quota exceeded → Clean up tasks` |

## Safety Gates

### DeleteLogset Safety Gate

**MUST** obtain explicit confirmation before deleting:

```
⚠️ WARNING: Deleting logset will PERMANENTLY REMOVE all topics and logs within it.

Logset to delete: {{user.logset_name}} ({{user.logset_id}})
This action is IRREVERSIBLE and data cannot be recovered.

Topics that will be deleted:
- [List topics via DescribeTopics]

Confirm deletion by typing the logset name: {{user.logset_name}}
```

**MUST** check:
- No active collection configs using this logset
- No active alarm rules depending on this logset
- No log shipping tasks configured

### DeleteTopic Safety Gate

**MUST** obtain explicit confirmation before deleting:

```
⚠️ WARNING: Deleting topic will PERMANENTLY REMOVE all logs stored in it.

Topic to delete: {{user.topic_name}} ({{user.topic_id}})
Logset: {{user.logset_name}}
Estimated data loss: [Check storage size via DescribeTopics]

This action is IRREVERSIBLE.

Confirm deletion by typing: DELETE {{user.topic_name}}
```

**MUST** check:
- No active collection configs shipping to this topic
- No active index (delete index first if exists)
- No active alarm rules for this topic
- User has backup if needed

### DeleteIndex Safety Gate

**MUST** warn:

```
⚠️ WARNING: Deleting index will DISABLE log search for this topic.

Topic: {{user.topic_name}} ({{user.topic_id}})
Existing logs will remain but cannot be searched until index is recreated.

Proceed? (yes/no)
```

## Reference Directory

| File | Description |
|------|-------------|
| [references/cli-usage.md](references/cli-usage.md) | Complete tccli command reference for CLS |
| [references/core-concepts.md](references/core-concepts.md) | CLS architecture: Logset, Topic, Index, MachineGroup, Config |
| [references/cos-log-analysis.md](references/cos-log-analysis.md) | COS access log analysis — fields, scenarios, query templates |
| [references/troubleshooting.md](references/troubleshooting.md) | Common issues and solutions |
| [references/integration.md](references/integration.md) | SDK setup, Cloud Shell, automation patterns |
| [references/well-architected-assessment.md](references/well-architected-assessment.md) | Architecture review checklist |
| [references/query-language.md](references/query-language.md) | Log search syntax and examples |
| [examples/](../examples/) | Sample scripts and use cases |

---

*Generated for Tencent Cloud CLS Operations Skill v1.0.0*
