# CVM Proactive Inspection

> **delegate-from:** `qcloud-proactive-inspection` — read-only discovery/collection for **CVM**.
> Output handoff: [inspection-output-schema.md](../../qcloud-proactive-inspection/references/inspection-output-schema.md).
> Architecture scoring → `qcloud-well-architected-review`.

Five-step closed-loop proactive inspection workflow for CVM.

---

## Overview

Proactive inspection follows the **Discovery → Collection → Detection → Diagnosis → Report** pattern to identify issues before they become critical.

---

## 1. Five-Step Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Discovery  │───▶│  Collection │───▶│  Detection  │───▶│  Diagnosis  │───▶│   Report    │
│  (发现)     │    │  (采集)     │    │  (检测)     │    │  (诊断)     │    │  (报告)     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     │                  │                  │                  │                  │
     │                  │                  │                  │                  │
     ▼                  ▼                  ▼                  ▼                  ▼
  发现资源          采集指标          检测异常          诊断根因          生成报告
```

---

## 2. Step 1: Discovery (发现)

### 2.1 Resource Discovery CLI

```bash
# Discover all CVM instances in region
tccli cvm DescribeInstances --Region ap-guangzhou --Limit 100

# Discover instances by tag (Environment=Production)
tccli cvm DescribeInstances \
  --Region ap-guangzhou \
  --Filters '[{"Name":"tag-value","Values":["Production"]}]'
```

### 2.2 Resource Inventory Generation

```python
def discover_cvm_resources(region: str) -> List[Resource]:
    # Discover all CVM resources in region
    client = cvm_client.CvmClient(cred, region)
    
    resources = []
    offset = 0
    limit = 100
    
    while True:
        req = models.DescribeInstancesRequest()
        req.Offset = offset
        req.Limit = limit
        
        resp = client.DescribeInstances(req)
        
        for instance in resp.InstanceSet:
            resources.append({
                'resource_id': instance.InstanceId,
                'resource_name': instance.InstanceName,
                'resource_type': 'CVM',
                'zone': instance.Zone,
                'status': instance.Status,
                'instance_type': instance.InstanceType,
                'cpu': instance.CPU,
                'memory': instance.Memory,
                'tags': {t.Key: t.Value for t in instance.Tags},
                'created_time': instance.CreatedTime,
                'vpc_id': instance.VirtualPrivateCloud.VpcId,
                'subnet_id': instance.VirtualPrivateCloud.SubnetId
            })
        
        if len(resp.InstanceSet) < limit:
            break
        offset += limit
    
    return resources
```

### 2.3 Resource Categorization

```yaml
resource_categories:
  production:
    filters:
      - tag: Environment=Production
    priority: HIGH
    
  staging:
    filters:
      - tag: Environment=Staging
    priority: MEDIUM
    
  development:
    filters:
      - tag: Environment=Development
    priority: LOW
    
  untagged:
    filters:
      - tag: missing
    priority: MEDIUM
    alert: "Untagged resources need categorization"
```

---

## 3. Step 2: Collection (采集)

### 3.1 Metrics Collection CLI

```bash
# Collect CPU usage for last 24h
tccli monitor GetMonitorData \
  --Namespace QCE/CVM \
  --MetricName CPUUsage \
  --Dimensions '[{"Name":"InstanceId","Value":"ins-xxx"}]' \
  --StartTime 2026-05-20T00:00:00+08:00 \
  --EndTime 2026-05-21T00:00:00+08:00 \
  --Period 300

# Collect Memory usage
tccli monitor GetMonitorData \
  --Namespace QCE/CVM \
  --MetricName MemUsage \
  --Dimensions '[{"Name":"InstanceId","Value":"ins-xxx"}]' \
  --StartTime 2026-05-20T00:00:00+08:00 \
  --EndTime 2026-05-21T00:00:00+08:00 \
  --Period 300
