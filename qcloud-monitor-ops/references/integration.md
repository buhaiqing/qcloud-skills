# Monitor Integration

## Overview

SDK setup, environment configuration, and cross-skill integration for Monitor.

---

## Environment Setup

### Required Environment Variables

```bash
export TENCENTCLOUD_SECRET_ID="your-secret-id"
export TENCENTCLOUD_SECRET_KEY="your-secret-key"  # NEVER print this value
export TENCENTCLOUD_REGION="ap-guangzhou"
```

### Python SDK Installation

```bash
pip install tencentcloud-sdk-python-monitor

# Verify
python -c "from tencentcloud.monitor.v20180317 import monitor_client; print('✅ Monitor SDK installed')"
```

---

## Cross-Skill Integration

### Monitor as Hub

Monitor skill is the **observability hub** connecting all product skills.

```yaml
monitor_integration_hub:
  inbound:
    - All product metrics flow to Monitor
    - Alarm policies delegate to product skills
    
  outbound:
    - Alarm triggers → delegate to product skill
    - Metric anomaly → diagnose with product skill
    - Proactive inspection → invoke all skills
```

### Delegation Matrix (From Monitor)

| Alarm Trigger | Delegate To | Context |
|---------------|-------------|---------|
| QCE/CVM CPUUsage alarm | `qcloud-cvm-ops` | InstanceId, CPU metrics |
| QCE/LB_PUBLIC HealthStatus | `qcloud-clb-ops` | LoadBalancerId, backend status |
| QCE/CDB SlowQuery | `qcloud-mysql-ops` | DB instance ID, slow query log |
| QCE/REDIS memory | `qcloud-redis-ops` | Redis instance ID |
| QCE/VPC network | `qcloud-vpc-ops` | VPC ID, flow metrics |

---

## Integration Flow

```yaml
alarm_triggered_flow:
  step_1_detect:
    skill: qcloud-monitor-ops
    action: detect_alarm_triggered
    output: alarm_record
    
  step_2_classify:
    skill: qcloud-monitor-ops
    action: classify_namespace
    input: alarm_record
    output: target_skill
    
  step_3_delegate:
    skill: [target_skill]  # e.g., qcloud-cvm-ops
    action: diagnose_alarm
    input: alarm_context
    output: diagnosis
    
  step_4_report:
    skill: qcloud-monitor-ops
    action: update_alarm_history
    input: diagnosis
    output: alarm_resolution
```

---

## Namespace to Skill Mapping

| Namespace | Product Skill | Key Delegation Triggers |
|-----------|---------------|------------------------|
| `QCE/CVM` | `qcloud-cvm-ops` | CPUUsage, MemUsage, DiskUsage alarms |
| `QCE/LB_PUBLIC` | `qcloud-clb-ops` | HealthStatus, HttpCode5XX alarms |
| `QCE/CDB` | `qcloud-mysql-ops` | SlowQuery, Connection alarms |
| `QCE/REDIS` | `qcloud-redis-ops` | CmdExecuteCount, CacheHitRate alarms |
| `QCE/VPC` | `qcloud-vpc-ops` | Flow metrics, EIP alarms |
| `QCE/CBS` | `qcloud-cvm-ops` | DiskUsage alarms (CBS attached to CVM) |

---

## Authentication

### CAM Policy for Monitor

```json
{
  "version": "2.0",
  "statement": [
    {
      "action": [
        "monitor:Describe*",
        "monitor:CreateAlarmPolicy",
        "monitor:ModifyAlarmPolicy*",
        "monitor:DeleteAlarmPolicy"
      ],
      "effect": "allow",
      "resource": "*"
    }
  ]
}
```

---

## Proactive Inspection Integration

### Multi-Skill Inspection

```python
def run_proactive_inspection():
    """Proactive inspection invoking all skills"""
    # Discovery phase
    resources = discover_all_resources()  # Monitor
    
    # Collection phase - invoke all product skills
    metrics = {}
    for namespace, instances in resources.items():
        skill = get_skill_for_namespace(namespace)
        metrics[namespace] = skill.collect_metrics(instances)
    
    # Detection phase - Monitor
    anomalies = detect_anomalies(metrics)
    
    # Diagnosis phase - delegate to product skills
    diagnoses = []
    for anomaly in anomalies:
        skill = get_skill_for_namespace(anomaly.namespace)
        diagnoses.append(skill.diagnose(anomaly))
    
    # Report phase - Monitor
    return generate_report(diagnoses)
```

---

## Alarm Policy Integration

### Product-Specific Policy Templates

```yaml
# CVM Alarm Policy Template
cvm_policy_template:
  namespace: QCE/CVM
  metrics:
    - CPUUsage
    - MemUsage
    - DiskUsage
  thresholds:
    warning: 80%
    critical: 90%
  delegate_on_trigger: qcloud-cvm-ops

# CLB Alarm Policy Template  
clb_policy_template:
  namespace: QCE/LB_PUBLIC
  metrics:
    - HealthCheckFailedNum
    - HttpCode5XX
  thresholds:
    warning: 5
    critical: 20
  delegate_on_trigger: qcloud-clb-ops
```

---

## Best Practices

### Notification Integration

| Channel | Integration | When to Use |
|---------|-------------|-------------|
| Webhook | CI/CD, automation | All critical alerts |
| SMS | Emergency | Level 3 alarm storms |
| Email | Reports | Daily summaries |
| WeChat Work | Team alerts | Level 1-2 alarms |

### Alarm Storm Coordination

```yaml
alarm_storm_coordination:
  level_1:
    monitor_action: aggregate_alarms
    product_skills: receive_context
    
  level_2:
    monitor_action: suppress_escalate
    product_skills: diagnose_concurrent
    
  level_3:
    monitor_action: emergency_mode
    product_skills: all_skills_diagnose
```