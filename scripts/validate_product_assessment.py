#!/usr/bin/env python3
"""Validate Worker Output Contract example JSON in well-architected-assessment.md files.

Usage:
  python3 scripts/validate_product_assessment.py [--root PATH]

Exit 0 if all examples pass; exit 1 on validation errors.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_TOP = {
    "skill_id",
    "product",
    "region",
    "scope",
    "assessment_date",
    "status",
    "partial",
    "resource_count",
    "pillars",
    "recommendations",
    "trace",
    "errors",
}
PILLARS = {"reliability", "security", "cost", "efficiency"}
PILLAR_PREFIX = {
    "rel": "reliability",
    "sec": "security",
    "cost": "cost",
    "eff": "efficiency",
}
FINDING_ID = re.compile(r"^([a-z0-9]+)-(rel|sec|cost|eff)-(\d{3})$")
STATUSES = {"OK", "PARTIAL", "ERROR"}
PILLAR_STATUS = {"assessed", "not_assessed", "skipped"}
SEVERITIES = {"Critical", "High", "Medium", "Low"}
CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}
EFFORT = {"quick", "medium", "major"}


def extract_example_jsons(text: str) -> list[tuple[int, dict]]:
    """Return (line_number, parsed_json) for each ```json block after 'Example'."""
    blocks: list[tuple[int, dict]] = []
    in_example = False
    for i, line in enumerate(text.splitlines(), start=1):
        if "Example" in line and "product_assessment" in line:
            in_example = True
        if in_example and line.strip().startswith("```json"):
            continue
        if in_example and line.strip() == "```":
            in_example = False
            continue
        if not in_example:
            continue
    # simpler: find all json blocks that look like product_assessment
    pattern = re.compile(r"```json\s*\n(\{.*?\})\n```", re.DOTALL)
    for m in pattern.finditer(text):
        raw = m.group(1)
        if '"product"' not in raw or '"pillars"' not in raw:
            continue
        try:
            blocks.append((text[: m.start()].count("\n") + 1, json.loads(raw)))
        except json.JSONDecodeError as e:
            blocks.append((text[: m.start()].count("\n") + 1, {"__parse_error__": str(e)}))
    return blocks


def validate_finding(product: str, pillar_key: str, finding: dict, path: str) -> list[str]:
    errs: list[str] = []
    fid = finding.get("id", "")
    m = FINDING_ID.match(fid)
    if not m:
        errs.append(f"{path}: finding id '{fid}' invalid (expected {{product}}-{{rel|sec|cost|eff}}-NNN)")
        return errs
    if m.group(1) != product:
        errs.append(f"{path}: finding id product prefix '{m.group(1)}' != top-level product '{product}'")
    expected_pillar = PILLAR_PREFIX[m.group(2)]
    if expected_pillar != pillar_key:
        errs.append(
            f"{path}: finding '{fid}' in pillars.{pillar_key} but id implies pillars.{expected_pillar}"
        )
    for field in ("severity", "confidence", "title", "evidence", "recommendation", "effort"):
        if field not in finding:
            errs.append(f"{path}: finding '{fid}' missing '{field}'")
    if finding.get("severity") not in SEVERITIES:
        errs.append(f"{path}: finding '{fid}' bad severity")
    if finding.get("confidence") not in CONFIDENCE:
        errs.append(f"{path}: finding '{fid}' bad confidence")
    if finding.get("effort") not in EFFORT:
        errs.append(f"{path}: finding '{fid}' bad effort")
    return errs


def validate_assessment(data: object, source: str) -> list[str]:
    errs: list[str] = []
    if not isinstance(data, dict):
        if isinstance(data, dict) and "__parse_error__" in data:
            return [f"{source}: JSON parse error: {data['__parse_error__']}"]
        return [f"{source}: not a JSON object"]
    if "__parse_error__" in data:
        return [f"{source}: JSON parse error: {data['__parse_error__']}"]

    missing = REQUIRED_TOP - set(data.keys())
    if missing:
        errs.append(f"{source}: missing top-level fields: {sorted(missing)}")

    if data.get("status") not in STATUSES:
        errs.append(f"{source}: invalid status '{data.get('status')}'")

    product = data.get("product")
    if not isinstance(product, str) or not product:
        errs.append(f"{source}: product must be non-empty string")

    pillars = data.get("pillars")
    if not isinstance(pillars, dict):
        errs.append(f"{source}: pillars must be object")
        return errs

    for pk, pv in pillars.items():
        if pk not in PILLARS:
            errs.append(f"{source}: unknown pillar key '{pk}'")
            continue
        if not isinstance(pv, dict):
            errs.append(f"{source}: pillars.{pk} must be object")
            continue
        st = pv.get("status")
        if st not in PILLAR_STATUS:
            errs.append(f"{source}: pillars.{pk}.status invalid '{st}'")
        findings = pv.get("findings", [])
        if not isinstance(findings, list):
            errs.append(f"{source}: pillars.{pk}.findings must be array")
            continue
        for fi, f in enumerate(findings):
            if isinstance(product, str):
                errs.extend(validate_finding(product, pk, f, f"{source} pillars.{pk}[{fi}]"))

    recs = data.get("recommendations", [])
    if isinstance(recs, list):
        for i, r in enumerate(recs):
            if not isinstance(r, dict):
                errs.append(f"{source}: recommendations[{i}] not object")
                continue
            if r.get("pillar") not in PILLARS:
                errs.append(f"{source}: recommendations[{i}].pillar invalid")

    trace = data.get("trace")
    if isinstance(trace, dict):
        cmds = trace.get("commands", [])
        if isinstance(cmds, list):
            for c in cmds:
                if isinstance(c, str) and "SecretKey=" in c and "<masked>" not in c:
                    errs.append(f"{source}: trace.commands contains unmasked SecretKey")

    # Worker Output Contract section required
    return errs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root: Path = args.root

    all_errs: list[str] = []
    files_checked = 0
    examples_checked = 0

    for md in sorted(root.glob("qcloud-*-ops/references/well-architected-assessment.md")):
        text = md.read_text(encoding="utf-8")
        files_checked += 1
        if "Worker Output Contract" not in text:
            all_errs.append(f"{md}: missing 'Worker Output Contract' section")
        examples = extract_example_jsons(text)
        if not examples:
            all_errs.append(f"{md}: no product_assessment JSON example found")
            continue
        for line_no, obj in examples:
            examples_checked += 1
            all_errs.extend(validate_assessment(obj, f"{md}:{line_no}"))

    if all_errs:
        print(f"FAIL: {len(all_errs)} error(s) in {files_checked} files ({examples_checked} examples)\n")
        for e in all_errs:
            print(f"  - {e}")
        return 1

    print(f"OK: {files_checked} files, {examples_checked} example JSON blocks validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
