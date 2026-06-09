# CDB Well-Architected Assessment

> **Mode split:** `[assessment-readonly]` — Describe* / GetMonitorData only (Well-Architected worker).
> `[remediation-only]` — Create/Modify/Delete runbooks; **MUST NOT** execute when `{{user.mode}}=well-architected-readonly`.
> Worker JSON: **Worker Output Contract** at end of this file.

Four-pillar assessment based on Tencent Cloud Well-Architected Framework for TencentDB for MySQL (CDB): Reliability, Security, Cost, Efficiency.

---

## 1. Framework Overview

Tencent Cloud Well-Architected Framework defines four pillars for cloud resource design:

| Pillar | Focus | CDB Assessment Scope |
|--------|-------|---------------------|
| **可靠性 (Reliability)** | Availability, DR, recovery | Multi-AZ, backup/restore, clone, replication, auto-failover |
| **安全性 (Security)** | Access control, encryption, network isolation | CAM, SSL, encryption-at-rest, VPC, account management |
| **成本 (Cost)** | Resource optimization, waste reduction | Right-sizing, prepaid vs postpaid, reserved instances, idle detection |
| **效率 (Efficiency)** | Automation, batch operations, CI/CD | Parameter tuning, slow query optimization, DTS migration, monitoring |

---

## 2. Reliability Pillar (可靠性)

### Multi-AZ Deployment

| Pattern | Description | Risk Level |
|---------|-------------|------------|
| Single AZ | Master instance in one zone | High (zone outage = total DB downtime) |
| Multi-AZ (DR instance) | Master in Zone A, DR in Zone B | Low (automatic failover) |
| Cross-Region (DR) | Master in Region A, DR in Region B | Very Low (region outage = DR promotion) |

**Assessment Checklist:**

```bash
# Check instance zone distribution and DR setup
tccli cdb DescribeDBInstances --Region ap-guangzhou | python3 -c "
import sys,json
d=json.load(sys.stdin)
for i in d['Response']['Items']:
    role = {1:'Master',2:'DR',3:'Read-only'}.get(i['InstanceType'],'Unknown')
    print(f\"{i['InstanceName']}: Zone={i['Zone']}\")
    print(f\"  Role: {role}\")
    print(f\"  Type: {i['InstanceType']}\")
"

# Expected: production instances have DR instance in different AZ
```

**Multi-AZ Setup:**

```bash
# Create a DR instance in a different AZ
tccli cdb CreateDBInstance \
  --Memory 4000 \
  --Volume 200 \
  --Period 12 \
  --GoodsNum 1 \
  --Zone ap-guangzhou-6 \
  --EngineVersion "8.0" \
  --InstanceRole "dr" \
  --MasterInstanceId "cdb-xxxxxx"
```

### Backup and Recovery

| Metric | Requirement | Assessment |
|--------|-------------|------------|
| RPO (Recovery Point Objective) | Max data loss window | Automatic daily backups + binlog (continuous) |
| RTO (Recovery Time Objective) | Max recovery time | Clone from backup duration |

**Backup Configuration:**

```bash
# Check current backup config
tccli cdb DescribeBackupConfig --InstanceId "cdb-xxxxxx"

# Set recommended backup config
tccli cdb ModifyBackupConfig \
  --InstanceId "cdb-xxxxxx" \
  --BackupTimeStart "02:00" \
  --BackupTimeEnd "06:00" \
  --BackupModel "physical" \
  --BackupPeriods '["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]' \
  --BackupRetentionDays 30
```

**Assessment Checklist:**

- [ ] Automatic daily backups enabled for all production instances
- [ ] Backup retention period ≥ 30 days
- [ ] Binlog backup enabled for point-in-time recovery
- [ ] Regular restore testing (quarterly minimum)
- [ ] Backup stored in same region (cross-region backup if available)

### DR Runbook (Phase 1 → 2 → 3)

**Phase 1: Immediate Response (0-15 min)**

