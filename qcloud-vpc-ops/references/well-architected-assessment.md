# VPC Well-Architected Assessment

## Four-Pillar Framework

This document maps VPC operations to Tencent Cloud Well-Architected Framework's four pillars:

| Pillar | Focus Area | VPC Integration |
|--------|------------|-----------------|
| **可靠性 (Reliability)** | Multi-AZ, DR, backup | Subnet distribution, peering DR |
| **安全性 (Security)** | CAM, encryption, isolation | Network ACL, SG, VPC isolation |
| **成本 (Cost)** | Pricing, optimization | NAT gateway, peering vs CCN |
| **效率 (Efficiency)** | Automation, batch | Route table automation, multi-subnet |

---

## Pillar 1: Reliability (可靠性)

### 1.1 Multi-AZ Deployment

**Requirement:** Distribute subnets across availability zones

**VPC Implementation:**

```
VPC (10.0.0.0/16)
├── Web Tier
│   ├── subnet-web-az1 (10.0.1.0/24, ap-guangzhou-1)
│   └── subnet-web-az2 (10.0.2.0/24, ap-guangzhou-2)
├── App Tier
│   ├── subnet-app-az1 (10.0.3.0/24, ap-guangzhou-1)
│   └── subnet-app-az2 (10.0.4.0/24, ap-guangzhou-2)
├── DB Tier
│   ├── subnet-db-az1 (10.0.5.0/24, ap-guangzhou-1)
│   └── subnet-db-az2 (10.0.6.0/24, ap-guangzhou-2)
```

**Assessment Checklist:**

| Check | Status | Evidence |
|-------|--------|----------|
| ≥ 2 subnets in different AZs | ✓ | DescribeSubnets shows multiple zones |
| CLB distributes across AZs | ✓ | CLB backend in multiple subnets |
| DB has cross-AZ replica | ✓ | MySQL Multi-AZ deployment |

### 1.2 Disaster Recovery (DR)

**DR Strategy:**

| Scenario | VPC DR Pattern |
|----------|---------------|
| Region outage | VPC peering to backup region |
| VPC failure | Re-create from backup config |
| Network partition | VPN to on-premise fallback |

**Backup VPC Configuration:**

```bash
# Export VPC config for backup
tccli vpc DescribeVpcs --VpcIds "[\"vpc-prod\"]" > vpc-backup.json
tccli vpc DescribeSubnets --Filters "[{\"Name\":\"vpc-id\",\"Values\":[\"vpc-prod\"]}]" > subnet-backup.json
tccli vpc DescribeRouteTables --Filters "[{\"Name\":\"vpc-id\",\"Values\":[\"vpc-prod\"]}]" > route-backup.json
```

**RTO/RPO Targets:**

| Resource | RTO | RPO | Strategy |
|----------|-----|-----|----------|
| VPC recreation | 5 min | 0 (config) | Automated recreation |
| Subnet recreation | 2 min | 0 | Batch create script |
| Route table restore | 1 min | 0 | Import from backup |

### 1.3 Backup Operations

**VPC Backup Requirements:**

| Item | Backup Method | Frequency |
|------|---------------|-----------|
| VPC config | Export to JSON | Before major changes |
| Subnet config | Export to JSON | Weekly |
| Route table rules | Export to JSON | Weekly |
| Network ACL rules | Export to JSON | Weekly |

### 1.4 Safety Gates (Mandatory)

For all destructive VPC operations:

| Gate | Implementation |
|------|----------------|
| User confirmation | Display VPC ID, CIDR, impact |
| Dependency check | Verify no instances, CLB, NAT |
| Pre-warning | Warn about connectivity loss |
| Post-verification | Poll DescribeVpcs until 404 |

---

## Pillar 2: Security (安全性)

### 2.1 CAM Permissions

**Minimum VPC Permissions:**

