"""Inspection mode resolver — delivery (default) vs CI (config + trigger words)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Literal

InspectionMode = Literal["delivery", "ci"]
EffectiveMode = Literal["delivery", "ci", "fallback"]
TriggerSource = Literal["cli", "keyword", "env", "default"]

DEFAULT_CI_KEYWORDS: tuple[str, ...] = (
    "ci模式",
    "无人值守",
    "定时巡检",
    "流水线巡检",
    "批量巡检",
    "自动巡检",
    "unattended",
    "#ci-inspection",
    "@ci-inspect",
    "nightly cruise",
    "cron巡检",
    "cron 巡检",
)


@dataclass(frozen=True)
class InspectionModeResult:
    mode: InspectionMode
    effective: EffectiveMode
    decision_maker: str
    trigger: TriggerSource
    matched_keyword: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_context(self) -> dict:
        return {
            "inspection_mode": self.mode,
            "inspection_effective": self.effective,
            "inspection_decision_maker": self.decision_maker,
            "inspection_trigger": self.trigger,
            "inspection_matched_keyword": self.matched_keyword,
            "inspection_warnings": list(self.warnings),
        }


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "")
    if not raw:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _normalize_keywords(extra: list[str] | None) -> list[str]:
    keywords = list(DEFAULT_CI_KEYWORDS)
    if extra:
        for item in extra:
            word = item.strip().lower()
            if word and word not in keywords:
                keywords.append(word)
    return keywords


def _match_ci_keyword(user_request: str, keywords: list[str]) -> str | None:
    text = user_request.lower()
    for keyword in sorted(keywords, key=len, reverse=True):
        if keyword in text:
            return keyword
    return None


def resolve_inspection_mode(
    user_request: str,
    *,
    cli_mode: str | None = None,
    env_mode: str | None = None,
    llm_enabled: bool | None = None,
    extra_keywords: list[str] | None = None,
) -> InspectionModeResult:
    """Resolve delivery vs CI per ADR D8 priority: CLI → keyword → env → default."""
    env_mode = (env_mode or os.environ.get("COPILOT_INSPECTION_MODE") or "auto").strip().lower()
    if llm_enabled is None:
        llm_enabled = _env_bool("COPILOT_LLM_REASONING", default=False)

    env_extra = os.environ.get("COPILOT_CI_TRIGGER_WORDS", "")
    if env_extra and extra_keywords is None:
        extra_keywords = [w.strip() for w in env_extra.split(",") if w.strip()]
    keywords = _normalize_keywords(extra_keywords)

    mode: InspectionMode = "delivery"
    trigger: TriggerSource = "default"
    matched: str | None = None
    warnings: list[str] = []

    if cli_mode:
        normalized = cli_mode.strip().lower()
        if normalized not in ("delivery", "ci"):
            msg = f"invalid --inspection-mode: {cli_mode!r}; using delivery"
            warnings.append(msg)
            mode = "delivery"
            trigger = "cli"
        else:
            mode = normalized  # type: ignore[assignment]
            trigger = "cli"
    elif env_mode == "delivery":
        mode = "delivery"
        trigger = "env"
    elif env_mode == "ci":
        mode = "ci"
        trigger = "env"
    else:
        matched = _match_ci_keyword(user_request, keywords)
        if matched:
            mode = "ci"
            trigger = "keyword"

    effective: EffectiveMode
    decision_maker: str
    if mode == "delivery":
        effective = "delivery"
        decision_maker = "agent_session_v1"
    elif llm_enabled:
        effective = "ci"
        decision_maker = "llm_reasoner_v1"
    else:
        effective = "fallback"
        decision_maker = "topology_reasoner_v1"
        warnings.append(
            "ci_requested_but_llm_disabled: COPILOT_LLM_REASONING=0; "
            "degraded to topology_reasoner_v1"
        )

    # CI strict gate: customer tag key must be explicitly set in CI mode.
    # Soft warning by default; future toggle can hard-fail.
    if effective == "ci" and not os.environ.get("COPILOT_CUSTOMER_TAG_KEY"):
        warnings.append(
            "ci_strict_gate: COPILOT_CUSTOMER_TAG_KEY not set; "
            "CI mode assumes '客户' default. Set it explicitly for audit clarity."
        )

    return InspectionModeResult(
        mode=mode,
        effective=effective,
        decision_maker=decision_maker,
        trigger=trigger,
        matched_keyword=matched,
        warnings=warnings,
    )


def strip_ci_trigger_words(user_request: str, matched_keyword: str | None) -> str:
    """Remove matched CI trigger token from request for cleaner customer parsing."""
    if not matched_keyword:
        return user_request
    pattern = re.compile(re.escape(matched_keyword), re.IGNORECASE)
    cleaned = pattern.sub(" ", user_request)
    return re.sub(r"\s+", " ", cleaned).strip()
