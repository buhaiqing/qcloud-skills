# COS Access Log Analysis Scenarios

> 从 `SKILL.md` 提取。COS 访问日志导入 CLS 后的多场景分析。

## Scenario Classification

| Scenario | User Keywords | Primary Fields |
|----------|--------------|----------------|
| Troubleshooting | "can't access", "object not found", "404 error" | `reqPath`, `resHttpCode`, `resErrorCode` |
| Audit | "who deleted", "who modified", "audit trail" | `eventName`, `requester`, `eventTime` |
| Security | "anomalous IP", "brute force", "suspicious" | `remoteIp`, `resHttpCode`, `requester` |
| Performance | "slow requests", "high latency", "timeout" | `resTotalTime`, `eventName` |
| Cost | "infrequent access", "cost optimization" | `reqPath`, `storageClass`, access count |
| General | No specific intent | Show overview dashboard |

## Scenario A: Troubleshooting

```bash
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '{{user.time_range}}' +%s) \
  --To $(date +%s) \
  --Query 'reqPath:"{{user.req_path}}"' \
  --Limit 100
```

## Scenario B: Audit Trail

```bash
# Delete events on a specific path
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '{{user.time_range}}' +%s) \
  --To $(date +%s) \
  --Query 'eventName:DeleteObject AND reqPath:"{{user.req_path}}"' \
  --Limit 50

# All delete events in a bucket
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '{{user.time_range}}' +%s) \
  --To $(date +%s) \
  --Query 'eventName:DeleteObject AND bucketName:{{user.cos_bucket}}' \
  --Limit 200
```

## Scenario C: Security Analysis

```bash
# Top requesting IPs with errors
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '{{user.time_range}}' +%s) \
  --To $(date +%s) \
  --Query 'resHttpCode:403 OR resHttpCode:404' \
  --Limit 200

# Anonymous access attempts
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '{{user.time_range}}' +%s) \
  --To $(date +%s) \
  --Query 'requester:- AND resHttpCode:403' \
  --Limit 100
```

## Scenario D: Performance Analysis

```bash
# Slow requests (resTotalTime > 1000ms)
tccli cls SearchLog \
  --Region "{{env.TENCENTCLOUD_REGION}}" \
  --TopicId "{{user.topic_id}}" \
  --From $(date -d '{{user.time_range}}' +%s) \
  --To $(date +%s) \
  --Query 'resTotalTime:>1000' \
  --Limit 100 \
  --Sort desc
```

## Result Presentation

| Scenario | Key Insights |
|----------|-------------|
| Troubleshooting | Log count by resHttpCode; highlight 4xx/5xx; latest error events |
| Audit | Who (requester), when (eventTime), what eventName, source IP |
| Security | Top IPs by error count; flag IPs with >100 errors; scan patterns |
| Performance | Top 10 slowest requests; average latency by eventName |
| Cost | Least-accessed objects; storage class transition recommendations |

## Failure Recovery

| Error pattern | Recovery |
|--------------|----------|
| No data in time range | Expand time range or wait for COS import to complete |
| Index not found | HALT; create COS log index first |
| Import task not found | HALT; run ImportCOSAccessLogs first |
