# CVM Monitoring Guide

Metrics, dashboards, alarms, and observability integration for CVM.

---

## 1. Monitoring Namespace

CVM uses namespace `QCE/CVM` in Tencent Cloud Monitor.

---

## 2. Core Metrics

### CPU Metrics

| Metric | Unit | Typical Threshold |
|--------|------|------------------|
| `CPUUsage` | % | > 80% warning, > 90% critical |
| `CPUUseRate` | % (deprecated) | Same |

### Memory Metrics

| Metric | Unit | Typical Threshold |
|--------|------|------------------|
| `MemUsage` | % | > 80% warning, > 90% critical |

### Disk Metrics

| Metric | Unit | Typical Threshold |
|--------|------|------------------|
| `DiskUsage` | % (agent required) | > 80% warning, > 95% critical |
| `DiskRead` | KB/s | Monitor baseline |
| `DiskWrite` | KB/s | Monitor baseline |

### Network Metrics

| Metric | Unit | Typical Threshold |
|--------|------|------------------|
| `NetworkIn` | Mbps | Compare to cap |
| `NetworkOut` | Mbps | Compare to cap |
| `TrafficIn` | MB | Cost tracking |
| `TrafficOut` | MB | Cost tracking |

### Status Metrics

| Metric | Unit |
|--------|------|
| `Status` | Enum (agent required) |

---

## 3. Monitor Query (CLI)

### Get CPU Usage

```bash
tccli monitor GetMonitorData \
  --Namespace QCE/CVM \
  --MetricName CPUUsage \
  --Dimensions '[{"Name":"InstanceId","Value":"ins-xxx"}]' \
  --StartTime 2026-05-21T00:00:00+08:00 \
  --EndTime 2026-05-21T23:59:59+08:00 \
  --Period 300
```

### Response

```json
{
  "Response": {
    "StartTime": "2026-05-21T00:00:00+08:00",
    "EndTime": "2026-05-21T23:59:59+08:00",
    "Period": 300,
    "MetricName": "CPUUsage",
    "DataPoints": [{"Dimensions": [...], "Values": [...], "Timestamps": [...]}],
    "RequestId": "..."
  }
}
```
<!-- Actual values vary; parse $.Response.DataPoints[0].Values for metrics -->

---

## 4. SDK Monitoring

```python
from tencentcloud.monitor import monitor_client, models
from datetime import datetime, timedelta

def get_cpu_usage(client, instance_id, hours=24):
    # Get CPU usage for last N hours
    req = models.GetMonitorDataRequest()
    req.Namespace = "QCE/CVM"
    req.MetricName = "CPUUsage"
    req.Dimensions = [{"Name": "InstanceId", "Value": instance_id}]
    
    # Calculate time range
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    req.StartTime = start_time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    req.EndTime = end_time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    req.Period = 300
    
    resp = client.GetMonitorData(req)
    
    values = resp.DataPoints[0].Values if resp.DataPoints else []
    max_value = max(v["Value"] for v in values) if values else 0
    avg_value = sum(v["Value"] for v in values) / len(values) if values else 0
    
    return {
        "max_cpu": max_value,
        "avg_cpu": avg_value,
        "samples": len(values)
    }
```

---

## 5. Alarm Configuration

### Create Alarm Policy

```bash
# Create alarm policy for CPU
tccli monitor CreateAlarmPolicy \
  --Module monitor \
  --PolicyName "CVM-CPU-High" \
  --Namespace QCE/CVM \
  --Conditions '[{"MetricName":"CPUUsage","CalcType":"gt","CalcValue":"90","ContinueTime":60}]' \
  --NoticeIds "[\"notice-xxx\"]" \
  --ProjectId 0
```

### Alarm Condition Parameters

| Parameter | Description |
|-----------|-------------|
| `MetricName` | Metric to monitor |
| `CalcType` | `gt` (greater), `lt` (less), `gte` (greater or equal) |
| `CalcValue` | Threshold value |
| `ContinueTime` | Duration before alert (seconds) |

### Notification Channels

| Channel | Config |
|---------|--------|
| SMS | Add phone number |
| Email | Add email address |
| WeChat | Enterprise WeChat webhook |
| HTTP | Webhook callback URL |

---

## 6. Dashboard Configuration

### Grafana Integration

Tencent Cloud supports Grafana integration:

