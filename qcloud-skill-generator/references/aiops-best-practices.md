# AIOps Best Practices

Mandatory AIOps patterns for monitoring/diagnosis Tencent Cloud skills.

---

## Overview

Skills involving monitoring, alarm, or diagnosis MUST implement AIOps patterns:

1. Multi-metric correlation
2. Cross-skill diagnosis decision tree
3. Delegation matrix
4. Proactive inspection
5. Alarm storm handling

---

## 1. Multi-Metric Correlation

### 1.1 Correlation Patterns

| Pattern | Primary Metric | Secondary Metrics | Correlation Logic |
|---------|---------------|-------------------|-------------------|
| CPU Pressure | CPUUsage | NetworkIn, MemUsage, DiskIO | CPU ↑ + Network ↑ = traffic spike |
| Memory Pressure | MemUsage | CPUUsage, OOMEvents | Mem ↑ + OOM = memory leak |
| Storage Pressure | DiskUsage | DiskIO, DiskLatency | Disk ↑ + Latency ↑ = I/O bottleneck |
| Network Pressure | NetworkIn/Out | CPUUsage, TCPConnections | Network ↑ + CPU ↑ = throughput limit |

### 1.2 Correlation Implementation

```python
def correlate_metrics(metrics: Dict[str, List[float]]) -> Dict:
    # Multi-metric correlation analysis
    correlations = {}
    
    # CPU + Network correlation
    cpu_values = metrics.get('CPUUsage', [])
    network_values = metrics.get('NetworkIn', [])
    
    if len(cpu_values) > 0 and len(network_values) > 0:
        # Pearson correlation
        correlation = pearson_correlation(cpu_values, network_values)
        correlations['cpu_network'] = {
            'value': correlation,
            'interpretation': interpret_correlation(correlation)
        }
    
    # CPU + Memory correlation
    mem_values = metrics.get('MemUsage', [])
    if len(cpu_values) > 0 and len(mem_values) > 0:
        correlation = pearson_correlation(cpu_values, mem_values)
        correlations['cpu_memory'] = {
            'value': correlation,
            'interpretation': interpret_correlation(correlation)
        }
    
    return correlations

def interpret_correlation(value: float) -> str:
    # Interpret correlation value
    if value > 0.7:
        return 'Strong positive correlation - likely same root cause'
    elif value > 0.3:
        return 'Moderate correlation - partially related'
    elif value < -0.3:
        return 'Negative correlation - inverse relationship'
    else:
        return 'No significant correlation - independent metrics'
```

### 1.3 Correlation-Based Diagnosis

```yaml
# Correlation diagnosis rules
correlation_rules:
  - name: traffic_spike
    condition: "CPUUsage ↑ AND NetworkIn ↑ AND correlation > 0.7"
    diagnosis: "Traffic spike causing CPU pressure"
    resolution: "Scale horizontally or optimize network handling"
    
  - name: memory_leak
    condition: "MemUsage ↑ ↑ AND OOMEvents > 0"
    diagnosis: "Memory leak detected"
    resolution: "Restart service, fix memory leak in code"
    
  - name: io_bottleneck
    condition: "DiskUsage stable AND DiskLatency ↑ AND DiskIO ↑"
    diagnosis: "I/O bottleneck without capacity issue"
    resolution: "Optimize I/O, check slow queries"
```

---

## 2. Cross-Skill Diagnosis Decision Tree

### 2.1 Decision Tree Structure

