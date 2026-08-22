from __future__ import annotations

import unittest

from agent_slo import DEFAULT_SLOS, SLO, SLOMonitor, render_dashboard


class SLOMonitorTest(unittest.TestCase):
    def test_record_and_compliance_all_pass(self) -> None:
        m = SLOMonitor(slos=[SLO(name="success_rate", target=0.99, window="30d")])
        m.record("agent-a", "success_rate", 0.995)
        m.record("agent-a", "success_rate", 1.0)
        self.assertEqual(m.compliance("agent-a")["success_rate"], 1.0)
        self.assertEqual(m.breaches("agent-a"), [])

    def test_compliance_partial(self) -> None:
        m = SLOMonitor(slos=[SLO(name="success_rate", target=0.99, window="30d")])
        m.record("agent-a", "success_rate", 0.995)
        m.record("agent-a", "success_rate", 0.5)
        self.assertAlmostEqual(m.compliance("agent-a")["success_rate"], 0.5)
        self.assertIn("success_rate", m.breaches("agent-a"))

    def test_latency_slo(self) -> None:
        m = SLOMonitor(slos=[SLO(name="p95_latency_ms", target=2000, window="30d")])
        m.record("agent-a", "p95_latency_ms", 1500)
        m.record("agent-a", "p95_latency_ms", 2500)
        self.assertAlmostEqual(m.compliance("agent-a")["p95_latency_ms"], 0.5)
        self.assertIn("p95_latency_ms", m.breaches("agent-a"))

    def test_no_samples_means_compliant(self) -> None:
        m = SLOMonitor(slos=[SLO(name="success_rate", target=0.99, window="30d")])
        self.assertEqual(m.compliance("agent-a")["success_rate"], 1.0)
        self.assertEqual(m.breaches("agent-a"), [])

    def test_default_slos(self) -> None:
        self.assertGreaterEqual(len(DEFAULT_SLOS), 2)
        names = [s.name for s in DEFAULT_SLOS]
        self.assertIn("success_rate", names)


class RenderDashboardTest(unittest.TestCase):
    def test_render_with_data(self) -> None:
        m = SLOMonitor(slos=[SLO(name="success_rate", target=0.99, window="30d")])
        m.record("agent-a", "success_rate", 1.0)
        out = render_dashboard(m)
        self.assertIn("SLO Dashboard", out)
        self.assertIn("agent-a", out)
        self.assertIn("success_rate", out)

    def test_render_no_data(self) -> None:
        m = SLOMonitor()
        out = render_dashboard(m)
        self.assertIn("No data", out)

    def test_render_deterministic(self) -> None:
        m = SLOMonitor(slos=[SLO(name="success_rate", target=0.99, window="30d")])
        m.record("agent-b", "success_rate", 0.99)
        m.record("agent-a", "success_rate", 1.0)
        out1 = render_dashboard(m)
        out2 = render_dashboard(m)
        self.assertEqual(out1, out2)


if __name__ == "__main__":
    unittest.main()
