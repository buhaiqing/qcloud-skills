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
  version: "1.0.0"
  last_updated: "2026-07-03"
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
- Task keywords: VPN gateway, VPN tunnel, VPN connection, customer gateway, IKE, pre-shared key, SSL VPN server, SSL VPN client, hybrid cloud, site-to-site, remote access
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
tccli vpc DescribeVpnGateways --Region ap-guangzhou
```

### Your First Command
```bash
# Create a VPN Gateway (IPSec)
tccli vpc CreateVpnGateway \
  --Region "ap-guangzhou" \
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
| DeleteVpnGateway | Delete a VPN Gateway | Medium | **High** — tears down hybrid cloud |
| CreateVpnConnection | Create an IPSec tunnel | Medium | Medium — wrong IKE policy = tunnel down |
| DeleteVpnConnection | Delete an IPSec tunnel | Low | **High** — cuts hybrid cloud traffic |
| CreateCustomerGateway | Register an on-prem / peer device | Low | Low |
| DeleteCustomerGateway | Remove a Customer Gateway | Low | Medium — may break other tunnels referencing it |
| CreateVpnGatewaySslServer | Create an SSL VPN server | Medium | Low |
| CreateVpnGatewaySslClient | Provision an SSL VPN client cert | Low | Low |
| DeleteVpnGatewaySslClient | Revoke an SSL VPN client cert | Low | Medium — revokes user access |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-07-03 | Initial VPN skill, dual-path execution. Scope: VPN Gateway + IPSec Connection + Customer Gateway + SSL VPN Server + SSL VPN Client. Hybrid cloud over encrypted tunnel is the primary differentiator from `qcloud-ccn-ops` (multi-region public backbone) and `qcloud-vpc-ops` (same-region same-account peering). |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI and SDK) → Validate → Recover**.

### Operation: Create VPN Gateway

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI installed | `tccli version` | Exit code 0 | Install tccli |
| Credentials | `test -n "$TENCENTCLOUD_SECRET_ID"` etc. | Non-empty | HALT; user configures env |
| Region valid | `tccli vpc DescribeRegions` | Region exists | Suggest valid region |
| VPC exists, AVAILABLE | `DescribeVpcs` | State `AVAILABLE` | HALT; create or recover VPC first |
| Zone valid | `tccli vpc DescribeZones --Region <region>` | Zone in region | Suggest valid zone |
| Quota | `DescribeVpnGateways` (count per VPC) | ≤ quota | HALT; raise quota |
| Bandwidth supported | Spec allows 5/10/20/50/100/200/500/1000 Mbps | Match | HALT; ask user for valid value |

#### Execution — CLI (`tccli`) (Primary Path)

```bash
tccli vpc CreateVpnGateway \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcId "{{user.vpc_id}}" \
  --VpnGatewayName "{{user.vpn_gateway_name}}" \
  --Bandwidth {{user.bandwidth}} \
  --Zone "{{user.zone}}" \
  --InstanceChargeType "POSTPAID_BY_HOUR" \
  --ClientToken "$(date +%s%N)"
```

#### Execution — Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.vpc import vpc_client, models
import os, json, time

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = vpc_client.VpcClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.CreateVpnGatewayRequest()
req.VpcId = "{{user.vpc_id}}"
req.VpnGatewayName = "{{user.vpn_gateway_name}}"
req.Bandwidth = int("{{user.bandwidth}}")
req.Zone = "{{user.zone}}"
req.InstanceChargeType = "POSTPAID_BY_HOUR"
req.ClientToken = str(int(time.time() * 1000000))

