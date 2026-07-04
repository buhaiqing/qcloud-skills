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
  version: "1.3.0"
  last_updated: "2026-07-04"
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

CVM operational runbook: dual-path (`tccli` + Python SDK), explicit pre-flight/validate/recover, web console not an agent path.

## Five Core Standards (Quality Gates)

1-5: Clear Boundaries, Structured I/O (`{{env.*}}`/`{{user.*}}`/`{{output.*}}`), Explicit Steps (Pre-flight→Execute→Validate→Recover), Complete Failure Strategies (≥12 CVM codes), Single Responsibility (CVM instances+CBS disks).

[WA integration](references/well-architected-assessment.md): Reliability (multi-AZ/backup/DR), Security (CAM/SSH/SG), Cost (type comparison/RI/idle), Efficiency (batch/auto-scaling/schedule).

## Trigger & Scope

**SHOULD:** CVM instance lifecycle (CRUD/start/stop/reboot/terminate), CBS disks (attach/detach/resize), snapshots/images, SSH/migration/performance issues.

**SHOULD NOT:** billing → `qcloud-billing-ops`, CAM → `qcloud-cam-ops`, VPC-only → `qcloud-vpc-ops`, CLB → `qcloud-clb-ops`, DB → `qcloud-cdb-ops`/`qcloud-redis-ops`, WA review → `qcloud-well-architected-review`.

**Delegate:** VPC/SG pre-check via VPC skill before RunInstances; CLB → CLB skill; CBS within CVM scope; snapshots/images within CVM scope; multi-product → per-skill. Read-only WA assessment → see below.

## Read-Only Assessment (WA delegate)

When `{{user.mode}}=well-architected-readonly`: read-only Describe*/GetMonitorData only. Execute [well-architected-assessment.md](references/well-architected-assessment.md) Worker Output Contract; paginate → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: cvm`).

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

## API Conventions

**API:** https://cloud.tencent.com/document/api/213. **Errors:** `Response.Error.Code`/`Message`. **Timestamps:** ISO 8601. **Idempotency:** `ClientToken` for RunInstances.

### Expected State Transitions

| Operation | Initial → Target | Wait |
|-----------|-----------------|------|
| RunInstances | → `RUNNING` | 5s×60 |
| StartInstances | `STOPPED`→`RUNNING` | 5s×24 |
| StopInstances | `RUNNING`→`STOPPED` | 5s×24 |
| RebootInstances | any→`RUNNING` | 5s×24 |
| TerminateInstances | any→404 | 5s×60 |

## Quick Start

| Env | Setup |
|-----|-------|
| **Cloud Shell** | [Console](https://console.cloud.tencent.com) → Cloud Shell icon. Pre-installed `tccli`/SDK, pre-authenticated, 10GB `/data/`. Limit: 30min idle, 10 sessions, no CI/CD. |
| **Local CLI** | `pip install tccli` + `TENCENTCLOUD_SECRET_ID`/`_KEY`/`_REGION` |
| **Local SDK** | `pip install tencentcloud-sdk-python-cvm` + same credentials |

```bash
# Verify (Cloud Shell or local)
tccli cvm DescribeZones --Region ap-guangzhou && python3 -c "from tencentcloud.cvm import cvm_client"

