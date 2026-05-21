# FinOps Cost Optimization Module

Cost optimization patterns for Tencent Cloud skills.

---

## Overview

Every generated skill SHOULD consider FinOps patterns:
- Cost anomaly detection
- Cost trend prediction
- Tag-based cost allocation
- Reserved Instance optimization
- Idle resource cost analysis

---

## 1. Cost Anomaly Detection

### 1.1 Anomaly Detection Patterns

| Anomaly Type | Detection Method | Threshold | Action |
|--------------|------------------|-----------|--------|
| Spike | Daily cost > 2x weekly average | 200% | Alert + investigate |
| Drop | Daily cost < 0.5x weekly average | 50% | Check for service disruption |
| Trend shift | Weekly trend slope change | 30% | Review recent changes |
| Resource outlier | Single resource > 30% of total | 30% | Review resource sizing |

### 1.2 Detection Implementation

```python
def detect_cost_anomaly(cost_history: List[Dict]) -> List[CostAnomaly]:
    """Detect cost anomalies from billing history"""
    anomalies = []
    
    # Calculate baseline
    daily_costs = [c['total_cost'] for c in cost_history[-30:]]
    baseline_avg = statistics.mean(daily_costs)
    baseline_std = statistics.stdev(daily_costs)
    
    # Check recent days
    for day_cost in cost_history[-7:]:
        ratio = day_cost['total_cost'] / baseline_avg
        
        # Spike detection
        if ratio > 2.0:
            anomalies.append(CostAnomaly(
                type='spike',
                date=day_cost['date'],
                value=day_cost['total_cost'],
                baseline=baseline_avg,
                ratio=ratio,
                severity='HIGH',
                recommendation='Check for unexpected resource usage or new deployments'
            ))
        
        # Drop detection
        if ratio < 0.5:
            anomalies.append(CostAnomaly(
                type='drop',
                date=day_cost['date'],
                value=day_cost['total_cost'],
                baseline=baseline_avg,
                ratio=ratio,
                severity='MEDIUM',
                recommendation='Verify service availability - possible disruption'
            ))
    
    return anomalies
```

---

## 2. Cost Trend Prediction

### 2.1 Prediction Methods

| Method | Use Case | Accuracy | Implementation |
|--------|----------|----------|----------------|
| Linear regression | Stable workload | High for 1-2 weeks | Simple slope calculation |
| Moving average | Variable workload | Medium | 7/30 day average |
| Tencent Cloud Forecast | Built-in | High | Monitor API forecast |

### 2.2 Cost Projection

```python
def project_monthly_cost(cost_history: List[Dict], days_remaining: int) -> Dict:
    """Project end-of-month cost"""
    # Linear regression on daily costs
    x = list(range(len(cost_history)))
    y = [c['total_cost'] for c in cost_history]
    
    slope, intercept = calculate_linear_regression(x, y)
    
    # Project remaining days
    projected_daily = slope * (len(cost_history) + days_remaining) + intercept
    
    # Current month total
    current_total = sum(y)
    
    # Projected total
    projected_total = current_total + (projected_daily * days_remaining)
    
    return {
        'current_total': current_total,
        'projected_daily': projected_daily,
        'projected_total': projected_total,
        'budget_alert': projected_total > budget_threshold
    }
```

### 2.3 Budget Alert Rules

```yaml
budget_alerts:
  - name: monthly_budget_threshold
    condition: "projected_total > budget * 0.8"
    severity: warning
    message: "Projected cost will reach 80% of monthly budget"
    
  - name: budget_exceeded_projected
    condition: "projected_total > budget"
    severity: critical
    message: "Projected cost will exceed monthly budget"
    
  - name: trend_acceleration
    condition: "slope > previous_slope * 1.5"
    severity: warning
    message: "Cost trend accelerating - review recent changes"
```

---

## 3. Tag-Based Cost Allocation

### 3.1 Required Tags for Cost Tracking

| Tag Key | Purpose | Required |
|---------|---------|----------|
| `Environment` | Environment type (prod/dev/staging) | ✓ |
| `Project` | Project code | ✓ |
| `CostCenter` | Department/team | ✓ |
| `Owner` | Resource owner | Recommended |
| `Application` | Application name | Recommended |

### 3.2 Cost Allocation Query

```python
def calculate_cost_by_tag(billing_data: List[Dict], tag_key: str) -> Dict:
    """Calculate cost breakdown by tag"""
    cost_by_tag = {}
    
    for item in billing_data:
        tags = item.get('Tags', {})
        tag_value = tags.get(tag_key, 'untagged')
        
        cost_by_tag[tag_value] = cost_by_tag.get(tag_value, 0) + item['Cost']
    
    return {
        'tag_key': tag_key,
        'breakdown': cost_by_tag,
        'untagged_ratio': cost_by_tag.get('untagged', 0) / sum(cost_by_tag.values()),
        'recommendation': generate_tag_recommendation(cost_by_tag)
    }

def generate_tag_recommendation(cost_breakdown: Dict) -> str:
    """Generate tagging improvement recommendation"""
    untagged_ratio = cost_breakdown.get('untagged', 0) / sum(cost_breakdown.values())
    
    if untagged_ratio > 0.3:
        return f"⚠️ {untagged_ratio:.1%} of costs are untagged. Improve tagging coverage."
    elif untagged_ratio > 0.1:
        return f"📝 {untagged_ratio:.1%} untagged. Consider mandatory tagging policy."
    else:
        return "✅ Good tagging coverage."
```

