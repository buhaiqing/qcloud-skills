# ES Well-Architected Assessment

Four-pillar assessment based on Tencent Cloud Well-Architected Framework for Elasticsearch Service: Reliability, Security, Cost, Efficiency.

---

## 1. Framework Overview

Tencent Cloud Well-Architected Framework defines four pillars for cloud resource design:

| Pillar | Focus | ES Assessment Scope |
|--------|-------|-------------------|
| **可靠性 (Reliability)** | Availability, DR, recovery | Multi-AZ, snapshot backup, health diagnosis, auto-recovery |
| **安全性 (Security)** | Access control, encryption, network isolation | CAM, VPC, Kibana access control, TLS, security groups |
| **成本 (Cost)** | Resource optimization, waste reduction | Node right-sizing, tiering, reserved instances, COS snapshot economics |
| **效率 (Efficiency)** | Automation, batch operations, CI/CD | ILM, rollover, force-merge, plugin/dictionary automation, monitoring |

---

## 2. Reliability Pillar (可靠性)

### Multi-AZ Deployment

> Tencent Cloud ES does not natively support multi-AZ within a single cluster instance. For high availability, rely on cross-region snapshot restore or application-level multi-cluster routing.

| Pattern | Description | Risk Level |
|---------|-------------|------------|
| Single AZ | All nodes in one zone | High (zone outage = total unavailability) |
| Cross-region snapshot | Backup to COS; restore in another region | Medium (RTO = restore time) |
| Application multi-cluster | Write to 2+ clusters across regions | Low (active-active) |

**Assessment Checklist:**

```bash
# Check cluster zone placement
tccli es DescribeInstances --Region ap-guangzhou | python3 -c "
import sys,json
d=json.load(sys.stdin)
for i in d['Response']['InstanceList']:
    print(f\"{i['InstanceName']}: Zone={i['Zone']}\")
"

# All production clusters should be evaluated for cross-region backup strategy
```

### Dedicated Master Nodes

For clusters with ≥ 6 data nodes, dedicated master nodes are strongly recommended:

| Node Count | Recommendation | Risk Without Dedicated Masters |
|-----------|----------------|-------------------------------|
| 1-5 | Dedicated masters optional | Low risk for small clusters |
| 6-10 | 3 dedicated master nodes | Medium — split-brain risk on node failure |
| 11+ | 3 dedicated master nodes (minimum) | High — cluster instability |

**Recommendation:** Always enable 3 dedicated master nodes for production clusters ≥ 6 data nodes. This separates cluster management from data/indexing workloads and prevents cluster instability during node failures.

### Shard Allocation and Rebalancing

After recovery operations, shard rebalancing is automatic but may cause performance impact:

```bash
# Check current shard allocation
# Via Kibana: GET _cat/shards?v

# Monitor unassigned shards after node restart
# Via Kibana: GET _cat/shards?v&h=index,shard,prirep,state,node&s=state

# Temporarily disable shard rebalancing during peak hours (if needed)
# Via Kibana: PUT _cluster/settings {"transient":{"cluster.routing.rebalance.enable":"none"}}

# Re-enable after maintenance
# Via Kibana: PUT _cluster/settings {"transient":{"cluster.routing.rebalance.enable":"all"}}
```

### Backup and Recovery

| Metric | Requirement | Assessment |
|--------|-------------|------------|
| RPO (Recovery Point Objective) | Max data loss window | Snapshot frequency (COS-based) |
| RTO (Recovery Time Objective) | Max recovery time | Snapshot restore duration (depends on data size) |

**Snapshot Policy:**

```bash
# Check existing snapshots
tccli es DescribeClusterSnapshot --InstanceId "es-xxxxxx"

# Recommended: Daily snapshots for production clusters
# Retention: 7-30 days based on RPO requirement
# Cross-region: Copy snapshots to another region's COS bucket
```

**Cross-Region Snapshot Automation:**

