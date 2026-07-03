---
name: qcloud-ccn-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud CCN (Cloud Connect Network, 云联网) — CCN instances, instance
  attachments (VPC, Direct Connect, VPN), route learning / propagation,
  bandwidth limits, and cross-region / cross-account network orchestration.
  User mentions CCN, 云联网, Cloud Connect Network, multi-region VPC interconnect,
  cross-region peering, cross-account network, 多地域互联, 跨账号组网, hub-and-spoke
  network, or describes scenarios where multiple VPCs (possibly across regions
  and accounts) need a single shared routing backbone. Not for billing, CAM,
  same-region same-account VPC peering (use `qcloud-vpc-ops`), IPSec / SSL VPN
  to on-prem (use `qcloud-vpn-ops`), or related products that have their own
  ops skills.
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
  api_profile: "https://cloud.tencent.com/document/api/215/19200"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli vpc help` and `tccli vpc help CreateCCN` —
    CLI exposes CreateCCN, DescribeCCNs, DeleteCCN, AttachCcnInstances,
    DetachCcnInstances, DescribeCcnAttachedInstances, DescribeCcnRegionBandwidthLimits,
    SetCcnRegionBandwidthLimits, CreateCcnRoute, DeleteCcnRoute, DescribeCcnRoutes,
    DescribeCcnRouteTables, and related operations. All CCN APIs share the
    `vpc` product namespace.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud CCN Operations Skill

## Overview

CCN (Cloud Connect Network, 云联网) is Tencent Cloud's **multi-region, multi-account, multi-product** private network backbone. A CCN instance acts as a hub; you attach VPCs, Direct Connect gateways, and VPN gateways to it from any region and account. CCN learns routes from all attachments and propagates them across the network, replacing the need for a full mesh of VPC peerings.

This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official `tccli` CLI and `tencentcloud-sdk-python` SDK), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

> **UX Compliance:** This skill follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md).

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** `tccli vpc` covers CCN operations. You **MUST** ship `references/cli-usage.md` and document **both** the SDK and `tccli` step for every operation.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with CCN-specific triggers; same-region same-account peering → delegate to `qcloud-vpc-ops`; IPSec / SSL VPN → delegate to `qcloud-vpn-ops` |
| 2 | **Structured I/O** | `{{env.*}}` / `{{user.*}}` / `{{output.*}}` placeholders with CCN API field types |
| 3 | **Explicit Actionable Steps** | Every CCN op: Pre-flight → Execute (CLI + SDK) → Validate → Recover |
| 4 | **Complete Failure Strategies** | Error taxonomy with ≥ 10 CCN-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | CCN instance + attachments + CCN routes + CCN bandwidth limits only; VPC / Subnet → `qcloud-vpc-ops`; VPN Gateway → `qcloud-vpn-ops` |

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-region CCN, multi-account failover, route table backup | `references/well-architected-assessment.md` |
| **安全性 (Security)** | Cross-account attachment via CAM, route filtering, bandwidth limits as DDoS guardrails | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Inter-region bandwidth pricing model, idle CCN detection, right-sizing bandwidth | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Batch attachment, route-table-driven automation | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Tencent Cloud CCN" OR "云联网" OR "Cloud Connect Network" OR "多地域互联" OR "跨账号组网"
- Task keywords: CCN instance, attach VPC to CCN, detach VPC, CCN route, CCN bandwidth limit, multi-region VPC, cross-account network, hub-and-spoke
- User describes a scenario where **multiple VPCs (possibly across regions and accounts) need shared routing** — CCN is the right backbone
- User asks to plan, deploy, or troubleshoot **inter-region** or **multi-account** VPC interconnect

### SHOULD NOT Use This Skill When

- Task is **same-region same-account cross-VPC** connectivity → delegate to `qcloud-vpc-ops` (VPC Peering is cheaper and lower latency than CCN for this case)
- Task is **IPSec / SSL VPN to on-prem** → delegate to `qcloud-vpn-ops`
- Task is **physical dedicated line** (Direct Connect gateway attachment) — only the *CCN attachment* part of DC is in scope; full DC lifecycle lives in a future `qcloud-dc-ops` skill
- Task is purely billing / account management → delegate to `qcloud-billing-ops`
- Task is CAM / permission model only → delegate to `qcloud-cam-ops`

### Delegation Rules

- For each attached VPC, the **VPC's route table** must contain a route pointing at the CCN (next-hop type `CCN`); if the agent is asked to verify a CCN-attached VPC end-to-end, hand off the route-table work to `qcloud-vpc-ops`.
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs into one ambiguous flow.

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use documented default only if skill explicitly allows |
| `{{user.ccn_name}}` | User-supplied CCN instance name | Ask once; reuse |
| `{{user.ccn_description}}` | User-supplied CCN description | Optional; ask if non-empty |
| `{{user.attach_vpc_id}}` | VPC to attach | Ask once; verify with `DescribeVpcs` |
| `{{user.attach_region}}` | Region of the attached VPC | Ask once; **must be a valid Tencent region code** |
| `{{user.attach_uin}}` | UIN of the VPC owner (cross-account) | Omit if same account |
| `{{user.bandwidth_limit_mbps}}` | Inter-region bandwidth cap | Ask once; numeric |
| `{{output.ccn_id}}` | From `$.Response.Ccn.CcnId` | Parse per API spec |
| `{{output.route_table_id}}` | From `$.Response.RouteTableId` | Parse per API spec |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning:** NEVER expose `TENCENTCLOUD_SECRET_KEY` in output. Use `test -n "$TENCENTCLOUD_SECRET_KEY"` for verification only.

## API and Response Conventions (Agent-Readable)

- **API spec:** https://cloud.tencent.com/document/api/215/19200
- **Idempotency:** Use `ClientToken` for `CreateCCN` to avoid duplicate creation on retry.
- **Errors:** Map to `Response.Error.Code` and `Response.Error.Message`.
- **Timestamps:** ISO 8601 format (e.g., `2026-07-03T10:00:00+08:00`).
- **Cross-account attach:** The accepting account must approve the attachment via `AcceptAttachCcnInstances` (initiator side uses `ApplyAttachCcnInstances` for cross-account; check API per region).

### JSON Path Reference

| Path | Maps To |
|------|---------|
| `ccn.id` | `$.Response.Ccn.CcnId` / `$.Response.CcnSet[].CcnId` |
| `ccn.name` | `$.Response.CcnSet[].CcnName` |
| `ccn.state` | `$.Response.CcnSet[].State` (`ISOLATED` / `AVAILABLE`) |
| `ccn.route_table_id` | `$.Response.RouteTableId` / `$.Response.CcnSet[].RouteTableId` |
| `attachment.instance_id` | `$.Response.CcnAttachedInstanceSet[].InstanceId` |
| `attachment.instance_type` | `$.Response.CcnAttachedInstanceSet[].InstanceType` (`VPC` / `DIRECTCONNECT` / `VPNGW`) |
| `attachment.state` | `$.Response.CcnAttachedInstanceSet[].InstanceState` (`PENDING` / `ACTIVE` / `EXPIRED` / `REJECTED` / `DELETED`) |
| `route.destination` | `$.Response.CcnRouteSet[].DestinationCidrBlock` |
| `route.next_hop` | `$.Response.CcnRouteSet[].NextHopInstanceId` |
| `bandwidth.region_a` / `region_b` | `$.Response.CcnBandwidthSet[].SrcRegion` / `DestRegion` |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| CreateCCN | — | `AVAILABLE` | 5s | 60s |
| AttachCcnInstances | — (per instance) | `ACTIVE` | 5s | 120s |
| DetachCcnInstances | `ACTIVE` | absent/removed | 5s | 60s |
| DeleteCCN | `AVAILABLE` and no attachments | absent | 5s | 60s |

## Quick Start

### What This Skill Does
Enables you to plan, deploy, and operate a CCN instance — attach multiple VPCs from any region and account, manage learned routes, and cap inter-region bandwidth.

### Prerequisites
- [ ] `tccli` CLI installed
- [ ] Credentials: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region: `TENCENTCLOUD_REGION` (default region; CCN is regional-aware but the instance itself is global)

### Verify Setup
```bash
tccli vpc DescribeCCNs --Region ap-guangzhou
```

### Your First Command
```bash
# Create a CCN instance
tccli vpc CreateCCN \
  --Region "ap-guangzhou" \
  --CcnName "global-mesh" \
  --CcnDescription "Production multi-region backbone" \
  --ClientToken "$(date +%s%N)"
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — CCN architecture, route learning, bandwidth pricing
- [Common Operations](#execution-flows) — Create, attach, route, bandwidth
- [Troubleshooting](references/troubleshooting.md) — Fix route / attach issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreateCCN | Create a new CCN instance | Low | Low |
| DescribeCCNs | List / describe CCN instances | Low | None |
| DeleteCCN | Delete a CCN instance | Low | **High** — tears down backbone |
| AttachCcnInstances | Attach VPC / DC / VPN GW to CCN | Medium | Medium — affects reachability |
| DetachCcnInstances | Detach an instance from CCN | Medium | **High** — cuts cross-region reachability |
| CreateCcnRoute | Add a static route to CCN route table | Medium | Medium — wrong route = traffic blackhole |
| DeleteCcnRoute | Remove a static route | Low | Medium |
| DescribeCcnRoutes | Inspect CCN route table | Low | None |
| SetCcnRegionBandwidthLimits | Cap inter-region bandwidth | Medium | Medium — too low = throttled traffic |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-07-03 | Initial CCN skill, dual-path execution. Scope: CCN instance + attachments (VPC / DC gateway / VPN GW) + CCN routes + inter-region bandwidth limits. Cross-region VPC interconnect and multi-account orchestration are the primary differentiator from `qcloud-vpc-ops` (which keeps same-region peering). |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI and SDK) → Validate → Recover**.

