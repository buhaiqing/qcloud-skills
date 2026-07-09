---
name: qcloud-dc-ops
description: >-
  Use when the user needs to create, configure, or troubleshoot Tencent Cloud
  Direct Connect (DC) — physical dedicated lines, direct connect tunnels,
  direct connect gateways, or专线接入. User mentions 专线, 物理专线,
  专用通道, 专线网关, dedicated line, direct connect, DC, 专线接入,
  边界路由器, BPG. Not for VPN (use `qcloud-vpn-ops`), CCN (use
  `qcloud-ccn-ops`), or VPC peering (use `qcloud-vpc-ops`).
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.1.0"
  last_updated: "2026-07-09"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/product/216"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli dc help` — CLI exposes CreateDirectConnect,
    DeleteDirectConnect, DescribeDirectConnects, CreateDirectConnectTunnel,
    DescribeDirectConnectTunnels, CreateDirectConnectGateway,
    DescribeDirectConnectGateways, and related operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
  gcl: required
  gcl_max_iter: 2
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud Direct Connect (DC) Operations Skill

## Overview

Tencent Cloud Direct Connect (DC) provides dedicated network connections from on-premises data centers to Tencent Cloud. It offers higher reliability, lower latency, and greater security than internet-based connections.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** `tccli dc` covers direct connect operations. You **MUST** ship `references/cli-usage.md` and document **both** the SDK and `tccli` step for every operation.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use with DC triggers; VPN → `qcloud-vpn-ops`; CCN → `qcloud-ccn-ops`; VPC peering → `qcloud-vpc-ops` |
| 2 | **Structured I/O** | `{{env.*}}` / `{{user.*}}` / `{{output.*}}` placeholders with DC API field types |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute (CLI + SDK) → Validate → Recover |
| 4 | **Complete Failure Strategies** | Error taxonomy with ≥ 10 DC-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | Direct Connect lifecycle only; VPN → `qcloud-vpn-ops`; CCN → `qcloud-ccn-ops` |

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Redundant connections, health checks, failover | `references/well-architected-assessment.md` |
| **安全性 (Security)** | Private connectivity, encryption, access control | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Bandwidth optimization, billing models | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Route optimization, traffic engineering | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "专线" OR "物理专线" OR "专用通道" OR "专线网关" OR "Direct Connect"
- Task keywords: dedicated line, DC, 专线接入, 边界路由器, BPG, 专线带宽
- User asks to create dedicated line, configure tunnel, or troubleshoot connectivity

### SHOULD NOT Use This Skill When

- Task is **VPN connection** → delegate to `qcloud-vpn-ops`
- Task is **CCN/cloud networking** → delegate to `qcloud-ccn-ops`
- Task is **VPC peering** → delegate to `qcloud-vpc-ops`
- Task is **load balancer** → delegate to `qcloud-clb-ops`

### Delegation Rules

- VPN tunnels: use `qcloud-vpn-ops`
- CCN cloud networking: use `qcloud-ccn-ops`
- VPC configuration: use `qcloud-vpc-ops`
- Cross-region networking: use `qcloud-ccn-ops`

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use documented default only if skill explicitly allows |
| `{{user.dc_id}}` | Direct Connect ID | Ask once or derive from `DescribeDirectConnects` |
| `{{user.tunnel_id}}` | Direct Connect Tunnel ID | Ask once or derive from API |
| `{{user.gateway_id}}` | Direct Connect Gateway ID | Ask once or derive from API |
| `{{user.access_point}}` | Access point location | Ask once |
| `{{user.bandwidth}}` | Bandwidth in Mbps | Ask once; validate supported values |
| `{{output.dc_id}}` | From API response | Parse per API spec |
| `{{output.tunnel_id}}` | From API response | Parse per API spec |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning:** NEVER expose `TENCENTCLOUD_SECRET_KEY` in output.

## JSON Path Reference

| Path | Maps To |
|------|---------|
| `dc.id` | `$.Response.DirectConnectSet[*].DirectConnectId` |
| `dc.name` | `$.Response.DirectConnectSet[*].DirectConnectName` |
| `dc.status` | `$.Response.DirectConnectSet[*].State` |
| `tunnel.id` | `$.Response.DirectConnectTunnelSet[*].DirectConnectTunnelId` |
| `tunnel.status` | `$.Response.DirectConnectTunnelSet[*].State` |
| `gateway.id` | `$.Response.DirectConnectGatewaySet[*].DirectConnectGatewayId` |

## Quick Start

### What This Skill Does
Enables you to create and manage Tencent Cloud Direct Connect — establish dedicated network connections between on-premises and cloud.

### Prerequisites
- [ ] `tccli` CLI installed
- [ ] Credentials: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region: `TENCENTCLOUD_REGION`
- [ ] Physical access to Tencent Cloud access point (or partner facility)

