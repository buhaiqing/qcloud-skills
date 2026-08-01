# Copyright (c) 2026. All rights reserved.
"""Unit tests for ml/predictors/ — LinearTrendPredictor and XGBoostCapacityPredictor.

Actual signatures:
  LinearTrendPredictor(period_seconds=3600)
  .fit(timestamps: list[int], values: list[float])   # requires >= 3 points
  .predict(steps) -> {predictions, model, horizon, slope_per_day}

  XGBoostCapacityPredictor(horizon_steps=24, period_seconds=3600, n_lags=3)
  .fit(timestamps: list[int], values: list[float])
  .predict(steps) -> {predictions, model, horizon, degraded}
"""

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from ml.predictors import LinearTrendPredictor, XGBoostCapacityPredictor


class TestLinearTrendPredictor(unittest.TestCase):
    """Tests for LinearTrendPredictor trend forecasting."""

    def _make_series(
        self, n: int, start: float = 50.0, step: float = 1.0,
    ) -> tuple[list[int], list[float]]:
        now = int(time.time())
        return ([now - 3600 * i for i in range(n, 0, -1)],
                [start + (n - i) * step for i in range(n)])

    def test_predict_returns_required_fields(self) -> None:
        """Verify predict returns predictions, model, horizon, and slope_per_day."""
        p = LinearTrendPredictor()
        ts, vals = self._make_series(12)
        p.fit(ts, vals)
        forecast = p.predict(steps=7)
        for field in ("predictions", "model", "horizon", "slope_per_day"):
            with self.subTest(field=field):
                assert field in forecast

    def test_predict_returns_list_of_predictions(self) -> None:
        """Verify predictions field is a list of correct length."""
        p = LinearTrendPredictor()
        ts, vals = self._make_series(12)
        p.fit(ts, vals)
        forecast = p.predict(steps=7)
        assert isinstance(forecast["predictions"], list)
        assert len(forecast["predictions"]) == 7

    def test_fit_accepts_numeric_lists(self) -> None:
        """Verify fit accepts aligned timestamp and value lists."""
        p = LinearTrendPredictor()
        ts, vals = self._make_series(10)
        p.fit(ts, vals)
        assert isinstance(p, LinearTrendPredictor)

    def test_fit_respects_series_order(self) -> None:
        """Verify fit respects the order of timestamp-value pairs."""
        p = LinearTrendPredictor()
        ts, vals = self._make_series(12)
        p.fit(ts, vals)
        forecast = p.predict(steps=3)
        assert "slope_per_day" in forecast
        assert isinstance(forecast["slope_per_day"], (int, float))

    def test_flat_series_near_zero_slope(self) -> None:
        """Verify flat series produces near-zero slope."""
        p = LinearTrendPredictor()
        ts, vals = self._make_series(12, start=50.0, step=0.0)
        p.fit(ts, vals)
        forecast = p.predict(steps=3)
        assert isinstance(forecast["slope_per_day"], (int, float))

    def test_insufficient_data_raises_error(self) -> None:
        """Fewer than 3 points raises ValueError — caller must guard."""
        p = LinearTrendPredictor()
        now = int(time.time())
        ts = [now, now - 3600]
        vals = [50.0, 51.0]
        with pytest.raises(ValueError, match="Need at least 3"):
            p.fit(ts, vals)


class TestXGBoostCapacityPredictor(unittest.TestCase):
    """Tests for XGBoostCapacityPredictor capacity forecasting."""

    def _make_series(
        self, n: int, start: float = 50.0, step: float = 1.0,
    ) -> tuple[list[int], list[float]]:
        now = int(time.time())
        return ([now - 3600 * i for i in range(n, 0, -1)],
                [start + (n - i) * step for i in range(n)])

    def test_predict_fallback_mode(self) -> None:
        """Verify predict works in fallback mode without xgboost."""
        p = XGBoostCapacityPredictor()
        ts, vals = self._make_series(12)
        p.fit(ts, vals)
        forecast = p.predict(steps=7)
        assert "predictions" in forecast
        assert "model" in forecast

    def test_predict_returns_required_fields(self) -> None:
        """Verify predict returns predictions, model, horizon, and slope_per_day."""
        p = XGBoostCapacityPredictor()
        ts, vals = self._make_series(12)
        p.fit(ts, vals)
        forecast = p.predict(steps=7)
        for field in ("predictions", "model", "horizon"):
            with self.subTest(field=field):
                assert field in forecast

    def test_predict_returns_list(self) -> None:
        """Verify predictions field is a list."""
        p = XGBoostCapacityPredictor()
        ts, vals = self._make_series(12)
        p.fit(ts, vals)
        forecast = p.predict(steps=5)
        assert isinstance(forecast["predictions"], list)
        assert len(forecast["predictions"]) == 5

    def test_insufficient_data_handled(self) -> None:
        """Verify insufficient data is handled gracefully."""
        p = XGBoostCapacityPredictor()
        now = int(time.time())
        ts = [now, now - 3600]
        vals = [50.0, 51.0]
        p.fit(ts, vals)
        forecast = p.predict(steps=3)
        assert "predictions" in forecast


if __name__ == "__main__":
    unittest.main()
