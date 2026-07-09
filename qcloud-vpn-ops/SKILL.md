---
name: qcloud-vpn-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud VPN (IPSec VPN / SSL VPN) — VPN Gateway, VPN Tunnel (IPSec VPN
  Connection), Customer Gateway, SSL VPN Server, SSL VPN Client, and the hybrid
  cloud connectivity they provide. User mentions VPN, IPSec, SSL VPN, 虚拟专用网络,
  VPN 网关, VPN 通道, 客户网关, hybrid cloud, on-prem connectivity, or describes
  scenarios requiring encrypted tunnels between a Tencent VPC and an on-prem /
  remote network. Not for billing, CAM, multi-region VPC interconnect (use
  `qcloud-ccn-ops`), same-region same-account VPC peering (use `qcloud-vpc-ops`),
  physical dedicated line (Direct Connect), or related products that have their
  own ops skills.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.4.0"
  last_updated: "2026-07-09"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/215/30691"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli vpc help` and `tccli vpc help CreateVpnGateway` —
    CLI exposes CreateVpnGateway, DescribeVpnGateways, DeleteVpnGateways,
    ModifyVpnGatewayAttribute, CreateVpnConnection, DescribeVpnConnections,
    DeleteVpnConnections, ModifyVpnConnectionAttribute, CreateCustomerGateway,
    DescribeCustomerGateways, DeleteCustomerGateways, ModifyCustomerGatewayAttribute,
    CreateVpnGatewaySslServer, DescribeVpnGatewaySslServers, DeleteVpnGatewaySslServers,
    CreateVpnGatewaySslClient, DescribeVpnGatewaySslClients, DeleteVpnGatewaySslClients,
    and related operations. All VPN APIs share the `vpc` product namespace.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud VPN Operations Skill

## Overview

Tencent Cloud VPN provides encrypted hybrid cloud connectivity from a VPC to on-prem or remote networks via two flavors:

- **IPSec VPN** — site-to-site encrypted tunnel between a **VPN Gateway** (in the VPC) and a peer device called a **Customer Gateway** (the on-prem / remote endpoint). Used for steady, always-on hybrid cloud traffic.
- **SSL VPN** — remote-access VPN where individual clients connect to an **SSL VPN Server** (fronted by a VPN Gateway) using the SSL VPN client. Used for telecommuters and O&M.

This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (`tccli` and `tencentcloud-sdk-python`), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

> **UX Compliance:** This skill follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md).

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** `tccli vpc` covers VPN operations. You **MUST** ship `references/cli-usage.md` and document **both** the SDK and `tccli` step for every operation.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with VPN-specific triggers; multi-region VPC interconnect → delegate to `qcloud-ccn-ops`; same-region peering → delegate to `qcloud-vpc-ops` |
| 2 | **Structured I/O** | `{{env.*}}` / `{{user.*}}` / `{{output.*}}` placeholders with VPN API field types |
| 3 | **Explicit Actionable Steps** | Every VPN op: Pre-flight → Execute (CLI + SDK) → Validate → Recover |
| 4 | **Complete Failure Strategies** | Error taxonomy with ≥ 10 VPN-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | VPN Gateway / IPSec Connection / Customer Gateway / SSL VPN Server / SSL VPN Client only; CCN / VPC Peering / Direct Connect → sibling skills |

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Active-standby / dual-tunnel VPN, BGP failover, health checks | `references/well-architected-assessment.md` |
| **安全性 (Security)** | Pre-shared key rotation, IKE / IPSec policy hardening, SSL client cert lifecycle | `references/well-architected-assessment.md` |
| **成本 (Cost)** | VPN Gateway hourly fee, traffic billing, right-sizing bandwidth cap | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Batch tunnel setup, route-table automation, SSL client bulk provisioning | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Tencent Cloud VPN" OR "IPSec VPN" OR "SSL VPN" OR "虚拟专用网络" OR "VPN 网关" OR "客户网关" OR "hybrid cloud" OR "on-prem connectivity"
- Task keywords: VPN gateway, VPN tunnel, VPN connection, customer gateway, IKE, pre-shared key, SSL VPN server, SSL VPN client, hybrid cloud, site-to-site, remote access, multi-branch topology, branch office, hub-and-spoke, active-standby failover
- User describes a scenario requiring **encrypted tunnels between a Tencent VPC and on-prem / remote networks** (IPSec) or **remote user access** to a VPC (SSL)
- User asks to design, deploy, configure, monitor, or troubleshoot a VPN connection end-to-end