```json
{
  "version": "2.0",
  "statement": [
    {
      "action": [
        "vpc:DescribeVpcs",
        "vpc:DescribeSubnets",
        "vpc:DescribeRouteTables",
        "vpc:DescribeNetworkAcls"
      ],
      "effect": "allow",
      "resource": "*"
    },
    {
      "action": [
        "vpc:CreateVpc",
        "vpc:CreateSubnet",
        "vpc:CreateRouteTable",
        "vpc:CreateNetworkAcl"
      ],
      "effect": "allow",
      "resource": "qcs:vpc:*:*:vpc-xxx/*"
    },
    {
      "action": [
        "vpc:DeleteVpc",
        "vpc:DeleteSubnet"
      ],
      "effect": "allow",
      "resource": "qcs:vpc:*:*:vpc-xxx/*",
      "condition": {
        "string_equal": {
          "vpc:resource/tag/env": "dev"
        }
      }
    }
  ]
}
```

### 2.2 Credential Management

**Rules (Mandatory):**

| Rule | Implementation |
|------|----------------|
| Environment variables | Use TENCENTCLOUD_SECRET_ID/KEY |
| Credential masking | NEVER print SecretKey in output |
| Secure storage | Prefer CAM role over static keys |
| Verification | `test -n "$SECRET_KEY"` (no print) |

### 2.3 Network Isolation

**VPC Isolation Patterns:**

| Pattern | Description |
|---------|-------------|
| Environment separation | Separate VPC for dev/test/prod |
| Service isolation | Subnet per service tier |
| DMZ architecture | Public subnet + private subnet |
| Peering isolation | Cross-account peering with ACL |

**Network ACL Configuration:**

```
Web Subnet ACL:
- Inbound: Allow HTTP/HTTPS from 0.0.0.0/0
- Outbound: Allow to App subnet only

App Subnet ACL:
- Inbound: Allow from Web subnet
- Outbound: Allow to DB subnet

DB Subnet ACL:
- Inbound: Allow from App subnet only
- Outbound: Deny all
```

### 2.4 Security Groups

**Recommended SG Rules:**

| SG Name | Inbound | Outbound |
|---------|---------|----------|
| sg-web | HTTP(80), HTTPS(443) | App subnet |
| sg-app | App port from web subnet | DB subnet |
| sg-db | DB port from app subnet | None |

### 2.5 Flow Logs

**Enable Flow Logs for monitoring:**

```bash
tccli vpc CreateFlowLog \
  --VpcId "vpc-xxx" \
  --FlowLogName "vpc-flow-log" \
  --FlowLogEnable "1"
```

---

## Pillar 3: Cost (成本)

### 3.1 VPC Pricing Model

**VPC Cost Components:**

| Component | Cost Model | Free Tier |
|-----------|------------|-----------|
| VPC | Free | Yes |
| Subnet | Free | Yes |
| Route Table | Free | Yes |
| Network ACL | Free | Yes |
| Security Group | Free | Yes |
| NAT Gateway | ¥0.50/hr + bandwidth | No |
| VPN Gateway | ¥80/hr + bandwidth | No |
| VPC Peering | Free (same region) | Yes |
| CCN | Per bandwidth unit | No |

**NAT Gateway Cost Comparison:**

| Scenario | NAT Gateway | EIP per instance |
|----------|-------------|------------------|
| 10 instances outbound | ¥0.50/hr + ¥0.80/GB | ¥10/hr (10 × ¥1) |
| 1 instance outbound | ¥0.50/hr + ¥0.80/GB | ¥1/hr |

**Recommendation:** Use NAT for ≥ 2 instances needing outbound access.

### 3.2 Idle Resource Detection

**VPC-Specific Idle Detection:**

| Pattern | Detection Method | Recommendation |
|---------|-----------------|----------------|
| Empty VPC | DescribeVpcs → check SubnetSet empty | Delete unused VPC |
| Empty subnet | DescribeSubnets → AvailableIpCount == TotalIpCount | Review need |
| Unused route table | DescribeRouteTables → RouteSet empty | Delete unused |
| Stopped NAT gateway | DescribeNatGateways → State != AVAILABLE | Stop if not needed |

**Detection Query:**

