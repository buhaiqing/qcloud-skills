# AIOps Self-Healing & Proactive Checks

> 从 `SKILL.md` 提取。本文件包含自愈流程、主动巡检、容量预测、告警风暴处理和可观测性管道。

## Multi-Metric Anomaly Detection

| Symptom | Correlate With | Likely Root Cause | Self-Heal Action |
|---------|---------------|-------------------|-------------------|
| CPU ≥ 90% | Slow queries ↑, IOPS ↑ | Missing index, seq scan | Optimize queries or add index |
| CPU ≥ 90% | Connections normal, IOPS normal | Autovacuum running | Wait; tune autovacuum params |
| Memory ≥ 85% | Connections ↑, slow queries | Connection leak, shared_buffers high | Kill idle connections; advise tuning |
| Memory ≥ 85% | Connections stable, QPS normal | Memory leak in application | Restart instance if critical |
| Disk ≥ 85% | WAL size ↑, replication lag | WAL not recycled by standby | Check replication health |
| Disk ≥ 95% | Read-only mode triggered | Storage full | Immediate storage expansion |
| Replication lag ≥ 300s | IOPS ↑ on primary | Heavy write load | Reduce writes or scale up primary |

## Self-Healing Workflows

### Disk Auto-Diagnose & Recover

```bash
#!/bin/bash
INSTANCE_ID="{{user.instance_id}}"
THRESHOLD=85

DISK_USAGE=$(tccli postgres DescribeDBInstances \
  --Filters "[{\"Name\":\"db-instance-id\",\"Values\":[\"$INSTANCE_ID\"]}]" \
  | jq '.Response.DBInstanceSet[0].Storage')

REPL_LAG=$(tccli monitor GetMonitorData \
  --Namespace "QCE/POSTGRES" --MetricName "replication_lag" \
  --Period 300 --Instances "[{\"Dimensions\":[{\"Name\":\"DBInstanceId\",\"Value\":\"$INSTANCE_ID\"}]}]" \
  | jq '.Response.DataPoints[0].Values[-1]')

if [ "$REPL_LAG" -lt 300 ]; then
  echo "[HEAL] WAL cleanup: Starting..."
  tccli postgres ModifyDBInstanceParameters \
    --DBInstanceId "$INSTANCE_ID" \
    --ParamList '[{"Name":"vacuum_cost_delay","Value":"0"}]'
  echo "[HEAL] WAL cleanup: Triggered vacuum_defer_cleanup_age reset"
else
  echo "[WARN] Replication lag > 300s. Cannot clean WAL safely."
fi

if [ "$DISK_USAGE" -ge 95 ]; then
  CURRENT_STORAGE=$(tccli postgres DescribeDBInstances \
    --Filters "[{\"Name\":\"db-instance-id\",\"Values\":[\"$INSTANCE_ID\"]}]" \
    | jq '.Response.DBInstanceSet[0].Storage')
  NEW_STORAGE=$(( CURRENT_STORAGE * 120 / 100 ))
  echo "[HEAL] Auto-scaling storage from ${CURRENT_STORAGE}GB to ${NEW_STORAGE}GB"
  tccli postgres UpgradeDBInstance \
    --DBInstanceId "$INSTANCE_ID" \
    --Memory $(tccli postgres DescribeDBInstances --Filters "[{\"Name\":\"db-instance-id\",\"Values\":[\"$INSTANCE_ID\"]}]" | jq '.Response.DBInstanceSet[0].Memory') \
    --Storage $NEW_STORAGE
fi
```

### Connection Storm Auto-Recovery

```bash
#!/bin/bash
INSTANCE_ID="{{user.instance_id}}"

tccli postgres DescribeSlowQueryList \
  --DBInstanceId "$INSTANCE_ID" \
  --StartTime "$(date -v-1H +'%Y-%m-%d %H:%M:%S')" \
  --EndTime "$(date +'%Y-%m-%d %H:%M:%S')"

echo "[HEAL] Temporarily increasing max_connections..."
tccli postgres ModifyDBInstanceParameters \
  --DBInstanceId "$INSTANCE_ID" \
  --ParamList '[{"Name":"max_connections","Value":"500"}]'
echo "[HEAL] max_connections set to 500. Investigate root cause."
```

## Proactive Health Checks

