---
name: qcloud-vpc-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud VPC (Virtual Private Cloud) — VPC, Subnet, Route Table, and VPC Peering
  Connection lifecycle, configuration, and diagnostics. User mentions VPC,
  私有网络, Private Network, VPC peering, 同地域对等连接, peering connection,
  or describes network-related scenarios (e.g., subnet creation, CIDR planning,
  routing configuration, cross-VPC connectivity, connectivity issues) even
  without naming the product directly. Not for billing, CAM, multi-region /
  multi-account network orchestration (use `qcloud-ccn-ops`), VPN / Direct
  Connect hybrid cloud (use `qcloud-vpn-ops`), or related products that have
  their own ops skills.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.2.0"
  last_updated: "2026-07-03"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "2024-01-01 - https://cloud.tencent.com/document/api/215"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    tccli vpc help confirms full CLI support for VPC operations including
    CreateVpc, DescribeVpcs, DeleteVpc, CreateSubnet, DescribeSubnets, and
    route table operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud VPC Operations Skill

## Overview

VPC (Virtual Private Cloud) on Tencent Cloud provides isolated network environments with customizable IP address ranges, subnets, route tables, and network gateways. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **SDK/API** and `tccli` **CLI** flows), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

> **UX Compliance:** This skill follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** Official `tccli` supports VPC. You **MUST** ship **`references/cli-usage.md`** and document **both** the SDK step **AND** the `tccli` step for every VPC operation.

## Five Core Standards (Quality Gates)

Every generated skill MUST satisfy these five standards. Use them as a design checklist:

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with VPC-specific triggers and delegation to CVM/CBS skills |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with VPC API field types |
| 3 | **Explicit Actionable Steps** | Every VPC operation: Pre-flight → Execute → Validate → Recover, numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy with 12+ VPC-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | VPC/Subnet/RouteTable only; delegate CVM, CBS, MySQL, CLB to their skills |

### Well-Architected Framework Integration (卓越架构)

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Multi-AZ subnet deployment, VPC peering DR, route table backup | `references/well-architected-assessment.md` |
| **安全性 (Security)** | Network ACLs, security groups, flow logs, VPC isolation | `references/well-architected-assessment.md` |
| **成本 (Cost)** | NAT gateway cost optimization, VPC peering vs Direct Connect | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Batch subnet creation, automated route table updates | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Tencent Cloud VPC" OR "私有网络" OR "Virtual Private Cloud" OR "Private Network"
- Task involves CRUD or lifecycle operations on **VPC, Subnet, Route Table, VPC Peering Connection** (create, describe, modify, delete, list)
- Task keywords: subnet, CIDR, route table, network ACL, NAT gateway, peering connection, 对等连接, 同地域对等, cross-VPC connectivity, inter-VPC routing
- User asks to deploy, configure, or troubleshoot network topology **via API, SDK, CLI, or automation**
- User describes connectivity issues, IP address planning, network isolation, or **same-region cross-VPC / cross-account VPC peering** requirements

### Out of scope (delegate to a sibling skill)

