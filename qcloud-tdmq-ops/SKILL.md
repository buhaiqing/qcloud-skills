---
name: qcloud-tdmq-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or operate Tencent
  Cloud Distributed Message Queue (TDMQ) — RocketMQ, Pulsar, RabbitMQ, CMQ, and
  Pulsar Pro clusters. Covers cluster/namespace/instance lifecycle, topic and
  subscription/group management, message production and consumption, offset
  reset, message rewind, and dead-letter queue handling. Triggers on keywords:
  TDMQ, 消息队列, RocketMQ, Pulsar, RabbitMQ, CMQ, 消息回溯, 主题, 订阅,
  topic, subscription, consumer group, 死信队列, dead-letter queue. Not for
  Kafka (use `qcloud-ckafka-ops`) or general CVM/network operations.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "2026-07-09"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/product/1495"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli tdmq help` — CLI exposes CreateRocketMQCluster,
    CreateRocketMQNamespace, CreateRocketMQTopic, CreateRocketMQGroup,
    CreateRocketMQVipInstance, CreateEnvironment, CreateTopic, CreateSubscription,
    SendRocketMQMessage, ReceiveMessage, RewindCmqQueue, DeleteRocketMQCluster,
    and 100+ related operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
  gcl: required
  gcl_max_iter: 2
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud TDMQ Operations Skill

## Overview

Tencent Cloud Distributed Message Queue (TDMQ / 腾讯云消息队列) provides fully-managed
messaging services across multiple protocols: **RocketMQ**, **Pulsar**, **RabbitMQ**,
**CMQ**, and **Pulsar Pro**. This skill is an **operational runbook** for agents: explicit
scope, credential rules, pre-flight checks, **dual-path execution** (`tccli tdmq` primary,
`tencentcloud-sdk-python` fallback), response validation, and failure recovery. **Do not use
the web console as the primary agent execution path** in `SKILL.md`.

> **UX Compliance:** This skill follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** `tccli tdmq` covers TDMQ operations. You **MUST** ship
  `references/cli-usage.md` and document **both** the SDK and `tccli` step for every operation
  the CLI exposes.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT with TDMQ triggers; Kafka → `qcloud-ckafka-ops` |
| 2 | **Structured I/O** | `{{env.*}}` for credentials, `{{user.*}}` for config, `{{output.*}}` from API responses |
| 3 | **Explicit Actionable Steps** | Every op: Pre-flight → Execute (CLI + SDK) → Validate → Recover |
| 4 | **Complete Failure Strategies** | ≥ 10 TDMQ-specific error codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | TDMQ message queue management only; Kafka → `qcloud-ckafka-ops` |

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-AZ clusters, message durability, DLQ handling, offset reset | `references/well-architected-assessment.md` |
| **安全性 (Security)** | Namespace roles, access policies, credential masking | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Cluster spec selection, instance billing model | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Batch send, consumer group tuning, partition strategy | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "TDMQ", "腾讯云消息队列", "RocketMQ", "Pulsar", "RabbitMQ", "CMQ"
- Task: create/manage clusters, namespaces, topics, subscriptions, consumer groups
- Task: send/receive messages, reset consumer offset, rewind messages, handle DLQ
- Keywords: 消息回溯, 主题, 订阅, 死信队列, topic, subscription, consumer group

### SHOULD NOT Use This Skill When

- Task is **Kafka** operations → delegate to `qcloud-ckafka-ops`
- Task is **CVM/network setup** → delegate to `qcloud-cvm-ops`, `qcloud-vpc-ops`
- Task is **CAM** only → delegate to `qcloud-cam-ops`
- User insists on **console-only** flows with no API → state limitation

### Delegation Rules

