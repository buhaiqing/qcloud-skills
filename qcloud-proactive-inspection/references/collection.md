# Metric Collection — Proactive Inspection

## Core Metrics per Product

### CVM Metrics
```bash
# CPU usage
tccli monitor DescribeBaseMetrics \
  --MetricName CPUUsage --Namespace QCE/CVM \
  --Dimensions '[{"Name":"InstanceId","Value":"ins-xxxx"}]' \
  --Period 300 --StartTime "2026-05-21 00:00:00" --EndTime "2026-05-21 23:59:59"

# Memory usage
tccli monitor DescribeBaseMetrics \
  --MetricName MemUsage --Namespace QCE/CVM \
  --Dimensions '[{"Name":"InstanceId","Value":"ins-xxxx"}]'

# Disk usage
tccli monitor DescribeBaseMetrics \
  --MetricName CvmDiskUsage --Namespace QCE/CVM \
  --Dimensions '[{"Name":"InstanceId","Value":"ins-xxxx"}]'
```

### Redis Metrics
| Metric | Namespace | MetricName |
|--------|-----------|------------|
| CPU utilization | QCE/REDIS | InstanceCpuUtil |
| Memory utilization | QCE/REDIS | InstanceMemUsage |
| Connections | QCE/REDIS | Connections |
| QPS | QCE/REDIS | RealtimeQps |

### CDB Metrics
| Metric | Namespace | MetricName |
|--------|-----------|------------|
| CPU utilization | QCE/CDB | CpuUseRate |
| Memory utilization | QCE/CDB | MemoryUseRate |
| Connections | QCE/CDB | Connection |
| IOPS | QCE/CDB | IOPS |

## Batch Collection Pattern
```python
def collect_metrics(client, metrics, resource_ids, period=300, time_range='1h'):
    results = []
    for resource_id in resource_ids:
        for metric in metrics:
            resp = client.DescribeBaseMetrics(
                Namespace=metric['namespace'],
                MetricName=metric['name'],
                Dimensions=[metric['dimension_name'], resource_id],
                Period=period,
                StartTime=metric['start_time'],
                EndTime=metric['end_time']
            )
            results.append({
                'resource_id': resource_id,
                'metric': metric['name'],
                'datapoints': [d.values for d in resp.DataPoints]
            })
    return results
```

## Rate Limit Handling
| Limit | Strategy |
|-------|----------|
| 20 req/s per product | Batch metrics, use DescribeBaseMetrics multi-metric |
| Exceeded Quota | Retry with exponential backoff (1s, 2s, 4s, max 3 retries) |
| Partial data | Proceed with available data, flag gaps in report |
