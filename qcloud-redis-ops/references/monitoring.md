# TencentDB for Redis Monitoring & Alerts

## Overview

Redis monitoring integrates with Tencent Cloud Monitor (TCOP). The monitoring namespace is **QCE/REDIS**.

## Metrics

### Instance-Level Metrics

| Metric Name | Unit | Description | Alert Threshold |
|-------------|------|-------------|-----------------|
| `CpuUsage` | % | Redis CPU utilization | > 80% sustained |
| `MemUsage` | % | Redis memory utilization | > 80% sustained |
| `ConnNum` | Count | Current client connections | > 80% of max connections |
| `CmdNum` | Count/s | Commands per second (QPS) | Sudden drops or spikes |
| `InFlow` | KB/s | Network input traffic | Sustained high |
| `OutFlow` | KB/s | Network output traffic | Sustained high |
| `EvictionNum` | Count | Key eviction count | > 100 in 5min |
| `ExpiredNum` | Count | Key expiry count | Informational |

### Node-Level Metrics (Master-Replica)

| Metric Name | Unit | Description | Alert Threshold |
|-------------|------|-------------|-----------------|
| `MasterSlaveRepl` | Status | Master-replica replication status (0=normal, 1=abnormal) | == 1 |
| `MasterSlaveSwitch` | Count | Failover/switch events | > 0 |

## Query via API

```bash
# Query Redis memory usage
tccli monitor GetMonitorData \
  --Namespace "QCE/REDIS" \
  --MetricName "MemUsage" \
  --Instances.0.Dimensions.0.Name "InstanceId" \
  --Instances.0.Dimensions.0.Value "{{user.instance_id}}" \
  --Period 60 \
  --StartTime "2026-05-21 00:00:00" \
  --EndTime "2026-05-21 23:59:59"
```

## Alert Rule Templates

### Memory Exhaustion Alert

- **Metric:** `MemUsage > 80%`
- **Period:** 5 minutes
- **Threshold:** continuous 3 periods
- **Action:** Notify + recommend UpgradeInstance or adjust eviction policy
- **Severity:** Critical

### Connection Limit Alert

- **Metric:** `ConnNum > 80% of max_connections`
- **Period:** 5 minutes
- **Action:** Notify — investigate connection sources
- **Severity:** Warning

### Replication Failure Alert

- **Metric:** `MasterSlaveRepl == 1`
- **Period:** 1 minute
- **Threshold:** immediate
- **Action:** Immediate SMS notification
- **Severity:** Critical

### QPS Anomaly Alert

- **Metric:** `CmdNum` drops > 50% from baseline OR spikes > 200%
- **Period:** 5 minutes
- **Action:** Notify — investigate application behavior
- **Severity:** Warning

## Recommended Alerts by Severity

| Severity | Metric | Condition | Notification |
|----------|--------|-----------|--------------|
| P0 (Critical) | Replication abnormal | MasterSlaveRepl = 1 | Immediate SMS |
| P0 (Critical) | Memory > 90% | Sustained 5min | Immediate SMS |
| P1 (Warning) | CPU > 80% | Sustained 15min | Slack/Email |
| P1 (Warning) | Connections > 80% of max | Sustained 10min | Email |
| P2 (Info) | High eviction rate | > 100 evictions in 5min | Dashboard alert |