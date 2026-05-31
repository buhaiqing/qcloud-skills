# Alarm Handling — AIOps Alarm Storm Management

## Alarm Storm Patterns

| Pattern | Detection | Handling |
|---------|-----------|----------|
| Burst | > 50 alarms in 5 min from same source | Group by resource, deduplicate by metric |
| Cascade | Related services alarming simultaneously | Identify root service, suppress downstream |
| Flapping | Alarm fires/resolves repeatedly in short window | Add hysteresis: resolve only after N minutes stable |
| Noise | Low-priority alarms overwhelming operators | Auto-classify by severity, mute LOW during storms |

## Deduplication Algorithm

```python
def deduplicate_alarms(alarms: List[Dict]) -> List[Dict]:
    """Deduplicate alarms by resource + metric group"""
    groups = {}
    for alarm in alarms:
        key = (alarm['resource_id'], alarm['metric_name'])
        if key not in groups:
            groups[key] = []
        groups[key].append(alarm)

    result = []
    for key, group_alarms in groups.items():
        representative = max(group_alarms, key=lambda a: a['severity'])
        representative['count'] = len(group_alarms)
        result.append(representative)
    return result
```

## Alarm Priority Rules

| Priority | Criteria | Response Time |
|----------|----------|---------------|
| P0 (Critical) | Service down, data loss risk | < 5 min |
| P1 (High) | Performance degraded, SLI at risk | < 15 min |
| P2 (Medium) | Capacity warning, non-blocking | < 1 hour |
| P3 (Low) | Informational, trend alert | < 4 hours |

## Storm Response Checklist

1. Identify storm source (which resource/metric triggered most alarms)
2. Group alarms by resource, deduplicate by metric
3. Find root alarm (earliest timestamp in the group)
4. Apply diagnostic workflow from [diagnostic-workflows.md](diagnostic-workflows.md)
5. Mute non-critical alarms during active investigation
6. Document storm pattern for future automation
