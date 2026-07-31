"""P3.3 + P3.4 — attribution + allocation.

P3.3: build_attribution_tree(observations) -> AttributionTree
  Walks observation.metadata, takes first non-null value per scope; idempotent.

P3.4: allocate_cost(total, attribution_keys, method, weights/shares) ->
  list[AllocationRecord]
  Methods:
    direct       - one AttributionKey gets 100%
    shared       - even split across declared keys
    resource     - weighted by weights[key_value] (resource_count vector)
    request      - weighted by weights[key_value] (request_count vector)
    usage        - weighted by weights[key_value] (token / unit vector)
    equal_split  - alias for shared
  Empty keys -> single ('scope', 'unallocated') bucket carrying 100%.
"""
from __future__ import annotations

import uuid
from collections.abc import Iterable

from copilot.trace_records import (
    AllocationRecord,
    AttributionTree,
    ObservationRecord,
)

# ---------------------------------------------------------------------------
# P3.3 — AttributionTree builder
# ---------------------------------------------------------------------------


_ATTRIBUTION_FIELDS = (
    "tenant_id",
    "customer_id",
    "account_id_hash",
    "business_unit",
    "cost_center",
    "region",
    "service",
    "environment",
    "product",
    "resource_id",
)


def build_attribution_tree(observations: Iterable[ObservationRecord]) -> AttributionTree:
    """Build an AttributionTree from observation metadata.

    First non-null value per scope wins (idempotent for stable ordering of input).
    Unknown metadata keys are ignored; empty list yields all-None tree.
    """
    init = {f: None for f in _ATTRIBUTION_FIELDS}
    for obs in observations:
        md = obs.metadata or {}
        for field_name in _ATTRIBUTION_FIELDS:
            if init[field_name] is None and isinstance(md.get(field_name), str) and md.get(field_name):
                init[field_name] = md[field_name]
    return AttributionTree(**init)


# ---------------------------------------------------------------------------
# P3.4 — allocate_cost
# ---------------------------------------------------------------------------


_METHODS = ("direct", "shared", "resource", "request", "usage", "equal_split")
_WEIGHTED_METHODS = ("resource", "request", "usage")


def _key_value(key: tuple[str, str]) -> str:
    """Return the value portion of an attribution key."""
    return key[1] if len(key) > 1 else ""


def _allocate(
    total_cost: float,
    keys: list[tuple[str, str]],
    method: str,
    weights: dict[str, float] | None,
    shares: dict[tuple[str, str], float] | None,
) -> list[AllocationRecord]:
    cost_id = f"alloc-{uuid.uuid4().hex[:12]}"

    # Empty keys -> unallocated bucket
    if not keys:
        return [
            AllocationRecord(
                cost_id=cost_id,
                attribution_key=("scope", "unallocated"),
                share=1.0,
                allocated_cost=total_cost,
                method=method,
            )
        ]

    if method == "direct":
        # shares map: {key -> share}; only one key may have share > 0 in practice.
        if not shares:
            raise ValueError("direct method requires `shares` map keyed by full tuple")
        # Sum to 1.0 assumed; allocate total_cost * share[key]
        return [
            AllocationRecord(
                cost_id=cost_id,
                attribution_key=key,
                share=float(shares.get(key, 0.0)),
                allocated_cost=total_cost * float(shares.get(key, 0.0)),
                method=method,
            )
            for key in keys
        ]

    if method == "shared" or method == "equal_split":
        n = len(keys)
        share = 1.0 / n
        per = total_cost / n
        return [
            AllocationRecord(
                cost_id=cost_id,
                attribution_key=key,
                share=share,
                allocated_cost=per,
                method=method,
            )
            for key in keys
        ]

    if method in _WEIGHTED_METHODS:
        if not weights:
            raise ValueError(f"{method} method requires `weights` map keyed by key_value")
        per_value = {kv: float(weights.get(kv, 0.0)) for _, kv in keys}
        total_w = sum(per_value.values())
        if total_w == 0:
            # No weights at all -> even fallback so cost still allocated
            n = len(keys)
            share = 1.0 / n
            per = total_cost / n
            return [
                AllocationRecord(
                    cost_id=cost_id,
                    attribution_key=key,
                    share=share,
                    allocated_cost=per,
                    method=method,
                )
                for key in keys
            ]
        return [
            AllocationRecord(
                cost_id=cost_id,
                attribution_key=key,
                share=per_value[_key_value(key)] / total_w,
                allocated_cost=total_cost * per_value[_key_value(key)] / total_w,
                method=method,
            )
            for key in keys
        ]

    raise ValueError(f"unknown allocation method: {method!r}; expected one of {_METHODS}")


def allocate_cost(
    *,
    total_cost: float,
    attribution_keys: list[tuple[str, str]],
    method: str = "shared",
    weights: dict[str, float] | None = None,
    shares: dict[tuple[str, str], float] | None = None,
) -> list[AllocationRecord]:
    """Allocate `total_cost` across `attribution_keys` per `method`.

    Returns one AllocationRecord per input key (or a single unallocated bucket).
    """
    return _allocate(
        total_cost=total_cost,
        keys=list(attribution_keys),
        method=method,
        weights=weights,
        shares=shares,
    )
