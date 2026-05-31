# Well-Architected Assessment — TencentDB for PostgreSQL

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
