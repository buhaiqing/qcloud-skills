# COS FinOps Cost Optimization Module

## 1. Cost Anomaly Detection

### Storage Cost Anomalies

| Anomaly Type | Detection Method | Threshold | Action |
|--------------|------------------|-----------|--------|
| Storage spike | Daily storage > 2x weekly avg | 200% | Check upload activity |
| Storage drop | Daily storage < 0.5x baseline | 50% | Verify no data loss |
| Class transition cost | Transition cost spike | 150% | Review lifecycle rules |

### Detection Implementation

```python
import statistics

def detect_cos_cost_anomaly(cost_history: list) -> list:
    anomalies = []
    
    daily_costs = [c['storage_cost'] + c['request_cost'] + c['bandwidth_cost'] for c in cost_history[-30:]]
    baseline_avg = statistics.mean(daily_costs)
    
    for day in cost_history[-7:]:
        ratio = (day['storage_cost'] + day['request_cost']) / baseline_avg
        
        if ratio > 2.0:
            anomalies.append({
                'type': 'spike',
                'date': day['date'],
                'recommendation': 'Check for unexpected uploads or lifecycle transitions'
            })
    
    return anomalies
```

## 2. Cost Trend Prediction

### Storage Growth Projection

```python
def project_cos_storage_cost(history: list, days_remaining: int) -> dict:
    storage_sizes = [h['storage_gb'] for h in history]
    growth_rate = (storage_sizes[-1] - storage_sizes[0]) / len(storage_sizes)
    
    projected_storage = storage_sizes[-1] + (growth_rate * days_remaining)
    
    standard_cost = projected_storage * 0.118
    archive_cost = projected_storage * 0.033
    
    return {
        'projected_storage_gb': projected_storage,
        'standard_monthly_cost': standard_cost,
        'archive_monthly_cost': archive_cost,
        'potential_savings': standard_cost - archive_cost
    }
```

## 3. Storage Class Optimization

### Optimal Class Selection

| Access Pattern | Recommended Class | Savings |
|----------------|-------------------|---------|
| Frequent (< 30 days) | STANDARD | — |
| Infrequent (30-180 days) | STANDARD_IA | 50% |
| Archive (> 180 days) | ARCHIVE | 90% |
| Long-term (> 1 year) | DEEP_ARCHIVE | 95% |

### Lifecycle Rule Recommendation

```yaml
lifecycle_optimization:
  rules:
    - prefix: logs/
      transition_days: 30
      target_class: STANDARD_IA
    
    - prefix: archive/
      transition_days: 90
      target_class: ARCHIVE
    
    - prefix: backup/
      expiration_days: 365
```

## 4. Idle Bucket Detection

### Idle Bucket Detection

```bash
# Find buckets with no recent access
coscmd list bucket-name -a

# Check last modified date
tccli cos GetBucket --Bucket bucket-name | jq '.Response.Contents[].LastModified'
```

### Idle Detection Patterns

| Pattern | Detection | Monthly Cost | Action |
|---------|-----------|--------------|--------|
| Empty bucket | ObjectCount == 0 | ¥0 | Delete unused bucket |
| No downloads 30 days | LastAccess > 30 days | Storage cost | Review need or archive |
| Large unused objects | Size > 1GB, no access | High storage | Archive or delete |

## 5. Tag-Based Cost Allocation

### Required COS Tags

| Tag Key | Purpose | Example |
|---------|---------|---------|
| `Environment` | Environment | prod/dev |
| `Project` | Project code | myapp |
| `CostCenter` | Department | ops-team |
| `DataClass` | Data classification | logs/backup/media |

## References

- [FinOps Cost Optimization](../qcloud-skill-generator/references/finops-cost-optimization.md)