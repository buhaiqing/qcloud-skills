# qcloud-skill-generator Quality-Gate Rubric (GCL)

> Runtime scoring rubric for **Generator-Critic-Loop (GCL)** of `qcloud-skill-generator`.
> This skill has **no destructive cloud operations**, so the rubric audits the **generated
> artifact** (a `qcloud-*-ops/SKILL.md` + `references/` tree), not cloud resources.

---

## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| Every skill-generation run: populating `SKILL.md`, `references/*`, `assets/*` from API spec | Live execution against cloud accounts (use the generated `qcloud-*-ops` skill instead) |
| Regeneration / realignment when API docs change | One-off debugging with no intent to maintain a reusable skill |
| Charter C1-C7 self-check after population | Skill execution at runtime (governed by the generated skill's own rubric) |

---

## 2. Five rubric dimensions (mandatory)
> **TE-6:** 5-dimension skeleton → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md).


| # | Dimension | Threshold | Why this threshold for skill-generation |
|---|---|---|---|
| 1 | **Correctness** | ≥ 0.5 (1.0 required for Charter C1, C5) | A half-correct frontmatter is unusable; half-correct Variables section breaks prompt injection safety |
| 2 | **Safety** | **= 1** (strict) | Generator MUST NOT emit `TENCENTCLOUD_SECRET_KEY` literals; MUST require env-var injection |
| 3 | **Idempotency** | ≥ 0.5 | Regenerating an existing skill must not duplicate sections; 2-round self-review already covers this |
| 4 | **Traceability** | ≥ 0.5 | Every generated `SKILL.md` must cite the API doc URL it was derived from |
| 5 | **Spec Compliance** | ≥ 0.5 | Generated skill must pass Charter C1-C7 (frontmatter, SHOULD/SHOULD NOT, Five Core Standards, Well-Architected, Variables, Token Efficiency, GCL Quality Gate) |

