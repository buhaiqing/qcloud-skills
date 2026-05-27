---
name: qcloud-vpc-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Tencent
  Cloud VPC (Virtual Private Cloud) — VPC, Subnet, Route Table lifecycle,
  configuration, and diagnostics. User mentions VPC, 私有网络, Private Network,
  or describes network-related scenarios (e.g., subnet creation, CIDR planning,
  routing configuration, connectivity issues) even without naming the product
  directly. Not for billing, CAM, or related products that have their own ops
  skills.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.0.0"
  last_updated: "2026-05-21"
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
- Task involves CRUD or lifecycle operations on **VPC, Subnet, Route Table** (create, describe, modify, delete, list)
- Task keywords: subnet, CIDR, route table, network ACL, NAT gateway, VPN, peering connection, Direct Connect
- User asks to deploy, configure, or troubleshoot network topology **via API, SDK, CLI, or automation**
- User describes connectivity issues, IP address planning, or network isolation requirements

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: `qcloud-billing-ops`
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops`
- Task is about **CVM instances** → delegate to: `qcloud-cvm-ops`
- Task is about **CBS disks** → delegate to: `qcloud-cbs-ops`
- Task is about **CLB load balancers** → delegate to: `qcloud-clb-ops`
- User insists on **console-only** flows with no API → state limitation; do not invent HTTP steps

### Delegation Rules

- If creating CVM instances in VPC, delegate CVM creation to `qcloud-cvm-ops` after VPC/Subnet setup
- If creating CLB in VPC, delegate to `qcloud-clb-ops` after VPC verification
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs

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

### VPC Response Field Table

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| CreateVpc | `$.Response.Vpc.VpcId` | string | VPC ID (e.g., `vpc-xxx`) |
| CreateVpc | `$.Response.Vpc.CidrBlock` | string | CIDR range (e.g., `10.0.0.0/16`) |
| DescribeVpcs | `$.Response.VpcSet[].VpcId` | array | VPC IDs list |
| DescribeVpcs | `$.Response.VpcSet[].VpcName` | array | VPC names |
| CreateSubnet | `$.Response.Subnet.SubnetId` | string | Subnet ID (e.g., `subnet-xxx`) |
| DescribeSubnets | `$.Response.SubnetSet[].SubnetId` | array | Subnet IDs |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| CreateVpc | — | `AVAILABLE` | 5s | 120s |
| CreateSubnet | — | `AVAILABLE` | 5s | 120s |
| DeleteVpc | `AVAILABLE` | absent/404 | 5s | 60s |
| DeleteSubnet | `AVAILABLE` | absent/404 | 5s | 60s |

## Quick Start

### What This Skill Does
This skill enables you to deploy, configure, and manage VPC network environments using `tccli` CLI (primary) or `tencentcloud-sdk-python` SDK (fallback).

### Prerequisites
- [ ] `tccli` CLI installed (or Python 3.8+ runtime for SDK fallback)
- [ ] Credentials configured: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region set: `TENCENTCLOUD_REGION`

### Verify Setup
```bash
tccli vpc DescribeVpcs --Region ap-guangzhou
```

### Your First Command
```bash
# Create a VPC with default CIDR
tccli vpc CreateVpc --Region ap-guangzhou --VpcName "my-vpc" --CidrBlock "10.0.0.0/16"
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — VPC architecture and subnet planning
- [Common Operations](#execution-flows) — Create and manage VPCs/Subnets
- [Troubleshooting](references/troubleshooting.md) — Fix connectivity issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| CreateVpc | Create a new VPC | Medium | Low |
| DescribeVpcs | View VPC details | Low | None |
| DeleteVpc | Remove a VPC | Low | **High** — irreversible |
| CreateSubnet | Create subnet in VPC | Medium | Low |
| DescribeSubnets | View subnet details | Low | None |
| DeleteSubnet | Remove a subnet | Low | **High** — disconnect instances |
| CreateRouteTable | Create route table | Medium | Low |
| DeleteRouteTable | Remove route table | Low | Medium |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial VPC skill with dual-path execution |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI and SDK) → Validate → Recover**.

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

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.vpc import vpc_client, models
import os, json

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = vpc_client.VpcClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.CreateVpcRequest()
req.VpcName = "{{user.vpc_name}}"
req.CidrBlock = "{{user.cidr_block}}"
req.ClientToken = str(int(time.time() * 1000000))