| Scenario | Delegate to |
|---|---|
| Multi-region VPC interconnect, multi-VPC hub-and-spoke, cross-account network orchestration, hybrid cloud over the public internet backbone | `qcloud-ccn-ops` |
| IPSec VPN / SSL VPN tunnel to on-prem, VPN Gateway lifecycle, Customer Gateway, hybrid cloud over encrypted tunnel | `qcloud-vpn-ops` |
| Dedicated physical line (Direct Connect) | `qcloud-vpn-ops` (if added later) or raise a follow-up skill |

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: `qcloud-billing-ops`
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops`
- Task is about **CVM instances** → delegate to: `qcloud-cvm-ops`
- Task is about **CBS disks** → delegate to: `qcloud-cbs-ops`
- Task is about **CLB load balancers** → delegate to: `qcloud-clb-ops`
- Task is **architecture design review** / four-pillar Well-Architected assessment → delegate to: `qcloud-well-architected-review`

### Delegation Rules

- If creating CVM instances in VPC, delegate CVM creation to `qcloud-cvm-ops` after VPC/Subnet setup
- If creating CLB in VPC, delegate to `qcloud-clb-ops` after VPC verification
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs
- Proactive inspection (read-only) → invoked by `qcloud-proactive-inspection`; see `references/proactive-inspection.md`
- Well-Architected assessment (read-only) → invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Read-only Well-Architected assessment for **VPC/network isolation**; return `{{output.product_assessment}}`.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | typically `security`; may include reliability |
| `{{user.scope}}` | `single-resource` or `account-wide` |

**Allowed:** `Describe*` only — **no** Create/Delete/Modify VPC, SG, NACL, or routes.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: vpc`).

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | From runtime environment | NEVER ask the user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | From runtime environment | Use documented default only if skill explicitly allows |
| `{{user.vpc_name}}` | User-supplied VPC name | Ask once; reuse |
| `{{user.cidr_block}}` | User-supplied CIDR range | Ask once; validate format |
| `{{user.subnet_name}}` | User-supplied Subnet name | Ask once; reuse |
| `{{user.subnet_cidr}}` | User-supplied Subnet CIDR | Ask once; validate subset of VPC CIDR |
| `{{output.vpc_id}}` | From last API response `$.Response.Vpc.VpcId` | Parse per VPC API spec |
| `{{output.subnet_id}}` | From last API response `$.Response.Subnet.SubnetId` | Parse per VPC API spec |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning:** NEVER expose `TENCENTCLOUD_SECRET_KEY` in output. Use `test -n "$TENCENTCLOUD_SECRET_KEY"` for verification only.

## API and Response Conventions (Agent-Readable)

- **API spec:** https://cloud.tencent.com/document/api/215
- **Idempotency**: Use `ClientToken` for CreateVpc to avoid duplicate creation on retry
- **Errors:** Map to `Response.Error.Code` and `Response.Error.Message`
- **Timestamps:** ISO 8601 format (e.g., `2026-05-21T10:00:00+08:00`)

### JSON Path Reference

| Path | Maps To |
|------|---------|
| `vpc.id` | `$.Response.Vpc.VpcId` |
| `vpc.name` | `$.Response.VpcSet[].VpcName` |
| `vpc.cidr` | `$.Response.VpcSet[].CidrBlock` |
| `vpc.state` | `$.Response.VpcSet[].State` |
| `subnet.id` | `$.Response.Subnet.SubnetId` / `$.Response.SubnetSet[].SubnetId` |
| `subnet.name` | `$.Response.SubnetSet[].SubnetName` |
| `subnet.cidr` | `$.Response.SubnetSet[].CidrBlock` |
| `subnet.zone` | `$.Response.SubnetSet[].Zone` |
| `subnet.ips` | `$.Response.SubnetSet[].AvailableIpAddressCount` |
| `rtable.id` | `$.Response.RouteTable.RouteTableId` / `$.Response.RouteTableSet[].RouteTableId` |
| `rtable.name` | `$.Response.RouteTableSet[].RouteTableName` |
| `rtable.routes` | `$.Response.RouteTableSet[].RouteSet` |

### State Transitions

| Operation | Initial → Target | Poll/Max |
|-----------|------------------|----------|
| CreateVpc/Subnet | — → `AVAILABLE` | 5s/120s |
| DeleteVpc/Subnet | `AVAILABLE` → absent | 5s/60s |

## Quick Start

### What This Skill Does
This skill enables you to deploy, configure, and manage VPC network environments using `tccli` CLI (primary) or `tencentcloud-sdk-python` SDK (fallback).

### Prerequisites
- [ ] `tccli` CLI installed (or Python 3.8+ runtime for SDK fallback)
- [ ] Credentials configured: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region set: `TENCENTCLOUD_REGION`

### Verify Setup
```bash
tccli vpc DescribeVpcs --Region "{{env.TENCENTCLOUD_REGION}}"
```