### Operation: Create CCN

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Credentials | `test -n "$TENCENTCLOUD_SECRET_ID"` etc. | Non-empty | HALT; user configures env |
| CLI installed | `tccli version` | Exit code 0 | Install tccli |
| Name uniqueness | `tccli vpc DescribeCCNs` | No existing CCN with same name | Use different name |

#### Execution — CLI (`tccli`) (Primary Path)

```bash
tccli vpc CreateCCN \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnName "{{user.ccn_name}}" \
  --CcnDescription "{{user.ccn_description}}" \
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

req = models.CreateCCNRequest()
req.CcnName = "{{user.ccn_name}}"
req.CcnDescription = "{{user.ccn_description}}"
req.ClientToken = str(int(time.time() * 1000000))

resp = client.CreateCCN(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

1. Capture `{{output.ccn_id}}` from `$.Response.Ccn.CcnId`.
2. Capture `{{output.route_table_id}}` from `$.Response.Ccn.RouteTableId` (every CCN has a default route table).
3. Poll `DescribeCCNs` until `State = AVAILABLE`:

```bash
for i in $(seq 1 12); do
  STATE=$(tccli vpc DescribeCCNs --CcnIds "[\"{{output.ccn_id}}\"]" | jq -r '.Response.CcnSet[0].State')
  [ "$STATE" = "AVAILABLE" ] && break
  sleep 5
