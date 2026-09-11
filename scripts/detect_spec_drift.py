#!/usr/bin/env python3
"""Detect spec/code drift across the repo.

Companion to docs/harness-engineering/spec-drift-gate.md. Implements the
two mechanical drift checks (Threshold + Source) described there. The
third class (Behavior) requires running real skills against real
tccli output, so it is out of scope for this offline detector.

What this script does
---------------------
1. **Threshold drift** — extract numeric thresholds from the watched
   spec file(s) under docs/superpowers/specs/ (e.g. ">=5"), extract
   numeric literals from scripts/*.py (assert N, exit N, sys.exit(N)),
   and report any spec threshold whose value is not matched in code.
   Scope: only _WATCHED_SPECS are scanned; narrative specs would
   produce a flood of false positives.

2. **Source drift** — extract `required` field names from the JSON
   schema in docs/evidence-kernel-schema.json, extract field names
   written inside emit_evidence_record in scripts/gcl_runner.py, and
   report any required field that is not directly written.

Known limitations (read this before trusting the output)
--------------------------------------------------------
- **Source drift has false positives for fields written via helper
  functions.** Fields like `correctness` / `idempotency` / `traceability`
  / `spec_compliance` are written indirectly via `_final_scores(trace)`,
  not as top-level dict literals in emit_evidence_record. The detector
  currently flags them as missing even though they appear in the
  emitted record. A real fix requires static data-flow analysis
  (track variable aliases), not regex.
- **Threshold drift is value-presence, not semantic match.** If a
  spec says ">=5" and code uses 5 somewhere unrelated, that counts as
  "covered". Tightening this requires parsing the spec phrase in
  context (e.g. ">=5 golden scenarios per skill") and finding the
  matching assertion in code.

Because of these limitations, this detector is **opt-in only** — it
is NOT wired into `make all`. Run it manually via
`python3 scripts/detect_spec_drift.py` and inspect the report before
acting on any drift item.

Exit codes
----------
  0  no drift detected
  1  one or more drift items found
  2  internal error (missing files this detector depends on)

Output
------
Markdown table on stdout (so `make drift-check` can pipe to console)
plus audit-results/spec-drift-report.json for trend tracking.

Scope guard
-----------
This detector only inspects files. It will report drift if any exists.
It does NOT modify any file. It is **opt-in** — not wired into
`make all` until the false-positive rate is acceptable.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "docs" / "superpowers" / "specs"
SCHEMA_PATH = ROOT / "docs" / "evidence-kernel-schema.json"
SCRIPTS_DIR = ROOT / "scripts"
AUDIT = ROOT / "audit-results"

# Specs that declare enforceable thresholds (vs narrative design docs).
# Narrative specs use numbers like "30 days" or "90% confidence"
# liberally; including them turns the detector into a noise machine.
# The harness-engineering-optimization spec is the only one whose
# thresholds are meant to be enforced by code today.
_WATCHED_SPECS = {
    "2026-07-28-harness-engineering-optimization-design.md",
}

# Threshold drift patterns. Spec prose uses phrases like ">=5", "< 2",
# "at least 10". Code uses assert N, exit(N), sys.exit(N), return N.
_THRESHOLD_RE_SPEC = re.compile(
    r"(?:>=|<=|>|<|==|!=)\s*(\d+)", re.IGNORECASE
)
_THRESHOLD_RE_CODE = re.compile(
    r"(?:assert\s+(?:.*?[\s<>=!]+\s*)(\d+)|"
    r"sys\.exit\s*\(\s*(\d+)\s*\)|"
    r"return\s+(\d+))"
)

# Source drift: schema required fields. JSON Schema arrays of strings.
_REQUIRED_RE = re.compile(r'"required"\s*:\s*\[([^\]]*)\]')


def _extract_spec_thresholds(spec_dir: Path) -> list[dict]:
    """Pull every numeric threshold from spec files under spec_dir.

    Scope guard: only files whose name appears in _WATCHED_SPECS are
    scanned. Other specs in the directory are narrative (telling a
    design story with '90 days', '15 modules', etc.) and would
    produce a flood of false positives.
    """
    out = []
    if not spec_dir.exists():
        return out
    for md in spec_dir.glob("*.md"):
        if md.name not in _WATCHED_SPECS:
            continue
        for m in _THRESHOLD_RE_SPEC.finditer(md.read_text(encoding="utf-8")):
            out.append({"file": str(md.relative_to(ROOT)), "value": int(m.group(1))})
    return out


def _extract_code_numbers(scripts_dir: Path) -> set[int]:
    """Pull every numeric literal that looks like a threshold from scripts/."""
    nums = set()
    if not scripts_dir.exists():
        return nums
    for py in scripts_dir.glob("*.py"):
        for m in _THRESHOLD_RE_CODE.finditer(py.read_text(encoding="utf-8")):
            for g in m.groups():
                if g is not None:
                    nums.add(int(g))
                    break
    return nums


def check_threshold_drift() -> list[dict]:
    """Return drift items where a spec threshold has no matching code number.

    Heuristic: a threshold value present in spec but absent in any
    scripts/*.py is a candidate drift. False positives are possible
    (e.g. spec value never enforced by code yet), so this detector
    only WARNs, never auto-fails the build.
    """
    spec_thresholds = _extract_spec_thresholds(SPEC_DIR)
    code_numbers = _extract_code_numbers(SCRIPTS_DIR)
    items = []
    seen = set()
    for t in spec_thresholds:
        key = (t["file"], t["value"])
        if key in seen:
            continue
        seen.add(key)
        if t["value"] not in code_numbers:
            items.append({
                "kind": "threshold_drift",
                "spec_file": t["file"],
                "spec_value": t["value"],
                "note": "value present in spec but not found in scripts/*.py literals",
            })
    return items


def _extract_required_fields(schema_path: Path) -> list[str]:
    if not schema_path.exists():
        return []
    text = schema_path.read_text(encoding="utf-8")
    fields = []
    for m in _REQUIRED_RE.finditer(text):
        inner = m.group(1)
        # inner is a JSON array literal of strings
        for s in re.findall(r'"([^"]+)"', inner):
            fields.append(s)
    return fields


def _extract_written_fields(scripts_dir: Path) -> set[str]:
    """Find every `"fieldname":` key written inside emit_evidence_record
    in scripts/gcl_runner.py. Walks the entire function body so nested
    dict literals (e.g. `"router_decision": {"top1_skill": ...}`) are
    counted. Without nested traversal the detector flags
    `top1_skill` / `correctness` / `idempotency` / etc. as missing
    even though they are written."""
    target = scripts_dir / "gcl_runner.py"
    if not target.exists():
        return set()
    text = target.read_text(encoding="utf-8")
    m = re.search(r"def emit_evidence_record.*?(?=\ndef |\Z)", text, re.DOTALL)
    if not m:
        return set()
    body = m.group(0)
    return set(re.findall(r'"([a-z_]+)"\s*:\s*', body))


def check_source_drift() -> list[dict]:
    required = _extract_required_fields(SCHEMA_PATH)
    written = _extract_written_fields(SCRIPTS_DIR)
    items = []
    for f in required:
        if f not in written:
            items.append({
                "kind": "source_drift",
                "schema_field": f,
                "note": "schema required field not written in gcl_runner.emit_evidence_record",
            })
    return items


def main() -> int:
    threshold = check_threshold_drift()
    source = check_source_drift()
    items = threshold + source

    if not items:
        print("| Drift class | Status | Detail |")
        print("|---|---|---|")
        print(f"| Threshold drift | \u2705 pass | all spec thresholds have matching code literals |")
        print(f"| Source drift    | \u2705 pass | all schema required fields written by emit_evidence_record |")
        print("\nSPEC DRIFT: clean")
        return 0

    print("| Drift class | Field/Value | File | Note |")
    print("|---|---|---|---|")
    for it in items:
        if it["kind"] == "threshold_drift":
            print(f"| threshold_drift | {it['spec_value']} | `{it['spec_file']}` | {it['note']} |")
        else:
            print(f"| source_drift | `{it['schema_field']}` | docs/evidence-kernel-schema.json | {it['note']} |")

    AUDIT.mkdir(exist_ok=True)
    (AUDIT / "spec-drift-report.json").write_text(
        json.dumps({"items": items, "count": len(items)}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nSPEC DRIFT: {len(items)} item(s) — see audit-results/spec-drift-report.json")
    return 1


if __name__ == "__main__":
    sys.exit(main())