### Your First Command
```bash
# Create a VPC with default CIDR
tccli vpc CreateVpc --Region "{{env.TENCENTCLOUD_REGION}}" --VpcName "my-vpc" --CidrBlock "10.0.0.0/16"
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — VPC architecture and subnet planning
- [Common Operations](#execution-flows) — Create and manage VPCs/Subnets
- [Troubleshooting](references/troubleshooting.md) — Fix connectivity issues

## Capabilities at a Glance

| Operation | Risk Level | Notes |
|-----------|------------|-------|
| CreateVpc | Low | Medium complexity |
| DescribeVpcs | None | Read-only |
| DeleteVpc | **High** | Irreversible |
| CreateSubnet | Low | In VPC |
| DescribeSubnets | None | Read-only |
| DeleteSubnet | **High** | Disconnects instances |
| CreateRouteTable | Low | — |
| DeleteRouteTable | Medium | — |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial VPC skill with dual-path execution |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 VPC-specific safety rules incl. VPC cascade delete, subnet resource dependency, EIP bound-release, route blackhole, SG rule loss), `references/prompt-templates.md`. `max_iter=2` per AGENTS.md §8 |
| 1.2.0 | 2026-07-03 | Scope split per `qcloud-skill-generator` Single Responsibility: this skill keeps **VPC/Subnet/RouteTable + same-region VPC Peering Connection**; multi-region / cross-account orchestration moved to new `qcloud-ccn-ops`; IPSec / SSL VPN / hybrid cloud moved to new `qcloud-vpn-ops`. Added 4 peering execution flows (`CreateVpcPeeringConnection` / `AcceptVpcPeeringConnection` / `DescribeVpcPeeringConnections` / `DeleteVpcPeeringConnection`) and 4 peering-specific error codes. Bumped `last_updated`. |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI and SDK) → Validate → Recover**.

> **SDK Templates:** Init/poll/error boilerplate → [references/sdk-templates.md](references/sdk-templates.md); Code examples → [references/sdk-code-examples.md](references/sdk-code-examples.md)

### Operation: Create VPC

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI installed | `tccli version` | Exit code 0 | Install tccli |
| Credentials | Check env vars | Non-empty | HALT; user configures |
| Region valid | `tccli vpc DescribeRegions` | Region exists | Suggest valid region |
| Quota | Describe quota API | ≤ 5 VPCs default | HALT if quota exceeded |
| CIDR format | Validate regex | Valid CIDR notation | Ask user for valid CIDR |

**CIDR Validation Example**:
```bash
# Validate CIDR format before API call
echo "{{user.cidr_block}}" | grep -qE '^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$' || { echo "Invalid CIDR format"; exit 1; }
```

#### Execution — CLI (`tccli`) (Primary Path)

```bash
tccli vpc CreateVpc \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcName "{{user.vpc_name}}" \
  --CidrBlock "{{user.cidr_block}}" \
  --ClientToken "$(date +%s%N)"
```

#### Execution — Python SDK (Fallback Path)


#### Post-execution Validation

1. Capture `{{output.vpc_id}}` from `$.Response.Vpc.VpcId`
2. Poll DescribeVpcs until status = `AVAILABLE`:

```bash
for i in $(seq 1 24); do
  STATUS=$(tccli vpc DescribeVpcs --VpcIds "[\"{{output.vpc_id}}\"]" | jq -r '.Response.VpcSet[0].State')
  [ "$STATUS" = "AVAILABLE" ] && break
  sleep 5
done
```

#### Failure Recovery

| Error pattern | Recovery |
|--------------|----------|
| `InvalidParameter.InvalidCidr` | Fix CIDR format |
| `ResourceQuotaExceeded.Vpc` | HALT; suggest quota increase |
| `InvalidSecretKey` | HALT; fix credentials |
| `ResourceAlreadyExists.Vpc` | Ask reuse or new name |
| `RequestLimitExceeded` | Backoff retry (2s,4s,8s) |

### Operation: Describe VPCs

#### Execution

```bash
tccli vpc DescribeVpcs \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcIds "[\"{{user.vpc_id}}\"]"
```

#### Execution — Python SDK (Fallback Path)


#### Present to User

| Field | Path |
|-------|------|
| VPC ID | `vpc.id` |
| VPC Name | `vpc.name` |
| CIDR | `vpc.cidr` |
| State | `vpc.state` |
| Subnets | `$.Response.VpcSet[0].SubnetSet` |

### Operation: Delete VPC

#### Pre-flight (Safety Gate)

- **MUST** check: no instances in VPC's subnets
- **MUST** check: no CLB or NAT gateway attached
- **MUST** obtain explicit user confirmation

**Pre-flight Validation Scripts**:
```bash
# Check no CVM instances in VPC subnets
tccli cvm DescribeInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=vpc-id,Values={{user.vpc_id}}"

