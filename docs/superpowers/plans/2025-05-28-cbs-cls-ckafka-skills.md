# 腾讯云 CBS/CLS/CKafka 运维技能开发计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 开发三个腾讯云运维技能：CBS(云硬盘)、CLS(日志服务)、CKafka(消息队列)，每个技能包含完整的SKILL.md、reference文档和CLI/SDK使用指南

**Architecture:** 遵循现有qcloud技能规范(如qcloud-cvm-ops/qcloud-tke-ops)，采用Agent Skill OpenSpec标准，支持dual-path(CLI+SDK)执行，包含完整错误处理和故障排查指南

**Tech Stack:** Markdown, tccli CLI, tencentcloud-sdk-python, jq, bash

---

## 前置准备

### 步骤1: 验证目录结构
**预计时间:** 2分钟

```bash
# 创建三个技能目录
mkdir -p qcloud-cbs-ops/{references,assets}
mkdir -p qcloud-cls-ops/{references,assets}
mkdir -p qcloud-ckafka-ops/{references,assets}

# 验证创建成功
ls -la qcloud-cbs-ops/ qcloud-cls-ops/ qcloud-ckafka-ops/
```

**预期输出:** 每个目录下都有 references 和 assets 子目录

---

## Skill 1: CBS (云硬盘) 运维技能

### 背景调研
CBS(Cloud Block Storage)是腾讯云的块存储服务，提供：
- 云硬盘生命周期管理（创建、删除、扩容）
- 挂载/卸载到CVM实例
- 快照管理（创建、回滚、删除）
- 性能监控和告警

**CLI支持验证:** `tccli cbs help` - 确认支持 CreateDisks, DescribeDisks, AttachDisks, DetachDisks, ResizeDisk, CreateSnapshot, DescribeSnapshots, DeleteSnapshots 等操作

### Task 1.1: 创建核心 SKILL.md 文件
**预计时间:** 10分钟

**Files:**
- Create: `qcloud-cbs-ops/SKILL.md`

**步骤1.1.1: 创建文件头部和元数据**

```markdown
---
name: qcloud-cbs-ops
description: >-
  Use when the user needs to manage Tencent Cloud CBS (Cloud Block Storage) disks,
  snapshots, and disk attachments to CVM instances. User mentions CBS, 云硬盘,
  cloud block storage, disk, 磁盘, snapshot, 快照, or describes scenarios like
  creating data disk, expanding disk size, attaching/detaching disk from CVM,
  backup and restore via snapshots. Not for billing, CAM, or COS object storage.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python-cbs),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "2026-05-28"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/362"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli cbs help` - CLI exposes CreateDisks, DescribeDisks,
    AttachDisks, DetachDisks, ResizeDisk, TerminateDisks, CreateSnapshot,
    DescribeSnapshots, DeleteSnapshots, BindAutoSnapshotPolicy, and 30+ more operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---
```

**步骤1.1.2: 添加技能概览和核心标准**

```markdown
> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud CBS Operations Skill

## Overview

CBS (Cloud Block Storage) is Tencent Cloud's high-performance block storage service for CVM instances, providing persistent storage with SSD and Premium Cloud Storage options. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **`tccli` CLI** and **Python SDK fallback**), response validation, and failure recovery.

> **UX Compliance:** This skill follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md).

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`**: Official `tccli` fully supports CBS. CLI is the **primary** execution path; Python SDK is used for edge-case operations.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | Precise triggers (CBS, 云硬盘, disk, snapshot) and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions per operation |
| 3 | **Explicit Actionable Steps** | Pre-flight → Execute → Validate → Recover |
| 4 | **Complete Failure Strategies** | Error taxonomy with ≥ 12 CBS-specific codes |
| 5 | **Absolute Single Responsibility** | One product (CBS), primary resource (Disk) |
```

**步骤1.1.3: 添加触发条件和范围**

```markdown
## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "CBS" OR "云硬盘" OR "disk" OR "磁盘" OR "snapshot" OR "快照"
- Task involves CRUD on **CBS Disks** (CreateDisks, DescribeDisks, TerminateDisks)
- Task involves **Disk Attachment** to CVM (AttachDisks, DetachDisks)
- Task involves **Disk Expansion** (ResizeDisk)
- Task involves **Snapshots** (CreateSnapshot, DescribeSnapshots, DeleteSnapshots, ApplySnapshot)
- Task keywords: create disk, attach disk, detach disk, expand disk, resize, backup disk, restore snapshot
- User asks to manage CBS via API, SDK, CLI, or automation

### SHOULD NOT Use This Skill When

- Task is billing / account management → delegate to: `qcloud-billing-ops`
- Task is CAM / permission only → delegate to: `qcloud-cam-ops`
- Task is **COS object storage** → delegate to: `qcloud-cos-ops`
- Task is **CVM instance management** (lifecycle) → delegate to: `qcloud-cvm-ops`
- User insists on console-only flows → state limitation
```

