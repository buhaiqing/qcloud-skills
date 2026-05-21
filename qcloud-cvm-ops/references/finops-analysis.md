# CVM FinOps Analysis

Cost optimization, anomaly detection, RI recommendations, and idle resource analysis for CVM.

---

## Overview

FinOps for CVM focuses on:
1. Cost anomaly detection
2. Right-sizing recommendations
3. Reserved Instance optimization
4. Idle resource cost analysis
5. Monthly cost report generation

---

## 1. Cost Query CLI

### 1.1 Price Inquiry

```bash
# Query instance creation price (postpaid)
tccli cvm InquiryPriceRunInstances \
  --Region ap-guangzhou \
  --Placement '{"Zone":"ap-guangzhou-3"}' \
  --InstanceType S5.LARGE4 \
  --InstanceChargeType POSTPAID_BY_HOUR

# Query prepaid price (1 year)
tccli cvm InquiryPriceRunInstances \
  --Region ap-guangzhou \
  --InstanceType S5.LARGE4 \
  --InstanceChargeType PREPAID \
  --InstanceChargePrepaid '{"Period":12}'
```

### 1.2 Price Comparison Table

```bash
# Generate price comparison for all instance types in zone
for TYPE in S5.SMALL1 S5.SMALL2 S5.MEDIUM2 S5.MEDIUM4 S5.LARGE4 S5.LARGE8 S5.2XLARGE16; do
  echo "Instance Type: $TYPE"
  tccli cvm InquiryPriceRunInstances \
    --Region ap-guangzhou \
    --Placement '{"Zone":"ap-guangzhou-3"}' \
    --InstanceType $TYPE \
    --InstanceChargeType POSTPAID_BY_HOUR | jq '.Response.Price'
done
```

---

## 2. Cost Anomaly Detection

### 2.1 Anomaly Patterns

| Pattern | Detection | Threshold | Severity |
|---------|-----------|-----------|----------|
| **Spike** | Daily cost > baseline | > 200% baseline | HIGH |
| **Drop** | Daily cost < baseline | < 50% baseline | MEDIUM (service risk) |
| **Trend Shift** | Slope change | > 30% increase | WARNING |
| **Resource Outlier** | Single resource > total | > 30% total | MEDIUM |

### 2.2 Baseline Calculation

```python
import statistics

def calculate_cost_baseline(cost_history: List[Dict], days: int = 30) -> Dict:
    """Calculate cost baseline from history"""
    daily_costs = [c['total_cost'] for c in cost_history[-days:]]
    
    baseline = {
        'avg': statistics.mean(daily_costs),
        'std': statistics.stdev(daily_costs) if len(daily_costs) > 1 else 0,
        'min': min(daily_costs),
        'max': max(daily_costs),
        'threshold_spike': statistics.mean(daily_costs) * 2.0,  # 2x = spike
        'threshold_drop': statistics.mean(daily_costs) * 0.5,   # 0.5x = drop
    }
    
    return baseline
```

### 2.3 Anomaly Detection Script

```python
def detect_cost_anomaly(current_cost: Dict, baseline: Dict) -> Optional[CostAnomaly]:
    """Detect cost anomaly for single day"""
    
    ratio = current_cost['total_cost'] / baseline['avg']
    
    # Spike detection
    if ratio > 2.0:
        return CostAnomaly(
            type='spike',
            date=current_cost['date'],
            current=current_cost['total_cost'],
            baseline=baseline['avg'],
            ratio=ratio,
            severity='HIGH',
            recommendation="Check for unexpected deployments or resource usage surge"
        )
    
    # Drop detection
    if ratio < 0.5:
        return CostAnomaly(
            type='drop',
            date=current_cost['date'],
            current=current_cost['total_cost'],
            baseline=baseline['avg'],
            ratio=ratio,
            severity='MEDIUM',
            recommendation="Verify service availability - possible service disruption"
        )
    
    # Gradual trend shift
    if current_cost['trend_slope'] > baseline['avg_slope'] * 1.3:
        return CostAnomaly(
            type='trend_shift',
            date=current_cost['date'],
            current=current_cost['total_cost'],
            baseline=baseline['avg'],
            ratio=ratio,
            severity='WARNING',
            recommendation="Cost trend accelerating - review recent changes"
        )
    
    return None
```

---

## 3. Right-Sizing Analysis

### 3.1 Utilization Thresholds

| Metric | Avg Range | Recommendation | Action |
|--------|-----------|----------------|--------|
| CPUUsage | < 20% | **Downsize** | Reduce instance type |
| CPUUsage | 20-60% | **Optimal** | Maintain current |
| CPUUsage | > 70% | **Upsize** | Increase instance or scale out |
| MemUsage | < 30% | **Memory waste** | Reduce memory config |
| MemUsage | > 85% | **Memory pressure** | Increase memory |

