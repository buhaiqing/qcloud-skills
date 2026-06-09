---
name: qcloud-ckafka-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or manage Tencent Cloud CKafka
  (Cloud Kafka) message queue service — instance lifecycle management, topic creation,
  consumer group monitoring, ACL rule management, message production/consumption, and
  performance diagnostics. User mentions CKafka, Kafka, 消息队列, 腾讯云CKafka, topic,
  partition, consumer group, or describes messaging/streaming scenarios even without naming
  the product directly. Not for billing, CAM, VPC-only, TDMQ, or related products that have
  their own ops skills.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python-ckafka),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.2.0"
  last_updated: "2026-06-09"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/597"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli ckafka help` - CLI exposes CreateInstance, DescribeInstances,
    ModifyInstanceAttributes, DeleteInstance, CreateTopic, DeleteTopic, DescribeTopic,
    CreatePartition, DescribeTopicDetail, CreateAcl, DeleteAcl, DescribeACL,
    DescribeConsumerGroup, CreateConsumerGroup, ModifyConsumerGroup, DeleteConsumerGroup,
    SendMessages, FetchMessageByOffset, DescribeInstanceAttributes, ModifyInstanceAttributes,
    DescribeRegion, DescribeTopicSubscribeGroup, DescribeGroupInfo, and 30+ more operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud CKafka Operations Skill

## Overview

CKafka (Cloud Kafka) is Tencent Cloud's fully managed, distributed message queue service built on Apache Kafka, providing high-throughput, low-latency messaging capabilities. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **`tccli` CLI** and **Python SDK fallback**), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