### Verify Setup
```bash
tccli dc DescribeDirectConnects --Region "{{env.TENCENTCLOUD_REGION}}"
```

### Your First Command
```bash
# List available access points
tccli dc DescribeAccessPoints --Region "{{env.TENCENTCLOUD_REGION}}"
```

### Next Steps
- [Common Operations](#execution-flows) — Create DC, tunnel, gateway
- [Troubleshooting](references/troubleshooting.md) — Fix connectivity issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreateDirectConnect | Apply for physical dedicated line | High | Low |
| DescribeDirectConnects | List dedicated lines | Low | None |
| DeleteDirectConnect | Delete dedicated line | Medium | **High** — requires offline coordination |
| CreateDirectConnectTunnel | Create dedicated tunnel | Medium | Medium |
| DescribeDirectConnectTunnels | List tunnels | Low | None |
| CreateDirectConnectGateway | Create DC gateway | Medium | Medium |
| DescribeDirectConnectGateways | List gateways | Low | None |
| CreateRedundantTunnel | Create backup tunnel for failover | Medium | Medium |
| ConfigureTunnelHealthCheck | Enable BFD/NQA health check | Medium | Medium |
| FailoverSwitch | Promote backup tunnel / reroute | Medium | **High** — reroutes live traffic |
| CreateCloudAttachService | Attach DC to CCN (multi-cloud/region) | Medium | Medium |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.1.0 | 2026-07-09 | Scenario enhancement: added redundant-tunnel (failover) provisioning, BFD/NQA health-check config, manual FailoverSwitch runbook, and multi-cloud/multi-region access via `CreateCloudAttachService` (CCN). Fixed credential masking in Prerequisites. Rubric safety rules extended to 5. |
| 1.0.0 | 2026-07-03 | Initial DC skill, dual-path execution. Scope: DC CRUD, tunnel management, gateway configuration. Delegates VPN to `qcloud-vpn-ops`, CCN to `qcloud-ccn-ops`. |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI and SDK) → Validate → Recover**.

### Operation: Create Direct Connect

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Credentials | `test -n "$TENCENTCLOUD_SECRET_ID"` etc. | Non-empty | HALT; user configures env |
| CLI installed | `tccli version` | Exit code 0 | Install tccli |
| Access point | `tccli dc DescribeAccessPoints` | Available points | HALT; contact Tencent Cloud |
| Quota | Check account quota | Within limit | HALT; request quota increase |

#### Execution — CLI (`tccli`) (Primary Path)

```bash
tccli dc CreateDirectConnect \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --DirectConnectName "{{user.dc_name}}" \
  --AccessPointId "{{user.access_point}}" \
  --LineOperator "{{user.operator}}" \
  --Bandwidth {{user.bandwidth}}
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Capture `{{output.dc_id}}` from `$.Response.DirectConnectId`.
2. Poll `DescribeDirectConnects` until `State = PENDING` (awaiting physical connection).

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.AccessPointNotFound` | Verify access point ID |
| `InvalidParameterValue.Bandwidth` | Use supported bandwidth value |
| `ResourceQuotaExceeded.DirectConnect` | HALT; request quota increase |
| `RequestLimitExceeded` | Backoff retry (2s,4s,8s) |

### Operation: Create Direct Connect Tunnel

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| DC exists | `DescribeDirectConnects` | State AVAILABLE | Create DC first |
| Gateway exists | `DescribeDirectConnectGateways` | Gateway exists | Create gateway first |

#### Execution — CLI

```bash
tccli dc CreateDirectConnectTunnel \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --DirectConnectId "{{output.dc_id}}" \
  --DirectConnectTunnelName "{{user.tunnel_name}}" \
  --DirectConnectGatewayId "{{user.gateway_id}}" \
  --NetworkType "{{user.network_type}}" \
  --NetworkRegion "{{user.network_region}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

Poll `DescribeDirectConnectTunnels` until `State = AVAILABLE`.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.DirectConnect` | Verify DC ID |
| `ResourceNotFound.DirectConnectGateway` | Verify gateway ID |
| `InvalidParameterValue.NetworkType` | Use supported network type |

### Operation: Describe Direct Connects

#### Execution — CLI

```bash
tccli dc DescribeDirectConnects \
  --Region "{{env.TENCENTCLOUD_REGION}}"
```

Filter by name:

```bash
tccli dc DescribeDirectConnects \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=direct-connect-name,Values={{user.dc_name}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

### Operation: Delete Direct Connect

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation with the DC ID and name.
- **MUST** warn: deleting a DC requires physical disconnection coordination.
- **MUST** verify no active tunnels exist (delete tunnels first).

#### Execution — CLI

```bash
# 1. Delete all tunnels first
for TUNNEL_ID in $(tccli dc DescribeDirectConnectTunnels \
  --Filters "Name=direct-connect-id,Values={{output.dc_id}}" \
  --query 'Response.DirectConnectTunnelSet[*].DirectConnectTunnelId'); do
  tccli dc DeleteDirectConnectTunnel --DirectConnectTunnelId "$TUNNEL_ID"
