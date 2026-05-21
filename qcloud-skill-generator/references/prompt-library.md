# Prompt Library

Structured prompts for Tencent Cloud skill generation lifecycle.

---

## Overview

This library provides reusable prompts for each phase of skill generation, ensuring consistent output quality.

---

## Phase 1: Analysis Prompts

### P1.1: Product Research Prompt

```markdown
**Context**: Researching Tencent Cloud [Product Name] for skill generation.

**Objective**: Extract comprehensive product information including:
- API methods and operations
- Resource types and relationships
- Error codes and handling
- CLI coverage

**Deliverable**: Analysis document with verified data from official sources.

**Prompt Template**:

You are analyzing Tencent Cloud [Product Name] to generate an operational skill.

Sources to consult:
1. Official API documentation: [URL]
2. CLI documentation: tccli help [product]
3. Product overview: [URL]

Extract and document:
1. **Operations**: List all API methods with descriptions
2. **Parameters**: Required vs optional for each operation
3. **Responses**: JSON structure and field names
4. **Errors**: Product-specific error codes (minimum 10)
5. **CLI Coverage**: Which operations tccli supports
6. **Relationships**: Dependencies on other products

Output format: Markdown table for each category.

Verification requirement: Every field MUST be traceable to official documentation.
```

### P1.2: Error Taxonomy Prompt

```markdown
**Context**: Building error taxonomy for [Product Name].

**Objective**: Extract product-specific error codes with recovery actions.

**Prompt Template**:

You are building an error taxonomy for Tencent Cloud [Product Name].

Sources:
- API error documentation: [URL]
- Common error patterns

Extract errors in this format:

| Code | Meaning | Retry? | Agent Action | UX Feedback |
|------|---------|--------|--------------|-------------|
| [Code] | [Meaning] | [Yes/No] | [Action] | `[ERROR] ... → fix → next step` |

Requirements:
- Minimum 10 product-specific errors
- Clear retry vs HALT distinction
- Actionable UX feedback for each

Output: Error code table with recovery strategies.
```

---

## Phase 2: Generation Prompts

### P2.1: Frontmatter Generation Prompt

```markdown
**Context**: Generating frontmatter for qcloud-[product]-ops skill.

**Objective**: Create compliant frontmatter following agentskills.io spec.

**Prompt Template**:

Generate frontmatter for qcloud-[product]-ops skill:

Parameters:
- Product name: [Name]
- CLI slug: [slug]
- Chinese name: [中文名]
- API profile: [version/doc link]
- CLI applicability: [cli-first/dual-path/sdk-only/cli-only]

Requirements:
1. name: `qcloud-[product]-ops` (lowercase, hyphenated)
2. description: Imperative phrasing, < 1024 chars, focus on triggers
3. license: MIT
4. compatibility: List CLI, SDK, runtime requirements
5. metadata: Include all required fields

Output format:

```yaml
---
name: qcloud-[product]-ops
description: >-
  Use when the user needs to [trigger description]...
license: MIT
compatibility: >-
  [CLI and SDK requirements]
metadata:
  [all required metadata fields]
---
```

Verify: description < 1024 chars, triggers specific.
```

### P2.2: Trigger & Scope Prompt

```markdown
**Context**: Defining triggers and scope for [Product Name].

**Objective**: Clear SHOULD/SHOULD NOT conditions with delegation rules.

**Prompt Template**:

Define Trigger & Scope for qcloud-[product]-ops:

Product info:
- Primary resource: [Resource Type]
- Operations: [list]
- Related products: [dependencies]

Generate:

### SHOULD Use This Skill When
- [5-8 specific trigger conditions]
- [Keywords to match]
- [Product aliases]

### SHOULD NOT Use This Skill When
- [3-5 negative conditions]
- [Delegate to which skill]

### Delegation Rules
- [Cross-product dependency rules]

Requirements:
- Triggers specific and actionable
- Negative conditions prevent misfires
- Delegation explicitly names target skills

Output: Trigger & Scope section in Markdown.
```