> **UX Compliance:** This skill follows the [User Experience Specification](../references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`**: Official `tccli` fully supports CKafka. You **MUST** ship **`references/cli-usage.md`** and, in **each** execution flow below, document **both** the SDK step **and** the `tccli` step. CLI is the **primary** execution path for simplicity; Python SDK is used for edge-case operations CLI doesn't expose or for complex parameter handling.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers (CKafka, Kafka, 消息队列) and delegation rules (TDMQ → other skills, VPC → qcloud-vpc-ops) |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented per operation |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps for CLI and SDK paths |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 12 CKafka-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (CKafka), primary resource model (Instance, Topic); cross-product delegation documented |

Refer to the [meta-skill](../qcloud-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions.

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-AZ CKafka deployment, automatic failover, data replication, consumer group rebalancing | `references/well-architected-assessment.md` |
| **安全性 (Security)** | CAM permissions, VPC network isolation, SASL/ACL authentication, SSL encryption | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Instance type right-sizing, prepaid vs pay-as-you-go, topic partition optimization, storage lifecycle | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Batch message processing, compression optimization, partition scaling, consumer lag monitoring | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "CKafka" OR "Kafka" OR "消息队列" OR "腾讯云CKafka" OR "腾讯云Kafka"
- Task involves CRUD or lifecycle operations on **CKafka Instances** (CreateInstance, DescribeInstances, ModifyInstanceAttributes, DeleteInstance)
- Task involves **Topic management** (CreateTopic, DeleteTopic, DescribeTopic, CreatePartition)
- Task involves **Consumer Group operations** (DescribeConsumerGroup, CreateConsumerGroup, ModifyConsumerGroup, DeleteConsumerGroup)
- Task involves **ACL and security** (CreateAcl, DeleteAcl, DescribeACL)
- Task involves **Message operations** (SendMessages, FetchMessageByOffset)
- Task keywords: kafka, ckafka, topic, partition, consumer group, message queue, broker, producer, consumer, offset, replication factor
- User asks to deploy, configure, troubleshoot, or monitor CKafka **via API, SDK, CLI, or automation**
- User describes messaging performance issues (consumer lag, message backlog, high latency) without naming product

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: `qcloud-billing-ops` (when present)
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops` (when present)
- Task is **VPC network only** (subnet, route table, NAT gateway) → delegate to: `qcloud-vpc-ops`
- Task is **TDMQ (Tencent Distributed Message Queue)** → delegate to: `qcloud-tdmq-ops` (when present)
- Task is **RocketMQ or other message queue services** → delegate to appropriate skills
- Task is **CVM / compute instance** → delegate to: `qcloud-cvm-ops`
- Task is **architecture design review** / four-pillar Well-Architected assessment → delegate to: `qcloud-well-architected-review`

### Delegation Rules

- CKafka depends on VPC: verify VPC/Subnet/SecurityGroup exist via `qcloud-vpc-ops` before CreateInstance
- CKafka uses Monitor for metrics: delegate alerting/dashboard to `qcloud-monitor-ops`
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs into one ambiguous flow
- Proactive inspection (read-only) → invoked by `qcloud-proactive-inspection`; see `references/proactive-inspection.md`
- Well-Architected assessment (read-only) → invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Read-only Well-Architected assessment for **CKafka**; return `{{output.product_assessment}}`.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | reliability / security / cost / efficiency (or `all`) |
| `{{user.scope}}` | `single-resource` or `account-wide` |

**Allowed:** `Describe*` and `GetMonitorData` only — **no** Create/Delete/Modify mutations.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: ckafka`).

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use documented default only if skill explicitly allows |
| `{{user.instance_id}}` | CKafka InstanceId (ckafka-xxxxxx) | Ask once; reuse |
| `{{user.instance_name}}` | User-supplied CKafka instance name | Ask once; reuse |
| `{{user.topic_name}}` | Topic name | Ask once; reuse |
| `{{user.partition_num}}` | Number of partitions | Default from existing config or ask |
| `{{user.replica_num}}` | Replication factor | Default 2 or 3 |
| `{{user.consumer_group_name}}` | Consumer group name | Ask once |
| `{{user.vpc_id}}` | User-supplied VPC ID | Ask once; reuse |
| `{{user.subnet_id}}` | User-supplied subnet ID | Ask once; reuse |
| `{{user.zone_id}}` | Availability zone ID | Ask once |
| `{{output.instance_id}}` | `$.Response.InstanceId` | Parse from API response |
| `{{output.topic_name}}` | `$.Response.TopicName` | Parse from CreateTopic response |
| `{{output.request_id}}` | `$.Response.RequestId` | Request tracking ID |
| `{{output.consumer_group_id}}` | `$.Response.ConsumerGroupId` | Parse from consumer group operations |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose `TENCENTCLOUD_SECRET_KEY`, `SecretKey`, or any credential field value. Credential verification MUST check existence only.

## API and Response Conventions

- **API spec is canonical** at https://cloud.tencent.com/document/api/597
- **Errors:** Map SDK/HTTP errors to `code` / `message` fields. Tencent Cloud uses `Response.Error` pattern
- **Async behavior:** Instance creation is async — poll DescribeInstances until Status = `1` (running)
- **Instance IDs:** Format `ckafka-xxxxxxxx`

### Instance Status Values

| Status Code | Description | Agent Action |
|-------------|-------------|--------------|
| `0` | Creating (创建中) | Wait for completion |
| `1` | Running (运行中) | Normal operational state |
| `2` | Deleting (删除中) | Wait for completion |
| `5` | Isolated (已隔离) | Instance unavailable, requires renewal or cleanup |
| `7` | Isolating (隔离中) | Wait for completion |

### Topic Status Values

| Status Code | Description | Agent Action |
|-------------|-------------|--------------|
| `0` | Normal (正常) | Topic operational |
| `1` | Deleting (删除中) | Wait for completion |
| `2` | Creating (创建中) | Wait for completion |
| `3` | Failed (创建失败) | Retry or escalate |

### Response Field Table

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| CreateInstance | `$.Response.InstanceId` | string | New instance ID (ckafka-xxx) |
| CreateInstance | `$.Response.RequestId` | string | Request tracking ID |
| DescribeInstances | `$.Response.Result[].InstanceId` | array | Instance IDs |
| DescribeInstances | `$.Response.Result[].Status` | number | 0=创建中, 1=运行中, 2=删除中, 5=已隔离, 7=隔离中 |
| DescribeInstances | `$.Response.Result[].InstanceName` | string | Instance name |
| DescribeInstances | `$.Response.Result[].KafkaVersion` | string | Kafka version (e.g., "2.4.1") |
| CreateTopic | `$.Response.Result.TopicId` | string | Topic ID |
| CreateTopic | `$.Response.Result.TopicName` | string | Topic name |
| DescribeTopic | `$.Response.Result.TopicList[].TopicName` | string | Topic name |
| DescribeTopic | `$.Response.Result.TopicList[].PartitionNum` | number | Number of partitions |
| DescribeConsumerGroup | `$.Response.Result.ConsumerGroupList[].ConsumerGroupName` | string | Consumer group name |
| DescribeConsumerGroup | `$.Response.Result.ConsumerGroupList[].ConsumeLag` | number | Consumer lag (messages) |

## Quick Start

### What This Skill Does

This skill enables you to deploy, configure, troubleshoot, and manage Tencent Cloud CKafka resources using the `tccli` CLI (primary) or `tencentcloud-sdk-python-ckafka` SDK (fallback).

### Prerequisites

- [ ] `tccli` CLI installed (or Python 3.8+ runtime for SDK fallback)
- [ ] Credentials configured: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region set: `TENCENTCLOUD_REGION`

### Verify Setup

```bash
tccli ckafka DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} --Limit 5
```

### Your First Command

```bash
# List CKafka instances
tccli ckafka DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} --Limit 10
```

### Next Steps

- [Core Concepts](references/core-concepts.md) — Understand CKafka architecture
- [Common Operations](#execution-flows) — Create instances, topics, manage consumer groups
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreateInstance | Create CKafka instance | High | Low |
| DescribeInstances | List CKafka instances | Low | None |
| ModifyInstanceAttributes | Update instance configuration | Medium | Medium |
| DeleteInstance | Terminate CKafka instance | Medium | **High** — irreversible |
| CreateTopic | Create Kafka topic | Low | Low |
| DeleteTopic | Delete Kafka topic | Low | **High** — data loss |
| DescribeConsumerGroup | Monitor consumer groups | Low | None |
| CreateConsumerGroup | Create consumer group | Low | Low |
| CreateAcl | Create ACL rule | Medium | Medium |
| SendMessages | Produce messages | Low | Low |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-28 | Initial API/SDK-oriented template with tccli CLI support |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 CKafka-specific safety rules incl. instance-delete cascade, topic-delete offset loss, partition rebalancing, broker-config retention drop, ACL open-access guard), `references/prompt-templates.md` (Generator + Critic + Orchestrator). `max_iter=2` per AGENTS.md §8 |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (SDK/API and tccli) → Validate → Recover**. Do not skip phases.

### Operation: CreateInstance (Create CKafka Instance)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Python SDK | `pip show tencentcloud-sdk-python-ckafka` | Version ≥ minimum | Document install |
| CLI / deps | `tccli version` | Exit code 0 | Document CLI install |
| Credentials | Check env vars | Non-empty values | HALT; user configures env |
| Region | Call DescribeInstances with limit 1 | Region valid | Suggest valid region |
| VPC/Subnet | Verify via qcloud-vpc-ops | VPC and subnet exist | HALT; create VPC first |
| Quota | Check `ResourceInsufficient` patterns | Sufficient quota | HALT; raise quota |

#### Execution — CLI (`tccli`) (Primary Path)

```bash
# Basic create (required params)
tccli ckafka CreateInstance \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ZoneId "{{user.zone_id}}" \
  --InstanceName "{{user.instance_name}}" \
  --VpcId "{{user.vpc_id}}" \
  --SubnetId "{{user.subnet_id}}" \
  --SpecType "standard" \
  --DiskType "CLOUD_SSD" \
  --DiskSize 1000 \
  --MsgRetentionTime 1440

