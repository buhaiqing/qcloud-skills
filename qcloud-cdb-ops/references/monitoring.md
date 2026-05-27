# CDB Monitoring Guide

Metrics, dashboards, alarms, and observability integration for Tencent Cloud TencentDB for MySQL.

---

## 1. Monitoring Namespace

CDB uses namespace `QCE/CDB` in Tencent Cloud Monitor.

---

## 2. Core Metrics

### Resource Metrics

| Metric | Unit | Description | Typical Threshold |
|--------|------|-------------|-------------------|
| `CpuUseRate` | % | CPU utilization | > 80% warning, > 90% critical |
| `MemoryUseRate` | % | Memory utilization | > 80% warning, > 90% critical |
| `VolumeRate` | % | Disk utilization | > 80% warning, > 95% critical |
| `RealCapacity` | MB | Data disk used | Track growth trend |
| `Capacity` | MB | Total disk capacity | Compare to `RealCapacity` |

### Connection and Thread Metrics

| Metric | Unit | Description | Typical Threshold |
|--------|------|-------------|-------------------|
| `ConnectionUseRate` | % | Connection utilization | > 80% warning |
| `MaxConnections` | Count | Max connections configured | Check against instance spec |
| `ThreadsConnected` | Count | Active connections | Compare to `MaxConnections` |
| `ThreadsRunning` | Count | Currently executing threads | High → query congestion |

### Query Metrics

| Metric | Unit | Description | Typical Threshold |
|--------|------|-------------|-------------------|
| `Queries` | Count/s | Query rate per second | Monitor baseline |
| `SlowQueries` | Count | Slow query count per period | > 0 → investigate |
| `SelectScan` | Count/s | Full table scan rate | > 0 → missing indexes |
| `Questions` | Count/s | Total command rate | Monitor baseline |

### Replication Metrics

| Metric | Unit | Description | Typical Threshold |
|--------|------|-------------|-------------------|
| `MasterSlaveSyncDistance` | MB | Replication lag (in MB) | > 100MB warning |
| `SecondsBehindMaster` | Seconds | Replication lag (in seconds) | > 30s warning, > 120s critical |

### IOPS Metrics

| Metric | Unit | Description | Typical Threshold |
|--------|------|-------------|-------------------|
| `IOPS` | Count/s | IO operations per second | Compare to disk IOPS limit |
| `IOWaitTime` | ms | I/O wait time | > 20ms warning |

### Error Log Metrics

| Metric | Unit | Description | Typical Threshold |
|--------|------|-------------|-------------------|
| `ErrorLogCount` | Count | Error log entries per period | > 0 → investigate |

---

## 3. Monitor Query (CLI)

### Get CPU Usage

```bash
tccli monitor GetMonitorData \
  --Namespace QCE/CDB \
  --MetricName CpuUseRate \
  --Dimensions '[{"Name":"InstanceId","Value":"cdb-xxxxxx"}]' \
  --StartTime 2026-05-21T00:00:00+08:00 \
  --EndTime 2026-05-21T23:59:59+08:00 \
  --Period 300
```

### Get Connection Usage

```bash
tccli monitor GetMonitorData \
  --Namespace QCE/CDB \
  --MetricName ConnectionUseRate \
  --Dimensions '[{"Name":"InstanceId","Value":"cdb-xxxxxx"}]' \
  --StartTime 2026-05-21T00:00:00+08:00 \
  --EndTime 2026-05-21T23:59:59+08:00 \
  --Period 300
```

### Response Example

```json
{
  "Response": {
    "StartTime": "...", "EndTime": "...", "Period": 300,
    "MetricName": "CpuUseRate",
    "DataPoints": [{"Dimensions": [...], "Values": [45.2, 62.1, ...], "Timestamps": [1747785600, ...]}],
    "RequestId": "..."
  }
}
```
<!-- Actual values vary; parse $.Response.DataPoints[0].Values for metrics -->

### Get Replication Lag

```bash
tccli monitor GetMonitorData \
  --Namespace QCE/CDB \
  --MetricName SecondsBehindMaster \
  --Dimensions '[{"Name":"InstanceId","Value":"cdb-xxxxxx"}]' \
  --StartTime 2026-05-21T00:00:00+08:00 \
  --EndTime 2026-05-21T23:59:59+08:00 \
  --Period 60
```

### Get Slow Query Count

```bash
tccli monitor GetMonitorData \
  --Namespace QCE/CDB \
  --MetricName SlowQueries \
  --Dimensions '[{"Name":"InstanceId","Value":"cdb-xxxxxx"}]' \
  --StartTime 2026-05-21T00:00:00+08:00 \
  --EndTime 2026-05-21T23:59:59+08:00 \
  --Period 300
```

---

## 4. Recommended Alarm Rules