**步骤1.1.4: 提交文件**

```bash
git add qcloud-cbs-ops/SKILL.md
git commit -m "feat(cbs): add core SKILL.md with metadata and scope"
```

### Task 1.2: 添加变量约定和API响应规范
**预计时间:** 5分钟

**Files:**
- Modify: `qcloud-cbs-ops/SKILL.md` (追加内容)

```markdown
## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Default `ap-guangzhou` if unset |
| `{{user.disk_name}}` | User-supplied disk name | Ask once; reuse |
| `{{user.disk_id}}` | User-supplied disk ID (disk-xxx) | Ask once; reuse |
| `{{user.disk_size}}` | Disk size in GB | Ask once; suggest standard sizes |
| `{{user.disk_type}}` | CLOUD_SSD / CLOUD_PREMIUM / CLOUD_HSSD | Ask once; default CLOUD_SSD |
| `{{user.instance_id}}` | CVM instance ID for attachment | Ask once; reuse |
| `{{user.snapshot_id}}` | Snapshot ID (snap-xxx) | Ask once; reuse |
| `{{output.disk_id}}` | From CreateDisks response | Parse `$.Response.DiskIdSet[0]` |
| `{{output.snapshot_id}}` | From CreateSnapshot response | Parse `$.Response.SnapshotId` |

> **Security Warning:** NEVER log `TENCENTCLOUD_SECRET_KEY`. Mask with `***`.

## API and Response Conventions

- **API spec:** https://cloud.tencent.com/document/api/362
- **Errors:** Map SDK/HTTP errors to `code` / `message` fields
- **Disk States:** `UNATTACHED`, `ATTACHING`, `ATTACHED`, `DETACHING`, `EXPANDING`
- **Async behavior:** Disk creation/expansion is async — poll DescribeDisks until status = `UNATTACHED` or `ATTACHED`

### Response Field Table

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| CreateDisks | `$.Response.DiskIdSet[0]` | string | New disk ID (disk-xxxxxxxx) |
| DescribeDisks | `$.Response.DiskSet[0].DiskId` | array | Disk IDs |
| DescribeDisks | `$.Response.DiskSet[0].DiskState` | string | Disk lifecycle state |
| CreateSnapshot | `$.Response.SnapshotId` | string | New snapshot ID (snap-xxx) |
| DescribeSnapshots | `$.Response.SnapshotSet[0].SnapshotId` | array | Snapshot IDs |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| CreateDisks | — | `UNATTACHED` | 5s | 120s |
| AttachDisks | `UNATTACHED` | `ATTACHED` | 5s | 120s |
| DetachDisks | `ATTACHED` | `UNATTACHED` | 5s | 120s |
| ResizeDisk | any | `EXPANDING` → `UNATTACHED`/`ATTACHED` | 5s | 300s |
```

### Task 1.3: 添加执行流程 - CreateDisk
**预计时间:** 8分钟

```markdown
## Execution Flows (Agent-Readable)

### Operation: CreateDisk

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI installed | `tccli cbs help CreateDisks` | Exit code 0 | Document CLI install |
| Credentials | Check env vars | Non-empty | HALT; user configures |
| Quota | `tccli cbs DescribeDiskConfigQuota` | Sufficient disk quota | HALT; request quota increase |
| Disk type valid | Check against region quota | Type available | Suggest alternative type |

#### Execution — CLI (Primary Path)

```bash
tccli cbs CreateDisks \
  --DiskName "{{user.disk_name}}" \
  --DiskSize {{user.disk_size}} \
  --DiskType "{{user.disk_type}}" \
  --Zone "{{env.TENCENTCLOUD_ZONE}}" \
  --Region {{env.TENCENTCLOUD_REGION}}
```

#### Execution — Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
import os, json
from tencentcloud.common import credential
from tencentcloud.cbs import cbs_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = cbs_client.CbsClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        req = models.CreateDisksRequest()
        req.DiskName = os.environ.get("DISK_NAME")
        req.DiskSize = int(os.environ.get("DISK_SIZE", "100"))
        req.DiskType = os.environ.get("DISK_TYPE", "CLOUD_SSD")
        req.Zone = os.environ.get("TENCENTCLOUD_ZONE")
        resp = client.CreateDisks(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except Exception as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

#### Post-execution Validation

1. Read `{{output.disk_id}}` from `$.Response.DiskIdSet[0]`
2. Poll DescribeDisks until DiskState = `UNATTACHED` (max 120s)
3. Report disk ID, type, and size to user
```

