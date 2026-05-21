# CLB AIOps Best Practices

## Overview

CLB-specific AIOps patterns for monitoring, diagnosis, and proactive inspection.

---

## 1. Multi-Metric Correlation for CLB

### Correlation Matrix

| Primary Metric | Secondary Metrics | Correlation Logic |
|----------------|-------------------|-------------------|
| ClientConnum ↑ | TrafficOut ↑, CPUUsage ↑ | Traffic spike |
| HttpCode5XX ↑ | HealthCheckFailedNum ↑ | Backend failure |
| ConnectionTimeout ↑ | BackendResponseTime ↑ | Backend slow |
| TrafficOut ↓ | ClientConnum stable | Backend throttling |

### Diagnostic Patterns

```yaml
clb_correlation_rules:
  - name: backend_health_failure
    condition: "HttpCode5XX ↑ AND HealthCheckFailedNum ↑"
    diagnosis: "Backend servers unhealthy"
    resolution: "Check backend health, restart failed instances"
    delegate_to: qcloud-cvm-ops
    
  - name: traffic_bottleneck
    condition: "ClientConnum ↑ AND TrafficOut NOT ↑"
    diagnosis: "Backend throughput limited"
    resolution: "Scale backend instances or optimize backend"
    
  - name: ssl_certificate_issue
    condition: "HTTPS connections ↓ AND SSL errors ↑"
    diagnosis: "SSL certificate problem"
    resolution: "Check cert expiry, renew certificate"
```

---

## 2. Cross-Skill Diagnosis Decision Tree

### CLB Diagnosis Tree

```yaml
clb_diagnosis_tree:
  root: check_lb_status
  
  branches:
    - condition: "LB Status != 2"
      diagnosis: lb_not_running
      actions: [wait_for_creation, check_error]
      
    - condition: "Listeners empty"
      diagnosis: no_listener
      actions: [create_listener]
      
    - condition: "Targets empty"
      diagnosis: no_backend
      actions: [register_targets]
      
    - condition: "HealthCheckFailedNum > 0"
      diagnosis: backend_unhealthy
      delegate_to: qcloud-cvm-ops
      delegate_context:
        issue: "Backend server health check failed"
        check: [backend_app_status, backend_port, security_group]
      
    - condition: "HttpCode5XX > threshold"
      diagnosis: backend_error
      delegate_to: qcloud-cvm-ops
      delegate_context:
        issue: "Backend returning 5XX errors"
        check: [app_logs, backend_health]
```

---

## 3. Delegation Matrix

### CLB Delegation

| Issue Detected | Delegate To | Trigger Condition |
|----------------|-------------|-------------------|
| Backend server unhealthy | `qcloud-cvm-ops` | HealthCheckFailedNum > 0 |
| Backend port not responding | `qcloud-cvm-ops` | Connection refused |
| Backend app error | `qcloud-cvm-ops` | HttpCode5XX spikes |
| VPC/Subnet issue | `qcloud-vpc-ops` | LB creation fails (VPC error) |
| SSL certificate issue | `qcloud-ssl-ops` | HTTPS listener fails |

### Delegation Protocol

```markdown
**CLB → CVM Delegation:**

When backend health check fails:

1. Prepare Context:
   - Backend InstanceId: [ins-xxx]
   - Issue: Health check failed for port [8080]
   - LB Listener: [listener-xxx]
   
2. Invoke qcloud-cvm-ops:
   - Check instance status
   - Check port binding
   - Check security group rules
   
3. Collect Results:
   - Instance status: RUNNING/STOPPED
   - Port [8080]: Open/Closed
   - Security Group: Allow CLB VIP
   
4. Integrate:
   - If STOPPED → Start instance
   - If port closed → Check backend app
   - If SG blocks → Add CLB VIP to SG
```

---

## 4. Proactive Inspection for CLB

### Daily Checks

| Check | Metric | Threshold | Action |
|-------|--------|-----------|--------|
| Backend health | HealthCheckFailedNum | > 0 | Investigate failed backends |
| Connection health | ClientConnum | Trend check | Monitor traffic patterns |
| Error rate | HttpCode4XX + HttpCode5XX | > 1% | Check backend apps |

### Weekly Checks

| Check | Metric | Threshold | Action |
|-------|--------|-----------|--------|
| Certificate expiry | SSL cert expiry date | < 30 days | Renew certificate |
| Idle backends | Target weight = 0 | > 0 | Review or remove |
| Capacity trend | ClientConnum trend | Growth > 20% | Plan scaling |

### Inspection Flow

```yaml
clb_inspection_flow:
  stages:
    - name: discovery
      action: describe_all_lbs
      output: lb_inventory
      
    - name: listener_collection
      action: describe_all_listeners
      input: lb_inventory
      output: listener_metrics
      
    - name: backend_health_collection
      action: describe_target_health
      input: lb_inventory
      output: health_status
      
    - name: detection
      action: detect_anomalies
      input: [listener_metrics, health_status]
      output: anomaly_list
      
    - name: diagnosis
      action: diagnose_anomalies
      input: anomaly_list
      output: diagnosis_results
      
    - name: report
      action: generate_clb_inspection_report
      output: inspection_report
```

---

## 5. Alarm Storm Handling

### Alarm Storm Definition for CLB

**CLB Alarm Storm**: > 5 backend health alarms within 5 minutes for same LB.

### Handling Actions

```yaml
clb_alarm_storm_handling:
  detection:
    condition: "HealthCheckFailedNum alarms > 5 in 5min for same LB"
    
  actions:
    - name: aggregate_alarms
      action: "Group all backend health alarms into single incident"
      
    - name: identify_pattern
      action: "Check if all backends affected or subset"
      
    - name: root_cause_analysis
      patterns:
        - all_backends: "Network/VPC issue or LB configuration"
        - subset_backends: "Specific backend issue"
        
    - name: suppress_duplicates
      action: "Suppress repeated health alarms for 10 minutes"
      
  delegation:
    condition: "Pattern suggests backend issue"
    delegate_to: qcloud-cvm-ops
    context: "Multiple backend health failures detected"
```

---

## AIOps Compliance Checklist

| Requirement | CLB Implementation | Location |
|-------------|--------------------|----------|
| Multi-metric correlation | ✓ CLB correlation matrix | This document |
| Diagnosis decision tree | ✓ CLB diagnosis tree | This document |
| Delegation matrix | ✓ CLB → CVM/VPC delegation | This document |
| Proactive inspection | ✓ Daily/Weekly checks | This document |
| Alarm storm handling | ✓ Health alarm aggregation | This document |