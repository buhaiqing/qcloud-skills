# CVM AIOps Diagnosis

Multi-metric correlation, cross-skill diagnosis decision tree, alarm storm handling, and fault prediction for CVM.

---

## Overview

AIOps for CVM implements:
1. Multi-metric correlation analysis
2. Cross-skill diagnosis decision tree
3. Delegation matrix to related skills
4. Alarm storm detection and handling
5. Fault prediction and early warning

---

## 1. Multi-Metric Correlation

### 1.1 Correlation Patterns

| Pattern | Primary Metric | Correlated Metrics | Diagnosis |
|---------|---------------|-------------------|-----------|
| **Traffic Spike** | CPUUsage ↑ | NetworkIn ↑ | Traffic surge → scale out |
| **CPU Bottleneck** | CPUUsage ↑ | NetworkIn stable | Compute-heavy → optimize |
| **Memory Leak** | MemUsage ↑↑ | CPU stable, OOMEvents | Memory leak → restart |
| **I/O Bottleneck** | DiskLatency ↑ | DiskIO ↑ | Storage bottleneck → upgrade disk |
| **Network Pressure** | NetworkIn ↑ | CPU ↑, Connections ↑ | Bandwidth limit → increase BW |

### 1.2 Correlation Calculation

```python
from scipy import stats

def calculate_correlation(metric_a: List[float], metric_b: List[float]) -> float:
    # Calculate Pearson correlation coefficient
    if len(metric_a) != len(metric_b) or len(metric_a) < 2:
        return 0.0
    
    correlation, p_value = stats.pearsonr(metric_a, metric_b)
    return correlation

def interpret_correlation(value: float) -> str:
    # Interpret correlation value
    if value > 0.7:
        return "Strong positive - likely same root cause"
    elif value > 0.3:
        return "Moderate positive - partially related"
    elif value < -0.3:
        return "Negative correlation - inverse relationship"
    else:
        return "No significant correlation - independent"
```

### 1.3 Correlation Analysis Script

```python
def correlate_metrics_for_instance(instance_id: str, metrics_data: Dict) -> CorrelationResult:
    # Perform multi-metric correlation for single instance
    
    result = CorrelationResult()
    result.instance_id = instance_id
    
    # Extract metric values
    cpu_values = metrics_data['CPUUsage']['values']
    mem_values = metrics_data['MemUsage']['values']
    net_in_values = metrics_data['NetworkIn']['values']
    net_out_values = metrics_data['NetworkOut']['values']
    
    # Calculate correlations
    result.cpu_network_in = calculate_correlation(cpu_values, net_in_values)
    result.cpu_mem = calculate_correlation(cpu_values, mem_values)
    result.network_in_out = calculate_correlation(net_in_values, net_out_values)
    
    # Interpret correlations for diagnosis
    if result.cpu_network_in > 0.7:
        result.diagnosis_patterns.append({
            'pattern': 'traffic_spike',
            'confidence': 'HIGH',
            'description': 'CPU and Network highly correlated - traffic-driven',
            'recommendation': 'Scale horizontally or optimize network handling'
        })
    
    if result.cpu_mem > 0.5 and metrics_data['MemUsage']['max'] > 90:
        result.diagnosis_patterns.append({
            'pattern': 'resource_pressure',
            'confidence': 'HIGH',
            'description': 'CPU and Memory both elevated',
            'recommendation': 'Application under pressure - scale or optimize'
        })
    
    if result.cpu_network_in < 0.2 and metrics_data['CPUUsage']['avg'] > 80:
        result.diagnosis_patterns.append({
            'pattern': 'compute_bound',
            'confidence': 'MEDIUM',
            'description': 'High CPU but no network correlation - compute-heavy',
            'recommendation': 'Optimize compute-intensive operations'
        })
    
    return result
```

---

## 2. Cross-Skill Diagnosis Decision Tree

### 2.1 Decision Tree Structure

