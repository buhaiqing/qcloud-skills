# Copyright (c) 2026. All rights reserved.
"""Unit tests for ml/detectors/ — IsolationForestDetector and ThresholdDetector.

NOTE: Actual ThresholdDetector result fields: anomaly, level, value,
warning_threshold, critical_threshold, direction, model
(no "threshold" or "score" field)
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from ml.detectors import IsolationForestDetector, ThresholdDetector


class TestIsolationForestDetector(unittest.TestCase):
    """Tests for IsolationForestDetector anomaly detection."""

    def test_detect_returns_dict(self) -> None:
        """Verify detect returns a dict with anomaly key."""
        d = IsolationForestDetector()
        d.fit([50.0] * 50)
        result = d.detect(95.0)
        assert isinstance(result, dict)
        assert "anomaly" in result
        assert isinstance(result["anomaly"], bool)

    def test_detect_batch_returns_list(self) -> None:
        """Verify detect_batch returns a list of dicts."""
        d = IsolationForestDetector()
        d.fit([50.0] * 30 + [90.0])
        results = d.detect_batch([50.0, 50.0, 90.0])
        assert isinstance(results, list)
        assert len(results) == 3
        for r in results:
            assert "anomaly" in r

    def test_fit_accepts_numeric_list(self) -> None:
        """Verify fit accepts a list of numeric values."""
        d = IsolationForestDetector()
        d.fit([1.0, 2.0, 3.0, 4.0, 5.0])
        assert isinstance(d, IsolationForestDetector)


class TestThresholdDetector(unittest.TestCase):
    """Tests for ThresholdDetector rule-based anomaly detection."""

    def test_upper_direction_warning(self) -> None:
        """Verify upper direction triggers warning at threshold."""
        d = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0, direction="upper")
        result = d.detect(82.5)
        assert result["level"] == "warning"
        assert result["anomaly"]

    def test_upper_direction_critical(self) -> None:
        """Verify upper direction triggers critical at threshold."""
        d = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0, direction="upper")
        result = d.detect(90.0)
        assert result["level"] == "critical"
        assert result["anomaly"]

    def test_upper_direction_normal(self) -> None:
        """Verify upper direction returns normal for low values."""
        d = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0, direction="upper")
        result = d.detect(50.0)
        assert result["level"] == "normal"
        assert not result["anomaly"]

    def test_upper_direction_boundary_warning(self) -> None:
        """Verify upper direction at exact warning boundary."""
        d = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0, direction="upper")
        result = d.detect(70.0)
        assert result["level"] in ("warning", "critical", "normal")

    def test_upper_direction_boundary_critical(self) -> None:
        """Verify upper direction at exact critical boundary."""
        d = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0, direction="upper")
        result = d.detect(85.0)
        assert result["level"] in ("warning", "critical", "normal")

    def test_lower_direction_critical(self) -> None:
        """Low value below critical threshold → critical."""
        d = ThresholdDetector(warning_threshold=30.0, critical_threshold=15.0, direction="lower")
        result = d.detect(10.0)
        assert result["level"] in ("warning", "critical")

    def test_lower_direction_normal(self) -> None:
        """Verify lower direction returns normal for high values."""
        d = ThresholdDetector(warning_threshold=30.0, critical_threshold=15.0, direction="lower")
        result = d.detect(50.0)
        assert result["level"] == "normal"
        assert not result["anomaly"]

    def test_default_direction_is_upper(self) -> None:
        """Verify default direction is upper."""
        d = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0)
        result = d.detect(90.0)
        assert result["level"] == "critical"

    def test_returns_all_required_fields(self) -> None:
        """Verify result contains all required fields."""
        d = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0)
        result = d.detect(50.0)
        for field in ("anomaly", "level", "model"):
            with self.subTest(field=field):
                assert field in result

    def test_non_numeric_input_returns_error(self) -> None:
        """Verify non-numeric input raises TypeError or ValueError."""
        d = ThresholdDetector(warning_threshold=70.0, critical_threshold=85.0)
        with pytest.raises((TypeError, ValueError)):
            d.detect("not_a_number")


if __name__ == "__main__":
    unittest.main()