### 3.2 Right-Sizing Recommendation Script

```python
def analyze_right_sizing(instance_metrics: Dict, instance_type: str) -> RightSizingRecommendation:
    """Analyze instance for right-sizing recommendation"""
    
    cpu_avg = instance_metrics['CPUUsage']['avg']
    cpu_max = instance_metrics['CPUUsage']['max']
    mem_avg = instance_metrics['MemUsage']['avg']
    
    recommendation = RightSizingRecommendation()
    recommendation.current_type = instance_type
    
    # Downsize candidate
    if cpu_avg < 20 and mem_avg < 30:
        recommendation.action = 'DOWNSIZE'
        recommendation.target_type = get_smaller_instance_type(instance_type)
        recommendation.reason = f"Very low utilization: CPU avg {cpu_avg}%"
        recommendation.savings_estimate = calculate_savings(instance_type, recommendation.target_type)
    
    # Upsize candidate
    elif cpu_avg > 70 or cpu_max > 90:
        recommendation.action = 'UPSIZE'
        recommendation.target_type = get_larger_instance_type(instance_type)
        recommendation.reason = f"High utilization: CPU avg {cpu_avg}%, max {cpu_max}%"
        recommendation.cost_increase = calculate_cost_increase(instance_type, recommendation.target_type)
    
    # Optimal
    else:
        recommendation.action = 'MAINTAIN'
        recommendation.reason = f"Optimal utilization: CPU avg {cpu_avg}%"
    
    return recommendation

def get_smaller_instance_type(current_type: str) -> str:
    """Get smaller instance type recommendation"""
    type_hierarchy = {
        'S5.4XLARGE32': 'S5.2XLARGE16',
        'S5.2XLARGE16': 'S5.LARGE8',
        'S5.LARGE8': 'S5.LARGE4',
        'S5.LARGE4': 'S5.MEDIUM4',
        'S5.MEDIUM4': 'S5.MEDIUM2',
        'S5.MEDIUM2': 'S5.SMALL2',
        'S5.SMALL2': 'S5.SMALL1',
    }
    return type_hierarchy.get(current_type, current_type)
```

### 3.3 Batch Right-Sizing Report

```markdown
# CVM Right-Sizing Analysis Report

**Generated**: 2026-05-21
**Region**: ap-guangzhou

## Downsizing Candidates (Cost Savings)

| Instance | Current Type | CPU Avg | Recommendation | Est. Savings |
|----------|--------------|---------|----------------|--------------|
| ins-xxx | S5.LARGE4 | 15% | S5.MEDIUM4 | ¥[monthly_savings] |
| ins-yyy | S5.LARGE8 | 18% | S5.LARGE4 | ¥[monthly_savings] |

**Total Potential Savings**: ¥[total]/month

## Upsizing Candidates (Performance)

| Instance | Current Type | CPU Avg | Recommendation | Est. Cost Increase |
|----------|--------------|---------|----------------|---------------------|
| ins-aaa | S5.MEDIUM4 | 85% | S5.LARGE4 | ¥[monthly_increase] |

## Optimal Instances

| Instance | Type | CPU Avg | Status |
|----------|------|---------|--------|
| ins-bbb | S5.LARGE4 | 45% | ✅ Optimal |

## Recommendations

1. **Immediate**: Upsize high-utilization instances to prevent performance issues
2. **Cost Savings**: Downsize low-utilization instances after validation
3. **Validation**: Test downsize candidates in staging before production
```

---

## 4. Reserved Instance Optimization

### 4.1 RI Eligibility Analysis

| Running Hours/Month | Recommendation | Expected Savings |
|---------------------|----------------|------------------|
| > 720h (steady 24x7) | 1-year RI | 30-40% |
| > 720h (critical) | 3-year RI | 50-60% |
| 200-500h | Consider Spot | Variable pricing |
| < 200h | Stay On-demand | No RI benefit |

### 4.2 RI Recommendation Script