# First command
tccli cvm DescribeInstances --Region {{env.TENCENTCLOUD_REGION}}
```

**Next:** [Execution Flows](#execution-flows), [CLI Usage](references/cli-usage.md), [Integration](references/integration.md), [Troubleshooting](references/troubleshooting.md).

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
| ModifyInstanceSpec | Change instance type (CPU/memory) | Medium | Medium (requires STOPPED) |
| AttachDisks | Attach CBS disks to instance | Low | None |
| DetachDisk | Detach CBS disk from instance | Low | Medium (service interruption) |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial skill with RunInstances, DescribeInstances, Start/Stop/Reboot/Terminate, CBS disk operations, Snapshot/Image management |
| 1.1.0 | 2026-06-04 | Phase 1 GCL pilot: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 CVM-specific safety rules), `references/prompt-templates.md` (Generator + Critic + Orchestrator, isolated-context enforcement). `max_iter=2` per AGENTS.md §8 |
| 1.2.0 | 2026-06-27 | Round 1 self-review fixes: added ResetInstances execution flow (G1), TerminateInstances DryRun pre-flight (G2), SDK fallback for ResizeInstanceDisks/CreateSnapshot/CreateImage (G3-G5), StopInstances HARD gate (G6). Bumped version. |
| 1.3.0 | 2026-07-04 | Added ModifyInstanceSpec, AttachDisks, DetachDisk operations; created references/sdk-templates.md; replaced inline SDK blocks with references; merged Prerequisites into Quick Start; removed duplicate Variables section. Bumped version. |

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
  --InstanceChargeType "POSTPAID_BY_HOUR" > /tmp/response.json

# Capture instance ID from response
INSTANCE_ID=$(jq -r '.Response.InstanceIdSet[0]' /tmp/response.json)
```

#### Execution — Python SDK (Fallback Path)

> See [SDK Templates](references/sdk-templates.md) for common init/poll/error boilerplate.

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

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

| Error pattern | Retry Strategy | Recovery |
|--------------|----------------|----------|
| `InvalidParameter.ImageIdMalformed` | 0 | Fix image ID format to `img-xxx`; use DescribeImages to find valid images |
| `InvalidParameterValue.InstanceTypeUnsupported` | 0 | Check zone-instance type matrix via DescribeZoneInstanceConfigInfos |
| `ResourceInsufficient.CvmInstanceQuotaIsFull` | 0 | HALT. Request quota increase or delete unused instances |
| `QuotaExceeded.SecurityGroupLimit` | 0 | HALT. Use existing SG or request quota increase |
| `InvalidVpc.NotFound` | 0 | HALT. Delegate to qcloud-vpc-ops |
| `RequestLimitExceeded` | 3, exp backoff | Back off and retry |
| `InternalError` | 3 (2s,4s,8s) | Retry; HALT with RequestId if persists |

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

#### Execution — Python SDK (Fallback Path)

> See [SDK Templates](references/sdk-templates.md) for common init/poll/error boilerplate.

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

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

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Validation

Poll until `RUNNING` (5s interval, 120s max).

### Operation: StopInstances

#### Pre-flight (Safety Gate)

- **MUST** warn: stopping instance interrupts service
- **MUST** confirm: `{{user.instance_id}}`, `{{user.instance_name}}`
- Check for critical processes (optional suggestion to user)
- **If `StopType=HARD`**: block on production instance (name matches `^(prod|prd|live)-` or tag `Role=production`); require user to re-confirm with literal `"yes, force stop prod"` — HARD is equivalent to pulling power

#### Execution — CLI

```bash
tccli cvm StopInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceIds "[\"{{user.instance_id}}\"]" \
  --StopType "SOFT"  # or "HARD" for forced stop
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

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

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

### Operation: ResetInstance (Re-image)

> **⚠️ Destructive — re-images the instance OS.** This is NOT a restart. All data on the system disk is replaced. Use with extreme caution.

#### Pre-flight (Safety Gate — per rubric Rule 5)

- **MUST** confirm: `{{user.instance_id}}`, `{{user.instance_name}}` echoed by Agent
- **MUST** verify `ImageId` differs from current image (`DescribeInstances` → `OsPublicIdsSet` or `OsName`)
- **MUST** verify instance state is `STOPPED` or `SHUTDOWN`
- **MUST** warn: system disk will be wiped; all data on system disk is lost
- **MUST** suggest: snapshot of system disk before re-imaging
- **MUST NOT** proceed if instance is `RUNNING`

#### Execution — CLI

```bash
# Pre-flight: verify instance state and image
tccli cvm DescribeInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceIds "[\"{{user.instance_id}}\"]" | jq -r '.Response.InstanceSet[0].Status, .Response.InstanceSet[0].OsPublicIdsSet[0]'

