# Well-Architected Assessment — TencentDB for MongoDB

## Reliability Pillar (可靠性)

### Multi-AZ Deployment

- Deploy replica set nodes across 3 availability zones for zone-level fault tolerance
- Query zone availability: `tccli mongodb DescribeSpecInfo`
- Configure via Zone parameter on CreateDBInstance (single zone) or ModifyInstanceAz (after creation)

### Backup Strategies

| Strategy | Method | RPO | RTO | Cost |
|----------|--------|-----|-----|------|
| Auto backup (daily) | SetBackupRules | 24h | Hours | Low |
| Manual backup (pre-change) | CreateBackupDBInstance | On-demand | Hours | Low |
| Key-based flashback | FlashBackDBInstance | Point-in-time | Minutes | Medium |
| Backup to COS | CreateBackupDownloadTask | N/A | Hours | Storage cost |

### Restore Procedures

1. List available backups: `tccli mongodb DescribeDBBackups`
2. Restore from backup: `tccli mongodb RestoreDBInstance`
3. Verify data integrity after restore
4. Update application connection strings if needed

### DR (Disaster Recovery)

- Standby instances (cross-region) via DescribeDBInstances.StandbyInstances
- Read-only instances for read traffic offloading via DescribeDBInstances.ReadonlyInstances
- Regular backup download to offsite storage via CreateBackupDownloadTask

### RTO/RPO Guidelines

| Scenario | Target RTO | Target RPO | Method |
|----------|-----------|------------|--------|
| Instance failure (same AZ) | < 30s | 0 | Automatic failover (replica set) |
| AZ failure | < 5min | < 5min | Cross-AZ replica set |
| Regional failure | < 4h | < 1h | Backup restore in new region |
| Accidental data loss | < 2h | < 1h | Key-based flashback |

### Failure Scenarios

- **Primary failure:** Automatic election, ~10-30s downtime
- **Secondary failure:** No impact on writes, reads served by other secondaries
- **Network partition:** Primary steps down if majority unreachable; writes pause
- **Disk full:** Instance enters read-only mode; scale volume immediately

## Security Pillar (安全性)

### Minimum CAM Permissions

```json
{
  "version": "2.0",
  "statement": [
    {
      "effect": "allow",
      "action": [
        "mongodb:Describe*",
        "mongodb:Create*",
        "mongodb:Modify*",
        "mongodb:Isolate*",
        "mongodb:Offline*",
        "mongodb:Renew*",
        "mongodb:Reset*",
        "mongodb:Set*",
        "mongodb:Inquire*"
      ],
      "resource": "qcs::mongodb:ap-guangzhou:uin/12345:instance/cmgo-*"
    }
  ]
}
```

### SSL/TLS Configuration

- Check status: `tccli mongodb DescribeInstanceSSL`
- Enable: `tccli mongodb InstanceEnableSSL --SslSwitch on`
- Connection strings change after enabling: use `DescribeDBInstanceURL` for new URIs

### Transparent Data Encryption (TDE)

- Only supported on certain instance types (HIO10G)
- Check status: `tccli mongodb DescribeTransparentDataEncryptionStatus`
- Enable: `tccli mongodb EnableTransparentDataEncryption`
- Requires KMS key management

### Audit Logging

- Enable: `tccli mongodb OpenAuditService --LogExpireDay 30`
- Query: `tccli mongodb DescribeAuditLogs`
- Export: `tccli mongodb CreateAuditLogFile`

### Network Security

| Feature | Method | Recommendation |
|---------|--------|---------------|
| VPC isolation | NetType=1 | Always use VPC for production |
| Security groups | ModifyDBInstanceSecurityGroup | Restrict to app server IPs only |
| Public access | EnableWanService | Disable unless necessary |
| Password-free access | Instance config | Disable; always use authentication |

### Password Policies

- Length: 8-32 characters
- Must include: uppercase letters, lowercase letters, digits, special characters
- Enable password rotation: `tccli mongodb EnablePasswordRotation`

## Cost Pillar (成本)