```python
def analyze_ri_eligibility(instance_history: Dict) -> RIRecommendation:
    """Analyze instance for RI eligibility"""
    
    # Calculate running hours per month
    running_hours = calculate_running_hours(instance_history['status_timeline'])
    
    # Get on-demand and RI prices
    on_demand_hourly = instance_history['hourly_cost']
    ri_hourly = get_ri_price(instance_history['instance_type'], period=12)
    
    recommendation = RIRecommendation()
    recommendation.instance_id = instance_history['instance_id']
    recommendation.running_hours = running_hours
    
    if running_hours > 720:  # Steady running
        # Calculate savings
        on_demand_monthly = on_demand_hourly * running_hours
        ri_monthly = ri_hourly * 720 + on_demand_hourly * (running_hours - 720)
        savings_ratio = (on_demand_monthly - ri_monthly) / on_demand_monthly
        
        if savings_ratio > 0.3:
            recommendation.eligible = True
            recommendation.ri_type = '1-year' if savings_ratio < 0.5 else '3-year'
            recommendation.savings_ratio = savings_ratio
            recommendation.reason = f"Running {running_hours}h/month - {savings_ratio:.1%} savings"
        else:
            recommendation.eligible = False
            recommendation.reason = "Insufficient savings (< 30%)"
    
    else:
        recommendation.eligible = False
        recommendation.reason = f"Running only {running_hours}h/month - use on-demand"
    
    return recommendation
```

### 4.3 RI Recommendation Report

```markdown
# Reserved Instance Recommendation Report

**Region**: ap-guangzhou
**Generated**: 2026-05-21

## RI Candidates (> 30% savings)

| Instance | Type | Running Hours | RI Period | Savings |
|----------|------|---------------|-----------|---------|
| ins-xxx | S5.LARGE4 | 730h/month | 1-year | 35% |
| ins-yyy | S5.LARGE8 | 720h/month | 1-year | 32% |

**Total RI Commitment**: ¥[total] for [N] instances
**Total Monthly Savings**: ¥[savings]

## Not Eligible for RI

| Instance | Type | Running Hours | Reason |
|----------|------|---------------|--------|
| ins-aaa | S5.SMALL1 | 150h/month | Variable usage - stay on-demand |

## Recommendations

1. Purchase 1-year RI for steady production instances
2. Consider 3-year RI for core infrastructure (50% savings)
3. Use Spot instances for variable/batch workloads
```

---

## 5. Idle Resource Detection

### 5.1 Idle Resource Definition

| Resource Type | Idle Threshold | Cost Impact | Action |
|---------------|----------------|-------------|--------|
| CVM stopped | > 7 days | Full cost | Terminate or restart |
| CVM running, CPU < 5% | 7 days avg | Full cost | Downsize or terminate |
| CBS unattached | > 30 days | Disk cost | Delete if confirmed unused |
| CLB zero connections | > 24 hours | LB cost | Delete or check backend |

### 5.2 Idle Detection CLI

```bash
# Find stopped instances
tccli cvm DescribeInstances \
  --Region ap-guangzhou \
  --Filters '[{"Name":"instance-status","Values":["STOPPED"]}]' \
  | jq '.Response.InstanceSet[] | {InstanceId, InstanceName, CreatedTime}'

# Find unattached CBS disks
tccli cbs DescribeDisks \
  --Region ap-guangzhou \
  --Filters '[{"Name":"disk-state","Values":["UNATTACHED"]}]' \
  | jq '.Response.DiskSet[] | {DiskId, DiskName, DiskSize, CreatedTime}'
```

### 5.3 Idle Cost Calculation

```python
def calculate_idle_cost(idle_resources: List[Dict]) -> IdleCostReport:
    """Calculate cost of idle resources"""
    
    report = IdleCostReport()
    
    for resource in idle_resources:
        # Get resource pricing
        if resource['type'] == 'CVM':
            hourly_cost = get_instance_pricing(resource['instance_type'])
            idle_days = resource['idle_days']
            monthly_cost = hourly_cost * 24 * idle_days
            
            report.stopped_cvm.append({
                'instance_id': resource['resource_id'],
                'idle_days': idle_days,
                'hourly_cost': hourly_cost,
                'monthly_cost': monthly_cost,
                'action': 'Terminate' if idle_days > 30 else 'Review'
            })
        
        elif resource['type'] == 'CBS':
            disk_cost = get_disk_pricing(resource['disk_size'])
            idle_days = resource['idle_days']
            monthly_cost = disk_cost * idle_days
            
            report.unattached_disks.append({
                'disk_id': resource['resource_id'],
                'disk_size': resource['disk_size'],
                'idle_days': idle_days,
                'monthly_cost': monthly_cost,
                'action': 'Delete' if idle_days > 60 else 'Review'
            })
    
    # Total potential savings
    report.total_monthly_savings = sum(
        r['monthly_cost'] for r in report.stopped_cvm + report.unattached_disks
    )
    
    return report
```

---

## 6. Monthly Cost Report

### 6.1 Report Template

