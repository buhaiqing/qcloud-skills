#!/usr/bin/env python3
"""Evidence Kernel: PreFlight gate + PostRecord persistence.

Stdlib-only. Every skill run emits one EvidenceRecord (validated by
validate_evidence_schema.py). This module provides:
  - preflight(): gate before execution (destructive op requires a token)
  - post_record(): persist an EvidenceRecord under audit-results/
  - plan_hash() / is_destructive() / mask_trace(): helpers
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit-results"
AUDIT.mkdir(exist_ok=True)

DESTRUCTIVE_VERBS = {"delete", "terminate", "destroy", "drop", "reset", "remove", "stop"}


def plan_hash(plan_text: str) -> str:
    return hashlib.sha256(plan_text.encode()).hexdigest()[:16]


def is_destructive(plan_text: str) -> bool:
    return any(v in plan_text.lower().split() for v in DESTRUCTIVE_VERBS)


def preflight(plan_text: str, human_token: str | None) -> dict:
    destructive = is_destructive(plan_text)
    decision = {"destructive": destructive, "allowed": True, "reason": ""}
    if destructive and not human_token:
        decision["allowed"] = False
        decision["reason"] = "destructive op requires human-issued confirmation token"
    return decision


def mask_trace(trace: dict) -> dict:
    text = json.dumps(trace, ensure_ascii=False)
    text = re.sub(r"(AKID|secretId|secretKey)[\w]*[\"'= :]+[\w-]+", "<masked>", text)
    text = re.sub(r"TENCENTCLOUD_SECRET_KEY=[\w-]+", "TENCENTCLOUD_SECRET_KEY=<masked>", text)
    return json.loads(text)


def post_record(record: dict) -> Path:
    out = AUDIT / f"evidence-{record['run_id']}.json"
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(plan_hash(Path(sys.argv[1]).read_text()))
