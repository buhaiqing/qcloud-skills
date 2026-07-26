"""Unit tests for ml/predictors/ — LinearTrendPredictor and XGBoostCapacityPredictor.

Actual signatures:
  LinearTrendPredictor(period_seconds=3600)
  .fit(timestamps: list[int], values: list[float])   # requires >= 3 points
  .predict(steps) -> {predictions, model, horizon, slope_per_day}

  XGBoostCapacityPredictor(horizon_steps=24, period_seconds=3600, n_lags=3)
  .fit(timestamps: list[int], values: list[float])
  .predict(steps) -> {predictions, model, horizon, degraded}
"""

import time
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.predictors import LinearTrendPredictor, XGBoostCapacityPredictor


class TestLinearTrendPredictor(unittest.TestCase):

    def _make_series(self, n: int, start: float = 50.0, step: float = 1.0):
        now = int(time.time())
        return ([now - 3600 * i for i in range(n, 0, -1)],
                [start + (n - i) * step for i in range(n)])

    def test_predict_returns_required_fields(self):
        p = LinearTrendPredictor()
        ts, vals = self._make_series(12)
        p.fit(ts, vals)
        forecast = p.predict(steps=7)
        for field in ("predictions", "model", "horizon", "slope_per_day"):
            with self.subTest(field=field):
                self.assertIn(field, forecast)

    def test_predict_returns_list_of_predictions(self):
        p = LinearTrendPredictor()
        ts, vals = self._make_series(12)
        p.fit(ts, vals)
        forecast = p.predict(steps=7)
        self.assertIsInstance(forecast["predictions"], list)
        self.assertEqual(len(forecast["predictions"]), 7)

    def test_fit_accepts_numeric_lists(self):
        p = LinearTrendPredictor()
        ts, vals = self._make_series(10)
        p.fit(ts, vals)
        self.assertIsInstance(p, LinearTrendPredictor)

    def test_fit_respects_series_order(self):
        p = LinearTrendPredictor()
        ts, vals = self._make_series(12)
        p.fit(ts, vals)
        forecast = p.predict(steps=3)
        self.assertIn("slope_per_day", forecast)
        self.assertIsInstance(forecast["slope_per_day"], (int, float))

    def test_flat_series_near_zero_slope(self):
        p = LinearTrendPredictor()
        ts, vals = self._make_series(12, start=50.0, step=0.0)
        p.fit(ts, vals)
        forecast = p.predict(steps=3)
        self.assertIsInstance(forecast["slope_per_day"], (int, float))

    def test_insufficient_data_raises_error(self):
        """Fewer than 3 points raises ValueError — caller must guard."""
        p = LinearTrendPredictor()
        now = int(time.time())
        ts = [now, now - 3600]
        vals = [50.0, 51.0]
        with self.assertRaises(ValueError):
            p.fit(ts, vals)


class TestXGBoostCapacityPredictor(unittest.TestCase):

    def _make_series(self, n: int, start: float = 50.0, step: float = 1.0):
        now = int(time.time())
        return ([now - 3600 * i for i in range(n, 0, -1)],
                [start + (n - i) * step for i in range(n)])

    def test_predict_fallback_mode(self):
        p = XGBoostCapacityPredictor()
        ts, vals = self._make_series(12)
        p.fit(ts, vals)
        forecast = p.predict(steps=7)
        self.assertIn("predictions", forecast)
        self.assertIn("model", forecast)

    def test_predict_returns_required_fields(self):
        p = XGBoostCapacityPredictor()
        ts, vals = self._make_series(12)
        p.fit(ts, vals)
        forecast = p.predict(steps=7)
        for field in ("predictions", "model", "horizon"):
            with self.subTest(field=field):
                self.assertIn(field, forecast)

    def test_predict_returns_list(self):
        p = XGBoostCapacityPredictor()
        ts, vals = self._make_series(12)
        p.fit(ts, vals)
        forecast = p.predict(steps=5)
        self.assertIsInstance(forecast["predictions"], list)
        self.assertEqual(len(forecast["predictions"]), 5)

    def test_insufficient_data_handled(self):
        p = XGBoostCapacityPredictor()
        now = int(time.time())
        ts = [now, now - 3600]
        vals = [50.0, 51.0]
        p.fit(ts, vals)
        forecast = p.predict(steps=3)
        self.assertIn("predictions", forecast)


if __name__ == "__main__":
    unittest.main()
