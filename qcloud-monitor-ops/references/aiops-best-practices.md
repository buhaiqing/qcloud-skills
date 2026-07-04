# Monitor AIOps Best Practices

## Overview

Monitor skill MUST implement comprehensive AIOps patterns for observability excellence.

---

## 1. Multi-Metric Correlation

### Comprehensive Correlation Matrix

| Resource | Correlation Group | Metrics | Expected Relationship |
|----------|-------------------|---------|----------------------|
| CVM | Capacity | CPUUsage, MemUsage, DiskUsage | Correlated when workload increases |
| CVM | Performance | CPUUsage, NetworkIO, DiskIO | Network/Disk affects CPU |
| CLB | Traffic | ClientConnum, TrafficIn, TrafficOut | Traffic correlation > 0.8 |
| CLB | Health | HealthStatus, HttpCode5XX, ResponseTime | 5XX ↑ with health failures |
| MySQL | Performance | CpuUseRate, SlowQuery, Connection | SlowQuery ↑ → CPU ↑ |

### Correlation Analysis Implementation

```python
def analyze_metric_correlation(metrics: Dict[str, List]) -> Dict:
    # Multi-metric correlation for Monitor
    correlations = {}
    
    # CVM capacity correlation
    cpu = metrics.get('CPUUsage', [])
    mem = metrics.get('MemUsage', [])
    disk = metrics.get('DiskUsage', [])
    
    if cpu and mem:
        correlations['cpu_mem'] = pearson_correlation(cpu, mem)
        if correlations['cpu_mem'] > 0.7:
            correlations['cpu_mem_diagnosis'] = "CPU and Memory correlated - likely workload increase"
    
    if cpu and disk:
        correlations['cpu_disk'] = pearson_correlation(cpu, disk)
        if correlations['cpu_disk'] > 0.7:
            correlations['cpu_disk_diagnosis'] = "CPU and Disk correlated - check I/O intensive apps"
    
    return correlations
```

---

## 2. Cross-Skill Diagnosis Decision Tree

### Complete Decision Tree

```yaml
diagnosis_decision_tree:
  root: classify_resource_type
  
  branches:
    # CVM branch
    - condition: "namespace == QCE/CVM"
      action: load_qcloud_cvm_ops
      sub_tree:
        - condition: "CPUUsage > 90%"
          diagnosis: cpu_pressure
          actions: [check_processes, check_network, check_logs]
        - condition: "MemUsage > 90%"
          diagnosis: memory_pressure
          actions: [check_memory_leak, check_swap]
        - condition: "DiskUsage > 90%"
          diagnosis: disk_full
          actions: [check_disk_usage, clean_logs]
          
    # CLB branch
    - condition: "namespace == QCE/LB_PUBLIC"
      action: load_qcloud_clb_ops
      sub_tree:
        - condition: "HttpCode5XX > threshold"
          diagnosis: backend_error
          delegate_to: qcloud-cvm-ops
        - condition: "HealthCheckFailedNum > 0"
          diagnosis: backend_unhealthy
          delegate_to: qcloud_cvm_ops
          
    # MySQL branch  
    - condition: "namespace == QCE/CDB"
      action: load_qcloud_mysql_ops
      sub_tree:
        - condition: "SlowQuery > threshold"
          diagnosis: slow_queries
          actions: [analyze_slow_log, optimize_query]
        - condition: "CpuUseRate > 90%"
          diagnosis: db_cpu_pressure
          actions: [check_connections, check_queries]
```

---

## 3. Complete Delegation Matrix

### Monitor Delegation

| Metric Anomaly | Delegate To | Reason |
|----------------|-------------|--------|
| CVM CPUUsage > 90% | `qcloud-cvm-ops` | Instance-level issue |
| CVM DiskUsage > 90% | `qcloud-cvm-ops` + `qcloud-cbs-ops` | Storage issue |
| CLB HealthStatus unhealthy | `qcloud-clb-ops` | Backend health |
| MySQL SlowQuery high | `qcloud-cdb-ops` | Database performance |
| Redis CmdExecuteCount anomaly | `qcloud-redis-ops` | Cache performance |
| VPC VpcFlowMetric anomaly | `qcloud-vpc-ops` | Network issue |

---

## 4. Proactive Inspection Framework

### Five-Stage Inspection Flow