# Check no CLB attached to VPC
tccli clb DescribeLoadBalancers \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=vpc-id,Values={{user.vpc_id}}"

# Check no NAT gateway attached
tccli vpc DescribeNatGateways \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=vpc-id,Values={{user.vpc_id}}"
```

#### Execution

```bash
tccli vpc DeleteVpc \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcId "{{user.vpc_id}}"
```

#### Execution — Python SDK (Fallback Path)


#### Post-execution Validation

Poll DescribeVpcs until 404 or empty response (max 60s).

### Operation: Create Subnet

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| VPC exists | DescribeVpcs | VPC AVAILABLE | HALT; create VPC first |
| CIDR subset | Validate CIDR | Within VPC CIDR | Ask valid subnet CIDR |
| No overlap | DescribeSubnets | No CIDR conflict | Ask different CIDR |
| Zone available | DescribeZones | Zone in region | Suggest valid zone |

#### Execution — CLI

```bash
tccli vpc CreateSubnet \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcId "{{output.vpc_id}}" \
  --SubnetName "{{user.subnet_name}}" \
  --CidrBlock "{{user.subnet_cidr}}" \
  --Zone "{{user.zone}}"
```

#### Execution — Python SDK (Fallback Path)


#### Validation

Capture `{{output.subnet_id}}`, poll until `AVAILABLE`.

### Operation: Delete Subnet

#### Pre-flight (Safety Gate)

- **MUST** check: no CVM instances in subnet
- **MUST** check: subnet not default subnet
- **MUST** warn: instances will be disconnected

#### Execution — CLI

```bash
tccli vpc DeleteSubnet \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --SubnetId "{{user.subnet_id}}"
```

#### Execution — Python SDK (Fallback Path)


#### Validation

Poll DescribeSubnets until 404 or empty response (max 60s).

### Operation: Describe Subnets

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| VPC exists | DescribeVpcs | VPC AVAILABLE | HALT; create VPC first |

#### Execution — CLI

```bash
tccli vpc DescribeSubnets \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcId "{{user.vpc_id}}"
```

#### Execution — Python SDK (Fallback Path)


#### Present to User

| Field | Path |
|-------|------|
| Subnet ID | `subnet.id` |
| Subnet Name | `subnet.name` |
| CIDR | `subnet.cidr` |
| State | `vpc.state` |
| Zone | `subnet.zone` |
| Available IPs | `subnet.ips` |

### Operation: Create Route Table

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| VPC exists | DescribeVpcs | VPC AVAILABLE | HALT; create VPC first |
| Route table name unique | DescribeRouteTables | No duplicate name | Use different name |

#### Execution — CLI

```bash
tccli vpc CreateRouteTable \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcId "{{user.vpc_id}}" \
  --RouteTableName "{{user.route_table_name}}"
```

#### Execution — Python SDK (Fallback Path)


#### Validation

Capture `{{output.route_table_id}}` from `$.Response.RouteTable.RouteTableId`, poll until `AVAILABLE`.

### Operation: Describe Route Tables

#### Execution — CLI

```bash
tccli vpc DescribeRouteTables \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --RouteTableIds "[\"{{user.route_table_id}}\"]"
```

#### Execution — Python SDK (Fallback Path)


#### Present to User

| Field | Path |
|-------|------|
| Route Table ID | `rtable.id` |
| Route Table Name | `rtable.name` |
| Routes | `rtable.routes` |
| Association | `$.Response.RouteTableSet[0].AssociationSet` |

### Operation: Delete Route Table

#### Pre-flight (Safety Gate)

- **MUST** check: no subnets associated with route table
- **MUST** obtain explicit user confirmation

#### Execution — CLI

```bash
tccli vpc DeleteRouteTable \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --RouteTableId "{{user.route_table_id}}"
```

#### Execution — Python SDK (Fallback Path)


#### Validation

Poll DescribeRouteTables until 404 or empty response (max 60s).

---

### Operation: Create VPC Peering Connection (VpcPeeringConnection)

> **Scope boundary:** This operation covers **same-region, same- or cross-account VPC peering only**. For cross-region, multi-VPC hub-and-spoke, or internet-grade multi-account orchestration, use `qcloud-ccn-ops`. Peering is **non-transitive**: VPC A ↔ VPC B and VPC B ↔ VPC C do **not** enable A ↔ C.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Both VPCs exist | `tccli vpc DescribeVpcs` for initiator + acceptor | Both `AVAILABLE` | HALT; create or recover missing VPC |
| Region match | Both `Region` fields equal | Same region | HALT — different regions require `qcloud-ccn-ops` |
| CIDR disjointness | Compute `{{user.local_cidr}}` ∩ `{{user.peer_cidr}}` | Empty intersection | HALT — overlap is rejected by API; would also break routing even if accepted |
| Quota | `tccli vpc DescribeVpcPeeringConnections` (count by region) | ≤ region quota | HALT; raise quota |
| Cross-account approval | Confirm peer account has the request accepted (or auto-accept flag set) | Approval path clear | For cross-account: HALT until requester has `AccepterUin` and peer account runs `AcceptVpcPeeringConnection` |

#### Execution — CLI

```bash
# Initiator side: create the peering request
tccli vpc CreateVpcPeeringConnection \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcId "{{user.local_vpc_id}}" \
  --PeerVpcId "{{user.peer_vpc_id}}" \
  --PeerRegion "{{env.TENCENTCLOUD_REGION}}" \
  --PeeringConnectionName "{{user.peering_name}}" \
  --PeerAccountId "{{user.peer_account_id}}"  # omit if same account
