# Shared Skill Boilerplate (TE-6 cross-file deduplication)

> Centralized sections that appear verbatim in every skill. Each SKILL.md
> references this file instead of inlining the content. Reduces ~400 tokens/skill.

---

## Five Core Standards (Quality Gates)

> See [AGENTS.md §Key conventions — Five Core Standards](../AGENTS.md#key-conventions).

Every skill MUST satisfy: (1) Clear Boundaries, (2) Structured I/O (`{{env.*}}`/`{{user.*}}`/`{{output.*}}`), (3) Explicit Actionable Steps, (4) Complete Failure Strategies (≥10 error codes, HALT vs retry per code), (5) Absolute Single Responsibility.

---

## Well-Architected Framework Integration

> Well-Architected pillars (Reliability, Security, Cost, Efficiency): see `references/well-architected-assessment.md`.

---

## Quality Gate (GCL)

> See [AGENTS.md §Runtime Quality Gates](../AGENTS.md#runtime-quality-gates-gcl--reflexion)
> and per-skill `references/rubric.md` + `references/prompt-templates.md`.

### Decision flow (first match wins)

1. **Safety = 0** OR rule violation in rubric §4 ⇒ **ABORT**
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions

For rubric dimensions, safety rules (§4), and worked examples (§6), see `references/rubric.md`.

---

## Safety Gates (Destructive Operations)

Every **delete / stop / restore** operation MUST have:

1. **Explicit user confirmation** with resource ID and name displayed
2. **Dependency check** (attached resources, downstream dependencies)
3. **Pre-backup reminder** (snapshot/backup before destructive op)
4. **Post-operation verification** (poll until terminal state)

For product-specific rules, see `references/rubric.md` §4.

---

## Output Schema (API response)

> Standard Tencent Cloud API response — see [AGENTS.md §SKILL.md frontmatter](../AGENTS.md#skillmd-frontmatter--required-fields).

```
{
  "Response": {
    "RequestId": "...",
    "Error": { "Code": "...", "Message": "..." }
  }
}
```

Error codes: see `references/troubleshooting.md` or `tccli <product> help`.

---

## Reference Directory

> Full reference table: see [AGENTS.md §Key References](../AGENTS.md#key-references).
> Per-skill references are listed in the skill's own `references/` directory.

Core references:

| Reference | Purpose |
|---|---|
| `references/core-concepts.md` | Architecture, limits, key concepts |
| `references/api-sdk-usage.md` | API spec, operation map, pagination |
| `references/cli-usage.md` | `tccli <product>` command reference |
| `references/sdk-templates.md` | SDK init/poll/error boilerplate |
| `references/troubleshooting.md` | Error codes and diagnostic workflows |
| `references/well-architected-assessment.md` | 4-pillar assessment |
| `references/rubric.md` | GCL rubric (5 dimensions + safety rules) |
| `references/prompt-templates.md` | GCL Generator/Critic/Orchestrator prompts |

Optional: `references/monitoring.md`, `references/finops-*.md`, `references/aiops-*.md`, `references/secops-*.md`.

---

## Operational Best Practices

- **Least privilege**: CAM policies scoped to minimal required APIs
- **Availability**: Multi-AZ deployment for production workloads
- **Backup**: Regular snapshots/backups; test restore quarterly
- **Cost**: Postpaid for dev/test; prepaid for stable prod
- **Monitoring**: Set up health checks and alarms (see `references/monitoring.md`)
