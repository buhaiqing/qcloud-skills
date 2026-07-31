"""P5.1 — security / observability hygiene helpers.

  - scan_text_for_secrets(text) -> [{pattern, offset, excerpt}, ...]
  - hash_resource_id(id, salt=...) -> stable hex digest
  - check_low_cardinality_labels(labels) -> [{key, reason}, ...] flagged when
    label key is recognized as unbounded (e.g. trace_id, user_email).

Pure functions. Never mutate input or echo the raw secret bytes.
"""
from __future__ import annotations

import hashlib
import re

# ---------------------------------------------------------------------------
# Secret scan patterns (compiled once)
# ---------------------------------------------------------------------------

_TENCENT_AK_RE = re.compile(r"\bAKID[A-Za-z0-9]{16,}\b")
_AWS_AK_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9_\-]{20,}")
_API_PARAM_RE = re.compile(
    r"(?:api_key|access_token|secret_key)=([A-Za-z0-9_\-]{16,})",
    re.IGNORECASE,
)

_SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("tencent_ak", _TENCENT_AK_RE),
    ("aws_access_key", _AWS_AK_RE),
    ("bearer", _BEARER_RE),
    ("api_param", _API_PARAM_RE),
]


def _redact(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return value[:3] + "..." + value[-3:]


def scan_text_for_secrets(text: str) -> list[dict]:
    findings: list[dict] = []
    if not text:
        return findings
    for name, pattern in _SECRET_PATTERNS:
        for match in pattern.finditer(text):
            raw = match.group(0)
            findings.append({
                "pattern": name,
                "offset": match.start(),
                "excerpt": _redact(raw),
            })
    return findings


# ---------------------------------------------------------------------------
# Resource ID hashing
# ---------------------------------------------------------------------------


def hash_resource_id(resource_id: str, salt: str = "qcloud-copilot:v1") -> str:
    if resource_id is None:
        resource_id = ""
    digest = hashlib.sha256(f"{salt}::{resource_id}".encode()).hexdigest()[:16]
    return f"sha256:{digest}"


# ---------------------------------------------------------------------------
# Low-cardinality prom label audit
# ---------------------------------------------------------------------------

_BOUNDED_KEYS = frozenset({
    "skill", "operation", "status", "decision", "region",
    "product", "service", "stage", "kind", "method",
    "outcome", "level",
})

_UNBOUNDED_KEYS = frozenset({
    "trace_id", "span_id", "observation_id",
    "user_email", "user_id", "instance_id",
    "request_id", "session_id", "tenant_id", "incident_id",
    "run_id", "ip", "host", "path",
})

_MAX_ALLOWED_BUCKETS = 100


def check_low_cardinality_labels(labels: dict[str, str]) -> list[dict]:
    issues: list[dict] = []
    if not labels:
        return issues
    for key in labels:
        if key in _BOUNDED_KEYS:
            continue
        if key in _UNBOUNDED_KEYS:
            issues.append({
                "key": key,
                "reason": f"{key!r} is a high-cardinality label.",
            })
            continue
    if len(labels) > _MAX_ALLOWED_BUCKETS:
        for k in labels:
            if k in _BOUNDED_KEYS or k in _UNBOUNDED_KEYS:
                continue
            issues.append({
                "key": k,
                "reason": f"{k!r} label map exceeds {_MAX_ALLOWED_BUCKETS} entries; verify cardinality budget.",
            })
    return issues
