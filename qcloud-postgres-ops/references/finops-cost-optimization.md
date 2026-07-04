# FinOps Cost Optimization

> 从 `SKILL.md` 提取。本文件包含闲置检测、成本对比、规格优化、成本报告和异常检测。

## Idle Instance Detection

```bash
#!/bin/bash
echo "=== Idle Instance Detection ==="

tccli postgres DescribeDBInstances --Limit 100 \
  | jq -r '.Response.DBInstanceSet[] | select(.DBInstanceStatus == "running") | .DBInstanceId' \
  | while read INSTANCE_ID; do
    AVG_CPU=$(tccli monitor GetMonitorData \
      --Namespace "QCE/POSTGRES" --MetricName "cpu_usage" \
      --Period 86400 --StartTime "$(date -v-7d +'%Y-%m-%dT%H:%M:%S+08:00')" \
      --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
      --Instances "[{\"Dimensions\":[{\"Name\":\"DBInstanceId\",\"Value\":\"$INSTANCE_ID\"}]}]" \
      | jq '.Response.DataPoints[0].Values | add / length')
    
    if [ "${AVG_CPU%.*}" -lt 5 ]; then
      MEM=$(tccli postgres DescribeDBInstances \
        --Filters "[{\"Name\":\"db-instance-id\",\"Values\":[\"$INSTANCE_ID\"]}]" \
        | jq '.Response.DBInstanceSet[0].Memory')
      echo "[IDLE] $INSTANCE_ID (${MEM}GB, avg CPU=${AVG_CPU}%) — consider downsizing or terminating"
    fi
  done
```

**Action Matrix:**

| Avg CPU | Recommended Action | Monthly Savings (est.) |
|---------|-------------------|----------------------|
| < 5% for 7 days | Downsize to lower spec or terminate | 30-60% |
| < 1% for 30 days | Terminate with final backup | 100% |
| Only accessed during business hours | Switch to postpaid + schedule start/stop | 50-70% |

## Pre-Creation Cost Comparison

```bash
#!/bin/bash
MEMORY=4
STORAGE=100
PERIOD=12

echo "=== Cost Comparison for ${MEMORY}GB / ${STORAGE}GB PostgreSQL ==="

PREPAID=$(tccli postgres InquiryPriceCreateDBInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --DBVersion "16" --Memory $MEMORY --Storage $STORAGE \
  --DBInstanceCount 1 --Period $PERIOD \
  --InstanceChargeType "prepaid" \
  | jq '.Response.OriginalPrice')

POSTPAID_HOUR=$(tccli postgres InquiryPriceCreateDBInstances \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --DBVersion "16" --Memory $MEMORY --Storage $STORAGE \
  --DBInstanceCount 1 \
  --InstanceChargeType "postpaid" \
  | jq '.Response.OriginalPrice')

MONTHLY_HOURS=$(echo "24 * 30" | bc)
echo "| Model | Cost | Period |"
echo "|-------|------|--------|"
echo "| Prepaid (${PERIOD}mo) | ¥${PREPAID} | ${PERIOD} months |"
echo "| Postpaid (hourly) | ¥${POSTPAID_HOUR}/hour ≈ ¥$(echo "$POSTPAID_HOUR * $MONTHLY_HOURS" | bc)/month | monthly |"
echo ""
echo "→ Recommendation: If workload runs > 60% of time, prepaid is cheaper."
echo "→ If workload is intermittent (< 30%), use postpaid with scheduled stop/start."
```

## Right-Sizing Recommendation