```

#### Execution — Python SDK (Fallback Path)


#### Post-execution Validation

1. Capture `{{output.peering_connection_id}}` from `$.Response.PeeringConnectionId` (initial state: `PENDING_ACCEPTANCE` for cross-account, `ACTIVE` for same-account).
2. If cross-account, run the **Accept** flow below from the acceptor side; then **both** sides must add a route table entry to make the path routable (peering is a wire, **not** a route).
3. Poll until `Status = ACTIVE`:

```bash
for i in $(seq 1 24); do
  STATUS=$(tccli vpc DescribeVpcPeeringConnections \
    --PeeringConnectionIds "[\"{{output.peering_connection_id}}\"]" | \
    jq -r '.Response.PcSet[0].Status')
  case "$STATUS" in
    ACTIVE)            echo "peering active"; break ;;
    REJECTED|EXPIRED|DELETED) echo "terminal failure: $STATUS"; exit 1 ;;
  esac
  sleep 5
done
```

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.CidrConflict` | The two VPC CIDR blocks overlap; pick a non-overlapping peer VPC or migrate one VPC's CIDR (irreversible) |
| `InvalidParameter.InvalidRegion` | Cross-region peering requested; delegate to `qcloud-ccn-ops` |
| `ResourceQuotaExceeded.PeerConn` | HALT; raise peering quota via console |
| `InvalidVpc.NotFound` | Verify `{{user.peer_vpc_id}}`; same-account only — for cross-account, use peer account's VPC ID |

---

### Operation: Accept VPC Peering Connection (cross-account)

> **Required when:** initiator and acceptor belong to different accounts. The initiator creates a `PENDING_ACCEPTANCE` request; only the acceptor's credentials (running against their `TENCENTCLOUD_SECRET_ID/KEY`) can flip it to `ACTIVE`.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Peer request pending | `DescribeVpcPeeringConnections` filtered by `PeeringConnectionName` | Status `PENDING_ACCEPTANCE` | HALT; nothing to accept |
| Accepting credentials | `TENCENTCLOUD_SECRET_ID` belongs to the **peer (acceptor) account** | Match | HALT; switch credentials to the accepting account |
| Accepting region | Run from a region in the same country/region family as the initiator | Same-region API endpoint | If API returns `InvalidParameter`, retry with the initiator's region |

#### Execution — CLI

```bash
# Run with ACCEPTOR's credentials
tccli vpc AcceptVpcPeeringConnection \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --PeeringConnectionId "{{user.peering_connection_id}}"
```

#### Execution — Python SDK (Fallback Path)


#### Post-execution Validation

Poll `DescribeVpcPeeringConnections` until `Status = ACTIVE` (max 60s). Then remind the user to **add route table entries on both sides** (peering is up but not yet routable).

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `InvalidParameter.PendingAcceptanceNotFound` | Peering already accepted, expired, or deleted; re-query |
| `UnauthorizedOperation` | Running with initiator's credentials, not acceptor's; switch credentials |

---

### Operation: Describe VPC Peering Connections

