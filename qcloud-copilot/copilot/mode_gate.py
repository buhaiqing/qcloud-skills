"""Mode gating + region auto-discovery producer for delivery mode (BC-T4).

Called by ``plan_gen.generate()`` before the per-intent builder runs. Three
hard rules determine whether region auto-discovery fires:

  1. CI / fallback mode → return None (CI never probes, no ask_user overhead)
  2. step.region already explicit → return None (user knows where to look)
  3. context already has region from prior ask_user round → return None

ponytail: the dispatcher ALSO rejects ask_user in CI (defense in depth — see
``copilot.dispatcher``), so even if the planner forgets to call this gate,
CI never blocks. This module's job is to **produce** region candidates so the
cruise planner can insert ``ask-region-0`` ahead of ``cruise-1``.
"""

from __future__ import annotations

from typing import Any

from copilot.region_scanner import (
    RegionCandidate,
    discover_across_regions,
)


def _build_tccli_client() -> Any:
    """Lazy import TccliClient — avoids forcing scripts/ path manipulation on copilot-only callers."""
    try:
        from lib.tccli_client import TccliClient  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover — copilot without cruise lib
        raise RuntimeError(
            "TccliClient unavailable; install qcloud-proactive-inspection or run from "
            "scripts/ context with sys.path including qcloud-proactive-inspection/scripts"
        ) from exc
    return TccliClient()


def _coerce_to_candidates(raw: Any) -> list[RegionCandidate]:
    """Accept list[RegionCandidate] or list[dict] (e.g. from session memory)."""
    out: list[RegionCandidate] = []
    for item in raw or []:
        if isinstance(item, RegionCandidate):
            out.append(item)
            continue
        if isinstance(item, dict) and item.get("region"):
            out.append(
                RegionCandidate(
                    region=item["region"],
                    customer_resources_count=int(item.get("customer_resources_count", 0)),
                    resource_types=dict(item.get("resource_types") or {}),
                    vpc_ids=list(item.get("vpc_ids") or []),
                )
            )
    return out


def maybe_discover_regions(
    *,
    intent: Any,
    customer: str,
    region: str,
    context: dict,
    mode_result: Any,
    client_factory: Any | None = None,
    scanner: Any = discover_across_regions,
) -> list[RegionCandidate] | None:
    """Return candidate regions for delivery mode, or None to skip.

    Args:
        intent: ClassifiedIntent — discovery only fires for cruise-like intents
            (CRUISE / INSPECT). Other intents don't benefit from region picks.
        customer: customer slug to scan for.
        region: region already in context/params (if any).
        context: plan context (may already carry region_candidates from a prior round).
        mode_result: InspectionModeResult; uses .effective in {delivery, ci, fallback}.
        client_factory: optional callable returning a cloud client; defaults to a Tencent-compatible client.
        scanner: discover_across_regions function (overridable for tests).

    Returns:
        list[RegionCandidate] when discovery ran; None when skipped.
        Empty list is a valid result (no regions matched) — caller must
        distinguish None (skipped) from [] (ran but found nothing).
    """
    # Hard rule 1: CI / fallback never probes
    if mode_result.effective in ("ci", "fallback"):
        return None
    # Hard rule 2: explicit region — user knows where to look
    if region:
        return None
    # Hard rule 3: prior round already picked
    if context.get("region"):
        return None
    # Only cruise-shaped intents benefit from region ambiguity resolution.
    primary = getattr(intent, "primary", None)
    if primary not in ("cruise", "inspect"):
        return None
    # Allow upstream (planner/session memory) to pre-populate; don't re-scan.
    if context.get("region_candidates"):
        return _coerce_to_candidates(context["region_candidates"])

    if not customer:
        return None

    # When the caller supplies a custom scanner (tests / mocks) the scanner
        # owns its client; otherwise we lazily build a real client.
    if client_factory is not None or scanner is not discover_across_regions:
        factory = client_factory or (lambda: None)
    else:
        factory = _build_tccli_client
    return scanner(factory(), customer)