```bash
# Find empty VPCs
tccli vpc DescribeVpcs | jq '.Response.VpcSet[] | select(.SubnetSet | length == 0) | .VpcId'

# Find empty subnets
tccli vpc DescribeSubnets | jq '.Response.SubnetSet[] | select(.AvailableIpCount == .TotalIpCount) | .SubnetId'
```

### 3.3 Right-Sizing Recommendations

| Current State | Recommendation | Cost Impact |
|---------------|----------------|-------------|
| NAT gateway with low traffic | Consider EIP per instance | Save ¥0.50/hr |
| VPN gateway idle | Disable or delete | Save ¥80/hr |
| Peering vs CCN cross-region | Use CCN for ≥ 3 regions | More cost-effective |

### 3.4 Cost Comparison Table

| Connectivity Type | Setup Cost | Hourly Cost | Bandwidth Cost |
|--------------------|------------|-------------|----------------|
| NAT Gateway | Free | ¥0.50/hr | ¥0.80/GB |
| VPN Gateway | Free | ¥80/hr | Included |
| Direct Connect | Hardware fee | Depends | Per Mbps |
| VPC Peering (same region) | Free | Free | Free |
| CCN (cross-region) | Free | Free | Per Mbps |

---

## Pillar 4: Efficiency (效率)

### 4.1 Batch Operations

**Supported Batch Operations:**

| Operation | Batch Support | Max Batch |
|-----------|---------------|-----------|
| CreateVpc | No (single) | — |
| DescribeVpcs | Yes (list) | Pagination 100 |
| CreateSubnet | No (single) | — |
| DescribeSubnets | Yes (list) | Pagination 100 |
| DeleteVpc | No (single) | — |
| DeleteSubnet | No (single) | — |

**Multi-Subnet Creation Pattern:**

```bash
# Sequential batch (avoid conflicts)
for i in 1 2 3; do
  tccli vpc CreateSubnet \
    --VpcId "vpc-xxx" \
    --SubnetName "subnet-tier$i" \
    --CidrBlock "10.0.$i.0/24" \
    --Zone "ap-guangzhou-$i"
  sleep 2
done
```

### 4.2 Automation Integration

**CI/CD VPC Provisioning:**

```yaml
# Terraform example
resource "tencentcloud_vpc" "main" {
  name       = "prod-vpc"
  cidr_block = "10.0.0.0/16"
}

resource "tencentcloud_subnet" "web" {
  vpc_id     = tencentcloud_vpc.main.id
  name       = "web-subnet"
  cidr_block = "10.0.1.0/24"
  zone       = "ap-guangzhou-1"
}
```

### 4.3 Resource Scheduling

**Auto-Start/Stop for NAT Gateway:**

```bash
# Disable NAT at night (save cost)
tccli vpc DisableNatGateway --NatId "nat-xxx"

# Enable in morning
tccli vpc EnableNatGateway --NatId "nat-xxx"
```

### 4.4 API Optimization

**Pagination Best Practices:**

| Query Type | Recommended Limit | Notes |
|------------|-------------------|-------|
| DescribeVpcs | 20 | Default sufficient |
| DescribeSubnets | 50 | Multi-subnet VPC |
| DescribeRouteTables | 20 | Default sufficient |

**Caching Strategy:**

```bash
# Cache VPC list (refresh every 5 min)
tccli vpc DescribeVpcs > /tmp/vpc-cache.json

# Use cache for quick lookups
jq -r '.Response.VpcSet[] | select(.VpcName == "prod") | .VpcId' /tmp/vpc-cache.json
```

---

## Assessment Checklist

### Reliability Assessment

| Requirement | Status | Documentation |
|-------------|--------|---------------|
| Multi-AZ subnets | ✓ | See Multi-AZ section |
| Backup config export | ✓ | See DR section |
| Recovery runbook | ✓ | See recreation script |
| Safety gates | ✓ | All delete ops have confirmation |

### Security Assessment