### Critical Alarms (P0)

| Metric | Condition | Duration | Action |
|--------|-----------|----------|--------|
| `CpuUseRate` | ≥ 90% | 5 min | Scale up instance; identify CPU-intensive queries |
| `VolumeRate` | ≥ 95% | 5 min | IMMEDIATE: Scale up disk or risk write failures |
| `SecondsBehindMaster` | ≥ 120s | 5 min | Check replica health; network/infrastructure issue |

### Warning Alarms (P1)

| Metric | Condition | Duration | Action |
|--------|-----------|----------|--------|
| `CpuUseRate` | ≥ 80% | 10 min | Plan scale-up; optimize slow queries |
| `MemoryUseRate` | ≥ 80% | 10 min | Check for memory leak; plan scale-up |
| `VolumeRate` | ≥ 80% | 15 min | Plan disk expansion or cleanup |
| `ConnectionUseRate` | ≥ 80% | 10 min | Check connection pool; increase `max_connections` |
| `SlowQueries` | ≥ 50 | 5 min | Analyze slow log; optimize queries |
| `SecondsBehindMaster` | ≥ 30s | 5 min | Check replica; reduce master load |

### Informational Alarms (P2)

| Metric | Condition | Duration | Action |
|--------|-----------|----------|--------|
| `IOPS` | Near limit | 30 min | Consider upgrade to higher IOPS spec |
| `SelectScan` | Increasing trend | 1 hour | Check for missing indexes |
| `ErrorLogCount` | > 0 | 30 min | Review error log for patterns |

---

## 5. Python SDK Monitor Query

```python
from tencentcloud.common import credential
from tencentcloud.monitor.v20180724 import monitor_client, models

def get_cdb_metrics(instance_id, metric_name, start_time, end_time):
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = monitor_client.MonitorClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.GetMonitorDataRequest()
        req.Namespace = "QCE/CDB"
        req.MetricName = metric_name
        req.Dimensions = [{"Name": "InstanceId", "Value": instance_id}]
        req.StartTime = start_time
        req.EndTime = end_time
        req.Period = 300

        resp = client.GetMonitorData(req)
        return resp.to_json_string()
    except Exception as err:
        print(f"[ERROR] {err}")

# Usage
data = get_cdb_metrics(
    "cdb-xxxxxx",
    "CpuUseRate",
    "2026-05-21T00:00:00+08:00",
    "2026-05-21T23:59:59+08:00"
)
print(data)
```

---

## 6. Slow Query Log Analysis

### Query Slow Log via CLI

```bash
# Get recent slow queries
tccli cdb DescribeSlowLogData \
  --InstanceId "cdb-xxxxxx" \
  --StartTime "2026-05-20 00:00:00" \
  --EndTime "2026-05-21 00:00:00" \
  --Limit 20 \
  --OrderBy "QueryTime" \
  --Order "DESC"

# Get slow log summary
tccli cdb DescribeSlowLogs --InstanceId "cdb-xxxxxx" --Limit 10
```

### Error Log via CLI

```bash
tccli cdb DescribeErrorLogData \
  --InstanceId "cdb-xxxxxx" \
  --StartTime "2026-05-20 00:00:00" \
  --EndTime "2026-05-21 00:00:00" \
  --Limit 20
```

---

## 7. Observability Best Practices

### Daily Checks

1. **CPU and memory:** Verify < 80% for sustained periods
2. **Connection count:** Ensure connections < 80% of max
3. **Slow queries:** Review and optimize any slow queries
4. **Replication lag:** Ensure lag is < 30s for DR instances

### Weekly Checks

1. **Backup verification:** Confirm automatic backups completed successfully
2. **Disk growth:** Track `RealCapacity` trend for capacity planning
3. **Error logs:** Review for recurring error patterns
4. **Parameter review:** Check `max_connections`, `innodb_buffer_pool_size` appropriateness

### Monthly Checks

1. **Performance baseline:** Compare current metrics against 30-day baseline
2. **Version upgrade:** Evaluate if newer MySQL version should be deployed
3. **Cost analysis:** Review prepaid vs postpaid cost optimization opportunities
4. **Security audit:** Review SSL status, account privileges, and access patterns

---

## 8. Cloud Monitor Dashboard Setup

For full dashboard and alarm configuration, delegate to `qcloud-monitor-ops`.

```bash
# Create dashboard
tccli monitor CreateDashboard --DashboardName "CDB-Production-Overview"

# Create alarm policy
tccli monitor CreateAlarmPolicy \
  --PolicyName "CDB-CPU-High" \
  --PolicyType "CDB" \
  --Condition '{"MetricName":"CpuUseRate","Operator":"gt","Value":80,"Period":300,"ContinuePeriod":2}'
```
