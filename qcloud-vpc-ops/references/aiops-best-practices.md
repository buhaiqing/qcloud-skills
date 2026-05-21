# VPC AIOps Best Practices Module

## 1. Multi-Metric Correlation

### VPC Correlation Patterns

| Pattern | Primary Metric | Secondary Metrics | Diagnosis |
|---------|---------------|-------------------|-----------|
| NAT Saturation | NATConnections | BandwidthOut, ErrorRate | NAT capacity limit |
| VPN Latency | VPNLatency | PacketLoss, Jitter | VPN quality issue |
| Subnet Overload | SubnetIPUsage | InstanceCount, AvailableIPs | IP exhaustion |

### Correlation Implementation

```python
import numpy as np

def correlate_vpc_metrics(metrics: dict) -> dict:
    correlations = {}
    
    nat_conn = metrics.get('NATConnections', [])
    bandwidth = metrics.get('BandwidthOut', [])
    
    if len(nat_conn) > 0 and len(bandwidth) > 0:
        correlation = np.corrcoef(nat_conn, bandwidth)[0, 1]
        correlations['nat_bandwidth'] = {
            'value': correlation,
            'interpretation': interpret_correlation(correlation)
        }
    
    return correlations

def interpret_correlation(value: float) -> str:
    if value > 0.7:
        return 'Strong correlation - likely same root cause'
    elif value > 0.3:
        return 'Moderate correlation - partially related'
    else:
        return 'No correlation - independent'
```

## 2. Cross-Skill Diagnosis Decision Tree

### VPC Diagnosis Tree

```yaml
vpc_diagnosis_tree:
  root: connectivity_check
  
  branches:
    - condition: "issue == 'connectivity'"
      diagnosis: network_connectivity
      sub_branches:
        - condition: "instance_in_subnet == false"
          diagnosis: subnet_issue
          delegate: qcloud-cvm-ops
        
        - condition: "nat_gateway_state != AVAILABLE"
          diagnosis: nat_gateway_issue
          actions: [check_nat_status, restart_nat]
        
        - condition: "acl_blocks_traffic"
          diagnosis: acl_configuration
          actions: [review_acl_rules, modify_acl]
    
    - condition: "issue == 'ip_exhaustion'"
      diagnosis: subnet_capacity
      actions: [check_available_ips, expand_cidr, create_subnet]
    
    - condition: "issue == 'routing'"
      diagnosis: route_table_issue
      actions: [check_routes, verify_next_hop]
```

### Decision Tree Implementation

```python
class VPCDiagnosisTree:
    def diagnose(self, issue: str, metrics: dict) -> dict:
        tree = self._load_tree()
        
        for branch in tree['branches']:
            if self._check_condition(branch['condition'], {'issue': issue, **metrics}):
                diagnosis = branch['diagnosis']
                
                if 'delegate' in branch:
                    return {
                        'diagnosis': diagnosis,
                        'delegate_to': branch['delegate'],
                        'context': metrics
                    }
                
                return {
                    'diagnosis': diagnosis,
                    'actions': branch.get('actions', [])
                }
        
        return {'diagnosis': 'unknown', 'actions': ['gather_more_metrics']}
```

## 3. Delegation Matrix

### VPC Delegation Matrix

| Issue Type | Delegate To | Context |
|------------|-------------|---------|
| CVM connectivity | qcloud-cvm-ops | Subnet ID, Instance ID |
| CLB backend issue | qcloud-clb-ops | VPC ID, Subnet IDs |
| MySQL network issue | qcloud-mysql-ops | VPC ID, Subnet ID |
| CBS attachment | qcloud-cbs-ops | Instance ID, Disk ID |

### Delegation Protocol

```markdown
**Delegation Example:**

When VPC connectivity issue involves CVM:

Invoke: qcloud-cvm-ops
Context: {
  "issue": "CVM connectivity",
  "subnet_id": "subnet-xxx",
  "vpc_id": "vpc-xxx",
  "instance_id": "ins-xxx"
}

Collect: CVM diagnosis results
Integrate: Combine VPC network + CVM instance diagnosis
```

## 4. Proactive Inspection

### VPC Inspection Schedule

| Category | Frequency | Checks |
|----------|-----------|--------|
| Daily | 24h | VPC state, subnet IP usage, NAT status |
| Weekly | 7d | ACL rules review, security group audit |
| Monthly | 30d | CIDR planning review, cost analysis |

### Proactive Inspection Flow

```yaml
vpc_inspection_flow:
  stages:
    - discovery:
        action: discover_vpcs
        output: vpc_inventory
    
    - collection:
        action: collect_vpc_metrics
        output: metrics_dataset
    
    - detection:
        action: detect_vpc_anomalies
        anomalies:
          - subnet_ip_exhaustion: AvailableIPCount < 10
          - nat_connection_limit: Connections > 10000
          - unused_flow_log: FlowLogState == disabled
    
    - report:
        action: generate_inspection_report
        output: vpc_health_report
```

### Proactive Alert Rules

```yaml
vpc_alerts:
  - name: subnet_ip_exhaustion
    condition: "AvailableIPCount < 10"
    severity: warning
    message: "Subnet approaching IP exhaustion"
    action: "Create new subnet or expand CIDR"
  
  - name: nat_connection_limit
    condition: "NATConnections > 10000"
    severity: warning
    message: "NAT gateway connection limit approaching"
    action: "Monitor or scale NAT"
  
  - name: flow_log_disabled
    condition: "FlowLogState != enabled"
    severity: medium
    message: "VPC Flow Logs not enabled"
    action: "Enable Flow Logs for security monitoring"
```

## 5. Alarm Storm Handling

### Alarm Storm Definition

**VPC Alarm Storm**: > 10 VPC-related alarms within 5 minutes.

### Alarm Storm Detection

```python
def detect_vpc_alarm_storm(alarm_events: list) -> dict:
    recent_alarms = [a for a in alarm_events if a['timestamp'] > datetime.now() - timedelta(minutes=5)]
    
    vpc_alarms = [a for a in recent_alarms if 'vpc' in a['resource_type'].lower()]
    
    if len(vpc_alarms) > 10:
        return {
            'storm': True,
            'alarm_count': len(vpc_alarms),
            'alarm_types': set(a['alarm_type'] for a in vpc_alarms),
            'root_cause_hint': correlate_alarm_sources(vpc_alarms)
        }
    
    return {'storm': False}
```

### Alarm Storm Handling

```yaml
vpc_alarm_storm_handling:
  actions:
    - suppress_duplicates:
        duration: 5m
        condition: same_vpc AND same_metric
    
    - aggregate:
        action: Create single incident
    
    - root_cause:
        action: Correlate alarms to identify common source
    
    - escalate:
        action: Alert on-call if unresolved in 10m
  
  notification:
    storm_detected: "⚠️ VPC alarm storm: {count} alarms for {vpc_id}"
    root_cause: "Root cause: {diagnosis}"
```

## AIOps Compliance Checklist

| Requirement | Status | Location |
|-------------|--------|----------|
| Multi-metric correlation | ✓ | references/aiops-best-practices.md |
| Diagnosis decision tree | ✓ | references/aiops-best-practices.md |
| Delegation matrix | ✓ | SKILL.md Trigger & Scope |
| Proactive inspection | ✓ | references/aiops-best-practices.md |
| Alarm storm handling | ✓ | references/aiops-best-practices.md |

## References

- [AIOps Best Practices](../qcloud-skill-generator/references/aiops-best-practices.md)