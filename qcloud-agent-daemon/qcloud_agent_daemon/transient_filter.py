"""TransientStateFilter — whitelist of "normal transient" cloud states.

Per ADR-0002 D6 + Spec §6. Filters states like RUNNING / STOPPED (stable)
vs STARTING / STOPPING (transient — daemon must NOT treat as incident).
Unknown states are NOT classified as transient — they trigger human review.

Whitelist source: tests/fixtures/transient-states/<service>.json (per Plan T3.1).
Do NOT hardcode values here — load from fixtures and validate provenance.

Lazy-load strategy: each service's fixture is loaded on first classify()
call. known_services() reflects what's available on disk, not what was
queried — this matches user expectations ("which services can I classify?").
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

Classification = Literal["stable", "transient", "unknown"]

# All known services (must have a matching fixture file available when queried)
KNOWN_SERVICES = ("cvm", "cdb", "redis", "clb", "mongodb", "postgres", "ckafka")


class TransientStateFilter:
    """Filter cloud states into stable / transient / unknown.

    Lazy: per-service fixture is loaded on first classify() call.
    """

    def __init__(self, whitelist_dir: Path | str) -> None:
        self.whitelist_dir = Path(whitelist_dir)
        self._tables: dict[str, dict[str, set[str]]] = {}
        self._loaded: set[str] = set()
        # Verify whitelist_dir exists; known_services() will inspect it.
        if not self.whitelist_dir.is_dir():
            raise FileNotFoundError(
                f"Whitelist directory does not exist: {self.whitelist_dir}"
            )

    def _load(self, service: str) -> bool:
        """Load fixture for a service. Returns True if loaded, False if missing."""
        if service in self._loaded:
            return True
        path = self.whitelist_dir / f"{service}.json"
        if not path.is_file():
            return False
        data = json.loads(path.read_text(encoding="utf-8"))
        self._tables[service] = {
            "stable": set(data.get("stable_states", [])),
            "transient": set(data.get("transient_states", [])),
        }
        self._loaded.add(service)
        return True

    def is_transient(self, service: str, state: str) -> bool:
        """True = filter out (do not alarm); False = real state change."""
        return self.classify(service, state) == "transient"

    def classify(self, service: str, state: str) -> Classification:
        """Classify a (service, state) tuple.

        Returns 'unknown' if either:
          - the service fixture could not be loaded (missing file)
          - the state is in neither the stable nor transient set
          - the state appears in BOTH sets (config error → human review)
        """
        if not self._load(service):
            return "unknown"
        table = self._tables[service]
        is_stable = state in table["stable"]
        is_transient = state in table["transient"]
        if is_stable and is_transient:
            return "unknown"  # config error; route to human
        if is_transient:
            return "transient"
        if is_stable:
            return "stable"
        return "unknown"

    def known_services(self) -> tuple[str, ...]:
        """Return services whose fixture files exist in whitelist_dir.

        Reflects disk state, not query state — so callers can verify which
        services are available without having to query them first.
        """
        return tuple(
            sorted(
                svc for svc in KNOWN_SERVICES
                if (self.whitelist_dir / f"{svc}.json").is_file()
            )
        )


__all__ = ["Classification", "KNOWN_SERVICES", "TransientStateFilter"]