```bash
# 1. Check instance status
tccli cdb DescribeDBInstances --InstanceIds '["cdb-xxxxxx"]'

# 2. If instance is down, check DR instance status
tccli cdb DescribeDBInstances | python3 -c "
import sys,json
d=json.load(sys.stdin)
for i in d['Response']['Items']:
    if i.get('MasterInstanceId') == 'cdb-xxxxxx':
        print(f'DR instance: {i[\"InstanceId\"]} Status={i[\"Status\"]}')
"

# 3. Promote DR instance (if available)
# Note: DR promotion requires modifying application connection string
# The DR instance becomes the new master
```

**Phase 2: Data Recovery (15-60 min)**

```bash
# 1. Find the latest backup
tccli cdb DescribeBackups --InstanceId "cdb-xxxxxx" --Offset 0 --Limit 1

# 2. Clone from backup (creates a new instance)
tccli cdb CreateCloneInstance \
  --InstanceId "cdb-xxxxxx" \
  --SpecifyBackupId 12345 \
  --SpecifyBackupType "BackupId"

# 3. Or clone to point-in-time (right before the failure)
tccli cdb CreateCloneInstance \
  --InstanceId "cdb-xxxxxx" \
  --SpecifyBackupType "Timepoint" \
  --SpecifyBackupTime "2026-05-21 11:59:00"
```

**Phase 3: Post-Recovery (60+ min)**

```bash
# 1. Verify data integrity on recovered instance
# 2. Update application connection strings to new instance IP
# 3. Set up replication or backup for new primary
# 4. Document RTO achieved and report
```

### Read Replica Management

Read-only replicas provide horizontal read scaling but require consistency awareness:

| Aspect | Guidance | Assessment |
|--------|----------|------------|
| Replica limit | Max 5 per master instance | Plan read capacity accordingly |
| Replication lag | SecondsBehindMaster < 30s | Monitor; adjust replica count if lag persists |
| Consistency | Eventual consistency for read replicas | Application must tolerate stale reads |
| Failover | Read replicas do NOT auto-promote to master | Manual promotion via console/API |

**Read Replica Consistency Check:**

```bash
# Check replication lag
tccli monitor GetMonitorData \
  --Namespace QCE/CDB \
  --MetricName SecondsBehindMaster \
  --Dimensions '[{"Name":"InstanceId","Value":"cdb-ro-xxxxxx"}]' \
  --StartTime 2026-05-21T00:00:00+08:00 \
  --EndTime 2026-05-21T23:59:59+08:00 \
  --Period 60

# Compare data count between master and replica
# mysql -h <master_vip> -e "SELECT COUNT(*) FROM mydb.orders"
# mysql -h <replica_vip> -e "SELECT COUNT(*) FROM mydb.orders"
```

### Connection Proxy and Pooling

For applications with fluctuating connection patterns, consider Tencent Cloud Database Proxy or application-side pooling:

| Pattern | Benefit | Implementation |
|---------|---------|----------------|
| Application connection pool | Reduces connection churn | HikariCP, DBCP, c3p0 |
| Database Proxy | Connection multiplexing, read/write splitting | Tencent Cloud DB Proxy (if available) |
| ProxySQL (self-managed) | Advanced routing, query caching | Deploy on CVM in same VPC |

**Recommended Connection Pool Settings:**

```python
# HikariCP (Spring Boot) example
spring.datasource.hikari.maximum-pool-size=20
spring.datasource.hikari.minimum-idle=5
spring.datasource.hikari.connection-timeout=30000
spring.datasource.hikari.idle-timeout=600000
spring.datasource.hikari.max-lifetime=1800000
```

---

## 3. Security Pillar (安全性)

### Network Security

| Control | Implementation | Assessment |
|---------|---------------|------------|
| VPC Isolation | CDB instance must be deployed in a VPC | Default — created in VPC |
| Security Groups | Firewall rules for MySQL port 3306 | Whitelist only trusted source subnets |
| Public Access | WAN service (OpenWanService) | Disabled for production |
| SSL/TLS | Encrypt connections to MySQL | Enable for production |

**Assessment Checklist:**

