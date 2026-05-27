# ES Monitoring Guide

Metrics, dashboards, alarms, and observability integration for Tencent Cloud Elasticsearch Service.

---

## 1. Monitoring Namespace

ES uses namespace `QCE/ES` in Tencent Cloud Monitor.

---

## 2. Core Metrics

### Cluster Metrics

| Metric | Unit | Description | Typical Threshold |
|--------|------|-------------|-------------------|
| `ClusterStatus` | Enum | Cluster health (0/1/2 = green/yellow/red) | 0 (green) for production |
| `AvgQps` | Count/s | Average query QPS | Monitor baseline |
| `AvgWriteQps` | Count/s | Average write QPS | Monitor baseline |
| `AvgDocCount` | Count | Total document count | Track growth |
| `AvgStorageSize` | GB | Total cluster storage used | > 80% disk warning |

### Node Metrics

| Metric | Unit | Description | Typical Threshold |
|--------|------|-------------|-------------------|
| `CpuUsage` | % | CPU utilization | > 80% warning, > 90% critical |
| `JvmHeapUsage` | % | JVM heap memory usage | > 75% warning, > 90% critical |
| `SegmentCount` | Count | Number of segments | High count → force-merge needed |
| `DiskUsage` | % | Disk utilization | > 80% warning, > 90% critical |
| `DiskUsed` | GB | Disk used | Compare to disk size |
| `DiskReadIops` | Count/s | Disk read IOPS | Compare to disk type limit |
| `DiskWriteIops` | Count/s | Disk write IOPS | Compare to disk type limit |

### Indexing/Search Metrics

| Metric | Unit | Description | Typical Threshold |
|--------|------|-------------|-------------------|
| `SearchQueryLatency` | ms | Average search latency | > 1000ms warning |
| `FetchLatency` | ms | Average fetch latency | > 500ms warning |
| `IndexingLatency` | ms | Average indexing latency | > 200ms warning |
| `BulkRejected` | Count | Bulk request rejections | > 0 → thread pool issue |
| `SearchRejected` | Count | Search rejections | > 0 → thread pool issue |

---

## 3. Monitor Query (CLI)

### Get Cluster Status

```bash
tccli monitor GetMonitorData \
  --Namespace QCE/ES \
  --MetricName ClusterStatus \
  --Dimensions '[{"Name":"InstanceId","Value":"es-xxxxxx"}]' \
  --StartTime 2026-05-21T00:00:00+08:00 \
  --EndTime 2026-05-21T23:59:59+08:00 \
  --Period 300
```

### Get JVM Heap Usage

```bash
tccli monitor GetMonitorData \
  --Namespace QCE/ES \
  --MetricName JvmHeapUsage \
  --Dimensions '[{"Name":"InstanceId","Value":"es-xxxxxx"}]' \
  --StartTime 2026-05-21T00:00:00+08:00 \
  --EndTime 2026-05-21T23:59:59+08:00 \
  --Period 300
```

### Response Example

```json
{
  "Response": {
    "StartTime": "...", "EndTime": "...", "Period": 300,
    "MetricName": "JvmHeapUsage",
    "DataPoints": [{"Dimensions": [...], "Values": [65.2, 68.1, ...], "Timestamps": [1747785600, ...]}],
    "RequestId": "..."
  }
}
```
<!-- Actual values vary; parse $.Response.DataPoints[0].Values for metrics -->

### Get Search Latency

```bash
tccli monitor GetMonitorData \
  --Namespace QCE/ES \
  --MetricName SearchQueryLatency \
  --Dimensions '[{"Name":"InstanceId","Value":"es-xxxxxx"}]' \
  --StartTime 2026-05-21T00:00:00+08:00 \
  --EndTime 2026-05-21T23:59:59+08:00 \
  --Period 300
```

---

## 4. Recommended Alarm Rules

### Critical Alarms (P0)