- Kafka topic/cluster ops → `qcloud-ckafka-ops`
- Underlying CVM for self-built MQ → `qcloud-cvm-ops`
- VPC/networking for private access → `qcloud-vpc-ops`
- CAM policy for TDMQ roles → `qcloud-cam-ops`

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use documented default only if skill allows |
| `{{user.cluster_id}}` | RocketMQ cluster ID | Ask once; reuse |
| `{{user.namespace}}` | RocketMQ namespace name | Ask once; reuse |
| `{{user.topic_name}}` | Topic name | Ask once; reuse |
| `{{user.group_name}}` | Consumer group name | Ask once; reuse |
| `{{user.environment_id}}` | Pulsar environment ID | Ask once; reuse |
| `{{output.cluster_id}}` | From API response | Parse per API spec |
| `{{output.topic_id}}` | From API response | Parse per API spec |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose
> `TENCENTCLOUD_SECRET_KEY`, `SecretKey`, or any credential field value in console output,
> debug messages, error messages, or logs.

## JSON Path Reference

| Path | Maps To |
|------|---------|
| `cluster.id` | `$.Response.ClusterId` / `$.Response.ClusterList[].ClusterId` |
| `topic.name` | `$.Response.TopicName` |
| `topic.id` | `$.Response.TopicId` |
| `group.name` | `$.Response.GroupName` |
| `msg.id` | `$.Response.MsgId` |

## Quick Start

### What This Skill Does

Manage Tencent Cloud TDMQ messaging resources (RocketMQ, Pulsar, RabbitMQ, CMQ) — create
clusters/namespaces/topics/groups, send and receive messages, reset offsets, and handle
dead-letter queues using `tccli tdmq` (primary) or `tencentcloud-sdk-python` (fallback).

### Prerequisites
- [ ] `tccli` CLI installed
- [ ] Credentials: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region: `TENCENTCLOUD_REGION`

### Verify Setup
```bash
tccli tdmq DescribeRocketMQClusters --Region "{{env.TENCENTCLOUD_REGION}}"
```

### Your First Command
```bash
# List RocketMQ clusters
tccli tdmq DescribeRocketMQClusters --Region "{{env.TENCENTCLOUD_REGION}}"
```

### Next Steps
- [Common Operations](#execution-flows) — Create cluster, topic, send message
- [Troubleshooting](references/troubleshooting.md) — Fix message and cluster issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreateRocketMQCluster | Create a RocketMQ cluster | Medium | Low |
| CreateRocketMQNamespace | Create a namespace | Low | Low |
| CreateRocketMQTopic | Create a topic | Low | Low |
| CreateRocketMQGroup | Create a consumer group | Low | Low |
| DeleteRocketMQTopic | Delete a topic | Low | **High** — data loss |
| DeleteRocketMQCluster | Delete a cluster | Medium | **High** — destroys all resources |
| SendRocketMQMessage | Produce a message | Low | None |
| ReceiveMessage | Consume a message | Low | None |
| ResetRocketMQConsumerOffSet | Reset consumer offset | Medium | Medium |
| RewindCmqQueue | Rewind CMQ queue messages | Medium | Medium |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-07-09 | Initial TDMQ skill: RocketMQ cluster/namespace/topic/group lifecycle, message send/receive, offset reset, CMQ rewind, DLQ handling. Dual-path execution. Delegates Kafka to `qcloud-ckafka-ops`. |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI and SDK) → Validate → Recover**.

### Operation: Create RocketMQ Cluster

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Credentials | `test -n "$TENCENTCLOUD_SECRET_ID"` | Non-empty | HALT; user configures env |
| CLI installed | `tccli version` | Exit code 0 | Install tccli |
| Region supported | `tccli tdmq DescribeRocketMQClusters` | Returns list | Use supported region |

#### Execution — CLI (`tccli`) (Primary Path)

```bash
tccli tdmq CreateRocketMQCluster \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ClusterName "{{user.cluster_name}}" \
  --Remark "{{user.remark}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Capture `{{output.cluster_id}}` from `$.Response.ClusterId`.
2. Poll `DescribeRocketMQCluster --ClusterId "{{output.cluster_id}}"` until status = `RUNNING`.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.ClusterNameExists` | Use a different cluster name |
| `ResourceInsufficient` | HALT; raise quota |
| `RequestLimitExceeded` | Backoff retry (2s,4s,8s) |

### Operation: Create RocketMQ Namespace

#### Execution — CLI

