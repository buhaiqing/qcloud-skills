"""Linear trend predictor for capacity planning.

No external dependencies. Uses ordinary least-squares (OLS) to fit a line
through (timestamp, value) points and extrapolate.
"""

from __future__ import annotations

import math  # noqa: F401 — kept for public API; used in predict_interval
from typing import Any

from ml.predictors.base import BasePredictor


class LinearTrendPredictor(BasePredictor):
    """Simple linear regression predictor.

    Fits y = slope * t + intercept via OLS. No external libs required.
    Works on any regularly-spaced time series.

    Args:
        period_seconds: Duration of one "step" in the forecast horizon
            (e.g., 3600 for hourly, 86400 for daily).
    """

    name = "LinearTrendPredictor"

    def __init__(self, period_seconds: int = 3600):
        self.period_seconds = period_seconds
        self._slope: float | None = None
        self._intercept: float | None = None
        self._residuals: list[float] = []
        self._t_mean: float | None = None
        self._y_mean: float | None = None

    def fit(self, timestamps: list[int], values: list[float]) -> "LinearTrendPredictor":
        """Fit OLS line through (timestamp, value) pairs."""
        if len(timestamps) < 3 or len(timestamps) != len(values):
            raise ValueError("Need at least 3 aligned (timestamps, values) pairs.")

        n = len(timestamps)
        t_arr = [float(t) for t in timestamps]
        y_arr = list(values)

        t_mean = sum(t_arr) / n
        y_mean = sum(y_arr) / n

        num = sum((t_arr[i] - t_mean) * (y_arr[i] - y_mean) for i in range(n))
        denom = sum((t_arr[i] - t_mean) ** 2 for i in range(n))

        if abs(denom) < 1e-12:
            self._slope = 0.0
            self._intercept = y_mean
        else:
            self._slope = num / denom
            self._intercept = y_mean - self._slope * t_mean

        self._t_mean = t_mean
        self._y_mean = y_mean

        # Compute residuals
        self._residuals = [y_arr[i] - (self._slope * t_arr[i] + self._intercept) for i in range(n)]

        return self

    def predict(self, steps: int) -> dict[str, Any]:
        """Extrapolate line `steps` periods ahead."""
        if self._slope is None:
            raise RuntimeError("Model not fitted. Call fit() first.")

        last_ts = max(getattr(self, "_last_ts", 0), self._t_mean or 0)
        predictions = [
            self._slope * (last_ts + (i + 1) * self.period_seconds) + self._intercept
            for i in range(steps)
        ]
        self._last_ts = last_ts + steps * self.period_seconds

        return {
            "predictions": [max(0.0, p) for p in predictions],  # capacities can't go negative
            "model": self.name,
            "horizon": steps,
            "slope_per_day": self._slope * 86400 if self.period_seconds != 86400 else None,
        }

    def predict_interval(self, steps: int, confidence: float = 0.95) -> dict[str, Any]:
        """Predict with confidence bands from residual stddev."""
        result = self.predict(steps)
        n = len(self._residuals)
        std = (
            math.sqrt(sum(r * r for r in self._residuals) / max(n - 2, 1))
            if n > 2
            else 0.0
        )
        z = 1.96 if confidence >= 0.95 else 1.645
        result["lower"] = [max(0.0, p - z * std) for p in result["predictions"]]
        result["upper"] = [p + z * std for p in result["predictions"]]
        result["confidence"] = confidence
        return result
