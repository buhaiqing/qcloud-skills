"""P5.2 — tenant isolation + sensitive field redactor.
"""
from __future__ import annotations

from typing import Iterable

from copilot.security import scan_text_for_secrets


REDACTED = "REDACTED"


def enforce_tenant_isolation(records: Iterable, *, current_tenant_id: str) -> list[dict]:
    issues: list[dict] = []
    if not current_tenant_id:
        return issues
    for rec in records:
        identity = getattr(rec, "identity", None)
        tenant = getattr(identity, "tenant_id", None) if identity else None
        if tenant and tenant != current_tenant_id:
            issues.append({
                "record_id": getattr(rec, "id", "?"),
                "record_tenant": tenant,
                "current_tenant": current_tenant_id,
                "reason": "cross-tenant access blocked",
            })
    return issues


_SENSITIVE_KEYS = {
    "password",
    "passwd",
    "pwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "authorization",
    "auth",
    "secret_key",
    "secret_id",
    "private_key",
}


def _is_sensitive_key(key: str) -> bool:
    """Case-insensitive whole-token match against _SENSITIVE_KEYS.

    Word-boundary semantics: 'api_key' matches (segments api, key),
    'secret_question' does NOT because 'secret' alone is fine but
    'secret_question' is not exactly in the set and no single segment equals
    'secret' (segments: secret, question; 'secret' is in set so this is
    why we treat it as match). We narrow: only match when a segment AT
    THE START OR END matches, OR the whole key matches.
    """
    if not isinstance(key, str):
        return False
    lower = key.lower()
    if lower in _SENSITIVE_KEYS:
        return True
    segments = lower.replace("-", "_").split("_")
    if not segments:
        return False
    # Anchor: only flag when the FIRST or LAST segment is the sensitive token,
    # or when the key is exactly 2 segments, both of which are sensitive.
    if segments[0] in _SENSITIVE_KEYS:
        return True
    if segments[-1] in _SENSITIVE_KEYS:
        return True
    if len(segments) == 2 and all(seg in _SENSITIVE_KEYS for seg in segments):
        return True
    return False


def redact_sensitive_fields(payload):
    """Return a copy of `payload` with sensitive values replaced by REDACTED."""
    if isinstance(payload, dict):
        out: dict = {}
        for k, v in payload.items():
            if _is_sensitive_key(k):
                out[k] = REDACTED
            elif isinstance(v, dict):
                out[k] = redact_sensitive_fields(v)
            elif isinstance(v, list):
                out[k] = [redact_sensitive_fields(item) for item in v]
            else:
                out[k] = v
        return out
    if isinstance(payload, list):
        return [redact_sensitive_fields(item) for item in payload]
    return payload


def assert_no_secrets_on_disk(text: str) -> None:
    findings = scan_text_for_secrets(text)
    if findings:
        keys = sorted({f["pattern"] for f in findings})
        raise AssertionError(
            f"on-disk payload contains secrets: {', '.join(keys)} (N={len(findings)})"
        )
