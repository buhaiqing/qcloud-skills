# ML Anomaly Detection

> Passive diagnosis mode. Uses ML to detect metric anomalies without pre-defined thresholds. Complements `threshold_based` detectors for metrics without known baselines.

## Detector Interface

All detectors implement:

```python
class BaseDetector(ABC):
    name: str

    def fit(self, data: list[float]) -> "BaseDetector": ...
    def detect(self, point: float) -> dict[str, Any]: ...
    def detect_batch(self, points: list[float]) -> list[dict[str, Any]]: ...
```

Return shape:
```json
{
  "anomaly": true,
  "score": 0.87,
  "threshold": 0.72,
  "model": "IsolationForestDetector",
  "level": "critical"
}
```

## Available Detectors

### IsolationForestDetector

Unsupervised — trains on historical data, no labels needed.

```python
from ml.detectors import IsolationForestDetector

det = IsolationForestDetector(contamination=0.05, n_estimators=100)
det.fit(historical_cpu_values)
result = det.detect(current_cpu_value)
```

- **Graceful degradation**: if `sklearn` unavailable, falls back to z-score detector transparently
- **Best for**: metrics with seasonal patterns, multi-variate relationships
- **Limitations**: requires ≥50 historical points for stable results

### ThresholdDetector

Rule-based — no training required.

```python
from ml.detectors import ThresholdDetector

det = ThresholdDetector(
    warning_threshold=75.0,
    critical_threshold=90.0,
    direction="upper"   # high values = anomalous
)
result = det.detect(cpu_utilization)
```

- **Best for**: well-understood metrics (CPU > 90%, error rate > 1%)
- `level` field: `"critical" | "warning" | "normal"`

## Output Schema

```json
{
  "anomaly": true,
  "score": 0.87,
  "threshold": 0.72,
  "model": "IsolationForestDetector",
  "degraded": false,
  "level": "critical"
}
```

## Integration Points

### In `detect_anomalies` workflow step

```python
# After metric fetch
if detector.fit_ready:
    detector.fit(metric_history)
results = [detector.detect(p) for p in latest_values]
```

### In `AIOpsSummary` aggregation

```python
# Skip summarization if model="ThresholdDetector" and anomaly=false
# Always summarize if model="IsolationForestDetector" and anomaly=true
```

## FinOps Integration

CPU/memory anomaly scores feed into `capacity_forecaster`:

```python
from lib.capacity_forecaster import CapacityForecaster

fc = CapacityForecaster(resource_id=inst_id, metric="cpu_util")
fc.fit(ts_list, val_list)
alerts = fc.check_thresholds(fc.forecast(steps=7))
```

## Anti-Patterns

| Anti-Pattern | Correct |
|---|---|
| `detect_batch` on IsolationForest with < 50 points | Use `detect` sequentially |
| Mixing `upper` and `lower` direction in same detector | Create separate `ThresholdDetector` per direction |
| `contamination=0.5` (too aggressive) | Start with `0.01–0.05` |
