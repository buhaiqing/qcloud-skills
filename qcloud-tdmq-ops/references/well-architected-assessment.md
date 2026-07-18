# TDMQ Well-Architected Assessment

## 可靠性 (Reliability)

| Check | Recommendation |
|-------|----------------|
| Multi-AZ deployment | Use Pro/cluster instances with cross-AZ replication |
| Message durability | Enable sync flush for critical topics |
| DLQ handling | Monitor DLQ depth; alert on threshold breach |
| Offset management | Document reset procedure; coordinate with consumers |

## 安全性 (Security)

| Check | Recommendation |
|-------|----------------|
| Namespace isolation | Separate namespaces per environment/team |
| Access control | Use namespace roles; least privilege |
| Credential masking | Never log `TENCENTCLOUD_SECRET_KEY` |
| Network | Use VPC private access for sensitive workloads |

## 成本 (Cost)

| Check | Recommendation |
|-------|----------------|
| Cluster spec | Right-size by throughput; avoid over-provisioning |
| Billing model | Compare pay-as-you-go vs monthly subscription |
| Retention | Set topic retention to minimum required |

## 效率 (Efficiency)

| Check | Recommendation |
|-------|----------------|
| Batch send | Use `SendBatchMessages` for high throughput |
| Consumer tuning | Match consumer count to partition/topic concurrency |
| Partition strategy | Even partition distribution avoids hot topics |

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-tdmq-ops` |
| `product` | `tdmq` |
| Finding `id` pattern | `tdmq-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

### Pillar → checklist map

| `pillars` key | Checklist source in this document |
|---------------|-------------------------------------|
| `reliability` | 可靠性 (Reliability) section |
| `security` | 安全性 (Security) section |
| `cost` | 成本 (Cost) section |
| `efficiency` | 效率 (Efficiency) section |

### Example `{{output.product_assessment}}`

```json
{
  "skill_id": "qcloud-tdmq-ops",
  "product": "tdmq",
  "region": "ap-guangzhou",
  "scope": "cluster-wide",
  "assessment_date": "2026-07-10T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 3,
  "pillars": {
    "reliability": {
      "score": 78,
      "status": "assessed",
      "findings": [
        {
          "id": "tdmq-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Single-AZ instance for critical topics",
          "evidence": "Pro/cluster instance without cross-AZ replication enabled",
          "recommendation": "Enable cross-AZ replication for critical topics",
          "effort": "major"
        }
      ]
    },
    "security": {
      "score": 80,
      "status": "assessed",
      "findings": []
    },
    "cost": {
      "score": 72,
      "status": "assessed",
      "findings": [
        {
          "id": "tdmq-cost-001",
          "severity": "Medium",
          "confidence": "MEDIUM",
          "title": "Over-provisioned cluster spec",
          "evidence": "Throughput below 30% of provisioned capacity",
          "recommendation": "Right-size cluster spec by observed throughput",
          "effort": "medium"
        }
      ]
    },
    "efficiency": {
      "score": 85,
      "status": "assessed",
      "findings": []
    }
  },
  "recommendations": [
    {
      "priority": "High",
      "pillar": "reliability",
      "action": "Enable cross-AZ replication for critical topics",
      "effort": "major"
    },
    {
      "priority": "Medium",
      "pillar": "cost",
      "action": "Right-size cluster spec to observed throughput",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tccli tdmq DescribeClusters (SecretKey=<masked>)",
      "tccli tdmq DescribeTopics (SecretKey=<masked>)"
    ],
    "request_ids": [
      "b2c3d4e5-f6a7-8901-bcde-f01234567890"
    ]
  },
  "errors": []
}
```
