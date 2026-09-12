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

# Docs ref drift: file:line refs and #fragment refs in markdown.
# These rot when source files change — see preflight-checklist.md §4
# and spec-drift-gate.md for why this is a real (not theoretical) drift.
_FILE_LINE_RE = re.compile(r'\bscripts/([a-zA-Z_-]+\.py):(\d+)(?:-\d+)?')
_MD_FRAGMENT_RE = re.compile(r'\]\((\.\.?/)([a-zA-Z_-]+\.md)#([a-zA-Z0-9-]+)\)')
_MD_LINK_RE = re.compile(r'\]\((\.\.?/)([a-zA-Z_-]+\.md)\)')


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


def _github_slug(heading: str) -> str:
    """GitHub-style markdown anchor slug (ASCII-simplified variant).

    The fragment refs in this repo's docs are pre-simplified — Unicode
    letters (e.g. Chinese characters), em-dashes, and other non-ASCII
    punctuation are dropped at link-author time rather than passed
    through GitHub's full unicode-aware slugger. This helper matches
    that convention so the two sides agree.

    Steps:
      1. lowercase
      2. strip every char that is not ASCII letter / digit / underscore /
         hyphen / space — drops parentheses, colons, em-dashes, Chinese
         chars, etc.
      3. collapse whitespace runs to '-'
      4. strip leading/trailing hyphens

    Leading numbers ARE preserved: `### 2. Source drift` becomes
    `2-source-drift` (matching the reference in
    runbooks/kpi2-destructive-token-plan-hash-failure.md). Earlier
    revisions stripped the leading `2.` and produced a false-positive
    drift on that known-good fragment.
    """
    s = heading.strip().lower()
    s = re.sub(r"[^a-z0-9_\- ]", "", s)  # drop non-ASCII-alphanumeric/hyphen/space
    s = re.sub(r"\s+", "-", s)            # whitespace runs -> '-'
    s = s.strip("-")                      # trim leading/trailing '-'
    return s


def check_md_fragment_refs(docs_root: Path) -> list[dict]:
    """Detect broken `.md#fragment` cross-doc links.

    Scans every `*.md` under `docs_root` for links of the form
    `[label](./path.md#fragment)` or `[label](../path.md#fragment)`.
    For each, resolves the relative path and computes GitHub-style
    heading slugs from the target md's h2/h3 headings. Reports two
    drift classes:

    1. **target md missing** — referenced md file does not exist.
    2. **fragment unresolved** — md exists but no heading slug matches.

    Known-good fragments already in use (Sep 2026):
    #the-8-attributes, #2-source-drift, #case-study-scoring-...
    """
    items = []
    if not docs_root.exists():
        return items
    for md in docs_root.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue
        md_dir = md.parent
        try:
            md_rel = str(md.relative_to(ROOT))
        except ValueError:
            md_rel = str(md)
        for m in _MD_FRAGMENT_RE.finditer(text):
            rel_prefix = m.group(1)
            target_md_name = m.group(2)
            fragment = m.group(3)
            target = (md_dir / rel_prefix / target_md_name).resolve()
            if not target.exists():
                items.append({
                    "kind": "md_fragment_drift",
                    "doc_file": md_rel,
                    "target": f"{rel_prefix}{target_md_name}#{fragment}",
                    "note": "target md missing",
                })
                continue
            try:
                target_text = target.read_text(encoding="utf-8")
            except OSError:
                continue
            slugs = set()
            for h in re.finditer(r"^(#{2,3})\s+(.+?)\s*$", target_text, re.MULTILINE):
                slugs.add(_github_slug(h.group(2)))
            if fragment not in slugs:
                items.append({
                    "kind": "md_fragment_drift",
                    "doc_file": md_rel,
                    "target": f"{rel_prefix}{target_md_name}#{fragment}",
                    "note": f"fragment '#{fragment}' does not resolve to any heading",
                })
    return items


def check_docs_file_line_refs(docs_root: Path) -> list[dict]:
    """Detect docs/code drift from `scripts/<name>.py:<N>` refs in markdown.

    Scans every `*.md` under `docs_root` recursively, extracts refs that
    look like `scripts/validate_x.py:64` (or `scripts/validate_x.py:64-70`),
    and reports two drift classes:

    1. **script file missing** — referenced script not present under
       `scripts/`. Usually means a renamed/deleted file the docs forgot
       to update.
    2. **line empty or past EOF** — script exists but line N is blank
       (whitespace only) or the file is shorter than N. Usually means
       the code at that line moved or was removed.

    The regex `_FILE_LINE_RE` requires the file path to start with
    `scripts/`, so plain prose like "see runbook #42" is not flagged.
    Only `.md` files inside `docs_root` are inspected — pass a
    different Path to widen the scope (e.g. ROOT/'docs').

    Returns an empty list when every ref resolves to a non-empty line
    in an existing file. No side effects; safe to call repeatedly.
    """
    items = []
    if not docs_root.exists():
        return items
    for md in docs_root.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue
        md_rel = md.relative_to(ROOT)
        for m in _FILE_LINE_RE.finditer(text):
            script = m.group(1)
            line = int(m.group(2))
            target = SCRIPTS_DIR / script
            if not target.exists():
                items.append({
                    "kind": "file_line_ref_drift",
                    "script": script,
                    "line": line,
                    "doc_file": str(md_rel),
                    "note": "script file missing",
                })
                continue
            try:
                lines = target.read_text(encoding="utf-8").splitlines()
            except OSError:
                items.append({
                    "kind": "file_line_ref_drift",
                    "script": script,
                    "line": line,
                    "doc_file": str(md_rel),
                    "note": f"line {line} is empty or past EOF in {script}",
                })
                continue
            if line > len(lines) or not lines[line - 1].strip():
                items.append({
                    "kind": "file_line_ref_drift",
                    "script": script,
                    "line": line,
                    "doc_file": str(md_rel),
                    "note": f"line {line} is empty or past EOF in {script}",
                })
    return items


