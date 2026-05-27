# Governance and Adversarial Review

Reviewer companion for Tencent Cloud skill generation quality assurance.

---

## Overview

Adversarial review catches issues before merge:
- Destructive-action shortcuts
- Credential leaks in instructions
- API hallucination
- Missing safety gates

---

## Charter (宪章)

**§0 Charter**: Every generated skill MUST pass Charter Compliance Checklist (C1-C6) before merge.

---

## Review Categories

### R1: Security Review

| Check | Risk | How to Review |
|-------|------|---------------|
| Credential exposure | HIGH | Search for SecretKey value printing |
| Missing credential masking | HIGH | Verify all credential outputs use `<masked>` |
| Unsafe CLI patterns | MEDIUM | Check for inline credentials in CLI commands |
| Missing CAM documentation | MEDIUM | Verify CAM policy section exists |

### R2: API Fidelity Review

| Check | Risk | How to Review |
|-------|------|---------------|
| Invented API methods | HIGH | Compare against official API spec |
| Wrong parameter names | HIGH | Cross-reference with API documentation |
| Incorrect JSON paths | MEDIUM | Validate response field names |
| Missing required parameters | HIGH | Verify required vs optional distinction |

### R3: Safety Gate Review

| Check | Risk | How to Review |
|-------|------|---------------|
| Missing delete confirmation | HIGH | Verify confirmation step before delete |
| Missing pre-backup reminder | MEDIUM | Check for backup suggestion |
| Missing rollback plan | MEDIUM | Verify rollback steps documented |
| Missing timeout specification | LOW | Check polling timeouts defined |

### R4: UX Review

| Check | Risk | How to Review |
|-------|------|---------------|
| Missing Quick Start | MEDIUM | Verify Quick Start section exists |
| Overly complex instructions | MEDIUM | Check for excessive prompts |
| Missing error format | MEDIUM | Verify error messages follow format |
| Unclear output format | LOW | Verify output schema documented |

---

## Adversarial Scenarios

### Scenario 1: Credential Exposure Attack

**Scenario**: Agent accidentally prints `TENCENTCLOUD_SECRET_KEY` in debug output.

**Test Steps**:
1. Search SKILL.md and references for patterns: `echo $TENCENTCLOUD_SECRET_KEY`, `print(secret_key)`
2. Check error handling section for credential exposure
3. Verify masking examples are correct

**Expected Result**: No credential value exposure in any output path.

**Severity**: HIGH — Blocking issue if found.

---

### Scenario 2: Destructive Shortcut Attack

**Scenario**: Agent skips confirmation step to "optimize" delete operation.

**Test Steps**:
1. Locate Delete operation section
2. Verify confirmation step is MANDATORY (not optional)
3. Check for explicit "MUST confirm" language

**Expected Result**: Every destructive operation has confirmation step.

**Severity**: HIGH — Blocking issue if missing.

---

### Scenario 3: API Hallucination Attack

**Scenario**: Agent invents a non-existent API method to fill a gap.

**Test Steps**:
1. Extract all API method names from skill
2. Cross-reference with official API documentation
3. Verify each method exists and is correctly named

**Expected Result**: All API methods match official documentation.

**Severity**: HIGH — Blocking issue if any invented.

---

### Scenario 4: Missing Dependency Attack

**Scenario**: Skill assumes prerequisite skill exists but doesn't document.

**Test Steps**:
1. Check Trigger & Scope for delegation rules
2. Verify prerequisite skills are listed
3. Check for implicit skill dependencies

**Expected Result**: All dependencies documented in Delegation Rules.

**Severity**: MEDIUM — Must document before merge.

---

### Scenario 5: Over-Broad Trigger Attack

**Scenario**: Skill description is too broad and triggers incorrectly.

**Test Steps**:
1. Review description field in frontmatter
2. Check against eval_queries.json
3. Identify potential false positives

**Expected Result**: Description focuses on specific triggers, excludes unrelated.

**Severity**: MEDIUM — Adjust description if too broad.

---

### Scenario 6: Token Efficiency Violations (C6)

**Scenario**: Generated skill contains unnecessarily verbose content — redundant docstrings, bloated tables, duplicated flows, or hardcoded static data that wastes LLM context.

**Test Steps**:
1. Check for TE-1 violations: hardcoded static data (engine versions, ports, zones) — verify with `tccli help <product>` or API Describe[Version] calls
2. Check for TE-2 violations: Python `"""docstring"""` on every function in SDK code blocks — should use `#` line comments instead
3. Check for TE-3 violations: error tables with > 3 columns — compact to `Error Code | Description | Recovery`
4. Check for TE-4 violations: JSON paths repeated inline instead of centralized declaration
5. Check for TE-5 violations: YAML configs with duplicate anchor-eligible fields
6. Check for TE-6 violations: Pre-flight → Execute → Validate → Recover flow duplicated across SKILL.md and reference files
7. Check for TE-7 violations: tables with redundant Description columns that merely restate the field name