done

# 2. Delete DC
tccli dc DeleteDirectConnect \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --DirectConnectId "{{output.dc_id}}"
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

Poll `DescribeDirectConnects`; expect DC absent within 60s.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.DirectConnect` | Already deleted; treat as success |
| `OperationDenied.HasTunnels` | Delete all tunnels first |
| `OperationDenied.DCInUse` | Remove dependencies first |

### Operation: Create Redundant Tunnel (Failover Prep)

Provision a **backup tunnel** (on a second physical line / second DC, or a second tunnel on the
same DC) so traffic can fail over when the primary fails.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Primary DC/tunnel healthy | `DescribeDirectConnectTunnels` | `State=AVAILABLE` | Fix primary first |
| Gateway exists | `DescribeDirectConnectGateways` | Gateway exists | Create gateway first |
| Backup line available | `DescribeDirectConnects` | Second DC AVAILABLE or port free | Order backup line |

#### Execution — CLI

```bash
tccli dc CreateDirectConnectTunnel \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --DirectConnectId "{{user.backup_dc_id}}" \
  --DirectConnectTunnelName "{{user.backup_tunnel_name}}" \
  --DirectConnectGatewayId "{{user.gateway_id}}" \
  --NetworkType "VPC" \
  --NetworkRegion "{{user.network_region}}" \
  --Bandwidth {{user.backup_bandwidth}} \
  --BfdEnable 1 \
  --NqaEnable 1
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

Poll `DescribeDirectConnectTunnels --Filters "Name=direct-connect-id,Values={{user.backup_dc_id}}"` until `State=AVAILABLE`.

### Operation: Configure Tunnel Health Check (BFD / NQA)

Enables sub-second failure detection so failover is automatic.

#### Execution — CLI

```bash
tccli dc ModifyDirectConnectTunnelExtra \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --DirectConnectTunnelId "{{output.tunnel_id}}" \
  --BfdEnable 1 \
  --BfdInfo '{"ProbeInterval":1000,"ProbeThreshold":3,"ProbeTimeout":200}' \
  --NqaEnable 1 \
  --NqaInfo '{"ProbeInterval":1000,"ProbeThreshold":3,"ProbeTimeout":200}'
```

#### Post-execution Validation

Verify via `DescribeDirectConnectTunnelExtra --DirectConnectTunnelId "{{output.tunnel_id}}"` that `BfdEnable=1` and `NqaEnable=1`.

### Operation: Failover Switch (Promote Backup)

#### Pre-flight (Safety Gate)

- **MUST** confirm the primary tunnel is actually down (BFD/NQA `Down`, or `DescribeDirectConnectTunnelExtra` shows session lost).
- **MUST** confirm the backup tunnel is `AVAILABLE` and healthy.
- **MUST** warn: switching withdraws primary routes and **reroutes live production traffic** to the backup path.
- **MUST** confirm failover not already applied (primary `ImportDirectRoute` still `true` before switch).
- With BFD/NQA enabled, failover is automatic; only run a manual switch when automatic failover did not trigger.

#### Execution — CLI

```bash
# 1. Verify backup tunnel health
tccli dc DescribeDirectConnectTunnelExtra \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --DirectConnectTunnelId "{{user.backup_tunnel_id}}"

# 2. Withdraw primary routes (manual switch) — reroute to backup
tccli dc ModifyDirectConnectTunnelExtra \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --DirectConnectTunnelId "{{user.primary_tunnel_id}}" \
  --ImportDirectRoute false

# 3. Confirm backup now carries traffic (route propagation / on-prem ping)
```

#### Post-execution Validation

