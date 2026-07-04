# Task for delegate

GENERATOR TASK: Fix ALL identified problems in the CVM skill.

Repo: /Users/bohaiqing/opensource/git/qcloud-skills

First, read the following context files:
1. qcloud-cvm-ops/SKILL.md (970 lines) - full file
2. qcloud-skill-generator/references/qcloud-skill-template.md - template
3. docs/gcl-spec.md - GCL spec
4. AGENTS.md - repo rules

Then apply these fixes:

## Fix 1: Create references/sdk-templates.md
Create a file with reusable SDK boilerplate:
- Common initialization (cred, client for CVM and CBS)
- Polling helper
- Common try-except wrappers

## Fix 2: Replace RunInstances SDK block with reference
Current: ~35 lines of full script with imports, cred, try-except
Replace with: 2-line reference comment + just the request-building code

## Fix 3: Replace DescribeInstances SDK block with reference
Current: ~20 lines of full script
Replace with: 2-line reference + just the request code

## Fix 4: Merge Prerequisites into Quick Start
Read both sections carefully. They overlap (both have Cloud Shell, Local CLI, SDK setup).
- Add Cloud Shell Limitations from Prerequisites into Quick Start
- Add Quick Environment Check into Quick Start
- Delete the Prerequisites section (lines 747-820) entirely

## Fix 5: Delete Variables section at end
Remove the duplicate Variables section (around lines 978-985)

## Fix 6: Add ModifyInstanceSpec operation
After ModifyInstanceAttribute section, add a new section:
  - Pre-flight: check instance exists, check current spec, verify target is different
  - CLI: tccli cvm ModifyInstanceSpec --InstanceId --InstanceType
  - SDK: short reference to sdk-templates.md
  - Validation: poll DescribeInstances for new InstanceType
  - Error recovery table

## Fix 7: Add AttachDisks operation
After CreateImage section, add:
  - Pre-flight: check instance RUNNING, disk ATTACHED state
  - CLI: tccli cbs AttachDisks --InstanceId --DiskIds
  - SDK: reference sdk-templates.md (CBS client)
  - Validation
  - Error recovery

## Fix 8: Add DetachDisk operation
After AttachDisks:
  - Pre-flight: warn service interruption, check disk attached to right instance
  - CLI: tccli cbs DetachDisk --InstanceId --DiskId
  - SDK: reference sdk-templates.md
  - Validation
  - Error recovery

## Fix 9: Update Capabilities table
Add rows for ModifyInstanceSpec, AttachDisks, DetachDisk

## Fix 10: Bump version to 1.3.0
Update version field in frontmatter (line 13: version: "1.2.0" -> "1.3.0")
Update last_updated to 2026-07-04
Add changelog entry for 1.3.0

## Constraints
- DO NOT change any existing API calls, CLI commands, parameter values, error codes, safety gates, or the Quality Gate section
- DO NOT change frontmatter name, compatibility, or metadata fields except version and last_updated
- All SDK code must use tencentcloud-sdk-python-cvm (not generic tencentcloud-sdk-python)
- All references use relative paths from SKILL.md location

## Verification checklist
1. sdk-templates.md exists with common init, polling, try-except
2. RunInstances SDK block is now ~15 lines (not ~35)
3. DescribeInstances SDK block is now ~8 lines (not ~20)
4. Prerequisites section is completely removed (no orphan headings)
5. Variables section at end is completely removed
6. ModifyInstanceSpec adds ~40 lines in proper format
7. AttachDisks adds ~30 lines in proper format
8. DetachDisk adds ~30 lines in proper format
9. Capabilities table has 3 new rows
10. version is 1.3.0, changelog has new entry, last_updated is today
11. Total line count reduction: roughly -50 lines

## Acceptance Contract
Acceptance level: checked
Completion is not accepted from prose alone. End with a structured acceptance report.

Criteria:
- criterion-1: Implement the requested change without widening scope

Required evidence: changed-files, tests-added, commands-run, residual-risks, no-staged-files

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