# Commit re-image (API: ResetInstance, singular)
tccli cvm ResetInstance \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceId "{{user.instance_id}}" \
  --ImageId "{{user.image_id}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Validation

Poll DescribeInstances until `RUNNING`, then confirm new OS matches `{{user.image_id}}`.

### Operation: TerminateInstances (Delete)

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible deletion of `{{user.instance_id}}` (`{{user.instance_name}}`)
- **MUST** warn: attached CBS disks may be deleted (check `DeleteWithInstance` flag)
- **MUST** suggest: create snapshot before deletion for backup
- **MUST NOT** proceed without clear user assent
- **DryRun**: for batch (n>1), run `--DryRun` first and abort if it returns error; for single, run `--DryRun` first as a sanity gate
- **Dependency check**: query CBS disks (`DescribeDisks`), CLB backend targets (`DescribeTargets`), and ASG membership (`DescribeAutoScalingInstances`) before commit

#### Execution — CLI

```bash
# DryRun sanity check (run before any commit)
tccli cvm TerminateInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceIds "[\"{{user.instance_id}}\"]" \
  --DryRun

# Commit only after DryRun passes and user confirmed
tccli cvm TerminateInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceIds "[\"{{user.instance_id}}\"]"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Validation

1. Run DryRun first: `DryRun=true`; abort if it returns error
2. Poll DescribeInstances until:
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

### Operation: ModifyInstanceSpec (Change Instance Type)

> **⚠️ Requires instance in `STOPPED` state.** Changing instance type (CPU/memory) is a cold migration — the instance must be stopped before modification.

#### Pre-flight

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | DescribeInstances | Instance found | HALT |
| Instance state | DescribeInstances | `STOPPED` | HALT; stop instance first |
| Current spec | DescribeInstances → `$.InstanceType` | Known | Continue |
| Target differs | User-provided value | Different from current | HALT; target same as current |

#### Execution — CLI

```bash
tccli cvm ModifyInstanceSpec \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceId "{{user.instance_id}}" \
  --InstanceType "{{user.new_instance_type}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Validation

Poll DescribeInstances until `STOPPED` (spec change completes while stopped), then confirm `$.InstanceType` matches `{{user.new_instance_type}}`.

#### Failure Recovery

| Error pattern | Max retries | Recovery |
|--------------|-------------|----------|
| `InvalidParameterValue.InstanceTypeNotSupported` | 0 | Check zone-instance type matrix via DescribeZoneInstanceConfigInfos |
| `InvalidInstanceState.InstanceIsRunning` | 0 | HALT; instance must be STOPPED |
| `TradeError.PriceError` | 0 | HALT; check billing eligibility for target type |
| `RequestLimitExceeded` | 3, exp backoff | Back off and retry |
| `InternalError` | 3 (2s,4s,8s) | Retry; HALT with RequestId if persists |

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

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

### Operation: CreateSnapshot (Backup)

> **Note on CBS API Namespace:** The `CreateSnapshot` and disk-related operations below use the CBS (Cloud Block Storage) API namespace (`tccli cbs`) rather than the CVM API. These operations are within CVM scope because CBS disks are directly attached storage for CVM instances and are essential to the instance lifecycle (backup, restore, resize). Standalone CBS management (e.g., creating independent disks not attached to instances) is also covered by this skill since CBS is tightly coupled with CVM operations.

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

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

### Operation: CreateImage (Custom Image)

#### Pre-flight

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | DescribeInstances | Instance found | HALT |
| Instance state | DescribeInstances | `RUNNING` or `SHUTDOWN` | HALT; imaging `PENDING`/`REBOOTING` is unsafe |
| Image name unique | DescribeImages | No duplicate | Warn; proceed if intentional |