resp = client.CreateVpnGateway(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

1. Capture `{{output.vpn_gateway_id}}` from `$.Response.VpnGateway.VpnGatewayId`.
2. Capture the public IP from `$.Response.VpnGateway.PublicIpAddress` — share with peer (Customer Gateway) operator.
3. Poll `DescribeVpnGateways` until `State = AVAILABLE`:

```bash
for i in $(seq 1 18); do
  STATE=$(tccli vpc DescribeVpnGateways --VpnGatewayIds "[\"{{output.vpn_gateway_id}}\"]" | \
    jq -r '.Response.VpnGatewaySet[0].State')
  [ "$STATE" = "AVAILABLE" ] && break
  sleep 10
done
```

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.InvalidBandwidth` | Use one of the supported bandwidth values (5/10/20/50/100/200/500/1000) |
| `InvalidVpc.NotFound` | Verify `{{user.vpc_id}}` |
| `ResourceQuotaExceeded.VpnGateway` | HALT; raise per-VPC VPN gateway quota |
| `InvalidSecretKey` | HALT; fix credentials |
| `RequestLimitExceeded` | Backoff retry (2s,4s,8s) |

### Operation: Describe VPN Gateways

#### Execution — CLI

```bash
tccli vpc DescribeVpnGateways \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpnGatewayIds "[\"{{output.vpn_gateway_id}}\"]"
```

Filter by VPC:

```bash
tccli vpc DescribeVpnGateways \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=vpc-id,Values={{user.vpc_id}}"
```

#### Execution — Python SDK (Fallback Path)

```python
req = models.DescribeVpnGatewaysRequest()
req.VpnGatewayIds = ["{{output.vpn_gateway_id}}"]
resp = client.DescribeVpnGateways(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

#### Present to User

| Field | Path |
|-------|------|
| VPN Gateway ID | `vgw.id` |
| Name | `vgw.name` |
| State | `vgw.state` |
| Public IP | `vgw.public_ip` |
| Bandwidth (Mbps) | `vgw.bandwidth` |
| VPC | `$.Response.VpnGatewaySet[].VpcId` |

### Operation: Create Customer Gateway (on-prem / peer device registration)

> **Concept:** A Customer Gateway is the **logical** representation of the on-prem / peer device. It only needs the peer's public IP and a name. It does **not** create the actual tunnel.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Peer IP format | Validate `{{user.peer_public_ip}}` is a valid IPv4 | Match | HALT; ask for a valid IP |
| Name uniqueness | `DescribeCustomerGateways` | No duplicate name | Use different name |

#### Execution — CLI

```bash
tccli vpc CreateCustomerGateway \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CustomerGatewayName "{{user.customer_gateway_name}}" \
  --IpAddress "{{user.peer_public_ip}}" \
  --ClientToken "$(date +%s%N)"
```

#### Execution — Python SDK (Fallback Path)

```python
req = models.CreateCustomerGatewayRequest()
req.CustomerGatewayName = "{{user.customer_gateway_name}}"
req.IpAddress = "{{user.peer_public_ip}}"
resp = client.CreateCustomerGateway(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

Poll `DescribeCustomerGateways` until the new entry is visible (max 30s).

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.InvalidIp` | Fix the IP format |
| `ResourceNotFound.CustomerGateway` | Verify customer gateway ID |

### Operation: Create VPN Connection (IPSec Tunnel)

> **Crypto policy reminder:** The IKE / IPSec policy (encryption algo, integrity, DH group, lifetime) must match the peer device. The two most common reasons a tunnel stays in `DOWN` state are: (a) IKE version mismatch, (b) PSK mismatch, (c) CIDR/local-proposal mismatch. The pre-flight below catches (c); (a) and (b) require peer coordination and are surfaced in [troubleshooting](references/troubleshooting.md).

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| VPN Gateway AVAILABLE | `DescribeVpnGateways` | State `AVAILABLE` | HALT; wait for gateway |
| Customer Gateway exists | `DescribeCustomerGateways` | Entry present | HALT; create customer gateway first |
| VPC CIDR not overlapping with peer | Compare `{{user.local_cidr}}` (VPC) vs peer `{{user.peer_cidr}}` (on-prem) | Disjoint | HALT — overlap causes blackhole routes |
| Pre-shared key length | `{{user.pre_shared_key}}` is 16–32 chars | Match | HALT; ask user for a strong key |

#### Execution — CLI

```bash
tccli vpc CreateVpnConnection \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpnGatewayId "{{output.vpn_gateway_id}}" \
  --CustomerGatewayId "{{output.customer_gateway_id}}" \
  --VpnConnectionName "{{user.vpn_connection_name}}" \
  --PreShareKey "{{user.pre_shared_key}}" \
  --VpnProto "IPsec" \
  --IKESettings '{"IkeVersion":"IKEV2","Identity":"ADDRESS","PSK":"{{user.pre_shared_key}}","ExchangeMode":"AGGRESSIVE","LocalAddress":"{{output.vpn_gateway_public_ip}}","RemoteAddress":"{{user.peer_public_ip}}","LocalId":"{{output.vpn_gateway_public_ip}}","RemoteId":"{{user.peer_public_ip}}","IKESaLifetimeSeconds":86400,"IKEEncryptionAlgorithm":"AES-256","IKEIntegrityAlgorithm":"SHA1","DHGroupName":"GROUP2"}' \
  --IPSECSettings '{"IpsecSaLifetimeTraffic":2560,"IpsecSaLifetimeSeconds":3600,'\''"'@type'"\'':'\''"system"'\'\''}' \
  --LocalCidrBlocks '["{{user.local_cidr}}"]' \
  --RemoteCidrBlocks '["{{user.peer_cidr}}"]' \
  --ClientToken "$(date +%s%N)"
```

> **PSK handling note:** The `--PreShareKey` flag and the PSK inside `IKESettings` are the same value. The agent should construct the CLI in a way that the value is **never echoed back** to the user. Use a heredoc, env var, or pass it programmatically; do not paste it into a chat echo.

#### Execution — Python SDK (Fallback Path)

```python
import os, json
from tencentcloud.common import credential
from tencentcloud.vpc import vpc_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = vpc_client.VpcClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.CreateVpnConnectionRequest()
req.VpnGatewayId = "{{output.vpn_gateway_id}}"
req.CustomerGatewayId = "{{output.customer_gateway_id}}"
req.VpnConnectionName = "{{user.vpn_connection_name}}"
req.PreShareKey = "{{user.pre_shared_key}}"
req.VpnProto = "IPsec"
req.LocalCidrBlocks = ["{{user.local_cidr}}"]
req.RemoteCidrBlocks = ["{{user.peer_cidr}}"]
# IKESettings / IPSECSettings: build per API spec
resp = client.CreateVpnConnection(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

1. Capture `{{output.vpn_connection_id}}` from `$.Response.VpnConnection.VpnConnectionId`.
2. **Tell the user the public IP of the VPN Gateway** — the on-prem operator needs it to configure their side.
3. Poll `DescribeVpnConnections` until `State = AVAILABLE`:

```bash
for i in $(seq 1 18); do
  STATE=$(tccli vpc DescribeVpnConnections \
    --VpnConnectionIds "[\"{{output.vpn_connection_id}}\"]" | \
    jq -r '.Response.VpnConnectionSet[0].State')
  [ "$STATE" = "AVAILABLE" ] && break
  sleep 10
done
```

4. **Important:** The tunnel is `AVAILABLE` only when the **peer** is also configured. If state stays `PENDING`, the peer device is not configured or the crypto policy does not match — see [troubleshooting](references/troubleshooting.md).

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.PreShareKeyFormat` | PSK must be 16–32 chars; ask user |
| `InvalidParameter.CidrConflict` | Local and remote CIDR overlap; pick non-overlapping ranges |
| `ResourceNotFound.VpnGateway` / `ResourceNotFound.CustomerGateway` | Verify IDs |
| `ResourceQuotaExceeded.VpnConnection` | HALT; raise per-gateway connection quota |

### Operation: Describe VPN Connections

#### Execution — CLI

```bash
tccli vpc DescribeVpnConnections \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpnConnectionIds "[\"{{output.vpn_connection_id}}\"]"
```

Filter by gateway:

```bash
tccli vpc DescribeVpnConnections \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=vpn-gateway-id,Values={{output.vpn_gateway_id}}"
```

#### Execution — Python SDK (Fallback Path)

```python
req = models.DescribeVpnConnectionsRequest()
req.VpnConnectionIds = ["{{output.vpn_connection_id}}"]
resp = client.DescribeVpnConnections(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

#### Present to User

| Field | Path |
|-------|------|
| VPN Connection ID | `vconn.id` |
| State | `vconn.state` |
| Negotiate type | `vconn.negotiate_type` |
| Local CIDR | `$.Response.VpnConnectionSet[].LocalCidrBlocks` |
| Remote CIDR | `$.Response.VpnConnectionSet[].RemoteCidrBlocks` |
| Health check | `$.Response.VpnConnectionSet[].HealthCheck` |

### Operation: Delete VPN Connection

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation with the connection ID and the on-prem peer device.
- **MUST** warn: this cuts hybrid cloud traffic for every workload that uses this tunnel.
- **MUST** check: no production workload depends solely on this connection (no in-flight fail-over partner).

#### Execution — CLI

```bash
tccli vpc DeleteVpnConnection \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpnConnectionId "{{output.vpn_connection_id}}"
```

#### Post-execution Validation

Poll `DescribeVpnConnections`; expect absent within 60s.

### Operation: Delete VPN Gateway

#### Pre-flight (Safety Gate)

- **MUST** list all VPN Connections on the gateway (`DescribeVpnConnections` filtered by gateway) — none may remain.
- **MUST** obtain explicit user confirmation with the gateway ID and a clear statement that **all** hybrid cloud tunnels on this gateway are torn down.

#### Execution — CLI

```bash
tccli vpc DeleteVpnGateway \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpnGatewayId "{{output.vpn_gateway_id}}"
```

#### Post-execution Validation

Poll `DescribeVpnGateways`; expect absent within 120s.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceInUse.VpnGateway` | Connections still attached; delete them first |
| `ResourceNotFound.VpnGateway` | Already deleted; treat as success |

### Operation: Create SSL VPN Server

> **Scope reminder:** SSL VPN is for **remote user access** (telecommuter, O&M engineer). For site-to-site hybrid cloud, use IPSec VPN above.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| VPN Gateway AVAILABLE | `DescribeVpnGateways` | State `AVAILABLE` | HALT; wait |
| Gateway supports SSL | `Type` field in gateway response | `SSL` or `CC` (combined) | HALT; create an SSL-capable gateway |

#### Execution — CLI

```bash
tccli vpc CreateVpnGatewaySslServer \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpnGatewayId "{{output.vpn_gateway_id}}" \
  --SslVpnServerName "{{user.ssl_vpn_server_name}}" \
  --LocalAddress "{{user.ssl_local_cidr}}" \
  --RemoteAddress "{{user.ssl_client_cidr}}" \
  --SslVpnProtocol "UDP" \
  --Port "{{user.ssl_port}}"
```

#### Post-execution Validation

Poll `DescribeVpnGatewaySslServers` until visible (max 30s).

### Operation: Create SSL VPN Client

> **Cert handling note:** The response contains a one-time downloadable client cert. Surface it to the user **once** with a clear "save this now" warning; the cert cannot be re-fetched in plaintext.

#### Execution — CLI

```bash
tccli vpc CreateVpnGatewaySslClient \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --SslVpnServerId "{{output.ssl_server_id}}" \
  --SslVpnClientName "{{user.ssl_client_name}}"
```

#### Post-execution Validation

Capture the cert payload from the response; warn user it is shown only once.

### Operation: Delete SSL VPN Client

> **Use case:** Revoke a single client's access (e.g., a former employee or a compromised device).

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation with the client name; revocation is not reversible without re-issuing a new client.

#### Execution — CLI

```bash
tccli vpc DeleteVpnGatewaySslClient \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --SslVpnClientId "{{output.ssl_client_id}}"
```

#### Post-execution Validation

Poll `DescribeVpnGatewaySslClients`; expect absent within 30s.

### Operation: Delete Customer Gateway

#### Pre-flight (Safety Gate)

- **MUST** confirm no VPN Connection references this customer gateway.
- **MUST** obtain explicit user confirmation.

#### Execution — CLI

```bash
tccli vpc DeleteCustomerGateway \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CustomerGatewayId "{{output.customer_gateway_id}}"
```

#### Post-execution Validation

Poll `DescribeCustomerGateways`; expect absent within 30s.

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
tccli vpc DescribeVpnGateways --Region ap-guangzhou
```

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [CLI Usage](references/cli-usage.md)
- [Troubleshooting](references/troubleshooting.md)
- [Well-Architected Assessment](references/well-architected-assessment.md)
- [Integration](references/integration.md)
- [FinOps Cost Optimization](references/finops-cost-optimization.md)
- [SecOps Security Operations](references/secops-security-operations.md)
- [AIOps Best Practices](references/aiops-best-practices.md)
- [Rubric](references/rubric.md)
- [Prompt Templates](references/prompt-templates.md)

## Error Code Reference (VPN-Specific)

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter.InvalidBandwidth` | Bandwidth not in supported set | Use 5/10/20/50/100/200/500/1000 Mbps |
| `InvalidParameter.InvalidIp` | Customer Gateway IP is not a valid IPv4 | Fix the IP |
| `InvalidParameter.PreShareKeyFormat` | PSK length out of range (16–32 chars) | Ask user for a strong key |
| `InvalidParameter.CidrConflict` | Local and remote CIDR blocks overlap | Pick non-overlapping ranges |
| `InvalidVpc.NotFound` | VPC ID not found | Verify `{{user.vpc_id}}` |
| `ResourceNotFound.VpnGateway` | VPN Gateway ID not found | Verify `{{output.vpn_gateway_id}}` |
| `ResourceNotFound.CustomerGateway` | Customer Gateway ID not found | Verify `{{output.customer_gateway_id}}` |
| `ResourceQuotaExceeded.VpnGateway` | Per-VPC VPN gateway quota exceeded | HALT; raise quota |
| `ResourceQuotaExceeded.VpnConnection` | Per-gateway connection quota exceeded | HALT; raise quota |
| `ResourceInUse.VpnGateway` | Gateway still has connections | Delete connections first |
| `InvalidStatus.VpnGatewayNotAvailable` | Gateway is in `PENDING` / `DELETING` | Wait for `AVAILABLE` |
| `InvalidSecretKey` | Credential invalid | HALT; fix credentials |
| `RequestLimitExceeded` | API rate limit | Exponential backoff (3x) |
| `InternalError` | Server error | Retry with RequestId (3x) |

## Safety Gates (Destructive Operations)

Every **DeleteVpnGateway / DeleteVpnConnection / DeleteCustomerGateway / DeleteVpnGatewaySslClient** MUST have:

1. Explicit user confirmation with resource ID
2. Dependency check (tunnels on a gateway; connections referencing a customer gateway; SSL clients on a server)
3. Pre-warning about reachability / access impact
4. Post-delete verification (poll until 404 or absent)

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. VPN is a hybrid cloud critical path — a single bad `DeleteVpnGateway` or `DeleteVpnConnection` call can disconnect production. GCL `required`, `max_iterations=2`.

| Property | Value |
|---|---|
| GCL applicability | **required** |
| `max_iterations` | **2** |
| Rubric instance | [`references/rubric.md`](references/rubric.md) |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive: `DeleteVpnGateway`, `DeleteVpnConnection`, `DeleteCustomerGateway`, `DeleteVpnGatewaySslServer`, `DeleteVpnGatewaySslClient` | **yes** | Hybrid cloud critical path; one bad call disconnects production |
| Mutating: `CreateVpnGateway`, `CreateVpnConnection`, `CreateCustomerGateway`, `CreateVpnGatewaySslServer`, `CreateVpnGatewaySslClient` | **yes** | State / crypto-policy risk; PSK / CIDR / bandwidth validation all need scoring |
| Read-only: `DescribeVpnGateways`, `DescribeVpnConnections`, `DescribeCustomerGateways`, `DescribeVpnGatewaySslServers`, `DescribeVpnGatewaySslClients` | optional (max_iter=1, no hard abort) | Polling tails are part of the parent op's trace |

### Decision flow (first match wins)

1. **Safety = 0** OR rule violation ⇒ **ABORT**
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected

### VPN-specific safety rules (rubric §4)

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | `DeleteVpnGateway` | Gateway ID + Name + VPC ID echoed; enumerate ALL VPN Connections on the gateway; confirm none remain; warn that all hybrid cloud traffic on this gateway is torn down |
| 2 | `DeleteVpnConnection` | Connection ID + Name + Local/Remote CIDR echoed; warn that hybrid cloud traffic for every workload using this tunnel is cut |
| 3 | `CreateVpnConnection` | PSK is **never** echoed; CIDR non-overlap confirmed; IKE / IPSec policy visible; user warned that the peer device must be configured before the tunnel reaches `AVAILABLE` |
| 4 | `DeleteCustomerGateway` | Confirm no VPN Connection still references this customer gateway |
| 5 | `DeleteVpnGatewaySslClient` | Client name + associated user echoed; warn that revocation is not reversible without re-issuing |

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