```yaml
diagnosis_decision_tree:
  root: identify_resource_type
  
  branches:
    - condition: "resource_type == 'CVM'"
      skill: qcloud-cvm-ops
      sub_tree: cvm_diagnosis
      
    - condition: "resource_type == 'CBS'"
      skill: qcloud-cbs-ops
      sub_tree: cbs_diagnosis
      
    - condition: "resource_type == 'MySQL'"
      skill: qcloud-mysql-ops
      sub_tree: mysql_diagnosis
      
    - condition: "resource_type == 'Redis'"
      skill: qcloud-redis-ops
      sub_tree: redis_diagnosis
      
    - condition: "resource_type == 'CLB'"
      skill: qcloud-clb-ops
      sub_tree: clb_diagnosis
      
cvm_diagnosis:
  branches:
    - condition: "CPUUsage > 90% AND NetworkIn correlation > 0.7"
      diagnosis: "traffic_spike"
      actions: [scale_out, optimize_network]
      
    - condition: "CPUUsage > 90% AND NetworkIn correlation < 0.3"
      diagnosis: "compute_bound"
      actions: [optimize_application, increase_cpu]
      
    - condition: "MemUsage > 90% AND increasing_trend"
      diagnosis: "memory_pressure_or_leak"
      actions: [check_memory_leak, restart_service, increase_memory]
      
    - condition: "Status == STOPPED unexpectedly"
      diagnosis: "unexpected_stop"
      actions: [check_audit_logs, check_recent_operations, restart]
      
    - condition: "Disk attached issue"
      diagnosis: "storage_issue"
      delegate_to: qcloud-cbs-ops
      
    - condition: "Network connectivity issue"
      diagnosis: "network_issue"
      delegate_to: qcloud-vpc-ops
```

### 2.2 Decision Tree Implementation

```python
class DiagnosisDecisionTree:
    # Cross-skill diagnosis decision tree
    
    skill_map = {
        'CVM': 'qcloud-cvm-ops',
        'CBS': 'qcloud-cbs-ops',
        'MySQL': 'qcloud-mysql-ops',
        'Redis': 'qcloud-redis-ops',
        'CLB': 'qcloud-clb-ops',
        'VPC': 'qcloud-vpc-ops',
    }
    
    def diagnose(self, issue: IssueContext) -> DiagnosisResult:
        # Execute diagnosis decision tree
        
        # Load appropriate skill
        skill_name = self.skill_map.get(issue.resource_type)
        
        # Traverse decision tree for this skill
        tree = self._load_tree(skill_name)
        
        result = DiagnosisResult()
        result.resource_id = issue.resource_id
        result.resource_type = issue.resource_type
        
        for branch in tree['branches']:
            if self._evaluate_condition(branch['condition'], issue.metrics):
                
                # Check if delegation needed
                if 'delegate_to' in branch:
                    result.delegate_to = branch['delegate_to']
                    result.diagnosis = branch['diagnosis']
                    result.delegation_context = {
                        'resource_id': issue.resource_id,
                        'issue_type': branch['diagnosis'],
                        'correlated_metrics': issue.metrics
                    }
                else:
                    result.diagnosis = branch['diagnosis']
                    result.actions = branch['actions']
                    result.confidence = self._calculate_confidence(issue.metrics, branch)
                
                break
        
        return result
    
    def _evaluate_condition(self, condition: str, metrics: Dict) -> bool:
        # Evaluate decision tree condition
        # Parse condition string
        # Example: "CPUUsage > 90% AND NetworkIn correlation > 0.7"
        
        parts = condition.split(' AND ')
        
        for part in parts:
            if 'correlation' in part:
                # Handle correlation condition
                metric, op, value = self._parse_correlation_condition(part)
                correlation = metrics.get('correlations', {}).get(metric, 0)
                if not self._compare(correlation, op, float(value)):
                    return False
            else:
                # Handle simple metric condition
                metric, op, value = self._parse_simple_condition(part)
                current = metrics.get(metric, {}).get('current', 0)
                if not self._compare(current, op, float(value)):
                    return False
        
        return True
```

---

## 3. Delegation Matrix

### 3.1 Skill Delegation Matrix

| Primary Skill | Issue Detected | Delegate To | Trigger Condition |
|--------------|----------------|-------------|-------------------|
| qcloud-cvm-ops | Disk I/O issue | qcloud-cbs-ops | DiskLatency ↑, DiskIO ↓ |
| qcloud-cvm-ops | Network/VPC issue | qcloud-vpc-ops | Connectivity failure, ACL blocked |
| qcloud-cvm-ops | Load balancer issue | qcloud-clb-ops | CLB backend health check failed |
| qcloud-cvm-ops | Security issue | qcloud-cam-ops | Unauthorized access, permission denied |
| qcloud-mysql-ops | Host-level issue | qcloud-cvm-ops | Host CPU/Memory high |
| qcloud-mysql-ops | Storage issue | qcloud-cbs-ops | Disk latency, disk full |
| qcloud-redis-ops | Host-level issue | qcloud-cvm-ops | Host memory pressure |
| qcloud-clb-ops | Backend issue | qcloud-cvm-ops | Backend server unreachable |

