# Task for delegate

CRITIC TASK: Review the changes to qcloud-cvm-ops for token efficiency.

Read the changed files at:
- /Users/bohaiqing/opensource/git/qcloud-skills/qcloud-cvm-ops/SKILL.md
- /Users/bohaiqing/opensource/git/qcloud-skills/qcloud-cvm-ops/references/sdk-templates.md

Check:
1. TE-4: JSON paths are centralized (verify the table still exists)
2. TE-6: SDK code is extracted to references/sdk-templates.md and NOT duplicated inline in any operation
3. TE-3: Error tables have at most 3 columns
4. No redundant sections remain (Prerequisites and Variables should be gone)
5. Line reduction estimate: before=970, after=?

Return structured JSON.

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