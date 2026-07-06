# CLB Well-Architected Assessment

> **Mode split:** `[assessment-readonly]` — Describe* / GetMonitorData only (Well-Architected worker).
> `[remediation-only]` — Create/Modify/Delete runbooks; **MUST NOT** execute when `{{user.mode}}=well-architected-readonly`.
> Worker JSON: **Worker Output Contract** at end of this file.

## Overview

This document maps CLB operations to Tencent Cloud's Well-Architected Framework four pillars.

---

## Pillar 1: Reliability (可靠性)

### 1.1 Multi-AZ Deployment

| Requirement | Status | Documentation |
|-------------|--------|---------------|
| Cross-AZ capability | ✓ | CLB supports multi-AZ backend binding |
| Disaster recovery | ✓ | Cross-region binding with Anycast CLB |
| Backup strategy | ✓ | Listener/target config export for DR |

**Implementation Guide:**

```bash
# Create CLB in primary zone
tccli clb CreateLoadBalancer --LoadBalancerType OPEN --VpcId vpc-xxx

# Bind backends across multiple zones
tccli clb RegisterTargets \
  --Targets "[{\"InstanceId\":\"ins-zone1\",\"Port\":8080},{\"InstanceId\":\"ins-zone2\",\"Port\":8080}]"
```

### 1.2 Backup & Recovery Operations

| Operation | Coverage | Implementation |
|-----------|----------|----------------|
| Configuration export | ✓ | Export listener/target config via Describe APIs |
| Configuration restore | ✓ | Recreate LB + listeners + targets from config |
| Listener backup | ✓ | DescribeListeners → save JSON |
| Target binding backup | ✓ | DescribeTargets → save JSON |

**Backup Flow:**

```bash
# Export CLB configuration
tccli clb DescribeLoadBalancers --LoadBalancerIds "[\"lb-xxx\"]" > lb-config.json
tccli clb DescribeListeners --LoadBalancerId lb-xxx > listener-config.json
tccli clb DescribeTargets --LoadBalancerId lb-xxx > target-config.json

# Restore from backup (new LB)
# 1. CreateLoadBalancer with same config
# 2. CreateListeners from listener-config.json
# 3. RegisterTargets from target-config.json
```

### 1.3 Failure-Oriented Design

| Scenario | Runbook | Recovery Time |
|----------|---------|---------------|
| Backend failure | Health check auto-removes, traffic to healthy | < 30s |
| LB instance failure | Multi-LB redundancy, DNS failover | < 5min |
| Region outage | Cross-region Anycast CLB failover | < 10min |
| SSL cert expiry | Certificate renewal + listener update | < 5min |

### 1.4 Safety Gates

**Mandatory for DeleteLoadBalancer:**

1. ✓ Explicit confirmation: "Delete lb-xxx? All listeners and bindings will be removed."
2. ✓ Dependency check: Warn if listeners exist
3. ✓ Traffic check: Warn if traffic > threshold
4. ✓ Post-delete verification: Poll until 404

---

## Pillar 2: Security (安全性)

### 2.1 CAM Permissions

**Minimum CAM Policy for CLB Operations:**

```json
{
  "version": "2.0",
  "statement": [
    {
      "action": [
        "clb:DescribeLoadBalancers",
        "clb:CreateLoadBalancer",
        "clb:DeleteLoadBalancer",
        "clb:ModifyLoadBalancerAttributes"
      ],
      "effect": "allow",
      "resource": "qcs:clb:*:*:*/*"
    },
    {
      "action": [
        "clb:DescribeListeners",
        "clb:CreateListener",
        "clb:DeleteListener",
        "clb:ModifyListener"
      ],
      "effect": "allow",
      "resource": "qcs:clb:*:*:*/*"
    },
    {
      "action": [
        "clb:DescribeTargets",
        "clb:RegisterTargets",
        "clb:DeregisterTargets",
        "clb:DescribeTargetHealth"
      ],
      "effect": "allow",
      "resource": "qcs:clb:*:*:*/*"
    },
    {
      "action": [
        "vpc:DescribeVpcs",
        "vpc:DescribeSubnets"
      ],
      "effect": "allow",
      "resource": "*"
    }
  ]
}
```

### 2.2 SSL Certificate Security

| Requirement | Status | Guidance |
|-------------|--------|----------|
| Certificate rotation | ✓ | Rotate certs before expiry via ModifyListener |
| TLS version | ✓ | Use TLS 1.2+ for HTTPS listeners |
| Cert validation | ✓ | Verify cert domain matches listener domain |

