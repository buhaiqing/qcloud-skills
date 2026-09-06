#!/usr/bin/env python3
"""
analyze_spec_blockers.py — P0-2
Precisely categorize spec_file_refs_missing suggestions from GCL traces.
Distinguish: actual spec file refs vs other uses of spec/file/ref/missing keywords.
Exit 0 = analysis complete.
"""
import glob
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

AUDIT_DIR = Path(__file__).resolve().parent.parent / "audit-results"
TRACER_PATTERN = "gcl-trace-*.json"


def classify_suggestion(s: str) -> str:
    """Return precise bucket for suggestion string."""
    low = s.lower()
    # 1. Actual spec file references (real spec_file_refs_missing)
    #    e.g. "refs/xxx not found", "spec file ... does not exist"
    spec_ref_re = re.compile(
        r"`(refs/[^`]+|references/[^`]+|docs/superpowers/[^`]+)`", re.IGNORECASE,
    )
    file_not_found_re = re.compile(
        r"(spec|file|path|reference).*(not found|does not exist|cannot find)",
        re.IGNORECASE,
    )
    if spec_ref_re.search(s):
        return "spec_file_ref"
    if file_not_found_re.search(s):
        return "file_not_found"
    # 2. Traceability — missing RequestId/trace fields
    if ("requestid" in low or "trace" in low) and "missing" in low:
        return "traceability"
    # 3. Idempotency — missing ClientToken
    if "clienttoken" in low and "missing" in low:
        return "idempotency"
    # 4. Missing field/data/param (not the above)
    if "missing" in low and any(k in low for k in ["field", "data", "value", "param", "argument"]):
        return "missing_field_data"
    # 5. Schema / yaml drift
    if any(k in low for k in ["schema", "yaml", "drift"]):
        return "yaml_schema_drift"
    # 6. Other "spec" uses (not file ref)
    if "spec" in low:
        return "other_spec"
    # 7. Other "file" uses
    if "file" in low:
        return "other_file"
    # 8. Other "ref" uses
    if "ref" in low:
        return "other_ref"
    return "other"


def main():
    files = sorted(glob.glob(str(AUDIT_DIR / TRACER_PATTERN)))
    gcl_files = []
    for f in files:
        try:
            with open(f) as fh:
                t = json.load(fh)
            if "iterations" in t:
                gcl_files.append(f)
        except (json.JSONDecodeError, OSError):
            pass

    print(f"Found {len(gcl_files)} GCL trace files")

    all_suggestions: list[tuple[str, str, str]] = []  # (suggestion, skill, filename)

    for fpath in gcl_files:
        with open(fpath) as fh:
            trace = json.load(fh)
        skill = trace.get("skill", "unknown")
        for it_idx, it in enumerate(trace.get("iterations", [])):
            for sugg in it.get("critic", {}).get("suggestions", []):
                all_suggestions.append((sugg, skill, fpath))

    total = len(all_suggestions)
    print(f"Total suggestions collected: {total}")

    # Filter to spec_file_refs_missing bucket per original aggregator logic
    original_bucket: list[tuple[str, str, str]] = []
    for sugg, skill, fpath in all_suggestions:
        low = sugg.lower()
        if any(k in low for k in ["spec", "file", "ref", "missing"]):
            original_bucket.append((sugg, skill, fpath))

    print(f"\nOriginal aggregator bucket (spec/file/ref/missing): {len(original_bucket)}")

    # Classify each
    precise_counter = Counter()
    skill_breakdown: dict[str, Counter] = defaultdict(Counter)
    for sugg, skill, fpath in original_bucket:
        bucket = classify_suggestion(sugg)
        precise_counter[bucket] += 1
        skill_breakdown[bucket][skill] += 1

    print("\n=== Precise Bucket Distribution ===")
    for bucket, cnt in precise_counter.most_common():
        print(f"  {bucket}: {cnt}")

    print("\n=== Top-5 Exact Suggestion Strings (deduped) ===")
    sugg_counter = Counter(orig for orig, _, _ in original_bucket)
    for sugg, cnt in sugg_counter.most_common(5):
        bucket = classify_suggestion(sugg)
        print(f"  [{cnt:3d}x] [{bucket}] {sugg[:120]}")

    print("\n=== Skill Breakdown for spec_file_ref ===")
    if "spec_file_ref" in skill_breakdown:
        for skill, cnt in skill_breakdown["spec_file_ref"].most_common(10):
            print(f"  {skill}: {cnt}")

    # Count true spec_file_ref proportion
    true_spec = precise_counter["spec_file_ref"] + precise_counter.get("file_not_found", 0)
    pct = true_spec / len(original_bucket) * 100 if original_bucket else 0
    print(f"\nTrue 'spec/file ref missing' proportion: {pct:.1f}% ({true_spec}/{len(original_bucket)})")
    print(f"  → {precise_counter['traceability']} are traceability issues")
    print(f"  → {precise_counter['idempotency']} are idempotency issues")
    print(f"  → {precise_counter['other']} are truly other/other_spec/other_file/other_ref")

    # Save detailed output
    report = {
        "original_bucket_size": len(original_bucket),
        "precise_distribution": dict(precise_counter),
        "top_suggestions": dict(sugg_counter.most_common(20)),
    }
    report_path = AUDIT_DIR / "spec_blocker_analysis.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nDetailed report saved to {report_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