### SHOULD NOT Use This Skill When

- Task is **multi-region VPC-to-VPC** interconnect (public internet backbone) → delegate to `qcloud-ccn-ops`
- Task is **same-region same-account cross-VPC** connectivity → delegate to `qcloud-vpc-ops` (VPC Peering is cheaper and lower latency than VPN for this case)
- Task is **physical dedicated line** (Direct Connect) — out of scope; raise a follow-up `qcloud-dc-ops` skill
- Task is purely billing / account management → delegate to `qcloud-billing-ops`
- Task is CAM / permission model only → delegate to `qcloud-cam-ops`

### Delegation Rules

- A VPN Gateway must be attached to a VPC; **VPC/Subnet/Route Table** CRUD belongs to `qcloud-vpc-ops`. After a VPN Connection is created, the **VPC route table** needs a route with `NextType=VPNGW` pointing at the gateway; that route work belongs to `qcloud-vpc-ops`.
- For a multi-region VPN mesh, the VPN Gateways are independent and connect via the public internet; CCN is **not** required for VPN.
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs.

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use documented default only if skill explicitly allows |
| `{{user.vpn_gateway_name}}` | User-supplied VPN Gateway name | Ask once; reuse |
| `{{user.vpc_id}}` | VPC the gateway attaches to | Ask once; verify with `DescribeVpcs` |
| `{{user.bandwidth}}` | Gateway bandwidth cap (Mbps) | Ask once; numeric |
| `{{user.peer_public_ip}}` | Public IP of the on-prem / peer device | Ask once; validate format |
| `{{user.pre_shared_key}}` | IPSec pre-shared key | Ask once; warn that it will be masked in output |
| `{{output.vpn_gateway_id}}` | From `$.Response.VpnGateway.VpnGatewayId` | Parse per API spec |
| `{{output.vpn_connection_id}}` | From `$.Response.VpnConnection.VpnConnectionId` | Parse per API spec |
| `{{output.customer_gateway_id}}` | From `$.Response.CustomerGateway.CustomerGatewayId` | Parse per API spec |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning:** The IPSec pre-shared key is a **secret**. Never log, print, or echo `{{user.pre_shared_key}}` in console output, error messages, or trace files. Use `test -n "$PSK"` style existence checks. SSL VPN client cert keys follow the same rule.

## API and Response Conventions (Agent-Readable)

- **API spec:** https://cloud.tencent.com/document/api/215/30691
- **Idempotency:** Use `ClientToken` for `CreateVpnGateway` / `CreateVpnConnection` to avoid duplicate creation on retry.
- **Errors:** Map to `Response.Error.Code` and `Response.Error.Message`.
- **Timestamps:** ISO 8601 format.
- **Tunnel state machine:** `PENDING` → `AVAILABLE` → `DOWN` (transient during re-key) → back to `AVAILABLE`. A `DOWN` for > 5 min is an alertable condition.

### JSON Path Reference