```bash
tccli tdmq CreateRocketMQNamespace \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ClusterId "{{user.cluster_id}}" \
  --NamespaceName "{{user.namespace}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

### Operation: Create RocketMQ Topic

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Cluster exists | `DescribeRocketMQCluster --ClusterId "{{user.cluster_id}}"` | Found | Create cluster first |
| Namespace exists | `DescribeRocketMQNamespaces --ClusterId "{{user.cluster_id}}"` | Found | Create namespace first |

#### Execution — CLI

```bash
tccli tdmq CreateRocketMQTopic \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ClusterId "{{user.cluster_id}}" \
  --Namespace "{{user.namespace}}" \
  --Topic "{{user.topic_name}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Capture `{{output.topic_id}}` from `$.Response.TopicId`.
2. Poll `DescribeRocketMQTopics` until topic appears with status `RUNNING`.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.TopicExists` | Topic already exists; reuse or rename |
| `ResourceNotFound.Cluster` | Verify cluster ID |
| `ResourceNotFound.Namespace` | Verify namespace |

### Operation: Create RocketMQ Group (Consumer Group)

#### Execution — CLI

```bash
tccli tdmq CreateRocketMQGroup \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ClusterId "{{user.cluster_id}}" \
  --Namespace "{{user.namespace}}" \
  --Group "{{user.group_name}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

### Operation: Send Message (RocketMQ)

#### Execution — CLI

```bash
tccli tdmq SendRocketMQMessage \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ClusterId "{{user.cluster_id}}" \
  --Namespace "{{user.namespace}}" \
  --Topic "{{user.topic_name}}" \
  --Body "{{user.message_body}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Capture `{{output.msg_id}}` from `$.Response.MsgId`.
2. Confirm `$.Response.ReturnCode == 0` (success).

### Operation: Receive Message

#### Execution — CLI

```bash
tccli tdmq ReceiveMessage \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ClusterId "{{user.cluster_id}}" \
  --Namespace "{{user.namespace}}" \
  --Topic "{{user.topic_name}}" \
  --Group "{{user.group_name}}"
```

### Operation: Reset Consumer Offset

#### Pre-flight (Safety Gate)

- **MUST** confirm: cluster, namespace, topic, group, target timestamp/offset.
- **MUST** warn: resetting offset reprocesses or skips messages — affects downstream consumers.

#### Execution — CLI

```bash
tccli tdmq ResetRocketMQConsumerOffSet \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ClusterId "{{user.cluster_id}}" \
  --Namespace "{{user.namespace}}" \
  --Topic "{{user.topic_name}}" \
  --Group "{{user.group_name}}" \
  --ResetTimestamp "{{user.reset_timestamp}}"
```

### Operation: Delete RocketMQ Topic

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation with topic name + cluster + namespace.
- **MUST** warn: deleting a topic destroys all messages and subscription state.

#### Execution — CLI

```bash
tccli tdmq DeleteRocketMQTopic \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ClusterId "{{user.cluster_id}}" \
  --Namespace "{{user.namespace}}" \
  --Topic "{{user.topic_name}}"
```

#### Post-execution Validation

Poll `DescribeRocketMQTopics`; expect topic absent.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.Topic` | Already removed; treat as success |
| `OperationDenied.TopicInUse` | Detach consumers first |

### Operation: Delete RocketMQ Cluster

#### Pre-flight (Safety Gate — MANDATORY)

- **MUST** obtain explicit user confirmation with cluster ID + name.
- **MUST** warn: deleting a cluster destroys ALL namespaces, topics, groups, and messages.
- **MUST** verify no active topics/groups remain.

#### Execution — CLI

```bash
tccli tdmq DeleteRocketMQCluster \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --ClusterId "{{user.cluster_id}}"
```

#### Post-execution Validation

Poll `DescribeRocketMQClusters`; expect cluster absent.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.Cluster` | Already removed |
| `OperationDenied.ClusterNotEmpty` | Delete all child topics/groups/namespaces first |

### Operation: CMQ Queue Rewind

#### Execution — CLI

```bash
tccli tdmq RewindCmqQueue \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --QueueName "{{user.queue_name}}" \
  --StartConsumeTime "{{user.rewind_timestamp}}"