| Metric | Condition | Duration | Action |
|--------|-----------|----------|--------|
| `ClusterStatus` | ≥ 1 (yellow) | 5 min | Diagnose cluster health; check shard allocation |
| `ClusterStatus` | = 2 (red) | 1 min | IMMEDIATE: Emergency response, data at risk |
| `JvmHeapUsage` | ≥ 90% | 5 min | Scale up node type or add nodes |
| `DiskUsage` | ≥ 90% | 5 min | Scale up disk or clean old indices |

### Warning Alarms (P1)

| Metric | Condition | Duration | Action |
|--------|-----------|----------|--------|
| `CpuUsage` | ≥ 80% | 10 min | Consider scaling up |
| `JvmHeapUsage` | ≥ 75% | 15 min | Plan for scale-up; check cache settings |
| `DiskUsage` | ≥ 80% | 15 min | Plan cleanup or expansion |
| `SearchQueryLatency` | ≥ 2000ms | 5 min | Check query patterns; optimize indices |

### Informational Alarms (P2)

| Metric | Condition | Duration | Action |
|--------|-----------|----------|--------|
| `BulkRejected` | > 0 | 5 min | Increase bulk queue size; reduce batch size |
| `SearchRejected` | > 0 | 5 min | Increase search thread pool; optimize queries |
| `SegmentCount` | Rapid increase | 30 min | Schedule force-merge during maintenance |

---

## 5. Python SDK Monitor Query

```python
from tencentcloud.common import credential
from tencentcloud.monitor.v20180724 import monitor_client, models

def get_es_metrics(instance_id, metric_name, start_time, end_time):
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = monitor_client.MonitorClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

        req = models.GetMonitorDataRequest()
        req.Namespace = "QCE/ES"
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
data = get_es_metrics(
    "es-xxxxxx",
    "JvmHeapUsage",
    "2026-05-21T00:00:00+08:00",
    "2026-05-21T23:59:59+08:00"
)
print(data)
```

---

## 6. Cloud Monitor Dashboard Setup

### Using CLI

```bash
# Create a dashboard for ES monitoring
tccli monitor CreateDashboard \
  --DashboardName "ES-Production-Overview"

# Add a graph panel (JVM heap)
tccli monitor CreatePolicyGroup \
  --GroupName "ES-Critical-Alerts" \
  --ViewName "ES监控"
```

For full dashboard and alarm configuration, delegate to `qcloud-monitor-ops`.

---

## 7. Log Monitoring

### ES Cluster Logs

```bash
# ES runtime logs
tccli es DescribeInstanceLogs --InstanceId "es-xxxxxx" --LogType 1 --Offset 0 --Limit 20

# Search slow logs (queries > threshold)
tccli es DescribeInstanceLogs --InstanceId "es-xxxxxx" --LogType 2 --Offset 0 --Limit 20

# Indexing slow logs (indexing > threshold)
tccli es DescribeInstanceLogs --InstanceId "es-xxxxxx" --LogType 3 --Offset 0 --Limit 20
```

### Log Analysis Notes

| Log Type | Content | What to Look For |
|----------|---------|------------------|
| ES Logs (Type 1) | General cluster logging | Errors, warnings, node join/leave events |
| Search Slow Log (Type 2) | Queries exceeding slow threshold | High-latency query patterns |
| Indexing Slow Log (Type 3) | Indexing operations exceeding threshold | Heavy indexing patterns |

---

## 8. Observability Best Practices

### Daily Checks

1. **Cluster health:** Verify green status for production clusters
2. **JVM heap:** Check heap usage trend; plan GC optimization if > 75%
3. **Disk usage:** Ensure < 80% disk usage on all nodes
4. **Search latency:** Monitor p99 search latency trends

### Weekly Checks

1. **Index management:** Check for large/old indices; apply ILM policies
2. **Force-merge:** Schedule force-merge on read-only indices > 1GB
3. **Snapshot verification:** Verify recent snapshots completed successfully
4. **Slow log review:** Analyze search/ indexing slow logs for optimization

### Monthly Checks

1. **Version upgrade:** Evaluate if newer ES version should be deployed
2. **Capacity planning:** Review growth trends; plan node scaling
3. **Backup restore test:** Verify snapshot restore process end-to-end
4. **Security audit:** Review access logs and Kibana access patterns