### 3.2 Delegation Protocol

```yaml
delegation_protocol:
  steps:
    1_prepare_context:
      action: "Prepare delegation context"
      required_fields:
        - resource_id
        - issue_type
        - correlated_metrics
        - severity
        
    2_invoke_target:
      action: "Invoke target skill with context"
      format: |
        Invoke: {target_skill}
        Context: {
          "resource_id": "{resource_id}",
          "issue": "{issue_description}",
          "correlated_metrics": {metrics},
          "severity": "{severity}"
        }
        
    3_collect_results:
      action: "Collect diagnosis from target skill"
      expected:
        - diagnosis_result
        - recommendations
        - actions
        
    4_integrate:
      action: "Integrate findings into primary diagnosis"
      output:
        - unified_diagnosis
        - combined_action_plan
```

### 3.3 Delegation Example

```python
def delegate_to_vpc_skill(cvm_client, instance_id: str, issue: str):
    # Delegate network issue to VPC skill
    
    # Prepare context
    context = {
        'resource_id': instance_id,
        'issue': issue,
        'correlated_metrics': {
            'instance_vpc': get_instance_vpc(cvm_client, instance_id),
            'instance_subnet': get_instance_subnet(cvm_client, instance_id),
            'security_groups': get_instance_security_groups(cvm_client, instance_id)
        },
        'severity': 'HIGH'
    }
    
    # Invoke VPC skill
    # Note: In actual implementation, this would load qcloud-vpc-ops skill
    vpc_diagnosis = invoke_skill('qcloud-vpc-ops', context)
    
    # Integrate results
    return {
        'primary_diagnosis': f"CVM {instance_id} network issue",
        'delegated_diagnosis': vpc_diagnosis,
        'action_plan': vpc_diagnosis.get('recommendations', [])
    }
```

---

## 4. Alarm Storm Handling

### 4.1 Alarm Storm Definition

**Alarm Storm**: > 10 alarms within 5 minutes for same resource or related resources.

### 4.2 Alarm Storm Detection

```python
def detect_alarm_storm(alarm_events: List[AlarmEvent], threshold: int = 10) -> Optional[AlarmStorm]:
    # Detect alarm storm condition
    
    # Filter recent alarms (last 5 minutes)
    recent_alarms = [
        a for a in alarm_events
        if a.timestamp > datetime.now() - timedelta(minutes=5)
    ]
    
    # Group by resource
    resource_groups = defaultdict(list)
    for alarm in recent_alarms:
        resource_groups[alarm.resource_id].append(alarm)
    
    # Check for storm
    for resource_id, alarms in resource_groups.items():
        if len(alarms) > threshold:
            return AlarmStorm(
                resource_id=resource_id,
                alarm_count=len(alarms),
                alarm_types=set(a.alarm_type for a in alarms),
                severity='storm',
                start_time=min(a.timestamp for a in alarms),
                end_time=max(a.timestamp for a in alarms)
            )
    
    return None
```

### 4.3 Alarm Storm Handling Actions

```yaml
alarm_storm_handling:
  immediate_actions:
    - name: suppress_duplicates
      action: "Suppress duplicate alarms for 5 minutes"
      priority: 1
      
    - name: aggregate_incident
      action: "Aggregate into single incident ticket"
      priority: 2
      
    - name: correlate_root_cause
      action: "Correlate alarms to identify root cause"
      priority: 3
      
  root_cause_analysis:
    steps:
      - "Analyze alarm correlation patterns"
      - "Identify primary triggering alarm"
      - "Determine cascade effect"
      
  notification:
    template: |
      ⚠️ Alarm Storm Detected
      
      Resource: {resource_id}
      Alarm Count: {count}
      Alarm Types: {types}
      
      Root Cause Analysis: {root_cause}
      
      Recommended Actions: {actions}
      
  suppression_rules:
    - condition: "same_resource AND same_metric"
      suppress_duration: 5m
      
    - condition: "related_resources AND same_root_cause"
      suppress_duration: 10m
      
    - condition: "cascade_alarm_from_primary"
      suppress_duration: 15m
```

