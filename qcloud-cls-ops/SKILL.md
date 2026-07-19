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
  version: "1.5.0"
  last_updated: "2026-07-05"
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

## Five Core Standards

> See [shared-boilerplate.md](../qcloud-skill-generator/SKILL.md#five-core-standards-quality-gates).

> Well-Architected pillars (Reliability, Security, Cost, Efficiency): see `references/well-architected-assessment.md`.

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
- Task is **architecture design review** / four-pillar Well-Architected assessment → delegate to: `qcloud-well-architected-review`

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
- Proactive inspection (read-only) → invoked by `qcloud-proactive-inspection`; see `references/proactive-inspection.md`
- Well-Architected assessment (read-only) → invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Read-only Well-Architected assessment for **CLS**; return `{{output.product_assessment}}`.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | reliability / security / cost / efficiency (or `all`) |
| `{{user.scope}}` | `single-resource` or `account-wide` |

**Allowed:** `Describe*`, `SearchLog` (read-only query) — **no** Create/Delete/Modify mutations.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: cls`).

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

### Response Field Summary

| Operation | Key Field Path | Description |
|-----------|----------------|-------------|
| CreateLogset | `$.Response.LogsetId` | New logset ID |
| DescribeLogsets | `$.Response.Logsets[].LogsetId/Name` | Logset list |
| CreateTopic | `$.Response.TopicId` | New topic ID |
| DescribeTopics | `$.Response.Topics[].TopicId/Name/PartitionCount` | Topic list |
| SearchLog | `$.Response.Results[].Timestamp/Content` | Log entries |

### State Transitions

| Operation | Initial → Target | Poll/Max |
|-----------|------------------|----------|
| CreateLogset/Topic | — → `ACTIVE` | 2s/30s |
| CreateIndex | — → `ACTIVE` | 5s/60s |
| DeleteLogset/Topic | `ACTIVE` → absent | 5s/60s |

## Quick Start

| Env | Setup |
|-----|-------|
| **Cloud Shell** | [Console](https://console.cloud.tencent.com) → Cloud Shell icon. Pre-installed `tccli`/SDK, pre-authenticated, 10GB `/data/`. Limit: 30min idle, 10 sessions, no CI/CD. |
| **Local CLI** | `pip install tccli` + `TENCENTCLOUD_SECRET_ID`/`_KEY`/`_REGION` |
| **Local SDK** | `pip install tencentcloud-sdk-python-cls` + same credentials |

```bash
# Verify (Cloud Shell or local)
tccli cls DescribeLogsets --Region "{{env.TENCENTCLOUD_REGION}}" && python3 -c "from tencentcloud.cls import cls_client"

# First command
tccli cls DescribeLogsets --Region {{env.TENCENTCLOUD_REGION}}
```

## Capabilities at a Glance

| Operation | Risk Level |
|-----------|------------|
| CreateLogset | Low |
| DescribeLogsets | None |
| DeleteLogset | **High** — irreversible |
| CreateTopic | Low |
| DescribeTopics | None |
| DeleteTopic | **High** — irreversible |
| CreateIndex | Low |
| DeleteIndex | Medium |
| SearchLog | None |
| CreateMachineGroup | Low |
| CreateConfig | Low |
| CreateShipper | Low |
| CreateAlarm | Low |
| ImportCOSAccessLogs | Low |
| COSAccessLogAnalysis | None |

## Changelog

> See `metadata.version` and `metadata.last_updated` in the frontmatter YAML.

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI and SDK) → Validate → Recover**. Do not skip phases.

> **SDK Templates:** Init/poll/error boilerplate → [references/sdk-templates.md](references/sdk-templates.md); Code examples → [references/sdk-code-examples.md](references/sdk-code-examples.md)

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

<!-- see references/failure-recovery-reference.md -->

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

<!-- see references/failure-recovery-reference.md -->

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


#### Post-execution Validation

1. Verify index is active:

```bash
tccli cls DescribeIndex \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --TopicId "{{user.topic_id}}"
```

2. Expected: `Status = true`, `Rule` contains configured fields

#### Failure Recovery

<!-- see references/failure-recovery-reference.md -->

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


#### Present to User

| Field | Path | Notes |
|-------|------|-------|
| Count | `$.Response.Count` | Total matching logs |
| Timestamp | `$.Response.Results[].Timestamp` | Unix timestamp |
| Content | `$.Response.Results[].Content` | Log content (JSON or text) |
| Source | `$.Response.Results[].Source` | Log source file |
| Hostname | `$.Response.Results[].Hostname` | Source host |

#### Failure Recovery

<!-- see references/failure-recovery-reference.md -->

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


#### Post-execution Validation

1. Capture group ID from response
2. Verify machine group status:

```bash
tccli cls DescribeMachineGroups \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --GroupId "{{output.group_id}}"
```

#### Failure Recovery

<!-- see references/failure-recovery-reference.md -->

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


#### Post-execution Validation

1. Verify config exists:

```bash
tccli cls DescribeConfigs \
  --Region {{env.TENCENTCLOUD_REGION}} \
  --Filters '[{"Key": "topicId", "Values": ["{{user.topic_id}}"]}]'
```

2. Check collection status via console or wait 1-2 minutes for logs to appear

#### Failure Recovery

<!-- see references/failure-recovery-reference.md -->

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

<!-- see references/failure-recovery-reference.md -->

---

### Operation: COSAccessLogAnalysis (Analyze COS Access Logs)

Multi-step analysis of COS access logs imported into CLS. Covers troubleshooting, audit, security, and performance scenarios.

→ 完整场景分类、查询模板、结果展示格式：见 [`references/cos-access-log-analysis.md`](references/cos-access-log-analysis.md)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| COS logs imported | `tccli cls DescribeCosRecharges --TopicId {{user.topic_id}}` | Import task exists | Run ImportCOSAccessLogs first |
| Index configured | `tccli cls DescribeIndex --TopicId {{user.topic_id}}` | Index exists | Create COS log index (see cos-log-analysis.md) |
| Recent data | `SearchLog` with 5-min window | Results found | Wait for log ingestion (may take 2-5 min) |
| Time range | Parse user intent | Valid time range | Default to last 24h |

#### Execution Flow

1. **Classify scenario** — map user intent to Troubleshooting / Audit / Security / Performance / Cost / General
2. **Execute** — run scenario-specific `SearchLog` query (see reference)
3. **Present** — structured Markdown table with key insights

#### Present to User

**Always** include:
1. Analysis scenario name
2. Time range examined
3. Summary statistics (total requests, error count, error rate)
4. Categorized findings with actionable insights
5. Reference to [cos-log-analysis.md](references/cos-log-analysis.md) for detailed queries

---

## Error Code Reference

> See `references/troubleshooting.md` and `references/failure-recovery-reference.md` for full list. Key codes:

| Code | Recovery |
|------|----------|
| `ResourceNotFound.*` | Verify resource ID |
| `ResourceInUse.*` | Resolve conflict first |
| `QuotaExceeded.*` | HALT; request quota increase |
| `RequestLimitExceeded` | Retry with exponential backoff |
| `UnauthorizedOperation` | HALT; check CAM permissions |
| `InternalError` | Retry 3x; escalate with RequestId |

## Quality Gate (GCL)

> Boilerplate: see [shared-boilerplate.md](../qcloud-skill-generator/SKILL.md#quality-gate-gcl).

### When the CLS loop runs

| Op class | Loop? | Why |
|---|---|---|
| Destructive: `DeleteLogset`, `DeleteTopic`, `DeleteIndex` | **yes** | No recycle bin; cascade to shippers and alarms |
| Sensitive mutating: `ModifyTopic` (retention reduction), `ModifyConfig`, `DeleteConfigAttachment` | **yes** | Hard-truncate historical data; collection gap |
| Mutating: `CreateLogset`, `CreateTopic`, `CreateIndex`, `CreateShipper`, `ApplyConfigToMachineGroup` | **yes** | Cost / search availability / pipeline risk |
| Read-only: `DescribeLogsets`, `DescribeTopics`, `DescribeIndex`, `SearchLog` | optional (max_iter=1) | Pre-flight for parent mutations |

### CLS-specific safety rules

> Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Ops | Gate (summary) |
|---:|---|---|
| 1 | `DeleteLogset` | Cascade check: enumerate all topics, shippers, alarms depending on this logset |
| 2 | `DeleteTopic` | Shipper orphan check: enumerate all shippers shipping to this topic |
| 3 | `ModifyTopic` (retention reduction) | Show current → target retention; warn historical data beyond new retention is deleted |
| 4 | `CreateIndex` | Show estimated storage cost per day before commit |
| 5 | `ModifyConfig` / `DeleteConfigAttachment` | Warn that existing machine group collection stops until re-apply |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — DeleteLogset with active COS shipper

Safety=0 (rule 1 violated — no shipper enumeration). `decision: ABORT`.
Recovery: Restore from COS archive if available; recreate pipeline.

See [`references/rubric.md`](references/rubric.md) §6 for full examples (PASS on `CreateTopic` + SAFETY_FAIL on `ModifyTopic` retention reduction).

> Decision flow: see [shared-boilerplate.md](../qcloud-skill-generator/SKILL.md#quality-gate-gcl).

## Reference Directory

> See [shared-boilerplate.md](../qcloud-skill-generator/SKILL.md#reference-directory).

Core: `references/cli-usage.md`, `references/core-concepts.md`, `references/failure-recovery-reference.md`, `references/sdk-templates.md`, `references/troubleshooting.md`, `references/well-architected-assessment.md`, `references/rubric.md`, `references/prompt-templates.md`.
Optional: `references/cos-log-analysis.md`, `references/query-language.md`, `references/integration.md`.

---


---

*Generated for Tencent Cloud CLS Operations Skill v1.0.0*
