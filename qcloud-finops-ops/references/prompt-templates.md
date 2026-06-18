# FinOps GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-finops-ops` |
| CLI | `tccli billing help` |
| max_iterations | 3 |
- **Advisory** — auto-execute ⇒ Safety=0

Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (FinOps).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **3**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (FinOps — 5 rules). Do not duplicate gate text here.

| Role | Action |
|---|---|
| Generator | Load rubric §4; map op → rule 1–5; run gates; append to trace `preflight` |
| Critic | Score rubric §3 + mark §4 rules VIOLATED / SATISFIED / NOT-APPLICABLE |
| Orchestrator | Safety=0 on §4 violation (destructive) → ABORT; advisory/read-only: rubric §2 |

API flows: [SKILL.md](../SKILL.md) (Pre-flight → Execute → Verify → Recover).

---

## 5. Anti-patterns (banned)


> Generic GCL anti-patterns: [../../qcloud-skill-generator/references/gcl-prompt-backbone.md](../../qcloud-skill-generator/references/gcl-prompt-backbone.md) §4.
> Below: **product-only** bans.


- ❌ **Logging secret content** — extending the AGENTS.md list with the
  FinOps-specific ban on letting `TENCENTCLOUD_SECRET_ID` /
  `TENCENTCLOUD_SECRET_KEY` / `TENCENTCLOUD_FINOPS_CONFIG` contents
  (webhook URLs) appear unmasked anywhere in command, response, or trace.

FinOps-specific anti-patterns (most common incidents per `rubric.md` §6
worked examples):

- ❌ **Auto-executing billing changes from FinOps** — the most expensive
  FinOps failure mode. The user asks "show me idle instances" and the
  agent terminates them. FinOps MUST surface a recommendation + a
  `delegation_markers` block; the actual destructive op must come from
  the target skill's GCL.
- ❌ **Direct `tccli cvm TerminateInstances` from FinOps** — the canonical
  boundary violation. FinOps must NEVER call any product-skill mutation
  API directly. The correct path is: emit a `delegation_markers` block
  with `target_skill: qcloud-cvm-ops`, `block_id`, and the resource IDs;
  the target skill's GCL handles the actual op with its own safety
  gates (id + name echo, dependency check, dry-run, two-step
  confirmation). Calling `tccli cvm TerminateInstances` directly from
  FinOps ⇒ ABORT (rule 5).
- ❌ **`DeleteBillSummary` without backup** — historical billing data is
  gone forever. The rubric must surface a backup path (export to COS
  first, verify checksum) and require the user to confirm the backup
  is verified. No backup ⇒ ABORT (rule 4 abort-class).
- ❌ **`RenewInstances` / `ModifyAutoRenewFlag` without the next-cycle
  warning** — the auto-renew flip takes effect on the next renewal
  cycle, not immediately. Users have been caught by surprise when an
  instance was renewed for another year after they expected the
  instance to expire. Always surface the next-cycle warning and require
  explicit confirmation (rule 2).
- ❌ **Raw `DescribeBillList` line items in trace** — `OwnerUin`,
  `InvoiceUrl`, `BillingContactEmail`, full voucher list. Replace with
  summary stats (`{keys, total, top_categories}`) at the Generator
  step, not later. PII in trace ⇒ ABORT (rule 1).
- ❌ **Treating idle detection as exact** — the `ii` + `iii` anomaly
  algorithm and the CLS / monitor-metric idle detection are
  **estimates**, not exact. CLS has sampling latency; monitor metrics
  have 1-minute granularity; the anomaly thresholds (ii=0.20,
  iii=0.80) are tunable in `example-config.yaml`. The Critic must
  flag any anomaly output that omits the baseline or the
  `ii_ratio` / `iii_ratio` math (rule 4).
- ❌ **Tag cost-allocation change without the retroactively-broken-report
  warning** — `CreateCostAllocationTag` does NOT re-attribute existing
  reports. The most common stakeholder complaint: "I changed the team
  tag from 'team-a' to 'team-b' but last month's report still shows
  'team-a' — the manager thinks team-b has zero costs". Always
  surface the warning (rule 3) and require the BEFORE/AFTER diff.
- ❌ **Changing `PeriodType` or `Dimension` silently on `ModifyBudget`**
  — the threshold-reduction false-alarm trap. The new `BudgetQuota`
  may match the user's request, but a silent `PeriodType` switch from
  `MONTH` to `QUARTER` (or `Dimension` switch from `project` to
  `tag`) changes the semantics. Always capture the BEFORE state via
  `DescribeBudget` and surface the full diff (rule 2).
- ❌ **Cross-skill delegation to a non-existent skill or to a script
  outside the skill system** — `target_skill` MUST be one of the 24
  canonical `qcloud-*-ops` skills. Delegating to a vanilla Python
  script or to a non-existent skill is a boundary violation (rule 5).
