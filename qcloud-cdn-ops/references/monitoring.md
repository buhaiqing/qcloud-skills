# CDN Monitoring

## Key Metrics

| Metric | Namespace | MetricName | Description | Alert Threshold |
|--------|-----------|------------|-------------|----------------|
| Bandwidth | QCE/CDN | CdnnetworkTraffic | Bandwidth usage (bps) | > 80% of plan limit |
| QPS | QCE/CDN | CdnRequest | Requests per second | Sudden spike > 2x baseline |
| Cache Hit Ratio | QCE/CDN | CacheHitRate | % of requests served from cache | < 80% = investigate |
| 200 Status Rate | QCE/CDN | StatusCode2XX | % of successful responses | < 95% = investigate |
| 4xx Rate | QCE/CDN | StatusCode4XX | % of client errors | > 5% = investigate |
| 5xx Rate | QCE/CDN | StatusCode5XX | % of origin errors | > 1% = Critical |
| Response Time | QCE/CDN | CdnResponseTime | Edge response latency | p99 > 500ms |

## Dashboard Configuration

```bash
# Query CDN bandwidth data
tccli monitor DescribeBaseMetrics \
  --MetricName CdnnetworkTraffic \
  --Namespace QCE/CDN \
  --Dimensions '[{"Name":"Domain","Value":"cdn.example.com"}]' \
  --Period 60 \
  --StartTime "2026-05-21 00:00:00" \
  --EndTime "2026-05-21 23:59:59"
```

## Alert Rules

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| High bandwidth | > 90% of plan for 10 min | High | Notify, check for traffic spike |
| Low cache hit ratio | < 70% for 30 min | Medium | Review cache rules, check origin headers |
| High 5xx rate | > 5% for 5 min | Critical | Check origin health, failover if needed |
| Origin connection timeout | > 10 timeouts/min | High | Check origin server health |
| Domain offline | Domain status = offline | Critical | Investigate, restart domain |

## Traffic Pattern Analysis

| Pattern | Indicator | Action |
|---------|-----------|--------|
| Traffic spike | Bandwidth > 2x baseline | Scale origin, enable rate limiting |
| Cache degradation | Hit ratio drops suddenly | Check origin Cache-Control headers |
| Regional concentration | > 80% traffic from one region | Consider additional CDN providers |
| Off-peak usage | Significant traffic during off-peak | Verify no unauthorized usage |