```

### 3.2 Batch Collection Script

```python
def collect_metrics_batch(resources: List[Resource], hours: int = 24) -> Dict:
    # Collect metrics for all resources in batch
    monitor_client = monitor_client.MonitorClient(cred, region)
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    metrics_data = {}
    
    for resource in resources:
        instance_id = resource['resource_id']
        
        # Collect CPU, Memory, Network metrics in parallel
        metrics = ['CPUUsage', 'MemUsage', 'NetworkIn', 'NetworkOut']
        
        for metric_name in metrics:
            req = models.GetMonitorDataRequest()
            req.Namespace = "QCE/CVM"
            req.MetricName = metric_name
            req.Dimensions = [{"Name": "InstanceId", "Value": instance_id}]
            req.StartTime = start_time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
            req.EndTime = end_time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
            req.Period = 300
            
            resp = monitor_client.GetMonitorData(req)
            
            if resp.DataPoints:
                values = resp.DataPoints[0].Values
                metrics_data[instance_id][metric_name] = {
                    'max': max(v['Value'] for v in values),
                    'avg': sum(v['Value'] for v in values) / len(values),
                    'samples': len(values)
                }
    
    return metrics_data
```

### 3.3 Core Metrics to Collect

| Category | Metrics | Frequency | Purpose |
|----------|---------|-----------|---------|
| CPU | `CPUUsage` | 5min | Performance bottleneck |
| Memory | `MemUsage` | 5min | Memory pressure |
| Storage | `DiskUsage` (agent) | 5min | Capacity planning |
| Network | `NetworkIn/Out` | 5min | Bandwidth utilization |
| Status | `Status` | 5min | Availability check |

---

## 4. Step 3: Detection (检测)

### 4.1 Threshold Detection

```yaml
thresholds:
  # Critical thresholds
  critical:
    CPUUsage:
      value: 95
      duration: 5m
      action: "Immediate investigation"
      
    MemUsage:
      value: 95
      duration: 5m
      action: "Immediate investigation"
      
    DiskUsage:
      value: 95
      duration: 10m
      action: "Immediate disk expansion"
      
  # Warning thresholds
  warning:
    CPUUsage:
      value: 80
      duration: 30m
      action: "Monitor trend"
      
    MemUsage:
      value: 85
      duration: 30m
      action: "Monitor trend"
      
    DiskUsage:
      value: 80
      duration: 60m
      action: "Plan expansion"
```

### 4.2 Detection Script

```python
def detect_anomalies(metrics_data: Dict, thresholds: Dict) -> List[Anomaly]:
    # Detect anomalies based on thresholds
    anomalies = []
    
    for instance_id, metrics in metrics_data.items():
        # CPU detection
        if metrics['CPUUsage']['max'] >= thresholds['critical']['CPUUsage']['value']:
            anomalies.append(Anomaly(
                resource_id=instance_id,
                metric='CPUUsage',
                severity='CRITICAL',
                value=metrics['CPUUsage']['max'],
                threshold=thresholds['critical']['CPUUsage']['value'],
                recommendation="Immediate investigation - CPU critical"
            ))
        elif metrics['CPUUsage']['avg'] >= thresholds['warning']['CPUUsage']['value']:
            anomalies.append(Anomaly(
                resource_id=instance_id,
                metric='CPUUsage',
                severity='WARNING',
                value=metrics['CPUUsage']['avg'],
                threshold=thresholds['warning']['CPUUsage']['value'],
                recommendation="Monitor CPU trend - potential capacity issue"
            ))
        
        # Memory detection
        if metrics['MemUsage']['max'] >= thresholds['critical']['MemUsage']['value']:
            anomalies.append(Anomaly(
                resource_id=instance_id,
                metric='MemUsage',
                severity='CRITICAL',
                value=metrics['MemUsage']['max'],
                threshold=thresholds['critical']['MemUsage']['value'],
                recommendation="Immediate investigation - Memory critical"
            ))
        
        # Idle detection (CPU avg < 10% for 24h)
        if metrics['CPUUsage']['avg'] < 10:
            anomalies.append(Anomaly(
                resource_id=instance_id,
                metric='CPUUsage',
                severity='INFO',
                value=metrics['CPUUsage']['avg'],
                threshold=10,
                recommendation="Downsize candidate - very low utilization"
            ))
    
    return anomalies