# Professional tier with multi-AZ
tccli ckafka CreateInstance \
  --Region "ap-guangzhou" \
  --ZoneId "ap-guangzhou-3" \
  --InstanceName "my-ckafka-cluster" \
  --VpcId "vpc-xxxxxx" \
  --SubnetId "subnet-xxxxxx" \
  --SpecType "professional" \
  --DiskType "CLOUD_SSD" \
  --DiskSize 3000 \
  --MsgRetentionTime 10080 \
  --InstanceVersion "2.4.1"
```

#### Execution — Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
import os
import json
import time
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.ckafka.v20190819 import ckafka_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = ckafka_client.CkafkaClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.CreateInstanceRequest()
        req.ZoneId = "ap-guangzhou-3"
        req.InstanceName = "my-ckafka-cluster"
        req.VpcId = "vpc-xxxxxx"
        req.SubnetId = "subnet-xxxxxx"
        req.SpecType = "standard"
        req.DiskType = "CLOUD_SSD"
        req.DiskSize = 1000
        req.MsgRetentionTime = 1440
        req.InstanceVersion = "2.4.1"

        resp = client.CreateInstance(req)
        result = json.loads(resp.to_json_string())
        print(json.dumps(result, indent=2))

        instance_id = result["Response"]["InstanceId"]
        print(f"Instance created: {instance_id}")

    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

#### Post-execution Validation

1. Capture `{{output.instance_id}}` from response: `$.Response.InstanceId`
2. Poll `DescribeInstances` until `Status = 1` (running) or timeout:

```bash
# CLI polling with adaptive backoff
# Phase 1: Fast polling (first 5 min) - check every 10s
# Phase 2: Slow polling (after 5 min) - check every 30s
# Total timeout: 20 minutes
for i in $(seq 1 50); do
  STATUS=$(tccli ckafka DescribeInstances --InstanceIds '["{{output.instance_id}}"]' --Region {{env.TENCENTCLOUD_REGION}} | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['Response']['Result'][0]['Status'])")
  [ "$STATUS" = "1" ] && break
  # Adaptive sleep: 10s for first 30 checks (5 min), then 30s
  if [ $i -le 30 ]; then
    sleep 10
  else
    sleep 30
  fi