#### Execution — CLI

```bash
tccli cvm CreateImage \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceId "{{user.instance_id}}" \
  --ImageName "{{user.image_name}}" \
  --ImageDescription "Custom image created at $(date +%Y%m%d)"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

### Operation: AttachDisks (Attach CBS Disks)

> **Note:** Uses CBS API namespace (`tccli cbs`). Attaches existing CBS disks to a running CVM instance.

#### Pre-flight

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | DescribeInstances | Instance found | HALT |
| Instance state | DescribeInstances | `RUNNING` | HALT; start instance first |
| Disks exist | DescribeDisks | All found | HALT; verify disk IDs |
| Disk state | DescribeDisks | `NOT_ATTACHED` | HALT; disk already attached |

#### Execution — CLI

```bash
tccli cbs AttachDisks \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceId "{{user.instance_id}}" \
  --DiskIds "[\"{{user.disk_id}}\"]"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Validation

Poll DescribeDisks until disk `Attached` status and `InstanceId` matches `{{user.instance_id}}`.

#### Failure Recovery

| Error pattern | Max retries | Recovery |
|--------------|-------------|----------|
| `InvalidDisk.NotSupported` | 0 | HALT; disk type not attachable to this instance |
| `InvalidDisk.DiskAttached` | 0 | HALT; disk already attached to an instance |
| `InvalidInstance.NotSupported` | 0 | HALT; instance does not accept more disks |
| `RequestLimitExceeded` | 3, exp backoff | Back off and retry |
| `InternalError` | 3 (2s,4s,8s) | Retry; HALT with RequestId if persists |

### Operation: DetachDisk (Detach CBS Disk)

> **⚠️ Service interruption:** Detaching a data disk may cause I/O errors if the disk is in use. Unmount the filesystem before detaching.

#### Pre-flight

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | DescribeInstances | Instance found | HALT |
| Disk exists | DescribeDisks | Disk found | HALT |
| Disk attached to instance | DescribeDisks | `InstanceId` matches `{{user.instance_id}}` | HALT; disk not attached to this instance |
| Warn unmount | Prompt user | User confirms filesystem unmounted | HALT; unmount first |

#### Execution — CLI

```bash
tccli cbs DetachDisk \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --InstanceId "{{user.instance_id}}" \
  --DiskId "{{user.disk_id}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Validation

Poll DescribeDisks until disk `NOT_ATTACHED` state and `InstanceId` is absent.

#### Failure Recovery

| Error pattern | Max retries | Recovery |
|--------------|-------------|----------|
| `InvalidDisk.NotSupported` | 0 | HALT; disk type does not support detach |
| `InvalidDisk.DiskBusy` | 0 | HALT; unmount filesystem, wait for I/O to drain |
| `InvalidDisk.NotAttached` | 0 | HALT; disk not attached to specified instance |
| `RequestLimitExceeded` | 3, exp backoff | Back off and retry |
| `InternalError` | 3 (2s,4s,8s) | Retry; HALT with RequestId if persists |



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
- [AIOps Diagnosis](references/aiops-diagnosis.md) — Delegate to `qcloud-aiops-diagnosis` for multi-metric RCA and alarm storm bundling

## Operational Best Practices

- **Least privilege**: CAM policies scoped to `cvm:*` APIs only
- **Availability**: Multi-AZ deployment with auto-recovery enabled
- **Cost**: Use prepaid for stable workloads, postpaid for variable
- **Backup**: Regular snapshots, cross-region image replication for DR

---

## Error Code Reference (CVM-Specific)

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter` | Generic parameter error | Fix per API spec |
| `InvalidParameter.ImageIdMalformed` | Image ID format wrong | Use `img-xxx` format |
| `InvalidParameterValue.InstanceTypeUnsupported` | Type not in zone | Check zone-type matrix |
| `InvalidParameterValue.ZoneNotSupported` | Zone invalid for operation | Use valid zone |
| `MissingParameter` | Required param absent | Add missing param |
| `ResourceNotFound.InstanceNotFound` | Instance ID invalid | Verify via Describe |
| `ResourceInsufficient.CvmInstanceQuotaIsFull` | Instance quota exceeded | Request quota increase |
| `QuotaExceeded.SecurityGroupLimit` | SG quota exceeded | Use existing SG |
| `InvalidVpc.NotFound` | VPC ID invalid | Delegate to VPC skill |
| `InvalidSubnet.NotFound` | Subnet ID invalid | Delegate to VPC skill |
| `OperationConflict.InstanceOperationConflict` | Another op in progress | Retry (3x, 30s) |
| `RequestLimitExceeded` | API rate limit | Retry (3x, exp backoff) |
| `InternalError` | Server error | Retry (3x); escalate |