```bash
#!/bin/bash
INSTANCE_ID="{{user.instance_id}}"

echo "=== Right-Sizing Analysis ==="

CURRENT=$(tccli postgres DescribeDBInstances \
  --Filters "[{\"Name\":\"db-instance-id\",\"Values\":[\"$INSTANCE_ID\"]}]" \
  | jq '.Response.DBInstanceSet[0]')
CURRENT_MEM=$(echo "$CURRENT" | jq '.Memory')
CURRENT_STORAGE=$(echo "$CURRENT" | jq '.Storage')

PEAK_CPU=$(tccli monitor GetMonitorData \
  --Namespace "QCE/POSTGRES" --MetricName "cpu_usage" \
  --Period 3600 --StartTime "$(date -v-7d +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --Instances "[{\"Dimensions\":[{\"Name\":\"DBInstanceId\",\"Value\":\"$INSTANCE_ID\"}]}]" \
  | jq '[.Response.DataPoints[0].Values[] | values] | max')

PEAK_MEM=$(tccli monitor GetMonitorData \
  --Namespace "QCE/POSTGRES" --MetricName "memory_usage" \
  --Period 3600 --Instances "[{\"Dimensions\":[{\"Name\":\"DBInstanceId\",\"Value\":\"$INSTANCE_ID\"}]}]" \
  | jq '[.Response.DataPoints[0].Values[] | values] | max')

echo "| Metric | Current | 7d Peak | Utilization |"
echo "|--------|---------|---------|-------------|"
echo "| Memory | ${CURRENT_MEM}GB | ${PEAK_MEM}% | $(echo "$PEAK_MEM * $CURRENT_MEM / 100" | bc)GB effective |"
echo "| CPU | - | ${PEAK_CPU}% | - |"

if [ "${PEAK_CPU%.*}" -lt 20 ] && [ "${PEAK_MEM%.*}" -lt 30 ]; then
  TARGET_MEM=$(( CURRENT_MEM / 2 ))
  echo "[RIGHT-SIZE] Instance is over-provisioned. Suggest downgrade to ${TARGET_MEM}GB."
elif [ "${PEAK_CPU%.*}" -gt 80 ] || [ "${PEAK_MEM%.*}" -gt 85 ]; then
  TARGET_MEM=$(( CURRENT_MEM * 2 ))
  echo "[RIGHT-SIZE] Instance is under-provisioned. Suggest upgrade to ${TARGET_MEM}GB."
fi
```

## Cost Reporting

```bash
#!/bin/bash
echo "=== PostgreSQL Monthly Cost Report ==="
tccli postgres DescribeDBInstances --Limit 100 \
  | jq -r '.Response.DBInstanceSet[] | "\(.DBInstanceId) | \(.Memory)GB | \(.Storage)GB | \(.DBInstanceStatus) | \(.CreateTime)"' \
  | while IFS='|' read -r ID MEM STORAGE STATUS CREATE; do
    if [ "$STATUS" = "isolated" ]; then
      echo "| ${ID} | ${MEM}/${STORAGE} | ${STATUS} | ⚠️ Billing stopped | Should delete? |"
    else
      echo "| ${ID} | ${MEM}/${STORAGE} | ${STATUS} | active | Monitor utilization |"
    fi
  done
```

## Cost Anomaly Detection

```bash
#!/bin/bash
echo "=== Cost Anomaly Detection ==="
tccli postgres DescribeDBInstances --Limit 100 \
  | jq -r '.Response.DBInstanceSet[] | "\(.DBInstanceId)|\(.DBInstanceStatus)|\(.Memory)|\(.Storage)"' \
  | while IFS='|' read -r ID STATUS MEM STORAGE; do
    if [ "$STATUS" = "isolated" ]; then
      echo "[ANOMALY] $ID — ISOLATED but reserved ${MEM}GB/${STORAGE}GB. Monthly cost continues until deleted."
      echo "  Action: tccli postgres DeleteDBInstance --DBInstanceId \"$ID\""
    fi
    
    CREATED=$(tccli postgres DescribeDBInstances \
      --Filters "[{\"Name\":\"db-instance-id\",\"Values\":[\"$ID\"]}]" \
      | jq -r '.Response.DBInstanceSet[0].CreateTime // ""')
    if [ -n "$CREATED" ] && [ "$(echo "$CREATED" | cut -c1-7)" = "$(date +'%Y-%m')" ]; then
      echo "[INFO] $ID — created this month ($CREATED). Track new cost."
    fi
  done
```
