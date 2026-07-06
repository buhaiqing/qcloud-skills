# CLB FinOps Cost Optimization

## Overview

Cost optimization patterns specifically for CLB (Load Balancer) resources.

---

## 1. Billing Model Analysis

### CLB Instance Types

| Type | Pricing Model | Best For |
|------|----------------|----------|
| **公网共享型 (Shared)** | Postpaid + bandwidth | Low traffic, cost-sensitive |
| **公网独享型 (Dedicated)** | Postpaid + bandwidth | High traffic, guaranteed performance |
| **内网型 (Internal)** | Postpaid | Internal microservices |
| **Anycast** | Postpaid + cross-region | Global access, cross-region |

> Hourly rates vary by region and are subject to change. Check current pricing via `https://buy.cloud.tencent.com/price/clb` or query billing APIs.

### Bandwidth Pricing

| Bandwidth Package | Notes |
|-------------------|-------|
| Postpaid bandwidth | Charged daily |
| Bandwidth package | Prepaid, cheaper for stable traffic |
| Shared bandwidth | Team-level billing share across multiple LBs |

> Check current bandwidth pricing at `https://buy.cloud.tencent.com/price/clb`.

### Monthly Cost Calculator

```python
def calculate_clb_monthly_cost(lb_type: str, bandwidth_mbps: int, hours: int = 720) -> float:
    # Calculate CLB monthly cost
    # <!-- Use API for latest: tccli billing DescribeProductPrice --ProductType=clb --Bandwidth=<Mbps> --...] -->
    base_rates = {
        # <!-- Use API: tccli billing DescribeProductPrice --ProductType=clb --InstanceType=shared -->
        'shared': 0.02,       # $/hr — verify via DescribeProductPrice
        # <!-- Use API: tccli billing DescribeProductPrice --ProductType=clb --InstanceType=dedicated -->
        'dedicated': 0.8,     # $/hr — verify via DescribeProductPrice
        # <!-- Use API: tccli billing DescribeProductPrice --ProductType=clb --InstanceType=internal -->
        'internal': 0.01,     # $/hr — verify via DescribeProductPrice
        # <!-- Use API: tccli billing DescribeProductPrice --ProductType=clb --InstanceType=anycast -->
        'anycast': 1.2       # $/hr — verify via DescribeProductPrice
    }

    hourly_cost = base_rates.get(lb_type, 0.02)
    base_cost = hourly_cost * hours

    # Add bandwidth if public LB
    if lb_type in ['shared', 'dedicated', 'anycast']:
        # <!-- Use API: tccli billing DescribeBandwidthPrice --BandwidthType=PostpaidByHour --TrafficPerMegabytes=... -->
        bandwidth_cost = bandwidth_mbps * 50  # ¥50/Mbps/month — verify via DescribeBandwidthPrice
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

| Pattern | Detection | Threshold |
|---------|-----------|-----------|
| **No listeners** | DescribeListeners returns empty | Empty |
| **No backends** | DescribeTargets returns empty | Empty |
| **Zero traffic** | ClientConnum = 0 for 24h | 0 |
| **Stopped backends** | All targets unhealthy for 7d | All unhealthy |

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

| Current State | Recommendation |
|---------------|----------------|
| Shared LB with > 5000 connections | Upgrade to Dedicated |
| Dedicated LB with < 100 connections | Downgrade to Shared |
| Multiple Shared LBs | Consolidate to 1 Dedicated |
| Internal LB in public subnet | Review VPC config |

### Bandwidth Optimization

| Current Bandwidth | Utilization | Recommendation |
|-------------------|-------------|----------------|
| 100 Mbps | Avg 20 Mbps | Reduce to 50 Mbps |
| 50 Mbps | Peak 45 Mbps | Keep or increase |
| Shared bandwidth | Single LB | Consider dedicated bandwidth |

---

## 5. Reserved Capacity (Prepaid)

### CLB Prepaid Options

| Option | Commitment | Best For |
|--------|------------|----------|
| Monthly package | 1 month | Stable workload |
| Quarterly package | 3 months | Production stable |
| Annual package | 12 months | Long-term production |

> Discount rates vary. Check current prepaid pricing at `https://buy.cloud.tencent.com/price/clb`.

### RI Analysis

```python
def should_use_prepaid_clb(avg_daily_connections: int, stability_months: int) -> bool:
    # Determine if prepaid CLB makes sense
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