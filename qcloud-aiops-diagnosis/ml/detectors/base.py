"""Abstract base class for all ML anomaly detectors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseDetector(ABC):
    """Abstract base for anomaly detectors.

    All detectors share the same interface:
    - `fit(data)` → trains on historical data (optional for threshold-based)
    - `detect(point)` → returns anomaly score for a single point
    - `detect_batch(points)` → returns anomaly scores for multiple points
    """

    name: str = "BaseDetector"

    @abstractmethod
    def fit(self, data: list[float]) -> "BaseDetector":
        """Train the detector on historical values.

        Args:
            data: List of scalar values (e.g., metric readings).

        Returns:
            self (for chaining).
        """
        raise NotImplementedError

    @abstractmethod
    def detect(self, point: float) -> dict[str, Any]:
        """Detect anomaly for a single data point.

        Returns:
            dict with keys:
            - "anomaly": bool — True if point is anomalous
            - "score": float — raw anomaly score (0=normal, 1=max anomalous)
            - "threshold": float — effective threshold used
            - "model": str — self.name
        """
        raise NotImplementedError

    def detect_batch(self, points: list[float]) -> list[dict[str, Any]]:
        """Run detect() on a list of points."""
        return [self.detect(p) for p in points]