```

### 4.3 Multi-Metric Correlation Detection

```python
def correlate_and_detect(metrics_data: Dict) -> List[CorrelatedAnomaly]:
    # Detect correlated anomalies
    anomalies = []
    
    for instance_id, metrics in metrics_data.items():
        # CPU + Memory correlation
        cpu_high = metrics['CPUUsage']['avg'] > 70
        mem_high = metrics['MemUsage']['avg'] > 70
        
        if cpu_high and mem_high:
            anomalies.append(CorrelatedAnomaly(
                resource_id=instance_id,
                metrics=['CPUUsage', 'MemUsage'],
                severity='HIGH',
                pattern='application_pressure',
                description="CPU and Memory both elevated",
                recommendation="Scale out or optimize application"
            ))
        
        # High CPU + Low Memory (CPU-bound)
        if cpu_high and not mem_high:
            anomalies.append(CorrelatedAnomaly(
                resource_id=instance_id,
                metrics=['CPUUsage'],
                severity='MEDIUM',
                pattern='cpu_bound',
                description="CPU bottleneck, Memory normal",
                recommendation="Increase CPU or optimize compute-heavy tasks"
            ))
        
        # Low CPU + High Memory (Memory-bound)
        if not cpu_high and mem_high:
            anomalies.append(CorrelatedAnomaly(
                resource_id=instance_id,
                metrics=['MemUsage'],
                severity='MEDIUM',
                pattern='memory_bound',
                description="Memory pressure, CPU normal",
                recommendation="Increase Memory or fix memory leak"
            ))
    
    return anomalies
```

---

## 5. Step 4: Diagnosis (诊断)

### 5.1 Diagnosis Decision Tree

```yaml
diagnosis_tree:
  root: check_status
  
  branches:
    - condition: "Status == STOPPED"
      diagnosis: "Instance stopped"
      actions:
        - check_stop_reason
        - check_recent_operations
        - recommend_restart_if_needed
        
    - condition: "Status == RUNNING AND CPUUsage > 90%"
      diagnosis: "CPU_pressure"
      sub_tree: cpu_diagnosis
      
    - condition: "Status == RUNNING AND MemUsage > 90%"
      diagnosis: "memory_pressure"
      sub_tree: memory_diagnosis
      
    - condition: "Status == RUNNING AND DiskUsage > 90%"
      diagnosis: "storage_pressure"
      sub_tree: storage_diagnosis

cpu_diagnosis:
  branches:
    - condition: "NetworkIn high AND CPU high"
      diagnosis: "traffic_spike"
      recommendation: "Scale horizontally or optimize network handling"
      
    - condition: "NetworkIn normal AND CPU high"
      diagnosis: "compute_intensive"
      recommendation: "Optimize application or increase CPU"
      
    - condition: "CPU high AND recent deployment"
      diagnosis: "deployment_issue"
      recommendation: "Check recent code changes"

memory_diagnosis:
  branches:
    - condition: "Memory increasing over time"
      diagnosis: "memory_leak"
      recommendation: "Restart service, analyze memory allocation"
      
    - condition: "Memory stable at high level"
      diagnosis: "insufficient_memory"
      recommendation: "Increase instance memory"
```

### 5.2 Diagnosis Execution

```python
def execute_diagnosis(anomaly: Anomaly, client) -> DiagnosisResult:
    # Execute diagnosis for detected anomaly
    
    # Get detailed instance info
    instance_info = get_instance_details(client, anomaly.resource_id)
    
    # Check recent operations
    recent_ops = get_recent_operations(client, anomaly.resource_id)
    
    # Check logs for errors
    logs = query_instance_logs(anomaly.resource_id, last_hours=1)
    
    # Build diagnosis result
    diagnosis = DiagnosisResult(
        anomaly=anomaly,
        instance_info=instance_info,
        recent_operations=recent_ops,
        log_analysis=analyze_logs(logs),
        root_cause=hypothesize_root_cause(anomaly, instance_info, logs),
        action_plan=generate_action_plan(anomaly, instance_info)
    )
    
    return diagnosis