done
```

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.CcnNameTooLong` | Shorten name (60 char limit) |
| `ResourceQuotaExceeded.Ccn` | HALT; raise per-region CCN quota |
| `InvalidSecretKey` | HALT; fix credentials |
| `RequestLimitExceeded` | Backoff retry (2s,4s,8s) |

### Operation: Describe CCNs

#### Execution — CLI

```bash
tccli vpc DescribeCCNs \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnIds "[\"{{output.ccn_id}}\"]"
```

Filter by name:

```bash
tccli vpc DescribeCCNs \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=ccn-name,Values={{user.ccn_name}}"
```

#### Execution — Python SDK (Fallback Path)

```python
req = models.DescribeCCNsRequest()
req.CcnIds = ["{{output.ccn_id}}"]
resp = client.DescribeCCNs(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

#### Present to User

| Field | Path |
|-------|------|
| CCN ID | `ccn.id` |
| Name | `ccn.name` |
| State | `ccn.state` |
| Default Route Table | `ccn.route_table_id` |
| Bandwidth Limits | `$.Response.CcnSet[0].CcnBandwidthSet` |

### Operation: Attach Instances to CCN (VPC / DC GW / VPN GW)

> **Routing reminder:** Attaching a VPC to CCN makes its CIDR **reachable** at the CCN level. Each attached VPC's **own** route table must still have a route with `NextType=CCN` pointing at the CCN instance for traffic to flow into the CCN. Use `qcloud-vpc-ops` for that route-table work.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CCN exists, AVAILABLE | `DescribeCCNs` | State `AVAILABLE` | HALT; create / wait |
| Target instance exists | `DescribeVpcs` / `DescribeDirectConnectGateways` / `DescribeVpnGateways` | State AVAILABLE | HALT; create / wait |
| Region matches instance | `{{user.attach_region}}` matches instance's region | Match | HALT; mismatch causes attach failure |
| Cross-account approval | For cross-account: target account has Uin and accepts via console / API | Approval path clear | HALT; obtain acceptor approval first |
| Quota | CCN has free attachment slot | ≤ quota | HALT; raise quota |

#### Execution — CLI

```bash
tccli vpc AttachCcnInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}" \
  --Instances '[{"InstanceType":"VPC","InstanceId":"{{user.attach_vpc_id}}","InstanceRegion":"{{user.attach_region}}"}]'
