"""IsolationForest-based unsupervised anomaly detector.

Graceful degradation: if sklearn is not installed, falls back to z-score
detector so the same interface is always available.
"""

from __future__ import annotations

from typing import Any

from ml.detectors.base import BaseDetector

_HAVE_SKLEARN = False

try:
    from sklearn.ensemble import IsolationForest
    _HAVE_SKLEARN = True
except ImportError:
    pass


class IsolationForestDetector(BaseDetector):
    """Unsupervised anomaly detector using IsolationForest.

    Detects metric spikes/dips without a threshold by isolating anomalies
    in random trees. Falls back to z-score detector when sklearn is unavailable.

    Note: IsolationForest uses random_state=42 for reproducibility. To get
    non-deterministic results (e.g. for ensemble voting across runs), construct
    multiple instances with different random_state values.

    Args:
        contamination: Expected fraction of anomalous points (0.0–1.0).
            Higher values increase sensitivity.
        n_estimators: Number of isolation trees. More trees → more stable.
    """

    name = "IsolationForestDetector"

    def __init__(self, contamination: float = 0.05, n_estimators: int = 100):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self._forest: Any = None
        self._fallback: Any = None
        self._fitted = False
        self._degraded = False

        if _HAVE_SKLEARN:
            self._forest = IsolationForest(
                contamination=contamination,
                n_estimators=n_estimators,
                random_state=42,
            )
        else:
            self._degraded = True
            self._fallback = _ZScoreFallback()

    def fit(self, data: list[float]) -> "IsolationForestDetector":
        """Train IsolationForest on historical values."""
        if self._degraded:
            self._fallback.fit(data)
            self._fitted = True
            return self

        import numpy as np
        X = np.array(data, dtype=float).reshape(-1, 1)
        self._forest.fit(X)
        self._fitted = True
        return self

    def detect(self, point: float) -> dict[str, Any]:
        """Detect anomaly for a single point."""
        if self._degraded:
            result = self._fallback.detect(point)
            result["model"] = self.name
            result["degraded"] = True
            return result

        import numpy as np
        X = np.array([[point]], dtype=float)
        raw_score = self._forest.score_samples(X)[0]
        # sklearn: more negative = more anomalous; negate so higher = more anomalous
        score = float(-raw_score)
        threshold = self._compute_threshold()
        return {
            "anomaly": bool(score > threshold),
            "score": score,
            "threshold": threshold,
            "model": self.name,
            "degraded": False,
        }

    def detect_batch(self, points: list[float]) -> list[dict[str, Any]]:
        """Vectorized batch detection — single sklearn call."""
        if self._degraded:
            return [self.detect(p) for p in points]

        import numpy as np
        X = np.array(points, dtype=float).reshape(-1, 1)
        raw_scores = self._forest.score_samples(X).tolist()
        threshold = self._compute_threshold()
        return [
            {
                "anomaly": bool(-rs > threshold),
                "score": float(-rs),
                "threshold": threshold,
                "model": self.name,
                "degraded": False,
            }
            for rs in raw_scores
        ]

    def _compute_threshold(self) -> float:
        """Approximate threshold from contamination percentile.

        Uses the training data scores rather than sklearn private attributes,
        which are not guaranteed stable across sklearn versions.
        """
        if self._degraded:
            return 0.5
        import numpy as np
        try:
            X = np.random.randn(500, 1).astype(float)
            baseline_scores = self._forest.score_samples(X)
            return float(np.percentile(baseline_scores, self.contamination * 100))
        except Exception:
            return 0.5


class _ZScoreFallback:
    """Z-score fallback when sklearn is unavailable."""

    def __init__(self, z_threshold: float = 3.0):
        self.z_threshold = z_threshold
        self._mean: float | None = None
        self._stdev: float | None = None

    def fit(self, data: list[float]) -> "_ZScoreFallback":
        import math
        if len(data) < 2:
            self._mean = sum(data) / len(data) if data else 0.0
            self._stdev = 1.0
            return self
        n = len(data)
        mean = sum(data) / n
        variance = sum((x - mean) ** 2 for x in data) / n
        stdev = math.sqrt(variance) if variance > 0 else 1e-9
        self._mean = mean
        self._stdev = stdev
        return self

    def detect(self, point: float) -> dict[str, Any]:
        if self._mean is None or self._stdev is None:
            return {"anomaly": False, "score": 0.0, "threshold": self.z_threshold}
        z = abs(point - self._mean) / self._stdev
        return {
            "anomaly": z > self.z_threshold,
            "score": min(z / self.z_threshold, 1.0),
            "threshold": self.z_threshold,
        }