```bash
#!/bin/bash
# Copy ES snapshots cross-region for DR
# Requires: COS bucket in both source and destination region
SOURCE_REGION="ap-guangzhou"
DEST_REGION="ap-shanghai"
INSTANCE_ID="es-xxxxxx"

# 1. Create snapshot in source region
tccli es CreateClusterSnapshot \
  --InstanceId "$INSTANCE_ID" \
  --SnapshotName "dr-snapshot-$(date +%Y%m%d)"

# 2. Get snapshot info
SNAPSHOT_ID=$(tccli es DescribeClusterSnapshot --InstanceId "$INSTANCE_ID" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['Response']['ClusterSnapshotSet'][-1]['SnapshotId'])")

echo "Snapshot created: $SNAPSHOT_ID"

# 3. To truly cross-region: configure COS bucket cross-region replication
# Delegate to qcloud-cos-ops for COS bucket replication setup
```

**Assessment Checklist:**

- [ ] Automatic daily snapshots enabled for all production clusters
- [ ] Snapshots stored in cross-region COS bucket for DR
- [ ] Regular snapshot restore tests (quarterly minimum)
- [ ] Snapshot retention period ≥ organizational policy requirement
- [ ] Dedicated master nodes enabled for clusters ≥ 6 data nodes
- [ ] Shard rebalancing monitored during recovery operations

### DR Runbook (Phase 1 → 2 → 3)

**Phase 1: Immediate Response (0-15 min)**

```bash
# 1. Diagnose cluster health
tccli es DiagnoseInstance --InstanceId "es-xxxxxx"
tccli es DescribeDiagnose --InstanceId "es-xxxxxx"

# 2. Check cluster details
tccli es DescribeInstances --InstanceIds '["es-xxxxxx"]'

# 3. If health is RED, check unassigned shards
# Via Kibana: GET _cluster/allocation/explain

# 4. Attempt restart
tccli es RestartInstance --InstanceId "es-xxxxxx"

# 5. If restart fails, proceed to snapshot restore
```

**Phase 2: Data Recovery (15-60 min)**

```bash
# 1. Restore from latest snapshot
SNAPSHOT_ID=$(tccli es DescribeClusterSnapshot --InstanceId "es-xxxxxx" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['Response']['ClusterSnapshotSet'][-1]['SnapshotId'])")

tccli es RestoreClusterSnapshot \
  --InstanceId "es-xxxxxx" \
  --SnapshotId "$SNAPSHOT_ID"

# 2. Or create a new cluster from snapshot in another region
tccli es CreateInstance \
  --Region ap-shanghai \
  --Zone ap-shanghai-4 \
  --NodeType "ES.S1.LARGE8" \
  --NodeNum 3 \
  --EsVersion "7.14.2" \
  --VpcId "vpc-dr-xxxx" \
  --SubnetId "subnet-dr-xxxx" \
  --Password "{{user.password}}" \
  --InstanceName "${INSTANCE_NAME}-dr"

# Then restore snapshot on new cluster
# tccli es RestoreClusterSnapshot --InstanceId "es-new-xxx" --SnapshotId "$SNAPSHOT_ID"
```

**Phase 3: Post-Recovery (60+ min)**

```bash
# 1. Verify data integrity via Kibana
# 2. Verify search/indexing works
# 3. Verify shard allocation is complete (green status)
# 4. Update application connection strings
# 5. Document RTO achieved and report
# 6. Re-establish backup schedule on recovered cluster
```

---

## 3. Security Pillar (安全性)

### Network Security

| Control | Implementation | Assessment |
|---------|---------------|------------|
| VPC Isolation | ES cluster must be deployed in a VPC | Default — required for creation |
| Security Groups | Firewall rules for ES/Kibana ports | Whitelist only trusted source IPs |
| Private Access | ES and Kibana accessible within VPC | Default — WAN disabled by default |

**Assessment Checklist:**

```bash
# Verify cluster is in VPC (not public)
tccli es DescribeInstances --InstanceIds '["es-xxxxxx"]' | python3 -c "
import sys,json
d=json.load(sys.stdin)
i=d['Response']['InstanceList'][0]
print(f'VPC: {i.get(\"VpcId\", \"N/A\")}')
print(f'Subnet: {i.get(\"SubnetId\", \"N/A\")}')
"
```

### Access Control