| Path | Maps To |
|------|---------|
| `vgw.id` | `$.Response.VpnGateway.VpnGatewayId` / `$.Response.VpnGatewaySet[].VpnGatewayId` |
| `vgw.name` | `$.Response.VpnGatewaySet[].VpnGatewayName` |
| `vgw.state` | `$.Response.VpnGatewaySet[].State` (`PENDING` / `AVAILABLE` / `DELETING` / `DELETED`) |
| `vgw.bandwidth` | `$.Response.VpnGatewaySet[].Bandwidth` |
| `vgw.public_ip` | `$.Response.VpnGatewaySet[].PublicIpAddress` |
| `vconn.id` | `$.Response.VpnConnection.VpnConnectionId` / `$.Response.VpnConnectionSet[].VpnConnectionId` |
| `vconn.state` | `$.Response.VpnConnectionSet[].State` (`PENDING` / `AVAILABLE` / `DOWN` / `DELETING` / `DELETED`) |
| `vconn.negotiate_type` | `$.Response.VpnConnectionSet[].NegotiateType` (`active` / `passive` / `flowTrigger`) |
| `cgw.id` | `$.Response.CustomerGateway.CustomerGatewayId` / `$.Response.CustomerGatewaySet[].CustomerGatewayId` |
| `cgw.ip` | `$.Response.CustomerGatewaySet[].IpAddress` |
| `ssl_server.id` | `$.Response.SslVpnServerId` / `$.Response.SslVpnSeverSet[].SslVpnServerId` |
| `ssl_client.id` | `$.Response.SslVpnClientId` / `$.Response.SslVpnClientSet[].SslVpnClientId` |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| CreateVpnGateway | — | `AVAILABLE` | 10s | 180s |
| CreateVpnConnection | — | `AVAILABLE` | 10s | 180s |
| DeleteVpnGateway | `AVAILABLE` and no connections | absent | 10s | 120s |
| DeleteVpnConnection | `AVAILABLE` / `DOWN` | absent | 5s | 60s |

## Quick Start

### What This Skill Does
Enables you to plan, deploy, and operate VPN Gateway + IPSec VPN Connection / SSL VPN for hybrid cloud and remote-access scenarios.

### Prerequisites
- [ ] `tccli` CLI installed
- [ ] Credentials: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region: `TENCENTCLOUD_REGION`

### Verify Setup
```bash
tccli vpc DescribeVpnGateways --Region "{{env.TENCENTCLOUD_REGION}}"
```