```yaml
decision_tree:
  root: resource_health_check
  branches:
    - condition: "resource_type == CVM"
      action: load_qcloud_cvm_ops
      sub_tree: cvm_diagnosis_tree
      
    - condition: "resource_type == MySQL"
      action: load_qcloud_mysql_ops
      sub_tree: mysql_diagnosis_tree
      
    - condition: "resource_type == CBS"
      action: load_qcloud_cbs_ops
      sub_tree: cbs_diagnosis_tree
      
    - condition: "resource_type == CLB"
      action: load_qcloud_clb_ops
      sub_tree: clb_diagnosis_tree

cvm_diagnosis_tree:
  branches:
    - condition: "CPUUsage > 90%"
      diagnosis: cpu_high
      actions: [check_network, check_processes, check_logs]
      
    - condition: "MemUsage > 90%"
      diagnosis: memory_high
      actions: [check_processes, check_oom, check_swap]
      
    - condition: "DiskUsage > 90%"
      diagnosis: disk_full
      actions: [check_disk_usage, clean_logs, expand_disk]

mysql_diagnosis_tree:
  branches:
    - condition: "SlowQuery > threshold"
      diagnosis: slow_queries
      actions: [analyze_slow_log, check_index, optimize_query]
      
    - condition: "ConnectionUsage > 90%"
      diagnosis: connection_pool_exhausted
      actions: [check_max_connections, check_idle_connections]
```

### 2.2 Decision Tree Implementation

```python
class DiagnosisDecisionTree:
    """Cross-skill diagnosis decision tree"""
    
    def __init__(self):
        self.tree = self._load_tree()
    
    def diagnose(self, resource_type: str, metrics: Dict) -> DiagnosisResult:
        # Execute diagnosis based on decision tree
        # Load appropriate skill
        skill = self._load_skill(resource_type)
        
        # Traverse decision tree
        current_node = self.tree.get(resource_type)
        
        for branch in current_node.get('branches', []):
            if self._check_condition(branch['condition'], metrics):
                # Execute actions
                actions_results = self._execute_actions(branch['actions'], skill)
                
                return DiagnosisResult(
                    diagnosis=branch['diagnosis'],
                    actions=actions_results,
                    confidence=self._calculate_confidence(actions_results)
                )
        
        return DiagnosisResult(diagnosis='unknown', actions=[], confidence=0)
    
    def _load_skill(self, resource_type: str) -> Skill:
        # Load appropriate skill for resource type
        skill_map = {
            'CVM': 'qcloud-cvm-ops',
            'MySQL': 'qcloud-mysql-ops',
            'CBS': 'qcloud-cbs-ops',
            'CLB': 'qcloud-clb-ops',
            'Redis': 'qcloud-redis-ops',
        }
        return load_skill(skill_map.get(resource_type))
```

---

## 3. Delegation Matrix

### 3.1 Skill Delegation Matrix

| Primary Skill | Delegate To | Trigger |
|--------------|-------------|---------|
| qcloud-cvm-ops | qcloud-cbs-ops | Disk-related issue detected |
| qcloud-cvm-ops | qcloud-vpc-ops | Network/VPC issue detected |
| qcloud-cvm-ops | qcloud-clb-ops | Load balancer issue detected |
| qcloud-mysql-ops | qcloud-cvm-ops | Host-level issue detected |
| qcloud-mysql-ops | qcloud-cbs-ops | Storage issue detected |
| qcloud-redis-ops | qcloud-cvm-ops | Host-level issue detected |
| qcloud-clb-ops | qcloud-cvm-ops | Backend server issue |

### 3.2 Delegation Protocol

```markdown
**Delegation Protocol:**

When delegating to another skill:

1. **Prepare Context**:
   - Resource ID: [ID]
   - Issue: [Description]
   - Metrics: [Relevant metrics]
   
2. **Invoke Target Skill**:
   ```
   Invoke: qcloud-[target]-ops
   Context: {
     "resource_id": "[ID]",
     "issue": "[Issue description]",
     "correlated_metrics": {...}
   }
   ```
   
3. **Collect Results**:
   - Diagnosis from target skill
   - Recommendations
   
4. **Integrate Findings**:
   - Combine primary and delegated diagnosis
   - Present unified resolution plan
```

---

## 4. Proactive Inspection

### 4.1 Inspection Categories

| Category | Frequency | Checks |
|----------|-----------|--------|
| Daily | Every 24h | Critical metrics, recent errors |
| Weekly | Every 7d | Capacity trends, security posture |
| Monthly | Every 30d | Cost analysis, architecture review |

