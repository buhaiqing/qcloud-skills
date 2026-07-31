"""P1.6 / P1.7 — Identity resolution across CLI, config, env, session, automation, fallback.

Priority (highest first):
  1. CLI overrides         (e.g. --user-id / --tenant-id flags)
  2. Config dict           (project config / .env / apollo)
  3. Environment variables (QCLOUD_USER_ID, QCLOUD_TENANT_ID, ...)
  4. Session hint          (resume previous run from session_id)
  5. Automation hint       (cron / job / agent_id)
  6. Fallback              (all None; identity_source = "fallback")
"""
from __future__ import annotations

from typing import Any

from copilot.trace_records import IdentityTree

# Fixed env-var key map (kept narrow to avoid leaking unrelated env into identity).
ENV_KEY_MAP: dict[str, str] = {
    "QCLOUD_USER_ID": "user_id",
    "QCLOUD_TENANT_ID": "tenant_id",
    "QCLOUD_CUSTOMER_ID": "customer_id",
    "QCLOUD_OPERATOR_ID": "operator_id",
    "QCLOUD_SERVICE_ACCOUNT_ID": "service_account_id",
    "QCLOUD_ACCOUNT_ID_HASH": "account_id_hash",
    "QCLOUD_ACTOR_TYPE": "actor_type",
}

# IdentityTree fields the resolver will populate.
_IDENTITY_FIELDS = (
    "user_id",
    "tenant_id",
    "customer_id",
    "operator_id",
    "service_account_id",
    "account_id_hash",
    "actor_type",
)

# Allowed actor/initiator values per SPEC §16; unknown values fall back to None.
ALLOWED_ACTOR_TYPES = {"cli", "ci", "automation", "agent", "service_account", "human", "unknown"}
ALLOWED_INITIATOR_TYPES = {"cli", "ci", "session", "automation", "agent"}


class IdentityResolver:
    """Resolve `IdentityTree` from layered sources with deterministic priority."""

    def __init__(
        self,
        cli_overrides: dict[str, Any] | None = None,
        config_dict: dict[str, Any] | None = None,
        env: dict[str, str] | None = None,
        session_hint: dict[str, Any] | None = None,
        automation_hint: dict[str, Any] | None = None,
    ) -> None:
        self.cli_overrides = cli_overrides or {}
        self.config_dict = config_dict or {}
        self.env = env if env is not None else dict(__import__("os").environ)
        self.session_hint = session_hint or {}
        self.automation_hint = automation_hint or {}

    def _value_for(self, field_name: str) -> tuple[str | None, str | None]:
        """Return (value, source) for a field; source is one of cli/config/env/session/automation/fallback."""
        # CLI
        v = self.cli_overrides.get(field_name)
        if v:
            return (v, "cli")
        # Config
        v = self.config_dict.get(field_name)
        if v:
            return (v, "config")
        # Env (only mapped keys)
        env_field = next((k for k, f in ENV_KEY_MAP.items() if f == field_name), None)
        if env_field and self.env.get(env_field):
            return (self.env[env_field], "env")
        # Session
        v = self.session_hint.get(field_name)
        if v:
            return (v, "session")
        # Automation
        v = self.automation_hint.get(field_name)
        if v:
            return (v, "automation")
        return (None, None)

    def resolve(self) -> IdentityTree:
        """Produce an `IdentityTree` with priority-based fields and source tags."""
        resolved: dict[str, Any] = {}
        sources_used: list[str] = []
        for f in _IDENTITY_FIELDS:
            value, source = self._value_for(f)
            if value and source:
                resolved[f] = value
                if source not in sources_used:
                    sources_used.append(source)

        # initiator_type: derived from actor_type or CLI presence
        initiator_type = self.cli_overrides.get("initiator_type") or (
            "cli" if "cli" in sources_used else None
        )
        if initiator_type and initiator_type not in ALLOWED_INITIATOR_TYPES:
            initiator_type = None

        # identity_source: highest-priority source observed (cli > config > env > session > automation > fallback)
        priority_order = ("cli", "config", "env", "session", "automation")
        identity_source = next((s for s in priority_order if s in sources_used), "fallback")

        # confidence: declared for CLI, configured for config/env, historical for session/automation, unknown fallback
        confidence_map = {
            "cli": "declared",
            "config": "configured",
            "env": "configured",
            "session": "historical",
            "automation": "historical",
            "fallback": "unknown",
        }
        confidence = confidence_map[identity_source]

        return IdentityTree(
            **{k: v for k, v in resolved.items() if k in IdentityTree.__dataclass_fields__},
            actor_type=resolved.get("actor_type") if resolved.get("actor_type") in ALLOWED_ACTOR_TYPES else None,
            initiator_type=initiator_type,
            identity_source=identity_source,
            identity_confidence=confidence,
        )
