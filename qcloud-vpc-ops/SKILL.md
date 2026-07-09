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
  version: "1.3.0"
  last_updated: "2026-07-09"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/215"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    tccli vpc help confirms full CLI support for VPC operations including
    CreateVpc, DescribeVpcs, DeleteVpc, CreateSubnet, DescribeSubnets, and
    route table operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
related_skills:
  - qcloud-ccn-ops
  - qcloud-vpn-ops
  - qcloud-cvm-ops
  - qcloud-clb-ops
  - qcloud-cam-ops
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud VPC Operations Skill

## Overview

VPC (Virtual Private Cloud) on Tencent Cloud provides isolated network environments with customizable IP address ranges, subnets, route tables, and network gateways. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **SDK/API** and `tccli` **CLI** flows), response validation, and failure recovery. **Do not use the web console as the primary agent execution path**.

> **UX Compliance:** This skill follows the [User Experience Specification](../qcloud-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** Official `tccli` supports VPC. You **MUST** ship **`references/cli-usage.md`** and document **both** the SDK step **AND** the `tccli` step for every VPC operation.

## Five Core Standards

> See [shared-boilerplate.md](../qcloud-skill-generator/references/shared-skills-boilerplate.md#five-core-standards).

> Well-Architected pillars (Reliability, Security, Cost, Efficiency): see `references/well-architected-assessment.md`.

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

### JSON Path Reference (TE-4)

| Key | Path |
|-----|------|
| vpc.id | `$.Response.Vpc.VpcId` |
| subnet.id | `$.Response.Subnet.SubnetId` |
| rtable.id | `$.Response.RouteTable.RouteTableId` |
| peering.id | `$.Response.PeeringConnectionId` |

Full paths: `tccli vpc DescribeVpcs --help` or `references/api-sdk-usage.md`.

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

| Version | Date | Summary |
|---------|------|---------|
| 1.3.0 | 2026-07-09 | **Token Efficiency**: Compressed SKILL.md from 730→305 lines by moving Execution Flows to execution-flows.md; added sdk-templates.md; created missing reference files. |
| 1.2.0 | 2026-07-03 | AIOps: Add TE-6 dedup, shared-boilerplate references, dual-path alignment |
| 1.1.0 | 2026-06-15 | Add GCL Quality Gate, rubric, prompt-templates; TE-4 JSON path centralization |
| 1.0.0 | 2026-05-21 | Initial VPC ops skill |

---

## Execution Flows (Agent-Readable)

> **Detailed CLI/SDK steps for all 13 operations**: See [execution-flows.md](references/execution-flows.md). This section provides operation-level hints and safety gates.

### Operation Index

| # | Operation | Key Hints |
|---|-----------|-----------|
| 1 | Create VPC | Verify CIDR format, check quota (≤5 VPCs default), use ClientToken for idempotency |
| 2 | Describe VPCs | Filter by VPC ID or region; paginate with Offset/Limit |
| 3 | Delete VPC | **Safety Gate**: Check no instances/CLB/NAT attached; confirm user |
| 4 | Create Subnet | Verify VPC exists, CIDR within VPC range, zone in region |
| 5 | Describe Subnets | Filter by VPC ID; check AvailableIpCount |
| 6 | Delete Subnet | **Safety Gate**: Check no CVM instances; warn disconnect |
| 7 | Create Route Table | Verify VPC exists; unique name required |
| 8 | Describe Route Tables | Filter by VPC ID or route table ID |
| 9 | Delete Route Table | **Safety Gate**: Check no subnets associated |
| 10 | Create VPC Peering | Verify both VPCs exist, same region, CIDR non-overlapping |
| 11 | Accept VPC Peering | Cross-account only; use acceptor credentials |
| 12 | Describe VPC Peering | Filter by VPC ID or peering ID |
| 13 | Delete VPC Peering | **Safety Gate**: Check route tables; warn blackhole risk |

### Safety Gates (Destructive Operations)

Every **DeleteVpc / DeleteSubnet / DeleteRouteTable / DeleteVpcPeeringConnection** MUST have:

1. Explicit user confirmation with resource ID
2. Dependency check (instances, CLB, NAT, route tables)
3. Pre-warning about reachability / connectivity impact
4. Post-delete verification (poll until 404 or absent)

---

## Reference Directory

> See [shared-boilerplate.md](../qcloud-skill-generator/references/shared-skills-boilerplate.md#reference-directory).
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

## Quality Gate (GCL)

> Boilerplate: see [shared-boilerplate.md](../qcloud-skill-generator/references/shared-skills-boilerplate.md#quality-gate-gcl).

### When the VPC loop runs

| Op class | Loop? | Why |
|---|---|---|
| Destructive: `DeleteVpc`, `DeleteSubnet`, `DeleteRouteTable`, `DeleteRoutes` (`0.0.0.0/0`), `ReleaseAddresses` (EIP), `DeleteSecurityGroup` | **yes** | Graph ops; one bad `DeleteVpc` removes connectivity for sibling CVMs/CLBs/NATs/peers |
| Mutating: `CreateVpc`, `CreateSubnet`, `CreateRouteTable`, `CreateRoutes`, `CreateVpcPeeringConnection` | **yes** | CIDR subset, zone-in-region, route-next-hop, peering state need scoring |
| Read-only: `DescribeVpcs`, `DescribeSubnets`, `DescribeRouteTables`, `DescribeVpcPeeringConnections` | optional (max_iter=1) | Polling tails in parent trace |

### VPC-specific safety rules

> Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Ops | Gate (summary) |
|---:|---|---|
| 1 | `DeleteVpc` | VPC ID + Name + CIDR echo; enumerate ALL subnets, route tables, SGs, peering connections |
| 2 | `DeleteSubnet` | Subnet ID + VPC ID + CIDR echo; check `DescribeSubnetResourceDashboard` for running resources |
| 3 | `ReleaseAddresses` (EIP) | EIP ID + IP echoed; check if bound to CVM/CLB/NAT via `DescribeAddresses` |
| 4 | `DeleteRouteTable` / `DeleteRoutes` (`0.0.0.0/0`) | Route table ID + all route entries listed; warn blackhole risk |
| 5 | `DeleteSecurityGroup` (with rules) | SG ID + Name + rule count; warn all bound instances lose SG protection |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — DeleteSubnet with running CVMs

Safety=0 (rule 2 violated — `DescribeSubnetResourceDashboard` not called). `decision: ABORT`.
Recovery: migrate ENI to another subnet or restore the subnet.

See [`references/rubric.md`](references/rubric.md) §6 for full examples (PASS on `DeleteVpc` + RETRY on `ReleaseAddresses`).

> Decision flow: see [shared-boilerplate.md](../qcloud-skill-generator/references/shared-skills-boilerplate.md#decision-flow-first-match-wins).

## Output Schema

> See [shared-boilerplate.md](../qcloud-skill-generator/references/shared-skills-boilerplate.md#output-schema-api-response).

```json
{ "Response": { "RequestId": "...", "Vpc": { "VpcId": "vpc-xxx", "VpcName": "...", "CidrBlock": "10.0.0.0/16", "State": "AVAILABLE" } } }
```