| Control | Implementation | Assessment |
|---------|---------------|------------|
| CAM Permissions | IAM policies for ES API access | Least privilege principle |
| Kibana Auth | Built-in authentication (basic security) | Enable for production |
| Password Policy | Strong password for Kibana admin | Rotate periodically |
| IP Whitelist | Kibana access restricted to IP ranges | Required for production |

**Assessment Checklist:**

- [ ] CAM policies follow least privilege (only required ES actions)
- [ ] Kibana access restricted to specific IP ranges
- [ ] ES cluster password meets complexity requirements
- [ ] No public Kibana access (VPC-only where possible)

### Data Protection

| Control | Implementation | Assessment |
|---------|---------------|------------|
| Encryption at Rest | Disk encryption via CBS | Enabled by default |
| Encryption in Transit | HTTPS/TLS for ES API and Kibana | Configurable |
| Snapshot Encryption | COS SSE for snapshot storage | Verify COS bucket settings |

### Audit Logging

Tencent Cloud ES logs API operations via Cloud Audit (CloudAudit). Enable and review regularly:

| Audit Source | What It Logs | Retention | Action |
|-------------|-------------|-----------|--------|
| CloudAudit | All ES API calls (CreateInstance, DeleteInstance, UpdateInstance, etc.) | 180 days (default) | Enable multi-region trail |
| ES Instance Logs | Cluster runtime events, node join/leave, shard allocation | Configurable | Review regularly via DescribeInstanceLogs |
| Operation History | DescribeInstanceOperations output | Recent 20 entries | Check before/after maintenance |

**Assessment Checklist:**

- [ ] CloudAudit trail enabled (multi-region recommended)
- [ ] DescribeInstanceOperations reviewed periodically for suspicious API calls
- [ ] ES cluster logs retained for minimum 30 days
- [ ] Security group changes logged and reviewed

### Password Rotation Automation

Kibana admin password should be rotated periodically:

```bash
# Note: ES passwords are set at creation time via --Password parameter
# Password rotation may require cluster recreate or console operation
# Best practice: document rotation procedure and track in password manager

# Verify password complexity (check via DescribeInstances)
tccli es DescribeInstances --InstanceIds '["es-xxxxxx"]' | python3 -c "
import sys,json
d=json.load(sys.stdin)
i=d['Response']['InstanceList'][0]
# Note: API does not return password info (security by design)
print('Password: <masked> — verify via console if rotation is needed')
print(f'Basic security enabled: {i.get(\"BasicSecurityType\", 0) == 1}')
"
```

### Security Incident Response Runbook

**Phase 1: Containment (0-15 min)**

```bash
# 1. Identify suspicious activity
tccli es DescribeInstanceOperations --InstanceId "es-xxxxxx" --Offset 0 --Limit 20

# 2. Restrict network access — delegate to qcloud-vpc-ops
# Task: Update security group to block suspicious source IPs
# tccli vpc ModifySecurityGroupPolicys --SecurityGroupId "sg-xxxxxx" ...

# 3. If credentials compromised, rotate API keys
# Generate new TENCENTCLOUD_SECRET_ID and TENCENTCLOUD_SECRET_KEY
```

**Phase 2: Investigation (15-60 min)**

```bash
# 1. Review all recent operations
tccli es DescribeInstanceOperations --InstanceId "es-xxxxxx" --Offset 0 --Limit 100

# 2. Check for unauthorized index access
tccli es DescribeIndexList --InstanceId "es-xxxxxx"

# 3. Review logs
tccli es DescribeInstanceLogs --InstanceId "es-xxxxxx" --LogType 1 --Offset 0 --Limit 50
```

**Phase 3: Recovery (60+ min)**

- Restore from pre-incident snapshot if data was compromised
- Rotate all credentials (API keys, Kibana passwords)
- Review and tighten CAM policies
- Document incident and lessons learned

---

## 4. Cost Pillar (成本)

### Node Right-Sizing

| Strategy | Implementation | Assessment |
|----------|---------------|------------|
| Node type selection | Match node spec to workload | Over-provisioning is common |
| Node count optimization | Minimum 3 nodes for production | Scale based on data growth |
| Disk type selection | CLOUD_SSD vs CLOUD_HSSD | Match IOPS requirements |

**Cost Assessment:**

