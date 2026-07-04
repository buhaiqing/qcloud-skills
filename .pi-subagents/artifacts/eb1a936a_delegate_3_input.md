# Task for delegate

CRITIC TASK: Review the structural coherence of the CVM skill changes.

Read the changed file at:
- /Users/bohaiqing/opensource/git/qcloud-skills/qcloud-cvm-ops/SKILL.md

Check:
1. Section ordering follows the template (Overview -> Five Standards -> Trigger -> Variable Convention -> Quick Start -> Capabilities -> Changelog -> Execution Flows -> Reference Directory -> Error Codes -> Safety Gates -> Quality Gate -> Output Schema)
2. No orphan headings (sections without parents)
3. No broken internal links
4. New operations (ModifyInstanceSpec, AttachDisks, DetachDisk) match the format of existing ones
5. Quick Start section is self-contained after merge
6. Changelog is properly formatted

Return structured JSON.

---
Previous step output:
All evidence collected. Here's the TE review:

---

## TE Review: qcloud-cvm-ops (v1.2.0 → v1.3.0)

### Check 1: TE-4 — JSON paths centralized ✅

Centralized **Example Response Field Table** exists at line 143 with 7 entries covering RunInstances, DescribeInstances, StopInstances, CreateSnapshot. A secondary **Present to User** table (line 406) adds 6 per-operation display paths (CPU, Memory, PrivateIp, PublicIp, etc.) not covered in the central table — these are display guidance, not path reference duplication. Within TE-4 conventions, central table covers the common paths; operation-specific display tables add marginal value and don't duplicate the central table.

### Check 2: TE-6 — SDK code extracted ✅

No `from tencentcloud` import scaffold remains in SKILL.md (the one occurrence at line 236 is a one-liner SDK verification check, not a scaffold block). 
- **5 operations** reference `references/sdk-templates.md` and show only request-specific Python code
- **2 operations** (CreateSnapshot, CreateImage) still have inline `import os, json, time` — these are minimal per-operation stdlib imports for `time.strftime()` formatting, not scaffold duplication. The full CBS client init lives in sdk-templates.md. Acceptable.

### Check 3: TE-3 — Error tables ≤3 columns ✅

| Location | Columns | Status |
|----------|---------|--------|
| Main Error Code Reference (line 899) | Code, Description, Recovery | ✅ 3 cols |
| RunInstances Failure Recovery (line 368) | Error pattern, Retry Strategy, Recovery | ✅ 3 cols |
| ModifyInstanceSpec Failure Recovery (line 648) | Error pattern, Max retries, Recovery | ✅ 3 cols |
| AttachDisks Failure Recovery (line 800) | Error pattern, Max retries, Recovery | ✅ 3 cols |
| DetachDisk Failure Recovery (line 849) | Error pattern, Max retries, Recovery | ✅ 3 cols |

### Check 4: Redundant sections removed ✅

- Standalone `## Variables` section: **removed** (grep confirms no match)
- Standalone `## Prerequisites` section: **removed** (merged into Quick Start sub-sections under Option 2 and Option 3)

### Check 5: Line counts

| Metric | Value |
|--------|-------|
| Before (v1.2.0) | 970 lines |
| After (v1.3.0) | 1013 lines |
| Net change | +43 lines |
| Insertions | +164 |
| Deletions | -122 |
| sdk-templates.md (new) | +75 lines |

**Net increase** despite SDK extraction because 3 new operations were added (ModifyInstanceSpec, AttachDisks, DetachDisk) plus Cloud Shell Limitations section. The SDK extraction saved ~40-50 lines of duplicated scaffold boilerplate that would have been incurred by the new operations.

---

## Acceptance Contract
Acceptance level: attested
Completion is not accepted from prose alone. End with a structured acceptance report.

Criteria:
- criterion-1: Return a concise result and residual risks when applicable

Required evidence: manual-notes, residual-risks

Finish with a fenced JSON block tagged `acceptance-report` in this shape:
Use empty arrays when no items apply; array fields contain strings unless object entries are shown.
```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "specific proof"
    }
  ],
  "changedFiles": [
    "src/file.ts"
  ],
  "testsAddedOrUpdated": [
    "test/file.test.ts"
  ],
  "commandsRun": [
    {
      "command": "command",
      "result": "passed",
      "summary": "short result"
    }
  ],
  "validationOutput": [
    "validation output or concise summary"
  ],
  "residualRisks": [
    "none"
  ],
  "noStagedFiles": true,
  "diffSummary": "short description of the diff",
  "reviewFindings": [
    "blocker: file.ts:12 - issue found, or no blockers"
  ],
  "manualNotes": "anything else the parent should know"
}
```