1. `DescribeDirectConnectTunnels` shows primary `State` down and backup `AVAILABLE`.
2. On-prem connectivity test (ping VPC CIDR) succeeds via backup path.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.DirectConnectTunnel` | Verify tunnel IDs |
| Backup not `AVAILABLE` | Wait for backup provisioning; do NOT withdraw primary yet |
| `OperationDenied` | Automatic failover still active; avoid double-switch |
| Already switched (primary routes already withdrawn) | Verify backup carries traffic via `DescribeDirectConnectTunnelExtra`; treat as no-op, do not re-withdraw |

### Operation: Multi-cloud / Multi-region Access (Cloud Attach → CCN)

Attach the dedicated line to a **Cloud Attach Service (CCN)** so on-prem/other-cloud traffic
reaches multiple VPCs and regions. CCN routing configuration is delegated to `qcloud-ccn-ops`.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| DC gateway exists | `DescribeDirectConnectGateways` | Gateway exists | Create gateway first |
| CCN instance exists | delegate to `qcloud-ccn-ops` | CCN ID known | Create CCN first |
| Region support | `DescribeAccessPoints` | Region supported | Use supported region |

#### Execution — CLI

```bash
tccli dc CreateCloudAttachService \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Data '{"CcasType":"CCN","ProviderName":"tencent","DirectConnectGatewayId":"{{user.gateway_id}}","CcnId":"{{user.ccn_id}}"}'
```

#### Execution — Python SDK (Fallback Path)

→ SDK 代码示例见 [references/sdk-code-examples.md](references/sdk-code-examples.md)

#### Post-execution Validation

1. Capture `{{output.cloud_attach_id}}` from `$.Response.CloudAttach.CloudAttachId`.
2. Delegate CCN attachment verification to `qcloud-ccn-ops` (`AttachCcnInstances`).

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.DirectConnectGateway` | Verify gateway ID |
| `InvalidParameter.CcnNotFound` | Create/verify CCN via `qcloud-ccn-ops` |
| `OperationDenied.GatewayInUse` | Gateway already attached; verify existing `CloudAttachId` matches expected CCN; reuse or detach first |

## Error Code Reference (DC-Specific)

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter.AccessPointNotFound` | Access point not found | Verify access point ID |
| `InvalidParameterValue.Bandwidth` | Invalid bandwidth value | Use supported values |
| `ResourceNotFound.DirectConnect` | DC ID not found | Verify DC ID |
| `ResourceNotFound.DirectConnectTunnel` | Tunnel ID not found | Verify tunnel ID |
| `ResourceNotFound.DirectConnectGateway` | Gateway ID not found | Verify gateway ID |
| `ResourceQuotaExceeded.DirectConnect` | DC quota exceeded | HALT; request quota increase |
| `OperationDenied.HasTunnels` | DC has active tunnels | Delete tunnels first |
| `OperationDenied.DCInUse` | DC is in use | Remove dependencies first |
| `OperationDenied.DCNotAvailable` | DC not in available state | Wait for DC provisioning |
| `InvalidSecretKey` | Credential invalid | HALT; fix credentials |
| `RequestLimitExceeded` | API rate limit | Exponential backoff (3x) |
| `InternalError` | Server error | Retry with RequestId (3x) |

## Safety Gates (Destructive Operations)

Every **DeleteDirectConnect** MUST have:

1. Explicit user confirmation with DC ID
2. Dependency check (active tunnels, attached resources)
3. Pre-warning about physical disconnection requirements
4. Post-delete verification (poll until absent)

**FailoverSwitch** and **CreateCloudAttachService** are semi-destructive (affect live routing):

- **FailoverSwitch** MUST confirm primary is actually down, backup is `AVAILABLE`, and warn that it reroutes production traffic. With BFD/NQA enabled, prefer automatic failover.
- **CreateCloudAttachService** MUST confirm the CCN ID and delegate detach/routing cleanup to `qcloud-ccn-ops`.

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** quality gate for all mutation operations.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | frontmatter `gcl: required` |
| max_iterations | **2** | frontmatter `gcl_max_iter: 2` |
| Rubric instance | `references/rubric.md` | 5 dimensions, DC-specific safety rules |
| Prompt templates | `references/prompt-templates.md` | Generator + Critic + Orchestrator |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | per AGENTS.md §7 |

### When the loop runs

| Operation | Loop required? | Reason |
|---|---|---|
| `CreateDirectConnect` | Yes | Creates new DC |
| `DeleteDirectConnect` | Yes (blocking) | Physical disconnection, tunnel cleanup required |
| `CreateDirectConnectTunnel` | Yes | Creates tunnel |
| `DeleteDirectConnectTunnel` | Yes (blocking) | Cuts connection |
| `CreateDirectConnectGateway` | Yes | Creates gateway |
| `DeleteDirectConnectGateway` | Yes (blocking) | Removes routing, dependency cleanup required |
| `CreateRedundantTunnel` | Yes | Provisions backup path |
| `ConfigureTunnelHealthCheck` | Yes | Enables BFD/NQA detection |
| `FailoverSwitch` | Yes (blocking) | Reroutes live production traffic |
| `CreateCloudAttachService` | Yes | Attaches DC to CCN (delegate routing to `qcloud-ccn-ops`) |
| `DescribeDirectConnects` | No | Read-only |
| `DescribeDirectConnectTunnels` | No | Read-only |
| `DescribeDirectConnectGateways` | No | Read-only |

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
tccli dc DescribeDirectConnects --Region "{{env.TENCENTCLOUD_REGION}}"
```

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [CLI Usage](references/cli-usage.md)
- [Troubleshooting](references/troubleshooting.md)
- [Well-Architected Assessment](references/well-architected-assessment.md)
- [Integration](references/integration.md)