1. Install Grafana
2. Add Tencent Cloud Monitor data source plugin
3. Configure API credentials
4. Create dashboard with CVM metrics

### Dashboard Panels

| Panel | Metrics | Purpose |
|-------|---------|---------|
| CPU Overview | `CPUUsage` per instance | Identify overloaded instances |
| Memory Overview | `MemUsage` per instance | Memory pressure detection |
| Network Overview | `NetworkIn`, `NetworkOut` | Bandwidth utilization |
| Disk Overview | `DiskUsage` | Storage capacity tracking |

---

## 7. Performance Analysis

### CPU Analysis

```python
def analyze_cpu_trend(client, instance_id):
    # Analyze CPU trend for optimization
    data = get_cpu_usage(client, instance_id, hours=168)  # 7 days
    
    if data["avg_cpu"] < 20:
        return {
            "recommendation": "Downsize",
            "reason": "Average CPU under 20%, consider smaller instance type",
            "current_avg": data["avg_cpu"]
        }
    elif data["max_cpu"] > 90 and data["avg_cpu"] > 60:
        return {
            "recommendation": "Upsize",
            "reason": "CPU frequently peaks, consider larger instance or scale out",
            "current_max": data["max_cpu"],
            "current_avg": data["avg_cpu"]
        }
    else:
        return {
            "recommendation": "Normal",
            "reason": "CPU utilization within healthy range"
        }
```

### Cost Optimization Metrics

| Metric | Threshold | Recommendation |
|--------|-----------|----------------|
| Avg CPU < 20% for 7 days | Downsizing candidate | Reduce instance type |
| Avg Memory < 30% for 7 days | Memory waste | Reduce memory config |
| Network throughput < 10% of cap | Network over-provisioned | Lower bandwidth package |
| Instance stopped > 24h | Idle instance | Delete or schedule auto-stop |

---

## 8. Anomaly Detection

### Baseline Establishment

1. Collect 14 days of metrics
2. Calculate average and standard deviation
3. Set dynamic thresholds (avg + 2σ)

### Anomaly Patterns

| Pattern | Detection | Action |
|---------|-----------|--------|
| CPU spike (> 2σ from avg) | Monitor anomaly | Investigate application |
| Memory creep (gradual increase) | Trend analysis | Check for memory leak |
| Disk usage sudden drop | Monitor anomaly | Check for data deletion |
| Network spike | Monitor anomaly | Check for DDoS or data transfer |

---

## 9. Integration with AIOps

For skills implementing AIOps patterns, see [AIOps Best Practices](../qcloud-skill-generator/references/aiops-best-practices.md).

### Multi-Metric Correlation

```python
def correlate_metrics(cpu_data, mem_data, disk_data):
    # Correlate metrics for root cause analysis
    anomalies = []
    
    # High CPU + High Memory → Application issue
    if cpu_data["max"] > 90 and mem_data["max"] > 90:
        anomalies.append({
            "type": "ApplicationPressure",
            "severity": "HIGH",
            "description": "CPU and Memory both high",
            "recommendation": "Scale out or optimize application"
        })
    
    # High Disk + Normal CPU/Mem → Storage issue
    if disk_data["max"] > 95 and cpu_data["max"] < 50:
        anomalies.append({
            "type": "StoragePressure",
            "severity": "HIGH",
            "description": "Disk near capacity, CPU normal",
            "recommendation": "Resize disk or cleanup data"
        })
    
    return anomalies
```

---

## 10. Monitoring Checklist

### Daily Checks

- [ ] Check all instances in `RUNNING` state
- [ ] Review CPU usage > 90% alerts
- [ ] Review disk usage > 80% alerts
- [ ] Check network bandwidth utilization

### Weekly Checks

- [ ] Analyze CPU/Memory trends (7-day average)
- [ ] Identify downsize candidates (avg CPU < 20%)
- [ ] Identify upsize candidates (max CPU > 90%)
- [ ] Review snapshot backup status

### Monthly Checks

- [ ] Compare month-over-month resource usage
- [ ] Review cost trends and optimization opportunities
- [ ] Audit security group rules
- [ ] Check instance lifecycle and deletion candidates

---

## References

- [Cloud Monitor API](https://cloud.tencent.com/document/api/248)
- [CVM Metrics](https://cloud.tencent.com/document/product/248)
- [Alarm Configuration](https://cloud.tencent.com/document/product/248)