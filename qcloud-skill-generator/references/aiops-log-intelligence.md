# AIOps Log Intelligence Module

Log intelligence patterns for Tencent Cloud skills.

---

## Overview

Skills involving monitoring/diagnosis MUST implement log intelligence patterns:
- Log pattern recognition
- Anomaly detection from logs
- Log-based root cause analysis
- Log correlation with metrics

---

## 1. Log Pattern Recognition

### 1.1 Common Log Patterns

| Pattern Type | Regex Pattern | Severity | Root Cause |
|--------------|---------------|----------|------------|
| Error spike | `ERROR.*\n{10,}` | HIGH | Application failure |
| Exception pattern | `Exception:.*\n.*\n.*\n` | HIGH | Code defect |
| Timeout pattern | `timeout|Timeout|TIMEOUT` | MEDIUM | Network/performance issue |
| OOM pattern | `OutOfMemory|OOM|cannot allocate` | CRITICAL | Memory leak |
| Connection refused | `Connection refused|ECONNREFUSED` | HIGH | Service unavailable |
| Slow query | `Slow query.*time: (\d+)ms` (if > 1000) | MEDIUM | Database issue |

### 1.2 Pattern Detection Implementation

```python
def detect_log_patterns(log_lines: List[str]) -> List[LogAnomaly]:
    """Detect anomalous patterns in log stream"""
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
        for pattern_name, pattern_regex in patterns.items():
            match = re.search(pattern_regex, line)
            if match:
                anomalies.append(LogAnomaly(
                    pattern=pattern_name,
                    matched_text=match.group(0),
                    severity=get_severity(pattern_name),
                    line=line,
                    timestamp=extract_timestamp(line)
                ))
    
    # Aggregate similar patterns
    return aggregate_anomalies(anomalies)

def aggregate_anomalies(anomalies: List[LogAnomaly]) -> List[LogAnomalySummary]:
    """Aggregate similar log anomalies"""
    pattern_counts = Counter(a.pattern for a in anomalies)
    
    summaries = []
    for pattern, count in pattern_counts.items():
        if count > 10:  # Threshold for significant pattern
            summaries.append(LogAnomalySummary(
                pattern=pattern,
                count=count,
                severity=get_severity(pattern),
                first_occurrence=min(a.timestamp for a in anomalies if a.pattern == pattern),
                last_occurrence=max(a.timestamp for a in anomalies if a.pattern == pattern),
                sample_lines=[a.line for a in anomalies if a.pattern == pattern][:3]
            ))
    
    return sorted(summaries, key=lambda s: s.severity, reverse=True)
```

---

## 2. Anomaly Detection from Logs

### 2.1 Log Volume Anomaly

```python
def detect_log_volume_anomaly(log_counts: List[int]) -> Optional[VolumeAnomaly]:
    """Detect abnormal log volume"""
    # Calculate baseline
    baseline = statistics.mean(log_counts[-60:])  # Last 60 minutes
    
    # Check recent volume
    recent = log_counts[-5:]
    recent_avg = statistics.mean(recent)
    
    # Anomaly threshold: 3x baseline
    if recent_avg > 3 * baseline:
        return VolumeAnomaly(
            baseline=baseline,
            current=recent_avg,
            ratio=recent_avg / baseline,
            severity='HIGH',
            message=f"Log volume spike: {recent_avg:.0f} vs baseline {baseline:.0f}"
        )
    
    return None
```

### 2.2 Error Rate Anomaly

```python
def detect_error_rate_anomaly(total_logs: int, error_logs: int) -> Optional[ErrorRateAnomaly]:
    """Detect abnormal error rate"""
    error_rate = error_logs / total_logs if total_logs > 0 else 0
    
    # Thresholds
    thresholds = {
        'CRITICAL': 0.5,  # > 50% errors
        'HIGH': 0.1,      # > 10% errors
        'MEDIUM': 0.05,   # > 5% errors
    }
    
    for severity, threshold in thresholds.items():
        if error_rate > threshold:
            return ErrorRateAnomaly(
                error_rate=error_rate,
                severity=severity,
                message=f"Error rate {error_rate:.1%} exceeds {threshold:.1%} threshold"
            )
    
    return None
```

---

## 3. Log-Based Root Cause Analysis

### 3.1 Root Cause Inference

```yaml
root_cause_inference:
  # Log pattern → root cause mapping
  patterns:
    oom_pattern:
      pattern: "OutOfMemoryError|OOM"
      root_cause: "memory_leak_or_undersized"
      confidence: high
      actions:
        - "Check heap size configuration"
        - "Review memory-intensive operations"
        - "Consider upsizing instance"
        
    connection_refused:
      pattern: "Connection refused"
      root_cause: "service_unavailable"
      confidence: high
      actions:
        - "Check target service status"
        - "Verify network connectivity"
        - "Check security group rules"
        
    timeout_pattern:
      pattern: "timeout|Timeout"
      root_cause: "slow_network_or_processing"
      confidence: medium
      actions:
        - "Check network latency"
        - "Review processing time"
        - "Check database query performance"
        
    slow_query_pattern:
      pattern: "Slow query.*time:"
      root_cause: "database_performance"
      confidence: high
      actions:
        - "Analyze slow query log"
        - "Add missing indexes"
        - "Optimize query logic"
```

