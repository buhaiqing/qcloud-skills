# Detection Rules — Proactive Inspection

## Threshold-Based Detection

| Metric | Warning | Critical | Unit | Detection Window |
|--------|---------|----------|------|-----------------|
| CPU Usage | 90 | 97 | % | Sustained 15 min |
| Memory Usage | 90 | 95 | % | Sustained 15 min |
| Disk Usage | 85 | 95 | % | Instant |
| Disk Remaining | 100 | 50 | GB | Instant |
| Connection Ratio | 80 | 90 | % of max | Sustained 5 min |
| QPS Drop | 30 | 50 | % from baseline | 10 min window |

## Statistical Detection

### Standard Deviation Outliers
```python
import statistics

def detect_outliers(values, threshold_sigma=2.0):
    if len(values) < 3:
        return []
    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    if stdev == 0:
        return []
    return [i for i, v in enumerate(values) if abs(v - mean) > threshold_sigma * stdev]
```

### Percentile-Based Detection
```python
def detect_percentile_breach(values, p95_threshold):
    if not values:
        return False
    p95 = sorted(values)[int(len(values) * 0.95)]
    return p95 > p95_threshold
```

## Rule-Based Detection

| Rule | Condition | Severity |
|------|-----------|----------|
| Expiry warning | Resource expires < 30 days | Warning |
| Expiry critical | Resource expires < 7 days | Critical |
| Backup missing | No backup in last 24h | Warning |
| Security group open | Port 0.0.0.0/0 on 22/3389 | Critical |
| Public IP unnecessary | Non-web resource with public IP | Warning |
| Unattached disk | CBS unattached > 30 days | Warning |

## Multi-Metric Correlation Detection

| Primary Anomaly | Correlated Check | Combined Diagnosis |
|----------------|-----------------|-------------------|
| CPU Warning + Memory Warning | Both > 85% | Full system pressure → Scale up |
| Disk Warning + DiskIO High | Both triggered | I/O bottleneck → Upgrade disk |
| CPU Warning + Network High | Both > threshold | Traffic spike → Rate limit |
| Memory Warning + Connections High | Both > threshold | Connection memory leak → Fix pool |
