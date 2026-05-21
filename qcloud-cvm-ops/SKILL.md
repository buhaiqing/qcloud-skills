---
name: qcloud-cvm-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud CVM (Cloud Virtual Machine) instances, CBS disks, snapshots, and images.
  User mentions CVM, 云服务器, 腾讯云服务器, Tencent Cloud instance, virtual machine,
  or describes product-specific scenarios (e.g., instance creation, CPU/memory
  issues, disk expansion, snapshot backup, image management, network configuration,
  SSH access problems, instance migration, performance tuning) even without naming
  the product directly. Not for billing, CAM, VPC-only operations, CLB, or related
  products that have their own ops skills.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python-cvm),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "2026-05-21"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/213"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli cvm help` - CLI exposes RunInstances, DescribeInstances,
    StartInstances, StopInstances, RebootInstances, ModifyInstanceAttribute,
    TerminateInstances, AllocateHosts, DescribeHosts, CreateImage, DescribeImages,
    RunInstancesWithChargeType, InquiryPriceRunInstances, and 50+ more operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud CVM Operations Skill

## Overview

CVM (Cloud Virtual Machine) is Tencent Cloud's primary compute service providing scalable, high-performance virtual servers. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **`tccli` CLI** and **Python SDK fallback**), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

> **UX Compliance:** This skill follows the [User Experience Specification](../references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`**: Official `tccli` fully supports CVM. You **MUST** ship **`references/cli-usage.md`** and, in **each** execution flow below, document **both** the SDK step **and** the `tccli` step. CLI is the **primary** execution path for simplicity; Python SDK is used for edge-case operations CLI doesn't expose or for complex parameter handling.

## Five Core Standards (Quality Gates)

Every generated skill MUST satisfy these five standards. Use them as a design checklist:

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers (CVM, 云服务器) and delegation rules (VPC → qcloud-vpc-ops, CLB → qcloud-clb-ops) |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented per operation |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps for CLI and SDK paths |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 12 CVM-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (CVM), primary resource model (Instance); cross-product delegation documented |

Refer to the [meta-skill](../qcloud-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions.

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-AZ deployment, instance backup/snapshot, DR via image migration, auto-recovery configs | `references/well-architected-assessment.md` |
| **安全性 (Security)** | CAM permissions, SSH key management, security group rules, encryption-at-rest | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Instance type comparison, pay-as-you-go vs prepaid, reserved instances, idle resource detection | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Batch instance operations, auto-scaling integration, scheduled shutdown/start | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "CVM" OR "云服务器" OR "Tencent Cloud instance" OR "virtual machine" OR "腾讯云服务器"
- Task involves CRUD or lifecycle operations on **CVM Instances** (RunInstances, DescribeInstances, StartInstances, StopInstances, RebootInstances, TerminateInstances, ModifyInstanceAttribute)
- Task involves **CBS (Cloud Block Storage)** disks attached to CVM (CreateDisks, AttachDisk, DetachDisk, ResizeDisk)
- Task involves **Snapshots** and **Images** for CVM backup/restore (CreateSnapshot, DescribeSnapshots, CreateImage, DescribeImages)
- Task keywords: create instance, deploy server, launch VM, start/stop/reboot instance, resize disk, backup, snapshot, image, SSH, migrate instance, instance type, CPU/memory
- User asks to deploy, configure, troubleshoot, or monitor CVM **via API, SDK, CLI, or automation**
- User describes performance issues (CPU high, memory pressure, disk I/O) without naming product

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: `qcloud-billing-ops` (when present)
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops` (when present)
- Task is **VPC network only** (subnet, route table, NAT gateway) → delegate to: `qcloud-vpc-ops`
- Task is **CLB load balancing** → delegate to: `qcloud-clb-ops`
- Task is **MySQL/Redis database** → delegate to: `qcloud-mysql-ops` / `qcloud-redis-ops`
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented HTTP steps

### Delegation Rules

- CVM depends on VPC: verify VPC/Subnet/SecurityGroup exist via `qcloud-vpc-ops` before RunInstances
- CVM uses CLB: delegate load balancer operations to `qcloud-clb-ops`
- CBS disk operations are within CVM scope (attached storage), but standalone CBS management uses this skill
- Snapshot/Image operations are within CVM scope for instance backup/restore
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use default `ap-guangzhou` if unset |
| `{{user.zone}}` | User-supplied availability zone | Ask once; reuse (e.g., `ap-guangzhou-3`) |
| `{{user.instance_type}}` | User-supplied instance type | Ask once; suggest S5.SMALL1 for test |
| `{{user.image_id}}` | User-supplied image ID | Ask once; suggest default public image |
| `{{user.instance_name}}` | User-supplied instance name | Ask once; reuse |
| `{{user.instance_id}}` | User-supplied instance ID (ins-xxx) | Ask once; reuse for subsequent ops |
| `{{user.disk_size}}` | User-supplied disk size in GB | Ask once; default 50GB for system disk |
| `{{output.instance_id}}` | From RunInstances response | Parse `$.Response.InstanceIdSet[0]` |
| `{{output.request_id}}` | From any API response | Parse `$.Response.RequestId` for tracking |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose `TENCENTCLOUD_SECRET_KEY` in any output. Mask all credentials with `***` or `<masked>`. Check existence only: `test -n "$TENCENTCLOUD_SECRET_KEY"` ✅ | `echo $TENCENTCLOUD_SECRET_KEY` ❌

## API and Response Conventions (Agent-Readable)

- **API spec is canonical**: https://cloud.tencent.com/document/api/213
- **Errors**: Tencent Cloud uses `Response.Error.Code` / `Response.Error.Message` pattern
- **Timestamps**: ISO 8601 format (e.g., `2026-05-21T10:00:00+08:00`)
- **Idempotency**: Use `ClientToken` for RunInstances to avoid duplicate creation on retry

### Example Response Field Table

| Operation | JSON Path | Type | Description |
|-----------|----------|------|-------------|
| RunInstances | `$.Response.InstanceIdSet[0]` | string | New instance ID |
| DescribeInstances | `$.Response.InstanceSet[0].InstanceId` | string | Instance ID |
| DescribeInstances | `$.Response.InstanceSet[0].Status` | string | Instance state |
| DescribeInstances | `$.Response.InstanceSet[0].CPU` | int | CPU cores |
| DescribeInstances | `$.Response.InstanceSet[0].Memory` | int | Memory in GB |
| StopInstances | `$.Response.RequestId` | string | Request tracking ID |
| CreateSnapshot | `$.Response.SnapshotId` | string | Snapshot ID |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| RunInstances | — | `RUNNING` | 5s | 300s |
| StartInstances | `STOPPED` | `RUNNING` | 5s | 120s |
| StopInstances | `RUNNING` | `STOPPED` | 5s | 120s |
| RebootInstances | any stable | `RUNNING` | 5s | 120s |
| TerminateInstances | any | absent (404/empty) | 5s | 300s |

## Quick Start

### What This Skill Does
This skill enables you to deploy, configure, troubleshoot, and monitor CVM instances using `tccli` CLI (primary) or `tencentcloud-sdk-python-cvm` SDK (fallback).

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
tccli cvm DescribeZones --Region ap-guangzhou

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
- [ ] SDK installed: `pip install tencentcloud-sdk-python-cvm`
- [ ] Credentials configured

### Verify Setup (All Environments)
```bash
# Check CLI version
tccli version

# Test API access
tccli cvm DescribeZones --Region ap-guangzhou

# Expected output (JSON)
# {"Response": {"ZoneSet": [...], "RequestId": "..."}}
```

### Your First Command
```bash
# List all instances in current region
tccli cvm DescribeInstances --Region {{env.TENCENTCLOUD_REGION}}

# Cloud Shell: Use explicit region
tccli cvm DescribeInstances --Region ap-guangzhou
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — Understand CVM architecture and limits
- [Common Operations](#execution-flows) — Create, manage, and delete instances
- [CLI Usage Guide](references/cli-usage.md) — Detailed CLI command reference
- [Integration Guide](references/integration.md) — Cloud Shell, SDK setup, automation
- [Troubleshooting](references/troubleshooting.md) — Fix common CVM issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| RunInstances | Create new CVM instance(s) | Medium | Low |
| DescribeInstances | View instance details | Low | None |
| StartInstances | Start stopped instances | Low | None |
| StopInstances | Stop running instances | Low | Medium (service interruption) |
| RebootInstances | Reboot instances | Low | Medium |
| ModifyInstanceAttribute | Change instance config | Medium | Medium |
| TerminateInstances | Delete instances (irreversible) | Low | **High** |
| AllocateHosts | Create dedicated hosts | Medium | Low |
| CreateSnapshot | Create disk backup | Low | Low |
| CreateImage | Create custom image | Medium | Low |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial skill with RunInstances, DescribeInstances, Start/Stop/Reboot/Terminate, CBS disk operations, Snapshot/Image management |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI and SDK) → Validate → Recover**. Do not skip phases.

### Operation: RunInstances (Create CVM)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI install | `tccli version` | Exit 0 | Install: `pip install tccli` |
| Credentials | Check `TENCENTCLOUD_SECRET_ID/KEY` env | Non-empty | HALT; configure env |
| Region | `tccli cvm DescribeZones --Region {{env.TENCENTCLOUD_REGION}}` | Valid zone set | HALT; set valid region |
| VPC exists | Delegate to `qcloud-vpc-ops` DescribeVpcs | VPC in region | HALT; create VPC first |
| Security Group | Delegate to `qcloud-vpc-ops` DescribeSecurityGroups | SG exists | HALT; create SG first |
| Image available | `tccli cvm DescribeImages --ImageId {{user.image_id}}` | `IMAGE_AVAILABLE` | HALT; use valid image |
| Quota | `tccli cvm DescribeAccountQuota` | Instance quota > 0 | HALT; raise quota |

#### Execution — CLI (`tccli`) (Primary Path)

```bash
# Create single instance
tccli cvm RunInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Placement '{"Zone":"{{user.zone}}"}' \
  --InstanceType "{{user.instance_type}}" \
  --ImageId "{{user.image_id}}" \
  --InstanceName "{{user.instance_name}}" \
  --SystemDisk '{"DiskType":"CLOUD_PREMIUM","DiskSize":50}' \
  --InternetAccessible '{"InternetChargeType":"TRAFFIC_POSTPAID_BY_HOUR","PublicIpAssigned":true}' \
  --SecurityGroupIds "[\"{{user.security_group_id}}\"]" \
  --VpcId "{{user.vpc_id}}" \
  --SubnetId "{{user.subnet_id}}" \
  --ClientToken "$(date +%s%N)" \
  --InstanceChargeType "POSTPAID_BY_HOUR"

# Capture instance ID from response
INSTANCE_ID=$(cat /tmp/response.json | jq -r '.Response.InstanceIdSet[0]')
```

#### Execution — Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
"""
SDK fallback for RunInstances when CLI parameter handling is complex
"""
import os, json, time
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cvm import cvm_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = cvm_client.CvmClient(cred, os.environ.get("TENCENTCLOUD_REGION"))
        
        req = models.RunInstancesRequest()
        req.Placement = models.Placement()
        req.Placement.Zone = os.environ.get("ZONE", "ap-guangzhou-3")
        req.InstanceType = os.environ.get("INSTANCE_TYPE", "S5.SMALL1")
        req.ImageId = os.environ.get("IMAGE_ID", "img-xxx")
        req.InstanceName = os.environ.get("INSTANCE_NAME", "test-instance")
        req.SystemDisk = models.SystemDisk()
        req.SystemDisk.DiskType = "CLOUD_PREMIUM"
        req.SystemDisk.DiskSize = 50
        req.InstanceChargeType = "POSTPAID_BY_HOUR"
        req.ClientToken = str(int(time.time() * 1000000))
        
        resp = client.RunInstances(req)
        print(json.loads(resp.to_json_string()))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

#### Post-execution Validation

1. Capture `{{output.instance_id}}` from `$.Response.InstanceIdSet[0]`
2. Poll DescribeInstances until `RUNNING`:

```bash
for i in $(seq 1 60); do
  STATUS=$(tccli cvm DescribeInstances --Region {{env.TENCENTCLOUD_REGION}} --InstanceIds "[\"{{output.instance_id}}\"]" | jq -r '.Response.InstanceSet[0].Status')
  [ "$STATUS" = "RUNNING" ] && echo "✅ Instance running" && break
  sleep 5
done
```

3. Report instance ID, public IP, and private IP to user

#### Failure Recovery

| Error pattern | Max retries | Backoff | Agent Action | UX Feedback |
|--------------|-------------|---------|--------------|-------------|
| `InvalidParameter.ImageIdMalformed` | 0 | — | Fix image ID format | `[ERROR] InvalidParameter.ImageIdMalformed: Image ID format invalid. Fix: Use valid format img-xxx. Next: DescribeImages to find valid images.` |
| `InvalidParameterValue.InstanceTypeUnsupported` | 0 | — | Check instance type availability in zone | `[ERROR] InvalidParameterValue: Instance type not available. Fix: Check zone-instance type matrix. Next: DescribeZoneInstanceConfigInfos` |
| `ResourceInsufficient.CvmInstanceQuotaIsFull` | 0 | — | HALT | `[ERROR] Quota exceeded. Fix: Request quota increase or delete unused instances. Next: DescribeAccountQuota` |
| `QuotaExceeded.SecurityGroupLimit` | 0 | — | HALT | `[ERROR] Security group quota exceeded. Fix: Use existing SG or request quota increase.` |
| `InvalidVpc.NotFound` | 0 | — | HALT, delegate to VPC skill | `[ERROR] VPC not found. Delegate to qcloud-vpc-ops.` |
| `RequestLimitExceeded` | 3 | exp | Back off, retry | `⚠️ Rate limit. Retrying...` |
| `InternalError` | 3 | 2s,4s,8s | Retry; HALT with RequestId if persists | `[ERROR] Internal error. Retry or escalate with RequestId.` |

### Operation: DescribeInstances

#### Execution — CLI

```bash
# Describe single instance
tccli cvm DescribeInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceIds "[\"{{user.instance_id}}\"]"

# Describe all instances (paginated)
tccli cvm DescribeInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Offset 0 --Limit 100
```

#### Present to User

| Field | Path | Notes |
|-------|------|-------|
| InstanceId | `$.Response.InstanceSet[0].InstanceId` | Primary identifier |
| InstanceName | `$.Response.InstanceSet[0].InstanceName` | Display name |
| Status | `$.Response.InstanceSet[0].Status` | RUNNING/STOPPED/SHUTDOWN |
| CPU | `$.Response.InstanceSet[0].CPU` | Core count |
| Memory | `$.Response.InstanceSet[0].Memory` | GB |
| PrivateIp | `$.Response.InstanceSet[0].PrivateIpAddresses[0]` | VPC internal IP |
| PublicIp | `$.Response.InstanceSet[0].PublicIpAddresses[0]` | External IP (if assigned) |
| CreatedTime | `$.Response.InstanceSet[0].CreatedTime` | ISO timestamp |
| InstanceType | `$.Response.InstanceSet[0].InstanceType` | e.g., S5.SMALL1 |

### Operation: StartInstances

#### Pre-flight

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | DescribeInstances | Instance found | HALT |
| Instance state | DescribeInstances | `STOPPED` | Warn if already RUNNING |

#### Execution — CLI

```bash
tccli cvm StartInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceIds "[\"{{user.instance_id}}\"]"
```

#### Validation

Poll until `RUNNING` (5s interval, 120s max).

### Operation: StopInstances

#### Pre-flight (Safety Gate)

- **MUST** warn: stopping instance interrupts service
- **MUST** confirm: `{{user.instance_id}}`, `{{user.instance_name}}`
- Check for critical processes (optional suggestion to user)

#### Execution — CLI

```bash
tccli cvm StopInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceIds "[\"{{user.instance_id}}\"]" \
  --StopType "SOFT"  # or "HARD" for forced stop
```

#### Validation

Poll until `STOPPED`.

### Operation: RebootInstances

#### Execution — CLI

```bash
tccli cvm RebootInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceIds "[\"{{user.instance_id}}\"]" \
  --RebootType "SOFT"  # or "HARD"
```

### Operation: TerminateInstances (Delete)

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible deletion of `{{user.instance_id}}` (`{{user.instance_name}}`)
- **MUST** warn: attached CBS disks may be deleted (check `DeleteWithInstance` flag)
- **MUST** suggest: create snapshot before deletion for backup
- **MUST NOT** proceed without clear user assent

#### Execution — CLI

```bash
# Terminate (release) instance
tccli cvm TerminateInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceIds "[\"{{user.instance_id}}\"]"
```

#### Validation

Poll DescribeInstances until:
- Empty response (instance removed)
- Status `TERMINATED` or 404

### Operation: ModifyInstanceAttribute

#### Execution — CLI

```bash
# Modify instance name
tccli cvm ModifyInstanceAttribute \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceId "{{user.instance_id}}" \
  --InstanceName "{{user.new_instance_name}}"

# Modify security groups
tccli cvm ModifyInstanceAttribute \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceId "{{user.instance_id}}" \
  --SecurityGroupIds "[\"sg-new1\",\"sg-new2\"]"
```

### Operation: ResizeInstanceDisk (CBS Disk Expansion)

#### Pre-flight

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance running | DescribeInstances | `RUNNING` | Stop instance first |
| Disk type supports resize | DescribeDisks | `CLOUD_PREMIUM`/`CLOUD_SSD` | HALT; some types limited |
| Target size > current | Check current disk size | Size increase | HALT; must increase |

#### Execution — CLI

```bash
tccli cvm ResizeInstanceDisks \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceId "{{user.instance_id}}" \
  --DataDisks "[{\"DiskId\":\"{{user.disk_id}}\",\"DiskSize\":{{user.new_disk_size}}}]"
```

### Operation: CreateSnapshot (Backup)

#### Pre-flight

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Disk attached | DescribeDisks | Disk in `ATTACHED` state | HALT |
| Quota | DescribeSnapshotQuota | Quota available | HALT |

#### Execution — CLI

```bash
tccli cbs CreateSnapshot \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --DiskId "{{user.disk_id}}" \
  --SnapshotName "backup-{{user.instance_id}}-$(date +%Y%m%d-%H%M%S)"
```

#### Validation

Poll DescribeSnapshots until `SUCCESS` status.

### Operation: CreateImage (Custom Image)

#### Execution — CLI

```bash
tccli cvm CreateImage \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceId "{{user.instance_id}}" \
  --ImageName "{{user.image_name}}" \
  --ImageDescription "Custom image created at $(date +%Y%m%d)"
```

---

## Prerequisites

### Option A: Cloud Shell (Zero Setup)

**Browser-based execution environment with pre-installed tools**:

1. **Access Cloud Shell**:
   - Login to [Tencent Cloud Console](https://console.cloud.tencent.com)
   - Click **Cloud Shell** icon (top right toolbar)
   - Terminal opens automatically

2. **Pre-installed Components**:
   - `tccli` CLI (latest version)
   - `tencentcloud-sdk-python` (full SDK)
   - Python 3.8+
   - Common tools: jq, vim, curl

3. **Pre-authenticated**: Uses console login credentials automatically

4. **Persistent Storage**: Save scripts in `/data/` (10GB)

```bash
# In Cloud Shell - no setup required
tccli cvm DescribeZones --Region ap-guangzhou

# Save scripts for reuse
mkdir -p /data/scripts
vim /data/scripts/create_instance.sh
```

**Cloud Shell Limitations**:
- 30 min idle timeout (reconnect after)
- Max 10 concurrent sessions
- Browser-based (not for CI/CD)

### Option B: Local CLI Installation

1. **Install `tccli` CLI**:

```bash
pip install tccli

# Or via Homebrew (macOS)
brew install tccli
```

2. **Bootstrap Python runtime** (SDK fallback):

```bash
python3 --version  # ≥ 3.8
pip install tencentcloud-sdk-python-cvm
```

3. **Configure Credentials**:

```bash
export TENCENTCLOUD_SECRET_ID="AKIDxxxx"
export TENCENTCLOUD_SECRET_KEY="xxxxx"
export TENCENTCLOUD_REGION="ap-guangzhou"
```

4. **Verify Configuration**:

```bash
tccli cvm DescribeZones --Region ap-guangzhou
```

### Quick Environment Check

```bash
# One-line verification (works in Cloud Shell and Local)
python3 -c "from tencentcloud.cvm import cvm_client; print('✅ SDK OK')" && tccli version
```

## Reference Directory

### Core References

- [Core Concepts](references/core-concepts.md) — Architecture, limits, regions, instance types
- [API & SDK Usage](references/api-sdk-usage.md) — Operation map, pagination, response schemas
- [CLI Usage Guide](references/cli-usage.md) — `tccli cvm` command reference
- [Troubleshooting Guide](references/troubleshooting.md) — CVM-specific error codes and fixes
- [Monitoring & Alerts](references/monitoring.md) — CVM metrics and alarm configuration
- [Integration](references/integration.md) — Cloud Shell, SDK setup, environment variables

### Well-Architected Framework

- [Well-Architected Assessment](references/well-architected-assessment.md) — Four-pillar assessment (Reliability, Security, Cost, Efficiency)

### FinOps Cost Optimization

- [FinOps Analysis](references/finops-analysis.md) — Cost anomaly detection, right-sizing, RI recommendations, idle resource analysis, monthly cost reports

### SecOps Security Operations

- [Audit Rules](references/audit-rules.md) — 50+ audit rules across lifecycle, security, network, credential, backup, cost, monitoring, and tagging with automated audit script
- [SecOps Checklist](references/secops-checklist.md) — Security audit logs, credential rotation, security group audit, network isolation, compliance checklist

### AIOps Intelligent Operations

- [Proactive Inspection](references/proactive-inspection.md) — Five-step closed-loop inspection workflow (Discovery → Collection → Detection → Diagnosis → Report)
- [AIOps Diagnosis](references/aiops-diagnosis.md) — Multi-metric correlation, cross-skill diagnosis decision tree, alarm storm handling, fault prediction

## Operational Best Practices

- **Least privilege**: CAM policies scoped to `cvm:*` APIs only
- **Availability**: Multi-AZ deployment with auto-recovery enabled
- **Cost**: Use prepaid for stable workloads, postpaid for variable
- **Backup**: Regular snapshots, cross-region image replication for DR

---

## Error Code Reference (CVM-Specific)

| Code | Meaning | Retry? | Agent Action |
|------|---------|--------|--------------|
| `InvalidParameter` | Generic parameter error | No | Fix per API spec |
| `InvalidParameter.ImageIdMalformed` | Image ID format wrong | No | Use `img-xxx` format |
| `InvalidParameterValue.InstanceTypeUnsupported` | Type not in zone | No | Check zone-type matrix |
| `InvalidParameterValue.ZoneNotSupported` | Zone invalid for operation | No | Use valid zone |
| `MissingParameter` | Required param absent | No | Add missing param |
| `ResourceNotFound.InstanceNotFound` | Instance ID invalid | No | Verify via Describe |
| `ResourceInsufficient.CvmInstanceQuotaIsFull` | Instance quota exceeded | No | Request quota increase |
| `QuotaExceeded.SecurityGroupLimit` | SG quota exceeded | No | Use existing SG |
| `InvalidVpc.NotFound` | VPC ID invalid | No | Delegate to VPC skill |
| `InvalidSubnet.NotFound` | Subnet ID invalid | No | Delegate to VPC skill |
| `OperationConflict.InstanceOperationConflict` | Another op in progress | Yes (3x, 30s) | Wait, retry |
| `RequestLimitExceeded` | API rate limit | Yes (3x, exp) | Back off |
| `InternalError` | Server error | Yes (3x) | Retry; escalate |

---

## Safety Gates (Destructive Operations)

Every **TerminateInstances**, **ResizeDisk**, or **irreversible** operation MUST have:

1. **Explicit user confirmation** with instance ID and name displayed
2. **Pre-backup reminder** (snapshot suggestion)
3. **Dependency check** (CBS disks, CLB attachments, auto-scaling group membership)
4. **Post-operation verification** (poll until 404 or terminal state)

---

## Output Schema

Standard Tencent Cloud API response:

```json
{
  "Response": {
    "RequestId": "abc123",
    "InstanceIdSet": ["ins-xxx"],
    ...
  }
}
```

Error response:

```json
{
  "Response": {
    "RequestId": "abc123",
    "Error": {
      "Code": "InvalidParameter",
      "Message": "Parameter validation failed"
    }
  }
}
```

## Variables

| Variable | Source | Description | Example |
|----------|--------|-------------|---------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | Environment | Tencent Cloud Secret ID | `AKID...` |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | Environment | Tencent Cloud Secret Key | `***` (masked) |
| `{{env.TENCENTCLOUD_REGION}}` | Environment | Region code | `ap-guangzhou` |
| `{{user.zone}}` | User | Availability zone | `ap-guangzhou-3` |
| `{{user.instance_type}}` | User | Instance type | `S5.SMALL1` |
| `{{user.image_id}}` | User | Image ID | `img-xxx` |
| `{{user.instance_name}}` | User | Instance name | `my-cvm` |
| `{{user.instance_id}}` | User | Instance ID | `ins-xxx` |
| `{{user.disk_size}}` | User | Disk size (GB) | `50` |
| `{{output.instance_id}}` | API Response | Created instance ID | `ins-xxx` |
| `{{output.request_id}}` | API Response | Request tracking ID | `abc123` |