```bash
# Check current node specs and utilization
tccli monitor GetMonitorData \
  --Namespace QCE/ES \
  --MetricName CpuUsage \
  --Dimensions '[{"Name":"InstanceId","Value":"es-xxxxxx"}]' \
  --StartTime 2026-05-20T00:00:00+08:00 \
  --EndTime 2026-05-21T00:00:00+08:00 \
  --Period 3600
```

**Right-Sizing Checklist:**

- [ ] CPU utilization consistently < 50% → consider smaller node type
- [ ] JVM heap usage > 75% → consider larger node type
- [ ] Disk usage < 40% → consider reducing disk size or cost-optimizing tier
- [ ] Node count sufficient for shard distribution (no yellow status due to replicas)

### Warm/Cold Tiering

| Tier | Storage | Cost | Use Case |
|------|---------|------|----------|
| Hot | CLOUD_SSD/CLOUD_HSSD | Higher | Active indices (recent data) |
| Warm | Standard storage (COS-like) | Lower | Less accessed data |
| Cold/Frozen | Archive storage | Lowest | Compliance, rarely accessed |

**Recommendation:** Use ILM policies to move older indices to warm/cold storage. Delete indices that are no longer needed instead of keeping them on expensive SSD.

### Reserved Instances

For stable, predictable ES workloads, use prepaid billing:

```bash
# Check current billing model
tccli es DescribeInstances --InstanceIds '["es-xxxxxx"]' | python3 -c "
import sys,json
d=json.load(sys.stdin)
i=d['Response']['InstanceList'][0]
print(f'ChargeType: {i.get(\"ChargeType\", \"N/A\")}')
# Note: ES typically postpaid hourly; evaluate prepaid options
"
```

### Idle Cluster Detection

Stopped or underutilized ES clusters still incur storage costs:

```bash
# Find clusters with stopped status (-1)
tccli es DescribeInstances --Region ap-guangzhou | python3 -c "
import sys,json
d=json.load(sys.stdin)
for i in d['Response']['InstanceList']:
    status = i['Status']
    if status == -1:
        print(f'⚠️ STOPPED: {i[\"InstanceName\"]} ({i[\"InstanceId\"]}) — still billed for disk')
    else:
        print(f'  ACTIVE: {i[\"InstanceName\"]} — Nodes={i[\"NodeNum\"]}, Disk={i[\"DiskSize\"]}GB')
"

# Recommendation: Delete stopped clusters not needed within 30 days
# tccli es DeleteInstance --InstanceId "es-xxxxxx"
```

### COS Snapshot Cost Optimization

Snapshots stored in COS incur storage costs. Optimize by:

| Strategy | Savings | Implementation |
|----------|---------|----------------|
| Reduce snapshot frequency | Lower COS writes | Change from hourly to daily for non-critical indices |
| Shorten retention period | Lower COS storage | Delete snapshots > retention window |
| Transition to ARCHIVE | ~70% savings on cold data | Use COS lifecycle to move old snapshots to ARCHIVE |
| Delete redundant snapshots | Direct savings | Manual cleanup of staging/dev cluster snapshots |

```bash
# Count snapshots and estimate cost
tccli es DescribeClusterSnapshot --InstanceId "es-xxxxxx" | python3 -c "
import sys,json
d=json.load(sys.stdin)
snapshots = d['Response'].get('ClusterSnapshotSet', [])
print(f'Total snapshots: {len(snapshots)}')
for s in snapshots:
    print(f'  {s[\"SnapshotName\"]} — Created: {s[\"SnapshotCreateTime\"]}')
"
```

### Disk Type Cost Comparison

| Disk Type | Cost/GB/month (approx) | IOPS | Use Case |
|-----------|----------------------|------|----------|
| CLOUD_PREMIUM | Low | ~500-1000 | Dev/test, warm data, non-production |
| CLOUD_SSD | Medium | ~2000-4000 | General production (recommended default) |
| CLOUD_HSSD | Higher | ~5000-10000 | Write-heavy indexing, high-performance search |
| LOCAL_SSD | Highest | Very high | Latency-sensitive (note: data not persistent) |

**Cost Optimization Recommendation:** Use CLOUD_PREMIUM for dev/test clusters and CLOUD_SSD for general production. Reserve CLOUD_HSSD for write-heavy workloads where IOPS matters.