```bash
# Check if WAN is open (should be closed for production)
tccli cdb DescribeDBInstances --InstanceIds '["cdb-xxxxxx"]' | python3 -c "
import sys,json
d=json.load(sys.stdin)
i=d['Response']['Items'][0]
vip = i['Vip']
# If VIP is public (not 10.x/172.x/192.168.x), WAN is open
print(f'Internal IP: {vip}')
print('⚠️ WAN access should be disabled for production' if not vip.startswith('10.') and not vip.startswith('172.') else '✅ Internal access only')
"

# Check SSL status
tccli cdb DescribeSSLStatus --InstanceId "cdb-xxxxxx"
```

### Access Control

| Control | Implementation | Assessment |
|---------|---------------|------------|
| CAM Permissions | IAM policies for CDB API access | Least privilege principle |
| Account Management | MySQL user accounts with host restrictions | Host `%` only when necessary |
| Password Policy | Strong passwords for all accounts | Rotate regularly |
| Encryption at Rest | Data-at-rest encryption via KMS | Enabled for sensitive data |

**Security Configuration:**

```bash
# Enable SSL for encrypted connections
tccli cdb OpenSSL --InstanceId "cdb-xxxxxx"

# Enable encryption at rest (requires KMS key)
tccli cdb OpenDBInstanceEncryption \
  --InstanceId "cdb-xxxxxx" \
  --KeyId "kms-xxxxxx"

# Create restricted accounts (not % wildcard)
tccli cdb CreateAccounts \
  --InstanceId "cdb-xxxxxx" \
  --Accounts '[{"User":"app_user","Host":"10.0.0.%"}]' \
  --Password "SecurePassword123!"
```

**Assessment Checklist:**

- [ ] CAM policies follow least privilege (only required CDB actions)
- [ ] SSL enabled for all production instances
- [ ] Account hosts restricted (avoid `%` wildcard)
- [ ] Encryption at rest enabled
- [ ] WAN access disabled for production instances
- [ ] Security group only allows traffic from application tiers
- [ ] CloudAudit trail enabled for CDB API operations

### Audit Logging

| Audit Source | What It Logs | Action |
|-------------|-------------|--------|
| CloudAudit | All CDB API calls (CreateDBInstance, DeleteAccounts, etc.) | Enable multi-region trail |
| Error Log (DescribeErrorLogData) | MySQL error log — authentication failures, connection issues | Review daily |
| Slow Query Log (DescribeSlowLogData) | Queries exceeding threshold | Enable for performance + security anomaly detection |

### Password Security and Rotation

```bash
# Rotate MySQL account password
tccli cdb ModifyAccountPassword \
  --InstanceId "cdb-xxxxxx" \
  --Accounts '[{"User":"app_user","Host":"%"}]' \
  --NewPassword "StrongNewPassword789!"

# Verify password complexity — should:
# - Minimum 8 characters
# - Include uppercase, lowercase, numbers, special chars
# - Not contain common dictionary words

# Check for accounts with weak host restrictions
tccli cdb DescribeAccounts --InstanceId "cdb-xxxxxx" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('Accounts with unrestricted host (%):')
for a in d['Response'].get('Items', []):
    user = a.get('User', '?')
    host = a.get('Host', '?')
    if host in ['%', '']:
        print(f'  ⚠️ {user}@{host} — restrict to specific subnet if possibl')
    else:
        print(f'  ✅ {user}@{host}')
"
```

### Security Incident Response Runbook

**Phase 1: Containment (0-15 min)**

```bash
# 1. Check instance and recent operations
tccli cdb DescribeTasks --InstanceId "cdb-xxxxxx" \
  --StartTimeBegin "$(date -v-1d +'%Y-%m-%d 00:00:00')" \
  --StartTimeEnd "$(date +'%Y-%m-%d %H:%M:%S')"

# 2. Force password rotation for all accounts
# tccli cdb ModifyAccountPassword ...

# 3. Close WAN access if open
tccli cdb CloseWanService --InstanceId "cdb-xxxxxx"

# 4. Restrict network access via security group — delegate to qcloud-vpc-ops
```

**Phase 2: Investigation (15-60 min)**

