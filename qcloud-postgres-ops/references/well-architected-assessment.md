# Well-Architected Assessment — TencentDB for PostgreSQL

> **Mode split:** `[assessment-readonly]` — Describe* / GetMonitorData only (Well-Architected worker).
> `[remediation-only]` — Create/Modify/Delete runbooks; **MUST NOT** execute when `{{user.mode}}=well-architected-readonly`.
> Worker JSON: **Worker Output Contract** at end of this file.

## Pillar 1: Reliability (可靠性)

| Aspect | Assessment | Recommendation |
|--------|-----------|----------------|
| Multi-AZ | Supported via multi-node deployment across AZs | Deploy across ≥2 AZs for production |
| Backup | Physical/logical backup, auto/manual | Enable auto-backup with 7-30 day retention |
| Restore | Point-in-time recovery (PITR) available | Test restore quarterly |
| Failover | Automatic failover for multi-node instances | Test failover in staging environment |
| RTO | 1-5 minutes for automatic failover | Document RTO expectations |
| RPO | < 1 second for sync replication | Use synchronous replication for critical data |
| Disaster Recovery | Cross-region backup | Implement cross-region DR for critical systems |

## Pillar 2: Security (安全性)

| Aspect | Assessment | Recommendation |
|--------|-----------|----------------|
| CAM | Full CAM integration | Use least-privilege CAM policies |
| Network Isolation | VPC-only deployment | Deploy in VPC; avoid classic network |
| Encryption | SSL/TLS in-transit; TDE at-rest | Enable SSL for all connections |
| Security Groups | Instance-level SG binding | Restrict inbound to application IPs only |
| Password Policy | 8-32 chars, mixed case + digits + special | Enforce password rotation |
| Audit | Slow query logging available | Enable slow query logging for production |
| Patching | Automatic maintenance window | Set maintenance during off-peak hours |

### Minimum CAM Permissions

```json
{
  "Version": "2.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "postgres:DescribeDBInstances",
        "postgres:CreateBackup",
        "postgres:DescribeDBBackups",
        "postgres:RestoreDBInstance"
      ],
      "Resource": "*"
    }
  ]
}
```

## Pillar 3: Cost (成本)

| Aspect | Assessment | Recommendation |
|--------|-----------|----------------|
| Billing Models | Prepaid and postpaid | Prepaid for stable workloads; postpaid for dev |
| Right-Sizing | Memory: 4GB-128GB; Storage: 10GB-3000GB | Monitor utilization; right-size quarterly |
| Idle Detection | Monitor CPU/memory < 10% for 7 days | Downsize or terminate idle instances |
| Backup Cost | Free up to 50% of storage | Monitor backup storage usage |
| Reserved Instances | Not available for PG | Consider prepaid for discounts |
| Data Transfer | Cross-region transfer billed | Keep instances and clients in same region |
| Idle Instance Cost | 7-day avg CPU < 5% = waste | Downsize or terminate; see SKILL.md idle detection command |
| Prepaid vs Postpaid | Postpaid 2x+ cost for 24/7 workloads | Use prepaid for always-on, postpaid for burst |
| Right-Sizing Frequency | Monthly review via tccli | Automate with cron job (spectrum of peak vs actual) |
| Storage Cost | Billed per GB-month | Deploy auto-scaling at 80% threshold to avoid emergency expansion |

## Pillar 4: Efficiency (效率)

| Aspect | Assessment | Recommendation |
|--------|-----------|----------------|
| Batch Operations | API supports batch via DBInstanceCount | Use Count parameter for batch creation |
| Automation | Full CLI + SDK support | Use Infrastructure as Code (IaC) |
| Parameter Templates | Instance-level parameter groups | Use consistent templates across environments |
| Connection Pooling | Application-level pool recommended | Use PgBouncer or application pooler |
| Read Scaling | Up to 3 read-only replicas | Offload read queries to replicas |
| Monitoring | Cloud Monitor integration | Set up dashboard for key metrics |
| CI/CD Integration | API-based deployment | Integrate with CI/CD pipelines |

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-postgres-ops` |
| `product` | `postgres` |
| Finding `id` pattern | `postgres-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

### Pillar → checklist map

| `pillars` key | Checklist source in this document |
|---------------|-------------------------------------|
| `reliability` | Reliability sections |
| `security` | Security sections |
| `cost` | Cost sections |
| `efficiency` | Efficiency sections |

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
  "skill_id": "qcloud-postgres-ops",
  "product": "postgres",
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
          "id": "postgres-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Single-AZ deployment",
          "evidence": "Instance not deployed in multi-AZ mode",
          "recommendation": "Migrate to multi-AZ for production workloads",
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
      "action": "Migrate to multi-AZ for production workloads",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tccli postgres DescribeDBInstances --Region ap-guangzhou (SecretKey=<masked>)"
    ],
    "request_ids": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    ]
  },
  "errors": []
}
```