```

## Error Code Reference (Minimum 10 TDMQ-Specific Codes)

| Code | Meaning | Retry? | Agent Action |
|------|---------|--------|--------------|
| `InvalidParameter.ClusterNameExists` | Cluster name already exists | No | Use different name |
| `InvalidParameter.TopicExists` | Topic already exists | No | Reuse or rename |
| `InvalidParameterValue` | Parameter value out of range | No | Adjust per spec |
| `MissingParameter` | Required parameter missing | No | Add missing parameter |
| `ResourceNotFound.Cluster` | Cluster not found | No | Verify cluster ID |
| `ResourceNotFound.Namespace` | Namespace not found | No | Verify namespace |
| `ResourceNotFound.Topic` | Topic not found | No | Verify topic name |
| `ResourceInsufficient` | Quota exceeded | No | HALT; request quota increase |
| `OperationDenied.ClusterNotEmpty` | Cluster has child resources | No | Delete children first |
| `InvalidSecretKey` | Credential invalid | No | HALT; fix credentials |
| `RequestLimitExceeded` | API rate limit | Yes (3x) | Exponential backoff |
| `InternalError` | Server error | Yes (3x) | Retry; escalate with RequestId |

## Safety Gates (Destructive Operations)

Every **DeleteRocketMQTopic** / **DeleteRocketMQCluster** MUST have:

1. Explicit user confirmation with resource ID + name
2. Verification that resource is not in active use (no consumers for topic)
3. Pre-warning about message/data loss
4. Post-delete verification (poll until absent)

**ResetRocketMQConsumerOffSet** and **RewindCmqQueue** are semi-destructive (affect message
processing state) — always confirm target offset/timestamp with the user.

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | frontmatter `gcl: required` |
| max_iterations | **2** | frontmatter `gcl_max_iter: 2` |
| Rubric instance | `references/rubric.md` | 5 dimensions, TDMQ-specific safety rules |
| Prompt templates | `references/prompt-templates.md` | Generator + Critic + Orchestrator |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | per AGENTS.md §7 |

### When the loop runs

| Operation | Loop required? | Reason |
|---|---|---|
| `CreateRocketMQCluster` | Yes | Creates cluster |
| `CreateRocketMQTopic` | Yes | Creates topic |
| `DeleteRocketMQTopic` | Yes (blocking) | Data loss risk |
| `DeleteRocketMQCluster` | Yes (blocking) | Destroys all child resources |
| `ResetRocketMQConsumerOffSet` | Yes (blocking) | Alters consumption state |
| `RewindCmqQueue` | Yes (blocking) | Alters consumption state |
| `SendRocketMQMessage` | No | Read-only-ish produce |
| `Describe*` / `ReceiveMessage` | No | Read-only |

### Decision flow (first match wins)

1. **Safety=0** → `ABORT` — immediate halt, no output
2. **current_iter >= max_iterations** → `MAX_ITER` — return best result, blocking=true
3. **All thresholds met** → `PASS` — output accepted
4. **Otherwise** → `RETRY` — inject suggestions, increment iter

---

## Prerequisites

1. **Install `tccli` CLI:**
```bash
pip install tccli
tccli version
```

2. **Configure Credentials:**
```bash
export TENCENTCLOUD_SECRET_ID="{{env.TENCENTCLOUD_SECRET_ID}}"
export TENCENTCLOUD_SECRET_KEY="{{env.TENCENTCLOUD_SECRET_KEY}}"
export TENCENTCLOUD_REGION="{{env.TENCENTCLOUD_REGION}}"
```

3. **Verify:**
```bash
tccli tdmq DescribeRocketMQClusters --Region "{{env.TENCENTCLOUD_REGION}}"
```

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [CLI Usage](references/cli-usage.md)
- [Troubleshooting](references/troubleshooting.md)
- [Well-Architected Assessment](references/well-architected-assessment.md)
- [Integration](references/integration.md)
- [SDK Code Examples](references/sdk-code-examples.md)
- [GCL Rubric](references/rubric.md)
- [GCL Prompt Templates](references/prompt-templates.md)
- [Eval Queries](assets/eval_queries.json)
- [Example Configuration](assets/example-config.yaml)
