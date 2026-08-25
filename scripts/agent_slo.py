from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SLO:
    name: str
    target: float
    window: str


DEFAULT_SLOS: list[SLO] = [
    SLO(name="success_rate", target=0.99, window="30d"),
    SLO(name="p95_latency_ms", target=2000, window="30d"),
    SLO(name="availability", target=0.995, window="30d"),
]

# For latency SLO the value must be <= target; for rate/availability >= target.
# Determine direction by SLO name heuristic: latency metrics are "lower is better".
_LATENCY_KEYWORDS = ("latency", "p95", "p99", "duration")


def _meets_target(slo: SLO, value: float) -> bool:
    is_latency = any(k in slo.name for k in _LATENCY_KEYWORDS)
    if is_latency:
        return value <= slo.target
    return value >= slo.target


@dataclass
class SLOMonitor:
    slos: list[SLO] = field(default_factory=lambda: list(DEFAULT_SLOS))
    _samples: dict[str, dict[str, list[float]]] = field(default_factory=dict, init=False, repr=False)

    def record(self, agent: str, metric: str, value: float) -> None:
        self._samples.setdefault(agent, {}).setdefault(metric, []).append(value)

    def compliance(self, agent: str) -> dict[str, float | None]:
        """Compliance ratio per SLO. ``None`` = no samples (N/A).

        Missing telemetry MUST NOT read as a perfect SLO (lesson L8:
        "green but vacuous") — callers get ``None`` and ``breaches()``
        treats it as a breach.
        """
        result: dict[str, float | None] = {}
        agent_data = self._samples.get(agent, {})
        for slo in self.slos:
            samples = agent_data.get(slo.name, [])
            if not samples:
                result[slo.name] = None
                continue
            passing = sum(1 for v in samples if _meets_target(slo, v))
            result[slo.name] = passing / len(samples)
        return result

    def breaches(self, agent: str) -> list[str]:
        comp = self.compliance(agent)
        breached: list[str] = []
        for slo in self.slos:
            c = comp.get(slo.name)
            # Breach if any sample missed target OR no data at all —
            # an unobserved SLO is an alerting gap, not compliance.
            if c is None or c < 1.0:
                breached.append(slo.name)
        return breached



def render_dashboard(monitor: SLOMonitor) -> str:
    agents = sorted(monitor._samples.keys())
    if not agents:
        return "# SLO Dashboard\n\nNo data.\n"
    lines = ["# SLO Dashboard", ""]
    lines.append("| agent | SLO | target | compliance | breached |")
    lines.append("| --- | --- | --- | --- | --- |")
    for agent in agents:
        comp = monitor.compliance(agent)
        breached_set = set(monitor.breaches(agent))
        for slo in monitor.slos:
            c = comp.get(slo.name)
            c_str = "N/A" if c is None else f"{c:.1%}"
            breached = "yes" if slo.name in breached_set else "no"
            lines.append(f"| {agent} | {slo.name} | {slo.target} | {c_str} | {breached} |")
    lines.append("")
    return "\n".join(lines)
