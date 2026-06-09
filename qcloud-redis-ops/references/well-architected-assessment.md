# TencentDB for Redis Well-Architected Assessment

## Reliability (可靠性)

| Requirement | Status | Documentation |
|-------------|--------|---------------|
| Multi-AZ deployment | ✓ | Master-replica across different zones for fault tolerance |
| Backup operations | ✓ | Daily auto-backup via ModifyAutoBackupConfig; manual backup via DescribeInstanceBackupRecords |
| Recovery runbook | ✓ | Restore from backup via redis-cli import; UnIsolateInstance for soft-deleted instances |
| Safety gates | ✓ | All destructive ops (IsolateInstance, CleanInstance) require explicit confirmation |
| Automatic failover | ✓ | Master-replica auto-failover on master node failure |

### Multi-AZ Recommendation

Deploy Redis master-replica with the master and replica in different availability zones:

```bash
# Check zone availability
tccli redis DescribeProductInfo

# When creating, specify zone that supports master-replica
tccli redis CreateInstance --Memory 2048 --Zone "100001" --Type 2  # master-replica
```

## Security (安全性)

| Requirement | Status | Documentation |
|-------------|--------|---------------|
| Minimum CAM permissions | ✓ | See CAM Policy below |
| Credential masking | ✓ | Enforced — password never echoed, SecretKey masked |
| Network isolation | ✓ | VPC-only deployment recommended; whitelist for additional IP filtering |
| Password authentication | ✓ | Redis password required (configurable via ModifyInstancePassword) |
| TLS encryption | ✓ | TLS available for in-transit encryption (depends on Redis version) |

### CAM Policy Example

```json
{
  "version": "2.0",
  "statement": [
    {
      "action": [
        "redis:Describe*",
        "redis:Get*"
      ],
      "effect": "allow",
      "resource": "*"
    },
    {
      "action": [
        "redis:CreateInstance",
        "redis:UpgradeInstance",
        "redis:ModifyInstance*",
        "redis:AutoRenewInstance",
        "redis:ManualRenewInstance"
      ],
      "effect": "allow",
      "resource": "*"
    },
    {
      "action": [
        "redis:IsolateInstance",
        "redis:CleanInstance",
        "redis:UnIsolateInstance"
      ],
      "effect": "allow",
      "resource": "*"
    }
  ]
}
```

## Cost (成本)

| Requirement | Status | Documentation |
|-------------|--------|---------------|
| Billing models | ✓ | Pay-as-you-go (hourly) vs prepaid (monthly/annual, discounted) |
| Idle detection | ✓ | Detect instances with 0 connections for 7+ days |
| Right-sizing | ✓ | Recommend resizing based on memory utilization patterns |

### Idle Instance Detection

| Pattern | Detection | Recommendation |
|---------|-----------|----------------|
| Zero connections | ConnNum = 0 for 7+ days | Review if instance is still needed |
| Low CPU/Memory | CPU < 5%, Memory < 20% for 14 days | Downsize to smaller instance type |
| Expired and isolated | Status = 4 for > 7 days | CleanInstance to release resources |

### Cost Optimization

| Action | Savings |
|--------|---------|
| Use prepaid for production | 30-50% vs pay-as-you-go |
| Right-size memory | Match actual usage, not planned peak |
| Delete isolated instances | Avoid storage charges for unused instances |
| Adjust backup retention | Keep 7 days instead of 30 if not needed |

## Efficiency (效率)

| Requirement | Status | Documentation |
|-------------|--------|---------------|
| Batch operations | ✓ | UpgradeInstance, ModifyInstanceParams support batch patterns |
| Automation support | ✓ | Full CLI + SDK for CI/CD, Terraform, and scripting |
| API optimization | ✓ | Paginated DescribeInstanceList with appropriate Limit |
| Parameter tuning | ✓ | ModifyInstanceParams for runtime optimization |

### Batch Instance Operations

```bash
# List all instances with key metrics
tccli redis DescribeInstanceList --Region ap-guangzhou --Limit 100 \
  | jq '.Response.InstanceSet[] | {
      id: .InstanceId,
      name: .Name,
      memory_mb: .Size,
      status: .Status,
      ip: .Ip,
      port: .Port,
      vpc: .VpcId
    }'
```

### Automated Prepaid Renewal

```bash
# Auto-renew all prepaid instances
for INST_ID in $(tccli redis DescribeInstanceList --Region ap-guangzhou \
  | jq -r '.Response.InstanceSet[] | select(.AutoRenewFlag == 0) | .InstanceId'); do
  echo "Enabling auto-renew for $INST_ID"
  tccli redis AutoRenewInstance --InstanceId "$INST_ID" --Region ap-guangzhou
done
```

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-redis-ops` |
| `product` | `redis` |
| Finding `id` pattern | `redis-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

### Pillar → checklist map

| `pillars` key | Checklist source in this document |
|---------------|-------------------------------------|
| `reliability` | Reliability section |
| `security` | Security section |
| `cost` | Cost section |
| `efficiency` | Efficiency section |

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
  "skill_id": "qcloud-redis-ops",
  "product": "redis",
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
          "id": "redis-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "No replica for production tier",
          "evidence": "Standalone instance without replica node",
          "recommendation": "Enable master-replica or cluster HA mode",
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
      "action": "Enable master-replica or cluster HA mode",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tccli redis DescribeInstances --Region ap-guangzhou (SecretKey=<masked>)"
    ],
    "request_ids": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    ]
  },
  "errors": []
}
```