### Task 1.4: 添加更多执行流程
**预计时间:** 10分钟

添加 AttachDisk、DetachDisk、ResizeDisk、CreateSnapshot 等流程...

### Task 1.5: 创建 reference 文档
**预计时间:** 15分钟

创建以下文件：
- `qcloud-cbs-ops/references/cli-usage.md` - CLI命令映射
- `qcloud-cbs-ops/references/core-concepts.md` - 核心概念（磁盘类型、性能、配额）
- `qcloud-cbs-ops/references/troubleshooting.md` - 故障排查指南

---

## Skill 2: CLS (日志服务) 运维技能

### Task 2.1: 创建核心 SKILL.md
**预计时间:** 10分钟

**Files:**
- Create: `qcloud-cls-ops/SKILL.md`

**头部元数据：**
```yaml
name: qcloud-cls-ops
description: >-
  Use when the user needs to manage Tencent Cloud CLS (Cloud Log Service),
  including log topics, logsets, log collection, index configuration, and log queries.
  User mentions CLS, 日志服务, log service, 日志主题, log topic, logset, 日志集,
  or scenarios like collecting logs, querying logs, configuring index, log analysis.
  Not for monitoring metrics (use qcloud-monitor-ops), not for billing.
api_profile: "https://cloud.tencent.com/document/api/614"
```

**核心操作：**
- CreateLogset / DeleteLogset
- CreateTopic / DeleteTopic
- CreateIndex / ModifyIndex
- SearchLog / DownloadLog
- CreateMachineGroup / CreateConfig (日志采集配置)

### Task 2.2: 添加执行流程
**预计时间:** 15分钟

包括：
- 创建日志集和日志主题
- 配置日志索引
- 查询日志数据
- 配置日志采集（机器组 + 采集规则）

### Task 2.3: 创建 reference 文档
**预计时间:** 10分钟

---

## Skill 3: CKafka (消息队列) 运维技能

### Task 3.1: 创建核心 SKILL.md
**预计时间:** 10分钟

**Files:**
- Create: `qcloud-ckafka-ops/SKILL.md`

**头部元数据：**
```yaml
name: qcloud-ckafka-ops
description: >-
  Use when the user needs to manage Tencent Cloud CKafka (Cloud Kafka Service),
  including instances, topics, consumer groups, and ACL configurations.
  User mentions CKafka, Kafka, 消息队列, message queue, topic, partition,
  consumer group, producer, or scenarios like creating topic, managing consumers,
  sending/receiving messages. Not for TDMQ (RocketMQ/Pulsar), not for CMQ.
api_profile: "https://cloud.tencent.com/document/api/597"
```

**核心操作：**
- CreateInstance / DescribeInstances
- CreateTopic / DeleteTopic
- DescribeConsumerGroup / ModifyConsumerGroup
- CreateAcl / DeleteAcl
- SendMessage / FetchMessage

### Task 3.2: 添加执行流程
**预计时间:** 15分钟

### Task 3.3: 创建 reference 文档
**预计时间:** 10分钟

---

## 最终集成

### 步骤: 更新主 README
**预计时间:** 3分钟

**Files:**
- Modify: `README.md`

添加三个新技能到技能列表：
```markdown
| Skill | Description | Status |
|-------|-------------|--------|
| qcloud-cbs-ops | Cloud Block Storage (云硬盘) | 🆕 New |
| qcloud-cls-ops | Cloud Log Service (日志服务) | 🆕 New |
| qcloud-ckafka-ops | Cloud Kafka Service (消息队列) | 🆕 New |
```

### 步骤: 提交所有更改
**预计时间:** 2分钟

```bash
git add -A
git commit -m "feat: add CBS, CLS, CKafka operation skills

- Add qcloud-cbs-ops: Cloud Block Storage disk/snapshot management
- Add qcloud-cls-ops: Cloud Log Service topic/query/index management
- Add qcloud-ckafka-ops: Kafka instance/topic/consumer management
- All skills follow dual-path (CLI+SDK) execution
- Include complete error handling and troubleshooting guides

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## 执行选项

**Plan complete and saved to `docs/superpowers/plans/2025-05-28-cbs-cls-ckafka-skills.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach would you prefer?**

---

## Self-Review Checklist

- [ ] Spec coverage: All three products (CBS/CLS/CKafka) have complete task coverage
- [ ] No placeholders: All steps contain concrete code and commands
- [ ] Type consistency: Variable naming consistent across tasks
- [ ] File paths: Exact paths specified for all file operations
- [ ] Testing: Each skill includes validation steps
- [ ] Documentation: Reference docs planned for each skill
