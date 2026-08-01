# Copyright (c) 2026. All rights reserved.
"""Resource normalization helpers for proactive-inspection scripts."""

from __future__ import annotations


def _camel(key: str) -> str:
    """CamelCase -> lowerCamelCase key (InstanceId -> instanceId)."""
    return key[0].lower() + key[1:] if key else key


def normalize_resource(item: dict) -> dict:
    """Recursively normalize tccli CamelCase keys to lowerCamelCase.

    Tags become `tags` with `key`/`value` pairs; values are preserved as-is.
    Unknown-shaped entries pass through unchanged so callers can also check
    the original keys (e.g. `vm.get("SecurityGroupIds")`).
    """
    if not isinstance(item, dict):
        return item
    normalized: dict = {}
    for key, value in item.items():
        nk = _camel(str(key))
        if isinstance(value, dict):
            normalized[nk] = normalize_resource(value)
        elif isinstance(value, list):
            normalized[nk] = [normalize_resource(v) if isinstance(v, dict) else v for v in value]
        else:
            normalized[nk] = value
    return normalized
