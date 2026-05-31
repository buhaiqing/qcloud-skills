# Diagnosis Framework — AIOps Three-Dimensional Optimization

## Dimension 1: Fault Diagnosis (故障诊断)

### 1.1 Symptom Categories

| Category | Symptoms | Detection Method |
|----------|----------|------------------|
| Performance | Slow response, high latency, CPU/memory spike | Metric threshold breach |
| Availability | Connection failed, timeout, health check failure | Health check failure |
| Capacity | Quota exceeded, disk full, bandwidth limit | Quota/disk monitoring |
| Security | Access denied, unauthorized API calls | CAM audit logs |

### 1.2 Multi-Metric Correlation

| Primary Metric | Correlated Metrics | Diagnosis Pattern |
|---------------|-------------------|-------------------|
| CPUUsage ↑ | NetworkIn ↑, TrafficOut ↑ | Traffic spike → CPU pressure |
| CPUUsage ↑ | MemUsage stable | Application CPU-intensive |
| CPUUsage ↑ | MemUsage ↑, DiskIO ↑ | Full system pressure |
| MemUsage ↑ | OOM errors in logs | Memory leak or undersized |
| DiskUsage ↑ | DiskIO latency ↑ | I/O bottleneck |

## Dimension 2: Root Cause Localization (根因定位)

### 2.1 Decision Tree Template

```
symptom_type: performance
  check_cpu_metric:
    if CPUUsage > 90%:
      check_network:
        if NetworkIn high: diagnose_traffic_spike
        else: diagnose_app_performance
    if CPUUsage normal:
      check_memory:
        if MemUsage > 90%: diagnose_memory_issue
        else: check_disk_io
```

### 2.2 Localization Rules

| Symptom | Primary Check | Secondary Check | Root Cause |
|---------|--------------|-----------------|------------|
| CPU spike | NetworkIn | Process list | Traffic spike OR CPU-bound process |
| Memory spike | OOM logs | Cache size | Memory leak OR cache growth |
| Connection refused | Port status | Security group | Service down OR firewall block |
| Timeout | Latency metrics | Upstream health | Network latency OR upstream failure |
| Disk full | Large files | Log rotation | Unrotated logs OR data growth |

## Dimension 3: Rapid Resolution (快速恢复)

### 3.1 Recovery Priority

1. **Restore service** first (restart, scale out, failover)
2. **Root cause fix** second (code fix, configuration change)
3. **Prevent recurrence** third (alert rule, automation, runbook)

### 3.2 Resolution Patterns

| Problem | Immediate Fix | Root Cause Fix | Prevention |
|---------|--------------|----------------|------------|
| CPU spike | Scale out horizontally | Optimize hot code | Auto-scaling policy |
| Memory leak | Restart instance | Fix leak in code | Memory monitoring |
| Disk full | Delete temp files | Implement rotation | Disk usage alerts |
| Connection storm | Rate limit upstream | Fix connection pool | Connection monitoring |
| DB slow | Kill slow queries | Add index, optimize SQL | Slow query alerts |