#### Execution — CLI

```bash
tccli vpc DescribeVpcPeeringConnections \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --PeeringConnectionIds "[\"{{user.peering_connection_id}}\"]"
```

Filter by VPC ID (one-side pagination):

```bash
tccli vpc DescribeVpcPeeringConnections \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --Filters "Name=vpc-id,Values={{user.vpc_id}}"
```

#### Execution — Python SDK (Fallback Path)


#### Present to User

| Field | Path |
|-------|------|
| Peering ID | `$.Response.PcSet[].PeeringConnectionId` |
| Name | `$.Response.PcSet[].PeeringConnectionName` |
| Local VPC | `$.Response.PcSet[].VpcId` |
| Peer VPC | `$.Response.PcSet[].PeerVpcId` |
| Peer account | `$.Response.PcSet[].PeerAccountId` (Uin) |
| Region | `$.Response.PcSet[].PeerRegion` |
| Status | `$.Response.PcSet[].Status` (`PENDING_ACCEPTANCE` / `ACTIVE` / `REJECTED` / `EXPIRED` / `DELETED`) |
| Created | `$.Response.PcSet[].CreatedTime` |

---

### Operation: Delete VPC Peering Connection

> **Important:** Deleting a peering connection does **not** automatically remove the route table entries that point at it. After deletion, those routes become blackholes and must be cleaned up — see [troubleshooting](references/troubleshooting.md).

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation with both VPC IDs and the peering name.
- **MUST** list active route table entries that use the peering as next hop (via `DescribeRouteTables` on both sides); warn user that those routes will become blackholes unless they are removed **before or right after** the delete.
- **MUST** warn: any running CVM-to-CVM cross-VPC traffic over this peering will drop.

#### Execution — CLI

```bash
tccli vpc DeleteVpcPeeringConnection \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --PeeringConnectionId "{{user.peering_connection_id}}"
```

#### Execution — Python SDK (Fallback Path)


#### Post-execution Validation

Poll `DescribeVpcPeeringConnections` for the ID; expect empty / 404 within 60s.

#### Failure Recovery

| Error pattern | Recovery |
|---|---|
| `ResourceNotFound.PeerConn` | Already deleted; treat as success |
| `ResourceInUse.PeerConn` | A route table still references the peering as next hop; delete the routes first, then retry |
| `InvalidStatus.NotActive` | Peering is `PENDING_ACCEPTANCE`; either accept first or have the initiator cancel |

---

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

## Error Code Reference (VPC-Specific)

| Code | Description | Recovery |
|------|-------------|----------|
| `InvalidParameter.InvalidCidr` | CIDR format invalid | Fix CIDR notation |
| `InvalidParameter.InvalidVpcName` | VPC name invalid | Use valid name |
| `ResourceNotFound.InvalidVpc` | VPC not found | Verify VPC ID |
| `ResourceNotFound.InvalidSubnet` | Subnet not found | Verify subnet ID |
| `ResourceQuotaExceeded.Vpc` | VPC quota exceeded | HALT; raise quota |
| `ResourceQuotaExceeded.Subnet` | Subnet quota exceeded | HALT; raise quota |
| `InvalidVpc.StateMismatch` | VPC state invalid | Wait for stable state |
| `InvalidSubnet.CidrConflict` | CIDR overlaps | Use different CIDR |
| `InvalidSubnet.NotInVpcCidr` | Subnet CIDR outside VPC | Use subset CIDR |
| `InvalidSecretKey` | Credential invalid | HALT; fix credentials |
| `RequestLimitExceeded` | API rate limit | Exponential backoff (3x) |
| `InternalError` | Server error | Retry with RequestId (3x) |
| `InvalidParameter.CidrConflict` | Peering: local and peer VPC CIDR blocks overlap | Pick a non-overlapping peer VPC or migrate one VPC's CIDR |
| `InvalidParameter.InvalidRegion` | Peering: cross-region request sent to this skill | Delegate to `qcloud-ccn-ops` for cross-region interconnect |
| `ResourceQuotaExceeded.PeerConn` | Peering: per-region peering quota exceeded | HALT; raise quota via console |
| `ResourceInUse.PeerConn` | Peering: route table still references peering as next hop | Delete the dependent routes first, then retry |

## Safety Gates (Destructive Operations)