```yaml
proactive_inspection:
  stage_1_discovery:
    actions:
      - discover_all_resources
      - inventory_by_namespace
    output: resource_inventory
    
  stage_2_collection:
    actions:
      - collect_metrics_parallel
      - aggregate_by_resource_type
    input: resource_inventory
    output: metrics_dataset
    
  stage_3_detection:
    actions:
      - threshold_detection
      - trend_detection
      - anomaly_detection
    input: metrics_dataset
    output: anomaly_list
    
  stage_4_diagnosis:
    actions:
      - correlate_metrics
      - identify_root_cause
      - delegate_to_specialist_skill
    input: anomaly_list
    output: diagnosis_results
    
  stage_5_report:
    actions:
      - generate_inspection_report
      - prioritize_issues
      - suggest_actions
    input: diagnosis_results
    output: inspection_report
```

### Daily Proactive Alerts

```yaml
daily_proactive_alerts:
  - name: capacity_projection
    condition: "DiskUsage trend → 90% in 7 days"
    severity: warning
    message: "Disk will reach 90% capacity in ~7 days"
    action: "Plan disk expansion or cleanup"
    
  - name: cpu_baseline_shift
    condition: "CPUUsage baseline changed > 20%"
    severity: warning
    message: "CPU baseline shifted - workload change detected"
    action: "Investigate recent deployments"
    
  - name: connection_pool_trend
    condition: "MySQL ConnectionUsage trend → 90%"
    severity: warning
    message: "Connection pool approaching limit"
    action: "Increase max_connections or review connection usage"
```

---

## 5. Alarm Storm Handling (Enhanced)

### Alarm Storm Levels

| Level | Definition | Response |
|-------|------------|----------|
| Level 1 | 5-10 alarms/5min | Aggregate, suppress duplicates |
| Level 2 | 10-20 alarms/5min | Suppress + escalate |
| Level 3 | > 20 alarms/5min | Emergency suppression + immediate escalation |

### Handling Protocol

```yaml
alarm_storm_protocol:
  level_1:
    actions:
      - aggregate_similar_alarms
      - suppress_duplicate_metrics
      - identify_pattern
    duration: 5 minutes
    
  level_2:
    actions:
      - level_1_actions
      - suppress_all_duplicates
      - notify_on_call
      - start_incident
    duration: 10 minutes
    
  level_3:
    actions:
      - emergency_suppress
      - immediate_escalation
      - invoke_all_delegate_skills
      - create_major_incident
    duration: Until resolved
```

### Pattern-Based Aggregation

```python
def aggregate_alarm_storm(alarms: List[Alarm]) -> AggregatedIncident:
    # Aggregate alarm storm by pattern
    patterns = {}
    
    for alarm in alarms:
        # Group by root cause pattern
        pattern_key = f"{alarm.namespace}:{alarm.resource_type}:{alarm.metric_name}"
        
        if pattern_key not in patterns:
            patterns[pattern_key] = {
                'count': 0,
                'resources': [],
                'first_alarm': alarm,
                'last_alarm': alarm
            }
        
        patterns[pattern_key]['count'] += 1
        patterns[pattern_key]['resources'].append(alarm.resource_id)
        patterns[pattern_key]['last_alarm'] = alarm
    
    # Create aggregated incident
    return AggregatedIncident(
        patterns=patterns,
        total_alarms=len(alarms),
        recommendation=generate_aggregation_recommendation(patterns)
    )
```

---

## 6. Metric Trend Prediction

### Trend Analysis

```python
def predict_metric_trend(metric_history: List[float]) -> TrendPrediction:
    # Predict metric trend for proactive alerting
    # Linear regression
    x = list(range(len(metric_history)))
    y = metric_history
    
    slope, intercept = linear_regression(x, y)
    
    # Project forward
    projected_values = [slope * (len(y) + i) + intercept for i in range(7)]
    
    return TrendPrediction(
        slope=slope,
        intercept=intercept,
        projected_7_day=projected_values,
        will_exceed_threshold=max(projected_values) > threshold
    )
```

---

## AIOps Compliance Checklist

| Requirement | Monitor Implementation | Location |
|-------------|------------------------|----------|
| Multi-metric correlation | ✓ Comprehensive matrix | This document |
| Diagnosis decision tree | ✓ Complete tree with all products | This document |
| Delegation matrix | ✓ All product delegations | This document |
| Proactive inspection | ✓ Five-stage flow | This document |
| Alarm storm handling | ✓ Three-level protocol | This document |
| Trend prediction | ✓ Linear regression | This document |