### 3.2 Evidence Chain Building

```python
def build_evidence_chain(log_anomalies: List[LogAnomaly], 
                          metrics: Dict[str, float]) -> EvidenceChain:
    """Build evidence chain from logs and metrics"""
    chain = EvidenceChain()
    
    # Add log evidence
    for anomaly in log_anomalies:
        chain.add_evidence(
            type='log',
            pattern=anomaly.pattern,
            count=anomaly.count,
            sample=anomaly.sample_lines[0]
        )
    
    # Correlate with metrics
    if any(a.pattern in ['oom', 'OutOfMemory'] for a in log_anomalies):
        mem_usage = metrics.get('MemUsage', 0)
        if mem_usage > 80:
            chain.add_evidence(
                type='metric',
                name='MemUsage',
                value=mem_usage,
                correlation='confirms_memory_pressure'
            )
    
    # Build root cause hypothesis
    chain.root_cause = infer_root_cause(chain.evidence)
    chain.confidence = calculate_confidence(chain.evidence)
    
    return chain
```

---

## 4. Log-Metric Correlation

### 4.1 Correlation Matrix

| Log Pattern | Correlated Metric | Correlation Logic |
|-------------|------------------|-------------------|
| ERROR spike | CPUUsage ↑ | CPU pressure → errors |
| OOM | MemUsage ↑ ↑ | Memory full → OOM |
| Connection refused | NetworkConnections ↓ | Connections drop |
| Slow query | DiskIO ↑ | I/O pressure → slow |
| Timeout | NetworkLatency ↑ | Latency → timeouts |

### 4.2 Correlation Analysis

```python
def correlate_logs_metrics(log_anomalies: List[LogAnomaly],
                           metrics: Dict[str, List[float]]) -> Dict:
    """Correlate log patterns with metric anomalies"""
    correlations = {}
    
    # OOM logs + Memory metric
    oom_anomalies = [a for a in log_anomalies if 'oom' in a.pattern.lower()]
    if oom_anomalies:
        mem_values = metrics.get('MemUsage', [])
        mem_spike = any(v > 90 for v in mem_values[-10:])
        
        correlations['oom_memory'] = {
            'log_pattern': 'OOM',
            'metric_pattern': 'MemUsage > 90%',
            'correlation': mem_spike,
            'interpretation': 'Memory pressure confirmed by both logs and metrics'
        }
    
    # Error logs + CPU metric
    error_anomalies = [a for a in log_anomalies if 'error' in a.pattern.lower()]
    if error_anomalies and len(error_anomalies) > 10:
        cpu_values = metrics.get('CPUUsage', [])
        cpu_high = any(v > 80 for v in cpu_values[-10:])
        
        correlations['error_cpu'] = {
            'log_pattern': 'ERROR spike',
            'metric_pattern': 'CPUUsage > 80%',
            'correlation': cpu_high,
            'interpretation': 'CPU pressure may be causing application errors'
        }
    
    return correlations
```

---

## 5. Log Query Templates

### 5.1 Error Log Query (Loki/CLS)

```logql
# Query error logs for specific service
{logtype="applog", service_name="xxx"} |~ "ERROR|Exception"

# Count errors by type
{logtype="applog"} |~ "ERROR" | line_format "{{.error_type}}" | count by error_type

# Slow query detection
{logtype="applog"} |~ "Slow query" | regexp "time: (?P<time>\d+)ms" | time > 1000
```

### 5.2 Anomaly Detection Query

```logql
# Error spike detection (compare 5m vs 1h)
{logtype="applog"} |~ "ERROR" 
  | count_over_time(5m) > 3 * count_over_time(1h)

# OOM detection
{logtype="applog"} |~ "OutOfMemory|OOM"

# Connection refused pattern
{logtype="applog"} |~ "Connection refused|ECONNREFUSED"
```

---

## Integration in Generated Skills

```markdown
## AIOps Log Intelligence

### Log Pattern Detection

Monitor for critical patterns:
| Pattern | Severity | Root Cause |
|---------|----------|------------|
| OOM | CRITICAL | Memory leak |
| Connection refused | HIGH | Service unavailable |
| Timeout | MEDIUM | Network/performance |

### Log-Metric Correlation

When OOM detected, check:
- MemUsage metric > 90%
- Correlation confirms memory pressure

### Log Query Examples

```bash
# Query error logs via CLS
tccli cls SearchLog --TopicId xxx --Query "ERROR"
```
```

---

## References

- [Tencent Cloud CLS Documentation](https://cloud.tencent.com/document/product/xxx)
- [Loki LogQL Syntax](https://grafana.com/docs/loki/latest/logql/)
- [AIOps Best Practices](aiops-best-practices.md)