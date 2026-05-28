# Monitoring & Observability

## CLS (Cloud Log Service) Integration

AGSX sandbox tools can stream stdout/stderr to CLS.

### Enable logging on tool creation

```json
{
  "ToolName": "code-tool-prod",
  "LoggingConfig": {
    "Enabled": true,
    "LogsetId": "logset-xxxxxxxx",
    "TopicId": "topic-xxxxxxxx"
  }
}
```

### Recommended CLS queries

```
# All errors in last 1h
* | select * where Level = 'ERROR'

# Sandbox instance startup latency
* | select Timestamp, InstanceId, StartupLatencyMs where StartupLatencyMs > 500

# OOM events
* | select InstanceId, Message where Message like '%OOMKilled%'
```

## Cloud Monitor Metrics

| Metric Namespace | Metric | Statistic | Use |
|---|---|---|---|
| QCE/AGS | InstanceCount | Sum | Track live sandbox count |
| QCE/AGS | StartupLatency | P50/P95/P99 | Cold-start performance |
| QCE/AGS | CpuUtilization | Avg/Max | Right-sizing tool spec |
| QCE/AGS | MemoryUtilization | Avg/Max | Right-sizing tool spec |
| QCE/AGS | InstanceErrors | Sum | Failure rate |

## Alert Recommendations

| Alert | Threshold | Severity |
|---|---|---|
| StartupLatency P95 > 2s | 5m sustained | Warning |
| InstanceErrors / InstanceCount > 5% | 5m | Critical |
| MemoryUtilization Max > 90% | 10m | Warning |
| Account quota usage > 80% | 1h | Warning |

## Audit Logging

All control-plane API calls are recorded in CloudAudit:
https://console.cloud.tencent.com/cloudaudit

Filter: EventSource = ags.tencentcloudapi.com