def check_readme_phantom_links(readme_path: Path, docs_root: Path) -> list[dict]:
    """Detect phantom README table links: Ready rows pointing to missing .md.

    Scans `readme_path` for markdown table rows whose Status column contains
    "✅ Ready", extracts the first `./<name>.md` link on the row using
    `_MD_LINK_RE`, and reports any link whose target does not exist on
    disk relative to `readme_path.parent`.

    Rows marked "⏳ Pending" are skipped: per `preflight-checklist.md` §5,
    Pending rows are legitimate placeholders for patterns still in flight
    and must not be flagged. The same row pattern with a missing target
    is therefore expected behaviour, not drift.

    `docs_root` is part of the signature for parity with the other
    `check_docs_*` helpers; the current implementation resolves each link
    against `readme_path.parent` (which is always inside `docs_root`),
    so `docs_root` itself is unused. Keeping it in the signature keeps
    the call sites uniform and lets a future caller pass a different
    anchor (e.g. for multi-readme scans) without changing the function
    shape.

    Returns an empty list when every ✅ Ready link resolves. No side
    effects; safe to call repeatedly.
    """
    items = []
    if not readme_path.exists():
        return items
    try:
        text = readme_path.read_text(encoding="utf-8")
    except OSError:
        return items
    base = readme_path.parent
    readme_rel = readme_path.resolve().relative_to(ROOT.resolve())
    for line in text.splitlines():
        # Filter to ✅ Ready table rows only. ⏳ Pending rows are
        # explicitly out of scope (see preflight-checklist.md §5).
        if "✅ Ready" not in line:
            continue
        m = _MD_LINK_RE.search(line)
        if not m:
            continue
        target_name = m.group(2)
        target = base / target_name
        if not target.exists():
            items.append({
                "kind": "phantom_link_drift",
                "readme": str(readme_rel),
                "link_target": target_name,
                "note": "Ready row points to missing .md file",
            })
    return items


def main() -> int:
    threshold = check_threshold_drift()
    source = check_source_drift()
    docs_refs = check_docs_file_line_refs(ROOT / "docs")  # widened to match md_fragments scope
    readme_refs = check_readme_phantom_links(
        ROOT / "docs" / "harness-engineering" / "README.md",
        ROOT / "docs" / "harness-engineering",
    )
    md_fragments = check_md_fragment_refs(ROOT / "docs")
    items = threshold + source + docs_refs + readme_refs + md_fragments

    if not items:
        print("| Drift class | Status | Detail |")
        print("|---|---|---|")
        print("| Threshold drift        | \u2705 pass | all spec thresholds have matching code literals |")
        print("| Source drift           | \u2705 pass | all schema required fields written by emit_evidence_record |")
        print("| File-line ref drift    | \u2705 pass | all `scripts/*.py:N` refs in docs resolve to non-empty lines |")
        print("| MD fragment drift      | \u2705 pass | all `.md#fragment` cross-refs resolve to a heading |")
        print("| Phantom README link    | \u2705 pass | all ✅ Ready rows in README resolve to existing .md files |")
        print("\nSPEC DRIFT: clean")
        return 0

    print("| Drift class | Field/Value | File | Note |")
    print("|---|---|---|---|")
    for it in items:
        if it["kind"] == "threshold_drift":
            print(f"| threshold_drift | {it['spec_value']} | `{it['spec_file']}` | {it['note']} |")
        elif it["kind"] == "source_drift":
            print(f"| source_drift | `{it['schema_field']}` | docs/evidence-kernel-schema.json | {it['note']} |")
        elif it["kind"] == "phantom_link_drift":
            print(f"| phantom_link_drift | `{it['link_target']}` | `{it['readme']}` | {it['note']} |")
        elif it["kind"] == "md_fragment_drift":
            # `target` carries the relative path + fragment, e.g.
            # "../spec-drift-gate.md#2-source-drift".
            print(f"| md_fragment_drift | `{it['target']}` | `{it['doc_file']}` | {it['note']} |")
        elif it["kind"] == "file_line_ref_drift":
            print(f"| file_line_ref_drift | {it['script']}:{it['line']} | `{it['doc_file']}` | {it['note']} |")
        else:
            print(f"| UNKNOWN drift kind | {it} |")

    AUDIT.mkdir(exist_ok=True)
    (AUDIT / "spec-drift-report.json").write_text(
        json.dumps({"items": items, "count": len(items)}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nSPEC DRIFT: {len(items)} item(s) — see audit-results/spec-drift-report.json")
    return 1


if __name__ == "__main__":
    sys.exit(main())