### 3.3 Tagging Enforcement

```yaml
tagging_policy:
  mandatory_tags:
    - Environment
    - Project
    - CostCenter
    
  enforcement:
    # Block creation if tags missing
    create_require_tags: true
    
    # Auto-tag rules
    auto_tagging:
      - condition: "instance_type contains 'prod'"
        tag: {Environment: production}
        
      - condition: "vpc contains 'dev'"
        tag: {Environment: development}
```

---

## 4. Reserved Instance Optimization

### 4.1 RI Analysis Logic

```python
def analyze_ri_eligibility(instance_history: List[Dict]) -> List[RIRecommendation]:
    """Analyze which instances should use Reserved Instance"""
    recommendations = []
    
    for instance in instance_history:
        # Calculate running hours per month
        running_hours = calculate_running_hours(instance)
        
        # RI eligibility threshold: > 720h/month (running > 30 days * 24h)
        if running_hours > 720:
            # Calculate potential savings
            on_demand_cost = instance['hourly_cost'] * running_hours
            ri_cost = instance['ri_hourly_cost'] * 720 + \
                      instance['hourly_cost'] * (running_hours - 720)
            
            savings_ratio = (on_demand_cost - ri_cost) / on_demand_cost
            
            if savings_ratio > 0.3:  # > 30% savings
                recommendations.append(RIRecommendation(
                    instance_id=instance['InstanceId'],
                    instance_type=instance['InstanceType'],
                    running_hours=running_hours,
                    savings_ratio=savings_ratio,
                    recommendation=f"Consider {instance['InstanceType']} Reserved Instance - {savings_ratio:.1%} savings"
                ))
    
    return recommendations
```

### 4.2 RI Recommendation Table

| Instance Running Hours | RI Recommendation | Expected Savings |
|------------------------|-------------------|------------------|
| > 720h/month (steady) | 1-year RI | ~30-40% |
| > 720h/month (critical) | 3-year RI | ~50-60% |
| 200-500h/month | Consider Spot | Spot pricing variable |
| < 200h/month | Stay On-demand | No RI benefit |

---

## 5. Idle Resource Cost Analysis

### 5.1 Idle Resource Detection

```yaml
idle_detection:
  # CVM instances
  cvm:
    stopped_days_threshold: 7
    cpu_utilization_threshold: 5   # < 5% over 7 days
    action: "Recommend terminate or restart with purpose"
    
  # CBS disks
  cbs:
    unattached_days_threshold: 30
    action: "Recommend delete if confirmed unused"
    
  # Load Balancers
  clb:
    zero_connections_threshold: 24  # hours
    action: "Recommend delete or check configuration"
    
  # MySQL instances
  mysql:
    stopped_threshold: 7
    low_qps_threshold: 10  # queries/sec over 7 days
    action: "Recommend scale down or terminate"
```

### 5.2 Monthly Idle Cost Report

```markdown
# Monthly Idle Resource Cost Report

**Report Period**: [Month]

## Summary

| Category | Count | Monthly Cost | Potential Savings |
|----------|-------|--------------|-------------------|
| Stopped CVM | [count] | ¥[cost] | ¥[savings] |
| Unattached CBS | [count] | ¥[cost] | ¥[savings] |
| Idle CLB | [count] | ¥[cost] | ¥[savings] |
| Low-util MySQL | [count] | ¥[cost] | ¥[savings] |

## Recommendations

1. **Immediate Action**: Terminate stopped instances > 30 days
2. **Short-term**: Delete unattached disks > 60 days
3. **Review**: Low utilization resources - scale down or repurpose

**Total Potential Monthly Savings**: ¥[total]
```

---

## Integration in Generated Skills

```markdown
## FinOps Cost Optimization

### Cost Anomaly Detection

When monitoring costs, check for anomalies:
- Daily cost spike > 2x baseline
- Cost trend acceleration > 30%

### Idle Resource Detection

| Resource Type | Idle Threshold | Action |
|---------------|----------------|--------|
| CVM stopped | > 7 days | Review purpose |
| CBS unattached | > 30 days | Delete if unused |

### RI Recommendations

Consider Reserved Instance for:
- Instances running > 720h/month
- Steady-state production workloads
- Expected savings > 30%
```

---

## References

- [Tencent Cloud Cost Management](https://cloud.tencent.com/document/product/555)
- [Reserved Instance Guide](https://cloud.tencent.com/document/product/xxx)