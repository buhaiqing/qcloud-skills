"""Unit tests for selective analyzer resolution."""

# pyright: reportMissingImports=false
# analyzers/ is reachable at runtime via sys.path injection below; pyright's static analysis can't see it.
from __future__ import annotations

import sys
from pathlib import Path

REASON = Path(__file__).resolve().parent / "02-reason"
SCRIPTS = Path(__file__).resolve().parent
for path in (SCRIPTS, REASON):
    sys.path.insert(0, str(path))

from analyzers import create_by_names, list_available  # noqa: E402
from analyzers.selective import list_catalog, resolve_analyzer_names  # noqa: E402


def test_catalog_has_eleven_analyzers():
    assert len(list_catalog()) == 11


def test_create_by_names_returns_instances():
    names = ["vm", "clb", "redis"]
    instances = create_by_names(names)
    assert len(instances) == 3
    assert {a.service_name for a in instances} == {"vm", "clb", "redis"}


def test_topology_fallback_skips_empty_services():
    topology = {
        "customer": "demo",
        "raw": {"vms": [{}], "lbs": [], "redis": [{}], "rds": [], "eips": []},
    }
    names, skipped, mode = resolve_analyzer_names(topology)
    assert mode == "topology_fallback"
    assert "vm" in names
    assert "redis" in names
    assert any(s["service"] == "clb" and s["reason"] == "topology_count=0" for s in skipped)


def test_registry_lists_all_analyzers():
    create_by_names(list_catalog())
    available = set(list_available())
    assert available == set(list_catalog())
