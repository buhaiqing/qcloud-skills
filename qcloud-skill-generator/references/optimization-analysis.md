# Optimization Analysis Framework

Three-dimensional optimization framework for Tencent Cloud skills: Fault Diagnosis, Root Cause Localization, Rapid Resolution.

---

## Overview

Every generated skill MUST consider optimization across three dimensions:

1. **Fault Diagnosis Dimension** (故障诊断维度)
2. **Root Cause Localization Dimension** (根因定位维度)
3. **Rapid Resolution Dimension** (快速恢复维度)

---

## Dimension 1: Fault Diagnosis (故障诊断)

### 1.1 Diagnosis Flow

```
Symptom Detection → Metric Analysis → Log Correlation → Diagnosis Conclusion
```

### 1.2 Symptom Categories

| Category | Symptoms | Detection Method |
|----------|----------|------------------|
| Performance | Slow response, high latency | Metric threshold breach |
| Availability | Connection failed, timeout | Health check failure |
| Capacity | Quota exceeded, disk full | Quota/disk monitoring |
| Security | Access denied, unauthorized | CAM audit logs |

### 1.3 Multi-Metric Correlation

| Primary Metric | Correlated Metrics | Diagnosis Pattern |
|---------------|-------------------|-------------------|
| CPUUsage ↑ | NetworkIn ↑, TrafficOut ↑ | Traffic spike → CPU pressure |
| CPUUsage ↑ | MemUsage stable | Application CPU-intensive |
| CPUUsage ↑ | MemUsage ↑, DiskIO ↑ | Full system pressure |
| MemUsage ↑ | OOM errors in logs | Memory leak or undersized |
| DiskUsage ↑ | DiskIO latency ↑ | I/O bottleneck |

### 1.4 Diagnosis Decision Tree

```yaml
symptom_type: performance
  ↓
check_cpu_metric:
  - if CPUUsage > 90%:
    → check_network:
      - if NetworkIn high: diagnose_traffic_spike
      - else: diagnose_app_performance
  - if CPUUsage normal:
    → check_memory:
      - if MemUsage > 90%: diagnose_memory_issue
      - else: check_disk_io
```

### 1.5 Diagnosis Templates

```python
# Diagnosis template structure
diagnosis_template = {
    'symptom': 'High CPU usage',
    'metrics': ['CPUUsage', 'NetworkIn', 'MemUsage'],
    'thresholds': {'CPUUsage': 90, 'MemUsage': 85},
    'correlation_rules': [
        ('CPUUsage > 90 AND NetworkIn high', 'Traffic spike'),
        ('CPUUsage > 90 AND MemUsage normal', 'App CPU-bound'),
        ('CPUUsage > 90 AND MemUsage > 85', 'System pressure'),
    ],
    'diagnosis_actions': [
        'Check application logs for errors',
        'Review recent deployment changes',
        'Analyze traffic patterns',
        'Check resource sizing',
    ]
}
```

---

## Dimension 2: Root Cause Localization (根因定位)

### 2.1 Root Cause Categories

| Category | Root Causes | Localization Method |
|----------|-------------|---------------------|
| Infrastructure | Resource undersized, quota limit | Capacity analysis |
| Application | Code bug, memory leak, N+1 query | Log + APM analysis |
| Configuration | Wrong parameter, security group | Config diff |
| External | Network issue, upstream failure | Dependency check |

### 2.2 Localization Flowchart

```
Diagnosis Result → Scope Definition → Layer Analysis → Root Cause Identified

Layers:
├── L1: User/Application
├── L2: Service/Container
├── L3: Infrastructure/VM
├── L4: Network/VPC
├── L5: Platform/Cloud API
```

### 2.3 Evidence Chain

```markdown
**Root Cause Evidence Chain Template:**

1. **Observation**: [Symptom observed]
   - Metric: [Metric name and value]
   - Time: [When it occurred]
   
2. **Analysis**: [Analysis performed]
   - Log pattern: [What was found in logs]
   - Metric correlation: [Correlated metrics]
   
3. **Layer Determination**: [Which layer]
   - Evidence: [Why this layer]
   - Elimination: [Why other layers ruled out]
   
4. **Root Cause**: [Final determination]
   - Specific cause: [What caused it]
   - Confidence: [High/Medium/Low]
   
5. **Supporting Evidence**: [Additional proof]
   - Historical data: [Similar incidents]
   - Change events: [Recent changes]
```

### 2.4 Root Cause Localization Templates

