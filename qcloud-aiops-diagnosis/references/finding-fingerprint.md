# Finding Fingerprint

> Stable hash signature for cross-cruise deduplication. Two findings with identical fingerprints are the same root cause.

## Fingerprint Key Format

```
metric|resource_id|direction|window_minutes|agg_fn
```

Example: `cpu_util|ins-123456|upper|60|avg`

## Python API

```python
from lib.finding_fingerprint import FindingFingerprint, FingerprintRegistry

fp = FindingFingerprint(
    metric="cpu_util",
    resource_id="ins-123456",
    direction="upper",
    window_minutes=60,
    agg_fn="avg",
)
print(fp.key)    # stable primary key for grouping
print(fp.hash)   # short hex for compact representation
```

## Registry (Deduplication)

```python
from lib.finding_fingerprint import FindingFingerprint, FingerprintRegistry

reg = FingerprintRegistry()
is_new = reg.register(fp, summary="CPU > 90% for 60 min", severity="critical")
# is_new = True → first time seen
# is_new = False → duplicate, count incremented
```

## Merge (Multi-Cruise)

```python
reg_a.merge(reg_b)  # combine two cruise runs
```

## Export

```json
{
  "cpu_util|ins-123456|upper|60|avg": {
    "fp": {
      "metric": "cpu_util",
      "resource_id": "ins-123456",
      "direction": "upper",
      "window_minutes": 60,
      "agg_fn": "avg",
      "key": "cpu_util|ins-123456|upper|60|avg",
      "hash": "a3f5c2..."
    },
    "summary": "CPU > 90% for 60 min",
    "severity": "critical",
    "count": 3
  }
}
```

## Usage in Cruise Diff

When comparing two cruise runs, the fingerprint registry enables:
- **Same finding across runs**: fingerprint matches → increment `count`
- **New finding**: fingerprint not seen before → add to `unique_findings`
- **Resolved finding**: fingerprint in run A but not in run B → marked `resolved`