def generate_action_plan(anomaly: Anomaly, instance_info: Dict) -> List[str]:
    # Generate remediation action plan
    plans = {
        'CRITICAL_CPU': [
            '1. Identify top CPU-consuming processes',
            '2. Check for runaway processes',
            '3. Consider horizontal scaling',
            '4. Optimize compute-intensive tasks'
        ],
        'CRITICAL_MEMORY': [
            '1. Check for memory leaks',
            '2. Review application memory allocation',
            '3. Restart service if leak detected',
            '4. Increase instance memory if needed'
        ],
        'CRITICAL_DISK': [
            '1. Identify large files/directories',
            '2. Clean up logs and temp files',
            '3. Expand disk capacity',
            '4. Review data retention policy'
        ],
        'INFO_IDLE': [
            '1. Verify instance purpose',
            '2. Consider downsizing',
            '3. Delete if truly unused',
            '4. Schedule auto-stop for dev instances'
        ]
    }
    
    key = f"{anomaly.severity}_{anomaly.metric}"
    return plans.get(key, ['Manual investigation required'])
```

---

## 6. Step 5: Report (报告)

### 6.1 Report Template

```markdown
# CVM Proactive Inspection Report

**Generated**: 2026-05-21 10:00:00
**Region**: ap-guangzhou
**Scope**: All Production instances

## Executive Summary

| Metric | Count | Status |
|--------|-------|--------|
| Total Resources | [N] | ✅ |
| Critical Issues | [N] | 🔴 |
| Warning Issues | [N] | 🟡 |
| Optimization Opportunities | [N] | 🟢 |

## Critical Issues (Immediate Action Required)

| Resource | Metric | Value | Threshold | Recommendation |
|----------|--------|-------|-----------|----------------|
| ins-xxx | CPUUsage | 98% | 95% | Immediate investigation |
| ins-yyy | MemUsage | 97% | 95% | Memory pressure detected |

## Warning Issues (Monitor/Plan)

| Resource | Metric | Value | Threshold | Recommendation |
|----------|--------|-------|-----------|----------------|
| ins-aaa | DiskUsage | 85% | 80% | Plan disk expansion |

## Optimization Opportunities

| Resource | Metric | Value | Recommendation | Savings |
|----------|--------|-------|----------------|---------|
| ins-bbb | CPUUsage | avg 15% | Downsize to smaller type | ~30% |
| ins-ccc | Status | STOPPED 7d | Delete or restart | 100% |

## Capacity Planning

| Resource | Current | Trend | Projected (7d) | Action |
|----------|---------|-------|----------------|--------|
| ins-xxx | Disk 70% | +2%/d | 84% | Plan expansion |

## Recommendations Summary

