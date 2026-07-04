# Task for delegate

CRITIC TASK: Review the changes made to qcloud-cvm-ops SKILL.md for security issues.

Read the changed files at:
- /Users/bohaiqing/opensource/git/qcloud-skills/qcloud-cvm-ops/SKILL.md
- /Users/bohaiqing/opensource/git/qcloud-skills/qcloud-cvm-ops/references/sdk-templates.md

Check:
1. No credential exposure - no SecretKey printed in any output
2. New operations have proper safety gates (warnings, confirmation)
3. All destructive operations require explicit confirmation
4. The DetachDisk operation warns about service interruption
5. No API names were invented - ModifyInstanceSpec, AttachDisks, DetachDisk are real APIs

Return structured JSON.

---
Previous step output:
All validations pass. Here's the structured acceptance report.

## Acceptance Contract
Acceptance level: reviewed
Completion is not accepted from prose alone. End with a structured acceptance report.

Criteria:
- criterion-1: Implement the requested change without widening scope
- criterion-2: Return evidence sufficient for an independent acceptance review

Required evidence: changed-files, tests-added, commands-run, validation-output, residual-risks, no-staged-files

Review gate: required by reviewer.

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