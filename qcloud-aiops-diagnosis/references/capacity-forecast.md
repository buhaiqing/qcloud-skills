# Capacity Forecast

> Proactive FinOps capability. Forecasts capacity trends and alerts before thresholds are breached.

## High-Level Interface

```python
from lib.capacity_forecaster import CapacityForecaster

fc = CapacityForecaster(
    resource_id="ins-123",
    metric="cpu_util",
    period_seconds=86400,  # daily
)
fc.fit(timestamps, values)           # historical data
forecast = fc.forecast(steps=7)       # 7-day forecast
alerts = fc.check_thresholds(forecast)  # FinOps threshold checks
```

## Predictors

| Predictor | sklearn/xgboost required | Best for |
|-----------|------------------------|----------|
| `LinearTrendPredictor` | No | Trend extrapolation, < 30 days history |
| `XGBoostCapacityPredictor` | Yes (graceful fallback) | Seasonal data, complex patterns |

### LinearTrendPredictor

Pure Python OLS — no dependencies.

```python
from ml.predictors import LinearTrendPredictor

pred = LinearTrendPredictor(period_seconds=86400)
pred.fit(timestamps, values)
result = pred.predict_interval(steps=7, confidence=0.95)
# result["predictions"] = [val, ...]
# result["lower"]        = [val, ...]
# result["upper"]        = [val, ...]
```

### XGBoostCapacityPredictor

Feature-engineered XGBoost with cyclical time encoding + lags.

```python
from ml.predictors import XGBoostCapacityPredictor

pred = XGBoostCapacityPredictor(horizon_steps=24, period_seconds=3600, n_lags=3)
pred.fit(timestamps, values)
result = pred.predict(steps=24)
# result["degraded"] = True  # if xgboost unavailable, fell back to LinearTrendPredictor
```

Features: `sin/cos(hour)`, `sin/cos(day-of-week)`, trend index, N lag values.

## Default FinOps Thresholds

| Metric | Warning | Critical |
|--------|---------|---------|
| `cpu_util` | 75% | 90% |
| `mem_util` | 80% | 95% |
| `disk_util` | 85% | 95% |
| `cpu_allocated` | 80% | 95% |
| `mem_allocated` | 85% | 98% |

Override per resource:
```python
fc = CapacityForecaster(..., thresholds={"warning": 60.0, "critical": 80.0})
```

## Alert Output Schema

```json
{
  "resource_id": "ins-123",
  "metric": "cpu_util",
  "threshold": 90.0,
  "forecast_value": 93.4,
  "horizon_steps": 3,
  "severity": "critical"
}
```

## Output Schema (Forecast)

```json
{
  "predictions": [val, ...],
  "model": "XGBoostCapacityPredictor",
  "horizon": 7,
  "resource_id": "ins-123",
  "metric": "cpu_util",
  "lower": [val, ...],
  "upper": [val, ...],
  "confidence": 0.95,
  "degraded": false
}
```