### Billing Model Comparison

| Model | Discount | Flexibility | Best For |
|-------|----------|-------------|----------|
| Prepaid (包年包月) | 15-50% (1-3yr) | Low | Stable production workloads |
| Postpaid (按量计费) | None | High | Dev/test, burst workloads |

### Right-Sizing

- Use monitoring metrics (CPU, memory, disk, connections) to identify over-provisioned instances
- Scale down via ModifyDBInstanceSpec when utilization is consistently low
- Monitor ClusterDiskUsage and use auto-scaling patterns

### Cost Optimization

1. **Reserved instances:** Prepaid 1-year or 3-year for predictable workloads
2. **Idle instance detection:** Check instances with status=2 but zero connections
3. **Backup cost management:** Set appropriate BackupRetentionPeriod (7-30 days)
4. **Spec selection:** Choose HCD (cloud disk) for elastic scaling needs; HIO10G for high IOPS
5. **Right-sizing via price inquiry:** Always use InquirePriceModifyDBInstanceSpec before changes

### Cost Calculation

```bash
# Compare monthly vs hourly pricing
tccli mongodb InquirePriceCreateDBInstances --Zone ap-guangzhou-3 --NodeNum 3 --Memory 4 --Volume 10 --MongoVersion MONGO_60_WT --MachineCode HCD --GoodsNum 1 --ClusterType 0 --Period 1
tccli mongodb InquirePriceCreateDBInstances --Zone ap-guangzhou-3 --NodeNum 3 --Memory 4 --Volume 10 --MongoVersion MONGO_60_WT --MachineCode HCD --GoodsNum 1 --ClusterType 0 --Period 12
```

## Efficiency Pillar (效率)

### Batch Operations

| Pattern | Method | Description |
|---------|--------|-------------|
| Batch modify specs | Loop with ModifyDBInstanceSpec | Scale multiple instances |
| Batch backup | Loop with CreateBackupDBInstance | Backup all instances |
| Batch status check | DescribeDBInstances with Limit=100 | List all instances |

### Parameter Templates

- Create reusable parameter configs via CreateDBInstanceParamTpl
- Apply to new instances during creation (reference template ID)
- Standardize slowMS, maxConns, messageMaxBytes across environments

### CI/CD Automation

- Integrate backup scripts into CI/CD pipelines
- Use DescribeAsyncRequestInfo for deployment wait states
- Automate instance creation for ephemeral environments

### Scaling Patterns

| Scale Type | Method | Downtime | Use Case |
|------------|--------|----------|----------|
| Vertical (memory/disk) | ModifyDBInstanceSpec | Minutes | Growth within current architecture |
| Horizontal (shards) | Create new sharded instance | Hours | Beyond single shard capacity |
| Read scaling | Add/secondary nodes via ModifyDBInstanceSpec | None | Read-heavy workloads |

### Connection Pooling

- Set maxConns via ModifyInstanceParams: `net.maxIncomingConnections`
- Recommended pool size: (CPU cores × 2) per application instance
- Monitor Connper metric to avoid connection exhaustion

### Slow Query Optimization

1. Set appropriate slowMS threshold (100-500ms) via ModifyInstanceParams
2. Analyze DescribeSlowLogPatterns for frequent slow patterns
3. Use DescribeDetailedSlowLogs to get full query text
4. Recommend indexes for collection scans
5. Consider memory upgrade if working set exceeds RAM

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-mongodb-ops` |
| `product` | `mongodb` |
| Finding `id` pattern | `mongodb-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

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
  "skill_id": "qcloud-mongodb-ops",
  "product": "mongodb",
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
          "id": "mongodb-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Backup not enabled",
          "evidence": "Automated backup disabled on prod instance",
          "recommendation": "Enable automatic backup with retention ≥ 7 days",
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
      "action": "Enable automatic backup with retention ≥ 7 days",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tccli mongodb DescribeDBInstances --Region ap-guangzhou (SecretKey=<masked>)"
    ],
    "request_ids": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    ]
  },
  "errors": []
}
```