| Requirement | Status | Documentation |
|-------------|--------|---------------|
| Minimum CAM permissions | ✓ | See CAM policy |
| Credential masking | ✓ | Enforced in all paths |
| Network isolation | ✓ | ACL/SG documented |
| Flow logs | ✓ | Monitoring enabled |

### Cost Assessment

| Requirement | Status | Documentation |
|-------------|--------|---------------|
| Pricing documentation | ✓ | See cost table |
| Idle detection | ✓ | See detection queries |
| Right-sizing | ✓ | NAT vs EIP comparison |
| Optimization recommendations | ✓ | Cost pillar section |

### Efficiency Assessment

| Requirement | Status | Documentation |
|-------------|--------|---------------|
| Batch operations | ✓ | Sequential pattern |
| Automation support | ✓ | Terraform example |
| API optimization | ✓ | Pagination guidance |
| Caching strategy | ✓ | Cache recommendation |

---

## CAM Policy Example

```json
{
  "version": "2.0",
  "statement": [
    {
      "action": [
        "vpc:Describe*",
        "vpc:CreateVpc",
        "vpc:CreateSubnet",
        "vpc:CreateRouteTable"
      ],
      "effect": "allow",
      "resource": "qcs:vpc:*:*:*/*"
    },
    {
      "action": [
        "vpc:DeleteVpc",
        "vpc:DeleteSubnet"
      ],
      "effect": "allow",
      "resource": "qcs:vpc:*:*:vpc-dev/*"
    }
  ]
}
```


---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-vpc-ops` |
| `product` | `vpc` |
| Finding `id` pattern | `vpc-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

### Pillar → checklist map

| `pillars` key | Checklist source in this document |
|---------------|-------------------------------------|
| `reliability` | Pillar 1: Reliability |
| `security` | Pillar 2: Security |
| `cost` | Pillar 3: Cost |
| `efficiency` | Pillar 4: Efficiency |

### Populate rules

1. Include only pillar keys requested by orchestrator `{{user.pillars}}` (`all` = four keys).
2. `score = round(passed / applicable × 100)`; use `status=not_assessed` when data missing (omit score or null).
3. Each failed/warn checklist item → one `findings[]` entry with all six finding fields (§2.1 in schema).
4. `recommendations[]`: top 1–5 actions with `priority`, `pillar`, `action`, `effort` (§2.2 in schema).
5. `partial=true` when any pillar is `not_assessed`; top-level `status=PARTIAL`.
6. `trace.commands`: every read API call; mask credentials. `errors[]` on API failure (§3 in schema).
7. Local “Score Calculation” sections are for manual review only — **worker mode must emit this JSON**.

### Example `{{output.product_assessment}}`

```json
{
  "skill_id": "qcloud-vpc-ops",
  "product": "vpc",
  "region": "ap-guangzhou",
  "scope": "account-wide",
  "assessment_date": "2026-06-09T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 3,
  "pillars": {
    "reliability": {
      "score": 75,
      "status": "assessed",
      "findings": [
        {
          "id": "vpc-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Overly permissive security group",
          "evidence": "Ingress 0.0.0.0/0 on admin port",
          "recommendation": "Restrict source CIDRs; use bastion or VPN",
          "effort": "medium"
        }
      ]
    },
    "security": {
      "score": 88,
      "status": "assessed",
      "findings": []
    },
    "cost": {
      "score": 72,
      "status": "assessed",
      "findings": []
    },
    "efficiency": {
      "score": 70,
      "status": "assessed",
      "findings": []
    }
  },
  "recommendations": [
    {
      "priority": "High",
      "pillar": "reliability",
      "action": "Restrict source CIDRs; use bastion or VPN",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tccli vpc DescribeSecurityGroups --Region ap-guangzhou (SecretKey=<masked>)"
    ],
    "request_ids": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    ]
  },
  "errors": []
}
```

## References

- [Tencent Cloud Well-Architected Framework](https://cloud.tencent.com/document/product/xxx)
- [VPC Architecture Best Practices](https://cloud.tencent.com/document/product/215/39107)
- [CAM Policy Documentation](https://cloud.tencent.com/document/product/598)