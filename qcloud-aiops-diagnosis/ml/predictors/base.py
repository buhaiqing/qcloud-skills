# Copyright (c) 2026. All rights reserved.
"""Abstract base class for all ML predictors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BasePredictor(ABC):
    """Abstract base for capacity / trend predictors.

    All predictors share:
    - `fit(timestamps, values)` → train on historical data
    - `predict(steps)` → forecast N steps ahead
    - `predict_interval(steps)` → forecast with confidence bands
    """

    name: str = "BasePredictor"

    @abstractmethod
    def fit(self, timestamps: list[int], values: list[float]) -> BasePredictor:
        """Train the predictor.

        Args:
            timestamps: Unix epoch seconds (sorted ascending).
            values: Corresponding scalar values.

        Returns:
            self (for chaining).

        """
        raise NotImplementedError

    @abstractmethod
    def predict(self, steps: int) -> dict[str, Any]:
        """Forecast `steps` periods ahead.

        Returns:
            dict with keys:
            - "predictions": list[float] — forecasted values
            - "model": str
            - "horizon": int

        """
        raise NotImplementedError

    def predict_interval(self, steps: int, confidence: float = 0.95) -> dict[str, Any]:
        """Forecast with confidence intervals.

        Default implementation uses residual stddev as uniform interval width.
        Subclasses may override with proper quantile regression.
        """
        import math
        result = self.predict(steps)
        residuals = getattr(self, "_residuals", [])
        std = (
            math.sqrt(sum(r * r for r in residuals) / max(len(residuals) - 1, 1))
            if residuals
            else 0.0
        )
        z = 1.96 if confidence >= 0.95 else 1.645
        result["lower"] = [p - z * std for p in result["predictions"]]
        result["upper"] = [p + z * std for p in result["predictions"]]
        result["confidence"] = confidence
        return result
