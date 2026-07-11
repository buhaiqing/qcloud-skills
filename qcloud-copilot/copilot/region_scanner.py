"""Parallel region scanner for delivery-mode customer discovery (BC-T2).

Discovers which Tencent Cloud regions hold resources for a given customer (tagged)
by calling `discover_customer_resources` per region in parallel. Single-region
failures are isolated — one region's API rate-limit / auth error must not
abort scanning the rest.

ponytail:
  - max_workers default 4 (matches ALL_REGIONS length; raising this is the
    upgrade path when rate-limit token bucket lands).
  - Sort key: (-len(resource_types), -customer_resources_count, region asc)
    → most "diverse" candidates float up; ties broken by count then region.
  - Zero-hit regions are dropped (no candidate emitted).
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

# Lazy import: resource_discovery requires network/cloud SDK wiring
# capability — keep the import inside functions so unit tests can mock.
_DEFAULT_TAG_KEY = "客户"

# Built-in default fallback (mirrors qcloud-proactive-inspection ALL_REGIONS).
# When the proactive-inspection lib is importable we prefer its value (single source of
# truth); otherwise we ship the same default here so copilot runs standalone.
_BUILTIN_ALL_REGIONS = ("ap-guangzhou", "cn-east-2", "cn-south-1", "cn-east-1")


@dataclass(frozen=True)
class RegionCandidate:
    """One region that holds resources for the customer.

    Attributes:
        region: Tencent Cloud region id (e.g. 'ap-guangzhou').
        customer_resources_count: total tagged resources in this region.
        resource_types: per-type counts (e.g. {'vms': 12, 'lbs': 2}).
        vpc_ids: distinct VPC ids where the customer's resources live.
    """

    region: str
    customer_resources_count: int
    resource_types: dict[str, int] = field(default_factory=dict)
    vpc_ids: list[str] = field(default_factory=list)


def _resolve_scan_regions() -> list[str]:
    """Resolve the list of regions to scan.

    Priority: env COPILOT_SCAN_REGIONS (comma-separated) → fallback to the
    proactive-inspection library's ALL_REGIONS (if importable) → built-in default.
    """
    env = os.environ.get("COPILOT_SCAN_REGIONS", "").strip()
    if env:
        return [r.strip() for r in env.split(",") if r.strip()]
    try:
        from lib.resource_discovery import ALL_REGIONS  # type: ignore[import-not-found]

        return list(ALL_REGIONS)
    except ImportError:
        return list(_BUILTIN_ALL_REGIONS)


def _scan_region(
    client: object,
    customer: str,
    region: str,
    customer_tag_key: str | None,
) -> RegionCandidate | None:
    """Scan a single region for customer resources.

    Returns None when:
      - discovery returned zero customer resources, OR
      - any exception escaped the per-region call (rate-limit / auth / network).
    """
    try:
        from lib.resource_discovery import (  # type: ignore[import-not-found]
            discover_customer_resources,
        )
    except ImportError:
        # Copilot environment without proactive-inspection sys.path: caller must set
        # COPILOT_SCAN_REGIONS or supply regions explicitly. We surface as
        # "no resources" rather than crash, matching the isolation contract.
        return None

    try:
        data = discover_customer_resources(
            client,
            customer,
            regions=[region],
            customer_tag_key=customer_tag_key,
        )
    except Exception:
        return None

    raw = data.get("raw") or {}
    by_type: dict[str, int] = {k: len(v) for k, v in raw.items() if isinstance(v, list)}
    total = sum(by_type.values())
    if total == 0:
        return None

    # Distinct VPC ids from tagged resources; vpcId is the conventional field
        # name used by the Tencent Cloud SDK for VPC-scoped resources (cvm/clb/redis/cdb).
    vpc_ids: set[str] = set()
    for items in raw.values():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            vpc_id = item.get("vpcId")
            if isinstance(vpc_id, str) and vpc_id:
                vpc_ids.add(vpc_id)

    return RegionCandidate(
        region=region,
        customer_resources_count=total,
        resource_types=by_type,
        vpc_ids=sorted(vpc_ids),
    )


def discover_across_regions(
    client: object,
    customer: str,
    regions: list[str] | None = None,
    *,
    max_workers: int = 4,
    customer_tag_key: str | None = None,
) -> list[RegionCandidate]:
    """Discover customer resources across multiple regions in parallel.

    Args:
        client: cloud-client-compatible instance (must expose list_vms/lbs/etc.).
        customer: customer tag value (e.g. '朔州天源').
        regions: explicit region list; None → env COPILOT_SCAN_REGIONS → ALL_REGIONS.
        max_workers: thread pool size; capped to len(regions) automatically.
        customer_tag_key: override the default tag key (default: '客户').

    Returns:
        Sorted list of RegionCandidate (zero-hit regions omitted).
        Sort key: (-len(resource_types), -customer_resources_count, region).
    """
    target_regions = regions if regions is not None else _resolve_scan_regions()
    if not target_regions:
        return []

    candidates: list[RegionCandidate] = []
    workers = min(max_workers, len(target_regions))
    tag_key = customer_tag_key or _DEFAULT_TAG_KEY

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_region = {
            pool.submit(_scan_region, client, customer, region, tag_key): region
            for region in target_regions
        }
        for future in as_completed(future_to_region):
            try:
                result = future.result()
            except Exception:
                # Belt-and-suspenders: _scan_region already swallows internally,
                # but if anything escapes (e.g. test doubles that bypass the
                # inner try), still isolate that region from the result set.
                continue
            if result is not None:
                candidates.append(result)

    candidates.sort(key=lambda c: (-len(c.resource_types), -c.customer_resources_count, c.region))
    return candidates
