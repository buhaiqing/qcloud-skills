# VPC FinOps Cost Optimization Module

## 1. Cost Anomaly Detection

### Anomaly Patterns for VPC

| Anomaly Type | Detection Method | Threshold | Action |
|--------------|------------------|-----------|--------|
| NAT Gateway cost spike | Daily NAT cost > 2x weekly avg | 200% | Check outbound traffic surge |
| VPN Gateway cost drop | Daily VPN cost < 0.5x baseline | 50% | Verify VPN connectivity |
| Bandwidth trend shift | Weekly bandwidth slope change | 30% | Review traffic patterns |

### Detection Implementation

```python
import statistics

def detect_vpc_cost_anomaly(cost_history: list) -> list:
    anomalies = []
    
    daily_costs = [c['nat_gateway_cost'] + c['vpn_gateway_cost'] + c['bandwidth_cost'] for c in cost_history[-30:]]
    baseline_avg = statistics.mean(daily_costs)
    
    for day_cost in cost_history[-7:]:
        total = day_cost['nat_gateway_cost'] + day_cost['vpn_gateway_cost'] + day_cost['bandwidth_cost']
        ratio = total / baseline_avg
        
        if ratio > 2.0:
            anomalies.append({
                'type': 'spike',
                'date': day_cost['date'],
                'value': total,
                'ratio': ratio,
                'recommendation': 'Check NAT gateway traffic logs for unexpected outbound surge'
            })
        
        if ratio < 0.5:
            anomalies.append({
                'type': 'drop',
                'date': day_cost['date'],
                'value': total,
                'ratio': ratio,
                'recommendation': 'Verify VPN/NAT gateway connectivity - possible disruption'
            })
    
    return anomalies
```

## 2. Cost Trend Prediction

### Monthly Cost Projection

```python
def project_vpc_monthly_cost(cost_history: list, days_remaining: int) -> dict:
    x = list(range(len(cost_history)))
    y = [c['total_cost'] for c in cost_history]
    
    n = len(x)
    slope = (n * sum(x[i] * y[i] for i in range(n)) - sum(x) * sum(y)) / (n * sum(x[i]**2 for i in range(n)) - sum(x)**2)
    intercept = (sum(y) - slope * sum(x)) / n
    
    projected_daily = slope * (len(cost_history) + days_remaining) + intercept
    current_total = sum(y)
    projected_total = current_total + (projected_daily * days_remaining)
    
    return {
        'current_total': current_total,
        'projected_daily': projected_daily,
        'projected_total': projected_total,
        'budget_alert': projected_total > 1000
    }
```

## 3. Tag-Based Cost Allocation

### Required VPC Tags

| Tag Key | Purpose | Example |
|---------|---------|---------|
| `Environment` | Environment type | prod/dev/staging |
| `Project` | Project code | myapp |
| `CostCenter` | Department | ops-team |
| `Owner` | Resource owner | zhangsan |

### Tag Cost Query

```bash
tccli vpc DescribeVpcs | jq '.Response.VpcSet[] | {VpcId, VpcName, TagSet}'
```

### Tag Enforcement

```yaml
tagging_policy:
  mandatory_tags:
    - Environment
    - Project
    - CostCenter
  
  enforcement:
    create_require_tags: true
```

## 4. Reserved Instance Optimization

**Note:** VPC itself is free. Only NAT Gateway and VPN Gateway have costs.

| Gateway Type | Cost Model | Optimization |
|--------------|------------|--------------|
| NAT Gateway | Hourly + bandwidth | Disable at night for low-traffic |
| VPN Gateway | Hourly (¥80/hr) | Delete unused, use Direct Connect for steady traffic |

## 5. Idle Resource Cost Analysis

### VPC Idle Detection

```bash
# Find empty VPCs (cost: 0)
EMPTY_VPCS=$(tccli vpc DescribeVpcs | jq '.Response.VpcSet[] | select(.SubnetSet | length == 0) | .VpcId')

# Find unused NAT gateways
UNUSED_NATS=$(tccli vpc DescribeNatGateways | jq '.Response.NatGatewaySet[] | select(.State != "AVAILABLE") | .NatGatewayId')

# Calculate potential savings
# NAT Gateway: ¥0.50/hr * 24 * 30 = ¥360/month per unused NAT
```

### Monthly Idle Cost Report

| Category | Detection | Monthly Cost | Action |
|----------|-----------|--------------|--------|
| Empty VPC | SubnetSet empty | ¥0 (free) | Delete unused |
| Stopped NAT | State != AVAILABLE | ¥360/month | Delete if not needed |
| Idle VPN | No active connections | ¥2400/month | Delete or disable |

## References

- [FinOps Cost Optimization](../qcloud-skill-generator/references/finops-cost-optimization.md)