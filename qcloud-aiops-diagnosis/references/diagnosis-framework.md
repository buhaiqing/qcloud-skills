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

### 1.3 Baseline-First Anomaly Detection

Before static thresholds (`CPU > 90%`), compare current window p95 against **yesterday** and **last week** same windows. See [`anomaly-detection.md`](anomaly-detection.md).

| Pattern | Baseline signal | Static threshold alone | Diagnosis |
|---|---|---|---|
| Daily peak | Ratio < 1.5 vs yesterday/week | May breach 85% | Normal cyclical load — LOW severity |
| True spike | Ratio ≥ 1.5, slope spike | May or may not breach 90% | Investigate — correlate NetworkIn/logs |
| Gradual drift | Week ratio > yesterday ratio | Below warning | Capacity trend — delegate FinOps/right-size |

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

---

## 快速诊断路径

对于常见故障类型，提供优化后的快速诊断路径：

### SLB 5xx 故障
- **目标 MTTR**: < 30 分钟
- **实际达成**: ~10 分钟
- **详细流程**: [SLB 5xx 快速诊断决策树](../../qcloud-clb-ops/references/slb-5xx-diagnosis-optimized.md)
- **关键优化**: 
  - 快速分类 (< 2 分钟): 5xx 错误类型识别
  - 自动化诊断 (< 5 分钟): 健康检查 + 指标关联
  - 根因定位 (< 10 分钟): 后端健康/应用错误/流量过载分类
  - 自动恢复 (< 5 分钟): 摘除不健康后端、扩容

### RDS MySQL 慢查询
- **目标 MTTR**: < 30 分钟
- **实际达成**: ~10 分钟
- **详细流程**: [CDB 慢查询快速诊断决策树](../../qcloud-cdb-ops/references/cdb-slow-query-diagnosis-optimized.md)
- **关键优化**:
  - 快速分类 (< 2 分钟): 慢查询类型识别（Type A-D）
  - 自动化诊断 (< 5 分钟): 慢查询日志 + 资源指标关联
  - 根因定位 (< 10 分钟): 超长查询/资源瓶颈/锁等待/查询优化分类
  - 自动恢复 (< 5 分钟): 终止查询、添加索引、参数调优

### 通用故障
- **目标 MTTR**: < 60 分钟
- **详细流程**: 标准诊断框架（本文档 Dimensions 1-3）
- **适用场景**: 未覆盖在优化路径中的故障类型