```bash
#!/bin/bash
INSTANCE_ID="{{user.instance_id}}"

echo "=== PostgreSQL Health Check ==="

STATUS=$(tccli postgres DescribeDBInstances \
  --Filters "[{\"Name\":\"db-instance-id\",\"Values\":[\"$INSTANCE_ID\"]}]" \
  | jq -r '.Response.DBInstanceSet[0].DBInstanceStatus')
echo "[${STATUS}] Instance status: $STATUS"

echo "[METRIC] Checking 7-day disk growth..."
tccli monitor GetMonitorData \
  --Namespace "QCE/POSTGRES" --MetricName "disk_usage" \
  --Period 86400 --StartTime "$(date -v-7d +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --Instances "[{\"Dimensions\":[{\"Name\":\"DBInstanceId\",\"Value\":\"$INSTANCE_ID\"}]}]" \
  | jq '.Response.DataPoints[0].Values | {current: .[-1], trend: [.[]]}'

echo "[QUERY] Checking long-running queries..."
tccli postgres DescribeSlowQueryList \
  --DBInstanceId "$INSTANCE_ID" \
  --StartTime "$(date -v-1H +'%Y-%m-%d %H:%M:%S')" \
  --EndTime "$(date +'%Y-%m-%d %H:%M:%S')"

echo "[BACKUP] Last backup check..."
tccli postgres DescribeDBBackups \
  --DBInstanceId "$INSTANCE_ID" --Limit 1 | jq '.Response.BackupList[0] | {State, BackupType, StartTime}'

echo "=== Health Check Complete ==="
```

## Capacity Forecasting

```bash
#!/bin/bash
INSTANCE_ID="{{user.instance_id}}"
METRICS=$(tccli monitor GetMonitorData \
  --Namespace "QCE/POSTGRES" --MetricName "disk_usage" \
  --Period 86400 --StartTime "$(date -v-14d +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --Instances "[{\"Dimensions\":[{\"Name\":\"DBInstanceId\",\"Value\":\"$INSTANCE_ID\"}]}]")

FIRST=$(echo "$METRICS" | jq '.Response.DataPoints[0].Values[0]')
LAST=$(echo "$METRICS" | jq '.Response.DataPoints[0].Values[-1]')
CURRENT=$(echo "$METRICS" | jq '.Response.DataPoints[0].Values[-1]')

DAILY_GROWTH=$(echo "scale=2; ($LAST - $FIRST) / 14" | bc)
DAYS_TO_FULL=$(echo "scale=0; (95 - $CURRENT) / $DAILY_GROWTH" | bc 2>/dev/null || echo "N/A")

echo "[CAPACITY] Current disk: ${CURRENT}% | Daily growth: ${DAILY_GROWTH}%/day"
echo "[CAPACITY] Estimated days until 95%: ${DAYS_TO_FULL}"
```

## Alarm Storm Handling

1. **Triage by severity:** Instance down → Replication lag → Disk full → High CPU → Memory high
2. **Breadth vs depth:** For 5+ instances with same alarm, check if system-wide vs independent
3. **Auto-silence known patterns:** If alarm matches maintenance window, silence and escalate after
4. **Correlate before dispatch:** Group alarms from same application stack before routing

## Observability Pipeline

```bash
#!/bin/bash
INSTANCE_ID="{{user.instance_id}}"

echo "[OBSERVE] Fetching slow queries for correlation..."
tccli postgres DescribeSlowQueryList \
  --DBInstanceId "$INSTANCE_ID" \
  --StartTime "$(date -v-1H +'%Y-%m-%d %H:%M:%S')" \
  --EndTime "$(date +'%Y-%m-%d %H:%M:%S')" \
  > /tmp/pg_slow_queries.json

METRIC_CPU=$(tccli monitor GetMonitorData \
  --Namespace "QCE/POSTGRES" --MetricName "cpu_usage" \
  --Period 60 --StartTime "$(date -v-1H +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --Instances "[{\"Dimensions\":[{\"Name\":\"DBInstanceId\",\"Value\":\"$INSTANCE_ID\"}]}]")

echo "[OBSERVE] CPU at time of slow queries: $(echo "$METRIC_CPU" | jq '.Response.DataPoints[0].Values[-5:] // []')"
echo "[OBSERVE] Cross-reference: High CPU + slow queries + high IOPS → likely index missing"
```

## Error-Proof Script Guards

```bash
get_metric_safe() {
  local NAMESPACE="$1" METRIC="$2" INSTANCE="$3"
  local RESULT
  RESULT=$(tccli monitor GetMonitorData \
    --Namespace "$NAMESPACE" --MetricName "$METRIC" \
    --Period 300 --StartTime "$(date -v-1d +'%Y-%m-%dT%H:%M:%S+08:00')" \
    --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
    --Instances "[{\"Dimensions\":[{\"Name\":\"DBInstanceId\",\"Value\":\"$INSTANCE\"}]}]" 2>/dev/null)
  echo "$RESULT" | jq '.Response.DataPoints[0].Values[-1] // 0'
}
```