### 4.4 Alarm Storm Resolution

```python
def handle_alarm_storm(storm: AlarmStorm) -> AlarmStormResolution:
    # Handle alarm storm and generate resolution
    
    resolution = AlarmStormResolution()
    resolution.storm_id = storm.resource_id
    
    # Identify root cause
    alarms_by_type = Counter(a.alarm_type for a in storm.alarms)
    primary_alarm_type = alarms_by_type.most_common(1)[0][0]
    
    # Correlate alarms
    if 'CPUUsage' in alarms_by_type and 'NetworkIn' in alarms_by_type:
        resolution.root_cause = 'traffic_spike'
        resolution.primary_alarm = 'CPUUsage'
        resolution.cascade_alarms = ['NetworkIn', 'MemUsage']
    elif 'MemUsage' in alarms_by_type and alarms_by_type['MemUsage'] > 3:
        resolution.root_cause = 'memory_pressure'
        resolution.primary_alarm = 'MemUsage'
    else:
        resolution.root_cause = 'unknown'
        resolution.primary_alarm = primary_alarm_type
    
    # Generate action plan
    resolution.action_plan = get_action_plan_for_root_cause(resolution.root_cause)
    
    # Set suppression
    resolution.suppression_config = {
        'resource_id': storm.resource_id,
        'duration_minutes': 5,
        'suppressed_types': resolution.cascade_alarms
    }
    
    return resolution
```

---

## 5. Fault Prediction

### 5.1 Prediction Patterns

| Pattern | Indicators | Prediction | Time Window |
|---------|------------|------------|-------------|
| **Capacity Exhaustion** | DiskUsage trend + 2%/day | Disk full | 7-14 days |
| **Performance Degradation** | CPU baseline shift + 20% | CPU bottleneck | 3-7 days |
| **Memory Leak** | MemUsage trend + 5%/day | OOM crash | 5-10 days |
| **Connection Pool Exhaustion** | Connections trend + 10%/day | Connection failure | 3-5 days |

### 5.2 Trend Analysis

```python
def analyze_metric_trend(metric_values: List[float], window: int = 7) -> TrendResult:
    # Analyze metric trend for prediction
    
    if len(metric_values) < window:
        return TrendResult(trend='insufficient_data')
    
    # Calculate daily averages for window
    daily_avg = []
    for i in range(len(metric_values) - window + 1):
        daily_avg.append(sum(metric_values[i:i+window]) / window)
    
    # Linear regression for trend
    x = list(range(len(daily_avg)))
    y = daily_avg
    
    slope, intercept = calculate_linear_regression(x, y)
    
    # Project forward
    projected_days = 7
    projected_values = [slope * (len(daily_avg) + d) + intercept for d in range(projected_days)]
    
    # Determine trend
    if slope > 0.5:
        trend = 'increasing'
        alert = 'HIGH'
    elif slope > 0.1:
        trend = 'gradual_increase'
        alert = 'MEDIUM'
    elif slope < -0.5:
        trend = 'decreasing'
        alert = 'INFO'
    else:
        trend = 'stable'
        alert = 'LOW'
    
    return TrendResult(
        trend=trend,
        slope=slope,
        current_value=daily_avg[-1],
        projected_values=projected_values,
        days_to_threshold=calculate_days_to_threshold(daily_avg[-1], slope, 90),
        alert_level=alert
    )

def calculate_days_to_threshold(current: float, slope: float, threshold: float) -> int:
    # Calculate days until threshold is reached
    if slope <= 0:
        return -1  # Never reached
    
    days = (threshold - current) / slope
    return int(days) if days > 0 else -1
```

### 5.3 Fault Prediction Alerts

```yaml
fault_prediction_alerts:
  disk_capacity:
    condition: "DiskUsage trend + 2%/day"
    prediction: "Disk will reach 90% in ~{days} days"
    severity: WARNING
    action: "Plan disk expansion within {days} days"
    
  cpu_baseline_shift:
    condition: "CPUUsage baseline changed > 20%"
    prediction: "CPU baseline elevated - potential bottleneck"
    severity: WARNING
    action: "Investigate workload changes"
    
  memory_trend:
    condition: "MemUsage trend + 5%/day AND MemUsage > 70%"
    prediction: "Memory will reach 90% in ~{days} days"
    severity: WARNING
    action: "Check for memory leak, plan memory increase"
```