**Expected Result**: All TE rules applied per [Token Efficiency Requirements](../../SKILL.md#token-efficiency-requirements-p0).

**Severity**: MEDIUM — Optimize before merge. Blocking for context-heavy files (>2000 tokens).

---

## Review Protocol

### Pre-Merge Review Steps

```markdown
1. **Automated Charter Check**:
   - Run C1-C6 checklist via grep commands
   - All MUST pass
   
2. **Security Review (R1)**:
   - Manual review for credential exposure
   - Check all output paths
   
3. **API Review (R2)**:
   - Cross-reference with API spec
   - Verify all methods
   
4. **Safety Review (R3)**:
   - Check destructive operations
   - Verify safety gates
   
5. **UX Review (R4)**:
   - Quick Start verification
   - Error format check
   
6. **Adversarial Scenarios**:
   - Run all 6 scenarios
   - All MUST pass or be addressed
```

---

## Review Checklist Summary

| Category | Items | Severity |
|----------|-------|----------|
| Charter (C1-C6) | 6 checks | Blocking |
| Security (R1) | 4 checks | Blocking for HIGH |
| API Fidelity (R2) | 4 checks | Blocking for HIGH |
| Safety (R3) | 4 checks | Blocking for missing confirmation |
| UX (R4) | 4 checks | Non-blocking |
| Adversarial | 6 scenarios | Blocking for HIGH |

---

## Review Output Template

```markdown
## Governance Review Report

**Skill**: qcloud-[product]-ops
**Version**: [version]
**Reviewer**: [name]
**Date**: [date]

### Charter Compliance

| Check | Status | Notes |
|-------|--------|-------|
| C1 Frontmatter | ✓/✗ | [notes] |
| C2 SHOULD/SHOULD NOT | ✓/✗ | [notes] |
| C3 Five Standards | ✓/✗ | [notes] |
| C4 Well-Architected | ✓/✗ | [notes] |
| C5 Variables | ✓/✗ | [notes] |
| C6 Token Efficiency | ✓/✗ | [notes] |

### Security Review (R1)

| Check | Status | Risk |
|-------|--------|------|
| Credential exposure | ✓ | HIGH |
| Credential masking | ✓ | HIGH |
| CLI patterns | ✓ | MEDIUM |
| CAM documentation | ✓ | MEDIUM |

### API Fidelity (R2)

| Check | Status | Notes |
|-------|--------|-------|
| Methods exist | ✓ | All verified against [spec URL] |
| Parameters correct | ✓ | Cross-referenced |
| JSON paths correct | ✓ | Verified |
| Required/optional | ✓ | Documented |

### Safety Gates (R3)

| Operation | Confirmation | Backup Reminder | Status |
|-----------|--------------|-----------------|--------|
| Delete | ✓ | ✓ | Pass |
| Modify | ✓ | ✓ | Pass |
| Terminate | ✓ | ✓ | Pass |

### Adversarial Scenarios

| Scenario | Status | Notes |
|----------|--------|-------|
| Credential Exposure | ✓ | No exposure found |
| Destructive Shortcut | ✓ | All have confirmation |
| API Hallucination | ✓ | All methods verified |
| Missing Dependency | ✓ | Delegation documented |
| Over-Broad Trigger | ✓ | Description specific |
| Token Efficiency | ✓ | TE-1~TE-7 rules applied |

### Overall Assessment

**Result**: [PASS/FAIL/CONDITIONAL PASS]

**Blocking Issues**: [list or "None"]

**Recommendations**: [list or "None"]

**Merge Decision**: [Approved/Rejected/Needs Revision]
```

---

## Integration with Generation Workflow

Step 6 of generation workflow MUST include governance review:

```markdown
### Step 6: Verify & Review

Run the P0/P1 Checklist against the generated skill.
Run the Adversarial Review scenarios.

**For any failure:**
1. Identify the gap
2. Return to Step 4 or Step 5
3. Fix the gap
4. Re-verify the full checklist
5. Re-run adversarial scenarios
```

---

## References

- [Tencent Cloud API Documentation](https://cloud.tencent.com/document/api)
- [CAM Best Practices](https://cloud.tencent.com/document/product/598)
- [Well-Architected Assessment](well-architected-assessment.md)