```python
# Root cause localization for CPU high
root_cause_template_cpu = {
    'symptom': 'CPUUsage > 90%',
    'layers': {
        'L1_Application': {
            'check': 'Application logs for slow queries',
            'evidence': 'N+1 queries, inefficient loops',
        },
        'L2_Service': {
            'check': 'Service throughput and error rate',
            'evidence': 'High QPS, elevated error rate',
        },
        'L3_Infrastructure': {
            'check': 'Instance CPU count vs demand',
            'evidence': 'CPU undersized for workload',
        },
        'L4_Network': {
            'check': 'Network throughput and latency',
            'evidence': 'Network saturation',
        },
        'L5_Platform': {
            'check': 'Platform health and incidents',
            'evidence': 'Platform degraded',
        }
    },
    'decision_logic': [
        ('Application logs show errors', 'L1_Application'),
        ('High QPS with errors', 'L2_Service'),
        ('CPU undersized', 'L3_Infrastructure'),
        ('Network saturated', 'L4_Network'),
        ('Platform incident', 'L5_Platform'),
    ]
}
```

---

## Dimension 3: Rapid Resolution (快速恢复)

### 3.1 Resolution Strategies

| Strategy | When to Use | Actions |
|----------|-------------|---------|
| Immediate Fix | High severity, known fix | Apply fix immediately |
| Scaling | Capacity issue | Upsize or scale out |
| Restart | Service hang/crash | Restart service |
| Rollback | Recent change caused | Rollback change |
| Isolation | Cascading failure | Isolate affected resource |

### 3.2 Resolution Flowchart

```
Root Cause → Resolution Strategy → Implementation → Verification → Closure

Resolution Strategies:
├── Immediate Fix
│   ├── Apply configuration change
│   ├── Restart service
│   └── Clear cache
│
├── Scaling
│   ├── Vertical: Increase instance size
│   ├── Horizontal: Add instances
│   └── Storage: Expand disk
│
├── Rollback
│   ├── Configuration rollback
│   ├── Code rollback
│   └── Data rollback
│
├── Isolation
│   ├── Drain traffic
│   ├── Stop affected resource
│   └── Activate standby
```

### 3.3 Resolution Templates

```markdown
**Resolution Template:**

**Strategy**: [Selected strategy]

**Pre-conditions**:
- [ ] Root cause confirmed: [Root cause]
- [ ] Resolution impact assessed: [Impact]
- [ ] Rollback plan prepared: [Rollback steps]

**Execution Steps**:
1. [Step 1 - Preparation]
2. [Step 2 - Implementation]
3. [Step 3 - Verification]
4. [Step 4 - Monitoring]

**Verification**:
- Check: [What to verify]
- Metric: [Which metric to monitor]
- Threshold: [Success threshold]

**Rollback (if failed)**:
1. [Rollback step 1]
2. [Rollback step 2]
```

### 3.4 Resolution SLA Matrix

| Severity | Diagnosis | Root Cause | Resolution | Total |
|----------|-----------|------------|------------|-------|
| P1 (Critical) | 5 min | 5 min | 10 min | 20 min |
| P2 (High) | 15 min | 10 min | 30 min | 55 min |
| P3 (Medium) | 30 min | 15 min | 60 min | 105 min |
| P4 (Low) | 60 min | 30 min | 120 min | 210 min |

---

## Integration in Generated Skills

### Skill Optimization Section Template

```markdown
## Optimization Analysis

This skill integrates three-dimensional optimization:

### Fault Diagnosis Integration

| Metric | Threshold | Diagnosis Action |
|--------|-----------|------------------|
| [Metric1] | > [Threshold] | [Diagnosis step] |
| [Metric2] | > [Threshold] | [Diagnosis step] |

### Root Cause Localization

When [Condition], check:
- **L1 (Application)**: [Check items]
- **L2 (Service)**: [Check items]
- **L3 (Infrastructure)**: [Check items]

### Rapid Resolution

| Scenario | Strategy | Actions |
|----------|----------|---------|
| [Scenario1] | [Strategy] | [Actions] |
| [Scenario2] | [Strategy] | [Actions] |
```

---

## Metrics and Measurement

### Optimization Effectiveness Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| MTTR (Mean Time To Resolve) | < 30 min (P1) | Resolution time tracking |
| Diagnosis accuracy | > 90% | Correct diagnosis rate |
| Root cause hit rate | > 85% | First attempt correct |
| Resolution success rate | > 95% | Successful resolution rate |

---

## References

- [Tencent Cloud Monitoring Best Practices](https://cloud.tencent.com/document/product/248)
- [AIOps Best Practices](aiops-best-practices.md)