---

## 6. Multi-Skill Orchestration

### 6.1 Diagnosis Flow with Delegation

```yaml
diagnosis_flow:
  step_1_cvm_initial:
    skill: qcloud-cvm-ops
    actions:
      - DescribeInstances (check status)
      - GetMonitorData (collect metrics)
      - analyze_correlation
      
  step_2_delegate_if_needed:
    conditions:
      - if: "disk_issue_detected"
        delegate: qcloud-cbs-ops
        context: {disk_id, instance_id}
        
      - if: "network_issue_detected"
        delegate: qcloud-vpc-ops
        context: {vpc_id, subnet_id, sg_id}
        
      - if: "mysql_connection_issue"
        delegate: qcloud-mysql-ops
        context: {mysql_instance_id}
        
  step_3_integrate_results:
    action: "Combine primary and delegated diagnosis"
    output: unified_diagnosis_report
```

### 6.2 Cross-Skill Correlation

```python
def cross_skill_correlation(
    primary_metrics: Dict,
    delegated_metrics: Dict,
    resource_relationships: Dict
) -> CrossSkillCorrelationResult:
    # Correlate metrics across skills
    
    result = CrossSkillCorrelationResult()
    
    # CVM + CBS correlation
    if 'cbs_metrics' in delegated_metrics:
        cvm_disk_io = primary_metrics.get('DiskIO', {})
        cbs_latency = delegated_metrics['cbs_metrics'].get('DiskLatency', {})
        
        if cvm_disk_io['avg'] > 100 and cbs_latency['avg'] > 10:
            result.correlations.append({
                'type': 'cvm_cbs_io_bottleneck',
                'description': 'High disk I/O on CVM correlates with CBS latency',
                'root_cause': 'CBS performance issue affecting CVM',
                'recommendation': 'Investigate CBS disk performance'
            })
    
    # CVM + CLB correlation
    if 'clb_metrics' in delegated_metrics:
        cvm_cpu = primary_metrics.get('CPUUsage', {})
        clb_backend_health = delegated_metrics['clb_metrics'].get('BackendHealth', {})
        
        if cvm_cpu['avg'] > 80 and clb_backend_health['healthy_count'] < clb_backend_health['total_count']:
            result.correlations.append({
                'type': 'cvm_clb_backend_issue',
                'description': 'CVM CPU high correlates with CLB backend unhealthy',
                'root_cause': 'CVM performance affecting CLB health check',
                'recommendation': 'Address CVM performance or remove from CLB'
            })
    
    return result
```

---

## 7. Integration in CVM Skill

Add AIOps section to SKILL.md:

```markdown
## AIOps Intelligent Diagnosis

### Multi-Metric Correlation

```python
# Correlate CPU and Network metrics
from scipy import stats
correlation = stats.pearsonr(cpu_values, network_values)
```

### Cross-Skill Delegation

| Issue Detected | Delegate To |
|----------------|-------------|
| Disk I/O issue | qcloud-cbs-ops |
| Network connectivity | qcloud-vpc-ops |
| CLB backend issue | qcloud-clb-ops |

### Alarm Storm Detection

> 10 alarms within 5 minutes = alarm storm

Actions:
1. Suppress duplicates
2. Aggregate into single incident
3. Identify root cause
4. Escalate if unresolved

### Fault Prediction

| Metric Trend | Prediction | Action |
|--------------|------------|--------|
| DiskUsage + 2%/day | Full in ~{days} days | Plan expansion |
| MemUsage + 5%/day | OOM in ~{days} days | Check leak |

### References

- [AIOps Best Practices](../qcloud-skill-generator/references/aiops-best-practices.md)
- [Proactive Inspection](proactive-inspection.md)
- [Monitoring Guide](monitoring.md)
```

---

## References

- [AIOps Best Practices](../qcloud-skill-generator/references/aiops-best-practices.md)
- [Proactive Inspection](proactive-inspection.md)
- [Monitoring Guide](monitoring.md)
- [Troubleshooting](troubleshooting.md)