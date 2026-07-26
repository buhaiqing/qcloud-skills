# Finding Filters

> Suppress known-known and informational findings to reduce noise in cruise reports.

## Filter Rule Schema

```python
FindingFilter(
    name="my_rule",
    field="resource_id",      # which finding field to match
    op="regex",               # equals | contains | regex | severity_above
    value="^cmpt-test-",     # pattern
    action="suppress",        # suppress (drop) or flag (annotate)
)
```

## Fields Available for Matching

| Field | Type | Example |
|-------|------|---------|
| `resource_id` | string | `ins-123456` |
| `metric` | string | `cpu_util` |
| `severity` | string | `warning`, `critical`, `info` |
| `model` | string | `IsolationForestDetector` |
| `anomaly` | bool | `true` |
| `direction` | string | `upper`, `lower` |

## Pre-Built Filter Sets

### FinOps Cost Filter

```python
from lib.finding_filters import finops_cost_filter

fs = finops_cost_filter()
kept, suppressed = fs.apply(findings)
```

Rules:
- `severity < warning` → `suppress` (drops info-level findings)
- `resource_id` matches `^cmpt-test-` → `flag` (annotates test resources)

### Reliability Filter

```python
from lib.finding_filters import reliability_filter

fs = reliability_filter()
kept, suppressed = fs.apply(findings)
```

Rules:
- `resource_id` matches `(?i)(ha|standby|backup)-` → `flag` (annotates HA candidates)

## Custom Filter Set

```python
from lib.finding_filters import FindingFilterSet, FindingFilter

fs = FindingFilterSet(name="my_filter")

fs.add_rule(
    name="suppress_billing_noise",
    field="metric",
    op="equals",
    value="estimated_charge",
    action="suppress",
)

fs.add_rule(
    name="flag_anomalies_in_critical_sg",
    field="resource_id",
    op="regex",
    value="^sg-critical-",
    action="flag",
)

kept, suppressed = fs.apply(findings)
stats = fs.suppression_stats()  # {"total_suppressed": 7}
```

## Output with Annotations

```python
annotated = fs.apply_and_annotate(findings)
# Finding with _suppressed_by or _flagged_by keys added
```

```json
{
  "resource_id": "ins-123456",
  "metric": "cpu_util",
  "anomaly": true,
  "_suppressed_by": ["suppress_informational_billing"],
  "_flagged_by": ["flag_ha_candidates"]
}
```

## Anti-Patterns

| Anti-Pattern | Correct |
|---|---|
| `action="suppress"` on `severity_above=warning` | Suppress only info-level; critical findings must surface |
| No filter → cruise report floods with 500+ findings | Start with `finops_cost_filter()` then add custom rules |
| Overly broad regex (`".*"`) | Be specific; use `equals` for exact match |