---

## 5. Efficiency Pillar (效率)

### Index Lifecycle Management (ILM)

| Practice | Benefit |
|----------|---------|
| ILM Policy | Automate index rollover, shrink, force-merge |
| Index Templates | Consistent settings across indices |
| Rollover API | Automatically create new index on size/docs threshold |
| Force Merge | Reduce segment count on read-only indices |

**TODO:** Implement ILM policies for production indices:

```json
PUT _ilm/policy/production_policy
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_size": "50GB",
            "max_age": "30d"
          }
        }
      },
      "warm": {
        "min_age": "30d",
        "actions": {
          "forcemerge": {
            "max_num_segments": 1
          }
        }
      },
      "delete": {
        "min_age": "90d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

### Automation

| Area | Tool | Assessment |
|------|------|------------|
| Create/delete clusters | tccli es | Scripted operations |
| Snapshot backup | tccli es | Schedule via cron/CI |
| Plugin management | tccli es UpdatePlugins | Batch install/remove |
| Dictionary update | tccli es UpdateDictionaries | CI/CD pipeline integration |
| Monitoring | tccli monitor | Delegate to qcloud-monitor-ops |

### Monitoring and Observability

| Practice | Implementation |
|----------|---------------|
| Cluster health monitoring | Cloud Monitor alarm for RED/YELLOW status |
| JVM heap monitoring | Alarm at 75% and 90% thresholds |
| Search latency monitoring | P99 latency tracking |
| Log analysis | ES slow logs review (DescribeInstanceLogs) |

---

## 6. AIOps Integration (智能运维)

### Anomaly Detection Patterns

| Anomaly | Detection Method | Automated Action |
|---------|-----------------|------------------|
| JVM heap spike > 90% | Monitor data + DescribeInstanceLogs | Trigger diagnosis; notify if persistent |
| Search latency p99 > 5s | Monitor SearchQueryLatency trend | Check slow logs; scale if trend continues |
| Bulk rejection rate > 0 | Monitor BulkRejected metric | Log thread pool stats; suggest scaling |
| Disk usage accelerating | Monitor DiskUsed rate of change | Predict full date; proactive scaling |

**Automated Anomaly Detection Script:**

```bash
#!/bin/bash
# ES anomaly detection — run every 15 min via cron
INSTANCE_ID="${1:-es-xxxxxx}"
THRESHOLD_JVM=90
THRESHOLD_DISK=85