---

## Phase 3: Validation Prompts

### P3.1: Charter Check Prompt

```markdown
**Context**: Verifying Charter compliance for generated skill.

**Objective**: Execute C1-C5 checks and report results.

**Prompt Template**:

Execute Charter Compliance Check for qcloud-[product]-ops:

Checks:
C1: Frontmatter (grep -c "^---")
C2: SHOULD/SHOULD NOT (grep -c "SHOULD Use")
C3: Five Standards (grep -c "Five Core Standards")
C4: Well-Architected (grep -c "Well-Architected")
C5: Variables (grep -c "{{env.*}}")

For each check:
- Run command
- Report pass/fail
- If fail, note what's missing

Output format:

| Check | Command | Result | Pass/Fail | Action Needed |
|-------|---------|--------|-----------|---------------|
| C1 | [cmd] | [result] | ✓/✗ | [action] |

Overall: [PASS if all ✓, otherwise FIX recommendations]
```

### P3.2: API Fidelity Prompt

```markdown
**Context**: Verifying API methods match official documentation.

**Objective**: Cross-reference all API references in skill.

**Prompt Template**:

Verify API fidelity for qcloud-[product]-ops:

Source skill: [path]
Official API: [URL]

Steps:
1. Extract all API method names from skill
2. Extract all JSON paths from skill
3. Cross-reference each with official API spec
4. Flag any mismatches or invented items

Output format:

| Item | Found in Skill | Found in API | Match | Issue |
|------|---------------|--------------|-------|-------|
| [Method] | ✓ | ✓/✗ | ✓/✗ | [issue if mismatch] |

Overall: [PASS if all match, otherwise list invented items]
```

---

## Phase 4: Optimization Prompts

### P4.1: Description Optimization Prompt

```markdown
**Context**: Optimizing trigger accuracy for skill description.

**Objective**: Evaluate and improve description based on test queries.

**Prompt Template**:

Optimize description field for qcloud-[product]-ops:

Current description: [current description]
Eval queries: assets/eval_queries.json

Steps:
1. Run each query mentally and assess trigger likelihood
2. Identify false positives (should NOT trigger but would)
3. Identify false negatives (should trigger but wouldn't)
4. Propose adjustments

Evaluation criteria:
- Imperative phrasing ✓
- User intent focused ✓
- Implicit scenarios ✓
- Negative boundaries ✓
- Under 1024 chars ✓

Recommendations:
- [Adjustment 1]
- [Adjustment 2]

New description proposal: [proposed description]
```

---

## Prompt Effectiveness Tracking

| Prompt ID | Usage Count | Success Rate | Notes |
|-----------|-------------|--------------|-------|
| P1.1 | N/A | N/A | Track per use |
| P1.2 | N/A | N/A | Track per use |
| P2.1 | N/A | N/A | Track per use |
| P2.2 | N/A | N/A | Track per use |
| P3.1 | N/A | N/A | Track per use |
| P3.2 | N/A | N/A | Track per use |
| P4.1 | N/A | N/A | Track per use |

---

## Prompt Customization Guidelines

When adapting prompts:

1. **Replace placeholders**: `[Product Name]`, `[URL]`, etc.
2. **Add context**: Product-specific details
3. **Verify sources**: Ensure URLs are correct
4. **Test output**: Run prompt and check result quality

---

## Integration with Generation Workflow

| Workflow Step | Prompts Used |
|---------------|--------------|
| Step 1: Define Targets | P4.1 |
| Step 2: Analyze Sources | P1.1, P1.2 |
| Step 4: Populate SKILL.md | P2.1, P2.2 |
| Step 6: Verify & Review | P3.1, P3.2 |

---

## References

- [agentskills.io Description Optimization](https://agentskills.io/skill-creation/optimizing-descriptions)
- [Generation Workflow](../SKILL.md#evaluation-driven-generation-workflow)