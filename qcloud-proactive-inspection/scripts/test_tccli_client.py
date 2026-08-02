"""Unit tests for the tccli_client metric-fetch concurrency fix.

The tccli subprocess calls are mocked: the test focuses on the threading,
ordering, and error-degradation contract of ``TccliClient.get_metrics_batch``,
not on the real CLI.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from lib import tccli_client


def _ok_response(values: list[float], timestamps: list[int]) -> dict:
    """A valid monitor response (as returned by ``_run_tccli``: the inner Response)."""
    return {"DataPoints": [{"Timestamps": timestamps, "Values": values}]}


class TccliClientGetMetricsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = tccli_client.TccliClient(region="ap-guangzhou")

    def test_parallel_fetch_preserves_metric_order(self):
        responses = {
            "cpu_usage": _ok_response([10.0, 20.0], [100, 200]),
            "mem_usage": _ok_response([30.0, 40.0], [100, 200]),
            "disk_usage": _ok_response([50.0], [100]),
        }

        def fake_run(product, operation, region, extra):
            # The metric name is the value of the "--MetricName" flag (4th extra arg).
            metric = extra[3]
            return responses[metric]

        with mock.patch.object(tccli_client, "_run_tccli", side_effect=fake_run) as m:
            result = self.client.get_metrics_batch("ins-abc", ["cpu_usage", "mem_usage", "disk_usage"])

        # Returned dict must preserve the input metric order (no ordering regression).
        self.assertEqual(list(result.keys()), ["cpu_usage", "mem_usage", "disk_usage"])
        self.assertEqual(result["cpu_usage"], [(100, 10.0), (200, 20.0)])
        self.assertEqual(result["mem_usage"], [(100, 30.0), (200, 40.0)])
        self.assertEqual(result["disk_usage"], [(100, 50.0)])
        # Every metric must have been fetched exactly once.
        self.assertEqual(m.call_count, 3)

    def test_error_metric_is_skipped_others_survive(self):
        responses = {
            "good": _ok_response([1.0], [100]),
            "bad": {"_error": "AuthFailure", "_stderr": "denied"},
        }

        def fake_run(product, operation, region, extra):
            return responses[extra[3]]

        with mock.patch.object(tccli_client, "_run_tccli", side_effect=fake_run):
            result = self.client.get_metrics_batch("ins-abc", ["good", "bad"])

        # The errored metric must be degraded (skipped), the healthy one retained.
        self.assertEqual(list(result.keys()), ["good"])
        self.assertEqual(result["good"], [(100, 1.0)])

    def test_empty_points_metric_is_skipped(self):
        responses = {
            "has_data": _ok_response([1.0], [100]),
            "no_data": {"DataPoints": []},
        }

        def fake_run(product, operation, region, extra):
            return responses[extra[3]]

        with mock.patch.object(tccli_client, "_run_tccli", side_effect=fake_run):
            result = self.client.get_metrics_batch("ins-abc", ["has_data", "no_data"])

        self.assertEqual(list(result.keys()), ["has_data"])

    def test_subprocess_timeout_still_propagates(self):
        # The serial path propagated non-RuntimeError failures (e.g. TimeoutExpired);
        # the parallel path must preserve that abort-on-failure contract.
        def fake_run(product, operation, region, extra):
            raise subprocess.TimeoutExpired(cmd=["tccli"], timeout=90)

        with mock.patch.object(tccli_client, "_run_tccli", side_effect=fake_run):
            with self.assertRaises(subprocess.TimeoutExpired):
                self.client.get_metrics_batch("ins-abc", ["cpu_usage"])

    def test_metrics_fetch_run_concurrently(self):
        # A barrier of size 3 proves the three metric fetches overlap: if the loop
        # were still serial, the first fetch would wait for 3 parties and time out.
        barrier = threading.Barrier(3, timeout=5)
        responses = {f"m{i}": _ok_response([float(i)], [100]) for i in range(3)}

        def fake_run(product, operation, region, extra):
            barrier.wait()
            return responses[extra[3]]

        with mock.patch.object(tccli_client, "_run_tccli", side_effect=fake_run) as m:
            result = self.client.get_metrics_batch("ins-abc", ["m0", "m1", "m2"], max_workers=3)

        self.assertEqual(sorted(result.keys()), ["m0", "m1", "m2"])
        self.assertEqual(m.call_count, 3)


if __name__ == "__main__":
    unittest.main()