```bash
# 1. Review error logs for authentication failures
tccli cdb DescribeErrorLogData \
  --InstanceId "cdb-xxxxxx" \
  --StartTime "$(date -v-1d +'%Y-%m-%d 00:00:00')" \
  --EndTime "$(date +'%Y-%m-%d %H:%M:%S')" \
  --Limit 50

# 2. Review accounts and privileges
tccli cdb DescribeAccounts --InstanceId "cdb-xxxxxx"

# 3. Check SSL status
tccli cdb DescribeSSLStatus --InstanceId "cdb-xxxxxx"
```

**Phase 3: Recovery (60+ min)**

- Restore from pre-incident backup if data was compromised
- Rotate ALL passwords (root, application, read-only accounts)
- Revoke and recreate compromised API keys
- Enable CloudAudit if not already enabled
- Document incident and update security policies

---

## 4. Cost Pillar (成本)

### Instance Right-Sizing

| Strategy | Implementation | Assessment |
|----------|---------------|------------|
| CPU right-sizing | Match CPU to workload | Monitor CpuUseRate trend |
| Memory right-sizing | Match memory to data/query volume | Monitor MemoryUseRate |
| Storage right-sizing | Match disk to data growth | Monitor VolumeRate trend |

**Cost Assessment:**

```bash
# Check current utilization
tccli monitor GetMonitorData \
  --Namespace QCE/CDB \
  --MetricName CpuUseRate \
  --Dimensions '[{"Name":"InstanceId","Value":"cdb-xxxxxx"}]' \
  --StartTime 2026-05-20T00:00:00+08:00 \
  --EndTime 2026-05-21T00:00:00+08:00 \
  --Period 3600
```

**Right-Sizing Checklist:**

- [ ] CPU utilization consistently < 40% → consider downgrade
- [ ] Memory utilization consistently > 80% → consider upgrade
- [ ] Disk usage growth trend predictable → plan expansion before full
- [ ] Idle instances detected → isolate or release

### Billing Model Optimization

| Model | Best For | Savings vs Postpaid |
|-------|----------|---------------------|
| Postpaid (hourly) | Variable/dev/test workloads | Baseline |
| Prepaid (monthly/yearly) | Stable production workloads | 15-30% savings |
| Reserved Instances | Long-term commitments (1-3 years) | Up to 50% savings |

```bash
# Check current billing mode
tccli cdb DescribeDBInstances --InstanceIds '["cdb-xxxxxx"]' | python3 -c "
import sys,json
d=json.load(sys.stdin)
i=d['Response']['Items'][0]
print(f'PayType: {i.get(\"PayType\", \"N/A\")}')  # 0=prepaid, 1=postpaid
print(f'AutoRenew: {i.get(\"AutoRenew\", \"N/A\")}')
"

# Convert from postpaid to prepaid (via RenewDBInstance)
tccli cdb RenewDBInstance \
  --InstanceId "cdb-xxxxxx" \
  --TimeSpan 12 \
  --ModifyPayType 1  # Switch to prepaid
```

### Idle Instance Detection

```bash
# Find candidate instances for right-sizing or release
tccli cdb DescribeDBInstances --Region ap-guangzhou | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'{\"Name\":<25} {\"Spec\":<15} {\"Status\":<12} {\"Created\":<20}')
print('='*72)
for i in d['Response']['Items']:
    status = {0:'Creating',1:'Running',4:'Isolating',5:'Isolated'}.get(i['Status'],f'Unknown({i[\"Status\"]})')
    print(f\"{i.get('InstanceName',''):<25} {i['Memory']}MB/{i['Volume']}GB {status:<12} {i.get('CreateTime',''):<20}\")
print()
# Highlight isolated instances (Status=5) still incurring storage costs
isolated = [i for i in d['Response']['Items'] if i['Status'] == 5]
if isolated:
    print(f'⚠️ {len(isolated)} isolated instance(s) — release to stop storage costs')
    for i in isolated:
        print(f'  tccli cdb ReleaseIsolatedDBInstances --InstanceIds \"[\\\"{i[\"InstanceId\"]}\\\"]\"')
"

# Release isolated instances (irreversible — confirm first!)
# tccli cdb ReleaseIsolatedDBInstances --InstanceIds '["cdb-xxxxxx"]'
```

