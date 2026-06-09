# Log Intelligence — AIOps Pattern Recognition

> **Metric anomalies:** For baseline-first detection (yesterday/week comparison), use [`anomaly-detection.md`](anomaly-detection.md). Correlate log patterns below when `anomaly_severity` ≥ MEDIUM.

## Common Log Patterns

| Pattern Type | Regex | Severity | Root Cause |
|-------------|-------|----------|------------|
| Error spike | `ERROR.*\n{10,}` | HIGH | Application failure |
| Exception | `Exception:.*\n.*\n.*\n` | HIGH | Code defect |
| Timeout | `timeout\|Timeout\|TIMEOUT` | MEDIUM | Network/performance issue |
| OOM | `OutOfMemory\|OOM\|cannot allocate` | CRITICAL | Memory leak |
| Connection refused | `Connection refused\|ECONNREFUSED` | HIGH | Service unavailable |
| Slow query | `Slow query.*time: (\d+)ms` (if > 1000) | MEDIUM | Database issue |

## Pattern Detection

```python
import re
from collections import Counter
from typing import Dict, List

def detect_log_patterns(log_lines: List[str]) -> List[Dict]:
    patterns = {
        'error_spike': r'(ERROR|ERR).{10,}',
        'exception': r'Exception:\s*(\w+)',
        'timeout': r'(timeout|Timeout|TIMEOUT)',
        'oom': r'(OutOfMemoryError|OOM|cannot allocate memory)',
        'connection_refused': r'(Connection refused|ECONNREFUSED)',
        'slow_query': r'Slow query.*time:\s*(\d+)ms',
    }

    anomalies = []
    for line in log_lines:
        for name, regex in patterns.items():
            match = re.search(regex, line)
            if match:
                anomalies.append({
                    'pattern': name,
                    'matched': match.group(0),
                    'line': line
                })

    return aggregate_anomalies(anomalies)

def aggregate_anomalies(anomalies: List[Dict]) -> List[Dict]:
    counts = Counter(a['pattern'] for a in anomalies)
    summaries = []
    for pattern, count in counts.items():
        if count > 10:
            sample = [a['line'] for a in anomalies if a['pattern'] == pattern][:3]
            summaries.append({
                'pattern': pattern,
                'count': count,
                'sample_lines': sample
            })
    return sorted(summaries, key=lambda s: s['count'], reverse=True)
```

## Severity Classification

| Severity | Count Threshold | Action |
|----------|----------------|--------|
| CRITICAL | Error spike + OOM | Immediate investigation required |
| HIGH | 50+ error occurrences in 1h | Diagnose within 1 hour |
| MEDIUM | 10-50 error occurrences | Diagnose within 4 hours |
| LOW | < 10 error occurrences | Monitor, add to knowledge base |

## Log Correlation with Metrics

| Log Pattern | Correlated Metric | Diagnosis |
|-------------|------------------|-----------|
| OOM in logs | MemUsage > 95% | Memory leak confirmed |
| Timeout in logs | Latency p99 > 5s | Performance degradation |
| Connection refused | Active connections → 0 | Service crash |
| Slow query in logs | DB CPU > 80% | Database bottleneck |
