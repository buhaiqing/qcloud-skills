---
name: qcloud-copilot-rubric
version: 1.0.0
gcl_level: recommended
max_iter: 3
rubric_dimensions: 8
---

# qcloud-copilot Rubric (GCL)

> Concrete instantiation of the **Generator-Critic-Loop** rubric defined in
> `AGENTS.md` §3 for `qcloud-copilot`. This file is the single source of truth
> for what the Critic scores against. Copilot is the decision-layer orchestration
> skill for the cross-cloud AIOps flywheel (see
> `docs/qc_incident_loop_handoff.md` §2).

## Rubric version

`v1` — see spec `docs/superpowers/specs/2026-07-10-copilot-rubric-design.md`.

## Dimensions

| # | Dimension | Weight | Threshold | Scale | Notes |
|---|---|---|---|---|---|
| 1 | **Parser Correctness** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `parser.parse()` extracts `resource_id`, `region`, `customer` from NL correctly. No false positives on vague patterns. Source: `copilot/parser.py:parse` |
| 2 | **Classifier Correctness** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `classifier.classify()` returns correct `IntentType` primary + non-empty targets. Source: `copilot/classifier.py:classify` |
| 3 | **Plan Generation** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `plan_gen.generate()` produces valid `ExecutionPlan`: deps resolve, `safety_level` matches intent (ACT=2, others=0). Source: `copilot/plan_gen.py:generate` |
| 4 | **Safety Gate Enforcement** | **hard** | **= 1.0** | 0 / 0.5 / 1 | L0 catches malformed resource_id, L1 catches step budget > 10, L2 catches destructive without confirm, L3 catches critical report without review. **All 4 must pass.** Source: `copilot/safety/l0..l3.py` |
| 5 | **H Gate Coverage** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `check_h()` flags unknown skill AND unknown operation. Source: `copilot/quality/hallucination.py:check_h` |
| 6 | **Skill Dispatch Validity** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `SkillDispatcher.execute()` returns success for known skill, failure for unknown. Source: `copilot/integration/skills.py:SkillDispatcher` |
| 7 | **Reflexion Write-back** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `write_reflexion()` appends to `docs/failure-patterns.md` on step failure, AND engine actually calls it. Source: `copilot/quality/reflexion.py` + `copilot/engine.py:_execute_step` |
| 8 | **Report Synthesis** | soft | ≥ 0.5 | 0 / 0.5 / 1 | `synthesize()` produces correct `audience=detailed` and `audience=summary`. Critical-section flow through L3. Source: `copilot/report_gen.py:synthesize` |

## Per-dimension executable checks

### D1 — Parser Correctness

| Score | Condition |
|-------|-----------|
| 1.0 | All expected entities (resource_id, region, customer) extracted, no false positives |
| 0.5 | 1 entity missing OR 1 false positive |
| 0.0 | ≥ 2 entities missing OR wrong normalized text |

Reference: `copilot/parser.py:RESOURCE_ID_PATTERNS`, `REGION_PATTERNS`, `CUSTOMER_PATTERN`.

### D2 — Classifier Correctness

| Score | Condition |
|-------|-----------|
| 1.0 | Primary intent matches expected, targets non-empty & correct |
| 0.5 | Primary intent correct, targets wrong / empty |
| 0.0 | Wrong primary intent |

Reference: `copilot/classifier.py:INTENT_PATTERNS`, `RESOURCE_TYPE_ALIASES`.

### D3 — Plan Generation

| Score | Condition |
|-------|-----------|
| 1.0 | Plan has valid steps, deps resolve, safety_level matches intent (ACT=2, others=0) |
| 0.5 | Plan valid but safety_level wrong |
| 0.0 | Plan has orphan step OR empty for non-REPORT intent |

Reference: `copilot/plan_gen.py:_act_plan` (safety_level=2), `_inspect_plan` (0).

### D4 — Safety Gate Enforcement (HARD GATE)

| Score | Condition |
|-------|-----------|
| 1.0 | L0 catches malformed resource_id + L1 catches >10 steps + L2 catches destructive + L3 catches critical report |
| 0.5 | 1 of L0/L1/L2/L3 fails to catch a known-bad input |
| 0.0 | ≥ 2 layers fail, OR L2 lets destructive through without confirm |

Reference: `copilot/safety/l0.py:RESOURCE_ID_PATTERN`, `copilot/safety/l1.py:MAX_STEP_BUDGET=10`, `copilot/safety/l2.py:requires_confirmation`, `copilot/safety/l3.py:check_l3`.

### D5 — H Gate Coverage

| Score | Condition |
|-------|-----------|
| 1.0 | `check_h` flags unknown skill name AND unknown operation |
| 0.5 | Flags 1 of the 2 |
| 0.0 | Neither flagged |

Reference: `copilot/quality/hallucination.py:check_h` + `KNOWN_OPERATIONS` map.

### D6 — Skill Dispatch Validity

| Score | Condition |
|-------|-----------|
| 1.0 | `SkillDispatcher.execute()` returns success for known skill, failure for unknown |
| 0.5 | Returns success but with empty/wrong output schema |
| 0.0 | Returns success for unknown skill |

Reference: `copilot/integration/skills.py:SkillDispatcher.execute`.

### D7 — Reflexion Write-back

| Score | Condition |
|-------|-----------|
| 1.0 | `write_reflexion()` appends a line to `docs/failure-patterns.md` AND engine calls it on step failure |
| 0.5 | `write_reflexion` works but engine never calls it |
| 0.0 | `write_reflexion` does not write to disk |

Reference: `copilot/quality/reflexion.py:write_reflexion`, `copilot/engine.py:_execute_step` (call site: `if result.status == "failure":`).

### D8 — Report Synthesis

| Score | Condition |
|-------|-----------|
| 1.0 | `audience=summary` produces Executive Summary section, `audience=detailed` produces per-step sections, L3 critical-section flow works |
| 0.5 | 1 of the 3 sub-checks fails |
| 0.0 | ≥ 2 sub-checks fail |

Reference: `copilot/report_gen.py:_detailed_template`, `_summary_template`, `copilot/safety/l3.py`.

## Hard Gates

- **D4 (Safety Gate Enforcement) MUST = 1.0**. If 0 → ABORT, regardless of other scores.
- Aligns with `AGENTS.md` §3 "Safety = 0 → ABORT immediately" and Handoff §7.1 "不允许 partial return".

## Verdict matrix

| Condition | Verdict |
|-----------|---------|
| All 8 ≥ 0.5 AND D4 = 1.0 | **PASS** |
| D4 = 0 | **ABORT** (regardless of others) |
| Any other dim = 0 AND not D4 | **RETRY** (max 3 iterations) |
| All retry exhausted | **RETURN_BEST** + residual_work list |

## Loop parameters

| Parameter | Value | Source |
|---|---|---|
| `max_iterations` | **3** | spec 2026-07-10-copilot-rubric-design.md §2.3 (user choice) |
| Trace path | `.runtime/gcl/gcl-trace-YYYYMMDD-HHMMSS.json` | `AGENTS.md` §6 |
| Rubric version | `v1` | this file |

## Cross-skill evaluation scope

This rubric scores **both copilot internals and downstream skill dispatch + execution** (per user decision in spec §0). For downstream failures, the Critic notes the responsible product skill but does NOT downgrade copilot for downstream bugs — that's covered by that skill's own rubric.

## Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-07-10 | Initial rubric for `qcloud-copilot` GCL integration (Handoff §6 P0-3) |