### Backup Storage Cost Optimization

Backup files count against CDB instance's total disk quota (up to 200% of instance storage):

| Strategy | Savings | Implementation |
|----------|---------|----------------|
| Reduce retention days | Lower storage cost | `ModifyBackupConfig --BackupRetentionDays 14` |
| Delete manual backups | Direct savings | `DeleteBackups` for outdated manual backups |
| Physical vs logical backup | Physical is ~30% smaller | Use physical backup by default |
| Binlog retention tuning | Reduce binlog storage | Modify `binlog_expire_logs_seconds` |

**Backup Cost Check:**

```bash
# Check backup count and total size
tccli cdb DescribeBackups --InstanceId "cdb-xxxxxx" --Limit 100 | python3 -c "
import sys,json
d=json.load(sys.stdin)
total_size = sum(b.get('BackupSize', 0) for b in d['Response'].get('Items', []))
print(f'Total backups: {len(d[\"Response\"].get(\"Items\", []))}')
print(f'Total backup size: {total_size / 1024:.1f} MB')
print(f'Current disk: check via DescribeDBInstances')
"

# Check binlog retention
tccli cdb DescribeInstanceParams --InstanceId "cdb-xxxxxx" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for p in d['Response']['Items']:
    if p['Name'] == 'binlog_expire_logs_seconds':
        days = int(p['CurrentValue']) / 86400
        print(f'Binlog retention: {p[\"CurrentValue\"]}s ({days:.0f} days)')
        print(f'Recommendation: 7-14 days (604800-1209600s) for most workloads')
"
```

### Read Replica Cost Analysis

Read replicas are billed at the same rate as master instances:

| Replica Count | Cost Multiplier | When to Use |
|--------------|----------------|-------------|
| 0 | 1x (master only) | Read workload fits within master capacity |
| 1 | 2x | Moderate read scaling needs |
| 2-3 | 3-4x | Heavy read workload, reporting, analytics |
| 4-5 | 5-6x | Extreme read scaling (consider caching first) |

**Best Practice:** Start with 1 read replica for reporting/analytics queries. Monitor `SecondsBehindMaster`. Only add replicas when CPU or connection limits are consistently reached.

---

## 5. Efficiency Pillar (效率)

### Performance Optimization

| Practice | Benefit | Assessment |
|----------|---------|------------|
| Slow Query Log | Identify performance bottlenecks | Enable and review regularly |
| Parameter Tuning | Optimize for workload | Review vs best practices |
| Index Optimization | Reduce full table scans | Regular review |
| Connection Pooling | Manage connections efficiently | Application-level |

**Parameter Review:**

```bash
# Get current parameter values
tccli cdb DescribeInstanceParams --InstanceId "cdb-xxxxxx" | python3 -c "
import sys,json
d=json.load(sys.stdin)
key_params = ['max_connections','wait_timeout','innodb_buffer_pool_size','slow_query_log','long_query_time']
current = {p['Name']: p['CurrentValue'] for p in d['Response']['Items'] if p['Name'] in key_params}
import json as j
print(j.dumps(current, indent=2))
"
```

**Recommended Parameter Values:**

| Parameter | Recommended | Rationale |
|-----------|-------------|-----------|
| `max_connections` | 1000+ (based on spec) | Avoid connection starvation |
| `wait_timeout` | 28800 (8 hours) | Balance between timeout safety and connection reuse |
| `innodb_buffer_pool_size` | 50-70% of available memory | Optimal InnoDB caching |
| `slow_query_log` | ON | Enable slow query capture |
| `long_query_time` | 2 (seconds) | Capture slow queries |

### Automation

| Area | Tool | Assessment |
|------|------|------------|
| Backup management | tccli cdb | Automatic + manual |
| Scaling | tccli cdb UpgradeDBInstance | Online scaling |
| Parameter changes | tccli cdb ModifyInstanceParam | Batch updates |
| Monitoring | tccli monitor | Delegate to qcloud-monitor-ops |
| Slow query analysis | tccli cdb DescribeSlowLogData | Regular review |