done

# Check timeout
if [ "$STATUS" != "1" ]; then
  echo "[ERROR] Timeout waiting for CKafka instance running status (current: $STATUS)"
  exit 1
fi
```

```python
# SDK polling with adaptive backoff
# Phase 1: Fast polling (first 5 min) - check every 10s
# Phase 2: Slow polling (after 5 min) - check every 30s
# Total timeout: 20 minutes
import time

for i in range(50):
    desc_req = models.DescribeInstancesRequest()
    desc_req.InstanceIds = ["{{output.instance_id}}"]
    resp = client.DescribeInstances(desc_req)
    status = json.loads(resp.to_json_string())["Response"]["Result"][0]["Status"]
    if status == 1:
        break
    # Adaptive sleep: 10s for first 30 checks (5 min), then 30s
    sleep_time = 10 if i < 30 else 30
    time.sleep(sleep_time)

# Check timeout
if status != 1:
    raise TimeoutError(f"CKafka instance not ready after 20 min (status: {status})")
```

3. On success, report `{{output.instance_id}}` and instance details to the user
4. On terminal failure, go to **Failure Recovery**

#### Failure Recovery

| Error pattern | Max retries | Backoff | Agent Action | UX Feedback |
|--------------|-------------|---------|--------------|-------------|
| `InvalidParameterValue` / invalid spec type | 0–1 | — | Fix spec type from valid list; retry once | `[ERROR] InvalidParameterValue: Spec type invalid. Use standard or professional.` |
| `ResourceInsufficient` / quota exceeded | 0 | — | HALT | `[ERROR] ResourceInsufficient: Quota limit reached. Delete unused resources or request quota increase.` |
| `InvalidVpcId` / `InvalidSubnetId` | 0 | — | HALT | `[ERROR] Invalid VPC or Subnet. Verify IDs via qcloud-vpc-ops.` |
| `InvalidSecretKey` / `InvalidSecretId` | 0 | — | HALT | `[ERROR] Credential invalid. Verify TENCENTCLOUD_SECRET_ID and TENCENTCLOUD_SECRET_KEY.` |
| `RequestLimitExceeded` / 429 | 3 | exponential | Back off; respect rate limit | `⚠️ Rate limit reached. Retrying in {backoff}s...` |
| `InternalError` / 5xx | 3 | 2s, 4s, 8s | Retry; then HALT with RequestId | `[ERROR] InternalError. Retry or escalate with RequestId.` |

---

### Operation: CreateTopic (Create Kafka Topic)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | DescribeInstances | Status = 1 (running) | HALT |
| Topic name valid | Regex check | Valid Kafka topic name | Fix naming |
| Partition/replica valid | Check limits | Within instance limits | Adjust values |

#### Execution — CLI

```bash
# Create topic with basic config
tccli ckafka CreateTopic \
  --InstanceId "{{user.instance_id}}" \
  --TopicName "{{user.topic_name}}" \
  --PartitionNum {{user.partition_num}} \
  --ReplicaNum {{user.replica_num}}