**Safety = 0 → ABORT immediately**. See [AGENTS.md §5](../../AGENTS.md#5-termination-first-match-wins) → `SAFETY_FAIL`.

---

## 3. Per-dimension scoring checklist

### 3.1 Correctness (weight: high)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Frontmatter has `name`, `description`, `license`, `compatibility`, `metadata` (Charter C1) | ✓ all 5 present | 1 missing | ≥ 2 missing |
| API operation list matches `tccli <product> help` (PRIMARY) or tencentcloud-sdk-python (FALLBACK) | ✓ verified against `tccli help` output for the product slug | 1 of N operations missing | Operation invoked that does not exist in API |

### 3.2 Safety (weight: highest; threshold = 1)

| Check | Score 1 | Score 0 |
|---|---|---|
| Generated skill does NOT contain `SecretKey=...` or `TENCENTCLOUD_SECRET_KEY=...` literals in any example | ✓ | any literal credential present |
| Frontmatter `environment:` block lists `TENCENTCLOUD_SECRET_ID` / `TENCENTCLOUD_SECRET_KEY` / `TENCENTCLOUD_REGION` (Charter C1) | ✓ | missing or hard-coded |
| Generated `references/rubric.md` has `safety = 1.0` threshold for destructive ops | ✓ | threshold < 1.0 |
| Generated `references/prompt-templates.md` §2 Critic prompt is **isolated-context** (Critic does not see user request) | ✓ | shared-context G+C |

### 3.3 Idempotency (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Re-running on existing skill does not duplicate sections | ✓ | duplicates introduced but logged | silently overwrites user-edited sections |
| 2-round self-review (`R1` content audit + `R2` governance) executed | ✓ both | R1 only | neither |

### 3.4 Traceability (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Every cited API operation has a doc URL in the trace | ✓ | partial | none |
| Charter C1-C7 self-check log persisted to trace | ✓ | C1-C5 only | no log |

### 3.5 Spec Compliance (weight: medium)

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Charter C7 (GCL Quality Gate) passes for generated skill | ✓ | partial (rubric OR prompt, not both) | neither |
| Five Core Standards table populated with product-specific content | ✓ | table present but cells empty | table missing |
| Well-Architected four-pillar table populated | ✓ | one pillar empty | two or more empty |

---

## 4. qcloud-skill-generator-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | Populate `references/rubric.md` | MUST include `safety = 1.0` threshold for destructive ops of the generated product; MUST list ≥ 5 product-specific safety rules; MUST cross-reference the generated skill's SKILL.md `## Safety Gates` chapter | Generated skills that ship without a tight safety rubric are not safe to merge |
| 2 | Populate `references/prompt-templates.md` | §2 Critic prompt MUST be **isolated-context** (Critic does not see raw user request); MUST include `rule_violations` field for audit; MUST cite the rubric's `thresholds` block | Without isolated-context, the Critic rubber-stamps the Generator (AGENTS.md §2) |
| 3 | Populate `## Quality Gate (GCL)` in SKILL.md | MUST include the 5-row property table (`GCL applicability` / `max_iterations` / `Rubric instance` / `Prompt templates` / `Trace path`); MUST list the product-specific safety rules in the SKILL.md chapter | Charter C7 enforcement; ensures generated skills are GCL-conformant from birth |
| 4 | Populate frontmatter `metadata.cli_applicability` | MUST be one of `cli-first` / `dual-path` / `sdk-only` / `cli-only`; MUST cite evidence in `cli_support_evidence` | Missing applicability breaks the dual-path / SDK-only execution decision in generated skills |
| 5 | Real-time API doc changes | MUST diff old vs new spec and surface breaking changes in trace; MUST bump `metadata.last_updated` and the skill's changelog | Silent realignment causes generation drift |

---

## 5. Output schema (returned by Critic)

Strict JSON, same shape as the GCL spec in [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill):

```json
{
  "scores": {
    "correctness": 0|0.5|1,
    "safety": 0|1,
    "idempotency": 0|0.5|1,
    "traceability": 0|0.5|1,
    "spec_compliance": 0|0.5|1
  },
  "suggestions": ["≤ 3 concrete, executable improvements"],
  "blocking": true|false,
  "charter_violations": [
    {"rule": "C7", "rationale": "Generated qcloud-foo-ops missing references/rubric.md"}
  ],
  "thresholds": {
    "correctness": 0.5,
    "safety": 1.0,
    "idempotency": 0.5,
    "traceability": 0.5,
    "spec_compliance": 0.5
  },
  "rubric_version": "v1"
}
```

`charter_violations` is **qcloud-skill-generator-specific** (rules 1-5 in §4) and is the
audit trail the meta-skill emits to track which Charter checks fire most often.

---

## 6. Worked examples

### Example A — PASS on generating qcloud-cvm-ops

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | Frontmatter has all 5 keys (Charter C1); operations verified against `tccli cvm help` |
| Safety | 1 | No credential literals; rubric has `safety = 1.0`; Critic prompt is isolated-context |
| Idempotency | 1 | 2-round self-review (R1 + R2) executed; no section duplication |
| Traceability | 1 | All API ops cited; C1-C7 self-check logged to trace |
| Spec Compliance | 1 | Charter C7 passes; Five Core Standards + Well-Architected tables populated |

`blocking: false`. `final: PASS, iter: 1`.

### Example B — SAFETY_FAIL on generating qcloud-foo-ops with credential leak

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | — |
| **Safety** | **0** | Rule 1 violated: generated `references/api-sdk-usage.md` contains `TENCENTCLOUD_SECRET_KEY=AKID...` literal in example |
| Idempotency | 1 | — |
| Traceability | 1 | — |
| Spec Compliance | 0.5 | Charter C7 partial — rubric is present but prompt templates §2 Critic uses shared-context |

`blocking: true`. `charter_violations: [{rule: "C1", rationale: "credential literal in api-sdk-usage.md example"}]`. **ABORT** — recover by replacing the literal with `{{env.TENCENTCLOUD_SECRET_KEY}}`.

### Example C — RETRY on missing Quality Gate section

| Dimension | Score | Justification |
|---|---|---|
| Correctness | 1 | Frontmatter OK |
| Safety | 1 | — |
| Idempotency | 1 | — |
| Traceability | 1 | — |
| **Spec Compliance** | **0** | Charter C7 violated: generated SKILL.md has no `## Quality Gate (GCL)` section |

`blocking: true`. After re-generation with the GCL section appended, Spec Compliance scores 1.

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-18 | Phase D meta-skill rubric (5 dimensions, 5 generator-specific safety rules, worked examples) |
| 1.1.0 | 2026-06-19 | Tier D conformance rollout |

---

## 8. See also

- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill)
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-skill-generator` is `optional`, `max_iter=3`
- [AGENTS.md §10 GCL spec](../../AGENTS.md#10-generator-critic-loop-gcl--adversarial-quality-gate)
- [`prompt-templates.md`](prompt-templates.md) — G/C/O prompt skeletons
- [SKILL.md §Post-Generation Self-Check](../SKILL.md#post-generation-self-check------) — build-time sibling