resp = client.CreateVpc(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

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

| Error pattern | Max retries | Backoff | Agent Action |
|--------------|-------------|---------|--------------|
| `InvalidParameter.InvalidCidr` | 0 | — | Fix CIDR format |
| `ResourceQuotaExceeded.Vpc` | 0 | — | HALT; suggest quota increase |
| `InvalidSecretKey` | 0 | — | HALT; fix credentials |
| `ResourceAlreadyExists.Vpc` | 0 | — | Ask reuse or new name |
| `RequestLimitExceeded` | 3 | 2s,4s,8s | Backoff retry |

### Operation: Describe VPCs

#### Execution

```bash
tccli vpc DescribeVpcs \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --VpcIds "[\"{{user.vpc_id}}\"]"
```

#### Execution — Python SDK (Fallback Path)

```python
#!/usr/bin/env python3
from tencentcloud.common import credential
from tencentcloud.vpc import vpc_client, models
import os, json

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = vpc_client.VpcClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.DescribeVpcsRequest()
req.VpcIds = [os.environ.get("VPC_ID", "vpc-xxx")]

resp = client.DescribeVpcs(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

#### Present to User

| Field | Path | Notes |
|-------|------|-------|
| VPC ID | `$.Response.VpcSet[0].VpcId` | Plain text |
| VPC Name | `$.Response.VpcSet[0].VpcName` | Plain text |
| CIDR | `$.Response.VpcSet[0].CidrBlock` | Network range |
| State | `$.Response.VpcSet[0].State` | AVAILABLE/CREATING |
| Subnets | `$.Response.VpcSet[0].SubnetSet` | Subnet list |

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

```python
req = models.DeleteVpcRequest()
req.VpcId = "{{user.vpc_id}}"
resp = client.DeleteVpc(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

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

```python
req = models.CreateSubnetRequest()
req.VpcId = "{{output.vpc_id}}"
req.SubnetName = "{{user.subnet_name}}"
req.CidrBlock = "{{user.subnet_cidr}}"
req.Zone = "{{user.zone}}"
resp = client.CreateSubnet(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

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

```python
req = models.DeleteSubnetRequest()
req.SubnetId = "{{user.subnet_id}}"
resp = client.DeleteSubnet(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

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

```python
req = models.DescribeSubnetsRequest()
req.VpcId = "{{user.vpc_id}}"
req.Offset = 0
req.Limit = 100
resp = client.DescribeSubnets(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

#### Present to User

| Field | Path | Notes |
|-------|------|-------|
| Subnet ID | `$.Response.SubnetSet[0].SubnetId` | Primary identifier |
| Subnet Name | `$.Response.SubnetSet[0].SubnetName` | Display name |
| CIDR | `$.Response.SubnetSet[0].CidrBlock` | Network range |
| State | `$.Response.SubnetSet[0].State` | AVAILABLE/CREATING |
| Zone | `$.Response.SubnetSet[0].Zone` | Availability zone |
| Available IPs | `$.Response.SubnetSet[0].AvailableIpAddressCount` | Remaining IPs |

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

```python
req = models.CreateRouteTableRequest()
req.VpcId = "{{user.vpc_id}}"
req.RouteTableName = "{{user.route_table_name}}"
resp = client.CreateRouteTable(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

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

```python
req = models.DescribeRouteTablesRequest()
req.RouteTableIds = ["{{user.route_table_id}}"]
resp = client.DescribeRouteTables(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

#### Present to User

| Field | Path | Notes |
|-------|------|-------|
| Route Table ID | `$.Response.RouteTableSet[0].RouteTableId` | Primary identifier |
| Route Table Name | `$.Response.RouteTableSet[0].RouteTableName` | Display name |
| Routes | `$.Response.RouteTableSet[0].RouteSet` | Route entries list |
| Association | `$.Response.RouteTableSet[0].AssociationSet` | Associated subnets |

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

```python
req = models.DeleteRouteTableRequest()
req.RouteTableId = "{{user.route_table_id}}"
resp = client.DeleteRouteTable(req)
print(json.dumps(json.loads(resp.to_json_string()), indent=2))
```

#### Validation

Poll DescribeRouteTables until 404 or empty response (max 60s).

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
tccli vpc DescribeVpcs --Region ap-guangzhou
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

## Error Code Reference (VPC-Specific)

| Code | Meaning | Retry? | Agent Action |
|------|---------|--------|--------------|
| `InvalidParameter.InvalidCidr` | CIDR format invalid | No | Fix CIDR notation |
| `InvalidParameter.InvalidVpcName` | VPC name invalid | No | Use valid name |
| `ResourceNotFound.InvalidVpc` | VPC not found | No | Verify VPC ID |
| `ResourceNotFound.InvalidSubnet` | Subnet not found | No | Verify subnet ID |
| `ResourceQuotaExceeded.Vpc` | VPC quota exceeded | No | HALT; raise quota |
| `ResourceQuotaExceeded.Subnet` | Subnet quota exceeded | No | HALT; raise quota |
| `InvalidVpc.StateMismatch` | VPC state invalid | No | Wait for stable state |
| `InvalidSubnet.CidrConflict` | CIDR overlaps | No | Use different CIDR |
| `InvalidSubnet.NotInVpcCidr` | Subnet CIDR outside VPC | No | Use subset CIDR |
| `InvalidSecretKey` | Credential invalid | No | HALT; fix credentials |
| `RequestLimitExceeded` | API rate limit | Yes (3x) | Exponential backoff |
| `InternalError` | Server error | Yes (3x) | Retry with RequestId |

## Safety Gates (Destructive Operations)

Every **Delete VPC/Subnet** MUST have:

1. Explicit user confirmation with resource ID
2. Dependency check (instances, CLB, NAT gateway)
3. Pre-warning about impact
4. Post-delete verification (poll until 404)

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