```markdown
# CVM Monthly Cost Report

**Report Period**: [Month]
**Region**: [Region]

## Cost Summary

| Category | Resources | Monthly Cost | % of Total |
|----------|-----------|--------------|------------|
| Running CVM | [N] | ¥[cost] | [%] |
| Stopped CVM | [N] | ¥[cost] | [%] |
| CBS Disks | [N] | ¥[cost] | [%] |
| Snapshots | [N] | ¥[cost] | [%] |
| **Total** | [N] | ¥[total] | 100% |

## Cost Breakdown by Environment

| Environment | Resources | Cost | % |
|-------------|-----------|------|---|
| Production | [N] | ¥[cost] | [%] |
| Staging | [N] | ¥[cost] | [%] |
| Development | [N] | ¥[cost] | [%] |
| Untagged | [N] | ¥[cost] | [%] ⚠️ |

## Anomalies Detected

| Date | Type | Cost | Baseline | Ratio | Severity |
|------|------|------|----------|-------|----------|
| [date] | Spike | ¥[cost] | ¥[baseline] | [ratio] | HIGH |

## Idle Resource Waste

| Resource | Type | Idle Days | Monthly Cost | Recommendation |
|----------|------|-----------|--------------|----------------|
| [ID] | CVM stopped | 30d | ¥[cost] | Terminate |

**Total Idle Cost**: ¥[total]/month

## Optimization Opportunities

| Type | Count | Potential Savings |
|------|-------|-------------------|
| Downsize candidates | [N] | ¥[savings]/month |
| RI eligible | [N] | ¥[savings]/month |
| Idle cleanup | [N] | ¥[savings]/month |
| **Total Potential** | | ¥[total]/month |

## Recommendations

1. **Immediate**: Terminate stopped instances > 30 days
2. **Short-term**: Purchase RI for steady production instances
3. **Cost Savings**: Downsize low-utilization instances
4. **Tagging**: Improve tagging coverage (currently [untagged%] untagged)
```

---

## 7. Budget Alert Rules

### 7.1 Budget Thresholds

```yaml
budget_alerts:
  thresholds:
    - name: monthly_budget_80
      condition: "projected_cost > budget * 0.8"
      severity: WARNING
      message: "Projected cost will reach 80% of monthly budget"
      
    - name: monthly_budget_100
      condition: "projected_cost > budget"
      severity: CRITICAL
      message: "Projected cost will exceed monthly budget"
      
    - name: daily_spike
      condition: "daily_cost > baseline_avg * 2.0"
      severity: WARNING
      message: "Daily cost spike detected - investigate"
```

### 7.2 Budget Check Script

```python
def check_budget_status(current_cost: float, budget: float, days_remaining: int) -> BudgetStatus:
    """Check budget status and project end-of-month"""
    
    # Calculate daily average
    days_elapsed = 30 - days_remaining
    daily_avg = current_cost / days_elapsed
    
    # Project end-of-month
    projected_total = current_cost + (daily_avg * days_remaining)
    
    status = BudgetStatus()
    status.current_cost = current_cost
    status.budget = budget
    status.days_remaining = days_remaining
    status.projected_total = projected_total
    status.budget_ratio = projected_total / budget
    
    if status.budget_ratio > 1.0:
        status.alert = 'CRITICAL'
        status.message = f"Projected ¥{projected_total} exceeds budget ¥{budget}"
    elif status.budget_ratio > 0.8:
        status.alert = 'WARNING'
        status.message = f"Projected ¥{projected_total} approaching budget"
    else:
        status.alert = 'OK'
        status.message = f"Projected ¥{projected_total} within budget"
    
    return status
```

---

## 8. Integration in CVM Skill

Add FinOps section to SKILL.md:

```markdown
## FinOps Cost Optimization

### Cost Query

```bash
# Price inquiry for instance creation
tccli cvm InquiryPriceRunInstances --InstanceType S5.LARGE4
```

### Right-Sizing Analysis

```bash
# Get CPU utilization for right-sizing analysis
tccli monitor GetMonitorData --Namespace QCE/CVM --MetricName CPUUsage \
  --Dimensions '[{"Name":"InstanceId","Value":"ins-xxx"}]' \
  --StartTime "$(date -d '-7 days' +'%Y-%m-%dT%H:%M:%S+08:00')" \
  --EndTime "$(date +'%Y-%m-%dT%H:%M:%S+08:00')"
```

### Idle Resource Detection

```bash
# Find stopped instances (idle > 7d)
tccli cvm DescribeInstances --Filters '[{"Name":"instance-status","Values":["STOPPED"]}]'
```

### References

- [FinOps Cost Optimization Module](../qcloud-skill-generator/references/finops-cost-optimization.md)
```

---

## References

- [Tencent Cloud Billing](https://cloud.tencent.com/document/product/555)
- [Reserved Instance Guide](https://cloud.tencent.com/document/product/213)
- [FinOps Cost Optimization Module](../qcloud-skill-generator/references/finops-cost-optimization.md)