---

## 6. AIOps Integration (智能运维)

### Anomaly Detection Patterns

| Anomaly | Detection Method | Automated Action |
|---------|-----------------|------------------|
| CPU spike > 90% | Monitor CpuUseRate + DescribeSlowLogData | Check slow queries; notify |
| Disk fill prediction | Monitor VolumeRate trend | Calculate days-to-full; proactive alert |
| Connection surge | Monitor ConnectionUseRate | Check app connection pool; suggest scaling |
| Replication lag > 60s | Monitor SecondsBehindMaster | Check network; examine DR instance |

**Automated Anomaly Detection Script:**

```bash
#!/bin/bash
# CDB anomaly detection — run every 15 min via cron
INSTANCE_ID="${1:-cdb-xxxxxx}"

# Check CPU
CPU=$(tccli monitor GetMonitorData \
  --Namespace QCE/CDB --MetricName CpuUseRate \
  --Dimensions "[{\"Name\":\"InstanceId\",\"Value\":\"$INSTANCE_ID\"}]" \
  --StartTime "$(date -u -v-15M +%Y-%m-%dT%H:%M:%SZ)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --Period 300 | python3 -c "import sys,json;d=json.load(sys.stdin);v=d['Response']['DataPoints'][0]['Values'];print(max(v) if v else 0)" 2>/dev/null)

if [ "$CPU" -gt 90 ]; then
  echo "⚠️ HIGH CPU: ${CPU}% — checking slow queries"
  tccli cdb DescribeSlowLogData \
    --InstanceId "$INSTANCE_ID" \
    --StartTime "$(date -v-15M +'%Y-%m-%d %H:%M:%S')" \
    --EndTime "$(date +'%Y-%m-%d %H:%M:%S')" \
    --Limit 5
fi

# Check disk
DISK=$(tccli monitor GetMonitorData \
  --Namespace QCE/CDB --MetricName VolumeRate \
  --Dimensions "[{\"Name\":\"InstanceId\",\"Value\":\"$INSTANCE_ID\"}]" \
  --StartTime "$(date -u -v-15M +%Y-%m-%dT%H:%M:%SZ)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --Period 300 | python3 -c "import sys,json;d=json.load(sys.stdin);v=d['Response']['DataPoints'][0]['Values'];print(max(v) if v else 0)" 2>/dev/null)

if [ "$DISK" -gt 90 ]; then
  echo "⚠️ CRITICAL DISK: ${DISK}% — immediate action required"
fi
```

### Self-Healing Runbook

| Condition | Diagnosis | Auto-Remediation | Escalation |
|-----------|-----------|-----------------|------------|
| Instance unreachable | DescribeDBInstances Status != 1 | RestartDBInstances → wait 3min → re-check | Alert if still down |
| High CPU > 90% for 30min | Monitor CpuUseRate | Check slow queries; suggest scale-up | Create Jira ticket |
| Disk > 95% | Monitor VolumeRate | Alert user; suggest expansion or cleanup | Pager notification |
| Replication lag > 120s | Monitor SecondsBehindMaster | Check network; verify DR instance | Escalate if persists > 1h |

### Log-Metric Correlation

Combine error logs and metrics for faster root cause analysis:

```bash
# 1. Detect anomaly (metric shows CPU spike)
# 2. Check error logs at same time
tccli cdb DescribeErrorLogData \
  --InstanceId "cdb-xxxxxx" \
  --StartTime "2026-05-21 10:00:00" \
  --EndTime "2026-05-21 10:30:00" \
  --Limit 20

# 3. Check slow queries
tccli cdb DescribeSlowLogData \
  --InstanceId "cdb-xxxxxx" \
  --StartTime "2026-05-21 10:00:00" \
  --EndTime "2026-05-21 10:30:00" \
  --OrderBy "QueryTime" \
  --Order "DESC" \
  --Limit 10

# 4. Check recent tasks
tccli cdb DescribeTasks --InstanceId "cdb-xxxxxx" \
  --StartTimeBegin "2026-05-21 10:00:00" \
  --StartTimeEnd "2026-05-21 10:30:00"
```

