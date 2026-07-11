"""Resolve which analyzers to run — strategy / explicit list / topology fallback."""

from __future__ import annotations

from typing import Any

# Registry names → sniff raw keys (None = always eligible for discover())
_ANALYZER_RAW_KEYS: dict[str, str | None] = {
    "vm": "vms",
    "clb": "lbs",
    "eip": "eips",
    "redis": "redis",
    "rds_mysql": "rds",
    "rds_postgresql": "rds",
    "mongodb": "mongodb",
    "elasticsearch": "es",
    "nat": None,
    "k8s": "vms",
    "security_group": None,
}

_CATALOG_ORDER = [
    "eip",
    "clb",
    "vm",
    "redis",
    "rds_mysql",
    "rds_postgresql",
    "mongodb",
    "elasticsearch",
    "nat",
    "k8s",
    "security_group",
]

_LAYER_ANALYZERS: dict[str, list[str]] = {
    "公网入口": ["eip", "clb"],
    "数据层": ["redis", "rds_mysql", "rds_postgresql", "mongodb", "elasticsearch"],
    "应用层": ["vm", "k8s"],
    "出口层": ["eip", "nat"],
    "网络基础": ["security_group"],
}


def list_catalog() -> list[str]:
    return list(_CATALOG_ORDER)


def topology_count(raw: dict[str, Any], analyzer_name: str) -> int:
    key = _ANALYZER_RAW_KEYS.get(analyzer_name)
    if key is None:
        return 1
    return len(raw.get(key) or [])


def _dedupe_preserve_order(names: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for name in names:
        if name in _ANALYZER_RAW_KEYS and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _from_priority_chain(priority_chain: list[dict[str, Any]], raw: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in priority_chain:
        if str(item.get("analysis_depth", "")).lower() == "skip":
            continue
        layer = str(item.get("layer", ""))
        for analyzer in _LAYER_ANALYZERS.get(layer, []):
            if topology_count(raw, analyzer) > 0:
                names.append(analyzer)
    return _dedupe_preserve_order(names)


def resolve_analyzer_names(
    topology_data: dict[str, Any],
    *,
    explicit: list[str] | None = None,
    strategy: dict[str, Any] | None = None,
) -> tuple[list[str], list[dict[str, str]], str]:
    """Return (names to run, skipped records, selection_mode)."""
    raw = topology_data.get("raw") or {}
    skipped: list[dict[str, str]] = []
    seen_skip: set[str] = set()

    def _record_skip(service: str, reason: str) -> None:
        if service in seen_skip:
            return
        seen_skip.add(service)
        skipped.append({"service": service, "reason": reason})

    if explicit:
        names = []
        for name in explicit:
            if name not in _ANALYZER_RAW_KEYS:
                continue
            if topology_count(raw, name) <= 0:
                _record_skip(name, "topology_count=0")
            else:
                names.append(name)
        return names, skipped, "explicit"

    if strategy:
        for item in strategy.get("skipped_analyzers") or []:
            svc = str(item.get("service", ""))
            reason = str(item.get("reason", "strategy_skip"))
            if svc:
                _record_skip(svc, reason)

        selected = strategy.get("selected_analyzers")
        if selected:
            names = []
            for name in selected:
                if name not in _ANALYZER_RAW_KEYS:
                    continue
                if topology_count(raw, name) <= 0:
                    _record_skip(name, "topology_count=0")
                else:
                    names.append(name)
            return names, skipped, "strategy_selected"

        chain = strategy.get("priority_chain")
        if chain:
            names = _from_priority_chain(chain, raw)
            for name in _CATALOG_ORDER:
                if name not in names and topology_count(raw, name) > 0:
                    _record_skip(name, "not_in_priority_chain")
            return names, skipped, "strategy_priority_chain"

    # Topology fallback — only analyzers with resources (ponytail: not 11-way full run)
    names = []
    for name in _CATALOG_ORDER:
        if topology_count(raw, name) > 0:
            names.append(name)
        else:
            _record_skip(name, "topology_count=0")
    return names, skipped, "topology_fallback"
