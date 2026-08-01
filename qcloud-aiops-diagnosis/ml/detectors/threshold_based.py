# Copyright (c) 2026. All rights reserved.
"""Threshold-based rule anomaly detector.

No external dependencies. Supports both upper-bound (CPU > 85%) and
lower-bound (error rate < 1%) anomaly directions.
"""

from __future__ import annotations

from typing import Any

from ml.detectors.base import BaseDetector


class ThresholdDetector(BaseDetector):
    """Rule-based detector for metrics with well-known thresholds.

    Args:
        warning_threshold: Value above/below which a warning is raised.
        critical_threshold: Value above/below which a critical is raised.
            If None, only warning-level detection is active.
        direction: "upper" (high values are anomalous) or "lower" (low values are anomalous).

    """

    name = "ThresholdDetector"

    def __init__(
        self,
        warning_threshold: float,
        critical_threshold: float | None = None,
        direction: str = "upper",
    ) -> None:
        """Initialize the threshold detector.

        Args:
            warning_threshold: Value above/below which a warning is raised.
            critical_threshold: Value above/below which a critical is raised.
            direction: "upper" or "lower".

        """
        d = direction.lower()
        if d not in ("upper", "lower"):
            msg = "direction must be 'upper' or 'lower'"
            raise ValueError(msg)
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.direction = d

    def fit(self, data: list[float]) -> ThresholdDetector:
        """No training required for threshold-based detector."""
        return self

    def detect(self, point: float) -> dict[str, Any]:
        """Detect anomaly for a single point.

        Returns:
            {anomaly, level, value, warning_threshold, critical_threshold, direction, model}
            level is "critical" | "warning" | "normal"

        """
        if self.direction == "upper":
            if self.critical_threshold is not None and point >= self.critical_threshold:
                level, anomaly = "critical", True
            elif point >= self.warning_threshold:
                level, anomaly = "warning", True
            else:
                level, anomaly = "normal", False
        elif self.critical_threshold is not None and point <= self.critical_threshold:
            level, anomaly = "critical", True
        elif point <= self.warning_threshold:
            level, anomaly = "warning", True
        else:
            level, anomaly = "normal", False

        return {
            "anomaly": anomaly,
            "level": level,
            "value": point,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "direction": self.direction,
            "model": self.name,
        }

    def detect_batch(self, points: list[float]) -> list[dict[str, Any]]:
        """Run detect() on a list of points."""
        return [self.detect(p) for p in points]