1. **Immediate**: Address critical CPU/Memory issues
2. **Short-term**: Expand disk for warning instances
3. **Cost**: Downsize low-utilization instances
4. **Cleanup**: Delete stopped instances > 7 days
```

### 6.2 Report Generation CLI

```python
def generate_inspection_report(
    resources: List[Resource],
    metrics_data: Dict,
    anomalies: List[Anomaly],
    diagnosis_results: List[DiagnosisResult]
) -> str:
    # Generate inspection report in Markdown
    
    report = []
    
    # Header
    report.append("# CVM Proactive Inspection Report")
    report.append(f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"\n**Region**: {region}")
    report.append(f"\n**Scope**: All instances")
    
    # Summary
    critical_count = sum(1 for a in anomalies if a.severity == 'CRITICAL')
    warning_count = sum(1 for a in anomalies if a.severity == 'WARNING')
    info_count = sum(1 for a in anomalies if a.severity == 'INFO')
    
    report.append("\n## Executive Summary")
    report.append(f"\n- **Total Resources**: {len(resources)}")
    report.append(f"\n- **Critical Issues**: {critical_count} 🔴")
    report.append(f"\n- **Warning Issues**: {warning_count} 🟡")
    report.append(f"\n- **Optimization Opportunities**: {info_count} 🟢")
    
    # Critical issues
    if critical_count > 0:
        report.append("\n## Critical Issues (Immediate Action Required)")
        report.append("\n| Resource | Metric | Value | Threshold | Recommendation |")
        report.append("\n|----------|--------|-------|-----------|----------------|")
        
        for a in anomalies:
            if a.severity == 'CRITICAL':
                report.append(f"\n| {a.resource_id} | {a.metric} | {a.value}% | {a.threshold}% | {a.recommendation} |")
    
    # Warning issues
    if warning_count > 0:
        report.append("\n## Warning Issues (Monitor/Plan)")
        report.append("\n| Resource | Metric | Value | Threshold | Recommendation |")
        report.append("\n|----------|--------|-------|-----------|----------------|")
        
        for a in anomalies:
            if a.severity == 'WARNING':
                report.append(f"\n| {a.resource_id} | {a.metric} | {a.value}% | {a.threshold}% | {a.recommendation} |")
    
    # Optimization opportunities
    if info_count > 0:
        report.append("\n## Optimization Opportunities")
        report.append("\n| Resource | Metric | Value | Recommendation |")
        report.append("\n|----------|--------|-------|----------------|")
        
        for a in anomalies:
            if a.severity == 'INFO':
                report.append(f"\n| {a.resource_id} | {a.metric} | avg {a.value}% | {a.recommendation} |")
    
    return '\n'.join(report)
```

---

## 7. Scheduled Execution

### 7.1 Inspection Schedule

| Frequency | Scope | Focus | Output |
|-----------|-------|-------|--------|
| **Daily** | Production | Critical metrics | Critical alert report |
| **Weekly** | All | Comprehensive | Full inspection report |
| **Monthly** | All | Capacity + Cost | Monthly review report |

### 7.2 Execution Script (Cloud Shell)

```bash
#!/bin/bash
# Daily proactive inspection script
# Save in /data/scripts/daily_inspection.sh

REGION="ap-guangzhou"
OUTPUT_DIR="/data/reports"

# Step 1: Discovery
echo "Step 1: Discovering resources..."
tccli cvm DescribeInstances --Region $REGION --Limit 100 > /tmp/instances.json

# Step 2: Collection
echo "Step 2: Collecting metrics..."
INSTANCE_IDS=$(cat /tmp/instances.json | jq -r '.Response.InstanceSet[].InstanceId')

for ID in $INSTANCE_IDS; do
  tccli monitor GetMonitorData \
    --Namespace QCE/CVM \
    --MetricName CPUUsage \
    --Dimensions "[{\"Name\":\"InstanceId\",\"Value\":\"$ID\"}]" \
    --StartTime "$(date -d '-24 hours' +'%Y-%m-%dT%H:%M:%S+08:00')" \
    --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')" \
    --Period 300 > /tmp/metrics_$ID.json
done

# Step 3: Detection
echo "Step 3: Detecting anomalies..."
python3 /data/scripts/detect_anomalies.py > /tmp/anomalies.json

# Step 4: Diagnosis
echo "Step 4: Diagnosing issues..."
python3 /data/scripts/diagnose.py > /tmp/diagnosis.json

# Step 5: Report
echo "Step 5: Generating report..."
python3 /data/scripts/generate_report.py > $OUTPUT_DIR/inspection_$(date +%Y%m%d).md

echo "Inspection complete. Report saved to $OUTPUT_DIR"
```

---

---

## References

- [AIOps Best Practices](../qcloud-skill-generator/references/aiops-best-practices.md)
- [Monitoring Guide](monitoring.md)
- [Well-Architected Assessment](well-architected-assessment.md)