# Cross-account: add "InstanceAccountId": {"AccountId": <uin>}
```

#### Execution — Python SDK (Fallback Path)

```python
req = models.AttachCcnInstancesRequest()
req.CcnId = "{{output.ccn_id}}"
req.Instances = [
    models.CcnInstance()
]
req.Instances[0].InstanceType = "VPC"
req.Instances[0].InstanceId = "{{user.attach_vpc_id}}"
req.Instances[0].InstanceRegion = "{{user.attach_region}}"
resp = client.AttachCcnInstances(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

Poll `DescribeCcnAttachedInstances` until **all** attached entries are `InstanceState = ACTIVE` (max 120s):

```bash
for i in $(seq 1 24); do
  STATE=$(tccli vpc DescribeCcnAttachedInstances \
    --Region "{{env.TENCENTCLOUD_REGION}}" \
    --Filters "Name=ccn-id,Values={{output.ccn_id}}" | \
    jq -r '.Response.CcnAttachedInstanceSet[] | select(.InstanceId=="{{user.attach_vpc_id}}") | .InstanceState')
  [ "$STATE" = "ACTIVE" ] && break
  sleep 5
done
```

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.InvalidInstanceType` | `InstanceType` must be one of `VPC` / `DIRECTCONNECT` / `VPNGW` |
| `ResourceNotFound.Ccn` | Verify `{{output.ccn_id}}` |
| `ResourceNotFound.Instance` | Verify `{{user.attach_vpc_id}}` and region |
| `InvalidParameter.CidrConflict` | The VPC's CIDR overlaps with an existing CCN attachment; pick a non-overlapping VPC or migrate one CIDR |
| `ResourceQuotaExceeded.Instance` | HALT; raise per-CCN attachment quota |

### Operation: Describe CCN Attached Instances

#### Execution — CLI

```bash
tccli vpc DescribeCcnAttachedInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=ccn-id,Values={{output.ccn_id}}"
```

#### Execution — Python SDK (Fallback Path)

```python
req = models.DescribeCcnAttachedInstancesRequest()
req.Filters = [{"Name": "ccn-id", "Values": ["{{output.ccn_id}}"]}]
resp = client.DescribeCcnAttachedInstances(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

#### Present to User

| Field | Path |
|-------|------|
| Instance ID | `attachment.instance_id` |
| Instance Type | `attachment.instance_type` |
| Instance State | `attachment.state` |
| Region | `$.Response.CcnAttachedInstanceSet[].InstanceRegion` |
| Account | `$.Response.CcnAttachedInstanceSet[].InstanceAccountId` |

### Operation: Detach Instances from CCN

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation with the CCN ID and the attached instance ID.
- **MUST** warn: detaching **removes the cross-region/cross-account reachability** that this attachment was providing; traffic to/from this instance's CIDR will be dropped.
- **MUST** list any **route table entries** on other attached VPCs that point at the detached instance's CIDR (these become blackholes after detach).

#### Execution — CLI

```bash
tccli vpc DetachCcnInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}" \
  --Instances '[{"InstanceType":"VPC","InstanceId":"{{user.attach_vpc_id}}","InstanceRegion":"{{user.attach_region}}"}]'
```

#### Execution — Python SDK (Fallback Path)

```python
req = models.DetachCcnInstancesRequest()
req.CcnId = "{{output.ccn_id}}"
req.Instances = [models.CcnInstance()]
req.Instances[0].InstanceType = "VPC"
req.Instances[0].InstanceId = "{{user.attach_vpc_id}}"
req.Instances[0].InstanceRegion = "{{user.attach_region}}"
resp = client.DetachCcnInstances(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

Poll `DescribeCcnAttachedInstances`; expect the detached instance ID to be absent within 60s.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.NotAttached` | Already detached; treat as success |
| `InvalidStatus.CcnNotAvailable` | CCN is in `ISOLATED` state; cannot detach — restore CCN first |

### Operation: Set Inter-Region Bandwidth Limits

> **Pricing reminder:** Inter-region bandwidth is billed per Mbps per region pair. Default limit is 1 Gbps; the actual cost is `(used bandwidth) × (unit price per Mbps)`. Always set explicit limits for production CCNs.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Both regions valid | `tccli vpc DescribeRegions` | Both regions supported | HALT; pick a supported pair |
| CCN AVAILABLE | `DescribeCCNs` | `AVAILABLE` | HALT; restore CCN first |
| Value sanity | `{{user.bandwidth_limit_mbps}}` is a positive integer | > 0 | HALT; ask user for valid Mbps |

#### Execution — CLI

```bash
tccli vpc SetCcnRegionBandwidthLimits \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}" \
  --CcnBandwidthLimitSet '[{"SrcRegion":"{{env.TENCENTCLOUD_REGION}}","DestRegion":"{{user.attach_region}}","BandwidthLimit":{{user.bandwidth_limit_mbps}}}]'
```

#### Execution — Python SDK (Fallback Path)

```python
req = models.SetCcnRegionBandwidthLimitsRequest()
req.CcnId = "{{output.ccn_id}}"
req.CcnBandwidthLimitSet = [models.CcnBandwidthInfo()]
req.CcnBandwidthLimitSet[0].SrcRegion = os.environ.get("TENCENTCLOUD_REGION")
req.CcnBandwidthLimitSet[0].DestRegion = "{{user.attach_region}}"
req.CcnBandwidthLimitSet[0].BandwidthLimit = int("{{user.bandwidth_limit_mbps}}")
resp = client.SetCcnRegionBandwidthLimits(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

Poll `DescribeCcnRegionBandwidthLimits` and verify the new limit is reflected (max 30s).

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.BandwidthRange` | Bandwidth limit must be in the supported range (1–5000 Mbps depending on region pair); ask user |
| `ResourceNotFound.Ccn` | Verify CCN ID |

### Operation: Add a Static Route (CCN Route Table)

> **Use case:** Override the auto-learned path for a specific destination CIDR (e.g., force traffic to a specific VPN gateway, or steer between two competing equal-cost routes). Auto-learned routes are the default; static routes are the exception.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Destination not conflicting | Inspect `DescribeCcnRoutes` for the destination CIDR | No conflicting static route with higher priority | HALT; remove the conflicting route first |
| Next hop attached | The next-hop instance must be attached to this CCN and `ACTIVE` | Match | HALT; attach the next hop first |

#### Execution — CLI

```bash
tccli vpc CreateCcnRoute \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}" \
  --RouteTableId "{{output.route_table_id}}" \
  --DestinationCidrBlock "{{user.route_destination}}" \
  --NextHopType "VPC" \
  --NextHopInstanceId "{{user.next_hop_instance_id}}"
```

#### Execution — Python SDK (Fallback Path)

```python
req = models.CreateCcnRouteRequest()
req.CcnId = "{{output.ccn_id}}"
req.RouteTableId = "{{output.route_table_id}}"
req.DestinationCidrBlock = "{{user.route_destination}}"
req.NextHopType = "VPC"
req.NextHopInstanceId = "{{user.next_hop_instance_id}}"
resp = client.CreateCcnRoute(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

Poll `DescribeCcnRoutes`; expect the new entry within 30s.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.CidrInvalid` | Fix destination CIDR format |
| `ResourceNotFound.NextHop` | Verify the next-hop instance ID and that it is attached |
| `InvalidParameter.RouteConflict` | A conflicting static route already exists; remove it first |

### Operation: Describe CCN Routes

#### Execution — CLI

```bash
tccli vpc DescribeCcnRoutes \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}" \
  --Filters "Name=route-type,Values=Static"
```

#### Execution — Python SDK (Fallback Path)

```python
req = models.DescribeCcnRoutesRequest()
req.CcnId = "{{output.ccn_id}}"
req.Filters = [{"Name": "route-type", "Values": ["Static"]}]
resp = client.DescribeCcnRoutes(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

#### Present to User

| Field | Path |
|-------|------|
| Destination CIDR | `route.destination` |
| Next hop instance | `route.next_hop` |
| Next hop type | `$.Response.CcnRouteSet[].NextHopType` |
| Route type | `$.Response.CcnRouteSet[].RouteType` (`Static` / `BGP` / `StaticBGW`) |
| Enabled | `$.Response.CcnRouteSet[].Enabled` |

### Operation: Delete a Static CCN Route

#### Pre-flight (Safety Gate)

- **MUST** confirm destination CIDR and next hop with the user.
- **MUST** warn: deleting a static route can revert that destination to auto-learned paths; cross-check impact on traffic.

#### Execution — CLI

```bash
tccli vpc DeleteCcnRoute \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}" \
  --RouteTableId "{{output.route_table_id}}" \
  --DestinationCidrBlock "{{user.route_destination}}" \
  --NextHopInstanceId "{{user.next_hop_instance_id}}"
```

#### Post-execution Validation

Poll `DescribeCcnRoutes`; expect entry to be absent within 30s.

### Operation: Delete CCN

#### Pre-flight (Safety Gate)

- **MUST** list all current attachments (`DescribeCcnAttachedInstances`) and **all** VPC route-table entries that point at this CCN — none may remain or the API will reject the delete.
- **MUST** obtain explicit user confirmation with the CCN ID and a clear statement that the entire backbone will be torn down.

#### Execution — CLI

```bash
tccli vpc DeleteCCN \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --CcnId "{{output.ccn_id}}"
```

#### Execution — Python SDK (Fallback Path)

```python
req = models.DeleteCCNRequest()
req.CcnId = "{{output.ccn_id}}"
resp = client.DeleteCCN(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Post-execution Validation

Poll `DescribeCCNs` for the ID; expect absent within 60s.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceInUse.Ccn` | Attachments or route-table entries still reference this CCN; detach / clean routes first |
| `InvalidStatus.CcnIsolated` | CCN is already isolated due to overdue bill; settle then retry |

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
tccli vpc DescribeCCNs --Region ap-guangzhou
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

## Error Code Reference (CCN-Specific)

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter.CcnNameTooLong` | CCN name exceeds 60 chars | Shorten name |
| `InvalidParameter.InvalidInstanceType` | `InstanceType` not in `VPC` / `DIRECTCONNECT` / `VPNGW` | Use a valid value |
| `InvalidParameter.InvalidRegion` | Region code not recognized | Use `DescribeRegions` to pick a valid region |
| `InvalidParameter.CidrConflict` | Attached VPC CIDR conflicts with another attachment | Pick a non-overlapping VPC or migrate one CIDR |
| `InvalidParameter.CidrInvalid` | Route destination CIDR is malformed | Fix CIDR |
| `InvalidParameter.RouteConflict` | A static route with the same destination exists | Remove the conflicting route first |
| `InvalidParameter.BandwidthRange` | Bandwidth limit out of supported range | Use 1–5000 Mbps per region pair (verify per docs) |
| `ResourceNotFound.Ccn` | CCN ID not found | Verify `{{output.ccn_id}}` |
| `ResourceNotFound.Instance` | Target instance not found | Verify instance ID and region |
| `ResourceNotFound.NextHop` | Next-hop instance not found in CCN | Attach the next hop first |
| `ResourceQuotaExceeded.Ccn` | Per-region CCN quota exceeded | HALT; raise quota |
| `ResourceQuotaExceeded.Instance` | Per-CCN attachment quota exceeded | HALT; raise quota |
| `ResourceInUse.Ccn` | CCN has remaining attachments or route refs | Detach / clean routes first |
| `InvalidStatus.CcnNotAvailable` | CCN is not `AVAILABLE` (often `ISOLATED`) | Restore CCN (e.g., settle overdue) then retry |
| `InvalidStatus.CcnIsolated` | CCN is isolated (overdue / suspended) | Settle account, then retry |
| `InvalidSecretKey` | Credential invalid | HALT; fix credentials |
| `RequestLimitExceeded` | API rate limit | Exponential backoff (3x) |
| `InternalError` | Server error | Retry with RequestId (3x) |

## Safety Gates (Destructive Operations)

Every **DeleteCCN / DetachCcnInstances / DeleteCcnRoute** MUST have:

1. Explicit user confirmation with resource ID
2. Dependency check (attachments; VPC route-table entries pointing at the CCN or route; static route next hops)
3. Pre-warning about reachability impact
4. Post-delete verification (poll until 404 or absent)

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)**. CCN is a backbone resource — a single bad `DeleteCCN` or `DetachCcnInstances` call can break reachability across many VPCs and regions, causing network partitions that are hard to diagnose. GCL `required`, `max_iterations=2`.

| Property | Value |
|---|---|
| GCL applicability | **required** |
| `max_iterations` | **2** |
| Rubric instance | [`references/rubric.md`](references/rubric.md) — 5 dimensions + 5 CCN-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) — G/C/O skeletons |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive: `DeleteCCN`, `DetachCcnInstances`, `DeleteCcnRoute` | **yes** | Backbone-level; one bad call breaks reachability across many regions/accounts |
| Mutating: `CreateCCN`, `AttachCcnInstances`, `CreateCcnRoute`, `SetCcnRegionBandwidthLimits` | **yes** | Graph/state-change risk; CIDR overlap, bandwidth range, attachment quota all need scoring |
| Read-only: `DescribeCCNs`, `DescribeCcnAttachedInstances`, `DescribeCcnRoutes`, `DescribeCcnRegionBandwidthLimits` | optional (max_iter=1, no hard abort) | Polling tails are part of the parent op's trace |

