# CLB FinOps Cost Optimization

## Overview

Cost optimization patterns specifically for CLB (Load Balancer) resources.

---

## 1. Billing Model Analysis

### CLB Instance Types

| Type | Pricing Model | Hourly Rate | Best For |
|------|----------------|-------------|----------|
| **公网共享型 (Shared)** | Postpaid + bandwidth | ¥0.02/hr | Low traffic, cost-sensitive |
| **公网独享型 (Dedicated)** | Postpaid + bandwidth | ¥0.8/hr | High traffic, guaranteed performance |
| **内网型 (Internal)** | Postpaid | ¥0.01/hr | Internal microservices |
| **Anycast** | Postpaid + cross-region | ¥1.2/hr | Global access, cross-region |

### Bandwidth Pricing

| Bandwidth Package | Pricing | Notes |
|-------------------|---------|-------|
| Postpaid bandwidth | ¥0.8/GB/day | Charged daily |
| Bandwidth package | ¥50/Mbps/month | Prepaid, cheaper for stable traffic |
| Shared bandwidth | Team-level billing | Share across multiple LBs |

### Monthly Cost Calculator

```python
def calculate_clb_monthly_cost(lb_type: str, bandwidth_mbps: int, hours: int = 720) -> float:
    """Calculate CLB monthly cost"""
    base_rates = {
        'shared': 0.02,
        'dedicated': 0.8,
        'internal': 0.01,
        'anycast': 1.2
    }
    
    hourly_cost = base_rates.get(lb_type, 0.02)
    base_cost = hourly_cost * hours
    
    # Add bandwidth if public LB
    if lb_type in ['shared', 'dedicated', 'anycast']:
        bandwidth_cost = bandwidth_mbps * 50  # ¥50/Mbps/month
        total_cost = base_cost + bandwidth_cost
    else:
        total_cost = base_cost
    
    return total_cost
```

---

## 2. Cost Anomaly Detection

### CLB Cost Anomalies

| Anomaly | Detection Method | Threshold |
|---------|------------------|-----------|
| Bandwidth spike | Daily traffic > 2x weekly avg | 200% |
| Connection surge | ClientConnum spike > 3x | 300% |
| Idle CLB | Zero traffic for 24h | 0 connections |
| Unused listener | Listener with no traffic | 0 TrafficIn/Out |

### Detection Script

```bash
# Find idle load balancers
tccli clb DescribeIdleLoadBalancers --Region ap-guangzhou

# Check traffic patterns
tccli clb DescribeLoadBalancers --LoadBalancerIds "[\"lb-xxx\"]" | jq '.Response.LoadBalancerSet[0]'
```

---

## 3. Idle Resource Detection

### Idle CLB Patterns

| Pattern | Detection | Threshold | Monthly Waste |
|---------|-----------|-----------|---------------|
| **No listeners** | DescribeListeners returns empty | Empty | ¥14.4 (shared) |
| **No backends** | DescribeTargets returns empty | Empty | ¥14.4 (shared) |
| **Zero traffic** | ClientConnum = 0 for 24h | 0 | ¥14.4 + bandwidth |
| **Stopped backends** | All targets unhealthy for 7d | All unhealthy | Full LB cost |

### Idle Detection Query

```bash
# List CLBs with no listeners
for lb in $(tccli clb DescribeLoadBalancers | jq -r '.Response.LoadBalancerSet[].LoadBalancerId'); do
  listeners=$(tccli clb DescribeListeners --LoadBalancerId "$lb" | jq '.Response.ListenerSet | length')
  if [ "$listeners" = "0" ]; then
    echo "Idle CLB (no listeners): $lb"
  fi
done
```

---

## 4. Right-Sizing Recommendations

### CLB Type Optimization

| Current State | Recommendation | Savings |
|---------------|----------------|---------|
| Shared LB with > 5000 connections | Upgrade to Dedicated | Better performance |
| Dedicated LB with < 100 connections | Downgrade to Shared | ~¥560/month |
| Multiple Shared LBs | Consolidate to 1 Dedicated | Hardware + bandwidth |
| Internal LB in public subnet | Review VPC config | Possible VPC cost |

### Bandwidth Optimization

| Current Bandwidth | Utilization | Recommendation |
|-------------------|-------------|----------------|
| 100 Mbps | Avg 20 Mbps | Reduce to 50 Mbps |
| 50 Mbps | Peak 45 Mbps | Keep or increase |
| Shared bandwidth | Single LB | Consider dedicated bandwidth |

---

## 5. Reserved Capacity (Prepaid)

### CLB Prepaid Options

| Option | Commitment | Discount | Best For |
|--------|------------|----------|----------|
| Monthly package | 1 month | 10% off | Stable workload |
| Quarterly package | 3 months | 15% off | Production stable |
| Annual package | 12 months | 25% off | Long-term production |

### RI Analysis

```python
def should_use_prepaid_clb(avg_daily_connections: int, stability_months: int) -> bool:
    """Determine if prepaid CLB makes sense"""
    # Prepaid recommended for:
    # 1. Stable workload (> 720h/month usage)
    # 2. Production environment
    # 3. Commitment >= 3 months
    
    if stability_months >= 3 and avg_daily_connections > 1000:
        return True
    return False
```

---

## 6. Tag-Based Cost Allocation

### Recommended Tags

| Tag Key | Purpose | Example |
|---------|---------|---------|
| `Environment` | Cost allocation | production / staging / dev |
| `Project` | Project billing | web-app / api-service |
| `CostCenter` | Department billing | engineering / marketing |
| `Owner` | Resource owner | team-backend |

### Cost Query by Tag

```bash
# Query CLBs by project tag
tccli clb DescribeLoadBalancers --Filters "[{\"Name\":\"tag:Project\",\"Values\":[\"web-app\"]}]"
```

---

## 7. Cost Optimization Checklist

| Check | Action | Savings |
|-------|--------|---------|
| ✓ Delete idle CLBs | Monthly review | ¥14-576/LB |
| ✓ Consolidate LBs | Merge low-traffic LBs | Hardware cost |
| ✓ Right-size bandwidth | Match actual usage | Bandwidth cost |
| ✓ Use prepaid for stable | Commit > 3 months | 10-25% |
| ✓ Tag all CLBs | Enable cost tracking | Better visibility |

---

## Monthly CLB Cost Report Template

```markdown
# CLB Monthly Cost Report

## Summary

| Category | Count | Monthly Cost |
|----------|-------|--------------|
| Shared LBs | [count] | ¥[cost] |
| Dedicated LBs | [count] | ¥[cost] |
| Internal LBs | [count] | ¥[cost] |
| Bandwidth | [Mbps] | ¥[cost] |

## Idle Resources

| LB ID | Type | Idle Days | Wasted Cost |
|-------|------|-----------|-------------|
| [lb-id] | [type] | [days] | ¥[cost] |

## Recommendations

1. **Immediate**: Delete [count] idle CLBs → Save ¥[savings]/month
2. **Short-term**: Right-size bandwidth for [lb-ids] → Save ¥[savings]/month
3. **Long-term**: Prepaid for [stable-lbs] → Save [discount]%

**Total Potential Savings**: ¥[total]/month
```