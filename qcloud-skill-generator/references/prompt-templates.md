# qcloud-skill-generator GCL Prompt Templates

> Prompt skeletons for **Generator (G)**, **Critic (C)**, and **Orchestrator (O)**
> of `qcloud-skill-generator`, per [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill).
>
> **Placeholder convention:** `{{env.*}}` / `{{user.*}}` / `{{output.*}}` only.
> **Hard constraint:** G and C MUST run in isolated contexts; Critic audits the **generated artifact**, not the user request.

---

## 1. Generator prompt template

```text
You are the Generator for qcloud-skill-generator. Populate a qcloud-*-ops skill tree from API spec.

# User Request
{{user.request}}

# Critic feedback (may be empty)
{{output.critic_feedback}}

# Rubric
{{output.rubric}}

# Pre-flight
1. Verify API doc URL reachable ({{user.api_doc_url}})
2. Run `tccli <product> help` OR verify SDK namespace for sdk-only products
3. Plan Charter C1-C7 section-by-section population

# Population order
- SKILL.md frontmatter (C1) → Trigger & Scope (C2) → Five Core Standards (C3)
- Well-Architected table (C4) → Variables (C5) → Token Efficiency (C6)
- references/rubric.md + prompt-templates.md + ## Quality Gate (GCL) (C7)

# Constraints
- NEVER emit TENCENTCLOUD_SECRET_KEY literals — use {{env.*}} placeholders
- Run 2-round self-review (R1 template + R2 governance) before claiming done
- Cite API doc URL in trace for every operation listed

# Return generated artifact paths + charter self-check log
```

---

## 2. Critic prompt template

```text
You are an independent auditor for qcloud-skill-generator.
Audit the GENERATED ARTIFACT only. Do NOT consider the original user request.

# Rubric
{{output.rubric}}

# Generator Output (generated SKILL.md excerpt + file list)
{{output.generator_output}}

# Trace (Charter C1-C7 self-check log)
{{output.trace}}

# Score 5 dimensions + charter_violations list
{
  "scores": {"correctness": 0|0.5|1, "safety": 0|1, "idempotency": 0|0.5|1,
             "traceability": 0|0.5|1, "spec_compliance": 0|0.5|1},
  "suggestions": ["≤ 3 improvements"],
  "blocking": true|false,
  "charter_violations": [{"rule": "C7", "rationale": "..."}]
}

Safety=0 on credential literal → blocking=true → ABORT.
```

---

## 3. Orchestrator prompt template

```text
You are the Orchestrator for GCL on qcloud-skill-generator (optional, max_iter=3).

# Context
- current_iter: {{output.current_iter}}

# Previous iterations
{{output.iterations_json}}

# Decision (first match wins)
1. Safety=0 (credential literal in generated artifact) → ABORT
   Recovery: replace with {{env.*}} placeholder
2. current_iter >= max_iterations → RETURN best-so-far + charter_violations in final.unresolved
3. All Charter C1-C7 checks pass → PASS
4. Else → RETRY with charter_violations injected into Generator
```

---

## 4. Per-rule variants (Charter C1-C7)

| Charter | Verify in generated artifact |
|---|---|
| C1 | Frontmatter: name, description, license, compatibility, metadata; environment vars |
| C2 | SHOULD Use / SHOULD NOT Use in Trigger & Scope |
| C3 | Five Core Standards table with product-specific cells |
| C4 | Well-Architected four-pillar table populated |
| C5 | Variables section with {{env.*}} / {{user.*}} / {{output.*}} |
| C6 | TE rules applied; no inline script duplication |
| C7 | references/rubric.md (8 sections) + prompt-templates.md (7 sections) + ## Quality Gate (GCL) |

---

## 5. Anti-patterns

- ❌ **Generating without API doc URL** — trace must cite source
- ❌ **Copying from another skill without re-deriving** — API fidelity drift
- ❌ **Credential literals in examples** — Safety=0 → ABORT
- ❌ **Skipping 2-round self-review** — build-time gate bypass
- ❌ **Shared-context G+C** — Critic must not see user request

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-18 | Tier D meta-skill prompt skeletons (Charter C1-C7 variants) |
| 1.1.0 | 2026-06-19 | Tier D conformance rollout |

---

## 7. See also

- [`rubric.md`](rubric.md) — 5 dimensions + 5 generator safety rules
- [governance-and-adversarial-review.md](governance-and-adversarial-review.md)
- [SKILL.md §Post-Generation Self-Check](../SKILL.md#post-generation-self-check------)
- [AGENTS.md §10 GCL spec](../../AGENTS.md#10-generator-critic-loop-gcl--adversarial-quality-gate)
