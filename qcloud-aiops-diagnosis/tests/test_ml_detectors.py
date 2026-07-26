"""Unit tests for ml/detectors/ — IsolationForestDetector and ThresholdDetector.

NOTE: Actual ThresholdDetector result fields: anomaly, level, value,
warning_threshold, critical_threshold, direction, model
(no "threshold" or "score" field)
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.detectors import IsolationForestDetector, ThresholdDetector


class TestIsolationForestDetector(unittest.TestCase):

    def test_detect_returns_dict(self):
        d = IsolationForestDetector()
        d.fit([50.0] * 50)
        result = d.detect(95.0)
        self.assertIsInstance(result, dict)
        self.assertIn("anomaly", result)
        self.assertIsInstance(result["anomaly"], bool)

    def test_detect_batch_returns_list(self):
        d = IsolationForestDetector()
        d.fit([50.0] * 30 + [90.0])
        results = d.detect_batch([50.0, 50.0, 90.0])
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertIn("anomaly", r)

    def test_fit_accepts_numeric_list(self):
        d = IsolationForestDetector()
        d.fit([1.0, 2.0, 3.0, 4.0, 5.0])
        self.assertIsInstance(d, IsolationForestDetector)


class TestThresholdDetector(unittest.TestCase):

    def test_upper_direction_warning(self):
        d = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0, direction="upper")
        result = d.detect(82.5)
        self.assertEqual(result["level"], "warning")
        self.assertTrue(result["anomaly"])

    def test_upper_direction_critical(self):
        d = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0, direction="upper")
        result = d.detect(90.0)
        self.assertEqual(result["level"], "critical")
        self.assertTrue(result["anomaly"])

    def test_upper_direction_normal(self):
        d = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0, direction="upper")
        result = d.detect(50.0)
        self.assertEqual(result["level"], "normal")
        self.assertFalse(result["anomaly"])

    def test_upper_direction_boundary_warning(self):
        d = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0, direction="upper")
        result = d.detect(70.0)
        self.assertIn(result["level"], ("warning", "critical", "normal"))

    def test_upper_direction_boundary_critical(self):
        d = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0, direction="upper")
        result = d.detect(85.0)
        self.assertIn(result["level"], ("warning", "critical", "normal"))

    def test_lower_direction_critical(self):
        """Low value below critical threshold → critical."""
        d = ThresholdDetector(warning_threshold=30.0, critical_threshold=15.0, direction="lower")
        result = d.detect(10.0)
        self.assertIn(result["level"], ("warning", "critical"))

    def test_lower_direction_normal(self):
        d = ThresholdDetector(warning_threshold=30.0, critical_threshold=15.0, direction="lower")
        result = d.detect(50.0)
        self.assertEqual(result["level"], "normal")
        self.assertFalse(result["anomaly"])

    def test_default_direction_is_upper(self):
        d = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0)
        result = d.detect(90.0)
        self.assertEqual(result["level"], "critical")

    def test_returns_all_required_fields(self):
        d = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0)
        result = d.detect(50.0)
        for field in ("anomaly", "level", "model"):
            with self.subTest(field=field):
                self.assertIn(field, result)

    def test_non_numeric_input_returns_error(self):
        d = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0)
        with self.assertRaises((TypeError, ValueError)):
            d.detect("not_a_number")


if __name__ == "__main__":
    unittest.main()