### Decision flow (first match wins)

1. **Safety = 0** OR rule violation ⇒ **ABORT** (no partial result)
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected

### CCN-specific safety rules (rubric §4)

| # | Operation(s) | Gate (summary) | Rationale |
|---:|---|---|---|
| 1 | `DeleteCCN` | Echo CCN ID + Name; enumerate ALL attached instances (VPC/DC/VPN GW); enumerate ALL static routes; confirm none remain; warn this tears down the entire backbone; require literal "CONFIRM DELETE CCN <name>" | Backbone teardown affects all cross-region/cross-account connectivity |
| 2 | `DetachCcnInstances` | List each affected attachment (ID, type, region, account); warn that cross-region/cross-account reachability is removed; check for dependent static routes; surface remaining attachments; require confirmation with instance ID | Network partition for that VPC's cross-region traffic |
| 3 | `DeleteCcnRoute` | Echo route destination CIDR + next hop; warn that traffic will revert to auto-learned paths; require confirmation | Path reversion may cause latency spikes or asymmetric routing |
| 4 | `SetCcnRegionBandwidthLimits` (lower-than-current) | Echo new value vs current; warn that lowering the cap can throttle production cross-region traffic; require confirmation | Mid-flight throttling affects active connections |
| 5 | `AttachCcnInstances` (cross-account) | Verify acceptor's Uin; confirm user has the acceptor's approval; warn attachment stays `PENDING` until accepted | Bilateral consent required; unapproved attachments stay pending indefinitely |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### GCL integration with skill execution

