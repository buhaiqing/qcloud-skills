# User Experience Specification

This document defines mandatory UX requirements for all Tencent Cloud generated skills.

---

## Overview

Every generated `qcloud-[product]-ops` skill MUST comply with this UX specification to ensure:
- Fast onboarding (< 60s to first command)
- Minimal prompts (≤ 3 for common operations)
- Clear feedback (success/failure visible)
- User-friendly error handling (actionable messages)

---

## 1. Onboarding Experience

### 1.1 Quick Start Requirements

| Requirement | Target | Verification |
|-------------|--------|--------------|
| First command execution | < 60s | Time from skill load to first API call |
| Setup steps | ≤ 5 | Number of prerequisite steps |
| Documentation navigation | ≤ 2 clicks | From Quick Start to any reference |

### 1.2 Quick Start Template

```markdown
## Quick Start

### What This Skill Does
[1-2 sentence description of capabilities]

### Prerequisites
- [ ] tccli CLI installed (`pip install tccli`)
- [ ] Credentials: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`
- [ ] Region: `TENCENTCLOUD_REGION`

### Verify Setup (10s)
```bash
tccli cvm DescribeZones --Region ap-guangzhou
```

### Your First Command (30s)
```bash
# List resources
tccli [product] Describe[Resources] --Region {{env.TENCENTCLOUD_REGION}}
```

### Next Steps
- [Common Operations](#execution-flows) — Create, manage, delete
- [Troubleshooting](references/troubleshooting.md) — Fix issues
```

### 1.3 Progressive Disclosure

Complex content should be progressively disclosed:

| Level | Content | Location |
|-------|---------|----------|
| Level 1 (Immediate) | Quick Start, First Command | SKILL.md top |
| Level 2 (Next) | Common Operations | SKILL.md Execution Flows |
| Level 3 (Deep) | API details, Troubleshooting | references/*.md |
| Level 4 (Expert) | Advanced patterns, Optimization | references/optimization-analysis.md |

---

## 2. Interaction Design

### 2.1 Prompt Minimization

| Operation Type | Max Prompts | Default Strategy |
|---------------|-------------|-------------------|
| Read-only (Describe, List) | 0 | Use env region, no filters |
| Create | ≤ 2 | Smart defaults for optional params |
| Modify | ≤ 1 | Confirm changes only |
| Delete | 1 (confirmation) | MUST confirm |

### 2.2 Smart Defaults

```markdown
| Parameter | Default | When to Ask User |
|-----------|---------|------------------|
| Region | `{{env.TENCENTCLOUD_REGION}}` | Only if env unset |
| InstanceType | Product-specific baseline | User wants custom |
| ImageId | Latest stable OS image | User specifies version |
| SecurityGroups | Default SG if exists | User needs custom |
```

### 2.3 Batch Operations

For ≥ 3 resources, batch mode reduces prompts:

```bash
# Batch create (single prompt for count)
tccli cvm RunInstances --InstanceCount 5 ...

# Batch modify (single confirmation)
tccli cvm ModifyInstancesAttribute --InstanceIds "[ins-1,ins-2,ins-3]" --InstanceName "prefix"
```

---

## 3. Feedback Design

### 3.1 Success Feedback

```markdown
**Format:**
✅ [Operation] completed successfully

**Details:**
- Resource ID: [ID]
- Status: [Status]
- Time: [Duration]

**Example:**
✅ Instance created successfully

Details:
- Instance ID: ins-xxx
- Status: RUNNING
- Creation time: 45s
```

### 3.2 Progress Feedback

For operations > 5s, show progress:

```bash
# Polling progress
⏳ Waiting for instance to reach RUNNING status...
  [1/60] Status: PENDING (5s elapsed)
  [12/60] Status: RUNNING ✅ (60s elapsed)

Total time: 60s
```

### 3.3 Failure Feedback

See Section 5 for error handling format.

---

## 4. Safety Gates

### 4.1 Destructive Operation Confirmation

```markdown
⚠️ **Confirm Destructive Operation**

You are about to:
- **Action**: DELETE (irreversible)
- **Resource**: [Resource Type]
- **Name**: [Resource Name]
- **ID**: [Resource ID]

This operation CANNOT be undone.

Type "CONFIRM" to proceed, or "CANCEL" to abort.
```

### 4.2 Pre-Backup Reminder

```markdown
💡 **Backup Reminder**

Before deleting/modifying, consider creating a backup:

```bash
# Create backup first
tccli [product] CreateSnapshot --ResourceId [ID]
```

Would you like to create a backup before proceeding?
[Yes] [No] [Skip]
```

---

## 5. Error Handling UX

### 5.1 Error Message Format

```markdown
[ERROR] [Code]: [Summary]

**What happened:** [Plain language explanation]

**How to fix:** [Specific action steps]

**Next step:** [Immediate recommendation]

**Example:**

[ERROR] InvalidParameter: Invalid instance type

What happened: The specified InstanceType "S5.XXXXX" is not valid or not available in this region.

How to fix: 
1. Check available instance types: `tccli cvm DescribeInstanceTypeConfigs --Region ap-guangzhou`
2. Choose a valid type from the list
3. Retry with correct InstanceType

Next step: Run DescribeInstanceTypeConfigs and retry with valid type.
```

### 5.2 Error Categories and UX

| Category | UX Tone | User Action |
|----------|---------|-------------|
| InvalidParameter | Educational | Fix and retry |
| QuotaExceeded | HALT | Request increase |
| InvalidSecretKey | HALT | Fix credentials |
| ResourceNotFound | Guidance | Verify ID |
| InternalError | Retry + Escalate | Retry or contact support |
| RateLimitExceeded | Patience | Wait and retry |

### 5.3 Retry Guidance

```markdown
⏳ **Temporary Error - Retry Recommended**

Error: RequestLimitExceeded
Retrying in: 5s (attempt 1/3)

If error persists after 3 retries:
- Wait 60s before retrying
- Consider reducing request frequency
- Escalate with RequestId: [ID]
```

---

## 6. Accessibility

### 6.1 Clear Language

- Use plain language, avoid jargon
- Explain technical terms inline
- Provide context for region/zone codes

### 6.2 Visual Indicators

| Indicator | Meaning |
|-----------|---------|
| ✅ | Success |
| ⚠️ | Warning |
| ❌ | Error |
| ⏳ | In progress |
| 💡 | Suggestion |
| 🔒 | Security-related |

### 6.3 Formatting Standards

- **Bold** for emphasis: resource IDs, parameters
- `Code` for CLI commands, JSON paths
- *Italics* for notes, warnings
- Lists for multiple items or steps

---

## 7. Skill-Level UX Checklist

Generated skills MUST include:

| Item | Required | Location |
|------|----------|----------|
| Quick Start section | ✓ | SKILL.md top |
| Prerequisites checklist | ✓ | Quick Start |
| First command example | ✓ | Quick Start |
| Safety gate for delete | ✓ | Delete operation |
| Error message format | ✓ | Failure Recovery table |
| Progress indicator example | ✓ | Post-execution |
| Smart defaults table | ✓ | Variables section |

---

## 8. UX Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Time to first success | < 60s | User journey timing |
| Error resolution time | < 2 min | From error to retry |
| User satisfaction | ≥ 8/10 | Feedback survey |
| Documentation clarity | ≥ 8/10 | Readability score |

---

## References

- [Tencent Cloud Console UX](https://cloud.tencent.com)
- [Agent Skill UX Best Practices](https://agentskills.io)