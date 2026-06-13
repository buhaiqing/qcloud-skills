# Log Intelligence — AIOps Pattern Recognition

> **Metric anomalies:** [`anomaly-detection.md`](anomaly-detection.md). **Thresholds:** `assets/example-config.yaml` → `log_patterns` and `thresholds` anchors.

## Common Log Patterns

| Pattern Type | Regex | Severity | Root Cause |
|-------------|-------|----------|------------|
| Error spike | `(ERROR\|ERR).{10,}` | HIGH | Application failure |
| Exception | `Exception:\s*(\w+)` | HIGH | Code defect |
| Timeout | `(timeout\|Timeout\|TIMEOUT)` | MEDIUM | Network/performance issue |
| OOM | `(OutOfMemoryError\|OOM\|cannot allocate memory)` | CRITICAL | Memory leak |
| Connection refused | `(Connection refused\|ECONNREFUSED)` | HIGH | Service unavailable |
| Slow query | `Slow query.*time:\s*(\d+)ms` (>1000) | MEDIUM | Database issue |

## Detection Rules (Agent-Executable)

1. Scan CLS `SearchLog` results or user-supplied log lines within `{{user.time_start}}`–`{{user.time_end}}`.
2. Match each line against regex column above (case-sensitive unless noted).
3. Count matches per pattern; compare to `log_patterns.error_spike_threshold` (default 10) in config.
4. Emit pattern hits into RCA `evidence_by_layer.cls_events` or Event Bundle evidence block.

## Severity Classification

| Severity | Condition | Action |
|----------|-----------|--------|
| CRITICAL | OOM pattern + MemUsage anomaly or OOM in ≥1 line | Immediate RCA |
| HIGH | ≥50 matches/hour OR error_spike threshold exceeded | Diagnose within 1h |
| MEDIUM | 10–49 matches/hour | Diagnose within 4h |
| LOW | <10 matches/hour | Monitor; optional KB entry |

## Log ↔ Metric Correlation

| Log Pattern | Correlated Metric | Diagnosis |
|-------------|------------------|-----------|
| OOM in logs | MemUsage > 95% | Memory leak confirmed |
| Timeout in logs | Latency p99 > 5s | Performance degradation |
| Connection refused | Active connections → 0 | Service crash |
| Slow query in logs | DB CPU > 80% / CDB SlowQueries | Database bottleneck |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial pattern library |
| 1.1.0 | 2026-06-13 | Removed inline Python (TE-6); align with example-config anchors |