```
┌─────────────────────────────────────────────────────────┐
│  Generator (tccli vpc / SDK)                            │
│  ├── Pre-flight: Run rubric §4 safety gates            │
│  ├── Execute: Capture masked command + raw response    │
│  ├── Validate: Poll until terminal state               │
│  └── Return: Structured JSON with trace                │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Critic (isolated context)                              │
│  ├── Score 5 dimensions (rubric §3)                    │
│  ├── Mark §4 rules: VIOLATED / SATISFIED / N/A         │
│  └── Return: scores + suggestions + blocking flag      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Orchestrator                                           │
│  ├── Safety=0 OR §4 violation → ABORT                  │
│  ├── iter >= max_iter → MAX_ITER (best-so-far)         │
│  ├── All thresholds met → PASS                         │
│  └── Else → RETRY with Critic suggestions              │
└─────────────────────────────────────────────────────────┘
```

### Trace persistence

Every GCL run MUST persist a masked trace under `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` even on ABORT. The trace includes:

- `preflight`: Safety gate results, credential checks
- `execute`: Masked command, raw response, RequestId
- `validate`: Poll results, BEFORE/AFTER state snapshots
- `recover`: Error handling, retry attempts
- `critic_scores`: Per-dimension scores per iteration
- `final_decision`: PASS / RETRY / ABORT / MAX_ITER

---

## Output Schema

```json
{
  "Response": {
    "RequestId": "abc123",
    "Ccn": {
      "CcnId": "ccn-xxx",
      "CcnName": "global-mesh",
      "State": "AVAILABLE",
      "RouteTableId": "ccnrtb-xxx"
    }
  }
}
```
