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
  version: "1.0.0"
  last_updated: "2026-07-03"
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
tccli dc DescribeDirectConnects --Region ap-guangzhou
```

### Your First Command
```bash
# List available access points
tccli dc DescribeAccessPoints --Region ap-guangzhou
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

## Changelog

| Version | Date | Changes |
|---------|------|---------|
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

## GCL (Governance Check Loop)

This skill is marked `gcl: required` with `max_iter: 2` for destructive operations.

---

## Prerequisites

1. **Install `tccli` CLI:**

```bash
pip install tccli
tccli version
```

2. **Configure Credentials:**

```bash
export TENCENTCLOUD_SECRET_ID="AKID..."
export TENCENTCLOUD_SECRET_KEY="..."
export TENCENTCLOUD_REGION="ap-guangzhou"
```

3. **Verify:**

```bash
tccli dc DescribeDirectConnects --Region ap-guangzhou
```

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [CLI Usage](references/cli-usage.md)
- [Troubleshooting](references/troubleshooting.md)
- [Well-Architected Assessment](references/well-architected-assessment.md)
- [Integration](references/integration.md)