**Correlation Matrix:**

| Metric Anomaly | Look For In Logs | Likely Root Cause |
|----------------|-----------------|-------------------|
| CPU spike | Slow queries (full table scans) | Missing index; bad query pattern |
| Disk surge | Binary log growth, large temp tables | Long-running write transaction |
| Connection spike | Error log (auth failures, aborted connects) | Connection pool leak; app bug |
| Replication lag | Network latency, IO wait | Heavy write load; network issue |

### Capacity Forecasting

```bash
#!/bin/bash
# Simple capacity forecast based on current usage
INSTANCE_ID="${1:-cdb-xxxxxx}"

# Get current metrics
CPU=$(tccli monitor GetMonitorData \
  --Namespace QCE/CDB --MetricName CpuUseRate \
  --Dimensions "[{\"Name\":\"InstanceId\",\"Value\":\"$INSTANCE_ID\"}]" \
  --StartTime "$(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --Period 86400 | python3 -c "import sys,json;d=json.load(sys.stdin);v=d['Response']['DataPoints'][0]['Values'];print(f'Avg: {sum(v)/len(v):.1f}%, Max: {max(v)}%' if v else 'N/A')" 2>/dev/null)

echo "CPU (7-day): $CPU"
echo "Recommendation: If avg CPU > 70%, plan scale-up within next billing cycle"
echo "If max CPU > 90%, consider immediate scale-up or query optimization"
```

---

## 6. Assessment Summary

| Pillar | Score | Key Gaps | Priority |
|--------|-------|----------|----------|
| **可靠性** | ✅ Good | Multi-AZ DR for critical instances; backup/restore tested; read replica management added | High |
| **安全性** | ✅ Good | SSL, encryption, VPC isolation, audit logging, password rotation, incident response added | Medium |
| **成本** | ✅ Good | Right-sizing, prepaid evaluation, idle detection, backup storage cost, read replica cost analysis | Medium |
| **效率** | ✅ Good | Slow query log, parameter tuning, automation, connection pooling guidance available | Low |
| **AIOps** | ✅ Good | Anomaly detection script, self-healing runbook, log-metric correlation, capacity forecasting | Medium |

### Getting Started Checklist

- [ ] Enable automatic daily backups for all production instances (retention ≥ 30 days)
- [ ] Enable SSL for all production instances
- [ ] Enable slow query log (`slow_query_log=ON`, `long_query_time=2`)
- [ ] Review instance right-sizing for all instances (CPU/memory/disk)
- [ ] Evaluate prepaid billing for stable production workloads
- [ ] Configure Cloud Monitor alarms (CPU > 80%, disk > 80%, replication lag)
- [ ] 通过 DescribeSlowLogData 定期审查慢查询并优化索引
- [ ] Document DR runbook with tested restore procedures
- [ ] Deploy anomaly detection script (15-min cron for CPU/disk monitoring)
- [ ] Enable CloudAudit trail for security audit logging
- [ ] Review isolated/stopped instances monthly for cost optimization
- [ ] Test read replica consistency quarterly

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-cdb-ops` |
| `product` | `cdb` |
| Finding `id` pattern | `cdb-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

### Pillar → checklist map

| `pillars` key | Checklist source in this document |
|---------------|-------------------------------------|
| `reliability` | §2 Reliability Pillar |
| `security` | §3 Security Pillar |
| `cost` | §4 Cost Pillar |
| `efficiency` | §5 Efficiency Pillar |

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
  "skill_id": "qcloud-cdb-ops",
  "product": "cdb",
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
          "id": "cdb-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Backup age exceeds RPO",
          "evidence": "Latest backup > 24h for production instance",
          "recommendation": "Enable automated daily backup; verify retention policy",
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
      "action": "Enable automated daily backup; verify retention policy",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tccli cdb DescribeDBInstances --Region ap-guangzhou (SecretKey=<masked>)"
    ],
    "request_ids": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    ]
  },
  "errors": []
}
```
