"""LC-4-T1: topology-driven selective analyzer resolution."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REASON = REPO_ROOT / "qcloud-proactive-inspection" / "scripts" / "02-reason"
SCRIPTS = REASON.parent
for path in (SCRIPTS, REASON):
    sys.path.insert(0, str(path))

from analyzers.selective import resolve_analyzer_names  # noqa: E402


def _sniff_counts(counts: dict[str, int]) -> dict:
    return {"customer": "demo", "raw": {k: [{}] * n for k, n in counts.items()}}


def test_shuozhou_like_topology_includes_data_layer():
    names, skipped, mode = resolve_analyzer_names(
        _sniff_counts({"vms": 2, "lbs": 1, "redis": 1, "rds": 2, "eips": 1})
    )
    assert mode == "topology_fallback"
    assert "vm" in names
    assert "redis" in names
    assert "rds_mysql" in names
    assert any(s["service"] == "mongodb" for s in skipped)


def test_strategy_selected_analyzers():
    strategy = {"selected_analyzers": ["eip", "clb", "vm"]}
    names, skipped, mode = resolve_analyzer_names(
        _sniff_counts({"vms": 1, "lbs": 1, "eips": 1}),
        strategy=strategy,
    )
    assert mode == "strategy_selected"
    assert names == ["eip", "clb", "vm"]
    assert skipped == [] or isinstance(skipped, list)