# Check JVM heap
JVM=$(tccli monitor GetMonitorData \
  --Namespace QCE/ES --MetricName JvmHeapUsage \
  --Dimensions "[{\"Name\":\"InstanceId\",\"Value\":\"$INSTANCE_ID\"}]" \
  --StartTime "$(date -u -v-15M +%Y-%m-%dT%H:%M:%SZ)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --Period 300 | python3 -c "import sys,json;d=json.load(sys.stdin);v=d['Response']['DataPoints'][0]['Values'];print(max(v) if v else 0)" 2>/dev/null)

if [ "$JVM" -gt "$THRESHOLD_JVM" ]; then
  echo "⚠️ HIGH JVM: ${JVM}% — triggering diagnosis"
  tccli es DiagnoseInstance --InstanceId "$INSTANCE_ID"
fi

# Check disk
DISK=$(tccli monitor GetMonitorData \
  --Namespace QCE/ES --MetricName DiskUsage \
  --Dimensions "[{\"Name\":\"InstanceId\",\"Value\":\"$INSTANCE_ID\"}]" \
  --StartTime "$(date -u -v-15M +%Y-%m-%dT%H:%M:%SZ)" \
  --EndTime "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --Period 300 | python3 -c "import sys,json;d=json.load(sys.stdin);v=d['Response']['DataPoints'][0]['Values'];print(max(v) if v else 0)" 2>/dev/null)

if [ "$DISK" -gt "$THRESHOLD_DISK" ]; then
  echo "⚠️ HIGH DISK: ${DISK}% — consider scaling up"
fi
```

### Self-Healing Runbook

| Condition | Diagnosis | Auto-Remediation | Escalation |
|-----------|-----------|-----------------|------------|
| Node down | DescribeInstances shows Status=-1 or HealthStatus=2 | RestartInstance → wait 5min → re-check | Alert if still RED after restart |
| Yellow health > 1h | DescribeInstances HealthStatus=1 | Check shard allocation → suggest adding nodes | Create Jira ticket |
| Snapshot failure | CreateClusterSnapshot returns error | Retry after 30min | Alert after 3 consecutive failures |

### Log-Metric Correlation

Combine logs and metrics for faster root cause analysis:

```bash
# 1. Detect anomaly (metric)
# 2. Correlate with logs at same timestamp
tccli es DescribeInstanceLogs --InstanceId "es-xxxxxx" --LogType 1 --Offset 0 --Limit 20

# 3. Check operations at that time
tccli es DescribeInstanceOperations --InstanceId "es-xxxxxx" --Offset 0 --Limit 10

# 4. Run diagnosis
tccli es DiagnoseInstance --InstanceId "es-xxxxxx"
tccli es DescribeDiagnose --InstanceId "es-xxxxxx"
```

**Correlation Matrix:**

| Metric Anomaly | Look For In Logs | Likely Root Cause |
|----------------|-----------------|-------------------|
| CPU spike + JVM high | GC logs, indexing slow logs | Heavy indexing or GC thrashing |
| Search latency increase | Search slow logs | Complex query, missing filter |
| Bulk rejections | ES runtime logs | Thread pool queue full |
| Disk usage sudden increase | Index creation logs | Unexpected large index or log flood |

### Capacity Forecasting

```bash
#!/bin/bash
# Simple capacity forecast based on 30-day trend
INSTANCE_ID="${1:-es-xxxxxx}"

# Get current disk and 30-day growth
CURRENT_DISK=$(tccli es DescribeInstances --InstanceIds "[\"$INSTANCE_ID\"]" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['Response']['InstanceList'][0]['DiskSize'])")

# Get disk usage trend (requires Monitor data aggregation)
# Delegate to qcloud-monitor-ops for dashboard with trend analysis

echo "Current disk: ${CURRENT_DISK}GB"
echo "Recommendation: When disk usage exceeds 80%, plan expansion"
echo "Typical growth rate: 5-15% per month for production clusters"
```

---

## 6. Assessment Summary

| Pillar | Score | Key Gaps | Priority |
|--------|-------|----------|----------|
| **可靠性** | ⚠️ Medium | No native multi-AZ; snapshot DR plan must be tested quarterly; shard allocation awareness added | High |
| **安全性** | ✅ Good | VPC isolation by default; Kibana access control, audit logging, password rotation added | Medium |
| **成本** | ✅ Good | Right-sizing, idle cluster detection, COS snapshot cost, disk type comparison added | Medium |
| **效率** | ✅ Good | ILM/automation available; monitoring + CI/CD integration exists | Low |
| **AIOps** | ✅ Good | Anomaly detection script, self-healing runbook, log-metric correlation, capacity forecasting | Medium |

### Getting Started Checklist

- [ ] Enable daily snapshot backups for all production clusters
- [ ] Test snapshot restore process quarterly
- [ ] Review node right-sizing for all clusters
- [ ] Implement ILM policies for index lifecycle management
- [ ] Verify Kibana access is IP-restricted
- [ ] Set up Cloud Monitor alarms for RED health status
- [ ] Document cross-region DR plan
- [ ] Deploy anomaly detection script (15-min cron for JVM/disk checking)
- [ ] Implement self-healing runbook for RED/YELLOW health status
- [ ] Enable CloudAudit trail for security audit logging
- [ ] Review idle/stopped clusters monthly for cost optimization

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-es-ops` |
| `product` | `es` |
| Finding `id` pattern | `es-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

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
  "skill_id": "qcloud-es-ops",
  "product": "es",
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
          "id": "es-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Snapshot backup stale",
          "evidence": "No COS snapshot within RPO window",
          "recommendation": "Configure automated snapshot to COS",
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
      "action": "Configure automated snapshot to COS",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tccli es DescribeInstances --Region ap-guangzhou (SecretKey=<masked>)"
    ],
    "request_ids": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    ]
  },
  "errors": []
}
```