Every **Delete VPC/Subnet** MUST have:

1. Explicit user confirmation with resource ID
2. Dependency check (instances, CLB, NAT gateway)
3. Pre-warning about impact
4. Post-delete verification (poll until 404)

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate is a
**runtime** scoring layer that audits each VPC execution against an explicit rubric, in
addition to the build-time **Safety Gates** chapter above and the build-time **2-round
self-review** in [AGENTS.md](../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).
VPC destructive ops are **graph operations** — deleting one node removes connectivity for
many siblings — so a single bad `DeleteVpc` can take down production CLBs in another VPC
via cross-VPC peering.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | [AGENTS.md §8](../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **2** | per-skill override (matches AGENTS.md §8 default for `qcloud-vpc-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 VPC-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive: `DeleteVpc`, `DeleteSubnet`, `DeleteRouteTable`, `DeleteRoutes` (default `0.0.0.0/0`), `ReleaseAddresses` (EIP), `DeleteSecurityGroup` | **yes** | Graph operations; one bad call removes connectivity for many sibling resources (CVM, CLB, NAT, peering) — needs scoring |
| Mutating: `CreateVpc`, `CreateSubnet`, `CreateRouteTable`, `CreateRoutes`, `AssociateNetworkInterface`, `DisassociateNetworkInterface`, `CreateSecurityGroup`, `ModifySecurityGroupPolicies` | **yes** | State / graph-change risk; CIDR subset, zone-in-region, route-next-hop, SG-rule validation all need scoring |
| Read-only: `DescribeVpcs`, `DescribeSubnets`, `DescribeRouteTables`, `DescribeSecurityGroups`, `DescribeAddresses`, `DescribeVpcResourceDashboard`, `DescribeSubnetResourceDashboard` | optional (max_iter=1, no hard abort) | Polling tails are part of the parent op's trace |

### Decision flow (first match wins)

1. **Safety = 0** OR rule violation in `{1, 2, 3, 4, 5}` ⇒ **ABORT** (no partial result)
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

### VPC-specific safety rules (rubric §4)

Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | `DeleteVpc` (any) | VPC ID + Name + CIDR echo; enumerate ALL subnets, route tables, security groups, and dependent re... |
| 2 | `DeleteSubnet` (any, especially with running resources) | Subnet ID + VPC ID + CIDR echo; check if subnet has running resources via `DescribeSubnetResource... |
| 3 | `ReleaseAddresses` (EIP — single or batch) | EIP ID + IP address echoed; check if EIP is bound to a CVM / CLB / NAT Gateway via `DescribeAddre... |
| 4 | `DeleteRouteTable` / `DeleteRoutes` (any, especially default route `0.0.0.0/0`) | Route table ID + VPC ID + all route entries listed; for default route deletion (`0.0.0.0/0`): war... |
| 5 | `DeleteSecurityGroup` (any with rules) | Security group ID + Name + Inbound/Outbound rule count; warn that all instances bound to this SG ... |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — `DeleteSubnet` with running CVMs (cascading connectivity loss)

| Dimension | Score |
|---|---|
| Correctness | 0.5 (subnet was deleted, but the gate should have caught the situation) |
| **Safety** | **0** (rule 2 violated) |
| Idempotency | 1 |
| Traceability | 1 |
| Spec Compliance | 1 |

`decision: ABORT`. The running CVM `ins-prod-db-01` lost its ENI. Recovery suggestion emitted:
"Migrate the CVM's ENI to another subnet in the same VPC (`CreateNetworkInterface` + `AssociateNetworkInterface` + `DisassociateNetworkInterface`), or restore the subnet with the original CIDR if available. Going forward, add a hard pre-flight `DescribeInstances --Filters Name=SubnetId` gate to the skill's pre-flight for every `DeleteSubnet` call."

See [`references/rubric.md`](references/rubric.md) §6 for two more examples (PASS on `DeleteVpc` with confirmation and RETRY on `ReleaseAddresses` with bound CLB).

---

## Output Schema

```json
{
  "Response": {
    "RequestId": "abc123",
    "Vpc": {
      "VpcId": "vpc-xxx",
      "VpcName": "test-vpc",
      "CidrBlock": "10.0.0.0/16",
      "State": "AVAILABLE"
    }
  }
}
```