---

## Safety Gates (Destructive Operations)

Every **TerminateInstances**, **ResizeDisk**, or **irreversible** operation MUST have:

1. **Explicit user confirmation** with instance ID and name displayed
2. **Pre-backup reminder** (snapshot suggestion)
3. **Dependency check** (CBS disks, CLB attachments, auto-scaling group membership)
4. **Post-operation verification** (poll until 404 or terminal state)

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate
is a **runtime** scoring layer that audits each CVM execution against an explicit
rubric, in addition to the build-time **Safety Gates** above and the build-time
**2-round self-review** in [AGENTS.md](../../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **2** | per-skill override (matches AGENTS.md §8 default for `qcloud-cvm-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 CVM-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive: `TerminateInstances`, `ResetInstance`, `ResizeInstanceDisks` (shrink blocked by rule 3), `TerminateDisks` (CBS) | **yes** | Irreversible or near-irreversible; needs scoring |
| Mutating: `RunInstances`, `StopInstances`, `RebootInstances`, `ModifyInstanceAttribute`, `ResizeInstanceDisks` (grow only), `CreateImage`, `CreateSnapshot` | **yes** | Cost / state-change risk; needs scoring |
| Read-only: `DescribeInstances`, `DescribeImages`, `DescribeSnapshots`, `DescribeAccountQuota` | optional (max_iter=1, no hard abort) | Polling tails are part of the parent op's trace |

### Decision flow (first match wins)

1. **Safety = 0** OR rule violation in `{1, 2, 5}` ⇒ **ABORT** (no partial result)
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

### CVM-specific safety rules (rubric §4)

Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | `TerminateInstances` (any, batch or single) | ID + Name echo + explicit confirmation + `DeleteWithInstance` query + dependency check (CLB / ASG... |
| 2 | `StopInstances` with `--StopType HARD` | Block on production instance (heuristic: name matches `^(prod|prd|live)-` or any instance with `T... |
| 3 | `ResizeInstanceDisks` | Target `DiskSize` ≥ current `DiskSize`; `DiskType` must be resizable (no `LOCAL_BASIC`/`LOCAL_SSD... |
| 4 | `RunInstances` | `ClientToken` MUST be set; zone-instance type matrix MUST be validated (`DescribeZoneInstanceConf... |
| 5 | `ResetInstance` | `ImageId` MUST differ from current; current state MUST be `STOPPED` or `SHUTDOWN`; explicit confi... |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — `StopInstances` (HARD on prod)

| Dimension | Score |
|---|---|
| Correctness | 0.5 (state did transition, but gate should have caught it) |
| **Safety** | **0** (rule 2 violated) |
| Idempotency | 1 |
| Traceability | 1 |
| Spec Compliance | 1 |

`decision: ABORT`. Recovery suggestion emitted: power back on with `StartInstances` and re-run with `StopType=SOFT` (or with explicit prod exception).

See [`references/rubric.md`](references/rubric.md) §6 for two more examples (PASS on `TerminateInstances` and RETRY on `RunInstances`).

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
