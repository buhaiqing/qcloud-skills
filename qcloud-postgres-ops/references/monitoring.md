# Monitoring & Alerts — TencentDB for PostgreSQL

## Key Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| CPU利用率 | % | Instance CPU usage |
| 内存利用率 | % | Instance memory usage |
| 磁盘利用率 | % | Disk space usage |
| 连接数 | count | Active connections |
| QPS | ops/s | Queries per second |
| TPS | ops/s | Transactions per second |
| 慢查询数 | count/min | Slow queries per minute |
| 备机复制延迟 | seconds | Standby replication lag |
| IOPS | ops/s | I/O operations per second |
| 网络入流量 | bytes/s | Inbound traffic |
| 网络出流量 | bytes/s | Outbound traffic |

## Default Alarms

| Alarm Name | Threshold | Severity | Action |
|-----------|-----------|----------|--------|
| CPU > 90% | ≥90% for 5min | Critical | Scale up or optimize queries |
| Memory > 85% | ≥85% for 5min | Warning | Consider memory upgrade |
| Disk > 85% | ≥85% | Warning | Clean data or expand storage |
| Connection > 80% | ≥80% of max | Warning | Increase max_connections |
| Replication lag > 60s | >60s | Critical | Check network between nodes |

## Dashboards

- **Cloud Monitor Console:** https://console.cloud.tencent.com/monitor
- **Default dashboard:** Basic metrics (CPU, memory, disk, connections)
- **Custom dashboard:** Add slow queries, replication lag, IOPS

## Anomaly Patterns

| Pattern | Symptom | Likely Cause |
|---------|---------|-------------|
| CPU spike | CPU ≥ 90% suddenly | Bad query, missing index, autovacuum |
| Memory leak | Memory steadily increases | Unclosed connections, shared_buffers too high |
| Disk full | Disk ≥ 95% | WAL not purged, table bloat, insufficient retention |
| Connection storm | Connections max out | Application bug, connection pool leak |
| Replication lag | Standby behind ≥ 300s | Network issue, heavy write load on primary |

## AIOps Anomaly Correlation Matrix

| Symptom Cluster | Correlated Metrics | Diagnosis | Suggested Action |
|----------------|-------------------|-----------|------------------|
| (CPU ↑, SlowQ ↑, IOPS ↑) | All three spike together | Query performance regression | Add index or rewrite query |
| (CPU ↑, SlowQ normal, IOPS normal) | Only CPU spikes | Autovacuum or background process | Adjust autovacuum config |
| (Mem ↑, Connections ↑, SlowQ ↑) | Memory + connections rising together | Connection leak app-side | Kill idle connections; patch app |
| (Disk ↑, WAL ↑, RepLag ↑) | Disk growing with replication lag | Standby can't keep up | Check standby network/spec |
| (Connections max, QPS dropping) | Connection pool exhausted | Application pool config issue | Increase pool size or restart |
| (Disk ↑ steady, CPU/Mem normal) | Linear disk growth over weeks | Data growth, WAL accumulation | Archive old data; review retention |

## Using tccli to Query Metrics

```bash
# Get monitoring data via Cloud Monitor
tccli monitor GetMonitorData \
  --Namespace "QCE/POSTGRES" \
  --MetricName "cpu_usage" \
  --Period 300 \
  --StartTime "2026-05-31T00:00:00+08:00" \
  --EndTime "2026-05-31T12:00:00+08:00" \
  --Instances '[{"Dimensions":[{"Name":"DBInstanceId","Value":"postgres-xxxxx"}]}]'
```

## Cost & Performance Metrics

| Metric | Consideration |
|--------|--------------|
| IOPS pricing | Higher IOPS tiers cost more; match to workload |
| Backup storage | Free up to 50% of storage; excess is billed |
| Data transfer | Cross-region data transfer incurs costs |
| Read replicas | Billed separately; useful for read-heavy workloads |