### Your First Command
```bash
# Create a VPN Gateway (IPSec)
tccli vpc CreateVpnGateway \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcId "vpc-xxx" \
  --VpnGatewayName "to-dc-1" \
  --Bandwidth 10 \
  --Zone "ap-guangzhou-3"
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — IPSec vs SSL VPN, IKE / IPSec policy, PSK
- [Common Operations](#execution-flows) — Create gateway, tunnel, customer gateway
- [Troubleshooting](references/troubleshooting.md) — Fix tunnel-down issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreateVpnGateway | Create a new VPN Gateway | Medium | Low |
| DescribeVpnGateways | List / describe VPN Gateways | Low | None |
| ModifyVpnGatewayAttribute | Modify VPN Gateway attributes | Low | Low |
| DeleteVpnGateway | Delete a VPN Gateway | Medium | **High** — tears down hybrid cloud |
| CreateVpnConnection | Create an IPSec tunnel | Medium | Medium — wrong IKE policy = tunnel down |
| DescribeVpnConnections | List / describe VPN Connections | Low | None |
| ModifyVpnConnectionAttribute | Modify VPN Connection attributes | Low | Medium — crypto policy change may disrupt tunnel |
| DeleteVpnConnection | Delete an IPSec tunnel | Low | **High** — cuts hybrid cloud traffic |
| CreateCustomerGateway | Register an on-prem / peer device | Low | Low |
| DescribeCustomerGateways | List / describe Customer Gateways | Low | None |
| DeleteCustomerGateway | Remove a Customer Gateway | Low | Medium — may break other tunnels referencing it |
| CreateVpnGatewaySslServer | Create an SSL VPN server | Medium | Low |
| DescribeVpnGatewaySslServers | List / describe SSL VPN Servers | Low | None |
| DeleteVpnGatewaySslServers | Delete an SSL VPN server | Medium | **High** — disconnects all SSL clients |
| CreateVpnGatewaySslClient | Provision an SSL VPN client cert | Low | Low |
| DescribeVpnGatewaySslClients | List / describe SSL VPN Clients | Low | None |
| DeleteVpnGatewaySslClient | Revoke an SSL VPN client cert | Low | Medium — revokes user access |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.4.0 | 2026-07-09 | **Token Efficiency**: Compressed SKILL.md from 636→~400 lines by consolidating Execution Flows to operation list with key hints; moved detailed steps to execution-flows.md; removed duplicate Prerequisites section. |
| 1.3.0 | 2026-07-09 | **P2 Token Efficiency**: Centralized crypto policy to core-concepts.md; simplified multi-branch pre-flight checks (cross-reference to SKILL.md); updated example-config.yaml with recommended values (SHA-256, GROUP14). |
| 1.2.0 | 2026-07-09 | **P1 Enhancements**: Added ModifyVpnGatewayAttribute/ModifyVpnConnectionAttribute/DeleteVpnGatewaySslServers operations; rewrote aiops-best-practices.md with CLI/SDK commands and monitor integration; rewrote integration.md with CCN/DC hybrid patterns; fixed finops-cost-optimization.md state value (closed→DOWN); refactored multi-branch-topology.md to avoid duplication with execution-flows.md. |
| 1.1.0 | 2026-07-09 | **P0 Security & Correctness Fixes**: Fixed CreateCustomerGateway CLI parameter names; removed PSK plaintext inline (now uses env var); fixed weak crypto example (3DES+MD5→AES-256+SHA-256); expanded api-sdk-usage.md with all 16 VPN APIs; added SDK fallback to execution-flows.md §6-§11; fixed broken reference to non-existent audit-rules.md; changed example-config.yaml exchange_mode from AGGRESSIVE to MAIN. |
| 1.0.0 | 2026-07-03 | Initial VPN skill, dual-path execution. Scope: VPN Gateway + IPSec Connection + Customer Gateway + SSL VPN Server + SSL VPN Client. Hybrid cloud over encrypted tunnel is the primary differentiator from `qcloud-ccn-ops` (multi-region public backbone) and `qcloud-vpc-ops` (same-region same-account peering). |

---

## Execution Flows (Agent-Readable)

> **Detailed CLI/SDK steps for all 15 operations**: See [execution-flows.md](references/execution-flows.md). This section provides operation-level hints and safety gates.

### Operation Index

| # | Operation | Key Hints |
|---|-----------|-----------|
| 1 | Create VPN Gateway | Verify VPC exists, zone in region, bandwidth in [5,10,20,50,100,200,500,1000] Mbps |
| 2 | Describe VPN Gateways | Filter by VPC or gateway ID |
| 3 | Create Customer Gateway | Validate peer public IP format; check name uniqueness |
| 4 | Create VPN Connection | **PSK MUST be read from env var**; verify CIDR non-overlap; warn peer must be configured |
| 5 | Describe VPN Connections | Filter by gateway or connection ID |
| 6 | Delete VPN Connection | **Safety Gate**: Confirm connection ID + CIDR; warn hybrid cloud traffic cut |
| 7 | Delete VPN Gateway | **Safety Gate**: Enumerate ALL connections/servers; confirm none remain; warn all tunnels torn down |
| 8 | Create SSL VPN Server | Verify gateway supports SSL (Type=SSL or CC) |
| 9 | Create SSL VPN Client | **Cert shown only once** — warn user to save immediately |
| 10 | Delete SSL VPN Client | **Safety Gate**: Confirm client name; warn revocation irreversible |
| 11 | Delete Customer Gateway | **Safety Gate**: Confirm no VPN Connection references it |
| 12 | Multi-Branch Hub-Spoke | See [execution-flows.md §12](references/execution-flows.md#12-multi-branch-hub-spoke-topology-deployment) for batch deployment |
| 13 | Modify VPN Gateway Attribute | Gateway must be AVAILABLE; bandwidth change requires polling |
| 14 | Modify VPN Connection Attribute | Only name/health-check modifiable; crypto policy requires recreate |
| 15 | Delete SSL VPN Server | **Safety Gate**: Enumerate ALL SSL clients; warn all lose access |

### Safety Gates (Destructive Operations)

Every **DeleteVpnGateway / DeleteVpnConnection / DeleteCustomerGateway / DeleteVpnGatewaySslServer / DeleteVpnGatewaySslClient** MUST have:

1. Explicit user confirmation with resource ID
2. Dependency check (tunnels on a gateway; connections referencing a customer gateway; SSL clients on a server)
3. Pre-warning about reachability / access impact
4. Post-delete verification (poll until 404 or absent)

### PSK Security (Create VPN Connection)

- **NEVER** inline PSK in CLI command visible in chat
- **NEVER** echo PSK in output, logs, or error messages
- **ALWAYS** read from env var: `export PSK='...' && tccli ... --PreShareKey "$PSK" && unset PSK`
- See [cli-usage.md](references/cli-usage.md) for safe PSK handling pattern

---

## Reference Directory

- [Core Concepts](references/core-concepts.md) — IPSec vs SSL VPN, IKE/IPSec policy, PSK requirements
- [API & SDK Usage](references/api-sdk-usage.md) — All 16 VPN APIs with SDK examples
- [CLI Usage](references/cli-usage.md) — `tccli vpc` patterns and PSK safety
- [Troubleshooting](references/troubleshooting.md) — Tunnel DOWN, PSK mismatch, firewall issues
- [Well-Architected Assessment](references/well-architected-assessment.md) — Four-pillar evaluation
- [Integration](references/integration.md) — VPN + CCN/DC hybrid, route priority
- [Multi-Branch Topology](references/multi-branch-topology.md) — Hub-Spoke, active-standby, bandwidth planning
- [FinOps Cost Optimization](references/finops-cost-optimization.md) — Right-sizing, idle detection
- [SecOps Security Operations](references/secops-security-operations.md) — Security checklist, IKE policy
- [AIOps Best Practices](references/aiops-best-practices.md) — Monitoring, anomaly detection, auto-healing
- [Rubric](references/rubric.md) — GCL scoring dimensions
- [Prompt Templates](references/prompt-templates.md) — Generator/Critic/Orchestrator prompts

## Error Code Reference (VPN-Specific)

> Full error taxonomy with recovery strategies: See [troubleshooting.md](references/troubleshooting.md).

| Code | Meaning | Action |
|------|---------|--------|
| `InvalidParameter.InvalidBandwidth` | Bandwidth not in supported set | Use 5/10/20/50/100/200/500/1000 Mbps |
| `InvalidParameter.PreShareKeyFormat` | PSK length out of range (16–32 chars) | Ask user for strong key |
| `InvalidParameter.CidrConflict` | Local and remote CIDR overlap | Pick non-overlapping ranges |
| `ResourceInUse.VpnGateway` | Gateway still has connections | Delete connections first |
| `InvalidSecretKey` | Credential invalid | HALT; fix credentials |

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. VPN is a hybrid cloud critical path — a single bad `DeleteVpnGateway` or `DeleteVpnConnection` call can disconnect production. GCL `required`, `max_iterations=2`.

| Property | Value |
|---|---|
| GCL applicability | **required** |
| `max_iterations` | **2** |
| Rubric instance | [`references/rubric.md`](references/rubric.md) |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

### VPN-specific safety rules (rubric §4)

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | `DeleteVpnGateway` | Gateway ID + Name + VPC ID echoed; enumerate ALL VPN Connections and SSL Servers; confirm none remain; warn all hybrid cloud traffic torn down |
| 2 | `DeleteVpnConnection` | Connection ID + Name + Local/Remote CIDR echoed; warn hybrid cloud traffic for every workload using this tunnel is cut |
| 3 | `CreateVpnConnection` | PSK is **never** echoed; CIDR non-overlap confirmed; IKE / IPSec policy visible; user warned peer must be configured before tunnel reaches `AVAILABLE` |
| 4 | `DeleteCustomerGateway` | Confirm no VPN Connection still references this customer gateway |
| 5 | `DeleteVpnGatewaySslClient` | Client name + associated user echoed; warn revocation not reversible without re-issuing |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

---

## Output Schema

```json
{
  "Response": {
    "RequestId": "abc123",
    "VpnGateway": {
      "VpnGatewayId": "vpn-xxx",
      "VpnGatewayName": "to-dc-1",
      "State": "AVAILABLE",
      "PublicIpAddress": "1.2.3.4",
      "Bandwidth": 10
    }
  }
}
```