### 2.3 Network Isolation

| Requirement | Status | Guidance |
|-------------|--------|----------|
| VPC isolation | ✓ | CLB operates within VPC context |
| Security Group | ✓ | CLB uses SG for traffic filtering |
| Private LB | ✓ | Use Internal type for internal services |

**Security Group Configuration:**

```yaml
clb_security_group:
  inbound:
    - port: 80
      cidr: 0.0.0.0/0  # HTTP public
    - port: 443
      cidr: 0.0.0.0/0  # HTTPS public
    - port: 8080
      cidr: 10.0.0.0/8  # Internal only
  outbound:
    - port: all
      cidr: 10.0.0.0/8  # Backend servers only
```

---

## Pillar 3: Cost (成本)

### 3.1 Billing Model Comparison

| Model | Best For |
|-------|----------|
| Shared CLB (公网共享型) | Small traffic, cost-sensitive |
| Dedicated CLB (公网独享型) | High traffic, stable performance |
| Internal CLB (内网型) | Internal microservices |

> Hourly rates vary by region. Check current pricing at `https://buy.cloud.tencent.com/price/clb`.

### 3.2 Idle Resource Detection

| Pattern | Detection | Threshold | Recommendation |
|---------|-----------|-----------|----------------|
| Zero connections | ClientConnum | 0 for 24h | Delete or check config |
| No listeners | DescribeListeners | Empty | Delete unused LB |
| No backends | DescribeTargets | Empty | Review purpose |
| Low traffic | TrafficIn/Out | < 1MB/day | Evaluate need |

**Idle CLB Query:**

```bash
# Find idle load balancers
tccli clb DescribeIdleLoadBalancers --Region ap-guangzhou
```

### 3.3 Right-Sizing Recommendations

| Current State | Recommendation |
|---------------|----------------|
| Shared with high traffic | Upgrade to Dedicated |
| Dedicated with low traffic | Downgrade to Shared |
| Multiple LBs with low traffic | Consolidate to one |

---

## Pillar 4: Efficiency (效率)

### 4.1 Batch Operations

| Operation | Batch Support | Implementation |
|-----------|---------------|----------------|
| BatchRegisterTargets | ✓ | Register multiple backends in one call |
| BatchDeregisterTargets | ✓ | Deregister multiple backends |
| DeleteLoadBalancerListeners | ✓ | Delete multiple listeners |
| BatchModifyTargetWeight | ✓ | Modify weights for multiple targets |

### 4.2 Automation Integration

| Integration | Support | Documentation |
|-------------|---------|---------------|
| CI/CD | ✓ | Listener/target config via API |
| Terraform | ✓ | Tencent Cloud Terraform provider |
| Scheduled ops | ✓ | Target group scheduling |

### 4.3 Scaling Integration

| Feature | Support | Usage |
|---------|---------|-------|
| Auto Scaling | ✓ | Bind AS group to target group |
| Target groups | ✓ | Dynamic backend management |
| Health check auto-recovery | ✓ | Automatic backend removal |

---

## Assessment Checklist

| Pillar | Requirement | CLB Status |
|--------|-------------|------------|
| Reliability | Multi-AZ deployment | ✓ Documented |
| Reliability | Backup operations | ✓ Config export |
| Reliability | Recovery runbook | ✓ Listener restore |
| Reliability | Safety gates | ✓ Delete confirmation |
| Security | CAM permissions | ✓ Policy provided |
| Security | Credential masking | ✓ Enforced |
| Security | Network isolation | ✓ VPC/SG docs |
| Security | SSL/TLS | ✓ Certificate guidance |
| Cost | Billing models | ✓ Comparison table |
| Cost | Idle detection | ✓ Idle LB query |
| Cost | Right-sizing | ✓ Recommendations |
| Efficiency | Batch operations | ✓ Multi-target APIs |
| Efficiency | Automation | ✓ Terraform/CI-CD |
| Efficiency | Scaling | ✓ AS integration |

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-clb-ops` |
| `product` | `clb` |
| Finding `id` pattern | `clb-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

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
  "skill_id": "qcloud-clb-ops",
  "product": "clb",
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
          "id": "clb-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Single-AZ backend targets",
          "evidence": "All registered targets in one zone",
          "recommendation": "Register CVM targets across ≥2 availability zones",
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
      "action": "Register CVM targets across ≥2 availability zones",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tccli clb DescribeLoadBalancers --Region ap-guangzhou (SecretKey=<masked>)"
    ],
    "request_ids": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    ]
  },
  "errors": []
}
```