- ❌ **Invoice URLs / billing contact email in trace** — financial
  PII. Always mask as `<masked: invoice url>` / `<masked: billing
  contact>` before persisting the trace (rule 1).

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 FinOps rollout: Generator + Critic + Orchestrator templates (4-section stub covering §1 Generator delta + §4 per-operation variants + §5 FinOps-specific anti-patterns + §6 changelog). 5 rules: billing data privacy, no-auto-execute constraint, tag attribution timing, idle detection accuracy boundary, cross-skill delegation no-execution |
| 1.1.0 | 2026-06-19 | Tier A flesh-out (7 sections): §1 expanded to full Generator template with FinOps-specific pre-flight (Read-Only Assessment Mode gate, Mutation Confirmation Gate, Data-Privacy gate, cross-skill `block_id` assignment, billing PII masking at the Generator step); §2 new Critic template with explicit "MUST NOT see raw user request" gate, 5-dimension scoring with `correctness` default 0.5 (tightens to 1.0 for the 6 destructive / delegation ops), FinOps-specific `rule_violations` for rules 1-5, PII hygiene check, cross-skill delegation hygiene check, `tier: B-optional` + `max_iterations: 3` + `delegation_markers` fields; §3 new Orchestrator template with FinOps-specific decision flow (read op Safety=0 ⇒ RETRY not ABORT; direct mutation Safety=0 ⇒ ABORT; boundary-violating delegation ⇒ ABORT; cross-skill delegation special case verifying `target_skill` in 24-skill list + fresh `block_id` + user-confirmation timestamp; RECOMMENDATION final status); §4 expanded with 10 rows covering all direct mutations + cross-skill delegation + Read-Only Assessment Mode; §5 expanded with AGENTS.md §9 generic anti-patterns + 10 FinOps-specific anti-patterns (auto-execute billing changes, direct `tccli cvm TerminateInstances`, `DeleteBillSummary` without backup, `RenewInstances` without next-cycle warning, raw `DescribeBillList` PII, idle detection as exact, tag cost-allocation without retroactively-broken-report warning, silent `PeriodType` / `Dimension` on `ModifyBudget`, cross-skill delegation to non-existent skill, invoice URLs / billing contact in trace); §7 new See also. Sibling template backbone adapted from `qcloud-cos-ops/references/prompt-templates.md` v1.1.0 and `qcloud-vpc-ops/references/prompt-templates.md` v1.1.0 |

| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [AGENTS.md §9](../../AGENTS.md#9-anti-patterns-banned) — generic anti-patterns banned list
- [AGENTS.md §3 Rubric](../../AGENTS.md#3-rubric-mandatory-per-skill) — generic rubric spec (5 dimensions)
- [AGENTS.md §5 Termination](../../AGENTS.md#5-termination-first-match-wins) — `PASS` / `MAX_ITER` / `SAFETY_FAIL` semantics
- [AGENTS.md §8 Per-Skill Defaults](../../AGENTS.md#8-per-skill-defaults-qcloud) — `qcloud-finops-ops` is `optional`, `max_iter=3`
- [AGENTS.md §14 Reflexion Integration](../../AGENTS.md#14-reflexion-integration-lightweight-reflexion) — failure pattern memory for cross-session learning
- [rubric.md](rubric.md) — the rubric instance these templates score against (Tier A: 8 sections, 5 FinOps-specific safety rules, optional thresholds)
- [SKILL.md](../SKILL.md) — the build-time safety gates, 8 大核心模块, 5 个质量门, and `## Quality Gate (GCL)` per-skill header table
- [SKILL.md §Read-Only Assessment Mode](../SKILL.md#read-only-assessment-mode-delegate-from-qcloud-well-architected-review) — `qcloud-well-architected-review` delegate-from contract (Cost pillar)
- [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) — sibling templates (object storage pilot, Tier A `required`)
- [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md) — sibling templates (database pilot, Tier A `required`)
- [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) — sibling templates (compute pilot, Tier A `required`) — primary delegation target for `TerminateInstances` recommendations
- [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) — sibling templates (load balancer pilot) — delegation target for CLB recommendations
- [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) — sibling templates (object storage) — delegation target for COS lifecycle / idle-bucket recommendations
- [`references/finops-methodology.md`](finops-methodology.md) — anomaly `ii` + `iii` algorithm derivation, budget formula, optimization taxonomy
- [`references/billing-api-mapping.md`](billing-api-mapping.md) — `tccli billing / trade / voucher / tag` API surface and error codes
- [`references/cost-analysis-queries.md`](cost-analysis-queries.md) — tag whitelist (`business-line` / `dept` / `env` / `project-code` / `cost-center`), cost-allocation query patterns
- [`references/well-architected-assessment.md`](well-architected-assessment.md) — Read-Only Assessment Mode worker output contract (`product: finops`)
- [`assets/example-config.yaml`](../assets/example-config.yaml) — multi-account reserve, `mask_billing_pii`, anomaly thresholds