# Create topic with advanced config
tccli ckafka CreateTopic \
  --InstanceId "ckafka-xxxxxx" \
  --TopicName "order-events" \
  --PartitionNum 6 \
  --ReplicaNum 3 \
  --EnableWhiteList 0 \
  --RetentionMs 604800000 \
  --Note "Order processing events topic"
```

#### Execution — SDK

```python
req = models.CreateTopicRequest()
req.InstanceId = "{{user.instance_id}}"
req.TopicName = "{{user.topic_name}}"
req.PartitionNum = {{user.partition_num}}
req.ReplicaNum = {{user.replica_num}}
req.Note = "Created via API"
resp = client.CreateTopic(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

#### Post-execution Validation

```bash
# Verify topic creation
tccli ckafka DescribeTopic \
  --InstanceId "{{user.instance_id}}" \
  --TopicName "{{user.topic_name}}"
```

#### Key Response Fields

| Field | JSON Path | Description |
|-------|-----------|-------------|
| TopicId | `$.Response.Result.TopicId` | Topic unique ID |
| TopicName | `$.Response.Result.TopicName` | Topic name |

#### Failure Recovery

| Error pattern | Max retries | Agent Action |
|--------------|-------------|--------------|
| `TopicAlreadyExists` | 0 | HALT — topic already exists |
| `InvalidParameterValue` | 0–1 | Fix parameters; retry once |
| `ResourceUnavailable` | 3 | Retry with backoff |

---

### Operation: DescribeConsumerGroup (Monitor Consumer Groups)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | DescribeInstances | Status = 1 | HALT |

#### Execution — CLI

```bash
# List all consumer groups
tccli ckafka DescribeConsumerGroup \
  --InstanceId "{{user.instance_id}}" \
  --Offset 0 \
  --Limit 20

# List with filter
tccli ckafka DescribeConsumerGroup \
  --InstanceId "ckafka-xxxxxx" \
  --SearchWord "order-consumer"
```

#### Execution — SDK

```python
req = models.DescribeConsumerGroupRequest()
req.InstanceId = "{{user.instance_id}}"
req.Offset = 0
req.Limit = 20
resp = client.DescribeConsumerGroup(req)
result = json.loads(resp.to_json_string())

# Parse consumer group info
for group in result["Response"]["Result"]["ConsumerGroupList"]:
    print(f"Group: {group['ConsumerGroupName']}, Lag: {group.get('ConsumeLag', 'N/A')}")
```

#### Key Response Fields

| Field | JSON Path | Description |
|-------|-----------|-------------|
| ConsumerGroupName | `$.Response.Result.ConsumerGroupList[].ConsumerGroupName` | Consumer group name |
| ConsumerGroupId | `$.Response.Result.ConsumerGroupList[].ConsumerGroupId` | Consumer group ID |
| ConsumeLag | `$.Response.Result.ConsumerGroupList[].ConsumeLag` | Current lag in messages |
| ProtocolType | `$.Response.Result.ConsumerGroupList[].ProtocolType` | Consumer protocol |

#### Monitoring Consumer Lag

```bash
# Get detailed consumer group info including lag
tccli ckafka DescribeGroupInfo \
  --InstanceId "{{user.instance_id}}" \
  --GroupList '["{{user.consumer_group_name}}"]'
```

---

### Operation: CreateAcl (Create ACL Rule)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | DescribeInstances | Status = 1 | HALT |
| Resource exists | DescribeTopic | Topic exists | Create topic first |

#### Execution — CLI

```bash
# Create ACL for producer
tccli ckafka CreateAcl \
  --InstanceId "{{user.instance_id}}" \
  --ResourceType "TOPIC" \
  --ResourceName "{{user.topic_name}}" \
  --Principal "User:*" \
  --Host "*" \
  --Operation "Write" \
  --PermissionType "Allow"

# Create ACL for consumer (Read)
tccli ckafka CreateAcl \
  --InstanceId "ckafka-xxxxxx" \
  --ResourceType "TOPIC" \
  --ResourceName "order-events" \
  --Principal "User:consumer-app" \
  --Host "10.0.0.0/8" \
  --Operation "Read" \
  --PermissionType "Allow"

# Create consumer group ACL
tccli ckafka CreateAcl \
  --InstanceId "ckafka-xxxxxx" \
  --ResourceType "GROUP" \
  --ResourceName "order-consumer-group" \
  --Principal "User:consumer-app" \
  --Host "*" \
  --Operation "Read" \
  --PermissionType "Allow"
```

#### Execution — SDK

```python
req = models.CreateAclRequest()
req.InstanceId = "{{user.instance_id}}"
req.ResourceType = "TOPIC"
req.ResourceName = "{{user.topic_name}}"
req.Principal = "User:*"
req.Host = "*"
req.Operation = "Write"
req.PermissionType = "Allow"
resp = client.CreateAcl(req)
print(f"ACL created: {resp.to_json_string()}")
```

#### Post-execution Validation

```bash
# Verify ACL rules
tccli ckafka DescribeACL \
  --InstanceId "{{user.instance_id}}" \
  --ResourceType "TOPIC" \
  --ResourceName "{{user.topic_name}}"
```

#### Failure Recovery

| Error pattern | Max retries | Agent Action |
|--------------|-------------|--------------|
| `ResourceNotFound` | 0 | HALT — resource doesn't exist |
| `InvalidParameterValue` | 0–1 | Fix parameters; retry |

---

### Operation: SendMessage (Send Messages)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | DescribeInstances | Status = 1 | HALT |
| Topic exists | DescribeTopic | Topic exists | Create topic |
| ACL allows write | DescribeACL | Write permission | Create ACL |

#### Execution — CLI

```bash
# Send a single message
tccli ckafka SendMessages \
  --InstanceId "{{user.instance_id}}" \
  --Topic "{{user.topic_name}}" \
  --Partition 0 \
  --Message 'Hello Kafka!'

# Send JSON message (escape properly)
tccli ckafka SendMessages \
  --InstanceId "ckafka-xxxxxx" \
  --Topic "order-events" \
  --Message '{"orderId":"12345","status":"created","timestamp":"2026-05-28T10:00:00Z"}'
```

#### Execution — SDK

```python
import base64

req = models.SendMessageRequest()
req.InstanceId = "{{user.instance_id}}"
req.Topic = "{{user.topic_name}}"
req.Partition = 0

# Encode message (if required by SDK version)
message = '{"event":"test","data":"hello"}'
req.Message = base64.b64encode(message.encode()).decode()

resp = client.SendMessage(req)
result = json.loads(resp.to_json_string())
print(f"Message sent, offset: {result['Response'].get('Offset', 'N/A')}")
```

#### Post-execution Validation

```bash
# Verify message by fetching
tccli ckafka FetchMessageByOffset \
  --InstanceId "{{user.instance_id}}" \
  --Topic "{{user.topic_name}}" \
  --Partition 0 \
  --Offset 0 \
  --SinglePartitionRecordNumber 1
```

---

## Error Code Reference

### CKafka-Specific Error Codes

| Error Code | Description | Agent Action | UX Message |
|------------|-------------|--------------|------------|
| `InvalidParameterValue` | Invalid parameter value | Fix and retry | `Invalid parameter value. Check and correct input.` |
| `ResourceNotFound` | Resource not found | HALT | `Resource not found. Verify ID and region.` |
| `ResourceUnavailable` | Resource temporarily unavailable | Retry with backoff | `Resource temporarily unavailable. Retrying...` |
| `ResourceInsufficient` | Quota exceeded | HALT | `Quota limit reached. Request quota increase.` |
| `ResourceInUse` | Resource in use | Wait or force | `Resource in use. Wait for completion or use force flag.` |
| `TopicAlreadyExists` | Topic already exists | Skip or use existing | `Topic already exists. Use existing or choose different name.` |
| `ConsumerGroupNotExist` | Consumer group not found | HALT | `Consumer group not found. Create it first.` |
| `InstanceNotExist` | Instance not found | HALT | `Instance not found. Verify ID and region.` |
| `OperationDenied` | Operation not allowed | HALT | `Operation not permitted. Check permissions.` |
| `FailedOperation` | Operation failed | Retry or escalate | `Operation failed. Retry or contact support.` |
| `UnauthorizedOperation` | Unauthorized operation | Check CAM | `Unauthorized. Verify IAM permissions.` |
| `LimitExceeded` | Rate limit exceeded | Backoff and retry | `Rate limit exceeded. Retrying with backoff.` |
| `InternalError` | Internal server error | Retry 3x then HALT | `Internal error. Retry or escalate with RequestId.` |
| `InvalidInstanceStatus` | Invalid instance status | Wait for ready | `Instance not ready. Wait for status=1 (running).` |

---

## Safety Gates

### Instance Deletion

**MUST** follow this confirmation flow before executing DeleteInstance:

1. **Display warning**: "Deleting instance `{{user.instance_id}}` will permanently remove all topics, messages, consumer groups, and configurations. This action is irreversible."

2. **Require explicit confirmation**: User must type "CONFIRM DELETE {{user.instance_id}}" to proceed

3. **Suggest backup**: Recommend creating final topic exports or message dumps before deletion

4. **Check dependencies**: Verify no active producers/consumers via DescribeConsumerGroup

```bash
# Safety check - list all topics and consumer groups
tccli ckafka DescribeTopic --InstanceId "{{user.instance_id}}"
tccli ckafka DescribeConsumerGroup --InstanceId "{{user.instance_id}}"
```

### Topic Deletion

**MUST** follow this confirmation flow before executing DeleteTopic:

1. **Display warning**: "Deleting topic `{{user.topic_name}}` will permanently remove all messages and offsets. Consumer groups will lose progress for this topic."

2. **Require confirmation**: User must confirm with topic name

3. **Check active consumers**: Verify no active consumers via DescribeTopicSubscribeGroup

```bash
# Safety check
tccli ckafka DescribeTopicSubscribeGroup \
  --InstanceId "{{user.instance_id}}" \
  --TopicName "{{user.topic_name}}"
```

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **2** | per-skill override |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 CKafka-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### CKafka-specific safety rules (rubric §4)

1. `DeleteInstance` — instance ID + Name echo; list topics + consumer groups before commit; literal confirm
2. `DeleteTopic` — topic + partition + active consumer groups echo; confirm with topic name
3. `ModifyTopic` (partition change) — warn one-directional; surface rebalancing impact; confirm if >2×
4. `ModifyInstanceAttributes` (retention/config) — echo current → new; warn retention timing; warn CleanUpPolicy irreversibility
5. `CreateAcl` / `DeleteAcl` — surface ACL rule; warn `Host=*` + `ALL` open access; warn last-rule lockout

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

---

## Reference Directory

### Documentation

- [CLI Usage Guide](references/cli-usage.md) — tccli command reference
- [Core Concepts](references/core-concepts.md) — CKafka architecture and concepts
- [Troubleshooting](references/troubleshooting.md) — Common issues and fixes
- [Well-Architected Assessment](references/well-architected-assessment.md) — Architecture review

### API References

- [Tencent Cloud CKafka API Docs](https://cloud.tencent.com/document/api/597)
- [Instance Operations](references/api-instance.md)
- [Topic Operations](references/api-topic.md)
- [Consumer Group Operations](references/api-consumer.md)
- [ACL Operations](references/api-acl.md)

### Related Skills

- [qcloud-vpc-ops](../qcloud-vpc-ops/) — VPC network configuration
- [qcloud-monitor-ops](../qcloud-monitor-ops/) — Cloud monitoring
- [qcloud-cam-ops](../qcloud-cam-ops/) — Access management

---

## Prerequisites

1. **Install `tccli` CLI** (primary execution path):
   ```bash
   pip install tccli
   ```

2. **Bootstrap Python runtime** (for SDK fallback — Python 3.8+):
   ```bash
   pip install tencentcloud-sdk-python-ckafka
   ```

3. **Configure Credentials** — Environment variables:
   ```bash
   export TENCENTCLOUD_SECRET_ID="{{env.TENCENTCLOUD_SECRET_ID}}"
   export TENCENTCLOUD_SECRET_KEY="{{env.TENCENTCLOUD_SECRET_KEY}}"
   export TENCENTCLOUD_REGION="{{env.TENCENTCLOUD_REGION}}"
   ```

4. **Verify Configuration**:
   ```bash
   tccli ckafka DescribeInstances --Region ap-guangzhou --Limit 5
   ```
