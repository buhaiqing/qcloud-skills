#!/usr/bin/env python3
"""Evidence Kernel: PreFlight gate + PostRecord persistence.

Stdlib-only. Every skill run emits one EvidenceRecord (validated by
validate_evidence_schema.py). This module provides:
  - preflight(): gate before execution (destructive op requires a token)
  - post_record(): persist an EvidenceRecord under audit-results/
  - plan_hash() / is_destructive() / mask_trace(): helpers
"""
from __future__ import annotations

import functools
import hashlib
import json
import re
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit-results"
AUDIT.mkdir(exist_ok=True)

# The value is usually separated from the key by quotes, colons, `=` or spaces
# (`--secretKey abc`, `"secretKey": "abc"`); requiring it to be concatenated
# meant those forms were never redacted.
SENSITIVE_KEY_RE = re.compile(
    r'((?:AKID|secretId|secretKey)["\s:=]*)([A-Za-z0-9_\-]{8,})', re.IGNORECASE
)
SECRET_VAL_RE = re.compile(r"(TENCENTCLOUD_SECRET_KEY=)[A-Za-z0-9_-]+")

# Canonical destructive-verb set AND matching rule live in harness_safety
# (Phase 3 owner); reuse both so the two detection paths can never drift.
from harness_safety import VERBS as DESTRUCTIVE_VERBS  # noqa: F401  re-export for callers
from harness_safety import is_destructive as _harness_is_destructive


def plan_hash(plan_text: str) -> str:
    return hashlib.sha256(plan_text.encode()).hexdigest()[:16]


def is_destructive(plan_text: str) -> bool:
    return _harness_is_destructive(plan_text)


def preflight(plan_text: str, human_token: str | None) -> dict:
    destructive = is_destructive(plan_text)
    decision = {"destructive": destructive, "allowed": True, "reason": ""}
    if destructive and not human_token:
        decision["allowed"] = False
        decision["reason"] = "destructive op requires human-issued confirmation token"
    return decision


def mask_trace(trace: dict) -> dict:
    """Redact obvious secret patterns (KPI#1). Returns a sanitized copy."""
    text = json.dumps(trace, ensure_ascii=False)
    text = SENSITIVE_KEY_RE.sub(r"\1<masked>", text)
    text = SECRET_VAL_RE.sub(r"\1<masked>", text)
    return json.loads(text)


def post_record(record: dict, span_id: str | None = None) -> Path:
    """Persist an EvidenceRecord under audit-results/.

    ``span_id`` is the Phase 1.4 cross-system join key: when supplied it is
    recorded in the Evidence JSON so downstream queries can walk from a
    destructive-op audit back to the TraceSpan that caused it. Optional for
    backward compatibility with existing callers that don't pass it.
    """
    if span_id is not None:
        record = {**record, "span_id": span_id}
    out = AUDIT / f"evidence-{record['run_id']}.json"
    out.write_text(json.dumps(mask_trace(record), indent=2, ensure_ascii=False))
    return out


def with_timeout(fn, seconds: float):
    """Run an in-process generator fn; raise TimeoutError if it exceeds seconds.

    For GCL subprocess workers use run_command(timeout=...) in gcl_runner.py;
    this helper covers in-process generator functions.
    """
    @functools.wraps(fn)
    def _wrapped():
        result: dict = {}
        def _run():
            try:
                result["v"] = fn()
            except (ImportError, OSError, ValueError, KeyError, AttributeError, TypeError) as e:
                result["exc"] = e
        t = threading.Thread(target=_run)
        t.start()
        t.join(seconds)
        if t.is_alive():
            raise TimeoutError(f"exceeded {seconds}s")
        if "exc" in result:
            raise result["exc"]
        return result.get("v")
    return _wrapped()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(plan_hash(Path(sys.argv[1]).read_text()))