### 4.2 Proactive Inspection Flow

```yaml
inspection_flow:
  stages:
    - name: discovery
      action: discover_all_resources
      output: resource_inventory
      
    - name: collection
      action: collect_metrics_for_all
      input: resource_inventory
      output: metrics_dataset
      
    - name: detection
      action: detect_anomalies
      input: metrics_dataset
      output: anomaly_list
      
    - name: diagnosis
      action: diagnose_anomalies
      input: anomaly_list
      output: diagnosis_results
      
    - name: report
      action: generate_inspection_report
      input: diagnosis_results
      output: inspection_report
```

### 4.3 Proactive Alert Rules

```yaml
proactive_alerts:
  - name: capacity_projection
    condition: "DiskUsage trend + 7 days > 90%"
    severity: warning
    message: "Disk will reach 90% in ~7 days"
    action: "Plan disk expansion"
    
  - name: cpu_baseline_shift
    condition: "CPUUsage baseline changed > 20%"
    severity: warning
    message: "CPU baseline shifted significantly"
    action: "Investigate workload changes"
    
  - name: slow_query_increase
    condition: "SlowQuery count increased > 50%"
    severity: warning
    message: "Slow query count increasing"
    action: "Analyze query patterns"
```

---

## 5. Alarm Storm Handling

### 5.1 Alarm Storm Definition

**Alarm Storm**: > 10 alarms within 5 minutes for same resource or related resources.

### 5.2 Alarm Storm Detection

```python
def detect_alarm_storm(alarm_events: List[AlarmEvent]) -> Optional[AlarmStorm]:
    # Detect alarm storm condition
    # Group alarms by resource and time
    recent_alarms = [
        a for a in alarm_events 
        if a.timestamp > datetime.now() - timedelta(minutes=5)
    ]
    
    # Count per resource
    resource_counts = {}
    for alarm in recent_alarms:
        resource_counts[alarm.resource_id] = resource_counts.get(alarm.resource_id, 0) + 1
    
    # Check for storm
    for resource_id, count in resource_counts.items():
        if count > 10:
            return AlarmStorm(
                resource_id=resource_id,
                alarm_count=count,
                alarm_types=set(a.alarm_type for a in recent_alarms if a.resource_id == resource_id),
                severity='storm'
            )
    
    return None
```

### 5.3 Alarm Storm Handling

```yaml
alarm_storm_handling:
  actions:
    - name: suppress_duplicates
      action: "Suppress duplicate alarms for 5 minutes"
      priority: 1
      
    - name: aggregate_alarms
      action: "Aggregate into single incident"
      priority: 2
      
    - name: identify_root_cause
      action: "Correlate alarms to identify root cause"
      priority: 3
      
    - name: escalate
      action: "Escalate to on-call if unresolved in 10 minutes"
      priority: 4
      
  suppression_rules:
    - condition: "same_resource AND same_metric"
      suppress_duration: 5m
      
    - condition: "related_resources AND same_root_cause"
      suppress_duration: 10m
      
  notification:
    storm_detected: "⚠️ Alarm storm detected: {count} alarms for {resource_id}"
    root_cause: "Root cause identified: {diagnosis}"
    resolution: "✅ Alarm storm resolved"
```

---

## AIOps Compliance Checklist

Skills with monitoring/diagnosis MUST have:

| Requirement | Status | Location |
|-------------|--------|----------|
| Multi-metric correlation | ✓ | references/optimization-analysis.md |
| Diagnosis decision tree | ✓ | references/troubleshooting.md |
| Delegation matrix | ✓ | SKILL.md Trigger & Scope |
| Proactive inspection | ✓ | templates/proactive-inspection.md |
| Alarm storm handling | ✓ | references/monitoring.md |

---

## References

- [Tencent Cloud Monitor](https://cloud.tencent.com/document/product/248)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Optimization Analysis](optimization-analysis.md)