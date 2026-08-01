# Copyright (c) 2026. All rights reserved.
"""XGBoost-based capacity predictor with feature engineering.

Graceful degradation: if xgboost is not installed, falls back to
LinearTrendPredictor so the same interface is always available.
"""

from __future__ import annotations

import math
from typing import Any

from ml.predictors.base import BasePredictor

_HAVE_XGB = False
_LinearPredictor: type[BasePredictor] | None = None

try:
    import xgboost as xgb

    _HAVE_XGB = True
except ImportError:
    pass


def _get_fallback() -> BasePredictor:
    """Lazily import fallback predictor."""
    global _LinearPredictor
    if _LinearPredictor is None:
        from ml.predictors.linear_trend import LinearTrendPredictor

        _LinearPredictor = LinearTrendPredictor
    return _LinearPredictor(period_seconds=3600)


class XGBoostCapacityPredictor(BasePredictor):
    """XGBoost regressor for capacity forecasting.

    Uses engineered time features:
    - hour-of-day (cyclical, sin/cos encoded)
    - day-of-week (cyclical)
    - trend index (linear)
    - lag features (last N values)

    Falls back to LinearTrendPredictor when xgboost is unavailable.

    Args:
        horizon_steps: Number of periods ahead to forecast.
        period_seconds: Duration of one period (default 3600 s = hourly).
        n_lags: Number of lag features to use (default 3).

    """

    name = "XGBoostCapacityPredictor"

    def __init__(
        self,
        horizon_steps: int = 24,
        period_seconds: int = 3600,
        n_lags: int = 3,
    ) -> None:
        """Initialize the capacity predictor.

        Args:
            horizon_steps: Number of periods ahead to forecast.
            period_seconds: Duration of one period in seconds.
            n_lags: Number of lag features.

        """
        self.horizon_steps = horizon_steps
        self.period_seconds = period_seconds
        self.n_lags = n_lags
        self._model: Any = None
        self._fallback: Any = None
        self._degraded = False
        self._values_history: list[float] = []

        if not _HAVE_XGB:
            self._degraded = True
            self._fallback = _get_fallback()

    def _build_features(self, ts: int, lag_values: list[float]) -> list[float]:
        """Build feature vector for a single timestamp."""
        hour = (ts % 86400) / 3600
        dow = (ts % 604800) / 86400
        return [
            math.sin(2 * math.pi * hour / 24),
            math.cos(2 * math.pi * hour / 24),
            math.sin(2 * math.pi * dow / 7),
            math.cos(2 * math.pi * dow / 7),
            float(ts),  # trend
            *lag_values,
        ]

    def fit(self, timestamps: list[int], values: list[float]) -> XGBoostCapacityPredictor:
        """Train XGBoost on (timestamp, value) pairs."""
        self._values_history = list(values)

        if self._degraded:
            self._fallback.fit(timestamps, values)
            return self

        import numpy as np

        # Build lag-augmented feature matrix
        feature_rows: list[list[float]] = []
        for i in range(len(timestamps)):
            lag_vals = values[max(0, i - self.n_lags) : i]
            lag_vals = ([0.0] * (self.n_lags - len(lag_vals))) + lag_vals
            feature_rows.append(self._build_features(timestamps[i], lag_vals))

        X = np.array(feature_rows, dtype=float)
        y = np.array(values, dtype=float)

        self._model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
        )
        self._model.fit(X, y)
        return self

    def predict(self, steps: int) -> dict[str, Any]:
        """Forecast `steps` periods ahead using recursive rolling prediction."""
        if self._degraded:
            result = self._fallback.predict(steps)
            result["degraded"] = True
            return result

        import numpy as np

        predictions: list[float] = []
        last_known_ts = self._values_history[-1] if self._values_history else 0

        for i in range(steps):
            ts = int(last_known_ts + (i + 1) * self.period_seconds)
            lag_vals = self._values_history[-self.n_lags :]
            padded = ([0.0] * (self.n_lags - len(lag_vals))) + list(lag_vals)
            feat = np.array([self._build_features(ts, padded)], dtype=float)
            pred = float(self._model.predict(feat)[0])
            predictions.append(max(0.0, pred))
            self._values_history.append(pred)

        return {
            "predictions": predictions,
            "model": self.name,
            "horizon": steps,
            "degraded": False,
        }

    def predict_interval(self, steps: int, confidence: float = 0.95) -> dict[str, Any]:
        """Predict with confidence intervals using residual stddev from training."""
        import numpy as np

        result = self.predict(steps)

        if self._degraded:
            return self._fallback.predict_interval(steps, confidence)

        # Use training residual stddev as approximate interval
        X = np.array(
            [
                self._build_features(0, [0.0] * self.n_lags),
            ]
            * len(self._values_history),
            dtype=float,
        )
        y_pred = self._model.predict(X)
        residuals = [self._values_history[i] - y_pred[i] for i in range(len(self._values_history))]
        std = math.sqrt(sum(r * r for r in residuals) / max(len(residuals) - 1, 1))
        z = 1.96 if confidence >= 0.95 else 1.645
        result["lower"] = [max(0.0, p - z * std) for p in result["predictions"]]
        result["upper"] = [p + z * std for p in result["predictions"]]
        result["confidence"] = confidence
        return result
