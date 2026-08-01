"""Capacity forecaster — wraps ML predictor with threshold-based FinOps rules.

Provides a high-level interface:
    fc = CapacityForecaster(resource_id="ins-123", metric="cpu_util")
    fc.fit(historical_timestamps, historical_values)
    forecast = fc.forecast(steps=7)          # 7-period forecast
    alerts  = fc.check_thresholds(forecast)  # FinOps threshold checks
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Try to use the ML predictor, fall back to pure-python linear trend.
# Catch all exceptions — a syntax error or missing transitive dep in ml.predictors
# should not propagate; LinearTrendPredictor is always available.
try:
    from ml.predictors import XGBoostCapacityPredictor
    _Predictor = XGBoostCapacityPredictor
except Exception as _exc:  # noqa: BLE001  # intentional fallback, see comment above
    import sys
    print(f"[capacity_forecaster] XGBoost unavailable ({_exc}), using LinearTrendPredictor", file=sys.stderr)
    from ml.predictors import LinearTrendPredictor
    _Predictor = LinearTrendPredictor  # type: ignore


# FinOps capacity thresholds (can be overridden per resource via config)
DEFAULT_THRESHOLDS: dict[str, dict[str, float]] = {
    "cpu_util":      {"warning": 75.0, "critical": 90.0},
    "mem_util":      {"warning": 80.0, "critical": 95.0},
    "disk_util":     {"warning": 85.0, "critical": 95.0},
    "cpu_allocated": {"warning": 80.0, "critical": 95.0},
    "mem_allocated": {"warning": 85.0, "critical": 98.0},
}


@dataclass
class CapacityAlert:
    resource_id: str
    metric: str
    threshold: float
    forecast_value: float
    horizon: int
    severity: str  # "warning" | "critical"

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "metric": self.metric,
            "threshold": self.threshold,
            "forecast_value": self.forecast_value,
            "horizon_steps": self.horizon,
            "severity": self.severity,
        }


class CapacityForecaster:
    """High-level capacity forecasting with FinOps threshold checking."""

    def __init__(
        self,
        resource_id: str,
        metric: str,
        period_seconds: int = 86400,  # daily by default
        thresholds: dict[str, float] | None = None,
        predictor_type: str = "xgboost",  # "xgboost" or "linear"
    ):
        self.resource_id = resource_id
        self.metric = metric
        self.period_seconds = period_seconds

        # Resolve thresholds
        self.thresholds = thresholds or DEFAULT_THRESHOLDS.get(metric, {"warning": 80.0, "critical": 95.0})

        # Build predictor
        if predictor_type == "xgboost":
            self._predictor = _Predictor(period_seconds=period_seconds)
        else:
            from ml.predictors import LinearTrendPredictor
            self._predictor = LinearTrendPredictor(period_seconds=period_seconds)

    def fit(self, timestamps: list[int], values: list[float]) -> CapacityForecaster:
        """Train the forecaster on historical data."""
        self._predictor.fit(timestamps, values)
        return self

    def forecast(self, steps: int) -> dict[str, Any]:
        """Return a forecast for `steps` periods."""
        result = self._predictor.predict(steps)
        result["resource_id"] = self.resource_id
        result["metric"] = self.metric
        return result

    def forecast_with_intervals(self, steps: int, confidence: float = 0.95) -> dict[str, Any]:
        """Return a forecast with confidence intervals."""
        result = self._predictor.predict_interval(steps, confidence)
        result["resource_id"] = self.resource_id
        result["metric"] = self.metric
        return result

    def check_thresholds(self, forecast_result: dict[str, Any]) -> list[CapacityAlert]:
        """Check forecast values against FinOps thresholds.

        Generates CapacityAlert entries for any period where
        forecast_value exceeds warning or critical thresholds.
        """
        alerts: list[CapacityAlert] = []
        predictions = forecast_result.get("predictions", [])

        for i, value in enumerate(predictions):
            for severity in ("critical", "warning"):
                threshold = self.thresholds.get(severity)
                if threshold is not None and value >= threshold:
                    alerts.append(CapacityAlert(
                        resource_id=self.resource_id,
                        metric=self.metric,
                        threshold=threshold,
                        forecast_value=value,
                        horizon=i + 1,
                        severity=severity,
                    ))
                    break  # Only one alert per horizon step

        return alerts

    def days_until_threshold(self, threshold_key: str = "critical") -> float | None:
        """Estimate days until metric hits a threshold (linear extrapolation only).

        Returns None if the trend is downward or flat.
        """
        from ml.predictors import LinearTrendPredictor
        if not isinstance(self._predictor, LinearTrendPredictor):
            # Can't extrapolate from XGBoost easily — return None
            return None

        threshold = self.thresholds.get(threshold_key)
        if threshold is None:
            return None

        slope = getattr(self._predictor, "_slope", 0.0)
        if slope <= 0:
            return None

        last_value = getattr(self._predictor, "_values_history", [None])[-1]
        if last_value is None:
            return None

        days = (threshold - last_value) / (slope * 86400 / self.period_seconds)
        return max(0.0, days) if days > 0 else None
